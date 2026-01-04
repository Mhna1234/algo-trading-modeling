import json
import logging
import boto3
import os
from datetime import datetime, timedelta
from io import StringIO, BytesIO
import traceback

# Configure logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import your existing trading engine
import sys
sys.path.insert(0, '/var/task')
from src.daily_trading_engine import DailyTradingEngine
from src.checkpoint_manager import CheckpointManager
from src.config_loader import load_trading_config
from src.bandits.ucb import UCBBandit
from src.bandits.thompson import ThompsonSamplingBandit
from src.bandits.exp3 import EXP3Bandit

# AWS clients
s3_client = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

# Configuration from environment variables
BUCKET_NAME = os.environ.get('S3_BUCKET', 'sama-algo-trading-prod')
CHECKPOINTS_PREFIX = os.environ.get('CHECKPOINTS_PREFIX', 'checkpoints/')
DATA_PREFIX = os.environ.get('DATA_PREFIX', 'data/')
RESULTS_PREFIX = os.environ.get('RESULTS_PREFIX', 'results/')
CONFIG_KEY = os.environ.get('CONFIG_KEY', 'config/trading_config.yaml')


def lambda_handler(event, context):
    """
    Main Lambda handler for daily algorithmic trading workflow.
    
    Event format:
    {
        "action": "trade" | "validate" | "reset",
        "override_config": { optional config overrides }
    }
    
    Returns:
        {
            "statusCode": 200 | 400 | 500,
            "body": { execution results },
            "timestamp": ISO timestamp
        }
    """
    execution_start = datetime.utcnow()
    
    try:
        action = event.get('action', 'trade')
        logger.info(f"Lambda execution started. Action: {action}")
        
        # Load configuration from S3
        config = load_config_from_s3()
        
        # Apply overrides if provided
        if 'override_config' in event:
            config.update(event['override_config'])
            logger.info(f"Applied config overrides: {list(event['override_config'].keys())}")
        
        # Route to appropriate handler
        if action == 'trade':
            result = execute_daily_trading(config)
        elif action == 'validate':
            result = validate_system(config)
        elif action == 'reset':
            result = reset_state(config)
        else:
            return error_response(f"Unknown action: {action}", 400)
        
        # Calculate execution time
        execution_time = (datetime.utcnow() - execution_start).total_seconds()
        logger.info(f"Execution completed in {execution_time:.2f}s")
        
        # Publish metrics to CloudWatch
        publish_metrics(action, execution_time, 'SUCCESS')
        
        return success_response(result, execution_time)
    
    except Exception as e:
        execution_time = (datetime.utcnow() - execution_start).total_seconds()
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Lambda execution failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Publish failure metrics
        publish_metrics(event.get('action', 'trade'), execution_time, 'FAILURE')
        
        return error_response(error_msg, 500, traceback.format_exc())


