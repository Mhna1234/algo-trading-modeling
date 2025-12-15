"""
Comparison demonstration: UCB vs Thompson Sampling.

Shows how both algorithms behave on the same problem.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bandits import UCBBandit, ThompsonSamplingBandit


def simulate_strategy_rewards(arm: int, t: int) -> float:
    """
    Simulate rewards for different strategies.
    
    Strategy rewards:
    - Strategy 0: mean=0.05, low variance
    - Strategy 1: mean=0.10, medium variance
    - Strategy 2: mean=0.15, low variance (best!)
    """
    import math
    
    base_rewards = [0.05, 0.10, 0.15]
    noise_scale = [0.02, 0.05, 0.02]
    noise = math.sin(t * 0.5 + arm) * noise_scale[arm]
    
    return base_rewards[arm] + noise


def run_bandit(bandit, name, n_periods=50):
    """Run simulation for a bandit."""
    print(f"\n{'='*60}")
    print(f"{name}")
    print(f"{'='*60}\n")
    
    cumulative_reward = 0.0
    
    for t in range(n_periods):
        arm = bandit.select_arm(t)
        reward = simulate_strategy_rewards(arm, t)
        bandit.update(arm, reward)
        cumulative_reward += reward
    
    # Final statistics
    stats = bandit.get_arm_statistics()
    
    print(f"Total selections: {sum(stats['counts'])}")
    print(f"Cumulative reward: {cumulative_reward:.4f}")
    print(f"Average reward: {cumulative_reward / n_periods:.4f}")
    print()
    
    print("Per-strategy statistics:")
    for arm in range(len(stats['counts'])):
        pct = stats['counts'][arm] / n_periods * 100
        if 'means' in stats:
            print(f"  Strategy {arm}: {stats['counts'][arm]:2d} selections ({pct:5.1f}%), "
                  f"mean={stats['means'][arm]:.4f}")
        else:
            print(f"  Strategy {arm}: {stats['counts'][arm]:2d} selections ({pct:5.1f}%), "
                  f"value={stats['values'][arm]:.4f}")
    
    best_arm = max(range(len(stats['counts'])), 
                   key=lambda i: stats.get('means', stats.get('values', [0]*len(stats['counts'])))[i])
    print(f"\nBest strategy identified: Strategy {best_arm}")
    
    return cumulative_reward, stats


def main():
    """Run comparison between UCB and Thompson Sampling."""
    
    print("=" * 60)
    print("UCB vs Thompson Sampling Comparison")
    print("=" * 60)
    print("\nProblem: 3 strategies with different mean rewards")
    print("- Strategy 0: mean=0.05 (poor)")
    print("- Strategy 1: mean=0.10 (medium)")
    print("- Strategy 2: mean=0.15 (best)")
    print()
    
    n_strategies = 3
    n_periods = 50
    
    # Run UCB
    ucb_bandit = UCBBandit(n_arms=n_strategies, exploration_constant=1.0)
    ucb_reward, ucb_stats = run_bandit(ucb_bandit, "UCB Algorithm (Deterministic)", n_periods)
    
    # Run Thompson Sampling
    ts_bandit = ThompsonSamplingBandit(
        n_arms=n_strategies,
        random_seed=42  # For reproducibility
    )
    ts_reward, ts_stats = run_bandit(ts_bandit, "Thompson Sampling (Bayesian)", n_periods)
    
    # Comparison
    print("\n" + "=" * 60)
    print("Comparison Summary")
    print("=" * 60)
    print()
    
    print(f"UCB cumulative reward:        {ucb_reward:.4f}")
    print(f"Thompson cumulative reward:   {ts_reward:.4f}")
    print(f"Difference:                   {ts_reward - ucb_reward:+.4f}")
    print()
    
    print("Strategy 2 (best) selection rate:")
    ucb_best_pct = ucb_stats['counts'][2] / n_periods * 100
    ts_best_pct = ts_stats['counts'][2] / n_periods * 100
    print(f"  UCB:              {ucb_best_pct:.1f}%")
    print(f"  Thompson Sampling: {ts_best_pct:.1f}%")
    print()
    
    print("Key Differences:")
    print("  • UCB: Deterministic, forced exploration, confidence bounds")
    print("  • Thompson: Stochastic, natural exploration, Bayesian sampling")
    print("  • Both converge to best strategy over time")
    print()
    
    print("=" * 60)


if __name__ == '__main__':
    main()
