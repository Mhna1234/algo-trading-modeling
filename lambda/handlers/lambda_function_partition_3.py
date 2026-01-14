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

    Fetches OHLCV data from S3 (data-retrieval-output bucket) and transforms
    it into a price matrix suitable for backtesting.

    Returns
    -------
    pd.DataFrame
        Price data with DatetimeIndex (rows = dates, columns = tickers)
    """
    logger.info("Loading market data from S3 (data-retrieval-output bucket)...")

    try:
        # Get the latest available month in S3
        latest_year, latest_month = get_latest_available_month()
        logger.info(f"Latest available data: {latest_year:04d}-{latest_month:02d}")

        # Calculate start date (DATA_YEARS years back from latest)
        start_year = latest_year - DATA_YEARS
        start_month = latest_month

        logger.info(f"Loading data range: {start_year:04d}-{start_month:02d} to {latest_year:04d}-{latest_month:02d}")

        # Load OHLCV data from S3 using data_retrieval module
        # Returns DataFrame with columns: symbol, date, open, high, low, close, volume
        ohlcv_data = load_date_range(
            start_year=start_year,
            start_month=start_month,
            end_year=latest_year,
            end_month=latest_month
        )

        logger.info(f"Loaded {len(ohlcv_data)} rows of OHLCV data")

        # Transform to price matrix (rows = dates, columns = tickers)
        # Use adjusted close prices for backtesting
        prices = ohlcv_data.pivot(index='date', columns='symbol', values='close')

        # Ensure datetime index
        if not isinstance(prices.index, pd.DatetimeIndex):
            prices.index = pd.to_datetime(prices.index)

        # Sort by date
        prices = prices.sort_index()

        # Drop any columns with all NaN values (delisted stocks)
        prices = prices.dropna(axis=1, how='all')

        # Drop stocks with >10% missing data (insufficient history)
        # This preserves more historical data for walk-forward backtesting
        missing_pct_per_stock = prices.isna().sum() / len(prices)
        stocks_with_sufficient_data = missing_pct_per_stock[missing_pct_per_stock < 0.10].index
        prices = prices[stocks_with_sufficient_data]

        # Forward fill missing values (up to 5 days) to handle trading halts
        prices = prices.fillna(method='ffill', limit=5)

        # Drop any rows with remaining NaN values (after forward fill)
        prices = prices.dropna(how='any')

        logger.info(f"Processed price matrix: {len(prices)} days, {len(prices.columns)} assets")
        logger.info(f"Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
        logger.info(f"Sample tickers: {list(prices.columns[:5])}")

        return prices

    except Exception as e:
        logger.error(f"Failed to load market data: {e}")
        raise


def run_benchmark_backtest(
    strategy_name: str,
    strategy: Any,
    prices: pd.DataFrame,
    rebalance_freq: str
) -> Dict[str, Any]:
    """
    Run backtest for a single benchmark strategy.

    Parameters
    ----------
    strategy_name : str
        Strategy identifier
    strategy : BaseStrategyWrapper
        Strategy instance
    prices : pd.DataFrame
        Market price data
    rebalance_freq : str
        'D', 'W', or 'M'

    Returns
    -------
    dict
        Backtest results including metrics and time series
    """
    logger.info(f"Running {strategy_name} with {rebalance_freq} rebalancing...")

    try:
        # Initialize portfolio engine
        portfolio = PortfolioEngine(
            prices=prices,
            initial_capital=INITIAL_CAPITAL,
            transaction_cost_bps=10,  # 0.1% commission
            rebalance_freq=rebalance_freq
        )

        # Run backtest (use all available data)
        start_date = prices.index[0].strftime('%Y-%m-%d')
        end_date = prices.index[-1].strftime('%Y-%m-%d')

        result = portfolio.run_backtest(
            strategy_wrapper=strategy,
            start_date=start_date,
            end_date=end_date,
            soft_rebalance=True,
            drift_threshold=0.05,
            backtest_method='walk_forward'  # Walk-forward optimization for robust results
        )

        # Check if backtest returned valid results
        if result is None:
            raise ValueError("Walk-forward backtest returned None - insufficient data (need 30+ months)")

        # Extract key metrics from summary_metrics dict
        metrics = {
            'total_return': float(result.summary_metrics.get('total_return', 0.0)),
            'cagr': float(result.summary_metrics.get('annualized_return', 0.0)),
            'volatility': float(result.summary_metrics.get('volatility', 0.0)),
            'sharpe_ratio': float(result.summary_metrics.get('sharpe_ratio', 0.0)),
            'sortino_ratio': float(result.summary_metrics.get('sortino_ratio', 0.0)),
            'max_drawdown': float(result.summary_metrics.get('max_drawdown', 0.0)),
            'calmar_ratio': float(result.summary_metrics.get('calmar_ratio', 0.0)),
            'win_rate': float(result.summary_metrics.get('win_rate', 0.0)),
            'avg_turnover': float(result.summary_metrics.get('avg_turnover', 0.0)),
        }

        # Extract time series (convert to dict for JSON serialization)
        time_series = {
            'dates': result.equity_curve.index.strftime('%Y-%m-%d').tolist(),
            'equity': result.equity_curve.values.tolist(),
            'returns': result.returns_series.values.tolist(),
            'drawdowns': result.drawdown_series.values.tolist(),
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

        return {
            'strategy_name': strategy_name,
            'rebalance_freq': rebalance_freq,
            'status': 'success',
            'metrics': metrics,
            'time_series': time_series,
            'weights': weights_data,
            'backtest_period': {
                'start': str(result.equity_curve.index[0].date()),
                'end': str(result.equity_curve.index[-1].date()),
                'days': len(result.equity_curve)
            }
        }

    except Exception as e:
        logger.error(f"Error in {strategy_name} backtest: {str(e)}")
        logger.error(traceback.format_exc())

        return {
            'strategy_name': strategy_name,
            'rebalance_freq': rebalance_freq,
            'status': 'error',
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
        rebal_freq = result['rebalance_freq']

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
                'frequency': r['rebalance_freq'],
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
