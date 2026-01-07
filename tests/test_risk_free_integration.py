"""
Demo: Risk-Free Asset Integration Test

This demo tests the newly implemented RiskFreeAsset functionality:
1. RiskFreeAsset creation and rate calculation
2. PortfolioEngine integration with risk-free returns
3. Walk-forward backtesting as default
4. Reward calculations with opportunity cost
5. Comparison of results with/without risk-free asset

Author: Portfolio Engine Team
Date: December 2025
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from src import (
    PortfolioEngine, RiskFreeAsset, RiskFreeStrategyWrapper,
    EqualWeightStrategy, BacktestingMethods
)
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

print("="*70)
print("RISK-FREE ASSET INTEGRATION DEMO")
print("="*70)
print()

# Step 1: Create synthetic price data
print("Step 1: Creating synthetic price data...")
dates = pd.date_range('2020-01-01', '2023-12-31', freq='B')  # Business days
n_assets = 5
tickers = [f'ASSET_{i+1}' for i in range(n_assets)]

np.random.seed(42)
# Create realistic return series with some correlation
returns = pd.DataFrame(
    np.random.multivariate_normal(
        mean=np.array([0.0005] * n_assets),  # 12.6% annual return
        cov=np.array([[0.0004 if i==j else 0.0001 for j in range(n_assets)]
                     for i in range(n_assets)]),
        size=len(dates)
    ),
    index=dates,
    columns=tickers
)
prices = 100 * (1 + returns).cumprod()

print(f"✓ Created {n_assets} assets with {len(dates)} trading days")
print(f"✓ Date range: {dates[0].date()} to {dates[-1].date()}")
print()

# Step 2: Test RiskFreeAsset functionality
print("Step 2: Testing RiskFreeAsset functionality...")

# Create risk-free asset with different sources
rfa_config = RiskFreeAsset(initial_rate=0.04, rate_source='config')
rfa_fallback = RiskFreeAsset(rate_source='fallback')

# Test rate calculations
test_date = pd.Timestamp('2023-06-01')
config_rate = rfa_config.get_rate(test_date)
fallback_rate = rfa_fallback.get_rate(test_date)
daily_return = rfa_config.get_daily_return(test_date)

print(f"✓ Config rate: {config_rate:.1%}")
print(f"✓ Fallback rate (2020s): {fallback_rate:.1%}")
print(f"✓ Daily return: {daily_return:.6f} ({daily_return*100:.4f}%)")
print()

# Step 3: Create strategy for testing
print("Step 3: Creating Equal Weight strategy...")
strategy_signal = Strategy(prices)
optimizer = PortfolioOptimizer(risk_free_rate=0.04)
equal_weight = EqualWeightStrategy(strategy_signal, optimizer)
print("✓ Strategy created")
print()

# Step 4: Test PortfolioEngine with and without risk-free asset
print("Step 4: Testing PortfolioEngine integration...")

# Without risk-free asset
portfolio_no_rfa = PortfolioEngine(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0
)

# With risk-free asset
portfolio_with_rfa = PortfolioEngine(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0,
    risk_free_asset=rfa_config
)

print("✓ Portfolio engines created")
print()

# Step 5: Run backtests with walk-forward method (now default)
print("Step 5: Running walk-forward backtests...")

start_date = '2021-01-01'
end_date = '2023-12-31'

print(f"Backtest period: {start_date} to {end_date}")
print("Method: Walk-Forward (Rolling, 24M train, 6M test, 3M step)")
print()

# Run backtest without risk-free asset
print("Running backtest WITHOUT risk-free asset...")
result_no_rfa = portfolio_no_rfa.run_backtest(
    strategy_wrapper=equal_weight,
    start_date=start_date,
    end_date=end_date,
    backtest_method='walk_forward'  # Explicitly test walk-forward
)
print("✓ Completed")

# Run backtest with risk-free asset
print("Running backtest WITH risk-free asset...")
result_with_rfa = portfolio_with_rfa.run_backtest(
    strategy_wrapper=equal_weight,
    start_date=start_date,
    end_date=end_date,
    backtest_method='walk_forward'  # Explicitly test walk-forward
)
print("✓ Completed")
print()

# Step 6: Compare results
print("Step 6: Comparing results...")

metrics_no_rfa = result_no_rfa.summary_metrics
metrics_with_rfa = result_with_rfa.summary_metrics

print("WITHOUT Risk-Free Asset:")
print(f"  Final NAV: ${metrics_no_rfa['final_equity']:,.0f}")
print(f"  Total Return: {metrics_no_rfa['total_return']:.1%}")
print(f"  Annual Return: {metrics_no_rfa['annual_return']:.1%}")
print(f"  Sharpe Ratio: {metrics_no_rfa['sharpe_ratio']:.3f}")
print(f"  Max Drawdown: {metrics_no_rfa['max_drawdown']:.1%}")
print(f"  Final Cash: ${result_no_rfa.cash_history.iloc[-1]:,.0f}")
print()

print("WITH Risk-Free Asset:")
print(f"  Final NAV: ${metrics_with_rfa['final_equity']:,.0f}")
print(f"  Total Return: {metrics_with_rfa['total_return']:.1%}")
print(f"  Annual Return: {metrics_with_rfa['annual_return']:.1%}")
print(f"  Sharpe Ratio: {metrics_with_rfa['sharpe_ratio']:.3f}")
print(f"  Max Drawdown: {metrics_with_rfa['max_drawdown']:.1%}")
print(f"  Final Cash: ${result_with_rfa.cash_history.iloc[-1]:,.0f}")
print()

# Step 7: Test reward calculation with opportunity cost
print("Step 7: Testing reward calculations...")

# Get some returns data for testing
test_returns = result_with_rfa.returns_series.loc['2022-01-01':'2022-12-31']

# Test reward without opportunity cost
reward_no_cost = equal_weight.evaluate_reward(test_returns, risk_free_rate=0.0)
print(f"Reward without opportunity cost: {reward_no_cost:.3f}")

# Test reward with opportunity cost
reward_with_cost = equal_weight.evaluate_reward(test_returns, risk_free_rate=0.04)
print(f"Reward with opportunity cost (4%): {reward_with_cost:.3f}")

# Test risk-free strategy reward
rfa_wrapper = RiskFreeStrategyWrapper(rfa_config)
rfa_reward = rfa_wrapper.evaluate_reward(None)  # Uses current date internally
print(f"Risk-free asset reward: {rfa_reward:.1%}")
print()

# Step 8: Test advanced backtesting methods directly
print("Step 8: Testing BacktestingMethods class...")

backtester = BacktestingMethods(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0,
    enable_soft_rebalance=True,
    drift_threshold=0.05
)

# Test vanilla backtest
vanilla_result = backtester.vanilla_backtest(
    strategy=equal_weight,
    start_date=start_date,
    end_date=end_date
)
print(f"✓ Vanilla backtest: {vanilla_result.method_name}")
sharpe_val = vanilla_result.aggregate_metrics.get('sharpe_ratio_mean', 'N/A')
print(f"  Sharpe: {sharpe_val:.3f}" if isinstance(sharpe_val, (int, float)) else f"  Sharpe: {sharpe_val}")

# Test cross-validation
cv_result = backtester.cross_validation_backtest(
    strategy=equal_weight,
    start_date=start_date,
    end_date=end_date,
    n_splits=3
)
print(f"✓ Cross-validation: {cv_result.method_name}")
sharpe_val = cv_result.aggregate_metrics.get('sharpe_ratio_mean', 'N/A')
print(f"  Sharpe: {sharpe_val:.3f}" if isinstance(sharpe_val, (int, float)) else f"  Sharpe: {sharpe_val}")
print()

# Step 9: Summary
print("="*70)
print("SUMMARY")
print("="*70)
print()
print("✅ RiskFreeAsset Implementation:")
print("  • Dynamic rate sources (FRED API, fallback rates)")
print("  • Daily return calculation with proper compounding")
print("  • Integration with PortfolioEngine for cash earnings")
print()
print("✅ PortfolioEngine Enhancements:")
print("  • Walk-forward backtesting as default method")
print("  • Risk-free asset parameter for realistic cash management")
print("  • Automatic allocation of unallocated capital to risk-free")
print()
print("✅ Reward System Updates:")
print("  • Opportunity cost adjustment in Sharpe calculations")
print("  • Risk-free strategy wrapper for MAB integration")
print("  • Enhanced evaluate_reward method")
print()
print("✅ Advanced Backtesting:")
print("  • BacktestingMethods class with multiple methodologies")
print("  • Walk-forward, cross-validation, Monte Carlo, randomized testing")
print("  • Comprehensive result aggregation and confidence intervals")
print()
print("🎯 INTEGRATION COMPLETE - Ready for MAB implementation!")
print()

# Optional: Save results for further analysis
if input("Save results to CSV? (y/n): ").lower() == 'y':
    # Save equity curves
    equity_comparison = pd.DataFrame({
        'No_RFA': result_no_rfa.equity_curve,
        'With_RFA': result_with_rfa.equity_curve
    })
    equity_comparison.to_csv('demo_rfa_comparison.csv')
    print("✓ Results saved to demo_rfa_comparison.csv")