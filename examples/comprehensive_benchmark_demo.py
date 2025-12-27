"""
Comprehensive Strategy Benchmarking Demo
==========================================

This demo runs comprehensive backtesting for:
- All 12 individual benchmark strategies
- 3 Multi-Armed Bandit algorithms (UCB, Thompson, EXP3)

Each strategy follows the quarterly rebalancing algorithm:
- Soft rebalancing with 5% drift threshold
- Transaction costs: 0.15% (0.10% commission + 0.05% slippage)
- Quarterly rebalancing over 10 years (40 quarters)
- Daily performance tracking during holding periods

Output:
- Individual strategy performance metrics
- MAB algorithm performance comparison
- Comprehensive leaderboard ranked by Sharpe ratio
- API-ready JSON exports for all results

Author: Comprehensive Benchmarking Demo
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
from src.config_loader import load_trading_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('results/comprehensive_benchmark.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)


class ComprehensiveBenchmark:
    """
    Comprehensive benchmarking system for all strategies and MAB algorithms.
    """

    def __init__(self):
        self.config = load_trading_config()
        self.results_dir = Path('results')
        self.results_dir.mkdir(exist_ok=True)

        # Initialize data and components
        self._load_data()
        self._setup_strategies()

        # Results storage
        self.individual_results = {}
        self.mab_results = {}
        self.mab_wrappers = {}  # Store MAB wrappers for allocation data
        self.leaderboard = []

    def _load_data(self):
        """Load and prepare market data."""
        logger.info("Loading preprocessed data...")
        full_data, price_data = load_preprocessed_data()

        # Filter date range
        self.data = price_data.loc[self.config.start_date:self.config.end_date]
        logger.info(f"Loaded data: {len(self.data)} periods, {len(self.data.columns)} assets")

    def _setup_strategies(self):
        """Initialize all individual strategies."""
        logger.info("Setting up individual strategies...")

        signal_gen = Strategy(self.data)
        optimizer = PortfolioOptimizer()

        # Individual strategies
        self.individual_strategies = [
            ("Buy & Hold", BuyAndHoldStrategy(signal_gen, optimizer)),
            ("Equal Weight", EqualWeightStrategy(signal_gen, optimizer)),
            ("Quintile Factor", QuintileFactorStrategy(signal_gen, optimizer)),
            ("Low Volatility", QuintileLowVolatilityStrategy(signal_gen, optimizer)),
            ("Mean Reversion", MeanReversionStrategy(signal_gen, optimizer)),
            ("Global Min Variance", GlobalMinimumVarianceStrategy(signal_gen, optimizer)),
            ("Inverse Volatility", InverseVolatilityStrategy(signal_gen, optimizer)),
            ("Risk Parity", RiskParityStrategy(signal_gen, optimizer)),
            ("Max Diversification", MaximumDiversificationStrategy(signal_gen, optimizer)),
            ("Max Decorrelation", MaximumDecorrelationStrategy(signal_gen, optimizer)),
            ("Sharpe Max", SharpeMaximizationStrategy(signal_gen, optimizer)),
            ("CVaR Min", CVaRMinimizationStrategy(signal_gen, optimizer))
        ]

        logger.info(f"Initialized {len(self.individual_strategies)} individual strategies")

    def run_individual_strategy_backtests(self):
        """Run backtests for all individual strategies."""
        logger.info("Running individual strategy backtests...")

        for strategy_name, strategy in self.individual_strategies:
            logger.info(f"Backtesting: {strategy_name}")

            try:
                # Initialize portfolio engine with quarterly settings
                portfolio_engine = PortfolioEngine(
                    prices=self.data,
                    initial_capital=self.config.initial_capital,
                    transaction_cost_bps=self.config.transaction_cost_bps,
                    slippage_bps=self.config.slippage_bps
                )

                # Run quarterly backtest with soft rebalancing
                result = portfolio_engine.run_backtest(
                    strategy_wrapper=strategy,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    rebalance_freq='Q',  # Quarterly rebalancing
                    soft_rebalance=True,
                    drift_threshold=0.05,  # 5% threshold
                    backtest_method='walk_forward'
                )

                # Store results
                self.individual_results[strategy_name] = result
                logger.info(f"✓ {strategy_name}: ${result.equity_curve.iloc[-1]:,.0f} final value")

            except Exception as e:
                logger.error(f"✗ Error backtesting {strategy_name}: {e}")
                continue

        logger.info(f"Completed {len(self.individual_results)} individual strategy backtests")

    def run_mab_backtests(self):
        """Run backtests for all MAB algorithms."""
        logger.info("Running MAB algorithm backtests...")

        mab_configs = [
            ("UCB Bandit", UCBBandit),
            ("Thompson Sampling", ThompsonSamplingBandit),
            ("EXP3 Bandit", EXP3Bandit)
        ]

        for mab_name, bandit_class in mab_configs:
            logger.info(f"Backtesting: {mab_name}")

            try:
                # Create bandit allocator
                bandit = bandit_class(n_arms=len(self.individual_strategies))

                # Create bandit strategy wrapper
                bandit_wrapper = BanditStrategyWrapper(
                    child_strategies=[s for _, s in self.individual_strategies],
                    bandit_allocator=bandit,
                    strategy_names=[name for name, _ in self.individual_strategies],
                    burn_in_periods=self.config.burn_in_periods,
                    enable_soft_allocation=self.config.enable_soft_allocation,
                    reward_type=self.config.reward_type,
                    exploration_constant=self.config.exploration_constant,
                    min_allocation=self.config.min_allocation
                )

                # Initialize portfolio engine
                portfolio_engine = PortfolioEngine(
                    prices=self.data,
                    initial_capital=self.config.initial_capital,
                    transaction_cost_bps=self.config.transaction_cost_bps,
                    slippage_bps=self.config.slippage_bps
                )

                # Run quarterly backtest
                result = portfolio_engine.run_backtest(
                    strategy_wrapper=bandit_wrapper,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date,
                    rebalance_freq='Q',  # Quarterly rebalancing
                    soft_rebalance=True,
                    drift_threshold=0.05,  # 5% threshold
                    backtest_method='walk_forward'
                )

                # Store results
                self.mab_results[mab_name] = result
                self.mab_wrappers[mab_name] = bandit_wrapper  # Store wrapper for allocation data
                logger.info(f"✓ {mab_name}: ${result.equity_curve.iloc[-1]:,.0f} final value")

            except Exception as e:
                logger.error(f"✗ Error backtesting {mab_name}: {e}")
                continue

        logger.info(f"Completed {len(self.mab_results)} MAB algorithm backtests")

    def calculate_comprehensive_metrics(self, result: PortfolioResult) -> Dict:
        """Calculate all required performance metrics."""
        returns = result.returns_series.dropna()

        if len(returns) == 0:
            return {}

        # Basic metrics
        total_return = (result.equity_curve.iloc[-1] / result.equity_curve.iloc[0]) - 1.0
        n_years = len(returns) / 252.0
        annual_return = (1 + total_return) ** (1 / n_years) - 1.0 if n_years > 0 else 0.0
        annual_vol = returns.std() * np.sqrt(252)

        # Sharpe ratio
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0.0

        # Maximum drawdown
        peak = result.equity_curve.cummax()
        drawdown = (result.equity_curve / peak) - 1.0
        max_drawdown = drawdown.min()

        # Win rate
        win_rate = (returns > 0).mean()

        # Profit factor
        gains = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        profit_factor = gains / losses if losses > 0 else float('inf')

        # Turnover rate (average quarterly turnover)
        if len(result.turnover_history) > 0 and isinstance(result.turnover_history.index, pd.DatetimeIndex):
            try:
                quarterly_turnover = result.turnover_history.groupby(pd.Grouper(freq='Q')).mean()
                avg_turnover = quarterly_turnover.mean()
            except Exception as e:
                logger.warning(f"Error calculating turnover: {e}. Using 0.0")
                avg_turnover = 0.0
        else:
            avg_turnover = 0.0

        # Calmar ratio
        calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0.0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_turnover': avg_turnover,
            'calmar_ratio': calmar,
            'final_value': result.equity_curve.iloc[-1],
            'total_periods': len(result.equity_curve)
        }

    def generate_leaderboard(self):
        """Generate comprehensive leaderboard ranked by Sharpe ratio."""
        logger.info("Generating performance leaderboard...")

        all_results = []

        # Add individual strategies
        for strategy_name, result in self.individual_results.items():
            metrics = self.calculate_comprehensive_metrics(result)
            if metrics:
                all_results.append({
                    'strategy': strategy_name,
                    'type': 'Individual',
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'total_return': metrics['total_return'],
                    'max_drawdown': metrics['max_drawdown'],
                    'win_rate': metrics['win_rate'],
                    'profit_factor': metrics['profit_factor'],
                    'avg_turnover': metrics['avg_turnover'],
                    'final_value': metrics['final_value']
                })

        # Add MAB algorithms
        for mab_name, result in self.mab_results.items():
            metrics = self.calculate_comprehensive_metrics(result)
            if metrics:
                all_results.append({
                    'strategy': mab_name,
                    'type': 'MAB',
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'total_return': metrics['total_return'],
                    'max_drawdown': metrics['max_drawdown'],
                    'win_rate': metrics['win_rate'],
                    'profit_factor': metrics['profit_factor'],
                    'avg_turnover': metrics['avg_turnover'],
                    'final_value': metrics['final_value']
                })

        # Sort by Sharpe ratio (descending)
        self.leaderboard = sorted(all_results, key=lambda x: x['sharpe_ratio'], reverse=True)

    def export_results(self):
        """Export all results to JSON and CSV files."""
        logger.info("Exporting comprehensive results...")

        # Prepare comprehensive results
        results_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'backtest_period': f"{self.config.start_date} to {self.config.end_date}",
                'rebalance_frequency': 'Quarterly (Q)',
                'soft_rebalance_threshold': 0.05,
                'transaction_costs': f"{self.config.transaction_cost_bps/100:.2f}% commission + {self.config.slippage_bps/10000:.2f}% slippage",
                'initial_capital': self.config.initial_capital,
                'total_strategies_tested': len(self.individual_results) + len(self.mab_results)
            },
            'leaderboard': self.leaderboard,
            'individual_strategies': {},
            'mab_algorithms': {}
        }

        # Add detailed individual strategy results
        for strategy_name, result in self.individual_results.items():
            metrics = self.calculate_comprehensive_metrics(result)
            results_data['individual_strategies'][strategy_name] = {
                'metrics': metrics,
                'equity_curve': {
                    'dates': result.equity_curve.index.strftime('%Y-%m-%d').tolist(),
                    'values': result.equity_curve.values.tolist()
                },
                'quarterly_turnover': result.turnover_history.groupby(pd.Grouper(freq='Q')).mean().tolist()
            }

        # Add detailed MAB results
        for mab_name, result in self.mab_results.items():
            metrics = self.calculate_comprehensive_metrics(result)
            results_data['mab_algorithms'][mab_name] = {
                'metrics': metrics,
                'equity_curve': {
                    'dates': result.equity_curve.index.strftime('%Y-%m-%d').tolist(),
                    'values': result.equity_curve.values.tolist()
                },
                'quarterly_turnover': result.turnover_history.groupby(pd.Grouper(freq='Q')).mean().tolist()
            }

        # Export to JSON
        json_file = self.results_dir / 'comprehensive_benchmark_results.json'
        with open(json_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        logger.info(f"Comprehensive results exported to {json_file}")

        # Export leaderboard to CSV
        if self.leaderboard:
            df = pd.DataFrame(self.leaderboard)
            csv_file = self.results_dir / 'strategy_leaderboard.csv'
            df.to_csv(csv_file, index=False)
            logger.info(f"Leaderboard exported to {csv_file}")

    def create_visualizations(self):
        """Create comprehensive performance visualizations for all 15 strategies."""
        if not self.leaderboard:
            return

        # Set up color scheme
        colors = plt.cm.tab20(np.linspace(0, 1, 15))
        strategy_colors = {}
        for i, item in enumerate(self.leaderboard):
            strategy_colors[item['strategy']] = colors[i]

        # 1. NAV (Equity Curves) - All 15 strategies
        fig, ax = plt.subplots(figsize=(16, 10))
        for item in self.leaderboard:
            strategy_name = item['strategy']
            if strategy_name in self.individual_results:
                result = self.individual_results[strategy_name]
            elif strategy_name in self.mab_results:
                result = self.mab_results[strategy_name]
            else:
                continue

            ax.plot(result.equity_curve.index, result.equity_curve.values,
                   label=strategy_name, color=strategy_colors[strategy_name], linewidth=2)

        ax.set_title('NAV (Net Asset Value) - All 15 Strategies', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        nav_plot = self.results_dir / 'comprehensive_nav_all_strategies.png'
        plt.savefig(nav_plot, dpi=300, bbox_inches='tight')
        logger.info(f"NAV plot saved to {nav_plot}")
        plt.close()

        # 2. Sharpe Ratio Curves - All strategies with rolling Sharpe
        fig, ax = plt.subplots(figsize=(16, 10))
        for item in self.leaderboard:
            strategy_name = item['strategy']
            if strategy_name in self.individual_results:
                result = self.individual_results[strategy_name]
            elif strategy_name in self.mab_results:
                result = self.mab_results[strategy_name]
            else:
                continue

            # Check if rolling_metrics exists and has sharpe column
            if (hasattr(result, 'rolling_metrics') and 
                result.rolling_metrics is not None and 
                not result.rolling_metrics.empty and 
                'sharpe' in result.rolling_metrics.columns):
                sharpe_curve = result.rolling_metrics['sharpe']
                ax.plot(sharpe_curve.index, sharpe_curve.values,
                       label=strategy_name, color=strategy_colors[strategy_name], linewidth=1.5)

        ax.set_title('Rolling Sharpe Ratio Curves - All Strategies', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Rolling Sharpe Ratio (252-day)')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        sharpe_plot = self.results_dir / 'comprehensive_sharpe_curves.png'
        plt.savefig(sharpe_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Sharpe ratio curves plot saved to {sharpe_plot}")
        plt.close()

        # 3. Drawdown Curves - All strategies
        fig, ax = plt.subplots(figsize=(16, 10))
        for item in self.leaderboard:
            strategy_name = item['strategy']
            if strategy_name in self.individual_results:
                result = self.individual_results[strategy_name]
            elif strategy_name in self.mab_results:
                result = self.mab_results[strategy_name]
            else:
                continue

            # Check if drawdown_series exists and is not empty
            if (hasattr(result, 'drawdown_series') and 
                result.drawdown_series is not None and 
                not result.drawdown_series.empty):
                ax.fill_between(result.drawdown_series.index, result.drawdown_series.values, 0,
                              alpha=0.7, color=strategy_colors[strategy_name], label=strategy_name)

        ax.set_title('Drawdown Curves - All Strategies', fontsize=16)
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown (%)')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        dd_plot = self.results_dir / 'comprehensive_drawdown_curves.png'
        plt.savefig(dd_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Drawdown curves plot saved to {dd_plot}")
        plt.close()

        # 4. Last Weights - Individual Strategies
        individual_strategies = [item for item in self.leaderboard if item['type'] == 'Individual']
        if individual_strategies:
            fig, axes = plt.subplots(4, 3, figsize=(18, 16))
            axes = axes.flatten()

            for i, item in enumerate(individual_strategies):
                if i >= 12:  # Only 12 individual strategies
                    break

                strategy_name = item['strategy']
                result = self.individual_results[strategy_name]

                # Get last weights (excluding CASH)
                last_weights = result.weights_history.iloc[-1]
                last_weights = last_weights[last_weights.index != 'CASH']
                last_weights = last_weights[last_weights > 0.001]  # Only show significant weights

                if len(last_weights) > 0:
                    axes[i].bar(range(len(last_weights)), last_weights.values)
                    axes[i].set_title(f'{strategy_name} - Last Weights')
                    axes[i].set_xlabel('Assets')
                    axes[i].set_ylabel('Weight')
                    axes[i].set_xticks(range(len(last_weights)))
                    axes[i].set_xticklabels(last_weights.index, rotation=45, ha='right')
                    axes[i].grid(True, alpha=0.3)

            # Hide empty subplots
            for j in range(i + 1, 12):
                axes[j].set_visible(False)

            plt.tight_layout()
            weights_plot = self.results_dir / 'comprehensive_last_weights_individual.png'
            plt.savefig(weights_plot, dpi=300, bbox_inches='tight')
            logger.info(f"Individual strategy weights plot saved to {weights_plot}")
            plt.close()

        # 5. MAB Strategy Allocations - Show how MAB allocates across individual strategies
        mab_strategies = [item for item in self.leaderboard if item['type'] == 'MAB']
        if mab_strategies and self.mab_wrappers:
            fig, axes = plt.subplots(1, 3, figsize=(18, 6))

            # Get strategy names from the first MAB wrapper
            first_mab_name = mab_strategies[0]['strategy']
            strategy_names = self.mab_wrappers[first_mab_name].strategy_names

            for i, item in enumerate(mab_strategies):
                mab_name = item['strategy']
                if mab_name in self.mab_wrappers:
                    wrapper = self.mab_wrappers[mab_name]
                    allocations_df = wrapper.get_strategy_allocations()

                    if not allocations_df.empty:
                        # Get last allocations
                        last_allocations = allocations_df.iloc[-1]

                        axes[i].bar(range(len(last_allocations)), last_allocations.values)
                        axes[i].set_title(f'{mab_name} - Strategy Allocations')
                        axes[i].set_xlabel('Individual Strategies')
                        axes[i].set_ylabel('Allocation Weight')
                        axes[i].set_xticks(range(len(last_allocations)))
                        axes[i].set_xticklabels(strategy_names, rotation=45, ha='right')
                        axes[i].grid(True, alpha=0.3)

            plt.tight_layout()
            mab_alloc_plot = self.results_dir / 'comprehensive_mab_allocations.png'
            plt.savefig(mab_alloc_plot, dpi=300, bbox_inches='tight')
            logger.info(f"MAB allocations plot saved to {mab_alloc_plot}")
            plt.close()

        # 6. Summary Dashboard (original 2x2 plot for comparison)
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Comprehensive Strategy Benchmark Results - Summary', fontsize=16)

        # 1. Sharpe Ratio Comparison
        strategies = [item['strategy'] for item in self.leaderboard[:10]]  # Top 10
        sharpe_ratios = [item['sharpe_ratio'] for item in self.leaderboard[:10]]

        axes[0, 0].barh(strategies[::-1], sharpe_ratios[::-1])
        axes[0, 0].set_title('Sharpe Ratio (Top 10)')
        axes[0, 0].set_xlabel('Sharpe Ratio')

        # 2. Total Return vs Max Drawdown
        total_returns = [item['total_return'] for item in self.leaderboard]
        max_drawdowns = [abs(item['max_drawdown']) for item in self.leaderboard]
        strategy_names = [item['strategy'] for item in self.leaderboard]

        scatter = axes[0, 1].scatter(total_returns, max_drawdowns,
                                    c=[item['sharpe_ratio'] for item in self.leaderboard],
                                    cmap='viridis', alpha=0.7)
        axes[0, 1].set_title('Risk-Return Profile')
        axes[0, 1].set_xlabel('Total Return')
        axes[0, 1].set_ylabel('Max Drawdown (%)')
        plt.colorbar(scatter, ax=axes[0, 1], label='Sharpe Ratio')

        # Add strategy labels for top performers
        for i, name in enumerate(strategy_names):
            if i < 5:  # Label top 5
                axes[0, 1].annotate(name, (total_returns[i], max_drawdowns[i]),
                                   xytext=(5, 5), textcoords='offset points', fontsize=8)

        # 3. Win Rate Distribution
        win_rates = [item['win_rate'] for item in self.leaderboard]
        axes[1, 0].hist(win_rates, bins=10, alpha=0.7, edgecolor='black')
        axes[1, 0].set_title('Win Rate Distribution')
        axes[1, 0].set_xlabel('Win Rate')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].axvline(np.mean(win_rates), color='red', linestyle='--',
                          label=f'Mean: {np.mean(win_rates):.2f}')
        axes[1, 0].legend()

        # 4. Equity Curves (Top 3)
        for i, item in enumerate(self.leaderboard[:3]):
            strategy_name = item['strategy']
            if strategy_name in self.individual_results:
                result = self.individual_results[strategy_name]
            elif strategy_name in self.mab_results:
                result = self.mab_results[strategy_name]
            else:
                continue

            normalized_equity = result.equity_curve / result.equity_curve.iloc[0]
            axes[1, 1].plot(normalized_equity.index, normalized_equity.values,
                           label=strategy_name, linewidth=2)

        axes[1, 1].set_title('Top 3 Strategy Performance (Normalized)')
        axes[1, 1].set_xlabel('Date')
        axes[1, 1].set_ylabel('Normalized Value')
        axes[1, 1].legend()
        axes[1, 1].tick_params(axis='x', rotation=45)

        plt.tight_layout()
        summary_plot = self.results_dir / 'comprehensive_benchmark_summary.png'
        plt.savefig(summary_plot, dpi=300, bbox_inches='tight')
        logger.info(f"Summary dashboard plot saved to {summary_plot}")
        plt.close()

        logger.info("All comprehensive plots created successfully!")

    def print_summary_report(self):
        """Print comprehensive summary report."""
        print("\n" + "="*80)
        print("COMPREHENSIVE STRATEGY BENCHMARK RESULTS")
        print("="*80)

        print(f"\nBacktest Period: {self.config.start_date} to {self.config.end_date}")
        print(f"Rebalancing: Quarterly with 5% soft rebalance threshold")
        print(f"Transaction Costs: {self.config.transaction_cost_bps/100:.2f}% commission + {self.config.slippage_bps/10000:.2f}% slippage")
        print(f"Initial Capital: ${self.config.initial_capital:,.0f}")

        print(f"\nStrategies Tested: {len(self.individual_results)} individual + {len(self.mab_results)} MAB = {len(self.individual_results) + len(self.mab_results)} total")

        print("\n" + "-"*80)
        print("LEADERBOARD (Ranked by Sharpe Ratio)")
        print("-"*80)
        print("<10")
        print("-"*80)

        for i, item in enumerate(self.leaderboard[:10], 1):
            print("<2d")

        print("\n" + "-"*80)
        print("TOP PERFORMERS BY CATEGORY")
        print("-"*80)

        # Individual strategies
        individual_top = [item for item in self.leaderboard if item['type'] == 'Individual'][:3]
        if individual_top:
            print("\nIndividual Strategies:")
            for item in individual_top:
                print("<25")

        # MAB algorithms
        mab_top = [item for item in self.leaderboard if item['type'] == 'MAB'][:3]
        if mab_top:
            print("\nMAB Algorithms:")
            for item in mab_top:
                print("<25")

        print(f"\nDetailed results exported to: results/comprehensive_benchmark_results.json")
        print(f"Leaderboard CSV: results/strategy_leaderboard.csv")
        print(f"Summary dashboard: results/comprehensive_benchmark_summary.png")
        print(f"NAV curves (all strategies): results/comprehensive_nav_all_strategies.png")
        print(f"Sharpe ratio curves: results/comprehensive_sharpe_curves.png")
        print(f"Drawdown curves: results/comprehensive_drawdown_curves.png")
        print(f"Individual strategy weights: results/comprehensive_last_weights_individual.png")
        print(f"MAB strategy allocations: results/comprehensive_mab_allocations.png")

        print("\n" + "="*80)


def main():
    """Main execution function."""
    print("Starting Comprehensive Strategy Benchmark...")

    # Initialize benchmark system
    benchmark = ComprehensiveBenchmark()

    # Run all backtests
    benchmark.run_individual_strategy_backtests()
    benchmark.run_mab_backtests()

    # Generate analysis
    benchmark.generate_leaderboard()
    benchmark.export_results()
    benchmark.create_visualizations()

    # Print summary
    benchmark.print_summary_report()

    print("\n✅ Comprehensive benchmark completed successfully!")


if __name__ == "__main__":
    main()