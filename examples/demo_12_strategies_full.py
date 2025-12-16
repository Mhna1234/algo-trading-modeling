"""
Demo: 12 Benchmark Strategies Comparison (FULL VERSION)
========================================================

This demo runs a comprehensive backtest of all 12 required benchmark strategies
with daily rebalancing over the full historical period.

12 BENCHMARK STRATEGIES:
1. Buy & Hold (Market / Index Benchmark)
2. Equal Weight (1/N)
3. Quintile Momentum (Cross-Sectional)
4. Quintile Low Volatility
5. Mean Reversion Quintile (Contrarian)
6. Global Minimum Variance Portfolio (GMVP)
7. Inverse Volatility Portfolio (IVol)
8. Risk Parity (Equal Risk Contribution)
9. Maximum Diversification Portfolio (MDP)
10. Maximum Decorrelation Portfolio (MDCP)
11. Sharpe Ratio Maximization (Mean–Variance)
12. CVaR Minimization Portfolio

Configuration:
- Period: Full dataset (2015-2024, ~9 years)
- Rebalancing: Monthly (realistic frequency that balances performance and costs)
- Initial capital: $100,000
- Transaction costs: 0.1%
- Universe: All 20 assets

Performance Metrics:
- Cumulative Return
- CAGR (Compound Annual Growth Rate)
- Volatility (Annualized)
- Sharpe Ratio
- Maximum Drawdown
- Calmar Ratio
- Sortino Ratio
- Win Rate

Output:
- NAV curves comparison plot
- Performance metrics bar charts
- Correlation heatmap
- Results CSV in visualizations folder
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Import project modules
from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.demo_results_aggregator import DemoResultsAggregator
from src.strategies import (
    BuyAndHoldStrategy,
    EqualWeightStrategy,
    QuintileFactorStrategy,
    QuintileLowVolatilityStrategy,
    MeanReversionStrategy,
    GlobalMinimumVarianceStrategy,
    InverseVolatilityStrategy,
    RiskParityStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    SharpeMaximizationStrategy,
    CVaRMinimizationStrategy
)
from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.bandits.ucb import UCBBandit
from src.bandits.thompson import ThompsonSamplingBandit
from src.bandits.exp3 import EXP3Bandit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

# ============================================================================
# BANDIT WRAPPER CONFIGURATION (FEATURE FLAG)
# ============================================================================
USE_BANDIT_WRAPPER = True  # Set to True to enable bandit-based strategy selection
BANDIT_CONFIG = {
    'algorithm': 'ucb',  # 'ucb' or 'thompson'
    'exploration_constant': 2.0,  # For UCB
    'burn_in_periods': 12,  # Equal allocation during burn-in
    'reward_type': 'sharpe',  # 'return', 'sharpe', or 'sortino'
    'enable_soft_allocation': False,  # CHANGED: Hard selection of best strategy
    'random_seed': 42  # For reproducibility (Thompson Sampling)
}


def create_strategy_instances(
    signal_generator: Strategy,
    optimizer: PortfolioOptimizer
) -> Dict[str, object]:
    """
    Create instances of all 12 benchmark strategies.
    
    Parameters
    ----------
    signal_generator : Strategy
        Signal generator instance
    optimizer : PortfolioOptimizer
        Portfolio optimizer instance
        
    Returns
    -------
    Dict[str, object]
        Dictionary mapping strategy names to instances
    """
    strategies = {
        '1. Buy & Hold': BuyAndHoldStrategy(
            signal_generator, optimizer
        ),
        '2. Equal Weight': EqualWeightStrategy(
            signal_generator, optimizer
        ),
        '3. Quintile Momentum': QuintileFactorStrategy(
            signal_generator, optimizer, 
            lookback=126, target_quintile=5
        ),
        '4. Quintile Low Vol': QuintileLowVolatilityStrategy(
            signal_generator, optimizer, 
            lookback=126, target_quintile=1
        ),
        '5. Mean Reversion': MeanReversionStrategy(
            signal_generator, optimizer, 
            lookback=21
        ),
        '6. GMVP': GlobalMinimumVarianceStrategy(
            signal_generator, optimizer, 
            lookback=252, max_weight=0.5
        ),
        '7. Inverse Volatility': InverseVolatilityStrategy(
            signal_generator, optimizer, 
            lookback=63
        ),
        '8. Risk Parity': RiskParityStrategy(
            signal_generator, optimizer, 
            lookback=252, max_weight=0.4
        ),
        '9. Max Diversification': MaximumDiversificationStrategy(
            signal_generator, optimizer, 
            lookback=252, max_weight=0.5
        ),
        '10. Max Decorrelation': MaximumDecorrelationStrategy(
            signal_generator, optimizer, 
            lookback=252, max_weight=0.5
        ),
        '11. Sharpe Maximization': SharpeMaximizationStrategy(
            signal_generator, optimizer, 
            lookback=252, max_weight=0.3
        ),
        '12. CVaR Minimization': CVaRMinimizationStrategy(
            signal_generator, optimizer, 
            lookback=252, alpha=0.95, max_weight=0.3
        ),
    }
    
    return strategies


def run_backtest(
    strategy_instance,
    strategy_name: str,
    prices: pd.DataFrame,
    initial_capital: float = 100000.0,
    rebalance_frequency: int = 1,
    transaction_cost: float = 0.001
) -> Optional[Dict]:
    """
    Run backtest for a single strategy.
    
    Parameters
    ----------
    strategy_instance : BaseStrategyWrapper
        Strategy instance
    strategy_name : str
        Name of strategy
    prices : pd.DataFrame
        Price data
    initial_capital : float
        Initial portfolio value
    rebalance_frequency : int
        Days between rebalances (1 = daily)
    transaction_cost : float
        Transaction cost rate
        
    Returns
    -------
    Optional[Dict]
        Backtest results or None if failed
    """
    try:
        logger.info(f"Running backtest for: {strategy_name}")
        
        # Create portfolio engine
        engine = PortfolioEngine(
            prices=prices,
            initial_capital=initial_capital,
            transaction_cost_bps=transaction_cost * 10000,  # Convert to bps
            slippage_bps=1.0
        )
        
        # Run backtest
        result = engine.run_backtest(
            strategy_wrapper=strategy_instance,
            start_date=prices.index[0],
            end_date=prices.index[-1],
            rebalance_freq='M'  # Monthly rebalancing (more realistic than daily)
        )
        
        # Extract key metrics
        metrics = result.summary_metrics
        
        logger.info(
            f"  [OK] {strategy_name}: "
            f"Total Return={metrics.get('total_return', 0):.2%}, "
            f"Sharpe={metrics.get('sharpe_ratio', 0):.3f}, "
            f"MaxDD={metrics.get('max_drawdown', 0):.2%}"
        )
        
        return {
            'name': strategy_name,
            'result': result,
            'equity_curve': result.equity_curve,
            'metrics': metrics
        }
        
    except Exception as e:
        logger.error(f"  [FAIL] {strategy_name} FAILED: {str(e)}")
        return None






def print_bandit_summary(diagnostics: Dict):
    """Print bandit wrapper performance summary including allocations and arm stats."""
    print("\\n" + "="*80)
    print("BANDIT WRAPPER PERFORMANCE SUMMARY")
    print("="*80)
    
    # Current allocations
    print("\\n1. Current Strategy Allocations alpha(t):")
    print("-" * 80)
    current_allocs = diagnostics['current_allocations']
    for strategy_name, alloc in sorted(current_allocs.items(), key=lambda x: x[1], reverse=True):
        bar = '#' * int(alloc * 50)
        print(f"  {strategy_name:40s} {alloc:6.1%} {bar}")
    
    # Show actual allocation behavior over time
    print("\\n2. Actual Capital Allocation Over Time:")
    print("-" * 80)
    
    alloc_history = diagnostics.get('allocation_history', [])
    strategy_metrics = diagnostics['strategy_metrics']
    
    if len(alloc_history) > 0:
        # Build stats from allocation history
        strategy_names = list(diagnostics['current_allocations'].keys())
        strategy_stats = {name: [] for name in strategy_names}
        
        # Extract allocations from history (skip burn-in period typically)
        for period in alloc_history:
            allocations = period.get('allocations', [])
            if isinstance(allocations, (list, np.ndarray)) and len(allocations) == len(strategy_names):
                for i, name in enumerate(strategy_names):
                    strategy_stats[name].append(float(allocations[i]))
        
        print(f"{'Strategy':<40s} {'Mean Alloc':>12s} {'Min':>8s} {'Max':>8s} {'Periods>0':>10s}")
        print("-" * 80)
        
        stats_list = []
        for name in strategy_names:
            allocs = strategy_stats[name]
            if len(allocs) > 0:
                mean_alloc = np.mean(allocs)
                min_alloc = np.min(allocs)
                max_alloc = np.max(allocs)
                periods_active = sum(1 for a in allocs if a > 0.01)  # Count periods with >1% allocation
                stats_list.append((name, mean_alloc, min_alloc, max_alloc, periods_active))
        
        # Sort by mean allocation
        stats_list.sort(key=lambda x: x[1], reverse=True)
        
        for name, mean_alloc, min_alloc, max_alloc, periods_active in stats_list:
            print(f"  {name:<38s} {mean_alloc:>11.1%} {min_alloc:>7.1%} {max_alloc:>7.1%} {periods_active:>10d}")
    
    # Show UCB algorithm state
    print("\\n3. UCB Algorithm State (for reference):")
    print("-" * 80)
    print(f"{'Strategy':<40s} {'UCB Value':>15s} {'Mean Return':>15s}")
    print("-" * 80)
    
    bandit_state = diagnostics.get('bandit_state', {})
    values = bandit_state.get('values', [])
    
    ucb_list = []
    for i, strategy_name in enumerate(strategy_names):
        ucb_value = values[i] if i < len(values) else 0.0
        mean_return = strategy_metrics[strategy_name].get('mean_return', 0.0)
        ucb_list.append((strategy_name, ucb_value, mean_return))
    
    ucb_list.sort(key=lambda x: x[1], reverse=True)
    
    for strategy_name, ucb_value, mean_return in ucb_list:
        print(f"  {strategy_name:<38s} {ucb_value:>15.4f} {mean_return:>15.4f}")
    
    # Allocation history statistics
    if 'allocation_history' in diagnostics:
        print("\\n3. Allocation Statistics:")
        print("-" * 80)
        alloc_history = diagnostics['allocation_history']
        if len(alloc_history) > 0:
            alloc_df = pd.DataFrame(alloc_history)
            print(f"Total rebalancing periods: {len(alloc_df)}")
            print(f"Burn-in complete: {diagnostics.get('burn_in_complete', False)}")
            
            # Show allocation concentration (Herfindahl index)
            # Extract last allocations properly (allocations field contains the dict/array)
            last_period = alloc_history[-1]
            allocations = last_period.get('allocations', {})
            
            # Convert allocations to numeric array
            if isinstance(allocations, dict):
                numeric_allocs = np.array(list(allocations.values()))
            elif isinstance(allocations, (list, np.ndarray)):
                numeric_allocs = np.array(allocations)
            else:
                numeric_allocs = np.array([])
            
            # Normalize if values are percentages (>1.0)
            if len(numeric_allocs) > 0 and numeric_allocs.max() > 1.0:
                numeric_allocs = numeric_allocs / 100.0
            
            herfindahl = float((numeric_allocs ** 2).sum()) if len(numeric_allocs) > 0 else 0.0
            n_strategies = len(numeric_allocs)
            print(f"Current allocation concentration (HHI): {herfindahl:.3f}")
            print(f"  (1.0 = fully concentrated, {1/n_strategies if n_strategies > 0 else 0:.3f} = equally distributed)")
    
    print("="*80 + "\\n")


def main():
    """Main execution function."""
    print("=" * 80)
    print("12 BENCHMARK STRATEGIES - FULL BACKTEST")
    if USE_BANDIT_WRAPPER:
        print("BANDIT WRAPPER ENABLED: " + BANDIT_CONFIG['algorithm'].upper())
    print("=" * 80)
    print()
    
    start_time = time.time()
    
    # Load data
    logger.info("Loading full dataset...")
    full_data, prices = load_preprocessed_data()
    logger.info(f"Data loaded: {len(prices)} dates, {len(prices.columns)} assets")
    logger.info(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")
    
    # Create signal generator and optimizer
    logger.info("Initializing signal generator and optimizer...")
    signal_generator = Strategy(prices)
    optimizer = PortfolioOptimizer(
        returns=signal_generator.returns,
        risk_free_rate=0.02,
        max_weight=0.5,
        min_weight=0.0,
        transaction_cost=0.001
    )
    
    # Create all 12 strategy instances
    logger.info("Creating 12 benchmark strategies...")
    strategies = create_strategy_instances(signal_generator, optimizer)
    logger.info(f"Created {len(strategies)} strategies")
    
    # Run backtests
    print("\n" + "=" * 80)
    print("RUNNING BACKTESTS")
    print("=" * 80)
    
    results = []
    bandit_diagnostics = {}

    # List of bandit algorithms to compare
    bandit_algorithms = [
        ('UCB', UCBBandit(
            n_arms=len(strategies),
            exploration_constant=BANDIT_CONFIG['exploration_constant']
        )),
        ('Thompson Sampling', ThompsonSamplingBandit(
            n_arms=len(strategies),
            random_seed=BANDIT_CONFIG.get('random_seed')
        )),
        ('EXP3', EXP3Bandit(
            n_arms=len(strategies),
            gamma=0.07,  # Typical value for EXP3, can be tuned
            random_seed=BANDIT_CONFIG.get('random_seed')
        )),
    ]

    if USE_BANDIT_WRAPPER:
        for bandit_name, bandit in bandit_algorithms:
            logger.info(f"Running BanditStrategyWrapper with {bandit_name} algorithm")
            wrapper = BanditStrategyWrapper(
                child_strategies=list(strategies.values()),
                bandit_allocator=bandit,
                burn_in_periods=BANDIT_CONFIG['burn_in_periods'],
                reward_type=BANDIT_CONFIG['reward_type'],
                enable_soft_allocation=BANDIT_CONFIG['enable_soft_allocation'],
                random_seed=BANDIT_CONFIG.get('random_seed')
            )
            engine = PortfolioEngine(
                prices=prices,
                initial_capital=100000.0,
                transaction_cost_bps=10,  # 0.1%
                slippage_bps=1.0
            )
            result = engine.run_backtest(
                strategy_wrapper=wrapper,
                start_date=prices.index[0],
                end_date=prices.index[-1],
                rebalance_freq='M'  # Monthly rebalancing
            )
            diagnostics = wrapper.get_diagnostics()
            bandit_diagnostics[bandit_name] = diagnostics
            results.append({
                'name': f'Bandit Meta-Strategy ({bandit_name})',
                'result': result,
                'equity_curve': result.equity_curve,
                'metrics': result.summary_metrics
            })
            logger.info(f"Bandit backtest completed for {bandit_name}")
    else:
        # Run individual strategy backtests (existing path)
        for strategy_name, strategy_instance in strategies.items():
            result = run_backtest(
                strategy_instance=strategy_instance,
                strategy_name=strategy_name,
                prices=prices,
                initial_capital=100000.0,
                rebalance_frequency=1,  # Daily
                transaction_cost=0.001
            )
            if result is not None:
                results.append(result)

    if len(results) == 0:
        logger.error("No strategies completed successfully!")
        return

    logger.info(f"\nSuccessfully completed {len(results)} strategies")

    # Print bandit summaries if enabled
    if USE_BANDIT_WRAPPER and bandit_diagnostics:
        for bandit_name, diagnostics in bandit_diagnostics.items():
            print(f"\n{'='*80}\nBANDIT ALGORITHM: {bandit_name}\n{'='*80}")
            print_bandit_summary(diagnostics)

    # Generate visualizations and reports using DemoResultsAggregator
    logger.info("Aggregating results and generating reports...")

    # Create aggregator and record all strategies
    aggregator = DemoResultsAggregator(rolling_window=60)  # 60-day for full mode

    for result in results:
        # Extract portfolio history if available
        portfolio_history = None
        if result['result'] is not None and hasattr(result['result'], 'weights_history'):
            portfolio_history = result['result'].weights_history
        aggregator.record_strategy(
            strategy_name=result['name'],
            equity_curve=result['equity_curve'],
            portfolio_history=portfolio_history
        )

    # Export structured CSV files
    csv_output_dir = aggregator.export_csv(base_dir='results')
    logger.info(f"Structured CSV files exported to: {csv_output_dir}")

    # Generate summary plots
    aggregator.plot_summary(output_dir=csv_output_dir, log_scale=False)
    logger.info(f"Summary plots generated")

    # Get summary statistics
    summary_stats = aggregator.get_summary_stats()

    # Print summary table
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    print(summary_stats.to_string(index=False))
    print()

    # Print top performers
    print("=" * 80)
    print("TOP PERFORMERS")
    print("=" * 80)
    print(f"\nHighest Total Return: {summary_stats.loc[summary_stats['Total Return (%)'].idxmax(), 'Strategy']} ({summary_stats['Total Return (%)'].max():.2f}%)")
    print(f"Highest CAGR: {summary_stats.loc[summary_stats['CAGR (%)'].idxmax(), 'Strategy']} ({summary_stats['CAGR (%)'].max():.2f}%)")
    print(f"Highest Sharpe: {summary_stats.loc[summary_stats['Sharpe Ratio'].idxmax(), 'Strategy']} ({summary_stats['Sharpe Ratio'].max():.3f})")
    print(f"Lowest Volatility: {summary_stats.loc[summary_stats['Volatility (%)'].idxmin(), 'Strategy']} ({summary_stats['Volatility (%)'].min():.2f}%)")
    print(f"Smallest Drawdown: {summary_stats.loc[summary_stats['Max Drawdown (%)'].idxmax(), 'Strategy']} ({summary_stats['Max Drawdown (%)'].max():.2f}%)")

    elapsed = time.time() - start_time
    print(f"\n{'=' * 80}")
    print(f"Total execution time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"{'=' * 80}\n")

    print("OUTPUT FILES GENERATED:")
    print(f"  [OK] Structured CSV files: {csv_output_dir}")
    print(f"      - nav.csv")
    print(f"      - returns.csv")
    print(f"      - drawdown.csv")
    print(f"      - sharpe.csv")
    print(f"      - weights_final.csv")
    print(f"      - weights_history.csv")
    print(f"  [OK] Summary plots: {csv_output_dir / 'summary_plots.png'}")
    print()

    logger.info("[OK] Full backtest completed successfully!")


if __name__ == "__main__":
    main()
