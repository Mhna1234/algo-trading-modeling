"""
Benchmark Strategies Walk-Forward Backtest Demo

This script runs comprehensive monthly walk-forward backtesting for all
benchmark portfolio strategies using real market data.

Features:
- Uses real preprocessed market data from the project
- Monthly rebalancing with walk-forward validation
- Portfolio engine tracking of all metrics
- Generates comprehensive plots and CSV results
- Compares all 9 benchmark strategies

Output:
- CSV files with equity curves, weights, and metrics
- Performance comparison plots
- Risk-adjusted return analysis

Author: Algo Trading Team
Date: January 2026
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List
import logging

# Import project modules
from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine, PortfolioResult
from src.signal_generator import Strategy
from src.strategies.benchmarks import (
    EqualWeightBenchmark,
    InverseVolatilityBenchmark,
    InverseVarianceBenchmark,
    GlobalMinVarianceBenchmark,
    MaxDecorrelationBenchmark,
    TopKReturnBenchmark,
    TopKSharpeBenchmark,
    RiskParityBenchmark,
    MostDiversifiedBenchmark,
    list_benchmarks
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)


class BenchmarkStrategyBacktest:
    """
    Comprehensive backtesting system for benchmark strategies.
    """
    
    def __init__(self, 
                 start_date: str = '2016-01-01',
                 end_date: str = '2025-11-30',
                 initial_capital: float = 1_000_000,
                 transaction_cost_bps: float = 10.0,
                 slippage_bps: float = 5.0):
        """
        Initialize backtest system.
        
        Parameters
        ----------
        start_date : str
            Backtest start date
        end_date : str
            Backtest end date
        initial_capital : float
            Starting capital
        transaction_cost_bps : float
            Transaction costs in basis points
        slippage_bps : float
            Slippage in basis points
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        
        # Results storage
        self.results = {}
        self.results_dir = Path('results')
        self.viz_dir = Path('visualizations')
        self.results_dir.mkdir(exist_ok=True)
        self.viz_dir.mkdir(exist_ok=True)
        
        # Load data
        self._load_data()
        
        # Setup strategies
        self._setup_strategies()
    
    def _load_data(self):
        """Load and prepare market data."""
        logger.info("Loading preprocessed data...")
        
        try:
            full_data, price_data = load_preprocessed_data()
            
            # Filter date range
            self.data = price_data.loc[self.start_date:self.end_date]
            
            logger.info(f"Loaded data: {len(self.data)} periods, {len(self.data.columns)} assets")
            logger.info(f"Date range: {self.data.index[0]} to {self.data.index[-1]}")
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _setup_strategies(self):
        """Initialize all benchmark strategies."""
        logger.info("Setting up benchmark strategies...")
        
        # Create signal generator (data container)
        signal_gen = Strategy(self.data)
        
        # Initialize all benchmark strategies
        self.strategies = [
            ("Equal Weight", EqualWeightBenchmark(signal_gen)),
            ("Inverse Volatility", InverseVolatilityBenchmark(signal_gen)),
            ("Inverse Variance", InverseVarianceBenchmark(signal_gen)),
            ("Global Min Variance", GlobalMinVarianceBenchmark(signal_gen)),
            ("Max Decorrelation", MaxDecorrelationBenchmark(signal_gen)),
            ("Top-10 Return", TopKReturnBenchmark(signal_gen, top_k=10)),
            ("Top-10 Sharpe", TopKSharpeBenchmark(signal_gen, top_k=10)),
            ("Risk Parity", RiskParityBenchmark(signal_gen, max_iter=500)),
            ("Most Diversified", MostDiversifiedBenchmark(signal_gen, max_iter=500)),
        ]
        
        logger.info(f"Initialized {len(self.strategies)} benchmark strategies")
    
    def run_backtests(self):
        """Run monthly walk-forward backtests for all strategies."""
        logger.info("=" * 80)
        logger.info("STARTING MONTHLY WALK-FORWARD BACKTESTS")
        logger.info("=" * 80)
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info(f"Rebalance Frequency: Monthly")
        logger.info(f"Transaction Costs: {self.transaction_cost_bps} bps")
        logger.info(f"Slippage: {self.slippage_bps} bps")
        logger.info("")
        
        for strategy_name, strategy in self.strategies:
            logger.info(f"Running backtest: {strategy_name}")
            
            try:
                # Initialize portfolio engine
                portfolio_engine = PortfolioEngine(
                    prices=self.data,
                    initial_capital=self.initial_capital,
                    transaction_cost_bps=self.transaction_cost_bps,
                    slippage_bps=self.slippage_bps
                )
                
                # Run monthly walk-forward backtest
                result = portfolio_engine.run_backtest(
                    strategy_wrapper=strategy,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    rebalance_freq='M',  # Monthly rebalancing
                    backtest_method='walk_forward'
                )
                
                # Store results
                self.results[strategy_name] = result
                
                # Log key metrics
                final_value = result.equity_curve.iloc[-1]
                total_return = (final_value / self.initial_capital - 1) * 100
                sharpe = self._calculate_sharpe(result)
                max_dd = self._calculate_max_drawdown(result)
                
                logger.info(f"  ✓ Final Value: ${final_value:,.0f}")
                logger.info(f"    Total Return: {total_return:.2f}%")
                logger.info(f"    Sharpe Ratio: {sharpe:.2f}")
                logger.info(f"    Max Drawdown: {max_dd:.2%}")
                logger.info("")
                
            except Exception as e:
                logger.error(f"  ✗ Error backtesting {strategy_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        logger.info(f"Completed {len(self.results)} backtests")
        logger.info("=" * 80)
    
    def _calculate_sharpe(self, result: PortfolioResult, rf_rate: float = 0.04) -> float:
        """Calculate Sharpe ratio."""
        returns = result.returns_series.dropna()
        if len(returns) == 0:
            return 0.0
        
        annual_return = returns.mean() * 252
        annual_vol = returns.std() * np.sqrt(252)
        
        if annual_vol == 0:
            return 0.0
        
        return (annual_return - rf_rate) / annual_vol
    
    def _calculate_max_drawdown(self, result: PortfolioResult) -> float:
        """Calculate maximum drawdown."""
        peak = result.equity_curve.cummax()
        drawdown = (result.equity_curve / peak) - 1.0
        return drawdown.min()
    
    def _calculate_calmar(self, result: PortfolioResult) -> float:
        """Calculate Calmar ratio."""
        returns = result.returns_series.dropna()
        if len(returns) == 0:
            return 0.0
        
        n_years = len(returns) / 252
        total_return = (result.equity_curve.iloc[-1] / result.equity_curve.iloc[0]) - 1
        annual_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
        max_dd = abs(self._calculate_max_drawdown(result))
        
        return annual_return / max_dd if max_dd > 0 else 0.0
    
    def generate_summary_table(self) -> pd.DataFrame:
        """Generate summary table of all strategies."""
        logger.info("Generating summary table...")
        
        summary_data = []
        
        for strategy_name, result in self.results.items():
            returns = result.returns_series.dropna()
            
            if len(returns) == 0:
                continue
            
            # Calculate metrics
            total_return = (result.equity_curve.iloc[-1] / self.initial_capital - 1) * 100
            n_years = len(returns) / 252
            annual_return = ((1 + total_return/100) ** (1/n_years) - 1) * 100 if n_years > 0 else 0
            annual_vol = returns.std() * np.sqrt(252) * 100
            sharpe = self._calculate_sharpe(result)
            max_dd = self._calculate_max_drawdown(result) * 100
            calmar = self._calculate_calmar(result)
            
            # Winning days
            win_rate = (returns > 0).sum() / len(returns) * 100
            
            summary_data.append({
                'Strategy': strategy_name,
                'Total Return (%)': f"{total_return:.2f}",
                'Annual Return (%)': f"{annual_return:.2f}",
                'Annual Vol (%)': f"{annual_vol:.2f}",
                'Sharpe Ratio': f"{sharpe:.2f}",
                'Max Drawdown (%)': f"{max_dd:.2f}",
                'Calmar Ratio': f"{calmar:.2f}",
                'Win Rate (%)': f"{win_rate:.2f}",
                'Final Value ($)': f"{result.equity_curve.iloc[-1]:,.0f}"
            })
        
        df = pd.DataFrame(summary_data)
        
        # Save to CSV
        csv_path = self.results_dir / 'benchmark_strategies_summary.csv'
        df.to_csv(csv_path, index=False)
        logger.info(f"Summary table saved to {csv_path}")
        
        return df
    
    def export_equity_curves(self):
        """Export equity curves to CSV."""
        logger.info("Exporting equity curves...")
        
        # Combine all equity curves
        equity_curves = pd.DataFrame()
        
        for strategy_name, result in self.results.items():
            equity_curves[strategy_name] = result.equity_curve
        
        # Save to CSV
        csv_path = self.results_dir / 'benchmark_strategies_equity_curves.csv'
        equity_curves.to_csv(csv_path)
        logger.info(f"Equity curves saved to {csv_path}")
        
        return equity_curves
    
    def export_weights_history(self):
        """Export weight histories to CSV."""
        logger.info("Exporting weight histories...")
        
        for strategy_name, result in self.results.items():
            # Get weights history
            weights_df = result.weights_history
            
            # Save to CSV
            filename = strategy_name.replace(" ", "_").lower()
            csv_path = self.results_dir / f'weights_{filename}.csv'
            weights_df.to_csv(csv_path)
        
        logger.info(f"Weight histories saved to {self.results_dir}/weights_*.csv")
    
    def plot_equity_curves(self):
        """Plot equity curves for all strategies."""
        logger.info("Generating equity curve plot...")
        
        fig, ax = plt.subplots(figsize=(16, 10))
        
        for strategy_name, result in self.results.items():
            ax.plot(result.equity_curve.index, result.equity_curve.values,
                   label=strategy_name, linewidth=2)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Portfolio Value ($)', fontsize=12)
        ax.set_title('Benchmark Strategies: Equity Curves (Monthly Rebalancing)', 
                     fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))
        
        plt.tight_layout()
        plot_path = self.viz_dir / 'benchmark_equity_curves.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Equity curve plot saved to {plot_path}")
        plt.close()
    
    def plot_drawdowns(self):
        """Plot drawdowns for all strategies."""
        logger.info("Generating drawdown plot...")
        
        fig, ax = plt.subplots(figsize=(16, 10))
        
        for strategy_name, result in self.results.items():
            peak = result.equity_curve.cummax()
            drawdown = (result.equity_curve / peak) - 1.0
            ax.plot(drawdown.index, drawdown.values * 100,
                   label=strategy_name, linewidth=2)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Drawdown (%)', fontsize=12)
        ax.set_title('Benchmark Strategies: Drawdowns', 
                     fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        plt.tight_layout()
        plot_path = self.viz_dir / 'benchmark_drawdowns.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Drawdown plot saved to {plot_path}")
        plt.close()
    
    def plot_performance_comparison(self):
        """Plot performance comparison bar charts."""
        logger.info("Generating performance comparison plot...")
        
        # Collect metrics
        strategies = []
        sharpes = []
        returns = []
        volatilities = []
        
        for strategy_name, result in self.results.items():
            returns_series = result.returns_series.dropna()
            if len(returns_series) == 0:
                continue
            
            strategies.append(strategy_name)
            sharpes.append(self._calculate_sharpe(result))
            
            total_ret = (result.equity_curve.iloc[-1] / self.initial_capital - 1) * 100
            returns.append(total_ret)
            
            vol = returns_series.std() * np.sqrt(252) * 100
            volatilities.append(vol)
        
        # Create subplots
        fig, axes = plt.subplots(1, 3, figsize=(20, 6))
        
        # Sharpe Ratio
        axes[0].barh(strategies, sharpes, color='steelblue')
        axes[0].set_xlabel('Sharpe Ratio', fontsize=12)
        axes[0].set_title('Risk-Adjusted Returns', fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3, axis='x')
        
        # Total Returns
        colors = ['green' if r > 0 else 'red' for r in returns]
        axes[1].barh(strategies, returns, color=colors, alpha=0.7)
        axes[1].set_xlabel('Total Return (%)', fontsize=12)
        axes[1].set_title('Cumulative Returns', fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3, axis='x')
        
        # Volatility
        axes[2].barh(strategies, volatilities, color='coral')
        axes[2].set_xlabel('Annual Volatility (%)', fontsize=12)
        axes[2].set_title('Risk (Volatility)', fontsize=14, fontweight='bold')
        axes[2].grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        plot_path = self.viz_dir / 'benchmark_performance_comparison.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Performance comparison plot saved to {plot_path}")
        plt.close()
    
    def plot_risk_return_scatter(self):
        """Plot risk-return scatter plot."""
        logger.info("Generating risk-return scatter plot...")
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for strategy_name, result in self.results.items():
            returns_series = result.returns_series.dropna()
            if len(returns_series) == 0:
                continue
            
            # Calculate annualized metrics
            n_years = len(returns_series) / 252
            total_return = (result.equity_curve.iloc[-1] / self.initial_capital - 1)
            annual_return = ((1 + total_return) ** (1/n_years) - 1) * 100 if n_years > 0 else 0
            annual_vol = returns_series.std() * np.sqrt(252) * 100
            
            ax.scatter(annual_vol, annual_return, s=200, alpha=0.6, label=strategy_name)
        
        ax.set_xlabel('Annual Volatility (%)', fontsize=12)
        ax.set_ylabel('Annual Return (%)', fontsize=12)
        ax.set_title('Risk-Return Scatter Plot', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = self.viz_dir / 'benchmark_risk_return_scatter.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"Risk-return scatter saved to {plot_path}")
        plt.close()
    
    def generate_all_outputs(self):
        """Generate all outputs: tables, plots, and CSV files."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("GENERATING OUTPUTS")
        logger.info("=" * 80)
        
        # Generate summary table
        summary_df = self.generate_summary_table()
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        print(summary_df.to_string(index=False))
        print("")
        
        # Export data
        self.export_equity_curves()
        self.export_weights_history()
        
        # Generate plots
        self.plot_equity_curves()
        self.plot_drawdowns()
        self.plot_performance_comparison()
        self.plot_risk_return_scatter()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ ALL OUTPUTS GENERATED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Results saved to: {self.results_dir.absolute()}")
        logger.info(f"Plots saved to: {self.viz_dir.absolute()}")
        logger.info("")


def simple_example_usage():
    """Direct computation of weights given mu and Sigma."""
    print("=" * 70)
    print("EXAMPLE 1: Direct Weight Computation")
    print("=" * 70)
    print()
    
    # Create sample data
    n = 5
    assets = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META']
    
    mu = np.array([0.12, 0.10, 0.11, 0.13, 0.09])  # Expected returns
    
    # Create covariance matrix
    vol = np.array([0.25, 0.22, 0.24, 0.28, 0.26])
    corr = np.array([
        [1.00, 0.60, 0.70, 0.50, 0.55],
        [0.60, 1.00, 0.65, 0.45, 0.50],
        [0.70, 0.65, 1.00, 0.55, 0.60],
        [0.50, 0.45, 0.55, 1.00, 0.50],
        [0.55, 0.50, 0.60, 0.50, 1.00],
    ])
    
    D = np.diag(vol)
    Sigma = D @ corr @ D
    
    # Import benchmark strategies
    from src.strategies.benchmarks import (
        EqualWeightBenchmark,
        GlobalMinVarianceBenchmark,
        RiskParityBenchmark,
        MostDiversifiedBenchmark
    )
    
    # Mock strategy object
    class MockStrategy:
        def __init__(self):
            self.assets = assets
    
    mock = MockStrategy()
    
    # Test each strategy
    strategies = [
        ("Equal Weight", EqualWeightBenchmark(mock)),
        ("Global Min Variance", GlobalMinVarianceBenchmark(mock)),
        ("Risk Parity", RiskParityBenchmark(mock, max_iter=500)),
        ("Most Diversified", MostDiversifiedBenchmark(mock, max_iter=500)),
    ]
    
    for name, strategy in strategies:
        weights = strategy.compute_weights(mu, Sigma)
        
        # Compute portfolio metrics
        port_return = weights @ mu
        port_vol = np.sqrt(weights @ Sigma @ weights)
        sharpe = port_return / port_vol
        
        print(f"\n{name}:")
        print(f"  Weights: {dict(zip(assets, weights))}")
        print(f"  Return: {port_return:.2%}, Vol: {port_vol:.2%}, Sharpe: {sharpe:.2f}")


def example_with_dataframe():
    """Example using pandas DataFrames."""
    print("\n")
    print("=" * 70)
    print("EXAMPLE 2: Using with Pandas DataFrames")
    print("=" * 70)
    print()
    
    # Create sample data
    assets = ['SPY', 'TLT', 'GLD', 'VNQ', 'EEM']
    
    # Expected returns as Series
    mu = pd.Series({
        'SPY': 0.10,
        'TLT': 0.04,
        'GLD': 0.05,
        'VNQ': 0.08,
        'EEM': 0.12
    })
    
    # Covariance as DataFrame
    Sigma_data = np.array([
        [0.0400, 0.0020, 0.0010, 0.0150, 0.0200],
        [0.0020, 0.0100, 0.0005, 0.0010, 0.0015],
        [0.0010, 0.0005, 0.0225, 0.0020, 0.0025],
        [0.0150, 0.0010, 0.0020, 0.0361, 0.0180],
        [0.0200, 0.0015, 0.0025, 0.0180, 0.0625],
    ])
    
    Sigma = pd.DataFrame(Sigma_data, index=assets, columns=assets)
    
    from src.strategies.benchmarks import (
        InverseVolatilityBenchmark,
        GlobalMinVarianceBenchmark,
        MaxDecorrelationBenchmark
    )
    
    # Mock strategy
    class MockStrategy:
        def __init__(self):
            self.assets = assets
    
    mock = MockStrategy()
    
    strategies = [
        InverseVolatilityBenchmark(mock),
        GlobalMinVarianceBenchmark(mock),
        MaxDecorrelationBenchmark(mock),
    ]
    
    results = []
    
    for strategy in strategies:
        # Compute weights (convert to numpy)
        weights_np = strategy.compute_weights(mu.values, Sigma.values)
        
        # Create Series
        weights = pd.Series(weights_np, index=assets)
        
        results.append({
            'Strategy': strategy.name,
            **{asset: f"{w:.2%}" for asset, w in weights.items()}
        })
    
    # Display as table
    df = pd.DataFrame(results).set_index('Strategy')
    print(df)
    print()


def example_comparison():
    """Compare all benchmarks on same data."""
    print("=" * 70)
    print("EXAMPLE 3: Benchmark Strategy Comparison")
    print("=" * 70)
    print()
    
    # Create realistic test data
    n = 10
    np.random.seed(123)
    
    mu = np.random.randn(n) * 0.05 + 0.08
    
    # Create covariance
    A = np.random.randn(n, n) * 0.1
    Sigma = A @ A.T + 0.01 * np.eye(n)
    vol = np.sqrt(np.diag(Sigma))
    target_vol = np.random.uniform(0.10, 0.30, n)
    D = np.diag(target_vol / vol)
    Sigma = D @ Sigma @ D
    
    assets = [f"Asset{i+1}" for i in range(n)]
    
    from src.strategies.benchmarks import list_benchmarks
    
    # Mock strategy
    class MockStrategy:
        def __init__(self):
            self.assets = assets
    
    mock = MockStrategy()
    
    # Get all benchmarks
    all_benchmarks = list_benchmarks()
    
    results = []
    
    for name, strategy_class in all_benchmarks.items():
        # Create strategy instance
        if 'top_k' in name:
            strategy = strategy_class(mock, top_k=5)
        elif name in ['risk_parity', 'most_diversified']:
            strategy = strategy_class(mock, max_iter=500)
        else:
            strategy = strategy_class(mock)
        
        # Compute weights
        weights = strategy.compute_weights(mu, Sigma)
        
        # Compute metrics
        port_ret = weights @ mu
        port_vol = np.sqrt(weights @ Sigma @ weights)
        sharpe = port_ret / port_vol if port_vol > 0 else 0
        
        # Count non-zero positions
        n_positions = np.sum(weights > 1e-4)
        max_weight = np.max(weights)
        
        results.append({
            'Strategy': strategy.name,
            'Return': f"{port_ret:.2%}",
            'Vol': f"{port_vol:.2%}",
            'Sharpe': f"{sharpe:.2f}",
            'N_Pos': n_positions,
            'Max_Wt': f"{max_weight:.1%}"
        })
    
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print()


def simple_example_usage():
    """Quick example for documentation."""
    print("\n" + "=" * 80)
    print("SIMPLE USAGE EXAMPLE")
    print("=" * 80)
    print("\nThis shows how to use benchmark strategies programmatically:\n")
    
    print("from src.strategies.benchmarks import GlobalMinVarianceBenchmark")
    print("from src.portfolio_engine import PortfolioEngine")
    print("from src.signal_generator import Strategy")
    print()
    print("# Load data")
    print("signal_gen = Strategy(price_data)")
    print()
    print("# Create strategy")
    print("gmvp = GlobalMinVarianceBenchmark(signal_gen)")
    print()
    print("# Run backtest")
    print("engine = PortfolioEngine(price_data, initial_capital=1_000_000)")
    print("result = engine.run_backtest(")
    print("    strategy_wrapper=gmvp,")
    print("    start_date='2016-01-01',")
    print("    end_date='2025-11-30',")
    print("    rebalance_freq='M'")
    print(")")
    print()
    print("# Access results")
    print("print(result.equity_curve)")
    print("print(result.weights_history)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Show simple usage example
    simple_example_usage()
    
    # Run comprehensive backtest
    print("\n" + "=" * 80)
    print("COMPREHENSIVE BENCHMARK STRATEGY BACKTEST")
    print("=" * 80)
    print("\nStarting comprehensive monthly walk-forward backtest...")
    print("This will test all 9 benchmark strategies on real market data.")
    print("")
    
    try:
        # Initialize backtest system
        backtest = BenchmarkStrategyBacktest(
            start_date='2016-01-01',
            end_date='2025-11-30',
            initial_capital=1_000_000,
            transaction_cost_bps=10.0,  # 0.10% commission
            slippage_bps=5.0             # 0.05% slippage
        )
        
        # Run all backtests
        backtest.run_backtests()
        
        # Generate all outputs
        backtest.generate_all_outputs()
        
        print("\n" + "=" * 80)
        print("SUCCESS: BENCHMARK BACKTEST COMPLETED!")
        print("=" * 80)
        print("\nCheck the following directories for results:")
        print(f"  CSV files: {backtest.results_dir.absolute()}")
        print(f"  Plots: {backtest.viz_dir.absolute()}")
        print("\nGenerated files:")
        print("  - benchmark_strategies_summary.csv")
        print("  - benchmark_strategies_equity_curves.csv")
        print("  - weights_*.csv (one per strategy)")
        print("  - benchmark_equity_curves.png")
        print("  - benchmark_drawdowns.png")
        print("  - benchmark_performance_comparison.png")
        print("  - benchmark_risk_return_scatter.png")
        print("")
        
    except Exception as e:
        print(f"\nERROR: Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
