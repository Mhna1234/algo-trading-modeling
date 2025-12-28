"""
MAB Comparison Demo - Multi-Armed Bandit Algorithm Comparison
===============================================================

This demo compares four MAB algorithms (UCB, Thompson Sampling, EXP3, Epsilon-Greedy)
using the 12 benchmark strategies as arms. Each MAB algorithm dynamically
allocates capital across the strategies based on learned performance.

Key Features:
- 12 benchmark strategies as MAB arms
- Proper reward scaling for each algorithm
- Comprehensive performance tracking
- Allocation evolution visualization
- Learning curve analysis
- Risk-adjusted performance metrics

Algorithms Compared:
1. UCB (Upper Confidence Bound): Deterministic, balances exploration/exploitation
2. Thompson Sampling: Bayesian, samples from posterior distributions
3. EXP3: Adversarial, handles non-stationary environments
4. Epsilon-Greedy: Simple exploration strategy with fixed exploration rate

Backtesting Approach:
- Full dataset backtesting (not walk-forward) to allow continuous learning
- Quarterly rebalancing with soft thresholds
- Transaction cost awareness
- Risk-free asset integration

Output:
- Performance comparison across MAB algorithms
- Allocation evolution over time
- Learning effectiveness metrics
- Strategy contribution analysis
- Comprehensive visualizations

Author: MAB Comparison Demo
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
from typing import Dict, List, Tuple
import logging

# Import project modules
from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine, PortfolioResult
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
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
from src.bandits.epsilon_greedy import EpsilonGreedy
from src.config_loader import load_trading_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('results/mab_comparison.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)


class MABComparisonDemo:
    """
    Comprehensive MAB algorithm comparison using benchmark strategies as arms.
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

        logger.info(f"Initialized {len(self.strategies)} benchmark strategies")

    def run_mab_comparison(self):
        """Run comprehensive MAB algorithm comparison."""
        logger.info("Running MAB algorithm comparison...")

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
                'random_seed': 42,
                'n_arms': len(self.strategies)
            })
        ]

        for mab_name, bandit_class, bandit_params in mab_configs:
            logger.info(f"Testing: {mab_name}")

            try:
                # Create bandit allocator with proper parameters
                bandit = bandit_class(**bandit_params)

                # Create bandit strategy wrapper with optimized settings
                bandit_wrapper = BanditStrategyWrapper(
                    child_strategies=[s for _, s in self.strategies],
                    bandit_allocator=bandit,
                    strategy_names=[name for name, _ in self.strategies],
                    burn_in_periods=6,  # 6 quarters burn-in
                    reward_type='return',  # Use raw returns, let algorithms handle scaling
                    reward_lookback=12,   # 12-period lookback for Sharpe if needed
                    min_allocation=0.02,  # Minimum 2% allocation per strategy
                    transaction_cost_bps=15.0,  # 15bps total costs
                    enable_soft_allocation=True,  # Allow soft allocation
                    random_seed=42
                )

                # Initialize portfolio engine
                portfolio_engine = PortfolioEngine(
                    prices=self.data,
                    initial_capital=self.config.initial_capital,
                    transaction_cost_bps=self.config.transaction_cost_bps,
                    slippage_bps=self.config.slippage_bps
                )

                # Run backtest (full period, not walk-forward for learning continuity)
                result = portfolio_engine.run_backtest(
                    strategy_wrapper=bandit_wrapper,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    rebalance_freq='Q',  # Quarterly rebalancing
                    soft_rebalance=True,
                    drift_threshold=0.05,  # 5% threshold
                    backtest_method='vanilla'  # Full period backtest for learning
                )

                # Store results
                self.mab_results[mab_name] = result
                self.mab_wrappers[mab_name] = bandit_wrapper

                # Calculate metrics
                final_value = result.equity_curve.iloc[-1]
                total_return = (final_value / self.config.initial_capital) - 1.0
                sharpe = result.summary_metrics.get('sharpe_ratio', 0.0)
                max_dd = result.summary_metrics.get('max_drawdown', 0.0)

                self.leaderboard.append({
                    'algorithm': mab_name,
                    'final_value': final_value,
                    'total_return': total_return,
                    'sharpe_ratio': sharpe,
                    'max_drawdown': max_dd,
                    'annual_return': result.summary_metrics.get('annual_return', 0.0),
                    'annual_volatility': result.summary_metrics.get('annual_volatility', 0.0)
                })

                logger.info(".2f"
                           ".3f"
                           ".3f")

            except Exception as e:
                logger.error(f"Failed to run {mab_name}: {e}", exc_info=True)

        # Sort leaderboard by Sharpe ratio
        self.leaderboard.sort(key=lambda x: x['sharpe_ratio'], reverse=True)

    def create_comprehensive_visualizations(self):
        """Create comprehensive visualizations for MAB comparison."""
        if not self.mab_results:
            return

        logger.info("Creating comprehensive MAB visualizations...")

        # Set up color scheme
        colors = plt.cm.tab10(np.linspace(0, 1, len(self.mab_results)))
        algo_colors = {name: colors[i] for i, name in enumerate(self.mab_results.keys())}

        # 1. NAV Comparison - All MAB algorithms
        fig, ax = plt.subplots(figsize=(16, 10))
        for algo_name, result in self.mab_results.items():
            ax.plot(result.equity_curve.index, result.equity_curve.values,
                   label=algo_name, color=algo_colors[algo_name], linewidth=2.5)

        ax.set_title('MAB Algorithm Performance Comparison - Net Asset Value', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        nav_plot = self.results_dir / 'mab_nav_comparison.png'
        plt.savefig(nav_plot, dpi=300, bbox_inches='tight')
        logger.info(f"NAV comparison saved to {nav_plot}")
        plt.close()

        # 2. Normalized Performance (start at 1.0)
        fig, ax = plt.subplots(figsize=(16, 10))
        for algo_name, result in self.mab_results.items():
            normalized = result.equity_curve / result.equity_curve.iloc[0]
            ax.plot(normalized.index, normalized.values,
                   label=algo_name, color=algo_colors[algo_name], linewidth=2.5)

        ax.set_title('MAB Algorithm Performance Comparison - Normalized Returns', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Normalized Value (Starting at $1.00)')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        norm_plot = self.results_dir / 'mab_normalized_performance.png'
        plt.savefig(norm_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Normalized performance saved to {norm_plot}")
        plt.close()

        # 3. Allocation Evolution - Heatmaps for each algorithm
        for algo_name, wrapper in self.mab_wrappers.items():
            self._create_allocation_heatmap(algo_name, wrapper, algo_colors[algo_name])

        # 4. Strategy Allocation Over Time - Line plots
        for algo_name, wrapper in self.mab_wrappers.items():
            self._create_allocation_evolution(algo_name, wrapper, algo_colors[algo_name])

        # 5. Learning Effectiveness - Allocation concentration
        self._create_learning_effectiveness_plot(algo_colors)

        # 6. Risk-Return Scatter Plot
        self._create_risk_return_scatter(algo_colors)

        # 7. Performance Summary Dashboard
        self._create_performance_dashboard(algo_colors)

        logger.info("All MAB visualizations created successfully!")

    def _create_allocation_heatmap(self, algo_name, wrapper, color):
        """Create allocation heatmap for an algorithm."""
        allocations_df = wrapper.get_strategy_allocations()

        if allocations_df.empty:
            logger.warning(f"No allocation data for {algo_name}")
            return

        # Create heatmap
        fig, ax = plt.subplots(figsize=(18, 10))

        # Prepare data for heatmap
        alloc_data = allocations_df.T  # Transpose for time x strategies
        strategy_names = [name[:15] + '...' if len(name) > 15 else name
                         for name in wrapper.strategy_names]

        # Create heatmap
        sns.heatmap(alloc_data, cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Allocation Weight'})

        ax.set_title(f'{algo_name} - Strategy Allocation Heatmap', fontsize=16)
        ax.set_xlabel('Time Period')
        ax.set_ylabel('Strategy')
        ax.set_yticklabels(strategy_names)

        plt.tight_layout()
        heatmap_plot = self.results_dir / f'mab_{algo_name.lower().replace(" ", "_")}_heatmap.png'
        plt.savefig(heatmap_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Allocation heatmap saved to {heatmap_plot}")
        plt.close()

    def _create_allocation_evolution(self, algo_name, wrapper, color):
        """Create allocation evolution line plot."""
        allocations_df = wrapper.get_strategy_allocations()

        if allocations_df.empty:
            return

        fig, ax = plt.subplots(figsize=(16, 10))

        # Plot allocation evolution for each strategy
        for i, strategy_name in enumerate(wrapper.strategy_names):
            ax.plot(allocations_df.index, allocations_df.iloc[:, i],
                   label=strategy_name, linewidth=2)

        ax.set_title(f'{algo_name} - Strategy Allocation Evolution', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Allocation Weight')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        evolution_plot = self.results_dir / f'mab_{algo_name.lower().replace(" ", "_")}_evolution.png'
        plt.savefig(evolution_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Allocation evolution saved to {evolution_plot}")
        plt.close()

    def _create_learning_effectiveness_plot(self, algo_colors):
        """Create plot showing learning effectiveness (allocation concentration)."""
        fig, ax = plt.subplots(figsize=(16, 10))

        for algo_name, wrapper in self.mab_wrappers.items():
            allocations_df = wrapper.get_strategy_allocations()
            if not allocations_df.empty:
                # Calculate allocation concentration (1 - entropy)
                # Higher values = more concentrated allocations
                concentrations = []
                for _, row in allocations_df.iterrows():
                    # Remove zero allocations for entropy calculation
                    allocs = row[row > 0.01].values
                    if len(allocs) > 0:
                        # Normalize to sum to 1
                        allocs = allocs / allocs.sum()
                        # Calculate entropy
                        entropy = -np.sum(allocs * np.log(allocs + 1e-10))
                        # Convert to concentration (1 - normalized entropy)
                        max_entropy = np.log(len(allocs))
                        concentration = 1 - (entropy / max_entropy) if max_entropy > 0 else 1
                        concentrations.append(concentration)
                    else:
                        concentrations.append(0)

                ax.plot(allocations_df.index[:len(concentrations)], concentrations,
                       label=algo_name, color=algo_colors[algo_name], linewidth=2)

        ax.set_title('MAB Learning Effectiveness - Allocation Concentration', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Concentration (0=Uniform, 1=Single Strategy)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        learning_plot = self.results_dir / 'mab_learning_effectiveness.png'
        plt.savefig(learning_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Learning effectiveness plot saved to {learning_plot}")
        plt.close()

    def _create_risk_return_scatter(self, algo_colors):
        """Create risk-return scatter plot."""
        fig, ax = plt.subplots(figsize=(12, 8))

        for item in self.leaderboard:
            algo_name = item['algorithm']
            annual_return = item['annual_return']
            annual_vol = item['annual_volatility']
            sharpe = item['sharpe_ratio']

            ax.scatter(annual_vol, annual_return,
                      s=200, c=[sharpe], cmap='RdYlGn',
                      label=f"{algo_name} (Sharpe: {sharpe:.2f})",
                      edgecolors='black', linewidth=2)

        ax.set_title('MAB Algorithms - Risk-Return Profile', fontsize=16)
        ax.set_xlabel('Annual Volatility')
        ax.set_ylabel('Annual Return')
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap='RdYlGn')
        sm.set_array([item['sharpe_ratio'] for item in self.leaderboard])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label('Sharpe Ratio')

        plt.tight_layout()
        scatter_plot = self.results_dir / 'mab_risk_return_scatter.png'
        plt.savefig(scatter_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Risk-return scatter saved to {scatter_plot}")
        plt.close()

    def _create_performance_dashboard(self, algo_colors):
        """Create comprehensive performance dashboard."""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('MAB Algorithm Comparison Dashboard', fontsize=16)

        # 1. Sharpe Ratio Comparison
        algorithms = [item['algorithm'] for item in self.leaderboard]
        sharpe_ratios = [item['sharpe_ratio'] for item in self.leaderboard]

        bars = axes[0, 0].bar(range(len(algorithms)), sharpe_ratios,
                              color=[algo_colors[algo] for algo in algorithms])
        axes[0, 0].set_title('Sharpe Ratio Comparison')
        axes[0, 0].set_ylabel('Sharpe Ratio')
        axes[0, 0].set_xticks(range(len(algorithms)))
        axes[0, 0].set_xticklabels(algorithms, rotation=45, ha='right')

        # Add value labels on bars
        for bar, value in zip(bars, sharpe_ratios):
            axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                           '.2f', ha='center', va='bottom')

        # 2. Total Return Comparison
        total_returns = [item['total_return'] for item in self.leaderboard]

        bars = axes[0, 1].bar(range(len(algorithms)), total_returns,
                              color=[algo_colors[algo] for algo in algorithms])
        axes[0, 1].set_title('Total Return Comparison')
        axes[0, 1].set_ylabel('Total Return')
        axes[0, 1].set_xticks(range(len(algorithms)))
        axes[0, 1].set_xticklabels(algorithms, rotation=45, ha='right')

        for bar, value in zip(bars, total_returns):
            axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                           '.1%', ha='center', va='bottom')

        # 3. Maximum Drawdown Comparison
        max_drawdowns = [-item['max_drawdown'] for item in self.leaderboard]  # Negative for visualization

        bars = axes[0, 2].bar(range(len(algorithms)), max_drawdowns,
                              color=[algo_colors[algo] for algo in algorithms])
        axes[0, 2].set_title('Maximum Drawdown Comparison')
        axes[0, 2].set_ylabel('Max Drawdown (%)')
        axes[0, 2].set_xticks(range(len(algorithms)))
        axes[0, 2].set_xticklabels(algorithms, rotation=45, ha='right')

        for bar, value in zip(bars, max_drawdowns):
            axes[0, 2].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                           '.1%', ha='center', va='bottom')

        # 4. Final Portfolio Value
        final_values = [item['final_value'] for item in self.leaderboard]

        bars = axes[1, 0].bar(range(len(algorithms)), final_values,
                              color=[algo_colors[algo] for algo in algorithms])
        axes[1, 0].set_title('Final Portfolio Value')
        axes[1, 0].set_ylabel('Portfolio Value ($)')
        axes[1, 0].set_xticks(range(len(algorithms)))
        axes[1, 0].set_xticklabels(algorithms, rotation=45, ha='right')

        for bar, value in zip(bars, final_values):
            axes[1, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                           ',.0f', ha='center', va='bottom')

        # 5. Learning Timeline (simplified)
        axes[1, 1].text(0.5, 0.5, 'MAB Learning Analysis\n\n• UCB: Deterministic exploration\n• Thompson: Bayesian sampling\n• EXP3: Adversarial optimization\n\nEach algorithm adapts allocations\nbased on observed performance',
                       transform=axes[1, 1].transAxes, ha='center', va='center',
                       fontsize=12, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
        axes[1, 1].set_title('Algorithm Characteristics')
        axes[1, 1].set_xlim(0, 1)
        axes[1, 1].set_ylim(0, 1)
        axes[1, 1].axis('off')

        # 6. Summary Statistics Table
        axes[1, 2].axis('off')
        summary_text = "Performance Summary\n\n"
        for item in self.leaderboard:
            summary_text += f"{item['algorithm']}:\n"
            summary_text += f"  Sharpe: {item['sharpe_ratio']:.2f}\n"
            summary_text += f"  Return: {item['total_return']:.1%}\n"
            summary_text += f"  Max DD: {item['max_drawdown']:.1%}\n\n"

        axes[1, 2].text(0.05, 0.95, summary_text, transform=axes[1, 2].transAxes,
                       fontsize=10, verticalalignment='top',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))

        plt.tight_layout()
        dashboard_plot = self.results_dir / 'mab_performance_dashboard.png'
        plt.savefig(dashboard_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Performance dashboard saved to {dashboard_plot}")
        plt.close()

    def save_results_to_json(self):
        """Save comprehensive results to JSON file."""
        results_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'description': 'MAB Algorithm Comparison Results',
                'strategies_used': [name for name, _ in self.strategies],
                'backtest_period': {
                    'start': self.config.start_date,
                    'end': self.config.end_date
                },
                'parameters': {
                    'initial_capital': self.config.initial_capital,
                    'transaction_costs_bps': self.config.transaction_cost_bps,
                    'rebalance_frequency': 'quarterly',
                    'burn_in_periods': 6
                }
            },
            'leaderboard': self.leaderboard,
            'algorithm_details': {}
        }

        # Add detailed results for each algorithm
        for algo_name, wrapper in self.mab_wrappers.items():
            allocations_df = wrapper.get_strategy_allocations()

            results_data['algorithm_details'][algo_name] = {
                'bandit_type': wrapper.bandit_allocator.__class__.__name__,
                'allocation_history': allocations_df.to_dict('records') if not allocations_df.empty else [],
                'strategy_contributions': {},
                'learning_metrics': {}
            }

            # Add strategy-specific performance data
            for i, (strategy_name, _) in enumerate(self.strategies):
                tracker = wrapper.trackers[i]
                results_data['algorithm_details'][algo_name]['strategy_contributions'][strategy_name] = {
                    'total_returns': tracker.returns,
                    'allocations': tracker.allocations,
                    'performance_metrics': tracker.get_recent_metrics()
                }

        # Save to file
        results_file = self.results_dir / 'mab_comparison_results.json'
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)

        logger.info(f"Results saved to {results_file}")

    def print_summary_report(self):
        """Print comprehensive summary report."""
        print("\n" + "="*80)
        print("MAB ALGORITHM COMPARISON RESULTS")
        print("="*80)

        print(f"\nBacktest Period: {self.config.start_date} to {self.config.end_date}")
        print(f"Strategies as Arms: {len(self.strategies)} benchmark strategies")
        print(f"Rebalancing: Quarterly with 5% soft rebalance threshold")
        print(f"Transaction Costs: {self.config.transaction_cost_bps/100:.2f}% commission + {self.config.slippage_bps/10000:.2f}% slippage")
        print(f"Initial Capital: ${self.config.initial_capital:,.0f}")
        print(f"Burn-in Period: 6 quarters (1.5 years)")

        print(f"\nAlgorithms Tested: {len(self.mab_results)} MAB algorithms")

        print("\n" + "-"*80)
        print("LEADERBOARD (Ranked by Sharpe Ratio)")
        print("-"*80)
        print("<25")
        print("-"*80)

        for i, item in enumerate(self.leaderboard, 1):
            print("<2d")

        print("\n" + "-"*80)
        print("ALGORITHM CHARACTERISTICS")
        print("-"*80)

        algo_descriptions = {
            'UCB Bandit': 'Deterministic exploration using upper confidence bounds. Balances exploration/exploitation with mathematical guarantees.',
            'Thompson Sampling': 'Bayesian sampling from posterior distributions. Naturally balances uncertainty and expected rewards.',
            'EXP3': 'Adversarial algorithm for non-stationary environments. Uses exponential weighting with forced exploration.'
        }

        for algo_name, description in algo_descriptions.items():
            print(f"\n{algo_name}:")
            print(f"  {description}")

        print("\n" + "-"*80)
        print("KEY FINDINGS")
        print("-"*80)

        if len(self.leaderboard) >= 1:
            best_algo = self.leaderboard[0]['algorithm']
            best_sharpe = self.leaderboard[0]['sharpe_ratio']
            print(f"• Best Performing Algorithm: {best_algo} (Sharpe: {best_sharpe:.2f})")

        if len(self.leaderboard) >= 2:
            sharpe_diff = self.leaderboard[0]['sharpe_ratio'] - self.leaderboard[-1]['sharpe_ratio']
            print(f"• Sharpe Ratio Range: {sharpe_diff:.2f} (best to worst)")

        print("• All algorithms use the same 12 benchmark strategies as arms")
        print("• Performance differences reflect learning effectiveness")
        print("• EXP3 may excel in volatile market conditions")
        print("• UCB provides theoretical guarantees but may be conservative")
        print("• Thompson Sampling offers Bayesian adaptability")

        print(f"\nVisualization files saved to: {self.results_dir}/")
        print("- mab_nav_comparison.png: Performance comparison")
        print("- mab_normalized_performance.png: Normalized returns")
        print("- mab_*_heatmap.png: Allocation heatmaps for each algorithm")
        print("- mab_*_evolution.png: Allocation evolution over time")
        print("- mab_learning_effectiveness.png: Learning progress")
        print("- mab_risk_return_scatter.png: Risk-return profiles")
        print("- mab_performance_dashboard.png: Comprehensive summary")


def main():
    """Run the MAB comparison demo."""
    print("MAB Comparison Demo - Multi-Armed Bandit Algorithm Comparison")
    print("="*60)

    # Initialize and run demo
    demo = MABComparisonDemo()

    try:
        # Run the comparison
        demo.run_mab_comparison()

        # Create visualizations
        demo.create_comprehensive_visualizations()

        # Save results
        demo.save_results_to_json()

        # Print summary
        demo.print_summary_report()

        print("\n" + "="*60)
        print("MAB Comparison Demo completed successfully!")
        print("="*60)

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\nDemo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())