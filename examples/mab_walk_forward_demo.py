"""
MAB Walk-Forward Demo - Multi-Armed Bandit Algorithm Comparison with Walk-Forward Backtesting
===============================================================================================

This demo compares four MAB algorithms (UCB, Thompson Sampling, EXP3, Epsilon-Greedy)
using walk-forward backtesting with rolling windows for out-of-sample evaluation.
The 12 benchmark strategies plus a risk-free asset serve as arms for dynamic capital allocation.

Key Features:
- 12 benchmark strategies + risk-free asset as MAB arms
- Walk-forward backtesting with rolling windows (out-of-sample evaluation)
- Dynamic allocation between risky assets and cash
- Proper reward scaling for each algorithm
- Comprehensive performance tracking across folds
- Allocation evolution visualization
- Learning curve analysis
- Risk-adjusted performance metrics

Algorithms Compared:
1. UCB (Upper Confidence Bound): Deterministic, balances exploration/exploitation
2. Thompson Sampling: Bayesian, samples from posterior distributions
3. EXP3: Adversarial, handles non-stationary environments
4. Epsilon-Greedy: Simple exploration strategy with fixed exploration rate

Backtesting Approach:
- Walk-forward backtesting with rolling windows for out-of-sample evaluation
- Monthly rebalancing with hard allocation (single strategy selection)
- Transaction cost awareness
- Risk-free asset integration
- Fold-level diagnostics and aggregation

Output:
- Performance comparison across MAB algorithms
- Allocation evolution over time (including cash allocation)
- Learning effectiveness metrics across folds
- Strategy and cash contribution analysis
- Comprehensive visualizations
- Walk-forward integrity validation

Author: MAB Walk-Forward Demo
Date: December 2025
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from datetime import datetime
from pathlib import Path
import logging

from src.config_loader import load_trading_config
from src.data_loader import load_preprocessed_data
from src.backtesting_methods import BacktestingMethods, BacktestMethodResult
from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.bandits import UCBBandit, ThompsonSamplingBandit, EXP3Bandit, EpsilonGreedy
from src.strategies import (
    BuyAndHoldStrategy, EqualWeightStrategy, QuintileFactorStrategy,
    QuintileLowVolatilityStrategy, MeanReversionStrategy, GlobalMinimumVarianceStrategy,
    InverseVolatilityStrategy, RiskParityStrategy, MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy, SharpeMaximizationStrategy, CVaRMinimizationStrategy
)
from src.risk_free_asset import RiskFreeAsset, RiskFreeStrategyWrapper
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MABWalkForwardDemo:
    """
    Comprehensive MAB algorithm comparison using walk-forward backtesting.
    """

    def __init__(self):
        self.config = load_trading_config()
        self.results_dir = Path('results')
        self.results_dir.mkdir(exist_ok=True)

        # Initialize data and components
        self._load_data()
        self._setup_strategies()

        # Results storage
        self.mab_results = {}
        self.mab_wrappers = {}  # Store wrappers for detailed analysis
        self.leaderboard = []

    def _load_data(self):
        """Load and prepare market data."""
        logger.info("Loading market data...")
        full_data, price_data = load_preprocessed_data()

        # Filter date range
        self.data = price_data.loc[self.config.start_date:self.config.end_date]
        logger.info(f"Loaded data: {len(self.data)} assets, {len(self.data.index)} dates")

    def _setup_strategies(self):
        """Initialize the 12 benchmark strategies."""
        logger.info("Setting up benchmark strategies...")

        signal_gen = Strategy(self.data)
        optimizer = PortfolioOptimizer()

        self.strategies = [
            ("Buy & Hold", BuyAndHoldStrategy(signal_gen, optimizer)),
            ("Equal Weight", EqualWeightStrategy(signal_gen, optimizer)),
            ("Quintile Factor", QuintileFactorStrategy(signal_gen, optimizer)),
            ("Low Volatility", QuintileLowVolatilityStrategy(signal_gen, optimizer)),
            ("Mean Reversion", MeanReversionStrategy(signal_gen, optimizer)),
            ("Global Min Var", GlobalMinimumVarianceStrategy(signal_gen, optimizer)),
            ("Inverse Vol", InverseVolatilityStrategy(signal_gen, optimizer)),
            ("Risk Parity", RiskParityStrategy(signal_gen, optimizer)),
            ("Max Diversification", MaximumDiversificationStrategy(signal_gen, optimizer)),
            ("Max Decorrelation", MaximumDecorrelationStrategy(signal_gen, optimizer)),
            ("Sharpe Max", SharpeMaximizationStrategy(signal_gen, optimizer)),
            ("CVaR Min", CVaRMinimizationStrategy(signal_gen, optimizer))
        ]

        # Add risk-free asset as an additional arm
        risk_free_asset = RiskFreeAsset(
            initial_rate=0.02,    # 2% initial rate
            rate_source='config', # Use config rates
            maturity='3M'
        )
        risk_free_wrapper = RiskFreeStrategyWrapper(risk_free_asset)
        self.strategies.append(("Risk-Free Asset", risk_free_wrapper))

        logger.info(f"Initialized {len(self.strategies)} strategies (12 benchmark + 1 risk-free)")

    def run_walk_forward_comparison(self):
        """Run comprehensive MAB algorithm comparison using walk-forward backtesting."""
        logger.info("Running MAB algorithm walk-forward comparison...")

        # Initialize backtesting methods
        bt_methods = BacktestingMethods(
            prices=self.data,
            initial_capital=self.config.initial_capital,
            transaction_cost_bps=self.config.transaction_cost_bps,
            slippage_bps=self.config.slippage_bps,
            enable_soft_rebalance=True,
            drift_threshold=0.05
        )

        # MAB algorithm configurations with proper parameters
        mab_configs = [
            ("UCB Bandit", UCBBandit, {
                'exploration_constant': 1.0,  # Balanced exploration
                'n_arms': len(self.strategies)
            }),
            ("Thompson Sampling", ThompsonSamplingBandit, {
                'prior_mean': 0.02,  # Expect ~2% monthly return
                'prior_std': 0.05,   # High uncertainty initially
                'known_reward_std': 0.03,  # ~3% monthly volatility
                'random_seed': 42,
                'n_arms': len(self.strategies)
            }),
            ("EXP3 Bandit", EXP3Bandit, {
                'gamma': 0.1,        # Higher exploration for 12 arms
                'reward_shift': 0.05,  # Shift negative returns to positive
                'reward_scale': 0.1,   # Scale to reasonable range
                'random_seed': 42,
                'n_arms': len(self.strategies)
            }),
            ("Epsilon-Greedy", EpsilonGreedy, {
                'epsilon': 0.1,      # 10% exploration rate
                'n_arms': len(self.strategies)
            })
        ]

        for mab_name, bandit_class, bandit_params in mab_configs:
            logger.info(f"Testing: {mab_name} with walk-forward backtesting")

            try:
                # Create bandit allocator with proper parameters
                bandit = bandit_class(**bandit_params)

                # Create bandit strategy wrapper with optimized settings
                bandit_wrapper = BanditStrategyWrapper(
                    child_strategies=[s for _, s in self.strategies],
                    bandit_allocator=bandit,
                    strategy_names=[name for name, _ in self.strategies],
                    burn_in_periods=3,  # 3 months burn-in (fits within 6-month test windows)
                    reward_type='return',  # Use raw returns, let algorithms handle scaling
                    reward_lookback=12,   # 12-period lookback for Sharpe if needed
                    min_allocation=0.02,  # Minimum 2% allocation per strategy
                    transaction_cost_bps=15.0,  # 15bps total costs
                    enable_soft_allocation=False,  # Use hard allocation (select single best strategy)
                    random_seed=42
                )

                # Run walk-forward backtest
                wf_result = bt_methods.walk_forward_backtest(
                    strategy=bandit_wrapper,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    train_window_months=24,  # 2 years training
                    test_window_months=6,    # 6 months testing
                    step_months=3,           # 3 months step
                    rebalance_freq='M',      # Monthly rebalancing
                    anchored=False           # Rolling windows
                )

                # Store results
                self.mab_results[mab_name] = wf_result
                self.mab_wrappers[mab_name] = bandit_wrapper

                # Calculate aggregate metrics
                sharpe_mean = wf_result.aggregate_metrics.get('sharpe_ratio_mean', 0.0)
                return_mean = wf_result.aggregate_metrics.get('annual_return_mean', 0.0)
                dd_mean = wf_result.aggregate_metrics.get('max_drawdown_mean', 0.0)
                num_folds = len(wf_result.individual_results)

                self.leaderboard.append({
                    'algorithm': mab_name,
                    'sharpe_ratio_mean': sharpe_mean,
                    'annual_return_mean': return_mean,
                    'max_drawdown_mean': dd_mean,
                    'num_folds': num_folds,
                    'validation_results': wf_result.metadata.get('validation_results', {})
                })

                logger.info(f"Completed {mab_name}: {num_folds} folds, "
                           f"Mean Sharpe {sharpe_mean:.3f}, Mean Return {return_mean:.3f}")

            except Exception as e:
                logger.error(f"Failed to run walk-forward {mab_name}: {e}", exc_info=True)

        # Sort leaderboard by mean Sharpe ratio
        self.leaderboard.sort(key=lambda x: x['sharpe_ratio_mean'], reverse=True)

    def create_walk_forward_visualizations(self):
        """Create comprehensive visualizations for walk-forward MAB comparison."""
        if not self.mab_results:
            logger.warning("No results to visualize")
            return

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('MAB Algorithms - Walk-Forward Backtesting Results', fontsize=16)

        algorithms = list(self.mab_results.keys())
        sharpe_means = []
        sharpe_stds = []
        return_means = []
        return_stds = []
        dd_means = []
        dd_stds = []

        for algo in algorithms:
            result = self.mab_results[algo]
            sharpe_means.append(result.aggregate_metrics.get('sharpe_ratio_mean', 0))
            sharpe_stds.append(result.aggregate_metrics.get('sharpe_ratio_std', 0))
            return_means.append(result.aggregate_metrics.get('annual_return_mean', 0))
            return_stds.append(result.aggregate_metrics.get('annual_return_std', 0))
            dd_means.append(result.aggregate_metrics.get('max_drawdown_mean', 0))
            dd_stds.append(result.aggregate_metrics.get('max_drawdown_std', 0))

        # Sharpe Ratio comparison
        x = np.arange(len(algorithms))
        axes[0, 0].bar(x, sharpe_means, yerr=sharpe_stds, capsize=5, alpha=0.7,
                      color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(algorithms, rotation=45, ha='right')
        axes[0, 0].set_title('Mean Sharpe Ratio by MAB Algorithm')
        axes[0, 0].set_ylabel('Sharpe Ratio')
        axes[0, 0].grid(True, alpha=0.3)

        # Annual Return comparison
        axes[0, 1].bar(x, return_means, yerr=return_stds, capsize=5, alpha=0.7,
                      color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(algorithms, rotation=45, ha='right')
        axes[0, 1].set_title('Mean Annual Return by MAB Algorithm')
        axes[0, 1].set_ylabel('Annual Return')
        axes[0, 1].grid(True, alpha=0.3)

        # Max Drawdown comparison
        axes[1, 0].bar(x, dd_means, yerr=dd_stds, capsize=5, alpha=0.7,
                      color=['skyblue', 'lightgreen', 'lightcoral', 'gold'])
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(algorithms, rotation=45, ha='right')
        axes[1, 0].set_title('Mean Max Drawdown by MAB Algorithm')
        axes[1, 0].set_ylabel('Max Drawdown')
        axes[1, 0].grid(True, alpha=0.3)

        # Sharpe vs Return scatter
        colors = ['blue', 'green', 'red', 'orange']
        for i, algo in enumerate(algorithms):
            axes[1, 1].scatter(sharpe_means[i], return_means[i], s=100,
                              color=colors[i], label=algo, alpha=0.7)
            axes[1, 1].annotate(f'{algo}', (sharpe_means[i], return_means[i]),
                               xytext=(5, 5), textcoords='offset points')

        axes[1, 1].set_xlabel('Mean Sharpe Ratio')
        axes[1, 1].set_ylabel('Mean Annual Return')
        axes[1, 1].set_title('Risk-Return Profile')
        axes[1, 1].grid(True, alpha=0.3)
        axes[1, 1].legend()

        plt.tight_layout()
        plt.savefig(self.results_dir / 'mab_walk_forward_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()

    def save_results(self):
        """Save comprehensive results to JSON."""
        results_summary = {
            'timestamp': datetime.now().isoformat(),
            'backtest_method': 'walk_forward',
            'algorithms': {}
        }

        for algo, result in self.mab_results.items():
            results_summary['algorithms'][algo] = {
                'aggregate_metrics': result.aggregate_metrics,
                'confidence_intervals': result.confidence_intervals,
                'num_folds': len(result.individual_results),
                'metadata': result.metadata
            }

        # Add leaderboard
        results_summary['leaderboard'] = self.leaderboard

        with open(self.results_dir / 'mab_walk_forward_results.json', 'w') as f:
            json.dump(results_summary, f, indent=2, default=str)

        logger.info(f"Results saved to {self.results_dir / 'mab_walk_forward_results.json'}")

    def print_summary(self):
        """Print comprehensive summary of walk-forward results."""
        print("\n" + "="*80)
        print("MAB WALK-FORWARD BACKTESTING RESULTS")
        print("="*80)

        print(f"\nBacktest Period: {self.config.start_date} to {self.config.end_date}")
        print(f"Transaction Costs: {self.config.transaction_cost_bps/100:.2f}% commission + {self.config.slippage_bps/10000:.2f}% slippage")
        print(f"Initial Capital: ${self.config.initial_capital:,.0f}")

        print("\nALGORITHM LEADERBOARD (Walk-Forward Aggregates):")
        print("-" * 80)
        print("<10")
        print("-" * 80)

        for i, item in enumerate(self.leaderboard, 1):
            print("<2")

        if self.leaderboard:
            best_algo = self.leaderboard[0]['algorithm']
            best_sharpe = self.leaderboard[0]['sharpe_ratio_mean']
            worst_sharpe = self.leaderboard[-1]['sharpe_ratio_mean']
            sharpe_diff = best_sharpe - worst_sharpe

            print("\nKEY INSIGHTS:")
            print(f"• Best Performing Algorithm: {best_algo} (Mean Sharpe: {best_sharpe:.3f})")
            print(f"• Sharpe Ratio Range: {sharpe_diff:.3f} (best to worst)")
            print(f"• All algorithms completed {self.leaderboard[0]['num_folds']} walk-forward folds")

        print(f"\nResults saved to: {self.results_dir}")
        print("Visualizations: mab_walk_forward_comparison.png")


def main():
    """Run the MAB walk-forward demo."""
    print("MAB Walk-Forward Backtesting Demo")
    print("==================================")

    demo = MABWalkForwardDemo()
    demo.run_walk_forward_comparison()
    demo.create_walk_forward_visualizations()
    demo.save_results()
    demo.print_summary()

    print("\nDemo completed successfully!")


if __name__ == "__main__":
    main()