"""
Demo: 12 Benchmark Strategies Comparison (FAST VERSION)
========================================================

This demo runs a quick backtest of all 12 required benchmark strategies
optimized for speed (< 10 seconds on normal laptop).

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

FAST MODE OPTIMIZATIONS:
- Reduced time window (last 6 months)
- Weekly rebalancing (vs daily)
- Reduced asset universe (10 assets)
- Minimal logging
- Compact summary table (no heavy plots)
- Optional synthetic data for testing

Configuration:
- Period: Last 6 months
- Rebalancing: Weekly (reduces computation by 80%)
- Initial capital: $100,000
- Transaction costs: 0.1%
- Universe: 10 assets (subset)

Usage:
    python demo_12_strategies_fast.py              # Use real data
    python demo_12_strategies_fast.py --synthetic  # Use synthetic data for testing
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
import argparse
import logging
from typing import Dict, List, Optional
from pathlib import Path

# Import project modules
from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine
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

# Configure minimal logging
logging.basicConfig(
    level=logging.WARNING,  # Reduced logging for speed
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_data(n_assets: int = 10, n_days: int = 126) -> pd.DataFrame:
    """
    Generate synthetic price data for testing.
    
    Parameters
    ----------
    n_assets : int
        Number of assets
    n_days : int
        Number of trading days
        
    Returns
    -------
    pd.DataFrame
        Synthetic price data
    """
    np.random.seed(42)
    
    # Generate date range
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq='B')
    
    # Generate asset names
    assets = [f'ASSET_{i:02d}' for i in range(n_assets)]
    
    # Generate synthetic returns (correlated)
    mean_returns = np.random.uniform(-0.0005, 0.0015, n_assets)
    volatilities = np.random.uniform(0.01, 0.03, n_assets)
    
    # Create correlation matrix
    corr_matrix = np.random.uniform(0.3, 0.7, (n_assets, n_assets))
    corr_matrix = (corr_matrix + corr_matrix.T) / 2
    np.fill_diagonal(corr_matrix, 1.0)
    
    # Generate correlated returns
    returns = np.random.multivariate_normal(
        mean=mean_returns,
        cov=np.outer(volatilities, volatilities) * corr_matrix,
        size=n_days
    )
    
    # Convert to prices (starting at 100)
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(returns, axis=0)),
        index=dates,
        columns=assets
    )
    
    return prices


def create_strategy_instances_fast(
    signal_generator: Strategy,
    optimizer: PortfolioOptimizer
) -> Dict[str, object]:
    """
    Create instances of all 12 benchmark strategies (optimized for speed).
    
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
            lookback=63, target_quintile=5
        ),
        '4. Quintile Low Vol': QuintileLowVolatilityStrategy(
            signal_generator, optimizer, 
            lookback=63, target_quintile=1
        ),
        '5. Mean Reversion': MeanReversionStrategy(
            signal_generator, optimizer, 
            lookback=10
        ),
        '6. GMVP': GlobalMinimumVarianceStrategy(
            signal_generator, optimizer, 
            lookback=63, max_weight=0.5
        ),
        '7. Inverse Volatility': InverseVolatilityStrategy(
            signal_generator, optimizer, 
            lookback=21
        ),
        '8. Risk Parity': RiskParityStrategy(
            signal_generator, optimizer, 
            lookback=63, max_weight=0.4
        ),
        '9. Max Diversification': MaximumDiversificationStrategy(
            signal_generator, optimizer, 
            lookback=63, max_weight=0.5
        ),
        '10. Max Decorrelation': MaximumDecorrelationStrategy(
            signal_generator, optimizer, 
            lookback=63, max_weight=0.5
        ),
        '11. Sharpe Maximization': SharpeMaximizationStrategy(
            signal_generator, optimizer, 
            lookback=63, max_weight=0.3
        ),
        '12. CVaR Minimization': CVaRMinimizationStrategy(
            signal_generator, optimizer, 
            lookback=63, alpha=0.95, max_weight=0.3
        ),
    }
    
    return strategies


