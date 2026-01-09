"""
AWS Lambda Handler for Daily Benchmark Strategy Calculations

This Lambda function runs daily to:
1. Fetch latest market data from S3 (data-retrieval bucket)
2. Calculate portfolio weights for 15 benchmark strategies
3. Run backtests with 3 rebalancing frequencies (Daily, Weekly, Monthly)
4. Output results to S3 (benchmarks-modelling-output bucket)

Architecture:
- Numpy-only implementations (no scipy/cvxpy)
- ~150MB deployment package
- 15-minute timeout (actual runtime ~3-5 minutes)
- 3GB memory allocation

Author: Algo Trading Team
Date: January 2026
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import traceback

import boto3
import pandas as pd
import numpy as np

# Lambda-compatible benchmark imports
from src.strategies.benchmarks import (
    BuyAndHoldBenchmark,
    EqualWeightBenchmark,
    QuintileFactorBenchmark,
    QuintileLowVolatilityBenchmark,
    MeanReversionBenchmark,
    GlobalMinVarianceBenchmark,
    InverseVolatilityBenchmark,
    InverseVarianceBenchmark,
    RiskParityBenchmark,
    MaxDecorrelationBenchmark,
    MostDiversifiedBenchmark,
    SharpeMaximizationBenchmark,
    CVaRMinimizationBenchmark,
    TopKReturnBenchmark,
    TopKSharpeBenchmark,
)
from src.signal_generator import Strategy
from src.portfolio_engine import PortfolioEngine
from src.data_retrieval import load_preprocessed_data

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# S3 Configuration
DATA_BUCKET = os.environ.get('DATA_BUCKET', 'data-retrieval')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'benchmarks-modelling-output')
TICKERS_FILE = os.environ.get('TICKERS_FILE', 'sp500_tickers.txt')

# Strategy Configuration
REBALANCE_FREQUENCIES = ['D', 'W', 'M']  # Daily, Weekly, Monthly
INITIAL_CAPITAL = 1_000_000


def get_benchmark_strategies(signal_generator: Strategy) -> Dict[str, Any]:
    """
    Initialize all 15 Lambda-compatible benchmark strategies.

    Returns
    -------
    dict
        Mapping of strategy names to instances
    """
    return {
        # Passive
        'buy_and_hold': BuyAndHoldBenchmark(signal_generator),

        # Heuristic
        'equal_weight': EqualWeightBenchmark(signal_generator),
        'top_k_return': TopKReturnBenchmark(signal_generator, top_k=10),
        'top_k_sharpe': TopKSharpeBenchmark(signal_generator, top_k=10),
        'quintile_momentum': QuintileFactorBenchmark(
            signal_generator, lookback=126, target_quintile=5
        ),
        'quintile_low_vol': QuintileLowVolatilityBenchmark(
            signal_generator, lookback=126, target_quintile=1
        ),

        # Factor/Signal
        'mean_reversion': MeanReversionBenchmark(
            signal_generator, lookback=20, z_score_threshold=0.0
        ),

        # Risk-Based
        'global_min_variance': GlobalMinVarianceBenchmark(signal_generator),
        'inverse_volatility': InverseVolatilityBenchmark(signal_generator),
        'inverse_variance': InverseVarianceBenchmark(signal_generator),
        'risk_parity': RiskParityBenchmark(signal_generator, max_iter=1000),
        'max_decorrelation': MaxDecorrelationBenchmark(signal_generator),
        'most_diversified': MostDiversifiedBenchmark(signal_generator),

        # Optimization
        'sharpe_maximization': SharpeMaximizationBenchmark(
            signal_generator, risk_free_rate=0.02
        ),
        'cvar_minimization': CVaRMinimizationBenchmark(
            signal_generator, alpha=0.05, max_iter=100
        ),
    }


def load_market_data() -> pd.DataFrame:
    """
    Load latest market data from S3 data-retrieval bucket.

    Returns
    -------
    pd.DataFrame
        Price data with DatetimeIndex
    """
    logger.info(f"Loading data from S3 bucket: {DATA_BUCKET}")

    try:
        # Use existing data_retrieval module
        prices = load_preprocessed_data(
            data_dir='/tmp/market_data',  # Lambda tmp directory
            update_if_available=True
        )

        logger.info(f"Loaded data: {len(prices)} days, {len(prices.columns)} assets")
        logger.info(f"Date range: {prices.index[0]} to {prices.index[-1]}")

        return prices

    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
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

        # Run backtest
        result = portfolio.run_backtest(
            strategy_wrapper=strategy,
            soft_rebalance=True,
            drift_threshold=0.05
        )

        # Extract key metrics
        metrics = {
            'total_return': float(result.total_return),
            'cagr': float(result.cagr),
            'volatility': float(result.volatility),
            'sharpe_ratio': float(result.sharpe_ratio),
            'sortino_ratio': float(result.sortino_ratio),
            'max_drawdown': float(result.max_drawdown),
            'calmar_ratio': float(result.calmar_ratio),
            'win_rate': float(result.win_rate),
            'avg_turnover': float(result.avg_turnover),
        }

        # Extract time series (convert to dict for JSON serialization)
        time_series = {
            'dates': result.equity_curve.index.strftime('%Y-%m-%d').tolist(),
            'equity': result.equity_curve.values.tolist(),
            'returns': result.returns.values.tolist(),
            'drawdowns': result.drawdown_curve.values.tolist(),
        }

        # Extract weights history (last 100 rebalances for dashboard)
        weights_history = result.weights_history.tail(100)
        weights_data = {
            'dates': weights_history.index.strftime('%Y-%m-%d').tolist(),
            'weights': weights_history.to_dict(orient='list')
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


def save_results_to_s3(results: List[Dict], execution_date: str):
    """
    Save benchmark results to S3 output bucket.

    Organizes results by strategy and rebalancing frequency for dashboard access.

    Parameters
    ----------
    results : list of dict
        Backtest results for all strategies
    execution_date : str
        Date string (YYYY-MM-DD) for versioning
    """
    s3_client = boto3.client('s3')

    logger.info(f"Saving results to S3 bucket: {OUTPUT_BUCKET}")

    # Save individual strategy results
    for result in results:
        strategy_name = result['strategy_name']
        rebal_freq = result['rebalance_freq']

        # S3 key structure: {strategy}/{frequency}/{date}.json
        s3_key = f"{strategy_name}/{rebal_freq}/{execution_date}.json"

        try:
            s3_client.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=s3_key,
                Body=json.dumps(result, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Saved: s3://{OUTPUT_BUCKET}/{s3_key}")

        except Exception as e:
            logger.error(f"Error saving {s3_key}: {str(e)}")

    # Save summary file (latest results for all strategies)
    summary = {
        'execution_date': execution_date,
        'execution_timestamp': datetime.utcnow().isoformat(),
        'total_strategies': len(set(r['strategy_name'] for r in results)),
        'rebalance_frequencies': REBALANCE_FREQUENCIES,
        'total_backtests': len(results),
        'successful': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'results': results
    }

    try:
        # Latest summary
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key='latest/summary.json',
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )

        # Dated summary (for history)
        s3_client.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=f'history/{execution_date}/summary.json',
            Body=json.dumps(summary, indent=2),
            ContentType='application/json'
        )

        logger.info("Summary files saved successfully")

    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")


def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Triggered daily by EventBridge rule.

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
    logger.info("=== Starting Daily Benchmark Calculations ===")
    logger.info(f"Event: {json.dumps(event)}")

    execution_date = datetime.utcnow().strftime('%Y-%m-%d')
    start_time = datetime.utcnow()

    try:
        # Step 1: Load market data
        logger.info("Step 1/4: Loading market data from S3...")
        prices = load_market_data()

        # Step 2: Initialize strategies
        logger.info("Step 2/4: Initializing 15 benchmark strategies...")
        signal_generator = Strategy(prices)
        strategies = get_benchmark_strategies(signal_generator)
        logger.info(f"Initialized {len(strategies)} strategies")

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

                # Check remaining time (Lambda 15-minute timeout)
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                remaining = context.get_remaining_time_in_millis() / 1000 if context else 900

                if remaining < 180:  # Less than 3 minutes left
                    logger.warning(f"Approaching timeout. Completed {len(results)}/{total_runs}")
                    break

        # Step 4: Save results to S3
        logger.info("Step 4/4: Saving results to S3...")
        save_results_to_s3(results, execution_date)

        # Summary
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        successful = len([r for r in results if r['status'] == 'success'])
        failed = len([r for r in results if r['status'] == 'error'])

        summary = {
            'statusCode': 200,
            'status': 'success',
            'execution_date': execution_date,
            'duration_seconds': duration,
            'total_backtests': len(results),
            'successful': successful,
            'failed': failed,
            'output_bucket': OUTPUT_BUCKET,
            'message': f'Completed {successful}/{len(results)} benchmark calculations'
        }

        logger.info(f"=== Execution Complete ===")
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"Success Rate: {successful}/{len(results)}")

        return summary

    except Exception as e:
        logger.error(f"Fatal error in Lambda handler: {str(e)}")
        logger.error(traceback.format_exc())

        return {
            'statusCode': 500,
            'status': 'error',
            'error_message': str(e),
            'error_traceback': traceback.format_exc()
        }