def execute_daily_trading(config):
    """
    Execute the daily trading workflow:
    1. Load latest checkpoint
    2. Fetch new market data
    3. Prepare local /tmp/ filesystem for DailyTradingEngine
    4. Initialize bandit allocator
    5. Run optimization
    6. Save new checkpoint
    7. Save results
    """
    logger.info("=" * 60)
    logger.info("STARTING DAILY TRADING EXECUTION")
    logger.info("=" * 60)
    
    try:
        # Step 1: Load checkpoint from S3
        logger.info("Step 1: Loading latest checkpoint from S3...")
        checkpoint_data = load_latest_checkpoint()
        
        # Step 2: Fetch new market data from S3
        logger.info("Step 2: Fetching new market data from S3...")
        market_data = fetch_market_data(checkpoint_data)
        
        # Step 3: Prepare /tmp/ filesystem for DailyTradingEngine
        logger.info("Step 3: Preparing local filesystem in /tmp/...")
        prepare_tmp_directory(checkpoint_data, market_data)
        
        # Step 4: Initialize bandit allocator
        logger.info("Step 4: Initializing bandit allocator...")
        bandit = initialize_bandit(config, checkpoint_data)
        
        # Step 5: Initialize trading engine
        logger.info("Step 5: Initializing DailyTradingEngine...")
        engine = DailyTradingEngine(
            data_dir='/tmp/data',
            checkpoint_dir='/tmp/checkpoints',
            strategy_config={
                'bandit_type': config.get('bandit', {}).get('type', 'ucb'),
                'burn_in_periods': config.get('bandit', {}).get('burn_in_periods', 12)
            }
        )
        
        # Step 6: Run daily update
        logger.info("Step 6: Running daily trading update...")
        trading_result = engine.run_daily_update(bandit)
        
        # Check if update was successful
        if trading_result is None:
            logger.info("No trading update performed (no new data or already up-to-date)")
            return {
                "action": "trade",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "No update needed - already up-to-date"
            }
        
        # Step 7: Save new checkpoint
        logger.info("Step 7: Saving new checkpoint to S3...")
        # Load the checkpoint that was just created by the engine
        new_checkpoint = load_checkpoint_from_tmp()
        save_checkpoint_to_s3(new_checkpoint, bandit)
        
        # Step 8: Save detailed results
        logger.info("Step 8: Saving results to S3...")
        today = datetime.utcnow().strftime('%Y-%m-%d')
        save_results_to_s3(trading_result, today)
        
        logger.info("Daily trading execution completed successfully")
        
        return {
            "action": "trade",
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_value": trading_result.summary_metrics.get('final_value'),
            "total_return": trading_result.summary_metrics.get('total_return'),
            "sharpe_ratio": trading_result.summary_metrics.get('sharpe_ratio'),
            "message": "Daily trading completed successfully"
        }
    
    except Exception as e:
        logger.error(f"Daily trading execution failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def prepare_tmp_directory(checkpoint_data, market_data):
    """
    Prepare /tmp/ directory with checkpoint and market data.
    DailyTradingEngine expects files to exist in these locations.
    """
    try:
        # Create necessary directories
        os.makedirs('/tmp/data', exist_ok=True)
        os.makedirs('/tmp/checkpoints', exist_ok=True)
        
        # Save checkpoint to /tmp/checkpoints/
        checkpoint_path = '/tmp/checkpoints/latest.json'
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
        logger.info(f"Saved checkpoint to {checkpoint_path}")
        
        # Save market data to /tmp/data/
        data_path = '/tmp/data/price_data_latest.csv'
        market_data.to_csv(data_path)
        logger.info(f"Saved market data to {data_path}")
        logger.info(f"Data shape: {market_data.shape}")
        
    except Exception as e:
        logger.error(f"Failed to prepare /tmp/ directory: {str(e)}")
        raise


def load_checkpoint_from_tmp():
    """Load the most recent checkpoint from /tmp/checkpoints/"""
    try:
        checkpoint_dir = '/tmp/checkpoints'
        checkpoint_files = [f for f in os.listdir(checkpoint_dir) if f.endswith('.json')]
        
        if not checkpoint_files:
            logger.warning("No checkpoint files found in /tmp/checkpoints/")
            return None
        
        # Get the most recent checkpoint
        latest_file = max(checkpoint_files, key=lambda f: os.path.getmtime(os.path.join(checkpoint_dir, f)))
        checkpoint_path = os.path.join(checkpoint_dir, latest_file)
        
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
        
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
        return checkpoint
        
    except Exception as e:
        logger.error(f"Failed to load checkpoint from /tmp/: {str(e)}")
        raise


def initialize_bandit(config, checkpoint_data):
    """
    Initialize or restore bandit allocator.
    Tries to restore state from checkpoint if available.
    """
    try:
        # Determine bandit type from config
        bandit_type = config.get('bandit', {}).get('type', 'ucb').lower()
        n_strategies = 13  # 12 benchmark strategies + 1 risk-free asset
        
        logger.info(f"Initializing {bandit_type.upper()} bandit with {n_strategies} arms")
        
        # Create bandit instance
        if bandit_type == 'ucb':
            bandit = UCBBandit(n_arms=n_strategies)
        elif bandit_type == 'thompson':
            bandit = ThompsonSamplingBandit(n_arms=n_strategies)
        elif bandit_type == 'exp3':
            bandit = EXP3Bandit(n_arms=n_strategies)
        else:
            logger.warning(f"Unknown bandit type: {bandit_type}, defaulting to UCB")
            bandit = UCBBandit(n_arms=n_strategies)
        
        # Try to restore bandit state from checkpoint if available
        if checkpoint_data and 'bandit_state' in checkpoint_data:
            try:
                logger.info("Restoring bandit state from checkpoint...")
                # Restore bandit state (this depends on your checkpoint structure)
                # You may need to implement a restore method in your bandit classes
                pass  # Placeholder - implement based on your checkpoint format
            except Exception as e:
                logger.warning(f"Failed to restore bandit state: {str(e)}, using fresh bandit")
        
        return bandit
        
    except Exception as e:
        logger.error(f"Failed to initialize bandit: {str(e)}")
        raise


def validate_system(config):
    """
    Validate system configuration and connectivity.
    Useful for smoke testing before live execution.
    """
    logger.info("Starting system validation...")
    
    validation_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    try:
        # Check S3 connectivity
        logger.info("Checking S3 connectivity...")
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        validation_results["checks"]["s3_connectivity"] = "OK"
    except Exception as e:
        validation_results["checks"]["s3_connectivity"] = f"FAILED: {str(e)}"
    
    try:
        # Check config load
        logger.info("Checking config load...")
        config = load_config_from_s3()
        validation_results["checks"]["config_load"] = "OK"
    except Exception as e:
        validation_results["checks"]["config_load"] = f"FAILED: {str(e)}"
    
    try:
        # Check checkpoint load
        logger.info("Checking checkpoint availability...")
        checkpoint = load_latest_checkpoint()
        validation_results["checks"]["checkpoint_available"] = "OK"
        validation_results["last_checkpoint_date"] = checkpoint.get('timestamp')
    except Exception as e:
        validation_results["checks"]["checkpoint_available"] = f"FAILED: {str(e)}"
    
    try:
        # Check data file
        logger.info("Checking market data availability...")
        market_data = fetch_market_data({})
        validation_results["checks"]["market_data_available"] = "OK"
        validation_results["data_rows"] = len(market_data)
        validation_results["data_columns"] = len(market_data.columns)
    except Exception as e:
        validation_results["checks"]["market_data_available"] = f"FAILED: {str(e)}"
    
    try:
        # Check DailyTradingEngine import
        logger.info("Checking DailyTradingEngine import...")
        engine = DailyTradingEngine
        validation_results["checks"]["trading_engine_import"] = "OK"
    except Exception as e:
        validation_results["checks"]["trading_engine_import"] = f"FAILED: {str(e)}"
    
    try:
        # Check bandit imports
        logger.info("Checking bandit imports...")
        ucb = UCBBandit
        thompson = ThompsonSamplingBandit
        exp3 = EXP3Bandit
        validation_results["checks"]["bandit_imports"] = "OK"
    except Exception as e:
        validation_results["checks"]["bandit_imports"] = f"FAILED: {str(e)}"
    
    all_passed = all(v == "OK" for v in validation_results["checks"].values())
    
    return {
        "action": "validate",
        "status": "success",
        "all_checks_passed": all_passed,
        "validation_results": validation_results
    }


def reset_state(config):
    """
    Reset the trading state (use with caution).
    Creates a new checkpoint with zero positions.
    """
    logger.warning("RESETTING TRADING STATE - This action requires manual confirmation")
    
    new_checkpoint = {
        "timestamp": datetime.utcnow().isoformat(),
        "portfolio_value": config.get('trading', {}).get('initial_capital', 100000),
        "positions": {},
        "last_rebalance": datetime.utcnow().isoformat(),
        "action": "reset"
    }
    
    try:
        # Create a fresh bandit for the reset
        bandit = initialize_bandit(config, {})
        save_checkpoint_to_s3(new_checkpoint, bandit)
        logger.info("State reset successful")
        return {
            "action": "reset",
            "status": "success",
            "message": "Trading state reset to clean slate",
            "checkpoint": new_checkpoint
        }
    except Exception as e:
        logger.error(f"State reset failed: {str(e)}")
        raise


def load_config_from_s3():
    """Load trading configuration from S3."""
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=CONFIG_KEY)
        config_content = response['Body'].read().decode('utf-8')
        
        # Parse YAML (assuming config is YAML format)
        import yaml
        config = yaml.safe_load(config_content)
        logger.info(f"Loaded config from s3://{BUCKET_NAME}/{CONFIG_KEY}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        raise


def load_latest_checkpoint():
    """Load the latest checkpoint from S3."""
    try:
        # Try to load latest.json first
        try:
            key = f"{CHECKPOINTS_PREFIX}latest.json"
            obj_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
            checkpoint = json.loads(obj_response['Body'].read().decode('utf-8'))
            logger.info(f"Loaded checkpoint from s3://{BUCKET_NAME}/{key}")
            logger.info(f"Checkpoint timestamp: {checkpoint.get('timestamp')}")
            return checkpoint
        except s3_client.exceptions.NoSuchKey:
            logger.info("latest.json not found, searching for timestamped checkpoints...")
        
        # Fallback: List checkpoints and get the latest
        response = s3_client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=CHECKPOINTS_PREFIX,
            MaxKeys=100
        )
        
        if 'Contents' not in response or len(response['Contents']) == 0:
            logger.warning("No checkpoints found, returning empty checkpoint")
            return {
                "timestamp": None,
                "portfolio_value": 100000,
                "positions": {},
                "last_rebalance": None
            }
        
        # Get latest checkpoint (newest by timestamp)
        latest = max(response['Contents'], key=lambda x: x['LastModified'])
        
        obj_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=latest['Key'])
        checkpoint = json.loads(obj_response['Body'].read().decode('utf-8'))
        
        logger.info(f"Loaded checkpoint from s3://{BUCKET_NAME}/{latest['Key']}")
        logger.info(f"Checkpoint timestamp: {checkpoint.get('timestamp')}")
        
        return checkpoint
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in checkpoint: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to load checkpoint: {str(e)}")
        raise


