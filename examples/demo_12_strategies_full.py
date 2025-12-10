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
from src.strategy_wrapper import (
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set plot style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)


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
            signal_generator, optimizer, initial_method='equal'
        ),
        '2. Equal Weight': EqualWeightStrategy(
            signal_generator, optimizer
        ),
        '3. Quintile Momentum': QuintileFactorStrategy(
            signal_generator, optimizer, 
            factor='momentum', lookback=126, target_quintile=5
        ),
        '4. Quintile Low Vol': QuintileLowVolatilityStrategy(
            signal_generator, optimizer, 
            lookback=126, target_quintile=1
        ),
        '5. Mean Reversion': MeanReversionStrategy(
            signal_generator, optimizer, 
            window=21, top_k=8
        ),
        '6. GMVP': GlobalMinimumVarianceStrategy(
            signal_generator, optimizer, 
            lookback=252, max_weight=0.5
        ),
        '7. Inverse Volatility': InverseVolatilityStrategy(
            signal_generator, optimizer, 
            vol_window=63
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
            f"  ✓ {strategy_name}: "
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
        logger.error(f"  ✗ {strategy_name} FAILED: {str(e)}")
        return None


def compute_additional_metrics(equity_curve: pd.Series) -> Dict[str, float]:
    """Compute additional performance metrics."""
    returns = equity_curve.pct_change().dropna()
    
    # CAGR
    n_years = len(equity_curve) / 252
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / n_years) - 1
    
    # Volatility
    volatility = returns.std() * np.sqrt(252)
    
    # Sharpe Ratio
    sharpe = (returns.mean() * 252 - 0.02) / (returns.std() * np.sqrt(252))
    
    # Max Drawdown
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_drawdown = drawdown.min()
    
    # Calmar Ratio
    calmar = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Sortino Ratio
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (returns.mean() * 252 - 0.02) / downside_std if downside_std > 0 else 0
    
    # Win Rate
    win_rate = (returns > 0).sum() / len(returns)
    
    return {
        'cagr': cagr,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar,
        'sortino_ratio': sortino,
        'win_rate': win_rate
    }


def plot_nav_curves(results: List[Dict], output_dir: Path):
    """Plot NAV curves for all strategies."""
    plt.figure(figsize=(16, 10))
    
    for result in results:
        equity = result['equity_curve']
        # Normalize to start at 100
        normalized = (equity / equity.iloc[0]) * 100
        plt.plot(normalized.index, normalized.values, 
                label=result['name'], linewidth=2, alpha=0.8)
    
    plt.title('NAV Comparison: 12 Benchmark Strategies', fontsize=16, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Portfolio Value (Normalized to 100)', fontsize=12)
    plt.legend(loc='best', fontsize=10, ncol=2)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = output_dir / '12_strategies_nav_curves.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"NAV curves saved to: {output_file}")
    plt.close()


def plot_metrics_comparison(metrics_df: pd.DataFrame, output_dir: Path):
    """Plot performance metrics comparison."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Performance Metrics Comparison: 12 Benchmark Strategies', 
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
    output_file = output_dir / '12_strategies_metrics_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Metrics comparison saved to: {output_file}")
    plt.close()


def plot_correlation_heatmap(results: List[Dict], output_dir: Path):
    """Plot correlation heatmap of strategy returns."""
    returns_df = pd.DataFrame()
    
    for result in results:
        equity = result['equity_curve']
        returns = equity.pct_change().dropna()
        returns_df[result['name']] = returns
    
    corr_matrix = returns_df.corr()
    
    plt.figure(figsize=(14, 12))
    sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8})
    plt.title('Strategy Returns Correlation Matrix', fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    output_file = output_dir / '12_strategies_correlation_heatmap.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Correlation heatmap saved to: {output_file}")
    plt.close()


def main():
    """Main execution function."""
    print("=" * 80)
    print("12 BENCHMARK STRATEGIES - FULL BACKTEST")
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
    
    logger.info(f"\nSuccessfully completed {len(results)}/{len(strategies)} strategies")
    
    # Compute comprehensive metrics
    logger.info("Computing performance metrics...")
    metrics_data = []
    for result in results:
        metrics = compute_additional_metrics(result['equity_curve'])
        metrics['strategy'] = result['name']
        metrics_data.append(metrics)
    
    metrics_df = pd.DataFrame(metrics_data).set_index('strategy')
    
    # Create output directory
    output_dir = Path('visualizations')
    output_dir.mkdir(exist_ok=True)
    
    # Save metrics to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = output_dir / f'12_strategies_full_metrics_{timestamp}.csv'
    metrics_df.to_csv(csv_file)
    logger.info(f"Metrics saved to: {csv_file}")
    
    # Save metrics to JSON
    json_file = output_dir / f'12_strategies_full_metrics_{timestamp}.json'
    metrics_dict = metrics_df.to_dict(orient='index')
    with open(json_file, 'w') as f:
        json.dump(metrics_dict, f, indent=2, default=str)
    logger.info(f"Metrics JSON saved to: {json_file}")
    
    # Generate plots
    logger.info("Generating visualizations...")
    plot_nav_curves(results, output_dir)
    plot_metrics_comparison(metrics_df, output_dir)
    plot_correlation_heatmap(results, output_dir)
    
    # Print summary table
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    print(metrics_df.to_string())
    print()
    
    # Print top performers
    print("=" * 80)
    print("TOP PERFORMERS")
    print("=" * 80)
    print(f"\nHighest CAGR: {metrics_df['cagr'].idxmax()} ({metrics_df['cagr'].max():.2%})")
    print(f"Highest Sharpe: {metrics_df['sharpe_ratio'].idxmax()} ({metrics_df['sharpe_ratio'].max():.3f})")
    print(f"Lowest Volatility: {metrics_df['volatility'].idxmin()} ({metrics_df['volatility'].min():.2%})")
    print(f"Smallest Drawdown: {metrics_df['max_drawdown'].idxmax()} ({metrics_df['max_drawdown'].max():.2%})")
    
    elapsed = time.time() - start_time
    print(f"\n{'=' * 80}")
    print(f"Total execution time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"{'=' * 80}\n")
    
    print("OUTPUT FILES GENERATED:")
    print(f"  ✓ CSV metrics: {csv_file}")
    print(f"  ✓ JSON metrics: {json_file}")
    print(f"  ✓ NAV curves: {output_dir / '12_strategies_nav_curves.png'}")
    print(f"  ✓ Metrics comparison: {output_dir / '12_strategies_metrics_comparison.png'}")
    print(f"  ✓ Correlation heatmap: {output_dir / '12_strategies_correlation_heatmap.png'}")
    print()
    
    logger.info("✓ Full backtest completed successfully!")


if __name__ == "__main__":
    main()
