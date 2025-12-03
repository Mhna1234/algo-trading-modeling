"""
Demo: SVM Regime Classification Strategy

This demo showcases the Support Vector Machine (SVM) based market regime
classification strategy that adapts portfolio allocation based on detected
market conditions (bull, bear, sideways).

Features Demonstrated:
- Automatic regime detection using machine learning
- High-dimensional feature extraction (20+ technical indicators)
- Regime-adaptive portfolio strategies
- Quarterly model retraining with expanding window
- Performance comparison vs. single-strategy approaches

Author: Portfolio Engine Team
Date: December 2025
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging

from src.data_loader import load_data
from src.signal_generator import StrategySignalGenerator
from src.optimizer import PortfolioOptimizer
from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import (
    SVMRegimeStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    InverseVolatilityStrategy,
    EqualWeightStrategy
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_svm_regime_demo():
    """Run comprehensive demo of SVM Regime Classification Strategy."""
    
    print("=" * 80)
    print("SVM REGIME CLASSIFICATION STRATEGY DEMO")
    print("=" * 80)
    print()
    
    # ========================================================================
    # 1. LOAD DATA
    # ========================================================================
    print("📊 Loading Market Data...")
    print("-" * 80)
    
    # Use diverse assets for regime detection
    tickers = [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
        # Finance
        'JPM', 'BAC', 'WFC',
        # Consumer
        'PG', 'KO', 'WMT',
        # Industrial
        'CAT', 'BA',
        # Healthcare
        'JNJ', 'UNH',
        # Energy
        'XOM', 'CVX',
        # Utilities
        'NEE',
        # Market ETFs
        'SPY', 'QQQ'
    ]
    
    start_date = '2019-01-01'  # 5 years for robust testing
    end_date = '2024-01-01'
    
    try:
        ticker_to_name, prices = load_data(tickers, start_date, end_date)
        print(f"✓ Loaded {len(prices.columns)} assets")
        print(f"✓ Date range: {prices.index[0].date()} to {prices.index[-1].date()}")
        print(f"✓ Total trading days: {len(prices)}")
        print()
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # ========================================================================
    # 2. INITIALIZE STRATEGY COMPONENTS
    # ========================================================================
    print("🔧 Initializing Strategy Components...")
    print("-" * 80)
    
    # Signal generator with regime feature extraction
    strategy = StrategySignalGenerator(prices, risk_free_rate=0.02)
    print("✓ Signal generator initialized")
    
    # Optimizer for risk management
    optimizer = PortfolioOptimizer(strategy.get_return_matrix())
    print("✓ Portfolio optimizer initialized")
    
    # Portfolio engine
    portfolio = PortfolioEngine(prices, initial_capital=1_000_000)
    print("✓ Portfolio engine initialized")
    print()
    
    # ========================================================================
    # 3. CREATE SVM REGIME STRATEGY
    # ========================================================================
    print("🤖 Creating SVM Regime Classification Strategy...")
    print("-" * 80)
    
    svm_strategy = SVMRegimeStrategy(
        strategy=strategy,
        optimizer=optimizer,
        kernel='rbf',              # Radial Basis Function kernel
        C=1.0,                     # Regularization parameter
        gamma='scale',             # Kernel coefficient
        retrain_frequency=126,     # Retrain semi-annually (reduced for speed)
        lookback_window=252,       # 1 year of training data (reduced for speed)
        bull_threshold=0.05,       # 5% forward return = bull
        bear_threshold=-0.05,      # -5% forward return = bear
        bull_strategy='momentum',  # Aggressive in bull markets
        bear_strategy='inverse_vol',  # Defensive in bear markets
        sideways_strategy='mean_reversion',  # Range-bound trading
        objective='cvar',          # Tail risk management
        alpha=0.95,
        max_weight=0.20,           # 20% max per asset
        top_k=10                   # Hold top 10 assets
    )
    
    print("✓ SVM Regime Strategy configured:")
    print(f"  - Kernel: RBF")
    print(f"  - Retrain frequency: Semi-annually (126 days)")
    print(f"  - Training window: 1 year (252 days)")
    print(f"  - Bull regime strategy: Momentum")
    print(f"  - Bear regime strategy: Inverse Volatility")
    print(f"  - Sideways regime strategy: Mean Reversion")
    print()
    
    # ========================================================================
    # 4. CREATE COMPARISON STRATEGIES
    # ========================================================================
    print("📈 Creating Comparison Strategies...")
    print("-" * 80)
    
    strategies_to_test = {
        'SVM Regime Adaptive': svm_strategy,
        'Pure Momentum': MomentumStrategy(
            strategy, optimizer,
            top_k=10, lookback=126,
            objective='cvar', alpha=0.95, max_weight=0.20
        ),
        'Pure Mean Reversion': MeanReversionStrategy(
            strategy, optimizer,
            top_k=10, window=5,
            objective='mvo', risk_aversion=3.0, max_weight=0.20
        ),
        'Pure Inverse Vol': InverseVolatilityStrategy(
            strategy, optimizer,
            vol_window=20, objective='risk_parity', max_weight=0.25
        ),
        'Equal Weight': EqualWeightStrategy(strategy)
    }
    
    print(f"✓ Created {len(strategies_to_test)} strategies for comparison")
    print()
    
    # ========================================================================
    # 5. RUN BACKTESTS
    # ========================================================================
    print("🚀 Running Backtests...")
    print("=" * 80)
    
    results = {}
    
    for strategy_name, strat in strategies_to_test.items():
        print(f"\n{'='*80}")
        print(f"Testing: {strategy_name}")
        print(f"{'='*80}")
        
        try:
            result = portfolio.run_backtest(
                strategy_wrapper=strat,
                start_date=start_date,
                end_date=end_date,
                rebalance_freq='M',  # Monthly rebalancing
                initial_capital=1_000_000
            )
            
            results[strategy_name] = result
            
            # Print summary (access from summary_metrics dict)
            metrics = result.summary_metrics
            print(f"\n📊 {strategy_name} Results:")
            print(f"  Total Return: {metrics.get('total_return', 0):.2%}")
            print(f"  Annual Return: {metrics.get('annualized_return', 0):.2%}")
            print(f"  Volatility: {metrics.get('annualized_volatility', 0):.2%}")
            print(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
            print(f"  Max Drawdown: {metrics.get('max_drawdown', 0):.2%}")
            print(f"  Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}")
            print(f"  Win Rate: {metrics.get('win_rate', 0):.2%}")
            print(f"  Avg Turnover: {metrics.get('avg_turnover', 0):.2%}")
            
        except Exception as e:
            print(f"❌ Error testing {strategy_name}: {e}")
            import traceback
            traceback.print_exc()
    
    if not results:
        print("\n❌ No successful backtests")
        return
    
    # ========================================================================
    # 6. PERFORMANCE COMPARISON
    # ========================================================================
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE COMPARISON")
    print("=" * 80)
    
    # Create comparison DataFrame
    comparison = pd.DataFrame({
        name: {
            'Total Return': result.summary_metrics.get('total_return', 0),
            'Annual Return': result.summary_metrics.get('annualized_return', 0),
            'Volatility': result.summary_metrics.get('annualized_volatility', 0),
            'Sharpe Ratio': result.summary_metrics.get('sharpe_ratio', 0),
            'Max Drawdown': result.summary_metrics.get('max_drawdown', 0),
            'Calmar Ratio': result.summary_metrics.get('calmar_ratio', 0),
            'Sortino Ratio': result.summary_metrics.get('sortino_ratio', 0),
            'Win Rate': result.summary_metrics.get('win_rate', 0),
            'Avg Turnover': result.summary_metrics.get('avg_turnover', 0),
        }
        for name, result in results.items()
    }).T
    
    # Sort by Sharpe Ratio
    comparison = comparison.sort_values('Sharpe Ratio', ascending=False)
    
    print("\n" + comparison.to_string())
    
    # Save to CSV
    output_file = 'visualizations/svm_regime_strategy_comparison.csv'
    comparison.to_csv(output_file)
    print(f"\n✓ Results saved to {output_file}")
    
    # ========================================================================
    # 7. VISUALIZATIONS
    # ========================================================================
    print("\n" + "=" * 80)
    print("📈 Creating Visualizations...")
    print("=" * 80)
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 1. Equity Curves
    ax1 = fig.add_subplot(gs[0, :])
    for name, result in results.items():
        equity = result.equity_curve / result.equity_curve.iloc[0]  # Normalize to 1
        ax1.plot(equity.index, equity.values, label=name, linewidth=2)
    
    ax1.set_title('Normalized Equity Curves', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Normalized Value (Starting = 1.0)')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 2. Sharpe Ratio Comparison
    ax2 = fig.add_subplot(gs[1, 0])
    sharpe_ratios = comparison['Sharpe Ratio'].sort_values(ascending=True)
    colors = ['green' if x > 0 else 'red' for x in sharpe_ratios]
    sharpe_ratios.plot(kind='barh', ax=ax2, color=colors)
    ax2.set_title('Sharpe Ratio Comparison', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Sharpe Ratio')
    ax2.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax2.grid(True, alpha=0.3, axis='x')
    
    # 3. Max Drawdown Comparison
    ax3 = fig.add_subplot(gs[1, 1])
    max_dd = comparison['Max Drawdown'].sort_values(ascending=False)
    max_dd.plot(kind='barh', ax=ax3, color='darkred')
    ax3.set_title('Maximum Drawdown Comparison', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Max Drawdown')
    ax3.grid(True, alpha=0.3, axis='x')
    
    # 4. Return vs Risk Scatter
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.scatter(
        comparison['Volatility'] * 100,
        comparison['Annual Return'] * 100,
        s=200, alpha=0.6, c=comparison['Sharpe Ratio'],
        cmap='RdYlGn', edgecolors='black'
    )
    
    for idx, row in comparison.iterrows():
        ax4.annotate(
            idx,
            (row['Volatility'] * 100, row['Annual Return'] * 100),
            fontsize=8, ha='center'
        )
    
    ax4.set_title('Risk-Return Profile', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Volatility (%)')
    ax4.set_ylabel('Annual Return (%)')
    ax4.grid(True, alpha=0.3)
    cbar = plt.colorbar(ax4.collections[0], ax=ax4)
    cbar.set_label('Sharpe Ratio')
    
    # 5. Turnover vs Performance
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.scatter(
        comparison['Avg Turnover'] * 100,
        comparison['Sharpe Ratio'],
        s=200, alpha=0.6,
        c=comparison['Annual Return'],
        cmap='viridis', edgecolors='black'
    )
    
    for idx, row in comparison.iterrows():
        ax5.annotate(
            idx,
            (row['Avg Turnover'] * 100, row['Sharpe Ratio']),
            fontsize=8, ha='center'
        )
    
    ax5.set_title('Turnover vs Sharpe Ratio', fontsize=12, fontweight='bold')
    ax5.set_xlabel('Average Turnover (%)')
    ax5.set_ylabel('Sharpe Ratio')
    ax5.grid(True, alpha=0.3)
    cbar = plt.colorbar(ax5.collections[0], ax=ax5)
    cbar.set_label('Annual Return')
    
    plt.suptitle('SVM Regime Classification Strategy - Performance Analysis',
                 fontsize=16, fontweight='bold', y=0.995)
    
    # Save figure
    output_plot = 'visualizations/svm_regime_strategy_analysis.png'
    plt.savefig(output_plot, dpi=300, bbox_inches='tight')
    print(f"✓ Visualization saved to {output_plot}")
    
    # ========================================================================
    # 8. REGIME ANALYSIS (SVM Strategy Only)
    # ========================================================================
    if 'SVM Regime Adaptive' in results:
        print("\n" + "=" * 80)
        print("🤖 SVM REGIME DETECTION ANALYSIS")
        print("=" * 80)
        
        svm_result = results['SVM Regime Adaptive']
        svm_info = svm_strategy.get_strategy_info()
        
        if 'regime_distribution' in svm_info:
            print("\n📊 Regime Distribution (Last 20 Rebalances):")
            for regime, count in svm_info['regime_distribution'].items():
                print(f"  {regime.capitalize()}: {count} occurrences")
            
            print(f"\n🎯 Current Regime: {svm_info.get('current_regime', 'unknown').upper()}")
        
        print(f"\n✓ Model Status: {'Trained' if svm_info.get('model_trained') else 'Not Trained'}")
    
    # ========================================================================
    # 9. SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    # Find best strategy
    best_strategy = comparison['Sharpe Ratio'].idxmax()
    best_sharpe = comparison.loc[best_strategy, 'Sharpe Ratio']
    
    print(f"\n🏆 Best Strategy (by Sharpe Ratio): {best_strategy}")
    print(f"   Sharpe Ratio: {best_sharpe:.3f}")
    print(f"   Annual Return: {comparison.loc[best_strategy, 'Annual Return']:.2%}")
    print(f"   Max Drawdown: {comparison.loc[best_strategy, 'Max Drawdown']:.2%}")
    
    print("\n📁 Output Files:")
    print(f"  - {output_file}")
    print(f"  - {output_plot}")
    
    print("\n" + "=" * 80)
    print("Thank you for using the SVM Regime Classification Strategy!")
    print("=" * 80)


if __name__ == "__main__":
    run_svm_regime_demo()
