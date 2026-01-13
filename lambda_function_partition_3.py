"""
AWS Lambda Handler - Partition 3 of 3
Handles strategies 11-15 (Risk-Based 3-4 + Optimization)

Strategies in this partition:
11. Risk Parity
12. Max Decorrelation
13. Most Diversified
14. Sharpe Maximization
15. CVaR Minimization
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import traceback
from io import StringIO

import boto3
import pandas as pd
import numpy as np

# Data retrieval
from src.data_retrieval import load_date_range, get_latest_available_month

# Lambda-compatible benchmark imports (Partition 3: Risk-Based 3-4 + Optimization)
from src.strategies.benchmarks.risk_parity import RiskParityBenchmark
from src.strategies.benchmarks.max_decorrelation import MaxDecorrelationBenchmark
from src.strategies.benchmarks.most_diversified import MostDiversifiedBenchmark
from src.strategies.benchmarks.sharpe_maximization import SharpeMaximizationBenchmark
from src.strategies.benchmarks.cvar_minimization import CVaRMinimizationBenchmark

# Core imports
from src.signal_generator import Strategy
from src.portfolio_engine import PortfolioEngine

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 Configuration
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'benchmarks-modelling-output')
OUTPUT_PREFIX = os.environ.get('OUTPUT_PREFIX', 'benchmarks-output')

# Data Range Configuration
DATA_YEARS = int(os.environ.get('DATA_YEARS', '5'))

# Strategy Configuration
REBALANCE_FREQUENCIES = ['D', 'W', 'M']  # Daily, Weekly, Monthly
INITIAL_CAPITAL = 1_000_000
PARTITION_ID = 3


def get_benchmark_strategies(signal_generator: Strategy) -> Dict[str, Any]:
    """
    Initialize strategies for Partition 3 (5 strategies).

    Returns
    -------
    dict
        Mapping of strategy names to instances
    """
    return {
        # Risk-Based (3 strategies)
        'risk_parity': RiskParityBenchmark(signal_generator, max_iter=1000),
        'max_decorrelation': MaxDecorrelationBenchmark(signal_generator),
        'most_diversified': MostDiversifiedBenchmark(signal_generator),

        # Optimization (2 strategies)
        'sharpe_maximization': SharpeMaximizationBenchmark(
            signal_generator, risk_free_rate=0.02
        ),
        'cvar_minimization': CVaRMinimizationBenchmark(
            signal_generator, alpha=0.05, max_iter=100
        ),
    }


def load_market_data() -> pd.DataFrame:
    """
    Load latest market data from S3 using data_retrieval module.

    Returns
    -------
    pd.DataFrame
        Price data with DatetimeIndex and stock symbols as columns
    """
    logger.info(f"Loading last {DATA_YEARS} years of data from S3...")

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DATA_YEARS * 365)

    # Load data using data_retrieval module
    prices = load_date_range(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )

    logger.info(f"Raw data loaded: {len(prices)} days, {len(prices.columns)} stocks")
    logger.info(f"Date range: {prices.index.min()} to {prices.index.max()}")

    # Drop stocks with >10% missing data (insufficient history)
    # This preserves more historical data for walk-forward backtesting
    missing_pct_per_stock = prices.isna().sum() / len(prices)
    stocks_with_sufficient_data = missing_pct_per_stock[missing_pct_per_stock < 0.10].index
    prices = prices[stocks_with_sufficient_data]

    # Forward fill missing values (up to 5 days) to handle trading halts
    prices = prices.fillna(method='ffill', limit=5)

    # Drop any rows with remaining NaN values (after forward fill)
    prices = prices.dropna(how='any')

    logger.info(f"Clean data: {len(prices)} days, {len(prices.columns)} stocks")
    logger.info(f"Dropped {len(missing_pct_per_stock) - len(stocks_with_sufficient_data)} stocks with insufficient history")

    return prices


def run_benchmark_backtest(
    strategy_name: str,
    strategy: Any,
    prices: pd.DataFrame,
    rebalance_freq: str
) -> Dict[str, Any]:
    """
    Run backtest for a single strategy and rebalancing frequency.

    Parameters
    ----------
    strategy_name : str
        Name of the strategy
    strategy : BenchmarkStrategy
        Strategy instance
    prices : pd.DataFrame
        Price data
    rebalance_freq : str
        Rebalancing frequency ('D', 'W', 'M')

    Returns
    -------
    dict
        Backtest results with metrics, time series, and weights
    """
    try:
        # Initialize portfolio engine
        portfolio = PortfolioEngine(
            initial_capital=INITIAL_CAPITAL,
            rebalance_freq=rebalance_freq,
            commission_rate=0.001,  # 0.1% commission
            slippage_rate=0.0005    # 0.05% slippage
        )

        # Get date range for backtest
        start_date = prices.index.min()
        end_date = prices.index.max()

        logger.info(f"  Running backtest: {start_date} to {end_date}")

        # Run walk-forward backtest
        result = portfolio.run_backtest(
            strategy_wrapper=strategy,
            start_date=start_date,
            end_date=end_date,
            soft_rebalance=True,
            drift_threshold=0.05,
            backtest_method='walk_forward'  # Walk-forward optimization for robust results
        )

        # Check if backtest returned valid results (None = insufficient data for walk-forward)
        if result is None:
            raise ValueError("Walk-forward backtest returned None - insufficient data (need 30+ months)")

        # Calculate performance metrics
        metrics = portfolio.calculate_performance_metrics(
            result.portfolio_history,
            risk_free_rate=0.02
        )

        # Extract time series data (daily)
        time_series_data = {
            'dates': result.portfolio_history.index.strftime('%Y-%m-%d').tolist(),
            'equity': result.portfolio_history['Equity'].round(2).tolist(),
            'returns': result.portfolio_history['Returns'].round(6).tolist(),
            'drawdowns': (
                (result.portfolio_history['Equity'] / result.portfolio_history['Equity'].cummax() - 1)
                .round(6)
                .tolist()
            )
        }

        # Extract weights history - ONLY on rebalance dates (when trades occurred)
        # Filter to only include dates in trades_history (actual rebalance dates)
        rebalance_dates = result.trades_history.index
        weights_on_rebalance = result.weights_history.loc[rebalance_dates]

        # Last 100 rebalances for dashboard
        weights_on_rebalance = weights_on_rebalance.tail(100)

        # Round weights to 6 decimal places to save memory
        weights_on_rebalance = weights_on_rebalance.round(6)

        weights_data = {
            'dates': weights_on_rebalance.index.strftime('%Y-%m-%d').tolist(),
            'weights': weights_on_rebalance.to_dict(orient='list')
        }

        logger.info(f"  ✓ Success: Sharpe={metrics['sharpe_ratio']:.2f}, Return={metrics['total_return']:.2%}")

        return {
            'status': 'success',
            'strategy_name': strategy_name,
            'rebalance_frequency': rebalance_freq,
            'metrics': metrics,
            'time_series': time_series_data,
            'weights': weights_data,
            'data_info': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'num_days': len(prices),
                'num_stocks': len(prices.columns)
            }
        }

    except Exception as e:
        logger.error(f"  ✗ Error in {strategy_name} ({rebalance_freq}): {str(e)}")
        logger.error(traceback.format_exc())

        return {
            'status': 'error',
            'strategy_name': strategy_name,
            'rebalance_frequency': rebalance_freq,
            'error_message': str(e),
            'error_traceback': traceback.format_exc()
        }


def save_results_to_s3(results: List[Dict[str, Any]], execution_date: str):
    """
    Save backtest results to S3 in organized structure.

    Parameters
    ----------
    results : list
        List of backtest results
    execution_date : str
        Execution date (YYYY-MM-DD format)
    """
    s3_client = boto3.client('s3')

    # Save individual strategy results (JSON + CSV)
    for result in results:
        if result['status'] != 'success':
            continue

        strategy_name = result['strategy_name']
        rebal_freq = result['rebalance_frequency']

        try:
            # Save JSON file (complete results)
            s3_key_json = f"{OUTPUT_PREFIX}/strategies/{strategy_name}/{rebal_freq}/{execution_date}.json"

            s3_client.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=s3_key_json,
                Body=json.dumps(result, indent=2),
                ContentType='application/json'
            )

            logger.info(f"Saved JSON: s3://{OUTPUT_BUCKET}/{s3_key_json}")

        except Exception as e:
            logger.error(f"Error saving results for {strategy_name}/{rebal_freq}: {str(e)}")

        # Save CSV time series (if backtest was successful)
        if result['status'] == 'success' and 'time_series' in result:
            try:
                # Create DataFrame from time series data
                ts = result['time_series']
                df_timeseries = pd.DataFrame({
                    'date': ts['dates'],
                    'equity': ts['equity'],
                    'returns': ts['returns'],
                    'drawdowns': ts['drawdowns']
                })

                # Convert to CSV
                csv_buffer = StringIO()
                df_timeseries.to_csv(csv_buffer, index=False)
                csv_content = csv_buffer.getvalue()

                # Save CSV file
                s3_key_csv = f"{OUTPUT_PREFIX}/timeseries/{strategy_name}/{rebal_freq}/{execution_date}.csv"
                s3_client.put_object(
                    Bucket=OUTPUT_BUCKET,
                    Key=s3_key_csv,
                    Body=csv_content,
                    ContentType='text/csv'
                )

                logger.info(f"Saved CSV: s3://{OUTPUT_BUCKET}/{s3_key_csv}")

            except Exception as e:
                logger.error(f"Error saving CSV for {strategy_name}/{rebal_freq}: {str(e)}")

        # Save weights as CSV (if available)
        if result['status'] == 'success' and 'weights' in result:
            try:
                # Create DataFrame from weights data
                weights = result['weights']
                df_weights = pd.DataFrame(weights['weights'])
                df_weights.insert(0, 'date', weights['dates'])

                # Convert to CSV
                csv_buffer = StringIO()
                df_weights.to_csv(csv_buffer, index=False)
                csv_content = csv_buffer.getvalue()

                # Save weights CSV file
                s3_key_weights = f"{OUTPUT_PREFIX}/weights/{strategy_name}/{rebal_freq}/{execution_date}.csv"
                s3_client.put_object(
                    Bucket=OUTPUT_BUCKET,
                    Key=s3_key_weights,
                    Body=csv_content,
                    ContentType='text/csv'
                )

                logger.info(f"Saved weights CSV: s3://{OUTPUT_BUCKET}/{s3_key_weights}")

            except Exception as e:
                logger.error(f"Error saving weights CSV for {strategy_name}/{rebal_freq}: {str(e)}")

    # Save execution summary for this partition
    summary = {
        'partition_id': PARTITION_ID,
        'execution_date': execution_date,
        'timestamp': datetime.utcnow().isoformat(),
        'total_backtests': len(results),
        'successful': sum(1 for r in results if r['status'] == 'success'),
        'failed': sum(1 for r in results if r['status'] == 'error'),
        'strategies': list({r['strategy_name'] for r in results}),
        'results': [
            {
                'strategy': r['strategy_name'],
                'frequency': r['rebalance_frequency'],
                'status': r['status'],
                'metrics': r.get('metrics', {}) if r['status'] == 'success' else None,
                'error': r.get('error_message') if r['status'] == 'error' else None
            }
            for r in results
        ]
    }

    try:
        # Save to partition-specific summary
        summary_key = f"{OUTPUT_PREFIX}/history/{execution_date}/partition_{PARTITION_ID}_summary.json"
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=summary_key,
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )

        logger.info(f"Saved summary: s3://{OUTPUT_BUCKET}/{summary_key}")

    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")


def lambda_handler(event, context):
    """
    AWS Lambda entry point for Partition 3.

    Parameters
    ----------
    event : dict
        Lambda event (from EventBridge or manual invocation)
    context : LambdaContext
        Lambda runtime context

    Returns
    -------
    dict
        Status and results summary
    """
    logger.info(f"=== Starting Benchmark Calculations - Partition {PARTITION_ID} ===")
    logger.info(f"Event: {json.dumps(event)}")

    execution_date = datetime.utcnow().strftime('%Y-%m-%d')
    start_time = datetime.utcnow()

    try:
        # Step 1: Load market data
        logger.info("Step 1/4: Loading market data from S3...")
        prices = load_market_data()

        # Step 2: Initialize strategies (Partition 3: 5 strategies)
        logger.info(f"Step 2/4: Initializing {5} benchmark strategies...")
        signal_generator = Strategy(prices)
        strategies = get_benchmark_strategies(signal_generator)
        logger.info(f"Initialized strategies: {list(strategies.keys())}")

        # Step 3: Run backtests for all combinations
        logger.info("Step 3/4: Running backtests...")
        results = []

        total_runs = len(strategies) * len(REBALANCE_FREQUENCIES)
        logger.info(f"Total backtests to run: {total_runs}")

        for i, (strategy_name, strategy_instance) in enumerate(strategies.items(), 1):
            for rebal_freq in REBALANCE_FREQUENCIES:
                logger.info(f"Progress: {len(results)+1}/{total_runs} - {strategy_name} ({rebal_freq})")

                result = run_benchmark_backtest(
                    strategy_name=strategy_name,
                    strategy=strategy_instance,
                    prices=prices,
                    rebalance_freq=rebal_freq
                )

                results.append(result)

        # Step 4: Save results to S3
        logger.info("Step 4/4: Saving results to S3...")
        save_results_to_s3(results, execution_date)

        # Calculate execution time
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Success response
        response = {
            'statusCode': 200,
            'partition_id': PARTITION_ID,
            'execution_date': execution_date,
            'duration_seconds': duration,
            'total_backtests': len(results),
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'error'),
            'strategies': list(strategies.keys()),
            'message': f'Partition {PARTITION_ID} completed successfully'
        }

        logger.info(f"=== Partition {PARTITION_ID} Completed ===")
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"Success: {response['successful']}/{response['total_backtests']}")

        return response

    except Exception as e:
        logger.error(f"Fatal error in partition {PARTITION_ID}: {str(e)}")
        logger.error(traceback.format_exc())

        duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            'statusCode': 500,
            'partition_id': PARTITION_ID,
            'execution_date': execution_date,
            'duration_seconds': duration,
            'error_message': str(e),
            'error_traceback': traceback.format_exc()
        }
