"""
Simple demonstration of UCBBandit usage.

This script shows how to use the bandit module for strategy selection
without any trading infrastructure dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bandits import UCBBandit


def simulate_strategy_rewards(arm: int, t: int) -> float:
    """
    Simulate rewards for different strategies.
    
    In reality, these would come from actual strategy performance,
    but for demonstration we use synthetic rewards:
    - Strategy 0: Low mean (0.05), low variance
    - Strategy 1: Medium mean (0.10), medium variance
    - Strategy 2: High mean (0.15), low variance (best!)
    """
    import math
    
    # Base rewards (true means)
    base_rewards = [0.05, 0.10, 0.15]
    
    # Add some noise (variance)
    noise_scale = [0.02, 0.05, 0.02]
    noise = math.sin(t * 0.5 + arm) * noise_scale[arm]
    
    return base_rewards[arm] + noise


def main():
    """Run simple UCB bandit demonstration."""
    
    print("=" * 60)
    print("UCB Bandit Demonstration")
    print("=" * 60)
    print()
    
    # Initialize bandit with 3 strategies
    n_strategies = 3
    bandit = UCBBandit(n_arms=n_strategies, exploration_constant=1.0)
    
    print(f"Initialized {bandit}")
    print(f"Number of strategies: {n_strategies}")
    print()
    
    # Run simulation for 50 periods
    n_periods = 50
    print(f"Running simulation for {n_periods} periods...")
    print()
    
    cumulative_reward = 0.0
    
    for t in range(n_periods):
        # Select strategy
        selected_arm = bandit.select_arm(t)
        
        # Simulate reward (in real system, this comes from portfolio performance)
        reward = simulate_strategy_rewards(selected_arm, t)
        
        # Update bandit
        bandit.update(selected_arm, reward)
        
        cumulative_reward += reward
        
        # Print progress every 10 periods
        if (t + 1) % 10 == 0:
            stats = bandit.get_arm_statistics()
            print(f"Period {t+1:2d}:")
            print(f"  Selected: Strategy {selected_arm}")
            print(f"  Reward: {reward:.4f}")
            print(f"  Cumulative: {cumulative_reward:.4f}")
            print(f"  Selection counts: {stats['counts']}")
            print(f"  Average rewards: {[f'{v:.4f}' for v in stats['values']]}")
            print()
    
    # Final statistics
    print("=" * 60)
    print("Final Statistics")
    print("=" * 60)
    print()
    
    stats = bandit.get_arm_statistics()
    
    print(f"Total selections: {bandit.total_selections}")
    print(f"Cumulative reward: {cumulative_reward:.4f}")
    print(f"Average reward: {cumulative_reward / n_periods:.4f}")
    print()
    
    print("Per-strategy statistics:")
    for arm in range(n_strategies):
        print(f"  Strategy {arm}:")
        print(f"    Selections: {stats['counts'][arm]} ({stats['counts'][arm]/n_periods*100:.1f}%)")
        print(f"    Average reward: {stats['values'][arm]:.4f}")
        print(f"    UCB score: {stats['ucb_scores'][arm]:.4f}")
    
    print()
    best_arm = max(range(n_strategies), key=lambda i: stats['values'][i])
    print(f"Best strategy: Strategy {best_arm} (mean reward: {stats['values'][best_arm]:.4f})")
    
    # Test serialization
    print()
    print("=" * 60)
    print("Testing State Persistence")
    print("=" * 60)
    print()
    
    # Save state
    state = bandit.get_state()
    print("Saved bandit state")
    
    # Create new bandit and restore
    new_bandit = UCBBandit(n_arms=n_strategies)
    new_bandit.set_state(state)
    print("Restored state to new bandit instance")
    
    # Verify restoration
    new_stats = new_bandit.get_arm_statistics()
    match = (stats['counts'] == new_stats['counts'] and 
             all(abs(a - b) < 1e-10 for a, b in zip(stats['values'], new_stats['values'])))
    
    print(f"State restoration: {'✓ SUCCESS' if match else '✗ FAILED'}")
    print()
    
    print("=" * 60)
    print("Demonstration Complete")
    print("=" * 60)


if __name__ == '__main__':
    main()