def run_backtest_fast(
    strategy_instance,
    strategy_name: str,
    prices: pd.DataFrame,
    initial_capital: float = 100000.0,
    rebalance_frequency: int = 5,
    transaction_cost: float = 0.001
) -> Optional[Dict]:
    """
    Run fast backtest for a single strategy.
    
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
        Days between rebalances (5 = weekly)
    transaction_cost : float
        Transaction cost rate
        
    Returns
    -------
    Optional[Dict]
        Backtest results or None if failed
    """
    try:
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
            rebalance_freq='W'  # Weekly rebalancing
        )
        
        # Compute metrics
        equity = result.equity_curve
        returns = equity.pct_change().dropna()
        
        n_years = len(equity) / 252
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / n_years) - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe = (returns.mean() * 252 - 0.02) / (returns.std() * np.sqrt(252))
        
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_drawdown = drawdown.min()
        
        calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
        
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino = (returns.mean() * 252 - 0.02) / downside_std if downside_std > 0 else 0
        
        win_rate = (returns > 0).sum() / len(returns)
        
        return {
            'name': strategy_name,
            'result': result,
            'equity_curve': equity,
            'table_metrics': {
                'Strategy': strategy_name,
                'Total Return': f'{total_return:.2%}',
                'CAGR': f'{cagr:.2%}',
                'Volatility': f'{volatility:.2%}',
                'Sharpe': f'{sharpe:.3f}',
                'Max DD': f'{max_drawdown:.2%}',
                'Status': '✓'
            },
            'full_metrics': {
                'total_return': total_return,
                'cagr': cagr,
                'volatility': volatility,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar,
                'sortino_ratio': sortino,
                'win_rate': win_rate
            }
        }
        
    except Exception as e:
        return {
            'name': strategy_name,
            'result': None,
            'equity_curve': None,
            'table_metrics': {
                'Strategy': strategy_name,
                'Total Return': 'N/A',
                'CAGR': 'N/A',
                'Volatility': 'N/A',
                'Sharpe': 'N/A',
                'Max DD': 'N/A',
                'Status': f'✗ {str(e)[:30]}'
            },
            'full_metrics': None
        }


def print_table(results: List[Dict]):
    """Print results in a formatted table."""
    if not results:
        print("No results to display")
        return
    
    # Calculate column widths
    headers = list(results[0].keys())
    col_widths = {}
    
    for header in headers:
        col_widths[header] = max(
            len(header),
            max(len(str(r[header])) for r in results)
        )
    
    # Print header
    header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
    print(header_line)
    print("-" * len(header_line))
    
    # Print rows
    for result in results:
        row = " | ".join(str(result[h]).ljust(col_widths[h]) for h in headers)
        print(row)


