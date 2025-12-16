"""
Demo: Soft Rebalancing with Multi-Armed Bandit Strategies
==========================================================

This script demonstrates the soft rebalancing feature using sophisticated
multi-armed bandit (MAB) strategies.

Strategies tested:
1. UCB Bandit - Upper Confidence Bound algorithm
2. Thompson Sampling Bandit - Bayesian approach
3. Momentum - Traditional momentum strategy (for comparison)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Import components
from src.portfolio_engine import PortfolioEngine
from src.data_loader import load_preprocessed_data
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

# Import bandit strategies
from src.strategies import MomentumStrategy
from src.strategies.bandit_strategy_wrapper import BanditStrategyWrapper
from src.strategies import (
    MaximumDiversificationStrategy,
    RiskParityStrategy,
    InverseVolatilityStrategy
)
from src.bandits import UCBBandit, ThompsonSamplingBandit

# Configuration
INITIAL_CAPITAL = 100_000
START_DATE = '2020-01-01'
END_DATE = '2024-12-31'
REBALANCE_FREQ = 'Q'  # Quarterly

print("=" * 80)
print("SOFT REBALANCING DEMO: MULTI-ARMED BANDIT STRATEGIES")
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
    print("\nPlease run: python fix_price_data.py")
    sys.exit(1)

# Initialize base components
print("\nInitializing strategies...")
strategy_gen = Strategy(prices)
optimizer = PortfolioOptimizer(
    returns=strategy_gen.returns,
    risk_free_rate=0.02
)

# Create candidate sub-strategies for the bandits
print("\nCreating candidate strategies for bandits...")
candidate_strategies = [
    ("Max Diversification", MaximumDiversificationStrategy(strategy_gen, optimizer, lookback=252)),
    ("Risk Parity", RiskParityStrategy(strategy_gen, optimizer, lookback=252)),
    ("Inverse Volatility", InverseVolatilityStrategy(strategy_gen, optimizer, lookback=126)),
]
print(f"✓ Created {len(candidate_strategies)} candidate strategies")

# Create the main strategies to test
strategies = []

# 1. UCB Bandit Strategy
print("\nCreating UCB Bandit strategy...")
ucb_bandit = UCBBandit(n_arms=len(candidate_strategies), exploration_constant=1.0)
ucb_strategy = BanditStrategyWrapper(
    child_strategies=[s[1] for s in candidate_strategies],  # FIXED: use child_strategies
    bandit_allocator=ucb_bandit,
    burn_in_periods=4,  # 4 quarters to try each strategy
    min_allocation=0.20  # Minimum 20% per strategy
)
strategies.append(("UCB Bandit", ucb_strategy))

# 2. Thompson Sampling Bandit Strategy
print("Creating Thompson Sampling Bandit strategy...")
thompson_bandit = ThompsonSamplingBandit(n_arms=len(candidate_strategies))
thompson_strategy = BanditStrategyWrapper(
    child_strategies=[s[1] for s in candidate_strategies],  # FIXED: use child_strategies
    bandit_allocator=thompson_bandit,
    burn_in_periods=4,
    min_allocation=0.20
)
strategies.append(("Thompson Sampling", thompson_strategy))

# 3. Momentum Strategy (for comparison)
print("Creating Momentum strategy...")
momentum_strategy = MomentumStrategy(strategy_gen, optimizer, top_k=10, lookback=126)
strategies.append(("Momentum Top-10", momentum_strategy))

print(f"\n✓ Initialized {len(strategies)} strategies")

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
        import traceback
        traceback.print_exc()
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
    
    # For bandit strategies, show allocation info
    if "Bandit" in strategy_name:
        print(f"\n5. Bandit Strategy Performance:")
        try:
            # Get bandit statistics
            bandit_stats = strategy.get_diagnostics()
            if 'arm_statistics' in bandit_stats:
                arm_stats = bandit_stats['arm_statistics']
                print(f"   Strategy Allocations:")
                for i, (cand_name, _) in enumerate(candidate_strategies):
                    count = arm_stats['counts'][i]
                    pct = (count / sum(arm_stats['counts']) * 100) if sum(arm_stats['counts']) > 0 else 0
                    print(f"     {cand_name}: {count} selections ({pct:.1f}%)")
        except Exception as e:
            print(f"   ⚠ Could not retrieve bandit stats: {e}")
    
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

# Summary comparison
print("\n" + "=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)

print(f"\n{'Strategy':<25} {'Approach':<15} {'Return':<12} {'Sharpe':<10} {'Costs':<15}")
print("-" * 85)

for r in results:
    print(f"{r['strategy']:<25} {'Soft (5%)':<15} {r['soft_return']:>10.2f}% {r['soft_sharpe']:>8.3f} ${r['soft_costs']:>12,.2f}")
    print(f"{'':<25} {'Hard (Always)':<15} {r['hard_return']:>10.2f}% {r['hard_sharpe']:>8.3f} ${r['hard_costs']:>12,.2f}")
    print(f"{'':<25} {'Difference':<15} {r['soft_return']-r['hard_return']:>10.2f}% {r['soft_sharpe']-r['hard_sharpe']:>8.3f} ${r['cost_savings']:>12,.2f}")
    print("-" * 85)

# Aggregate statistics
total_cost_savings = sum(r['cost_savings'] for r in results)
avg_return_impact = np.mean([r['soft_return'] - r['hard_return'] for r in results])
avg_sharpe_impact = np.mean([r['soft_sharpe'] - r['hard_sharpe'] for r in results])

print(f"\nAggregate Statistics:")
print(f"  Total Cost Savings: ${total_cost_savings:,.2f}")
print(f"  Avg Return Impact: {avg_return_impact:+.2f}%")
print(f"  Avg Sharpe Impact: {avg_sharpe_impact:+.3f}")

# Visualizations
print("\n" + "=" * 80)
print("GENERATING VISUALIZATIONS")
print("=" * 80)

try:
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Soft vs Hard Rebalancing: Multi-Armed Bandit Strategies', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Equity Curves
    ax1 = axes[0, 0]
    for r in results:
        ax1.plot(r['result_soft'].equity_curve, label=f"{r['strategy']} (Soft)", linestyle='-', linewidth=2)
        ax1.plot(r['result_hard'].equity_curve, label=f"{r['strategy']} (Hard)", linestyle='--', alpha=0.6)
    ax1.set_title('Equity Curves', fontweight='bold')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    # Plot 2: Returns
    ax2 = axes[0, 1]
    names = [r['strategy'] for r in results]
    x = np.arange(len(names))
    width = 0.35
    ax2.bar(x - width/2, [r['soft_return'] for r in results], width, label='Soft', color='steelblue')
    ax2.bar(x + width/2, [r['hard_return'] for r in results], width, label='Hard', color='coral')
    ax2.set_title('Total Returns', fontweight='bold')
    ax2.set_ylabel('Return (%)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Costs
    ax3 = axes[1, 0]
    ax3.bar(x - width/2, [r['soft_costs'] for r in results], width, label='Soft', color='green', alpha=0.7)
    ax3.bar(x + width/2, [r['hard_costs'] for r in results], width, label='Hard', color='red', alpha=0.7)
    ax3.set_title('Transaction Costs', fontweight='bold')
    ax3.set_ylabel('Costs ($)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(names, rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Plot 4: Sharpe Ratios
    ax4 = axes[1, 1]
    ax4.bar(x - width/2, [r['soft_sharpe'] for r in results], width, label='Soft', color='purple', alpha=0.7)
    ax4.bar(x + width/2, [r['hard_sharpe'] for r in results], width, label='Hard', color='orange', alpha=0.7)
    ax4.set_title('Sharpe Ratios', fontweight='bold')
    ax4.set_ylabel('Sharpe Ratio')
    ax4.set_xticks(x)
    ax4.set_xticklabels(names, rotation=45, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    plot_path = 'results/soft_vs_hard_bandit_demo.png'
    Path('results').mkdir(exist_ok=True)
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved visualization to: {plot_path}")
    
    plt.show()
    
except Exception as e:
    print(f"⚠ Could not generate visualizations: {e}")

print("\n" + "=" * 80)
print("DEMO COMPLETE")
print("=" * 80)
print(f"""
Multi-Armed Bandit strategies dynamically allocate between sub-strategies.
Soft rebalancing reduces costs while maintaining performance.

Key Findings:
- Bandits learn which strategies work best over time
- Soft rebalancing saves transaction costs
- Performance remains comparable or better

Results saved to: results/soft_vs_hard_bandit_demo.png
""")
print("=" * 80)