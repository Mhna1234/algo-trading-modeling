"""
Demo: Benchmark Strategies Comparison (FAST MODE) - Enhanced
=============================================================

This is an optimized version that runs 3-5x faster by using:
- Weekly rebalancing instead of daily (reduces from 2500 to 520 rebalances)
- Shorter time period option (5 years instead of 10)
- Optimized calculations with caching
- Smart strategy selection (MAX 12 strategies)
- Robust error handling (continues on strategy failures)

CONFIGURATION:
- Maximum 12 strategies (configurable via ENABLED_STRATEGIES)
- Auto-filters and validates strategy names
- Safe execution with per-strategy error handling
- Detailed progress logging

Fast Mode Configuration:
- Period: 2019-01-01 to 2024-01-01 (5 years) - Change to 10 years if needed
- Rebalancing: WEEKLY (reduces computation by 80%)
- Initial capital: $100,000
- Transaction costs: 0.1%
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time
from datetime import datetime
import logging
from typing import Dict, List, Optional

# Import project modules
from src.data_loader import load_data
from src.portfolio_engine import PortfolioEngine
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategy_wrapper import (
    list_available_strategies,
    EqualWeightStrategy,
    BuyAndHoldStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    InverseVolatilityStrategy,
    GlobalMinimumVarianceStrategy,
    CVaRMinimizationStrategy,
    MaximumDiversificationStrategy,
    TimeSeriesMomentumStrategy,
    MovingAverageCrossoverStrategy,
    MarkowitzMVOStrategy,
    LinearRegressionStrategy,
    RegimeSwitchingStrategy,
    MLRandomForestStrategy,
    MLGradientBoostingStrategy,
    ARMAForecastStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION: SELECT YOUR 12 STRATEGIES
# ============================================================================
# Available strategies: equal_weight, momentum, mean_reversion, inverse_volatility,
# cvar_minimization, gmvp, gmrp, regime_switching, ml_random_forest, 
# ml_gradient_boosting, arma_forecast, arima_garch, linear_regression,
# buy_and_hold, max_diversification, time_series_momentum, ma_crossover, markowitz_mvo

ENABLED_STRATEGIES = [
    'equal_weight',           # 1. Baseline
    'buy_and_hold',          # 2. Passive benchmark
    'momentum',              # 3. Trend following
    'mean_reversion',        # 4. Contrarian
    'inverse_volatility',    # 5. Risk parity style
    'gmvp',                  # 6. Min variance
    'cvar_minimization',     # 7. Tail risk control
    'max_diversification',   # 8. Maximum diversification
    'time_series_momentum',  # 9. Time series momentum
    'ma_crossover',          # 10. Moving average crossover
    'markowitz_mvo',         # 11. Mean-variance optimization
    'linear_regression',     # 12. ML-based forecasting
][:12]  # Enforce maximum 12 strategies


def validate_strategies(strategy_names: List[str]) -> List[str]:
    """
    Validate strategy names against available strategies.
    
    Parameters
    ----------
    strategy_names : List[str]
        List of strategy names to validate
        
    Returns
    -------
    List[str]
        Validated strategy names (invalid ones filtered out)
    """
    available = list(list_available_strategies().keys())
    valid_strategies = []
    
    for name in strategy_names:
        if name in available:
            valid_strategies.append(name)
        else:
            logger.warning(f"Strategy '{name}' not found. Skipping.")
            logger.info(f"Available strategies: {', '.join(available)}")
    
    return valid_strategies


def create_strategy_instances(
    strategy_names: List[str],
    strategy: Strategy,
    optimizer: PortfolioOptimizer
) -> Dict[str, object]:
    """
    Create strategy instances with robust error handling.
    
    Parameters
    ----------
    strategy_names : List[str]
        List of strategy names to instantiate
    strategy : Strategy
        Signal generator
    optimizer : PortfolioOptimizer
        Portfolio optimizer
        
    Returns
    -------
    Dict[str, object]
        Dictionary mapping strategy names to instances
    """
    strategies = {}
    
    # Define strategy configurations
    strategy_configs = {
        'equal_weight': lambda: EqualWeightStrategy(strategy, optimizer),
        'buy_and_hold': lambda: BuyAndHoldStrategy(strategy, optimizer, initial_method='equal'),
        'momentum': lambda: MomentumStrategy(strategy, optimizer, top_k=4, lookback=126),
        'mean_reversion': lambda: MeanReversionStrategy(strategy, optimizer, window=21, top_k=4),
        'inverse_volatility': lambda: InverseVolatilityStrategy(strategy, optimizer, vol_window=63),
        'gmvp': lambda: GlobalMinimumVarianceStrategy(strategy, optimizer, lookback=252),
        'cvar_minimization': lambda: CVaRMinimizationStrategy(strategy, optimizer, lookback=126, alpha=0.95),
        'max_diversification': lambda: MaximumDiversificationStrategy(strategy, optimizer, lookback=252, max_weight=0.4),
        'time_series_momentum': lambda: TimeSeriesMomentumStrategy(strategy, optimizer, lookback=126, long_only=True),
        'ma_crossover': lambda: MovingAverageCrossoverStrategy(strategy, optimizer, fast_window=50, slow_window=200),
        'markowitz_mvo': lambda: MarkowitzMVOStrategy(strategy, optimizer, lookback=252, risk_aversion=1.0),
        'linear_regression': lambda: LinearRegressionStrategy(strategy, optimizer, lookback=252, regularization='ridge'),
        'regime_switching': lambda: RegimeSwitchingStrategy(strategy, optimizer, vol_window=63, vol_threshold=0.2),
        'ml_random_forest': lambda: MLRandomForestStrategy(strategy, optimizer, lookback=252, top_k=4),
        'ml_gradient_boosting': lambda: MLGradientBoostingStrategy(strategy, optimizer, lookback=252, top_k=4),
        'arma_forecast': lambda: ARMAForecastStrategy(strategy, optimizer, lookback=252),
    }
    
    for name in strategy_names:
        try:
            if name in strategy_configs:
                display_name = name.replace('_', ' ').title()
                strategies[display_name] = strategy_configs[name]()
                logger.info(f"✓ Created strategy: {display_name}")
            else:
                logger.warning(f"✗ No configuration found for: {name}")
        except Exception as e:
            logger.error(f"✗ Failed to create strategy '{name}': {e}")
    
    return strategies


def run_benchmark_comparison_fast(use_10_years=False):
    """
    Run fast benchmark comparison of up to 12 strategies.
    
    Parameters
    ----------
    use_10_years : bool, default=False
        If True, use 10-year period (2014-2024)
        If False, use 5-year period (2019-2024) - MUCH FASTER
    """
    
    # Choose time period
    if use_10_years:
        start_date = '2014-01-01'
        period_desc = "10 years"
    else:
        start_date = '2019-01-01'
        period_desc = "5 years"
    
    end_date = '2024-01-01'
    
    print("=" * 80)
    print("BENCHMARK STRATEGIES COMPARISON (FAST MODE - ENHANCED)")
    print("=" * 80)
    print(f"Period: {start_date} to {end_date} ({period_desc})")
    print("Rebalancing: WEEKLY (reduces computation by 80%)")
    print("Initial Capital: $100,000")
    print("Transaction Costs: 0.1%")
    print(f"Maximum Strategies: 12 (currently {len(ENABLED_STRATEGIES)} enabled)")
    print("=" * 80)
    print()
    
    # ========================================================================
    # 1. LOAD DATA
    # ========================================================================
    print("[1/5] Loading data...")
    logger.info("Starting data load")
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM']
    
    try:
        # load_data returns (full_data, price_data) tuple
        _, prices = load_data(tickers, start_date, end_date)
        logger.info(f"Loaded {len(tickers)} assets from {start_date} to {end_date}")
        print(f"Loaded {len(tickers)} assets from {start_date} to {end_date}")
        print(f"Data shape: {prices.shape} ({len(prices)} trading days)")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise
    
    # Estimate time savings
    daily_rebalances = len(prices)
    weekly_rebalances = len(prices) // 5
    time_saved_pct = (1 - weekly_rebalances / daily_rebalances) * 100
    print(f"Weekly rebalancing: ~{weekly_rebalances} rebalances (vs {daily_rebalances} daily)")
    print(f"Estimated speedup: {100/(100-time_saved_pct):.1f}x faster")
    print()
    
    # ========================================================================
    # 2. VALIDATE AND FILTER STRATEGIES
    # ========================================================================
    print("[2/5] Validating and configuring strategies...")
    logger.info("Validating strategy configuration")
    
    # Validate strategy names
    valid_strategy_names = validate_strategies(ENABLED_STRATEGIES)
    
    if len(valid_strategy_names) == 0:
        logger.error("No valid strategies found!")
        raise ValueError("No valid strategies configured")
    
    if len(valid_strategy_names) > 12:
        logger.warning(f"More than 12 strategies ({len(valid_strategy_names)}). Limiting to first 12.")
        valid_strategy_names = valid_strategy_names[:12]
    
    print(f"Validated {len(valid_strategy_names)} strategies:")
    for i, name in enumerate(valid_strategy_names, 1):
        print(f"  {i}. {name.replace('_', ' ').title()}")
    print()
    
    # ========================================================================
    # 3. CREATE STRATEGY INSTANCES
    # ========================================================================
    print("[3/5] Creating strategy instances...")
    logger.info("Instantiating strategies")
    
    try:
        signal_generator = Strategy(prices)
        optimizer = PortfolioOptimizer()
        
        strategies = create_strategy_instances(
            valid_strategy_names,
            signal_generator,
            optimizer
        )
        
        print(f"Successfully created {len(strategies)} strategy instances")
        print()
    except Exception as e:
        logger.error(f"Failed to create strategies: {e}")
        raise
    
    # ========================================================================
    # 4. RUN BACKTESTS WITH ROBUST ERROR HANDLING
    # ========================================================================
    print("[4/5] Running backtests with WEEKLY rebalancing...")
    print(f"Expected time: {len(strategies) * weekly_rebalances / 100:.0f}-{len(strategies) * weekly_rebalances / 50:.0f} seconds")
    print()
    
    results = {}
    failed_strategies = []
    total_start = time.time()
    
    for i, (name, strat) in enumerate(strategies.items(), 1):
        start_time = time.time()
        print(f"  [{i}/{len(strategies)}] Running {name}...", end=' ', flush=True)
        logger.info(f"Starting backtest for {name}")
        
        try:
            engine = PortfolioEngine(
                prices=prices,
                initial_capital=100000,
                transaction_cost_bps=10.0,  # 0.1% = 10 bps
                slippage_bps=0.0
            )
            
            result = engine.run_backtest(
                strategy_wrapper=strat,
                rebalance_freq='W',  # WEEKLY rebalancing for speed
                start_date=start_date,
                end_date=end_date
            )
            results[name] = result
            
            final_value = result.equity_curve.iloc[-1]
            total_return = (final_value / 100000 - 1) * 100
            elapsed = time.time() - start_time
            print(f"✓ Return: {total_return:+.2f}% (Time: {elapsed:.1f}s)")
            logger.info(f"✓ {name} completed successfully: {total_return:+.2f}%")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"✗ FAILED: {str(e)[:50]}... (Time: {elapsed:.1f}s)")
            logger.error(f"✗ {name} failed: {e}")
            failed_strategies.append(name)
    
    total_elapsed = time.time() - total_start
    print()
    print(f"Total execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
    print(f"Successful strategies: {len(results)}/{len(strategies)}")
    if failed_strategies:
        print(f"Failed strategies: {', '.join(failed_strategies)}")
    print()
    
    # Check if we have any results
    if len(results) == 0:
        logger.error("All strategies failed! Cannot generate report.")
        print("ERROR: All strategies failed. Please check the logs.")
        return None, None
    
    # ========================================================================
    # 5. EVALUATE AND COMPARE
    # ========================================================================
    print("[5/5] Evaluating performance...")
    logger.info("Computing performance metrics")
    
    # Compute metrics for all successful strategies
    metrics_list = []
    for name, result in results.items():
        try:
            metrics = result.summary_metrics.copy()
            metrics['Strategy'] = name
            if 'annual_return' in metrics:
                metrics['Annual Return (%)'] = metrics['annual_return'] * 100
            if 'annual_volatility' in metrics:
                metrics['Volatility (%)'] = metrics['annual_volatility'] * 100
            if 'sharpe_ratio' in metrics:
                metrics['Sharpe Ratio'] = metrics['sharpe_ratio']
            if 'max_drawdown' in metrics:
                metrics['Max Drawdown (%)'] = metrics['max_drawdown'] * 100
            metrics_list.append(metrics)
        except Exception as e:
            logger.warning(f"Failed to extract metrics for {name}: {e}")
    
    metrics_df = pd.DataFrame(metrics_list)
    metrics_df = metrics_df.set_index('Strategy')
    
    # Sort by Sharpe Ratio
    if 'Sharpe Ratio' in metrics_df.columns:
        metrics_df = metrics_df.sort_values('Sharpe Ratio', ascending=False)
    
    print()
    print("=" * 80)
    print(f"PERFORMANCE SUMMARY ({period_desc.upper()}, WEEKLY REBALANCING)")
    print("=" * 80)
    display_cols = ['Annual Return (%)', 'Volatility (%)', 'Sharpe Ratio', 'Max Drawdown (%)']
    display_cols = [col for col in display_cols if col in metrics_df.columns]
    print(metrics_df[display_cols].to_string())
    print()
    
    # ========================================================================
    # 6. VISUALIZATION
    # ========================================================================
    print("Creating visualizations...")
    logger.info("Generating plots")
    
    try:
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
        fig = plt.figure(figsize=(20, 12))
        
        # 1. Equity Curves
        ax1 = plt.subplot(2, 3, 1)
        for name, result in results.items():
            equity = result.equity_curve
            ax1.plot(equity.index, equity.values, label=name, alpha=0.7, linewidth=1.5)
        ax1.set_title(f'Equity Curves ({period_desc.title()})', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Portfolio Value ($)')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 2. Cumulative Returns
        ax2 = plt.subplot(2, 3, 2)
        for name, result in results.items():
            equity = result.equity_curve
            cum_returns = (equity / 100000 - 1) * 100
            ax2.plot(cum_returns.index, cum_returns.values, label=name, alpha=0.7, linewidth=1.5)
        ax2.set_title('Cumulative Returns (%)', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Return (%)')
        ax2.legend(loc='upper left', fontsize=8)
        ax2.grid(True, alpha=0.3)
        
        # 3. Sharpe Ratio Comparison
        if 'Sharpe Ratio' in metrics_df.columns:
            ax3 = plt.subplot(2, 3, 3)
            sharpe_data = metrics_df['Sharpe Ratio'].sort_values(ascending=True)
            colors = ['green' if x > 0 else 'red' for x in sharpe_data.values]
            ax3.barh(range(len(sharpe_data)), sharpe_data.values, color=colors, alpha=0.7)
            ax3.set_yticks(range(len(sharpe_data)))
            ax3.set_yticklabels(sharpe_data.index, fontsize=9)
            ax3.set_title('Sharpe Ratio Comparison', fontsize=14, fontweight='bold')
            ax3.set_xlabel('Sharpe Ratio')
            ax3.axvline(0, color='black', linestyle='--', linewidth=0.8)
            ax3.grid(True, alpha=0.3)
        
        # 4. Annual Returns Comparison
        if 'Annual Return (%)' in metrics_df.columns:
            ax4 = plt.subplot(2, 3, 4)
            returns_data = metrics_df['Annual Return (%)'].sort_values(ascending=True)
            colors = ['green' if x > 0 else 'red' for x in returns_data.values]
            ax4.barh(range(len(returns_data)), returns_data.values, color=colors, alpha=0.7)
            ax4.set_yticks(range(len(returns_data)))
            ax4.set_yticklabels(returns_data.index, fontsize=9)
            ax4.set_title('Annual Returns (%)', fontsize=14, fontweight='bold')
            ax4.set_xlabel('Return (%)')
            ax4.grid(True, alpha=0.3)
        
        # 5. Max Drawdown Comparison
        if 'Max Drawdown (%)' in metrics_df.columns:
            ax5 = plt.subplot(2, 3, 5)
            dd_data = metrics_df['Max Drawdown (%)'].sort_values(ascending=False)
            ax5.barh(range(len(dd_data)), dd_data.values, color='red', alpha=0.7)
            ax5.set_yticks(range(len(dd_data)))
            ax5.set_yticklabels(dd_data.index, fontsize=9)
            ax5.set_title('Maximum Drawdown (%)', fontsize=14, fontweight='bold')
            ax5.set_xlabel('Drawdown (%)')
            ax5.grid(True, alpha=0.3)
        
        # 6. Risk-Return Scatter
        if 'Volatility (%)' in metrics_df.columns and 'Annual Return (%)' in metrics_df.columns:
            ax6 = plt.subplot(2, 3, 6)
            for name in metrics_df.index:
                x = metrics_df.loc[name, 'Volatility (%)']
                y = metrics_df.loc[name, 'Annual Return (%)']
                ax6.scatter(x, y, s=100, alpha=0.7, label=name)
            ax6.set_title('Risk-Return Profile', fontsize=14, fontweight='bold')
            ax6.set_xlabel('Volatility (%)')
            ax6.set_ylabel('Annual Return (%)')
            ax6.legend(loc='best', fontsize=8)
            ax6.grid(True, alpha=0.3)
        
        plt.suptitle(f'Strategy Comparison - {period_desc.title()} - Weekly Rebalancing (Enhanced)', 
                     fontsize=16, fontweight='bold', y=0.995)
        
        # Ensure visualizations directory exists
        os.makedirs('visualizations', exist_ok=True)
        
        filename = f'visualizations/benchmark_strategies_fast_{period_desc.replace(" ", "")}_enhanced.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✓ Saved visualization: {filename}")
        logger.info(f"Saved visualization: {filename}")
        
        plt.close()
        
    except Exception as e:
        logger.error(f"Failed to create visualizations: {e}")
        print(f"✗ Visualization failed: {e}")
    
    # Save metrics to CSV
    try:
        csv_filename = f'visualizations/benchmark_strategies_fast_{period_desc.replace(" ", "")}_enhanced.csv'
        metrics_df.to_csv(csv_filename)
        print(f"✓ Saved metrics: {csv_filename}")
        logger.info(f"Saved metrics: {csv_filename}")
    except Exception as e:
        logger.error(f"Failed to save CSV: {e}")
        print(f"✗ CSV save failed: {e}")
    
    print()
    print("=" * 80)
    print("BENCHMARK COMPARISON COMPLETE (FAST MODE - ENHANCED)")
    print("=" * 80)
    print()
    print("PERFORMANCE TIPS:")
    print("- Weekly rebalancing is 5x faster than daily")
    print("- 5-year period is 2x faster than 10-year")
    print("- Combined: 10x speedup!")
    print()
    print("CONFIGURATION:")
    print("- Edit ENABLED_STRATEGIES list to change which strategies run")
    print("- Maximum 12 strategies enforced automatically")
    print("- Failed strategies are skipped gracefully")
    print()
    print("To run 10-year test: run_benchmark_comparison_fast(use_10_years=True)")
    print()
    
    return results, metrics_df


if __name__ == '__main__':
    # Default: Fast 5-year test
    logger.info("Starting benchmark comparison (fast mode)")
    try:
        results, metrics = run_benchmark_comparison_fast(use_10_years=False)
        logger.info("Benchmark comparison completed successfully")
    except Exception as e:
        logger.error(f"Benchmark comparison failed: {e}")
        raise
    
    # For 10-year test, uncomment:
    # results, metrics = run_benchmark_comparison_fast(use_10_years=True)
