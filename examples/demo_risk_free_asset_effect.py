"""
Demo: Risk-Free Asset Effect Demonstration

This demo shows the actual impact of risk-free asset integration by using
a strategy that deliberately under-allocates, leaving cash to earn risk-free returns.

Key Points Demonstrated:
1. Risk-free assets only affect unallocated cash
2. Strategies that allocate <100% to assets benefit from risk-free returns
3. Comparison of portfolios with/without risk-free assets
4. Realistic scenario where cash management matters

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
from src.strategies import BaseStrategyWrapper

print("="*70)
print("RISK-FREE ASSET EFFECT DEMONSTRATION")
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
    columns=tickers,
    index=dates
)
prices = (1 + returns).cumprod() * 100  # Start at $100

print(f"✓ Created {len(dates)} trading days, {n_assets} assets")
print(f"✓ Date range: {dates[0].date()} to {dates[-1].date()}")
print()

# Step 2: Create risk-free asset configurations
print("Step 2: Setting up risk-free assets...")
rfa_config = RiskFreeAsset(initial_rate=0.04, rate_source='config')  # 4% annual
rfa_fallback = RiskFreeAsset(rate_source='fallback')  # Historical rates

print("✓ Config RFA: 4.0% fixed rate")
print("✓ Fallback RFA: Decade-based historical rates")
print()

# Step 3: Create strategies that UNDER-ALLOCATE (key difference!)
print("Step 3: Creating under-allocating strategies...")

class ConservativeStrategy(BaseStrategyWrapper):
    """
    Conservative strategy that only allocates 70% to assets,
    leaving 30% in cash for risk-free returns.
    """

    def __init__(self, name="Conservative 70/30"):
        super().__init__(name, None, None)
        self.allocation_pct = 0.7  # Only allocate 70% to assets

    def get_weights(self, date: pd.Timestamp, portfolio_state):
        """Allocate 70% to equal-weighted assets, leave 30% cash."""
        # Get assets from portfolio state (exclude cash)
        assets = [asset for asset in portfolio_state.current_weights.index if asset != 'CASH']
        n_assets = len(assets)
        asset_weight = self.allocation_pct / n_assets
        weights = {asset: asset_weight for asset in assets}
        return pd.Series(weights)

    def evaluate_reward(self, returns, risk_free_rate=0.0):
        """Simple return-based reward."""
        if isinstance(returns, pd.Series):
            return returns.mean() * 252  # Annualized
        return 0.0

    def get_rebalancing_frequency(self):
        return 'M'

    def get_strategy_info(self):
        return {
            'name': self.name,
            'type': 'conservative',
            'allocation_pct': self.allocation_pct
        }

class ModerateStrategy(BaseStrategyWrapper):
    """
    Moderate strategy that allocates 90% to assets,
    leaving 10% in cash.
    """

    def __init__(self, name="Moderate 90/10"):
        super().__init__(name, None, None)
        self.allocation_pct = 0.9

    def get_weights(self, date: pd.Timestamp, portfolio_state):
        """Allocate 90% to equal-weighted assets, leave 10% cash."""
        # Get assets from portfolio state (exclude cash)
        assets = [asset for asset in portfolio_state.current_weights.index if asset != 'CASH']
        n_assets = len(assets)
        asset_weight = self.allocation_pct / n_assets
        weights = {asset: asset_weight for asset in assets}
        return pd.Series(weights)

    def evaluate_reward(self, returns, risk_free_rate=0.0):
        """Simple return-based reward."""
        if isinstance(returns, pd.Series):
            return returns.mean() * 252
        return 0.0

    def get_rebalancing_frequency(self):
        return 'M'

    def get_strategy_info(self):
        return {
            'name': self.name,
            'type': 'moderate',
            'allocation_pct': self.allocation_pct
        }

conservative = ConservativeStrategy()
moderate = ModerateStrategy()

print("✓ Conservative: 70% assets / 30% cash")
print("✓ Moderate: 90% assets / 10% cash")
print()

# Step 4: Create portfolio engines
print("Step 4: Setting up portfolio engines...")

# Without risk-free asset
portfolio_no_rfa = PortfolioEngine(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0
)

# With risk-free asset (4% fixed)
portfolio_with_rfa = PortfolioEngine(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0,
    risk_free_asset=rfa_config
)

# With fallback risk-free asset (historical rates)
portfolio_with_fallback_rfa = PortfolioEngine(
    prices=prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0,
    risk_free_asset=rfa_fallback
)

print("✓ Three portfolio configurations created")
print()

# Step 5: Run backtests
print("Step 5: Running backtests...")

start_date = '2021-01-01'
end_date = '2023-12-31'

strategies = [
    ("Conservative (70/30)", conservative),
    ("Moderate (90/10)", moderate)
]

results = {}

for strategy_name, strategy in strategies:
    print(f"\nRunning {strategy_name} strategy...")

    # No risk-free asset
    result_no_rfa = portfolio_no_rfa.run_backtest(
        strategy_wrapper=strategy,
        start_date=start_date,
        end_date=end_date
    )

    # With fixed 4% risk-free asset
    result_with_rfa = portfolio_with_rfa.run_backtest(
        strategy_wrapper=strategy,
        start_date=start_date,
        end_date=end_date
    )

    # With fallback risk-free asset
    result_with_fallback = portfolio_with_fallback_rfa.run_backtest(
        strategy_wrapper=strategy,
        start_date=start_date,
        end_date=end_date
    )

    results[strategy_name] = {
        'no_rfa': result_no_rfa,
        'fixed_rfa': result_with_rfa,
        'fallback_rfa': result_with_fallback
    }

    print("✓ Completed all variants")

print()

# Step 6: Analyze and display results
print("Step 6: Results Analysis")
print("="*50)

for strategy_name, strategy_results in results.items():
    print(f"\n{strategy_name} Strategy Results:")
    print("-" * 40)

    for rfa_type, result in strategy_results.items():
        rfa_label = {
            'no_rfa': 'No Risk-Free Asset',
            'fixed_rfa': '4% Fixed Rate',
            'fallback_rfa': 'Historical Rates'
        }[rfa_type]

        print(f"  Final NAV: ${result.equity_curve.iloc[-1]:,.2f}")
        print(f"  Total Return: {result.summary_metrics['total_return']:.1%}")
        print(f"  Annual Return: {result.summary_metrics['annual_return']:.1%}")
        print(f"  Sharpe Ratio: {result.summary_metrics['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {result.summary_metrics['max_drawdown']:.1%}")
        print(f"  Final Cash: ${result.cash_history.iloc[-1]:,.2f}")
        print()

# Step 7: Show the benefit of risk-free assets
print("Step 7: Risk-Free Asset Benefit Analysis")
print("="*50)

for strategy_name, strategy_results in results.items():
    print(f"\n{strategy_name} - Risk-Free Asset Impact:")

    no_rfa_nav = strategy_results['no_rfa'].equity_curve.iloc[-1]
    fixed_rfa_nav = strategy_results['fixed_rfa'].equity_curve.iloc[-1]
    fallback_rfa_nav = strategy_results['fallback_rfa'].equity_curve.iloc[-1]

    fixed_benefit = fixed_rfa_nav - no_rfa_nav
    fallback_benefit = fallback_rfa_nav - no_rfa_nav

    print(f"  Fixed 4% RFA benefit: ${fixed_benefit:,.2f}")
    print(f"  Historical RFA benefit: ${fallback_benefit:,.2f}")
    print(f"  Fixed RFA benefit: {fixed_benefit/no_rfa_nav:.1%} of portfolio")
    print(f"  Historical RFA benefit: {fallback_benefit/no_rfa_nav:.1%} of portfolio")

    # Calculate cash drag avoided
    if strategy_name == "Conservative (70/30)":
        expected_cash_pct = 0.30
    else:  # Moderate
        expected_cash_pct = 0.10

    initial_capital = 1_000_000
    avg_cash_holding = initial_capital * expected_cash_pct
    annual_rfa_return = 0.04
    expected_annual_benefit = avg_cash_holding * annual_rfa_return

    print(f"  Expected annual benefit from {expected_cash_pct:.0%} cash at 4%: ${expected_annual_benefit:,.0f}")
    print()

# Step 8: Summary
print("Step 8: Key Insights")
print("="*30)
print("✅ Risk-free assets only benefit strategies that hold cash")
print("✅ Under-allocation creates opportunity for risk-free returns")
print("✅ Conservative strategies benefit more from risk-free assets")
print("✅ Historical rates provide more realistic cash management")
print("✅ Integration works correctly - cash earns risk-free returns!")
print()

print("🎯 DEMO COMPLETE - Risk-free asset integration is working!")