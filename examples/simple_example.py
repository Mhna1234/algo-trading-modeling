"""
Simple Example - Getting Started with Portfolio Engine

This is a quick-start example showing the basic usage of the
Portfolio Engine with a momentum strategy.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import MomentumStrategy
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

print("\n" + "="*60)
print("PORTFOLIO ENGINE - SIMPLE EXAMPLE")
print("="*60 + "\n")

# Step 1: Create synthetic price data
print("Step 1: Creating synthetic price data...")
dates = pd.bdate_range('2020-01-01', '2023-12-31')
n_assets = 10
tickers = [f'STOCK_{i+1}' for i in range(n_assets)]

np.random.seed(42)
returns = pd.DataFrame(
    np.random.normal(0.0005, 0.02, (len(dates), n_assets)),
    index=dates,
    columns=tickers
)
prices = 100 * (1 + returns).cumprod()

print(f"[OK] Created {n_assets} assets with {len(dates)} days of data\n")

# Step 2: Initialize strategy and optimizer
print("Step 2: Initializing strategy and optimizer...")
strategy = Strategy(prices)
optimizer = PortfolioOptimizer(
    risk_free_rate=0.02,
    max_weight=0.3,
    min_weight=0.0
)
print("[OK] Ready\n")

# Step 3: Create portfolio engine
print("Step 3: Creating portfolio engine...")
portfolio = PortfolioEngine(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0
)
print("[OK] Portfolio engine created\n")

# Step 4: Create strategy wrapper
print("Step 4: Creating momentum strategy...")
momentum = MomentumStrategy(
    strategy=strategy,
    optimizer=optimizer,
    top_k=5,  # Hold top 5 assets
    lookback=126,  # 6-month momentum
    objective='cvar',
    alpha=0.95,
    max_weight=0.3
)
print("[OK] Momentum strategy configured\n")

# Step 5: Run backtest
print("Step 5: Running backtest...")
result = portfolio.run_backtest(
    strategy_wrapper=momentum,
    start_date='2021-01-01',  # Start after 1 year of history
    end_date='2023-12-31',
    rebalance_freq='M'  # Monthly rebalancing
)
print("[OK] Backtest complete\n")

# Step 6: Display results
print("="*60)
print("RESULTS")
print("="*60 + "\n")

metrics = result.summary_metrics
print(f"Total Return:       {metrics['total_return']:.2%}")
print(f"Annual Return:      {metrics['annual_return']:.2%}")
print(f"Annual Volatility:  {metrics['annual_volatility']:.2%}")
print(f"Sharpe Ratio:       {metrics['sharpe_ratio']:.3f}")
print(f"Max Drawdown:       {metrics['max_drawdown']:.2%}")
print(f"Calmar Ratio:       {metrics['calmar_ratio']:.3f}")
print(f"\nTotal Trades:       {metrics['total_trades']}")
print(f"Avg Turnover:       {metrics['avg_turnover']:.2%}")
print(f"Total Costs:        ${metrics['total_costs']:,.2f}")

# Step 7: Visualize
print("\n" + "="*60)
print("VISUALIZATIONS")
print("="*60 + "\n")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Equity curve
result.equity_curve.plot(ax=axes[0, 0], color='navy', linewidth=2)
axes[0, 0].set_title("Portfolio Value Over Time", fontweight='bold')
axes[0, 0].set_ylabel("Portfolio Value ($)")
axes[0, 0].grid(True, alpha=0.3)

# Drawdown
result.drawdown_series.plot(ax=axes[0, 1], color='red', linewidth=2)
axes[0, 1].fill_between(result.drawdown_series.index, result.drawdown_series, 0, 
                         alpha=0.3, color='red')
axes[0, 1].set_title("Drawdown", fontweight='bold')
axes[0, 1].set_ylabel("Drawdown (%)")
axes[0, 1].grid(True, alpha=0.3)

# Returns distribution
result.returns_series.hist(bins=50, ax=axes[1, 0], color='skyblue', edgecolor='black')
axes[1, 0].set_title("Daily Returns Distribution", fontweight='bold')
axes[1, 0].set_xlabel("Daily Return")
axes[1, 0].set_ylabel("Frequency")
axes[1, 0].grid(True, alpha=0.3, axis='y')

# Portfolio weights (last 12 periods)
weights_subset = result.weights_history.tail(12).drop('CASH', axis=1, errors='ignore')
weights_subset.plot(kind='bar', stacked=True, ax=axes[1, 1], legend=True)
axes[1, 1].set_title("Portfolio Weights (Last 12 Months)", fontweight='bold')
axes[1, 1].set_ylabel("Weight")
axes[1, 1].set_xlabel("Date")
axes[1, 1].legend(fontsize=8, loc='best')
axes[1, 1].grid(True, alpha=0.3, axis='y')

plt.suptitle("MOMENTUM STRATEGY BACKTEST", fontsize=16, fontweight='bold')
plt.tight_layout()

# Save
os.makedirs('visualizations', exist_ok=True)
plt.savefig('visualizations/simple_example.png', dpi=300, bbox_inches='tight')
print("[OK] Visualization saved to: visualizations/simple_example.png")

plt.show()

print("\n" + "="*60)
print("EXAMPLE COMPLETE!")
print("="*60 + "\n")
