"""
Demo: Advanced Backtesting Methods

This script demonstrates all available backtesting methodologies:
1. Vanilla Backtest - Traditional single-run
2. Walk-Forward Backtest - Rolling/expanding window
3. Cross-Validation Backtest - Time-series k-fold
4. Monte Carlo Backtest - Synthetic data generation
5. Randomized Backtest - Multiple randomized trials

Usage:
    python examples/demo_backtesting_methods.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from src.data_loader import load_preprocessed_data
from src.backtesting_methods import BacktestingMethods, BacktestMethodResult
from src.portfolio_engine import PortfolioEngine
from src.strategies import MomentumStrategy
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_results(result: BacktestMethodResult):
    """Print formatted results from a backtesting method."""
    print(f"\nMethod: {result.method_name}")
    print(f"Number of runs: {len(result.individual_results)}")
    print("\nAggregate Metrics:")
    print("-" * 60)
    
    # Group metrics by type
    main_metrics = {}
    for key, value in result.aggregate_metrics.items():
        if '_mean' in key:
            metric_name = key.replace('_mean', '')
            main_metrics[metric_name] = {
                'mean': value,
                'std': result.aggregate_metrics.get(f'{metric_name}_std', 0),
                'min': result.aggregate_metrics.get(f'{metric_name}_min', 0),
                'max': result.aggregate_metrics.get(f'{metric_name}_max', 0)
            }
    
    # Print key metrics
    key_metrics = ['annual_return', 'annual_volatility', 'sharpe_ratio', 'max_drawdown']
    for metric in key_metrics:
        if metric in main_metrics:
            data = main_metrics[metric]
            ci = result.confidence_intervals.get(metric, (None, None))
            
            print(f"\n{metric.replace('_', ' ').title()}:")
            print(f"  Mean: {data['mean']:.4f} +/- {data['std']:.4f}")
            print(f"  Range: [{data['min']:.4f}, {data['max']:.4f}]")
            if ci[0] is not None:
                print(f"  95% CI: [{ci[0]:.4f}, {ci[1]:.4f}]")


def plot_comparison(results: list, save_path: str = None):
    """Plot comparison of backtesting methods."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    methods = [r.method_name for r in results]
    
    # Extract metrics
    sharpe_means = []
    sharpe_stds = []
    return_means = []
    return_stds = []
    dd_means = []
    dd_stds = []
    
    for result in results:
        sharpe_means.append(result.aggregate_metrics.get('sharpe_ratio_mean', 0))
        sharpe_stds.append(result.aggregate_metrics.get('sharpe_ratio_std', 0))
        return_means.append(result.aggregate_metrics.get('annual_return_mean', 0))
        return_stds.append(result.aggregate_metrics.get('annual_return_std', 0))
        dd_means.append(result.aggregate_metrics.get('max_drawdown_mean', 0))
        dd_stds.append(result.aggregate_metrics.get('max_drawdown_std', 0))
    
    # Sharpe Ratio
    x = np.arange(len(methods))
    axes[0, 0].bar(x, sharpe_means, yerr=sharpe_stds, capsize=5, alpha=0.7)
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(methods, rotation=45, ha='right')
    axes[0, 0].set_title('Sharpe Ratio by Method')
    axes[0, 0].set_ylabel('Sharpe Ratio')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Annual Return
    axes[0, 1].bar(x, return_means, yerr=return_stds, capsize=5, alpha=0.7, color='green')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(methods, rotation=45, ha='right')
    axes[0, 1].set_title('Annual Return by Method')
    axes[0, 1].set_ylabel('Annual Return')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Max Drawdown
    axes[1, 0].bar(x, dd_means, yerr=dd_stds, capsize=5, alpha=0.7, color='red')
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels(methods, rotation=45, ha='right')
    axes[1, 0].set_title('Max Drawdown by Method')
    axes[1, 0].set_ylabel('Max Drawdown')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Distribution comparison
    for i, result in enumerate(results):
        sharpes = [r.summary_metrics.get('sharpe_ratio', 0) 
                  for r in result.individual_results]
        axes[1, 1].hist(sharpes, alpha=0.5, label=result.method_name, bins=20)
    
    axes[1, 1].set_title('Sharpe Ratio Distribution')
    axes[1, 1].set_xlabel('Sharpe Ratio')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nPlot saved to {save_path}")
    
    plt.show()


