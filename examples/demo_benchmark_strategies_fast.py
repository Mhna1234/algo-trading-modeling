"""
Demo: Benchmark Strategies Comparison (FAST MODE)
===================================================

This is an optimized version that runs 3-5x faster by using:
- Weekly rebalancing instead of daily (reduces from 2500 to 520 rebalances)
- Shorter time period option (5 years instead of 10)
- Optimized calculations with caching

Selected Strategies:
1. Equal Weight (Baseline)
2. Buy & Hold (Passive Benchmark)
3. Momentum (Cross-sectional)
4. Mean Reversion
5. Inverse Volatility
6. Global Minimum Variance Portfolio (GMVP)
7. CVaR Minimization
8. Maximum Diversification
9. Time-Series Momentum
10. Moving Average Crossover
11. Markowitz Mean-Variance Optimization
12. Linear Regression

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

# Import project modules
from src.data_loader import load_data
from src.portfolio_engine import PortfolioEngine
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategy_wrapper import (
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
    LinearRegressionStrategy
)


def run_benchmark_comparison_fast(use_10_years=False):
    """Run fast benchmark comparison of 12 strategies.
    
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
    print("BENCHMARK STRATEGIES COMPARISON (FAST MODE)")
    print("=" * 80)
    print(f"Period: {start_date} to {end_date} ({period_desc})")
    print("Rebalancing: WEEKLY (reduces computation by 80%)")
    print("Initial Capital: $100,000")
    print("Transaction Costs: 0.1%")
    print("=" * 80)
    print()
    
    # ========================================================================
    # 1. LOAD DATA
    # ========================================================================
    print("[1/4] Loading data...")
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM']
    
    # load_data returns (full_data, price_data) tuple
    _, prices = load_data(tickers, start_date, end_date)
    print(f"Loaded {len(tickers)} assets from {start_date} to {end_date}")
    print(f"Data shape: {prices.shape} ({len(prices)} trading days)")
    
    # Estimate time savings
    daily_rebalances = len(prices)
    weekly_rebalances = len(prices) // 5
    time_saved_pct = (1 - weekly_rebalances / daily_rebalances) * 100
    print(f"Weekly rebalancing: ~{weekly_rebalances} rebalances (vs {daily_rebalances} daily)")
    print(f"Estimated speedup: {100/time_saved_pct:.1f}x faster")
    print()
    
    # ========================================================================
    # 2. DEFINE STRATEGIES
    # ========================================================================
    print("[2/4] Setting up strategies...")
    
    strategy = Strategy(prices)
    optimizer = PortfolioOptimizer()
    
    strategies = {
        'Equal Weight': EqualWeightStrategy(strategy, optimizer),
        'Buy & Hold': BuyAndHoldStrategy(strategy, optimizer, initial_method='equal'),
        'Momentum': MomentumStrategy(strategy, optimizer, top_k=4, lookback=126),
        'Mean Reversion': MeanReversionStrategy(strategy, optimizer, window=21, top_k=4),
        'Inverse Volatility': InverseVolatilityStrategy(strategy, optimizer, vol_window=63),
        'GMVP': GlobalMinimumVarianceStrategy(strategy, optimizer, lookback=252),
        'CVaR Minimization': CVaRMinimizationStrategy(strategy, optimizer, lookback=126, alpha=0.95),
        'Max Diversification': MaximumDiversificationStrategy(strategy, optimizer, lookback=252, max_weight=0.4),
        'Time-Series Momentum': TimeSeriesMomentumStrategy(strategy, optimizer, lookback=126, long_only=True),
        'MA Crossover': MovingAverageCrossoverStrategy(strategy, optimizer, fast_window=50, slow_window=200),
        'Markowitz MVO': MarkowitzMVOStrategy(strategy, optimizer, lookback=252, risk_aversion=1.0),
        'Linear Regression': LinearRegressionStrategy(strategy, optimizer, lookback=252, regularization='ridge')
    }
    
    print(f"Configured {len(strategies)} strategies")
    print()
    
    # ========================================================================
    # 3. RUN BACKTESTS
    # ========================================================================
    print("[3/4] Running backtests with WEEKLY rebalancing...")
    print(f"Expected time: {len(strategies) * weekly_rebalances / 100:.0f}-{len(strategies) * weekly_rebalances / 50:.0f} seconds")
    print()
    
    results = {}
    total_start = time.time()
    
    for i, (name, strat) in enumerate(strategies.items(), 1):
        start_time = time.time()
        print(f"  [{i}/{len(strategies)}] Running {name}...", end=' ', flush=True)
        
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
            print(f"[OK] Return: {total_return:.2f}% (Time: {elapsed:.1f}s)")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[FAILED] Error: {str(e)} (Time: {elapsed:.1f}s)")
    
    total_elapsed = time.time() - total_start
    print()
    print(f"Total execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
    print()
    
    # ========================================================================
    # 4. EVALUATE AND COMPARE
    # ========================================================================
    print("[4/4] Evaluating performance...")
    
    # Compute metrics for all strategies
    metrics_list = []
    for name, result in results.items():
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
    
    metrics_df = pd.DataFrame(metrics_list)
    metrics_df = metrics_df.set_index('Strategy')
    
    # Sort by Sharpe Ratio
    metrics_df = metrics_df.sort_values('Sharpe Ratio', ascending=False)
    
    print()
    print("=" * 80)
    print(f"PERFORMANCE SUMMARY ({period_desc.upper()}, WEEKLY REBALANCING)")
    print("=" * 80)
    print(metrics_df[['Annual Return (%)', 'Volatility (%)', 'Sharpe Ratio', 'Max Drawdown (%)']].to_string())
    print()
    
    # ========================================================================
    # 5. VISUALIZATION
    # ========================================================================
    print("[5/5] Creating visualizations...")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
    
    plt.figure(figsize=(20, 12))
    
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
    ax5 = plt.subplot(2, 3, 5)
    dd_data = metrics_df['Max Drawdown (%)'].sort_values(ascending=False)
    ax5.barh(range(len(dd_data)), dd_data.values, color='red', alpha=0.7)
    ax5.set_yticks(range(len(dd_data)))
    ax5.set_yticklabels(dd_data.index, fontsize=9)
    ax5.set_title('Maximum Drawdown (%)', fontsize=14, fontweight='bold')
    ax5.set_xlabel('Drawdown (%)')
    ax5.grid(True, alpha=0.3)
    
    # 6. Risk-Return Scatter
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
    
    plt.suptitle(f'Strategy Comparison - {period_desc.title()} - Weekly Rebalancing', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    filename = f'visualizations/benchmark_strategies_fast_{period_desc.replace(" ", "")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"Saved: {filename}")
    
    # Save metrics to CSV
    csv_filename = f'visualizations/benchmark_strategies_fast_{period_desc.replace(" ", "")}.csv'
    metrics_df.to_csv(csv_filename)
    print(f"Saved: {csv_filename}")
    
    print()
    print("=" * 80)
    print("BENCHMARK COMPARISON COMPLETE (FAST MODE)")
    print("=" * 80)
    print()
    print("PERFORMANCE TIPS:")
    print("- Weekly rebalancing is 5x faster than daily")
    print("- 5-year period is 2x faster than 10-year")
    print("- Combined: 10x speedup!")
    print()
    print("To run 10-year test: run_benchmark_comparison_fast(use_10_years=True)")
    print()
    
    return results, metrics_df


if __name__ == '__main__':
    # Default: Fast 5-year test
    results, metrics = run_benchmark_comparison_fast(use_10_years=False)
    
    # For 10-year test, uncomment:
    # results, metrics = run_benchmark_comparison_fast(use_10_years=True)
