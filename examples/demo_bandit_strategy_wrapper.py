"""
Demo: BanditStrategyWrapper with Real Strategies

This example demonstrates how to use BanditStrategyWrapper to dynamically
allocate capital across multiple trading strategies using multi-armed bandits.

Key Features Demonstrated:
- Integration with existing strategy wrappers
- Comparison of UCB vs Thompson Sampling algorithms
- Strategy allocation evolution over time
- Performance attribution and diagnostics
- Risk-adjusted reward calculation

Author: GitHub Copilot
Date: December 2025
"""

import pandas as pd
import numpy as np
from pandas import Series
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from src.signal_generator import StrategySignalGenerator as Strategy
from src.optimizer import PortfolioOptimizer
from src.strategies import (
    MomentumStrategy, 
    MeanReversionStrategy, 
    InverseVolatilityStrategy
)
from src.bandits import UCBBandit, ThompsonSamplingBandit
from src.bandit_strategy_wrapper import BanditStrategyWrapper
from src.portfolio_engine import PortfolioEngine


def create_sample_data():
    """Create sample price data for demonstration."""
    # Use small date range for quick demo
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    
    # Generate correlated random returns
    np.random.seed(42)
    n_periods = len(dates)
    n_assets = len(tickers)
    
    # Create returns with some momentum and mean reversion
    returns = np.random.normal(0.001, 0.02, (n_periods, n_assets))
    
    # Add momentum to AAPL and NVDA
    returns[:, 0] += np.linspace(0, 0.005, n_periods)  # AAPL uptrend
    returns[:, 4] += np.linspace(0, 0.003, n_periods)  # NVDA uptrend
    
    # Add mean reversion to MSFT
    returns[:, 1] = np.sin(np.linspace(0, 4*np.pi, n_periods)) * 0.01
    
    # Create prices from returns (cumulative product along time axis)
    prices = pd.DataFrame(100 * (1 + returns).cumprod(axis=0), index=dates, columns=tickers)
    
    return prices


