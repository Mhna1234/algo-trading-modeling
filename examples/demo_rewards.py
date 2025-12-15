"""
Simple example demonstrating reward calculations

This example shows how to use the reward module to evaluate
strategy performance over multiple periods.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.rewards import (
    return_to_reward,
    sharpe_like_reward,
    drawdown_penalized_reward,
    compute_reward
)

def main():
    print("=" * 70)
    print("Reward Calculation Examples")
    print("=" * 70)
    print()
    
    # Example strategy returns over 10 periods
    strategy_a_returns = [0.02, 0.03, -0.01, 0.04, 0.01, 0.02, -0.02, 0.03, 0.01, 0.02]
    strategy_b_returns = [0.05, -0.03, 0.08, -0.04, 0.06, -0.02, 0.07, -0.01, 0.04, 0.03]
    
    print("Strategy A: Consistent returns")
    print(f"Returns: {strategy_a_returns}")
    print()
    
    print("Strategy B: Volatile returns")
    print(f"Returns: {strategy_b_returns}")
    print()
    print("-" * 70)
    
    # Calculate statistics
    import math
    
    def calc_stats(returns):
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        vol = math.sqrt(variance)
        
        # Calculate drawdown
        cumulative = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            cumulative *= (1 + r)
            peak = max(peak, cumulative)
            dd = (cumulative - peak) / peak
            max_dd = min(max_dd, dd)
        
        return mean, vol, max_dd
    
    mean_a, vol_a, dd_a = calc_stats(strategy_a_returns)
    mean_b, vol_b, dd_b = calc_stats(strategy_b_returns)
    
    print(f"\nStrategy A Statistics:")
    print(f"  Mean return:    {mean_a:>7.2%}")
    print(f"  Volatility:     {vol_a:>7.2%}")
    print(f"  Max drawdown:   {dd_a:>7.2%}")
    
    print(f"\nStrategy B Statistics:")
    print(f"  Mean return:    {mean_b:>7.2%}")
    print(f"  Volatility:     {vol_b:>7.2%}")
    print(f"  Max drawdown:   {dd_b:>7.2%}")
    
    print()
    print("=" * 70)
    print("Reward Calculations")
    print("=" * 70)
    
    # 1. Simple return reward
    print("\n1. Simple Return Reward (NOT RECOMMENDED)")
    print("-" * 70)
    return_a = return_to_reward(mean_a)
    return_b = return_to_reward(mean_b)
    print(f"Strategy A: {return_a:>7.4f}")
    print(f"Strategy B: {return_b:>7.4f}")
    print(f"Winner: {'B' if return_b > return_a else 'A'}")
    print("⚠️  B wins due to higher return, ignoring volatility!")
    
    # 2. Sharpe-like reward (RECOMMENDED)
    print("\n2. Sharpe-like Reward (RECOMMENDED)")
    print("-" * 70)
    sharpe_a = sharpe_like_reward(mean_a, vol_a)
    sharpe_b = sharpe_like_reward(mean_b, vol_b)
    print(f"Strategy A: {sharpe_a:>7.4f}")
    print(f"Strategy B: {sharpe_b:>7.4f}")
    print(f"Winner: {'B' if sharpe_b > sharpe_a else 'A'}")
    print("✓ A wins due to better risk-adjusted performance!")
    
    # 3. Drawdown-penalized reward
    print("\n3. Drawdown-penalized Reward")
    print("-" * 70)
    dd_pen_a = drawdown_penalized_reward(mean_a, dd_a, lambda_dd=1.0)
    dd_pen_b = drawdown_penalized_reward(mean_b, dd_b, lambda_dd=1.0)
    print(f"Strategy A: {dd_pen_a:>7.4f}")
    print(f"Strategy B: {dd_pen_b:>7.4f}")
    print(f"Winner: {'B' if dd_pen_b > dd_pen_a else 'A'}")
    print("✓ A wins due to lower drawdown!")
    
    # 4. Demonstrate clipping
    print("\n4. Clipping Demonstration")
    print("-" * 70)
    extreme_return = 0.50  # 50% return
    print(f"Extreme return: {extreme_return:.1%}")
    print(f"  Without clipping: {extreme_return:.4f}")
    print(f"  With clipping:    {return_to_reward(extreme_return):.4f}")
    print("✓ Clipping prevents outlier domination!")
    
    # 5. Edge case handling
    print("\n5. Edge Case Handling")
    print("-" * 70)
    print(f"NaN input:        {sharpe_like_reward(float('nan'), 0.01):.4f}")
    print(f"Zero volatility:  {sharpe_like_reward(0.01, 0.0):.4f}")
    print(f"Negative vol:     {sharpe_like_reward(0.01, -0.01):.4f}")
    print("✓ All edge cases handled gracefully!")
    
    # 6. Using compute_reward wrapper
    print("\n6. Convenience Wrapper (compute_reward)")
    print("-" * 70)
    reward_type = 'sharpe'
    reward = compute_reward(mean_a, vol=vol_a, reward_type=reward_type)
    print(f"Strategy A with '{reward_type}' type: {reward:.4f}")
    print("✓ Convenient interface for BanditStrategyWrapper!")
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print("""
Recommendation: Use sharpe_like_reward() as default

Why?
  • Balances return and risk
  • Penalizes volatile strategies
  • Scale-free and comparable across strategies
  • Robust and well-tested

When to use alternatives:
  • return_to_reward(): Only for debugging/prototyping
  • drawdown_penalized_reward(): When tail risk is critical
  • multi_objective_reward(): Advanced tuning after testing
    """)
    
    print("=" * 70)
    print("Example Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