def plot_nav_curves_fast(results: List[Dict], output_dir: Path):
    """Plot NAV curves for all strategies."""
    plt.figure(figsize=(16, 10))
    
    for result in results:
        if result['equity_curve'] is not None:
            equity = result['equity_curve']
            # Normalize to start at 100
            normalized = (equity / equity.iloc[0]) * 100
            plt.plot(normalized.index, normalized.values, 
                    label=result['name'], linewidth=2, alpha=0.8)
    
    plt.title('NAV Comparison: 12 Benchmark Strategies (Fast Mode)', 
              fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Portfolio Value (Normalized to 100)', fontsize=12)
    plt.legend(loc='best', fontsize=10, ncol=2)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = output_dir / '12_strategies_fast_nav_curves.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


def plot_metrics_comparison_fast(metrics_df: pd.DataFrame, output_dir: Path):
    """Plot performance metrics comparison."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Performance Metrics Comparison: 12 Benchmark Strategies (Fast Mode)', 
                 fontsize=16, fontweight='bold')
    
    metrics_to_plot = [
        ('cagr', 'CAGR', True),
        ('sharpe_ratio', 'Sharpe Ratio', True),
        ('volatility', 'Volatility (Ann.)', False),
        ('max_drawdown', 'Max Drawdown', False),
        ('calmar_ratio', 'Calmar Ratio', True),
        ('sortino_ratio', 'Sortino Ratio', True)
    ]
    
    for idx, (metric, title, higher_better) in enumerate(metrics_to_plot):
        ax = axes[idx // 3, idx % 3]
        
        data = metrics_df[metric].sort_values(ascending=not higher_better)
        colors = ['green' if higher_better else 'red' 
                 if i == 0 else 'blue' for i in range(len(data))]
        
        data.plot(kind='barh', ax=ax, color=colors, alpha=0.7)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel('Value', fontsize=10)
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, v in enumerate(data.values):
            if metric in ['cagr', 'max_drawdown']:
                label = f'{v:.1%}'
            else:
                label = f'{v:.3f}'
            ax.text(v, i, label, va='center', fontsize=9)
    
    plt.tight_layout()
    output_file = output_dir / '12_strategies_fast_metrics_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


def plot_correlation_heatmap_fast(results: List[Dict], output_dir: Path):
    """Plot correlation heatmap of strategy returns."""
    returns_df = pd.DataFrame()
    
    for result in results:
        if result['equity_curve'] is not None:
            equity = result['equity_curve']
            returns = equity.pct_change().dropna()
            returns_df[result['name']] = returns
    
    if returns_df.empty:
        return
    
    corr_matrix = returns_df.corr()
    
    plt.figure(figsize=(14, 12))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8})
    plt.title('Strategy Returns Correlation Matrix (Fast Mode)', 
              fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / '12_strategies_fast_correlation_heatmap.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Fast demo of 12 benchmark strategies'
    )
    parser.add_argument(
        '--synthetic',
        action='store_true',
        help='Use synthetic data for testing (no real data needed)'
    )
    args = parser.parse_args()
    
    print("=" * 80)
    print("12 BENCHMARK STRATEGIES - FAST MODE")
    if args.synthetic:
        print("MODE: SYNTHETIC DATA (Testing)")
    else:
        print("MODE: REAL DATA (Last 6 months)")
    print("=" * 80)
    print()
    
    start_time = time.time()
    
    # Load or generate data
    if args.synthetic:
        print("Generating synthetic data...")
        prices = generate_synthetic_data(n_assets=10, n_days=126)
        print(f"✓ Generated: {len(prices)} dates, {len(prices.columns)} assets")
    else:
        print("Loading real data...")
        full_data, all_prices = load_preprocessed_data()
        
        # Use last 6 months, subset of assets
        prices = all_prices.iloc[-126:]  # Last ~6 months
        prices = prices[prices.columns[:10]]  # First 10 assets
        print(f"✓ Loaded: {len(prices)} dates, {len(prices.columns)} assets")
    
    print(f"Period: {prices.index[0].date()} to {prices.index[-1].date()}")
    
    # Create signal generator and optimizer
    signal_generator = Strategy(prices)
    optimizer = PortfolioOptimizer(
        returns=signal_generator.returns,
        risk_free_rate=0.02,
        max_weight=0.5,
        min_weight=0.0,
        transaction_cost=0.001
    )
    
    # Create all 12 strategy instances
    strategies = create_strategy_instances_fast(signal_generator, optimizer)
    
    # Run backtests
    print(f"\nRunning {len(strategies)} strategies with WEEKLY rebalancing...")
    print("-" * 80)
    
    results = []
    table_results = []
    for strategy_name, strategy_instance in strategies.items():
        result = run_backtest_fast(
            strategy_instance=strategy_instance,
            strategy_name=strategy_name,
            prices=prices,
            initial_capital=100000.0,
            rebalance_frequency=5,  # Weekly
            transaction_cost=0.001
        )
        
        if result is not None:
            results.append(result)
            table_results.append(result['table_metrics'])
            status = result['table_metrics']['Status']
            print(f"  {status} {strategy_name}")
    
    # Print summary table
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    print_table(table_results)
    
    # Count successes
    successes = sum(1 for r in results if r['table_metrics']['Status'] == '✓')
    print()
    print(f"Completed: {successes}/{len(strategies)} strategies")
    
    elapsed = time.time() - start_time
    print(f"Execution time: {elapsed:.2f} seconds")
    
    # Validation check
    if elapsed > 10:
        print("\n⚠ WARNING: Execution time exceeded 10 seconds target")
    
    # Generate visualizations and save metrics
    output_dir = Path('visualizations')
    output_dir.mkdir(exist_ok=True)
    
    print("\n" + "=" * 80)
    print("GENERATING VISUALIZATIONS AND REPORTS")
    print("=" * 80)
    
    # Filter successful results
    successful_results = [r for r in results if r['full_metrics'] is not None]
    
    if successful_results:
        # Create metrics DataFrame
        metrics_data = {}
        for result in successful_results:
            metrics_data[result['name']] = result['full_metrics']
        metrics_df = pd.DataFrame(metrics_data).T
        
        # 1. Plot NAV curves
        plot_nav_curves_fast(successful_results, output_dir)
        print("  ✓ NAV curves saved")
        
        # 2. Plot metrics comparison
        plot_metrics_comparison_fast(metrics_df, output_dir)
        print("  ✓ Metrics comparison saved")
        
        # 3. Plot correlation heatmap
        plot_correlation_heatmap_fast(successful_results, output_dir)
        print("  ✓ Correlation heatmap saved")
        
        # 4. Save metrics to CSV
        csv_file = output_dir / '12_strategies_fast_metrics.csv'
        metrics_df.to_csv(csv_file)
        print(f"  ✓ Metrics CSV saved")
        
        # 5. Save metrics to JSON
        json_file = output_dir / '12_strategies_fast_metrics.json'
        metrics_dict = metrics_df.to_dict(orient='index')
        with open(json_file, 'w') as f:
            json.dump(metrics_dict, f, indent=2, default=str)
        print(f"  ✓ Metrics JSON saved")
        
        print("\nOUTPUT FILES:")
        print(f"  - {output_dir / '12_strategies_fast_nav_curves.png'}")
        print(f"  - {output_dir / '12_strategies_fast_metrics_comparison.png'}")
        print(f"  - {output_dir / '12_strategies_fast_correlation_heatmap.png'}")
        print(f"  - {csv_file}")
        print(f"  - {json_file}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