def main():
    """Main demonstration function."""
    print_section("ADVANCED BACKTESTING METHODS DEMO")
    
    # Configuration
    start_date = '2020-01-01'
    end_date = '2023-12-31'
    
    print(f"\nConfiguration:")
    print(f"  Date Range: {start_date} to {end_date}")
    print(f"  Initial Capital: $1,000,000")
    print(f"  Data Source: Pre-processed S3 data (2015-11 to 2025-11)")
    
    # Load pre-processed data
    print("\nLoading pre-processed data...")
    try:
        full_data, price_data = load_preprocessed_data(
            start=start_date,
            end=end_date
        )
        print(f"  Loaded {len(price_data)} days of data for {len(price_data.columns)} assets")
        print(f"  Price data shape: {price_data.shape}")
        # Handle MultiIndex or regular columns
        if hasattr(price_data.columns, 'nlevels') and price_data.columns.nlevels > 1:
            assets = price_data.columns.get_level_values(0).unique().tolist()
        else:
            assets = price_data.columns.tolist()
        print(f"  Assets: {', '.join(str(a) for a in assets)}")
    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize strategy components
    print("\nInitializing strategy...")
    strategy_obj = Strategy(price_data)
    optimizer = PortfolioOptimizer()
    
    # Create strategy wrapper
    strategy = MomentumStrategy(
        strategy_obj,
        optimizer,
        lookback=120,
        top_k=5,
        objective='cvar'
    )
    
    # Initialize backtesting methods
    bt_methods = BacktestingMethods(
        prices=price_data,
        initial_capital=1000000.0,
        transaction_cost_bps=5.0,
        slippage_bps=1.0
    )
    
    # Store results
    all_results = []
    
    # ========================================================================
    # 1. VANILLA BACKTEST
    # ========================================================================
    print_section("1. VANILLA BACKTEST")
    print("Running traditional single-run backtest...")
    
    try:
        vanilla_result = bt_methods.vanilla_backtest(
            strategy=strategy,
            start_date='2021-01-01',
            end_date='2023-12-31',
            rebalance_freq='M'
        )
        all_results.append(vanilla_result)
        print_results(vanilla_result)
    except Exception as e:
        print(f"Error in vanilla backtest: {e}")
    
    # ========================================================================
    # 2. WALK-FORWARD BACKTEST
    # ========================================================================
    print_section("2. WALK-FORWARD BACKTEST")
    print("Running walk-forward analysis with rolling windows...")
    
    try:
        wf_result = bt_methods.walk_forward_backtest(
            strategy=strategy,
            start_date='2020-01-01',
            end_date='2023-12-31',
            train_window_months=12,
            test_window_months=3,
            step_months=3,
            rebalance_freq='M',
            anchored=False
        )
        all_results.append(wf_result)
        print_results(wf_result)
        
        print(f"\nWalk-Forward Details:")
        print(f"  Total walks: {len(wf_result.individual_results)}")
        for walk in wf_result.metadata['walks']:
            print(f"  Walk {walk['walk_number']}: Train [{walk['train_start']} to {walk['train_end']}], "
                  f"Test [{walk['test_start']} to {walk['test_end']}]")
    except Exception as e:
        print(f"Error in walk-forward backtest: {e}")
    
    # ========================================================================
    # 3. CROSS-VALIDATION BACKTEST
    # ========================================================================
    print_section("3. CROSS-VALIDATION BACKTEST")
    print("Running time-series cross-validation...")
    
    try:
        cv_result = bt_methods.cross_validation_backtest(
            strategy=strategy,
            start_date='2020-01-01',
            end_date='2023-12-31',
            n_splits=4,
            test_size_months=6,
            rebalance_freq='M'
        )
        all_results.append(cv_result)
        print_results(cv_result)
        
        print(f"\nCross-Validation Details:")
        print(f"  Total folds: {len(cv_result.individual_results)}")
        for fold in cv_result.metadata['folds']:
            print(f"  Fold {fold['fold']}: Test [{fold['test_start']} to {fold['test_end']}]")
    except Exception as e:
        print(f"Error in cross-validation backtest: {e}")
    
    # ========================================================================
    # 4. MONTE CARLO BACKTEST (reduced simulations for speed)
    # ========================================================================
    print_section("4. MONTE CARLO BACKTEST")
    print("Running Monte Carlo simulation with bootstrap resampling...")
    print("(Using 20 simulations for demonstration - increase for production)")
    
    try:
        mc_result = bt_methods.monte_carlo_backtest(
            strategy=strategy,
            start_date='2021-01-01',
            end_date='2023-12-31',
            n_simulations=20,
            method='bootstrap',
            rebalance_freq='M',
            block_size=20
        )
        all_results.append(mc_result)
        print_results(mc_result)
    except Exception as e:
        print(f"Error in Monte Carlo backtest: {e}")
    
    # ========================================================================
    # 5. RANDOMIZED BACKTEST
    # ========================================================================
    print_section("5. RANDOMIZED BACKTEST")
    print("Running randomized backtest with random starting dates...")
    
    try:
        rand_result = bt_methods.randomized_backtest(
            strategy=strategy,
            start_date='2020-01-01',
            end_date='2023-12-31',
            n_trials=25,
            randomization_type='start_date',
            rebalance_freq='M',
            window_months=12
        )
        all_results.append(rand_result)
        print_results(rand_result)
    except Exception as e:
        print(f"Error in randomized backtest: {e}")
    
    # ========================================================================
    # COMPARISON
    # ========================================================================
    if all_results:
        print_section("COMPARISON OF ALL METHODS")
        
        comparison_df = bt_methods.compare_methods(all_results)
        print("\nComparison Table:")
        print(comparison_df.to_string())
        
        # Save comparison
        comparison_path = 'visualizations/backtesting_methods_comparison.csv'
        os.makedirs('visualizations', exist_ok=True)
        comparison_df.to_csv(comparison_path, index=False)
        print(f"\nComparison saved to {comparison_path}")
        
        # Plot comparison
        print("\nGenerating comparison plots...")
        plot_comparison(all_results, save_path='visualizations/backtesting_methods_comparison.png')
    
    # ========================================================================
    # RECOMMENDATIONS
    # ========================================================================
    print_section("RECOMMENDATIONS")
    print("""
When to use each method:

1. VANILLA BACKTEST
   - Quick initial testing
   - Baseline performance estimation
   - When computational resources are limited
   ⚠️  Susceptible to overfitting

2. WALK-FORWARD BACKTEST
   - Most realistic for live trading
   - Simulates actual strategy deployment
   - Tests strategy adaptability over time
   [OK] Recommended for production strategies

3. CROSS-VALIDATION BACKTEST
   - Assessing statistical robustness
   - Comparing multiple strategies
   - Understanding performance variability
   [OK] Good for strategy selection

4. MONTE CARLO BACKTEST
   - Stress testing strategies
   - Understanding worst-case scenarios
   - Assessing sensitivity to market conditions
   [OK] Essential for risk management

5. RANDOMIZED BACKTEST
   - Testing statistical significance
   - Detecting data-snooping bias
   - Validating strategy robustness
   [OK] Good for research validation

BEST PRACTICE:
Use multiple methods in combination:
1. Start with Vanilla for quick testing
2. Use Walk-Forward for realistic assessment
3. Apply Monte Carlo for risk analysis
4. Confirm with Randomized for validation
    """)
    
    print_section("DEMO COMPLETE")


if __name__ == "__main__":
    main()
