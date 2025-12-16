"""
Demo: 12 Benchmark Strategies Comparison with EXP3 Bandit
========================================================

This demo runs a comprehensive backtest of all 12 required benchmark strategies
using the EXP3 bandit algorithm for dynamic strategy allocation.

Configuration:
- Period: Full dataset (2015-2024, ~9 years)
- Rebalancing: Monthly
- Initial capital: $100,000
- Transaction costs: 0.1%
- Universe: All 20 assets
- Bandit: EXP3 (adversarial, non-stationary)

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
import logging
from typing import Dict, Optional

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
from src.bandits.exp3 import EXP3Bandit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

# BANDIT WRAPPER CONFIGURATION
USE_BANDIT_WRAPPER = True
BANDIT_CONFIG = {
    'algorithm': 'exp3',
    'gamma': 0.07,  # EXP3 exploration parameter
    'burn_in_periods': 12,
    'reward_type': 'sharpe',
    'enable_soft_allocation': False,
    'random_seed': 42,
    'reward_shift': 0.5,  # Example: shift rewards to [0,1] if needed
    'reward_scale': 1.0
}

def create_strategy_instances(signal_generator: Strategy, optimizer: PortfolioOptimizer) -> Dict[str, object]:
    strategies = {
        '1. Buy & Hold': BuyAndHoldStrategy(signal_generator, optimizer),
        '2. Equal Weight': EqualWeightStrategy(signal_generator, optimizer),
        '3. Quintile Momentum': QuintileFactorStrategy(signal_generator, optimizer, lookback=126, target_quintile=5),
        '4. Quintile Low Vol': QuintileLowVolatilityStrategy(signal_generator, optimizer, lookback=126, target_quintile=1),
        '5. Mean Reversion': MeanReversionStrategy(signal_generator, optimizer, lookback=21),
        '6. GMVP': GlobalMinimumVarianceStrategy(signal_generator, optimizer, lookback=252, max_weight=0.5),
        '7. Inverse Volatility': InverseVolatilityStrategy(signal_generator, optimizer, lookback=63),
        '8. Risk Parity': RiskParityStrategy(signal_generator, optimizer, lookback=252, max_weight=0.4),
        '9. Max Diversification': MaximumDiversificationStrategy(signal_generator, optimizer, lookback=252, max_weight=0.5),
        '10. Max Decorrelation': MaximumDecorrelationStrategy(signal_generator, optimizer, lookback=252, max_weight=0.5),
        '11. Sharpe Maximization': SharpeMaximizationStrategy(signal_generator, optimizer, lookback=252, max_weight=0.3),
        '12. CVaR Minimization': CVaRMinimizationStrategy(signal_generator, optimizer, lookback=252, alpha=0.95, max_weight=0.3),
    }
    return strategies

def main():
    print("=" * 80)
    print("12 BENCHMARK STRATEGIES - FULL BACKTEST (EXP3 BANDIT)")
    print("BANDIT WRAPPER ENABLED: EXP3")
    print("=" * 80)
    print()
    start_time = time.time()
    logger.info("Loading full dataset...")
    full_data, prices = load_preprocessed_data()
    logger.info(f"Data loaded: {len(prices)} dates, {len(prices.columns)} assets")
    logger.info(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")
    logger.info("Initializing signal generator and optimizer...")
    signal_generator = Strategy(prices)
    optimizer = PortfolioOptimizer(
        returns=signal_generator.returns,
        risk_free_rate=0.02,
        max_weight=0.5,
        min_weight=0.0,
        transaction_cost=0.001
    )
    logger.info("Creating 12 benchmark strategies...")
    strategies = create_strategy_instances(signal_generator, optimizer)
    logger.info(f"Created {len(strategies)} strategies")
    print("\n" + "=" * 80)
    print("RUNNING BACKTESTS")
    print("=" * 80)
    results = []
    bandit_diagnostics = None
    if USE_BANDIT_WRAPPER:
        logger.info("Creating BanditStrategyWrapper with EXP3 algorithm")
        bandit = EXP3Bandit(
            n_arms=len(strategies),
            gamma=BANDIT_CONFIG['gamma'],
            reward_shift=BANDIT_CONFIG.get('reward_shift'),
            reward_scale=BANDIT_CONFIG.get('reward_scale'),
            random_seed=BANDIT_CONFIG.get('random_seed')
        )
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
            rebalance_freq='M'
        )
        bandit_diagnostics = wrapper.get_diagnostics()
        results.append({
            'name': 'EXP3 Bandit Meta-Strategy',
            'result': result,
            'equity_curve': result.equity_curve,
            'metrics': result.summary_metrics
        })
        logger.info("Bandit backtest completed")
    if len(results) == 0:
        logger.error("No strategies completed successfully!")
        return
    logger.info(f"\nSuccessfully completed {len(results)} strategy")
    # Generate visualizations and reports using DemoResultsAggregator
    logger.info("Aggregating results and generating reports...")
    aggregator = DemoResultsAggregator(rolling_window=60)
    for result in results:
        portfolio_history = None
        if result['result'] is not None and hasattr(result['result'], 'weights_history'):
            portfolio_history = result['result'].weights_history
        aggregator.record_strategy(
            strategy_name=result['name'],
            equity_curve=result['equity_curve'],
            portfolio_history=portfolio_history
        )
    csv_output_dir = aggregator.export_csv(base_dir='results')
    logger.info(f"Structured CSV files exported to: {csv_output_dir}")
    aggregator.plot_summary(output_dir=csv_output_dir, log_scale=False)
    logger.info(f"Summary plots generated")
    summary_stats = aggregator.get_summary_stats()
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    print(summary_stats.to_string(index=False))
    print()
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
