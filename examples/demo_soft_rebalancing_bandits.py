"""
Demo: Soft Rebalancing with Multi-Armed Bandit Strategies
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from src.portfolio_engine import PortfolioEngine
from src.data_loader import load_preprocessed_data
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
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
REBALANCE_FREQ = 'Q'

print("=" * 80)
print("SOFT REBALANCING DEMO: MULTI-ARMED BANDIT STRATEGIES")
print("=" * 80)
print(f"\nConfiguration:")
print(f"  Initial Capital: ${INITIAL_CAPITAL:,.0f}")
print(f"  Period: {START_DATE} to {END_DATE}")
print(f"  Rebalancing: {REBALANCE_FREQ} (Quarterly)")
print("\n" + "=" * 80)

# Load data
print("\nLoading data...")
_, prices = load_preprocessed_data(start=START_DATE, end=END_DATE)
print(f"✓ Loaded {len(prices)} days, {len(prices.columns)} tickers")

# Initialize
strategy_gen = Strategy(prices)
optimizer = PortfolioOptimizer(returns=strategy_gen.returns, risk_free_rate=0.02)

# Create candidate strategies
candidate_strategies = [
    ("Max Diversification", MaximumDiversificationStrategy(strategy_gen, optimizer, lookback=252)),
    ("Risk Parity", RiskParityStrategy(strategy_gen, optimizer, lookback=252)),
    ("Inverse Volatility", InverseVolatilityStrategy(strategy_gen, optimizer, lookback=126)),
]

# Create main strategies
strategies = []

# UCB Bandit
ucb_bandit = UCBBandit(n_arms=len(candidate_strategies), exploration_constant=1.0)
ucb_strategy = BanditStrategyWrapper(
    child_strategies=[s[1] for s in candidate_strategies],
    bandit_allocator=ucb_bandit,
    burn_in_periods=4,
    min_allocation=0.20
)
strategies.append(("UCB Bandit", ucb_strategy))

# Thompson Sampling
thompson_bandit = ThompsonSamplingBandit(n_arms=len(candidate_strategies))
thompson_strategy = BanditStrategyWrapper(
    child_strategies=[s[1] for s in candidate_strategies],
    bandit_allocator=thompson_bandit,
    burn_in_periods=4,
    min_allocation=0.20
)
strategies.append(("Thompson Sampling", thompson_strategy))

# Momentum
momentum_strategy = MomentumStrategy(strategy_gen, optimizer, top_k=10, lookback=126)
strategies.append(("Momentum Top-10", momentum_strategy))

print(f"\n✓ Initialized {len(strategies)} strategies")

# Run backtests
results = []

for strategy_name, strategy in strategies:
    print(f"\nRunning: {strategy_name}")
    
    engine = PortfolioEngine(
        prices=prices,
        initial_capital=INITIAL_CAPITAL,
        transaction_cost_bps=10.0,
        slippage_bps=5.0
    )
    
    # Soft
    result_soft = engine.run_backtest(
        strategy_wrapper=strategy,
        start_date=START_DATE,
        end_date=END_DATE,
        rebalance_freq=REBALANCE_FREQ,
        soft_rebalance=True,
        drift_threshold=0.05
    )
    
    # Hard
    result_hard = engine.run_backtest(
        strategy_wrapper=strategy,
        start_date=START_DATE,
        end_date=END_DATE,
        rebalance_freq=REBALANCE_FREQ,
        soft_rebalance=False
    )
    
    soft_metrics = result_soft.summary_metrics
    hard_metrics = result_hard.summary_metrics
    
    results.append({
        'strategy': strategy_name,
        'soft_return': soft_metrics['total_return'] * 100,
        'hard_return': hard_metrics['total_return'] * 100,
        'soft_sharpe': soft_metrics['sharpe_ratio'],
        'hard_sharpe': hard_metrics['sharpe_ratio'],
        'soft_costs': soft_metrics['total_costs'],
        'hard_costs': hard_metrics['total_costs'],
        'cost_savings': hard_metrics['total_costs'] - soft_metrics['total_costs'],
        'result_soft': result_soft,
        'result_hard': result_hard
    })

# Summary
print("\n" + "=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)

for r in results:
    print(f"\n{r['strategy']}:")
    print(f"  Returns: {r['soft_return']:.1f}% (soft) vs {r['hard_return']:.1f}% (hard)")
    print(f"  Sharpe: {r['soft_sharpe']:.3f} (soft) vs {r['hard_sharpe']:.3f} (hard)")
    print(f"  Costs: ${r['soft_costs']:,.0f} (soft) vs ${r['hard_costs']:,.0f} (hard)")
    print(f"  Savings: ${r['cost_savings']:,.0f}")

# Visualizations
print("\n" + "=" * 80)
print("GENERATING VISUALIZATIONS")
print("=" * 80)

try:
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Soft vs Hard Rebalancing: Multi-Armed Bandit Strategies', 
                 fontsize=16, fontweight='bold')
    
    # ========================================
    # Plot 1: Equity Curves
    # ========================================
    ax1 = axes[0, 0]
    
    # Define colors
    colors = ['red', 'green', 'purple']
    
    # Plot hard lines first 
    for i, r in enumerate(results):
        ax1.plot(r['result_soft'].equity_curve, 
                label=f"{r['strategy']} (Soft)", 
                linestyle='-', 
                linewidth=1.5, 
                color=colors[i])
       
    for i, r in enumerate(results):
        ax1.plot(r['result_hard'].equity_curve, 
                label=f"{r['strategy']} (Hard)", 
                linestyle='--', 
                alpha=0.8, 
                linewidth=1.5, 
                color=colors[i])
    
    
   
    
    ax1.set_title('Equity Curves', fontweight='bold', fontsize=12)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(fontsize=8, loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1000:.0f}K'))
    
    # ========================================
    # Plot 2: Returns Comparison
    # ========================================
    ax2 = axes[0, 1]
    
    strategy_names = [r['strategy'] for r in results]
    x_pos = np.arange(len(strategy_names))
    width = 0.35
    
    bars1 = ax2.bar(x_pos - width/2, [r['soft_return'] for r in results], 
                    width, label='Soft', color='steelblue', alpha=0.8)
    bars2 = ax2.bar(x_pos + width/2, [r['hard_return'] for r in results], 
                    width, label='Hard', color='coral', alpha=0.8)
    
    ax2.set_title('Total Returns Comparison', fontweight='bold', fontsize=12)
    ax2.set_xlabel('Strategy')
    ax2.set_ylabel('Total Return (%)')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(strategy_names, rotation=15, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # ========================================
    # Plot 3: Transaction Costs
    # ========================================
    ax3 = axes[1, 0]
    
    bars1 = ax3.bar(x_pos - width/2, [r['soft_costs'] for r in results], 
                    width, label='Soft', color='green', alpha=0.7)
    bars2 = ax3.bar(x_pos + width/2, [r['hard_costs'] for r in results], 
                    width, label='Hard', color='red', alpha=0.7)
    
    ax3.set_title('Transaction Costs Comparison', fontweight='bold', fontsize=12)
    ax3.set_xlabel('Strategy')
    ax3.set_ylabel('Total Costs ($)')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(strategy_names, rotation=15, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # ========================================
    # Plot 4: Sharpe Ratios
    # ========================================
    ax4 = axes[1, 1]
    
    bars1 = ax4.bar(x_pos - width/2, [r['soft_sharpe'] for r in results], 
                    width, label='Soft', color='purple', alpha=0.7)
    bars2 = ax4.bar(x_pos + width/2, [r['hard_sharpe'] for r in results], 
                    width, label='Hard', color='orange', alpha=0.7)
    
    ax4.set_title('Sharpe Ratio Comparison', fontweight='bold', fontsize=12)
    ax4.set_xlabel('Strategy')
    ax4.set_ylabel('Sharpe Ratio')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(strategy_names, rotation=15, ha='right')
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    
    # Save
    plot_path = 'results/soft_vs_hard_bandit_demo_fixed.png'
    Path('results').mkdir(exist_ok=True)
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved visualization to: {plot_path}")
    
    plt.show()
    
except Exception as e:
    print(f"⚠ Could not generate visualizations: {e}")
    import traceback
    traceback.print_exc()

# Print final equity values to verify all strategies ran
print("\n" + "=" * 80)
print("VERIFICATION: Final Equity Values")
print("=" * 80)
for r in results:
    soft_final = r['result_soft'].equity_curve.iloc[-1]
    hard_final = r['result_hard'].equity_curve.iloc[-1]
    print(f"{r['strategy']:<20} Soft: ${soft_final:>10,.0f}  Hard: ${hard_final:>10,.0f}")

print("\n" + "=" * 80)
print("DEMO COMPLETE")
print("=" * 80)