def fetch_market_data(checkpoint_data):
    """
    Fetch market data from S3.
    Loads the price_data_latest.csv file.
    """
    try:
        # Load the known filename
        key = f"{DATA_PREFIX}price_data_latest.csv"
        
        logger.info(f"Fetching market data from s3://{BUCKET_NAME}/{key}")
        
        obj_response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        
        import pandas as pd
        
        data_bytes = obj_response['Body'].read()
        market_data = pd.read_csv(BytesIO(data_bytes), index_col=0, parse_dates=True)
        
        logger.info(f"Loaded market data: {market_data.shape[0]} rows, {market_data.shape[1]} columns")
        logger.info(f"Date range: {market_data.index[0]} to {market_data.index[-1]}")
        
        return market_data
    except Exception as e:
        logger.error(f"Failed to fetch market data: {str(e)}")
        raise


def save_checkpoint_to_s3(checkpoint_data, bandit=None):
    """
    Save checkpoint to S3 with timestamp-based naming.
    Optionally includes bandit state if provided.
    """
    try:
        # Add bandit state to checkpoint if provided
        if bandit is not None:
            try:
                checkpoint_data['bandit_state'] = {
                    'algorithm': bandit.__class__.__name__,
                    'n_arms': bandit.n_arms,
                    # Add other bandit-specific state here
                    # This depends on your bandit implementation
                }
            except Exception as e:
                logger.warning(f"Failed to save bandit state: {str(e)}")
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        key = f"{CHECKPOINTS_PREFIX}checkpoint_{timestamp}.json"
        
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(checkpoint_data, indent=2, default=str),
            ContentType='application/json',
            Metadata={'timestamp': datetime.utcnow().isoformat()}
        )
        
        # Also save as 'latest.json' for quick access
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{CHECKPOINTS_PREFIX}latest.json",
            Body=json.dumps(checkpoint_data, indent=2, default=str),
            ContentType='application/json',
            Metadata={'timestamp': datetime.utcnow().isoformat()}
        )
        
        logger.info(f"Saved checkpoint to s3://{BUCKET_NAME}/{key}")
        logger.info(f"Updated latest checkpoint: s3://{BUCKET_NAME}/{CHECKPOINTS_PREFIX}latest.json")
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {str(e)}")
        raise


