"""
Demo: Benchmark Strategies Comparison
========================================

This demo compares 12 key portfolio strategies with daily rebalancing
over a 10-year period (2014-2024).

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

Configuration:
- Period: 2014-01-01 to 2024-01-01 (10 years)
- Rebalancing: Daily
- Initial capital: $100,000
- Transaction costs: 0.1%
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Import project modules
from src.data_loader import load_data
from src.portfolio_engine import PortfolioEngine
from src.strategy import Strategy
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


def run_benchmark_comparison():
    """Run comprehensive benchmark comparison of 12 strategies."""
    
    print("=" * 80)
    print("BENCHMARK STRATEGIES COMPARISON")
    print("=" * 80)
    print("Period: 2014-01-01 to 2024-01-01 (10 years)")
    print("Rebalancing: Daily")
    print("Initial Capital: $100,000")
    print("Transaction Costs: 0.1%")
    print("=" * 80)
    print()
    
    # ========================================================================
    # 1. LOAD DATA
    # ========================================================================
    print("[1/4] Loading data...")
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM']
    start_date = '2014-01-01'
    end_date = '2024-01-01'
    
    # load_data returns (full_data, price_data) tuple
    _, prices = load_data(tickers, start_date, end_date)
    print(f"Loaded {len(tickers)} assets from {start_date} to {end_date}")
    print(f"Data shape: {prices.shape}")
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
    print("[3/4] Running backtests with daily rebalancing...")
    print("Note: This may take several minutes due to daily rebalancing over 10 years...")
    print()
    
    results = {}
    
    for i, (name, strat) in enumerate(strategies.items(), 1):
        print(f"  [{i}/{len(strategies)}] Running {name}...", end=' ')
        
        try:
            engine = PortfolioEngine(
                prices=prices,
                initial_capital=100000,
                transaction_cost_bps=10.0,  # 0.1% = 10 bps
                slippage_bps=0.0
            )
            
            result = engine.run_backtest(
                strategy_wrapper=strat,
                rebalance_freq='D',  # Daily rebalancing
                start_date='2014-01-01',
                end_date='2024-01-01'
            )
            results[name] = result
            
            final_value = result.equity_curve.iloc[-1]
            total_return = (final_value / 100000 - 1) * 100
            print(f"[OK] Final Return: {total_return:.2f}%")
            
        except Exception as e:
            print(f"[FAILED] Error: {str(e)}")
    
    print()
    
    # ========================================================================
    # 4. EVALUATE AND COMPARE
    # ========================================================================
    print("[4/4] Evaluating performance...")
    
    # Compute metrics for all strategies
    metrics_list = []
    for name, result in results.items():
        # Use summary_metrics from result object
        metrics = result.summary_metrics.copy()
        metrics['Strategy'] = name
        # Rename keys to match expected format
        if 'annual_return' in metrics:
            metrics['Total Return (%)'] = metrics['annual_return'] * 100
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
    print("PERFORMANCE SUMMARY (Sorted by Sharpe Ratio)")
    print("=" * 80)
    print(metrics_df.to_string())
    print()
    
    # ========================================================================
    # 5. VISUALIZATION
    # ========================================================================
    print("[5/5] Creating visualizations...")
    
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
    
    plt.figure(figsize=(20, 12))
    
    # 1. Equity Curves
    ax1 = plt.subplot(2, 3, 1)
    for name, result in results.items():
        equity = result.equity_curve
        ax1.plot(equity.index, equity.values, label=name, alpha=0.7, linewidth=1.5)
    ax1.set_title('Equity Curves (10-Year Horizon)', fontsize=14, fontweight='bold')
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
    
    # 4. Total Returns Comparison
    ax4 = plt.subplot(2, 3, 4)
    returns_data = metrics_df['Total Return (%)'].sort_values(ascending=True)
    colors = ['green' if x > 0 else 'red' for x in returns_data.values]
    ax4.barh(range(len(returns_data)), returns_data.values, color=colors, alpha=0.7)
    ax4.set_yticks(range(len(returns_data)))
    ax4.set_yticklabels(returns_data.index, fontsize=9)
    ax4.set_title('Total Returns (%)', fontsize=14, fontweight='bold')
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
        y = metrics_df.loc[name, 'Total Return (%)']
        ax6.scatter(x, y, s=100, alpha=0.7, label=name)
    ax6.set_title('Risk-Return Profile', fontsize=14, fontweight='bold')
    ax6.set_xlabel('Volatility (%)')
    ax6.set_ylabel('Total Return (%)')
    ax6.legend(loc='best', fontsize=8)
    ax6.grid(True, alpha=0.3)
    
    plt.savefig('visualizations/benchmark_strategies_comparison.png', dpi=150, bbox_inches='tight')
    print("Saved: visualizations/benchmark_strategies_comparison.png")
    
    print()
    print("=" * 80)
    print("BENCHMARK COMPARISON COMPLETE")
    print("=" * 80)
    
    return results, metrics_df


if __name__ == '__main__':
    results, metrics = run_benchmark_comparison()
