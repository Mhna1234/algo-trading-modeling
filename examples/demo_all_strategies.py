"""
Comprehensive Demo - All 10 Strategies

This script demonstrates all available trading strategies with:
- Individual strategy backtests
- Performance comparison
- Visualization
- Dashboard-ready data export

Run this to see all strategies in action!
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import (
    EqualWeightStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    InverseVolatilityStrategy,
    CVaRMinimizationStrategy,
    RegimeSwitchingStrategy,
    MLRandomForestStrategy,
    MLGradientBoostingStrategy,
    ARMAForecastStrategy,
    MultiFactorMLStrategy
)
from src.strategy import Strategy
from src.optimizer import PortfolioOptimizer
from src.data_loader import load_data
from src.evaluator import Evaluator

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (15, 10)

print("="*80)
print("PORTFOLIO ENGINE - ALL STRATEGIES DEMO")
print("="*80)
print()

# ============================================================================
# 1. LOAD DATA
# ============================================================================

print("1. Loading data...")

# Load sample data (adjust tickers and dates as needed)
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'JPM', 
           'V', 'JNJ', 'WMT', 'PG', 'UNH', 'HD', 'BAC']
start_date = '2020-01-01'
end_date = '2023-12-31'

try:
    _, prices = load_data(tickers, start_date, end_date)
    print(f"   ✓ Loaded {len(prices.columns)} assets from {prices.index[0].date()} to {prices.index[-1].date()}")
except Exception as e:
    print(f"   Error loading data: {e}")
    print("   Creating synthetic data for demonstration...")
    
    # Generate synthetic data
    dates = pd.bdate_range(start_date, end_date)
    n_assets = 15
    tickers = [f'ASSET_{i+1}' for i in range(n_assets)]
    
    # Synthetic returns with different characteristics
    np.random.seed(42)
    drifts = np.linspace(0.05, 0.15, n_assets) / 252
    vols = np.linspace(0.15, 0.30, n_assets) / np.sqrt(252)
    
    returns_data = pd.DataFrame(
        np.random.normal(loc=drifts, scale=vols, size=(len(dates), n_assets)),
        index=dates,
        columns=tickers
    )
    
    prices = 100 * (1 + returns_data).cumprod()
    print(f"   ✓ Generated {len(prices.columns)} synthetic assets")

print()

# ============================================================================
# 2. CREATE STRATEGY AND OPTIMIZER
# ============================================================================

print("2. Initializing strategy and optimizer...")

strategy = Strategy(prices)
optimizer = PortfolioOptimizer(
    risk_free_rate=0.02,
    max_weight=0.2,
    min_weight=0.0
)

print("   ✓ Strategy and optimizer ready")
print()

# ============================================================================
# 3. RUN ALL STRATEGIES
# ============================================================================

print("3. Running backtests for all 10 strategies...")
print()

strategies_to_test = [
    ("Equal Weight", EqualWeightStrategy(strategy)),
    ("Momentum", MomentumStrategy(strategy, optimizer, top_k=10, lookback=126)),
    ("Mean Reversion", MeanReversionStrategy(strategy, optimizer, top_k=10, window=5)),
    ("Inverse Volatility", InverseVolatilityStrategy(strategy, optimizer, vol_window=21)),
    ("CVaR Minimization", CVaRMinimizationStrategy(strategy, optimizer, alpha=0.95)),
    ("Regime Switching", RegimeSwitchingStrategy(strategy, optimizer, top_k=10)),
    ("ML Random Forest", MLRandomForestStrategy(strategy, optimizer, top_k=8)),
    ("ML Gradient Boosting", MLGradientBoostingStrategy(strategy, optimizer, top_k=8)),
    ("ARMA Forecast", ARMAForecastStrategy(strategy, optimizer, top_k=8)),
    ("Multi-Factor ML", MultiFactorMLStrategy(strategy, optimizer, top_k=10))
]

results = {}
portfolio = PortfolioEngine(
    prices,
    initial_capital=1_000_000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0
)

for i, (name, strategy_wrapper) in enumerate(strategies_to_test, 1):
    print(f"   [{i}/10] Running {name}...")
    try:
        result = portfolio.run_backtest(
            strategy_wrapper,
            start_date=prices.index[252],  # Start after 1 year of history
            end_date=prices.index[-1],
            rebalance_freq='M'
        )
        results[name] = result
        print(f"   ✓ {name}: Sharpe={result.metrics['sharpe_ratio']:.2f}, "
              f"Return={result.metrics['annual_return']:.2%}")
    except Exception as e:
        print(f"   ✗ {name}: Error - {str(e)[:50]}")
    print()

print(f"✓ Completed {len(results)}/10 strategy backtests")
print()

# ============================================================================
# 4. COMPARE RESULTS
# ============================================================================

print("4. Comparing strategy performance...")
print()

if len(results) > 0:
    evaluator = Evaluator(list(results.values())[0])
    comparison = evaluator.compare_strategies(results)
    
    # Display key metrics
    print("STRATEGY COMPARISON (Ranked by Sharpe Ratio)")
    print("="*80)
    
    display_cols = ['annual_return', 'annual_volatility', 'sharpe_ratio', 
                    'max_drawdown', 'calmar_ratio']
    available_cols = [col for col in display_cols if col in comparison.columns]
    
    comparison_sorted = comparison[available_cols].sort_values('sharpe_ratio', ascending=False)
    
    print(comparison_sorted.to_string())
    print()

# ============================================================================
# 5. VISUALIZATIONS
# ============================================================================

print("5. Creating visualizations...")
print()

if len(results) >= 2:
    # Create comprehensive visualization
    fig = plt.figure(figsize=(20, 12))
    
    # 1. Equity Curves
    ax1 = plt.subplot(2, 3, 1)
    for name, result in results.items():
        ax1.plot(result.equity_curve.index, result.equity_curve.values, 
                label=name, linewidth=2, alpha=0.7)
    ax1.set_title("Equity Curves - All Strategies", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Portfolio Value ($)")
    ax1.legend(fontsize=8, loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 2. Sharpe Ratios
    ax2 = plt.subplot(2, 3, 2)
    sharpe_data = {name: res.metrics['sharpe_ratio'] for name, res in results.items()}
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(sharpe_data)))
    bars = ax2.barh(list(sharpe_data.keys()), list(sharpe_data.values()), color=colors)
    ax2.set_title("Sharpe Ratio Comparison", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Sharpe Ratio")
    ax2.grid(True, alpha=0.3, axis='x')
    
    # 3. Drawdowns
    ax3 = plt.subplot(2, 3, 3)
    for name, result in results.items():
        ax3.plot(result.drawdown_series.index, result.drawdown_series.values,
                label=name, alpha=0.6)
    ax3.set_title("Drawdowns", fontsize=14, fontweight='bold')
    ax3.set_ylabel("Drawdown (%)")
    ax3.legend(fontsize=8, loc='best')
    ax3.grid(True, alpha=0.3)
    
    # 4. Returns vs Volatility
    ax4 = plt.subplot(2, 3, 4)
    returns = [res.metrics['annual_return'] for res in results.values()]
    vols = [res.metrics['annual_volatility'] for res in results.values()]
    sharpes = [res.metrics['sharpe_ratio'] for res in results.values()]
    
    scatter = ax4.scatter(vols, returns, s=200, c=sharpes, cmap='RdYlGn', 
                         alpha=0.7, edgecolors='black', linewidth=1.5)
    for i, name in enumerate(results.keys()):
        ax4.annotate(name, (vols[i], returns[i]), fontsize=8, 
                    ha='center', va='bottom')
    ax4.set_xlabel("Annualized Volatility")
    ax4.set_ylabel("Annualized Return")
    ax4.set_title("Risk-Return Profile", fontsize=14, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax4, label='Sharpe Ratio')
    
    # 5. Max Drawdown Comparison
    ax5 = plt.subplot(2, 3, 5)
    dd_data = {name: res.metrics['max_drawdown'] for name, res in results.items()}
    colors = plt.cm.RdYlGn_r(np.linspace(0.3, 0.9, len(dd_data)))
    ax5.barh(list(dd_data.keys()), list(dd_data.values()), color=colors)
    ax5.set_title("Maximum Drawdown Comparison", fontsize=14, fontweight='bold')
    ax5.set_xlabel("Max Drawdown (%)")
    ax5.grid(True, alpha=0.3, axis='x')
    
    # 6. Win Rates
    ax6 = plt.subplot(2, 3, 6)
    win_rates = {name: res.metrics['win_rate'] for name, res in results.items()}
    ax6.bar(range(len(win_rates)), list(win_rates.values()), 
           color='skyblue', edgecolor='black', linewidth=1.5)
    ax6.set_xticks(range(len(win_rates)))
    ax6.set_xticklabels(list(win_rates.keys()), rotation=45, ha='right', fontsize=9)
    ax6.set_title("Win Rate Comparison", fontsize=14, fontweight='bold')
    ax6.set_ylabel("Win Rate")
    ax6.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='50%')
    ax6.legend()
    ax6.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle("PORTFOLIO ENGINE - ALL STRATEGIES ANALYSIS", 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    # Save figure
    output_path = os.path.join('visualizations', 'all_strategies_comparison.png')
    os.makedirs('visualizations', exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"   ✓ Saved visualization: {output_path}")
    
    plt.show()

# ============================================================================
# 6. EXPORT DASHBOARD DATA
# ============================================================================

print()
print("6. Exporting dashboard data...")
print()

for name, result in results.items():
    dashboard_data = portfolio.get_dashboard_data()
    
    # Save to CSV
    output_dir = f'visualizations/dashboard_data_{name.replace(" ", "_").lower()}'
    os.makedirs(output_dir, exist_ok=True)
    
    result.equity_curve.to_csv(f'{output_dir}/equity_curve.csv')
    result.weights_history.to_csv(f'{output_dir}/weights.csv')
    result.returns_series.to_csv(f'{output_dir}/returns.csv')
    
    # Save metrics as JSON
    import json
    with open(f'{output_dir}/metrics.json', 'w') as f:
        json.dump(result.metrics, f, indent=2)
    
    print(f"   ✓ Exported {name} data to {output_dir}/")

print()
print("="*80)
print("DEMO COMPLETE!")
print("="*80)
print()
print("Summary:")
print(f"  • Tested {len(results)} strategies")
print(f"  • Best Sharpe Ratio: {comparison_sorted.iloc[0]['sharpe_ratio']:.2f} ({comparison_sorted.index[0]})")
print(f"  • Best Return: {comparison_sorted['annual_return'].max():.2%}")
print(f"  • Lowest Drawdown: {comparison_sorted['max_drawdown'].max():.2%}")
print()
print("Visualization and data exported to: visualizations/")
print()