def save_results_to_s3(trading_result, date_str):
    """Save detailed trading results to S3 with date-based organization."""
    try:
        # Create results dictionary from PortfolioResult object
        results_dict = {
            "date": date_str,
            "timestamp": datetime.utcnow().isoformat(),
            "summary_metrics": trading_result.summary_metrics if hasattr(trading_result, 'summary_metrics') else {},
            "final_value": trading_result.summary_metrics.get('final_value') if hasattr(trading_result, 'summary_metrics') else None,
            "total_return": trading_result.summary_metrics.get('total_return') if hasattr(trading_result, 'summary_metrics') else None,
            "sharpe_ratio": trading_result.summary_metrics.get('sharpe_ratio') if hasattr(trading_result, 'summary_metrics') else None
        }
        
        key = f"{RESULTS_PREFIX}{date_str}/trading_result.json"
        
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(results_dict, indent=2, default=str),
            ContentType='application/json'
        )
        
        logger.info(f"Saved results to s3://{BUCKET_NAME}/{key}")
    except Exception as e:
        logger.error(f"Failed to save results: {str(e)}")
        raise


def publish_metrics(action, execution_time, status):
    """Publish execution metrics to CloudWatch."""
    try:
        cloudwatch.put_metric_data(
            Namespace='AlgoTradingLambda',
            MetricData=[
                {
                    'MetricName': 'ExecutionTime',
                    'Value': execution_time,
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {'Name': 'Action', 'Value': action},
                        {'Name': 'Status', 'Value': status}
                    ]
                },
                {
                    'MetricName': 'ExecutionCount',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Action', 'Value': action},
                        {'Name': 'Status', 'Value': status}
                    ]
                }
            ]
        )
        logger.info(f"Published metrics: action={action}, time={execution_time}s, status={status}")
    except Exception as e:
        logger.error(f"Failed to publish metrics: {str(e)}")
        # Don't raise - metrics failure shouldn't fail the whole execution


def success_response(body, execution_time):
    """Format successful response."""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'success',
            'result': body,
            'executionTime': f"{execution_time:.2f}s",
            'timestamp': datetime.utcnow().isoformat()
        }, default=str),
        'headers': {
            'Content-Type': 'application/json'
        }
    }


def error_response(message, status_code, traceback_str=None):
    """Format error response."""
    error_body = {
        'status': 'error',
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if traceback_str:
        error_body['traceback'] = traceback_str
    
    return {
        'statusCode': status_code,
        'body': json.dumps(error_body, default=str),
        'headers': {
            'Content-Type': 'application/json'
        }
    }