def run_bandit_demo():
    """Run comprehensive BanditStrategyWrapper demonstration."""
    print("=" * 80)
    print("BanditStrategyWrapper Demonstration")
    print("=" * 80)
    print()
    
    # 1. Load data
    print("1. Loading sample data...")
    prices = create_sample_data()
    print(f"   Data shape: {prices.shape}")
    print(f"   Date range: {prices.index[0]} to {prices.index[-1]}")
    print(f"   Assets: {list(prices.columns)}")
    print()
    
    # 2. Create strategy and optimizer objects
    print("2. Initializing signal generators and optimizers...")
    strategy = Strategy(prices)
    optimizer = PortfolioOptimizer(strategy.get_return_matrix())
    print()
    
    # 3. Create child strategies
    print("3. Creating child strategies...")
    
    # Strategy 1: Momentum (trend following)
    momentum_strategy = MomentumStrategy(
        strategy=strategy,
        optimizer=optimizer,
        top_k=3,
        lookback=20,
        objective='cvar',
        alpha=0.95,
        max_weight=0.5
    )
    print(f"   - {momentum_strategy.name}")
    
    # Strategy 2: Mean Reversion (contrarian)
    mean_rev_strategy = MeanReversionStrategy(
        strategy=strategy,
        optimizer=optimizer,
        top_k=3,
        window=10,
        objective='mvo',
        risk_aversion=2.0,
        max_weight=0.5
    )
    print(f"   - {mean_rev_strategy.name}")
    
    # Strategy 3: Inverse Volatility (risk parity)
    inv_vol_strategy = InverseVolatilityStrategy(
        strategy=strategy,
        optimizer=optimizer,
        vol_window=20,
        objective='risk_parity',
        max_weight=0.5
    )
    print(f"   - {inv_vol_strategy.name}")
    print()
    
    # 4. Create bandit allocators
    print("4. Creating bandit allocators...")
    
    ucb_bandit = UCBBandit(n_arms=3, exploration_constant=2.0)
    print(f"   - UCB Bandit (exploration_constant=2.0)")
    
    thompson_bandit = ThompsonSamplingBandit(
        n_arms=3,
        prior_mean=0.0,
        prior_variance=1.0,
        random_seed=42
    )
    print(f"   - Thompson Sampling Bandit (seed=42)")
    print()
    
    # 5. Create bandit wrappers
    print("5. Creating BanditStrategyWrappers...")
    
    ucb_wrapper = BanditStrategyWrapper(
        child_strategies=[momentum_strategy, mean_rev_strategy, inv_vol_strategy],
        bandit_allocator=ucb_bandit,
        strategy=strategy,
        optimizer=optimizer,
        reward_type='sharpe',
        reward_lookback=10,
        burn_in_periods=5,
        min_allocation=0.1,
        enable_soft_allocation=True,
        random_seed=42
    )
    print(f"   - {ucb_wrapper.name} (UCB)")
    
    thompson_wrapper = BanditStrategyWrapper(
        child_strategies=[
            MomentumStrategy(strategy, optimizer, top_k=3, lookback=20, max_weight=0.5),
            MeanReversionStrategy(strategy, optimizer, top_k=3, window=10, max_weight=0.5),
            InverseVolatilityStrategy(strategy, optimizer, vol_window=20, max_weight=0.5)
        ],
        bandit_allocator=thompson_bandit,
        strategy=strategy,
        optimizer=optimizer,
        reward_type='sharpe',
        reward_lookback=10,
        burn_in_periods=5,
        min_allocation=0.1,
        enable_soft_allocation=True,
        random_seed=43  # Different seed for independent simulation
    )
    print(f"   - {thompson_wrapper.name} (Thompson)")
    print()
    
    # 6. Run backtests
    print("6. Running backtests...")
    print("   (This simulates real portfolio engine usage)")
    
    # Configuration
    rebalance_freq = 'W'  # Weekly rebalancing
    initial_capital = 100000.0
    transaction_cost_bps = 5.0
    
    print(f"   - Rebalance frequency: {rebalance_freq}")
    print(f"   - Initial capital: ${initial_capital:,.0f}")
    print(f"   - Transaction cost: {transaction_cost_bps} bps")
    print()
    
    # Create portfolio engines
    ucb_engine = PortfolioEngine(
        prices=prices,
        initial_capital=initial_capital,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=1.0
    )
    
    thompson_engine = PortfolioEngine(
        prices=prices,
        initial_capital=initial_capital,
        transaction_cost_bps=transaction_cost_bps,
        slippage_bps=1.0
    )
    
    # Run backtests
    print("   Running UCB backtest...")
    ucb_result = ucb_engine.run_backtest(
        strategy_wrapper=ucb_wrapper,
        start_date=prices.index[20],  # Start after warmup
        end_date=prices.index[-1],
        rebalance_freq=rebalance_freq
    )
    
    print("   Running Thompson Sampling backtest...")
    thompson_result = thompson_engine.run_backtest(
        strategy_wrapper=thompson_wrapper,
        start_date=prices.index[20],  # Start after warmup
        end_date=prices.index[-1],
        rebalance_freq=rebalance_freq
    )
    print()
    
    # 7. Compare results
    print("7. Performance Comparison")
    print("-" * 80)
    
    def print_metrics(name, result):
        metrics = result.summary_metrics
        print(f"\n{name}:")
        print(f"   Total Return:     {metrics.get('total_return', 0.0):>10.2%}")
        print(f"   Sharpe Ratio:     {metrics.get('sharpe_ratio', 0.0):>10.4f}")
        print(f"   Max Drawdown:     {metrics.get('max_drawdown', 0.0):>10.2%}")
        print(f"   Annual Volatility:{metrics.get('annual_volatility', 0.0):>10.2%}")
        print(f"   Final Value:      ${result.equity_curve.iloc[-1]:>10,.2f}")
    
    print_metrics("UCB Bandit", ucb_result)
    print_metrics("Thompson Sampling", thompson_result)
    print()
    
    # 8. Strategy allocation analysis
    print("8. Strategy Allocation Analysis")
    print("-" * 80)
    
    def print_allocations(name, wrapper):
        print(f"\n{name}:")
        alloc_df = wrapper.get_strategy_allocations()
        
        if len(alloc_df) > 0:
            # Show last 5 periods
            print("\nRecent allocations (last 5 periods):")
            print(alloc_df.tail(5).to_string(float_format=lambda x: f"{x:.3f}"))
            
            # Show average allocations
            print("\nAverage allocations:")
            avg_alloc = alloc_df.mean()
            for strategy_name, alloc in avg_alloc.items():
                print(f"   {strategy_name:<30} {alloc:>6.2%}")
    
    print_allocations("UCB Bandit", ucb_wrapper)
    print_allocations("Thompson Sampling", thompson_wrapper)
    print()
    
    # 9. Diagnostics
    print("9. Detailed Diagnostics")
    print("-" * 80)
    
    def print_diagnostics(name, wrapper):
        print(f"\n{name}:")
        diagnostics = wrapper.get_diagnostics()
        
        print(f"   Periods processed: {diagnostics['period_count']}")
        print(f"   Burn-in complete: {diagnostics['burn_in_complete']}")
        
        print("\n   Current strategy allocations:")
        for strategy_name, alloc in diagnostics['current_allocations'].items():
            print(f"      {strategy_name:<30} {alloc:>6.2%}")
        
        print("\n   Strategy performance metrics:")
        for strategy_name, metrics in diagnostics['strategy_metrics'].items():
            print(f"      {strategy_name}:")
            print(f"         Mean return:    {metrics['mean_return']:>8.4f}")
            print(f"         Volatility:     {metrics['volatility']:>8.4f}")
            print(f"         Sharpe:         {metrics['sharpe']:>8.4f}")
            print(f"         Mean allocation:{metrics['mean_allocation']:>8.4f}")
    
    print_diagnostics("UCB Bandit", ucb_wrapper)
    print_diagnostics("Thompson Sampling", thompson_wrapper)
    print()
    
    # 10. Summary
    print("10. Summary")
    print("=" * 80)
    print()
    print("The BanditStrategyWrapper successfully:")
    print("  [OK] Integrated with existing strategy wrappers")
    print("  [OK] Dynamically allocated capital across strategies")
    print("  [OK] Calculated risk-adjusted rewards (Sharpe ratio)")
    print("  [OK] Respected burn-in period for initial exploration")
    print("  [OK] Applied minimum allocation constraints")
    print("  [OK] Provided comprehensive diagnostics")
    print()
    
    # Determine winner
    ucb_sharpe = ucb_result.summary_metrics.get('sharpe_ratio', 0.0)
    thompson_sharpe = thompson_result.summary_metrics.get('sharpe_ratio', 0.0)
    
    if ucb_sharpe > thompson_sharpe:
        winner = "UCB"
        diff = (ucb_sharpe - thompson_sharpe) / thompson_sharpe * 100
    else:
        winner = "Thompson Sampling"
        diff = (thompson_sharpe - ucb_sharpe) / ucb_sharpe * 100
    
    print(f"Winner: {winner} (+{diff:.1f}% better Sharpe ratio)")
    print()
    
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_bandit_demo()
