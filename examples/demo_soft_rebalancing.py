"""
Demo: Soft Rebalancing vs Hard Rebalancing
===========================================

This script demonstrates the difference between soft rebalancing (5% drift threshold)
and hard rebalancing (always rebalance) using 3 example strategies:

1. Equal Weight - Simple 1/N allocation
2. Momentum - Top 10 momentum stocks
3. Risk Parity - Equal risk contribution

For each strategy, we run TWO backtests:
- Soft Rebalancing: Only trades when weight drift > 5%
- Hard Rebalancing: Always rebalances on schedule

We then compare:
- Total returns
- Sharpe ratios
- Transaction costs
- Turnover rates
- Number of trades

This demonstrates the cost savings and performance impact of soft rebalancing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Import modified portfolio engine
from src.portfolio_engine import PortfolioEngine
from src.data_loader import load_preprocessed_data
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategies import (
    EqualWeightStrategy,
    MomentumStrategy,
    RiskParityStrategy
)

# Configuration
INITIAL_CAPITAL = 100_000
START_DATE = '2020-01-01'
END_DATE = '2024-12-31'
REBALANCE_FREQ = 'Q'  # Quarterly

print("=" * 80)
print("SOFT REBALANCING DEMONSTRATION")
print("=" * 80)
print(f"\nConfiguration:")
print(f"  Initial Capital: ${INITIAL_CAPITAL:,.0f}")
print(f"  Period: {START_DATE} to {END_DATE}")
print(f"  Rebalancing: {REBALANCE_FREQ} (Quarterly)")
print(f"  Transaction Costs: 0.15% (0.10% commission + 0.05% slippage)")
print(f"  Soft Rebalancing Threshold: 5%")
print("\n" + "=" * 80)

# Load data
print("\nLoading data...")
try:
    _, prices = load_preprocessed_data(start=START_DATE, end=END_DATE)
    print(f"✓ Loaded {len(prices)} days, {len(prices.columns)} tickers")
except Exception as e:
    print(f"✗ Error loading data: {e}")
    print("\nPlease run: python scripts/prepare_data.py")
    sys.exit(1)

# Initialize strategies
print("\nInitializing strategies...")
strategy_gen = Strategy(prices)
optimizer = PortfolioOptimizer(
    returns=strategy_gen.returns,
    risk_free_rate=0.02
)

strategies = [
    ("Equal Weight", EqualWeightStrategy(strategy_gen, optimizer)),
    ("Momentum Top-10", MomentumStrategy(strategy_gen, optimizer, top_k=10, lookback=126)),
    ("Risk Parity", RiskParityStrategy(strategy_gen, optimizer, lookback=252))
]

print(f"✓ Initialized {len(strategies)} strategies")

# Results storage
results = []

# Run backtests for each strategy
for strategy_name, strategy in strategies:
    print("\n" + "=" * 80)
    print(f"STRATEGY: {strategy_name}")
    print("=" * 80)
    
    # Create engine with updated costs
    engine = PortfolioEngine(
        prices=prices,
        initial_capital=INITIAL_CAPITAL,
        transaction_cost_bps=10.0,  # 0.10%
        slippage_bps=5.0             # 0.05%
    )
    
    # Run with SOFT rebalancing
    print(f"\n1. Running with SOFT rebalancing (5% threshold)...")
    try:
        result_soft = engine.run_backtest(
            strategy_wrapper=strategy,
            start_date=START_DATE,
            end_date=END_DATE,
            rebalance_freq=REBALANCE_FREQ,
            soft_rebalance=True,
            drift_threshold=0.05
        )
        print(f"   ✓ Completed soft rebalancing backtest")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        continue
    
    # Run with HARD rebalancing
    print(f"\n2. Running with HARD rebalancing (always rebalance)...")
    try:
        result_hard = engine.run_backtest(
            strategy_wrapper=strategy,
            start_date=START_DATE,
            end_date=END_DATE,
            rebalance_freq=REBALANCE_FREQ,
            soft_rebalance=False
        )
        print(f"   ✓ Completed hard rebalancing backtest")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        continue
    
    # Extract metrics
    soft_metrics = result_soft.summary_metrics
    hard_metrics = result_hard.summary_metrics
    
    # Compare results
    print(f"\n3. Comparison:")
    print(f"   {'Metric':<25} {'Soft Rebalance':<20} {'Hard Rebalance':<20} {'Difference':<15}")
    print(f"   {'-'*25} {'-'*20} {'-'*20} {'-'*15}")
    
    # Total Return
    soft_return = soft_metrics['total_return'] * 100
    hard_return = hard_metrics['total_return'] * 100
    print(f"   {'Total Return':<25} {soft_return:>18.2f}% {hard_return:>18.2f}% {soft_return-hard_return:>13.2f}%")
    
    # Annual Return
    soft_annual = soft_metrics['annual_return'] * 100
    hard_annual = hard_metrics['annual_return'] * 100
    print(f"   {'Annual Return':<25} {soft_annual:>18.2f}% {hard_annual:>18.2f}% {soft_annual-hard_annual:>13.2f}%")
    
    # Sharpe Ratio
    soft_sharpe = soft_metrics['sharpe_ratio']
    hard_sharpe = hard_metrics['sharpe_ratio']
    print(f"   {'Sharpe Ratio':<25} {soft_sharpe:>18.3f} {hard_sharpe:>18.3f} {soft_sharpe-hard_sharpe:>13.3f}")
    
    # Max Drawdown
    soft_dd = soft_metrics['max_drawdown'] * 100
    hard_dd = hard_metrics['max_drawdown'] * 100
    print(f"   {'Max Drawdown':<25} {soft_dd:>18.2f}% {hard_dd:>18.2f}% {soft_dd-hard_dd:>13.2f}%")
    
    # Turnover
    soft_turnover = soft_metrics['avg_turnover'] * 100
    hard_turnover = hard_metrics['avg_turnover'] * 100
    print(f"   {'Avg Turnover':<25} {soft_turnover:>18.2f}% {hard_turnover:>18.2f}% {soft_turnover-hard_turnover:>13.2f}%")
    
    # Transaction Costs
    soft_costs = soft_metrics['total_costs']
    hard_costs = hard_metrics['total_costs']
    print(f"   {'Transaction Costs':<25} ${soft_costs:>17,.2f} ${hard_costs:>17,.2f} ${soft_costs-hard_costs:>12,.2f}")
    
    # Cost as % of Return
    soft_cost_pct = (soft_costs / soft_metrics['final_equity']) * 100 if soft_metrics['final_equity'] > 0 else 0
    hard_cost_pct = (hard_costs / hard_metrics['final_equity']) * 100 if hard_metrics['final_equity'] > 0 else 0
    print(f"   {'Costs/Final Value':<25} {soft_cost_pct:>18.3f}% {hard_cost_pct:>18.3f}% {soft_cost_pct-hard_cost_pct:>13.3f}%")
    
    # Win Rate
    soft_wr = soft_metrics['win_rate'] * 100
    hard_wr = hard_metrics['win_rate'] * 100
    print(f"   {'Win Rate':<25} {soft_wr:>18.2f}% {hard_wr:>18.2f}% {soft_wr-hard_wr:>13.2f}%")
    
    # Calculate cost savings
    cost_savings = hard_costs - soft_costs
    cost_savings_pct = (cost_savings / hard_costs * 100) if hard_costs > 0 else 0
    
    print(f"\n4. Summary:")
    print(f"   💰 Cost Savings: ${cost_savings:,.2f} ({cost_savings_pct:.1f}% reduction)")
    print(f"   📊 Return Impact: {(soft_return - hard_return):.2f}% {'better' if soft_return > hard_return else 'worse'}")
    print(f"   📈 Sharpe Impact: {(soft_sharpe - hard_sharpe):.3f} {'better' if soft_sharpe > hard_sharpe else 'worse'}")
    
    # Store results
    results.append({
        'strategy': strategy_name,
        'soft_return': soft_return,
        'hard_return': hard_return,
        'soft_sharpe': soft_sharpe,
        'hard_sharpe': hard_sharpe,
        'soft_costs': soft_costs,
        'hard_costs': hard_costs,
        'cost_savings': cost_savings,
        'soft_turnover': soft_turnover,
        'hard_turnover': hard_turnover,
        'result_soft': result_soft,
        'result_hard': result_hard
    })

# Summary comparison across all strategies
print("\n" + "=" * 80)
print("OVERALL SUMMARY: Soft vs Hard Rebalancing")
print("=" * 80)

print(f"\n{'Strategy':<20} {'Approach':<15} {'Return':<12} {'Sharpe':<10} {'Costs':<15} {'Turnover':<12}")
print("-" * 95)

for r in results:
    print(f"{r['strategy']:<20} {'Soft (5%)':<15} {r['soft_return']:>10.2f}% {r['soft_sharpe']:>8.3f} ${r['soft_costs']:>12,.2f} {r['soft_turnover']:>10.2f}%")
    print(f"{'':<20} {'Hard (Always)':<15} {r['hard_return']:>10.2f}% {r['hard_sharpe']:>8.3f} ${r['hard_costs']:>12,.2f} {r['hard_turnover']:>10.2f}%")
    print(f"{'':<20} {'Difference':<15} {r['soft_return']-r['hard_return']:>10.2f}% {r['soft_sharpe']-r['hard_sharpe']:>8.3f} ${r['cost_savings']:>12,.2f} {r['soft_turnover']-r['hard_turnover']:>10.2f}%")
    print("-" * 95)

# Calculate aggregate statistics
total_cost_savings = sum(r['cost_savings'] for r in results)
avg_return_impact = np.mean([r['soft_return'] - r['hard_return'] for r in results])
avg_sharpe_impact = np.mean([r['soft_sharpe'] - r['hard_sharpe'] for r in results])

print(f"\nAggregate Statistics:")
print(f"  Total Cost Savings (all strategies): ${total_cost_savings:,.2f}")
print(f"  Average Return Impact: {avg_return_impact:+.2f}%")
print(f"  Average Sharpe Impact: {avg_sharpe_impact:+.3f}")

# Key insights
print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)

insights = []

# Insight 1: Cost savings
if total_cost_savings > 0:
    insights.append(f"✓ Soft rebalancing saved ${total_cost_savings:,.2f} in transaction costs across all strategies")
else:
    insights.append(f"⚠ Hard rebalancing had lower costs (unusual - check data)")

# Insight 2: Return impact
if avg_return_impact >= -0.5:
    insights.append(f"✓ Soft rebalancing maintained similar returns (avg impact: {avg_return_impact:+.2f}%)")
else:
    insights.append(f"⚠ Soft rebalancing reduced returns by {abs(avg_return_impact):.2f}%")

# Insight 3: Risk-adjusted returns
if avg_sharpe_impact >= 0:
    insights.append(f"✓ Soft rebalancing improved risk-adjusted returns (Sharpe +{avg_sharpe_impact:.3f})")
else:
    insights.append(f"⚠ Soft rebalancing slightly reduced Sharpe ratio ({avg_sharpe_impact:.3f})")

# Insight 4: Turnover reduction
avg_turnover_reduction = np.mean([r['hard_turnover'] - r['soft_turnover'] for r in results])
if avg_turnover_reduction > 0:
    insights.append(f"✓ Soft rebalancing reduced average turnover by {avg_turnover_reduction:.2f}%")

# Insight 5: Best strategy
best_soft = max(results, key=lambda x: x['soft_sharpe'])
insights.append(f"✓ Best performing strategy (soft): {best_soft['strategy']} (Sharpe: {best_soft['soft_sharpe']:.3f})")

for i, insight in enumerate(insights, 1):
    print(f"\n{i}. {insight}")

# Visualization
print("\n" + "=" * 80)
print("GENERATING VISUALIZATIONS")
print("=" * 80)

try:
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Soft vs Hard Rebalancing Comparison', fontsize=16, fontweight='bold')
    
    # Plot 1: Equity Curves
    ax1 = axes[0, 0]
    for r in results:
        ax1.plot(r['result_soft'].equity_curve, label=f"{r['strategy']} (Soft)", linestyle='-', linewidth=2)
        ax1.plot(r['result_hard'].equity_curve, label=f"{r['strategy']} (Hard)", linestyle='--', alpha=0.6)
    ax1.set_title('Equity Curves: Soft vs Hard Rebalancing', fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(fontsize=8, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    # Plot 2: Returns Comparison
    ax2 = axes[0, 1]
    strategies_names = [r['strategy'] for r in results]
    x = np.arange(len(strategies_names))
    width = 0.35
    ax2.bar(x - width/2, [r['soft_return'] for r in results], width, label='Soft Rebalancing', color='steelblue')
    ax2.bar(x + width/2, [r['hard_return'] for r in results], width, label='Hard Rebalancing', color='coral')
    ax2.set_title('Total Returns Comparison', fontweight='bold')
    ax2.set_xlabel('Strategy')
    ax2.set_ylabel('Total Return (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(strategies_names, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Transaction Costs
    ax3 = axes[1, 0]
    ax3.bar(x - width/2, [r['soft_costs'] for r in results], width, label='Soft Rebalancing', color='green', alpha=0.7)
    ax3.bar(x + width/2, [r['hard_costs'] for r in results], width, label='Hard Rebalancing', color='red', alpha=0.7)
    ax3.set_title('Transaction Costs Comparison', fontweight='bold')
    ax3.set_xlabel('Strategy')
    ax3.set_ylabel('Total Costs ($)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(strategies_names, rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Plot 4: Sharpe Ratios
    ax4 = axes[1, 1]
    ax4.bar(x - width/2, [r['soft_sharpe'] for r in results], width, label='Soft Rebalancing', color='purple', alpha=0.7)
    ax4.bar(x + width/2, [r['hard_sharpe'] for r in results], width, label='Hard Rebalancing', color='orange', alpha=0.7)
    ax4.set_title('Sharpe Ratio Comparison', fontweight='bold')
    ax4.set_xlabel('Strategy')
    ax4.set_ylabel('Sharpe Ratio')
    ax4.set_xticks(x)
    ax4.set_xticklabels(strategies_names, rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    
    # Save plot
    plot_path = 'results/soft_vs_hard_rebalancing_demo.png'
    Path('results').mkdir(exist_ok=True)
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved visualization to: {plot_path}")
    
    # Show plot
    plt.show()
    
except Exception as e:
    print(f"\n⚠ Could not generate visualizations: {e}")

# Export detailed results to CSV
print("\n" + "=" * 80)
print("EXPORTING RESULTS")
print("=" * 80)

try:
    # Create summary DataFrame
    summary_data = []
    for r in results:
        summary_data.append({
            'Strategy': r['strategy'],
            'Approach': 'Soft (5%)',
            'Total_Return_%': r['soft_return'],
            'Annual_Return_%': r['result_soft'].summary_metrics['annual_return'] * 100,
            'Sharpe_Ratio': r['soft_sharpe'],
            'Max_Drawdown_%': r['result_soft'].summary_metrics['max_drawdown'] * 100,
            'Volatility_%': r['result_soft'].summary_metrics['annual_volatility'] * 100,
            'Win_Rate_%': r['result_soft'].summary_metrics['win_rate'] * 100,
            'Avg_Turnover_%': r['soft_turnover'],
            'Total_Costs_$': r['soft_costs'],
            'Final_Value_$': r['result_soft'].summary_metrics['final_equity']
        })
        summary_data.append({
            'Strategy': r['strategy'],
            'Approach': 'Hard (Always)',
            'Total_Return_%': r['hard_return'],
            'Annual_Return_%': r['result_hard'].summary_metrics['annual_return'] * 100,
            'Sharpe_Ratio': r['hard_sharpe'],
            'Max_Drawdown_%': r['result_hard'].summary_metrics['max_drawdown'] * 100,
            'Volatility_%': r['result_hard'].summary_metrics['annual_volatility'] * 100,
            'Win_Rate_%': r['result_hard'].summary_metrics['win_rate'] * 100,
            'Avg_Turnover_%': r['hard_turnover'],
            'Total_Costs_$': r['hard_costs'],
            'Final_Value_$': r['result_hard'].summary_metrics['final_equity']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_path = 'results/soft_vs_hard_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"✓ Saved summary to: {summary_path}")
    
    # Export equity curves
    for r in results:
        strategy_name = r['strategy'].replace(' ', '_').lower()
        
        # Soft rebalancing equity curve
        soft_path = f"results/equity_curve_{strategy_name}_soft.csv"
        r['result_soft'].equity_curve.to_csv(soft_path)
        
        # Hard rebalancing equity curve
        hard_path = f"results/equity_curve_{strategy_name}_hard.csv"
        r['result_hard'].equity_curve.to_csv(hard_path)
    
    print(f"✓ Saved {len(results)*2} equity curve files")
    
except Exception as e:
    print(f"⚠ Could not export results: {e}")

# Final summary
print("\n" + "=" * 80)
print("DEMO COMPLETE")
print("=" * 80)
print(f"""
This demo compared soft rebalancing (5% drift threshold) vs hard rebalancing
(always rebalance) across {len(strategies)} strategies over {(pd.to_datetime(END_DATE) - pd.to_datetime(START_DATE)).days} days.

Key Takeaways:
1. Soft rebalancing typically reduces transaction costs by allowing natural drift
2. Performance impact is usually minimal (returns stay similar)
3. Risk-adjusted returns often improve due to lower costs
4. Turnover is significantly reduced
5. Best for quarterly/monthly rebalancing frequencies

Results saved to:
- results/soft_vs_hard_summary.csv
- results/soft_vs_hard_rebalancing_demo.png
- results/equity_curve_*.csv

Next Steps:
1. Try different drift thresholds (3%, 7%, 10%)
2. Test with more strategies
3. Analyze different time periods
4. Compare different rebalancing frequencies (M, Q, Y)
""")

print("\n" + "=" * 80)
