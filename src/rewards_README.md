# Reward Calculation Module

Lightweight reward functions for evaluating strategy performance in multi-armed bandit allocation.

## Overview

This module provides three main reward calculation methods, each with different risk-return tradeoffs:

1. **Simple Return** - Fast, but ignores risk
2. **Sharpe-like Reward** - Risk-adjusted (recommended default)
3. **Drawdown-penalized** - Explicitly penalizes tail risk

## Quick Start

```python
from src.rewards import (
    return_to_reward,
    sharpe_like_reward,
    drawdown_penalized_reward,
    compute_reward  # Convenience wrapper
)

# Simple return (not recommended for production)
reward1 = return_to_reward(0.03)  # 3% return → 0.03 reward

# Sharpe-like (RECOMMENDED DEFAULT)
reward2 = sharpe_like_reward(0.03, 0.01)  # 3% return, 1% vol → 2.0 Sharpe

# Drawdown-penalized
reward3 = drawdown_penalized_reward(0.05, -0.02)  # 5% return, 2% DD → 0.03

# Convenience wrapper
reward4 = compute_reward(0.03, vol=0.01, reward_type='sharpe')
```

## Function Reference

### 1. Simple Return Reward

```python
return_to_reward(ret, clip=(-0.05, 0.05))
```

**When to use:**
- Very short evaluation periods (1-2 periods)
- All strategies have similar risk profiles
- Quick prototyping or debugging

**Not recommended for production** - ignores volatility and tail risk.

**Example:**
```python
>>> return_to_reward(0.03)
0.03
>>> return_to_reward(0.10)  # Clipped
0.05
```

---

### 2. Sharpe-like Reward ⭐ RECOMMENDED

```python
sharpe_like_reward(ret, vol, clip=(-2.0, 2.0), vol_floor=1e-6)
```

**When to use:**
- Multi-period evaluation (5+ periods)
- Strategies with varying risk profiles
- **Production deployments (recommended default)**
- When risk-adjusted performance matters

**Advantages:**
- ✅ Penalizes volatile strategies
- ✅ Rewards consistent performance
- ✅ Scale-free (comparable across strategies)
- ✅ Robust to different return magnitudes

**Example:**
```python
>>> sharpe_like_reward(0.02, 0.01)  # 2% return, 1% vol
2.0
>>> sharpe_like_reward(0.02, 0.04)  # Same return, higher vol
0.5
```

---

### 3. Drawdown-penalized Reward

```python
drawdown_penalized_reward(ret, drawdown, lambda_dd=1.0, clip=(-0.10, 0.10))
```

**When to use:**
- Tail risk is critical concern
- Want to explicitly avoid large losses
- Strategies have different drawdown profiles

**Formula:** `reward = return - lambda_dd * |drawdown|`

**Lambda tuning:**
- `lambda_dd=0.5` - Light penalty
- `lambda_dd=1.0` - Balanced (default)
- `lambda_dd=2.0` - Conservative
- `lambda_dd=3.0+` - Very conservative

**Example:**
```python
>>> drawdown_penalized_reward(0.05, -0.02)  # 5% return, 2% DD
0.03
>>> drawdown_penalized_reward(0.05, -0.02, lambda_dd=2.0)  # Higher penalty
0.01
```

---

### 4. Multi-objective Reward (Advanced)

```python
multi_objective_reward(ret, vol, drawdown, 
                       weight_return=0.3, weight_sharpe=0.4, weight_dd=0.3)
```

Combines all three reward types with configurable weights.

**When to use:**
- Need fine-grained control
- Production systems with well-tuned parameters
- After experimenting with individual types

**Not recommended for initial implementations.**

---

### 5. Convenience Wrapper

```python
compute_reward(ret, vol=None, drawdown=None, reward_type='sharpe')
```

Automatically selects the appropriate reward function based on `reward_type`.

**Supported types:**
- `'return'` - Simple return
- `'sharpe'` - Sharpe-like (default, recommended)
- `'drawdown'` - Drawdown-penalized
- `'multi'` - Multi-objective

**Example:**
```python
>>> compute_reward(0.03, vol=0.01, reward_type='sharpe')
2.0
```

## Edge Case Handling

All functions gracefully handle:

✅ **NaN values** - Return 0.0  
✅ **Zero volatility** - Use vol_floor to prevent division by zero  
✅ **Extreme values** - Clipping prevents outlier domination  
✅ **Negative volatility** - Take absolute value  
✅ **Infinity** - Clipped to bounds  

## Choosing Clip Bounds

### Return clipping
Default: `(-0.05, 0.05)` = ±5%
- Prevents single extreme period from dominating
- Adjust based on strategy volatility

### Sharpe clipping
Default: `(-2.0, 2.0)`
- Sharpe > 2.0 rare for real strategies
- Maintains relative ordering
- Consider `(-3.0, 3.0)` for very stable strategies

### Drawdown clipping
Default: `(-0.10, 0.10)` = ±10%
- Handles extreme drawdown scenarios
- Prevents excessive penalty

## Best Practices

### ✅ DO:
- Use `sharpe_like_reward()` as default
- Clip rewards to prevent outlier domination
- Use 5+ periods for stable volatility estimates
- Test with historical data before deployment

### ❌ DON'T:
- Use raw returns in production (ignores risk)
- Set clip bounds too wide (outliers dominate)
- Calculate rewards over < 3 periods (noisy)
- Ignore NaN handling (will cause crashes)

## Integration Example

```python
from src.rewards import sharpe_like_reward
from src.bandits import UCBBandit

# Setup
bandit = UCBBandit(n_arms=3)
strategy_returns = [0.02, 0.03, 0.01]
strategy_vols = [0.01, 0.02, 0.01]

# Calculate rewards
for arm_idx in range(3):
    reward = sharpe_like_reward(
        ret=strategy_returns[arm_idx],
        vol=strategy_vols[arm_idx]
    )
    bandit.update(arm_idx, reward)

# Select next strategy
next_arm = bandit.select_arm(t=10)
```

## Testing

Run comprehensive tests:
```bash
pytest tests/test_rewards.py -v
```

Tests cover:
- ✅ Basic functionality (59 tests)
- ✅ Clipping behavior
- ✅ Edge cases (zero vol, NaN, infinity)
- ✅ Numerical stability
- ✅ Ordering preservation

## Dependencies

**Zero external dependencies** - uses only Python stdlib:
- `math` - For isnan() and basic operations
- `typing` - For type hints

## Performance

All functions are **lightweight and fast**:
- No pandas/numpy required
- O(1) time complexity
- Suitable for real-time usage

## References

- Sutton & Barto (2018). "Reinforcement Learning: An Introduction"
- Agarwal et al. (2014). "Taming the Monster: A Fast and Simple Algorithm for Contextual Bandits"

---

**Version:** 1.0  
**Author:** GitHub Copilot  
**Date:** December 2025
