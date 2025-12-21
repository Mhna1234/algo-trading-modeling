"""
Demo: Soft Rebalancing Walk-Forward Comparison (15 Strategies)
============================================================

This demo compares all 15 strategies (12 benchmarks + 3 bandit meta-strategies)
using soft rebalancing (5% drift threshold) with walk-forward (rolling window) backtesting.

Metrics and plots include:
- Cumulative Return
- CAGR
- Volatility (Annualized)
- Sharpe Ratio
- Max Drawdown
- Calmar Ratio
- Sortino Ratio
- Win Rate
- Turnover
- Transaction Costs

Output:
- NAV curves comparison plot
- Performance metrics bar charts
- Results CSV in visualizations folder
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import logging

# Project imports
sys.path.insert(0, str(Path(__file__).parent.parent))
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

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

# Configuration
DRIFT_THRESHOLD = 0.05
ENABLE_SOFT_REBALANCE = True
INITIAL_CAPITAL = 100_000
TRANSACTION_COST_BPS = 10.0
SLIPPAGE_BPS = 5.0
RISK_FREE_RATE = 0.02

# Walk-forward config
TRAIN_WINDOW_MONTHS = 24
TEST_WINDOW_MONTHS = 6
STEP_MONTHS = 6
REBALANCE_FREQ = 'Q'  # Quarterly

BANDIT_CONFIG = {
    'exploration_constant': 2.0,
    'burn_in_periods': 12,
    'reward_type': 'sharpe',
    'enable_soft_allocation': False,
    'random_seed': 42
}


def create_strategy_instances(signal_generator, optimizer):
    """Create all 12 benchmark strategies."""
    return {
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


def run_walk_forward(prices, strategy_name, strategy_instance):
    """Run walk-forward backtest for a single strategy."""
    from src.backtesting_methods import BacktestingMethods
    bt_methods = BacktestingMethods(
        prices=prices,
        initial_capital=INITIAL_CAPITAL,
        transaction_cost_bps=TRANSACTION_COST_BPS,
        slippage_bps=SLIPPAGE_BPS,
        drift_threshold=DRIFT_THRESHOLD,
        enable_soft_rebalance=ENABLE_SOFT_REBALANCE
    )
    result = bt_methods.walk_forward_backtest(
        strategy=strategy_instance,
        start_date=prices.index[0].strftime('%Y-%m-%d'),
        end_date=prices.index[-1].strftime('%Y-%m-%d'),
        train_window_months=TRAIN_WINDOW_MONTHS,
        test_window_months=TEST_WINDOW_MONTHS,
        step_months=STEP_MONTHS,
        rebalance_freq=REBALANCE_FREQ,
        anchored=False
    )
    return result


def main():
    print("=" * 80)
    print("SOFT REBALANCING WALK-FORWARD DEMO: 15 STRATEGIES")
    print("=" * 80)
    start_time = time.time()

    # Load data
    logger.info("Loading full dataset...")
    full_data, prices = load_preprocessed_data()
    logger.info(f"Data loaded: {len(prices)} dates, {len(prices.columns)} assets")
    logger.info(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")

    # Create signal generator and optimizer
    signal_generator = Strategy(prices)
    optimizer = PortfolioOptimizer(
        returns=signal_generator.returns,
        risk_free_rate=RISK_FREE_RATE,
        max_weight=0.5,
        min_weight=0.0,
        transaction_cost=TRANSACTION_COST_BPS / 10000.0
    )

    # Create all 12 strategy instances
    strategies = create_strategy_instances(signal_generator, optimizer)

    # Add bandit meta-strategies
    bandit_algorithms = [
        ('Bandit Meta-Strategy (UCB)', UCBBandit(n_arms=len(strategies), exploration_constant=BANDIT_CONFIG['exploration_constant'])),
        ('Bandit Meta-Strategy (Thompson)', ThompsonSamplingBandit(n_arms=len(strategies), random_seed=BANDIT_CONFIG['random_seed'])),
        ('Bandit Meta-Strategy (EXP3)', EXP3Bandit(n_arms=len(strategies), gamma=0.07, random_seed=BANDIT_CONFIG['random_seed'])),
    ]

    all_results = []
    for strategy_name, strategy_instance in strategies.items():
        logger.info(f"Running walk-forward for: {strategy_name}")
        result = run_walk_forward(prices, strategy_name, strategy_instance)
        all_results.append((strategy_name, result))

    # Bandit wrappers
    for bandit_name, bandit in bandit_algorithms:
        logger.info(f"Running walk-forward for: {bandit_name}")
        wrapper = BanditStrategyWrapper(
            child_strategies=list(strategies.values()),
            bandit_allocator=bandit,
            burn_in_periods=BANDIT_CONFIG['burn_in_periods'],
            reward_type=BANDIT_CONFIG['reward_type'],
            enable_soft_allocation=BANDIT_CONFIG['enable_soft_allocation'],
            random_seed=BANDIT_CONFIG['random_seed']
        )
        result = run_walk_forward(prices, bandit_name, wrapper)
        all_results.append((bandit_name, result))

    # Aggregate and plot results
    logger.info("Aggregating results and generating reports...")
    metrics = []
    nav_curves = {}
    for name, wf_result in all_results:
        # Use mean of test periods for summary
        agg = wf_result.aggregate_metrics
        # Use the first individual result's equity_curve as NAV curve for now
        if hasattr(wf_result, 'individual_results') and wf_result.individual_results:
            nav_curves[name] = wf_result.individual_results[0].equity_curve
        else:
            nav_curves[name] = None
        metrics.append({
            'Strategy': name,
            'Total Return (%)': agg.get('total_return_mean', np.nan) * 100,
            'CAGR (%)': agg.get('annual_return_mean', np.nan) * 100,
            'Volatility (%)': agg.get('annual_volatility_mean', np.nan) * 100,
            'Sharpe Ratio': agg.get('sharpe_ratio_mean', np.nan),
            'Max Drawdown (%)': agg.get('max_drawdown_mean', np.nan) * 100,
            'Calmar Ratio': agg.get('calmar_ratio_mean', np.nan),
            'Sortino Ratio': agg.get('sortino_ratio_mean', np.nan),
            'Win Rate (%)': agg.get('win_rate_mean', np.nan) * 100,
            'Avg Turnover (%)': agg.get('avg_turnover_mean', np.nan) * 100,
            'Transaction Costs ($)': agg.get('total_transaction_costs_mean', np.nan),
        })

    df_metrics = pd.DataFrame(metrics)
    df_metrics.sort_values('Sharpe Ratio', ascending=False, inplace=True)

    # Save metrics
    os.makedirs('visualizations', exist_ok=True)
    metrics_path = 'visualizations/soft_rebalancing_walkforward_metrics.csv'
    df_metrics.to_csv(metrics_path, index=False)
    print(f"[OK] Metrics saved to {metrics_path}")

    # Plot NAV curves
    plt.figure(figsize=(16, 8))
    for name, nav in nav_curves.items():
        plt.plot(nav.index, nav.values, label=name)
    plt.title('NAV Curves: Soft Rebalancing Walk-Forward (15 Strategies)', fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.legend(fontsize=8, loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    nav_plot_path = 'visualizations/soft_rebalancing_walkforward_nav.png'
    plt.savefig(nav_plot_path, dpi=300)
    print(f"[OK] NAV plot saved to {nav_plot_path}")
    plt.close()

    # Plot bar charts for key metrics
    bar_metrics = [
        ('Sharpe Ratio', 'Sharpe Ratio'),
        ('Total Return (%)', 'Total Return (%)'),
        ('Max Drawdown (%)', 'Max Drawdown (%)'),
        ('Avg Turnover (%)', 'Avg Turnover (%)'),
        ('Transaction Costs ($)', 'Transaction Costs ($)'),
    ]
    for metric, col in bar_metrics:
        plt.figure(figsize=(14, 6))
        sns.barplot(x='Strategy', y=col, data=df_metrics, palette='viridis')
        plt.title(f'{metric} by Strategy (Soft Rebalancing Walk-Forward)', fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plot_path = f'visualizations/soft_rebalancing_walkforward_{col.replace(" ", "_").replace("%", "pct").replace("$", "usd").lower()}.png'
        plt.savefig(plot_path, dpi=300)
        print(f"[OK] {metric} plot saved to {plot_path}")
        plt.close()

    print("\n[OK] All results and plots saved in 'visualizations/' folder.")
    print("\nTop 5 by Sharpe Ratio:")
    print(df_metrics[['Strategy', 'Sharpe Ratio', 'Total Return (%)', 'Max Drawdown (%)']].head(5).to_string(index=False))

    elapsed = time.time() - start_time
    print(f"\nTotal execution time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print("=" * 80)

if __name__ == "__main__":
    main()
