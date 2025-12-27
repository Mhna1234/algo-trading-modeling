"""
Reward Calculation Module for Multi-Armed Bandits

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

Key Principles:
1. **Risk-adjusted rewards are preferred** - Raw returns ignore volatility and tail risk
2. **Clipping prevents outlier domination** - Extreme values shouldn't drive all decisions
3. **NaN handling is critical** - Graceful degradation for missing data
4. **Zero-dependency** - Uses only stdlib (math, typing)

Reward Types:
- Simple Return: Fast, but ignores risk
- Sharpe-like: Balances return and volatility
- Drawdown-penalized: Explicitly penalizes tail risk

Author: GitHub Copilot
Date: December 2025
"""

import math
from typing import Optional, Tuple


def return_to_reward(
    ret: float,
    clip: Tuple[float, float] = (-0.05, 0.05)
) -> float:
    """
    Convert raw return to reward with clipping.
    
    This is the simplest reward function but has significant drawbacks:
    - Ignores volatility (risky strategies look attractive)
    - Ignores tail risk (high Sharpe but large drawdowns)
    - Ignores consistency (lumpy returns vs steady gains)
    
    **When to use:**
    - Very short evaluation periods (1-2 periods)
    - When all strategies have similar risk profiles
    - Quick prototyping or debugging
    
    **Not recommended for production** unless risk is controlled elsewhere.
    
    Parameters
    ----------
    ret : float
        Realized return (e.g., 0.05 for 5% gain)
    clip : Tuple[float, float], default=(-0.05, 0.05)
        (min, max) bounds for reward clipping
        Default clips at ±5% to prevent outlier domination
    
    Returns
    -------
    float
        Clipped reward in range [clip[0], clip[1]]
        Returns 0.0 for NaN inputs
    
    Examples
    --------
    >>> return_to_reward(0.03)  # 3% return
    0.03
    >>> return_to_reward(0.10)  # Clipped to 5%
    0.05
    >>> return_to_reward(-0.08)  # Clipped to -5%
    -0.05
    >>> return_to_reward(float('nan'))  # NaN handling
    0.0
    
    Notes
    -----
    Clipping is essential to prevent a single extreme period from dominating
    the bandit's learning. Without clipping, one lucky trade can cause
    permanent overallocation to a risky strategy.
    """
    # Handle NaN
    if math.isnan(ret):
        return 0.0
    
    # Clip to bounds
    return max(clip[0], min(clip[1], ret))


def sharpe_like_reward(
    ret: float,
    vol: float,
    clip: Tuple[float, float] = (-2.0, 2.0),
    vol_floor: float = 1e-6,
    risk_free_rate: float = 0.0
) -> float:
    """
    Calculate risk-adjusted reward (Sharpe-like ratio).
    
    This is the **recommended default** for most applications. It balances
    return and volatility, preventing the bandit from overallocating to
    high-risk strategies.
    
    Formula: reward = (return - risk_free_rate) / (volatility + vol_floor)
    
    **When to use:**
    - Multi-period evaluation (5+ periods for stable vol estimates)
    - Strategies with varying risk profiles
    - Production deployments (recommended default)
    - When risk-adjusted performance matters
    
    **Advantages:**
    - Penalizes volatile strategies
    - Rewards consistent performance
    - Scale-free (comparable across strategies)
    - Robust to different return magnitudes
    
    **Limitations:**
    - Requires stable volatility estimates (use 5+ periods)
    - Doesn't explicitly penalize drawdowns
    - Can be noisy with very short windows
    
    Parameters
    ----------
    ret : float
        Realized return (e.g., 0.02 for 2% gain)
    vol : float
        Realized volatility (standard deviation of returns)
        Should be > 0 in normal cases
    clip : Tuple[float, float], default=(-2.0, 2.0)
        (min, max) bounds for Sharpe ratio
        Default clips at ±2.0 (reasonable for most strategies)
    vol_floor : float, default=1e-6
        Minimum volatility to prevent division by zero
        Ensures stability even with constant returns
    risk_free_rate : float, default=0.0
        Risk-free rate to subtract for opportunity cost adjustment
    
    Returns
    -------
    float
        Risk-adjusted reward in range [clip[0], clip[1]]
        Returns 0.0 for NaN inputs
    
    Returns
    -------
    float
        Risk-adjusted reward in range [clip[0], clip[1]]
        Returns 0.0 for NaN inputs
    
    Examples
    --------
    >>> sharpe_like_reward(0.02, 0.01)  # 2% return, 1% vol
    2.0
    >>> sharpe_like_reward(0.02, 0.04)  # Same return, higher vol
    0.5
    >>> sharpe_like_reward(0.05, 0.01)  # High Sharpe, clipped
    2.0
    >>> sharpe_like_reward(0.01, 0.0)  # Zero vol handled
    1000000.0  # But clipped to 2.0 in practice
    >>> sharpe_like_reward(float('nan'), 0.01)  # NaN handling
    0.0
    
    Notes
    -----
    The vol_floor prevents division by zero when volatility is extremely low.
    This can happen with:
    - Constant returns over evaluation window
    - Very stable strategies in calm markets
    - Short evaluation windows with limited data
    
    Clipping at ±2.0 is appropriate because:
    - Sharpe ratios > 2.0 are rare for real strategies
    - Prevents single lucky period from dominating
    - Maintains relative ordering (best strategies still ranked correctly)
    """
    # Handle NaN
    if math.isnan(ret) or math.isnan(vol):
        return 0.0
    
    # Handle negative volatility (shouldn't happen, but be safe)
    vol = abs(vol)
    
    # Add floor to prevent division by zero
    vol_safe = max(vol, vol_floor)
    
    # Adjust for opportunity cost
    excess_ret = ret - risk_free_rate
    
    # Calculate Sharpe-like ratio
    sharpe = excess_ret / vol_safe
    
    # Clip to bounds
    return max(clip[0], min(clip[1], sharpe))


def drawdown_penalized_reward(
    ret: float,
    drawdown: float,
    lambda_dd: float = 1.0,
    clip: Tuple[float, float] = (-0.10, 0.10)
) -> float:
    """
    Calculate return minus drawdown penalty.
    
    This explicitly penalizes strategies that experience large drawdowns,
    even if they eventually recover. Useful when tail risk is a primary concern.
    
    Formula: reward = return - lambda_dd * |drawdown|
    
    **When to use:**
    - Tail risk is critical concern (e.g., pension funds, risk-averse clients)
    - Strategies have different drawdown profiles
    - Want to explicitly avoid strategies with large losses
    - Backtests show volatile equity curves
    
    **Advantages:**
    - Explicitly penalizes drawdowns
    - Can be tuned via lambda_dd parameter
    - Intuitive interpretation (return minus risk penalty)
    - Complements Sharpe ratio (addresses different risk dimension)
    
    **Limitations:**
    - Requires accurate drawdown tracking
    - May be too conservative (underallocates to momentum strategies)
    - Drawdown calculation can be noisy over short windows
    
    Parameters
    ----------
    ret : float
        Realized return over evaluation period
    drawdown : float
        Maximum drawdown over evaluation period
        Should be negative (e.g., -0.10 for 10% drawdown)
        If positive, treated as 0 (no drawdown)
    lambda_dd : float, default=1.0
        Drawdown penalty weight
        - lambda_dd=0.0: No penalty (equivalent to raw return)
        - lambda_dd=1.0: Equal weighting of return and drawdown
        - lambda_dd=2.0: Drawdown penalty twice as important
    clip : Tuple[float, float], default=(-0.10, 0.10)
        (min, max) bounds for final reward
        Default clips at ±10% to handle extreme cases
    
    Returns
    -------
    float
        Drawdown-penalized reward in range [clip[0], clip[1]]
        Returns 0.0 for NaN inputs
    
    Examples
    --------
    >>> drawdown_penalized_reward(0.05, -0.02)  # 5% return, 2% DD
    0.03
    >>> drawdown_penalized_reward(0.05, -0.02, lambda_dd=2.0)  # Higher penalty
    0.01
    >>> drawdown_penalized_reward(0.05, 0.0)  # No drawdown
    0.05
    >>> drawdown_penalized_reward(0.05, 0.01)  # Positive DD (treated as 0)
    0.05
    >>> drawdown_penalized_reward(float('nan'), -0.02)  # NaN handling
    0.0
    
    Notes
    -----
    **Choosing lambda_dd:**
    - lambda_dd=0.5: Light penalty, allows some drawdown tolerance
    - lambda_dd=1.0: Balanced (recommended default)
    - lambda_dd=2.0: Conservative, strongly penalizes drawdowns
    - lambda_dd=3.0+: Very conservative, may underallocate to all strategies
    
    **Drawdown conventions:**
    - Drawdown should be negative (e.g., -0.15 for 15% loss from peak)
    - If positive, treated as zero (no penalty applied)
    - Absolute value taken to ensure penalty is always subtracted
    
    **Combination with Sharpe:**
    For maximum robustness, consider using both:
    - Sharpe-like reward: Handles volatility
    - Drawdown penalty: Handles tail risk
    - Can alternate or blend (e.g., 0.7*sharpe + 0.3*dd_penalized)
    """
    # Handle NaN
    if math.isnan(ret) or math.isnan(drawdown):
        return 0.0
    
    # Drawdown should be negative; if positive, treat as zero
    dd_penalty = abs(min(drawdown, 0.0))
    
    # Calculate reward with penalty
    reward = ret - lambda_dd * dd_penalty
    
    # Clip to bounds
    return max(clip[0], min(clip[1], reward))


def multi_objective_reward(
    ret: float,
    vol: float,
    drawdown: float,
    weight_return: float = 0.3,
    weight_sharpe: float = 0.4,
    weight_dd: float = 0.3,
    lambda_dd: float = 1.0,
    clip: Tuple[float, float] = (-1.0, 1.0)
) -> float:
    """
    Combine multiple reward signals with configurable weights.
    
    This is an **advanced option** that blends return, Sharpe, and drawdown
    considerations. Use when you want fine-grained control over the tradeoff
    between different risk dimensions.
    
    Formula: reward = w1*return + w2*sharpe + w3*dd_penalty
    
    **When to use:**
    - Need to balance multiple objectives
    - Have strong preferences on return vs risk vs drawdown
    - Production systems with well-tuned parameters
    - After experimenting with individual reward types
    
    **Not recommended for:**
    - Initial implementations (use sharpe_like_reward first)
    - Short evaluation windows (< 10 periods)
    - When unsure about weight selection
    
    Parameters
    ----------
    ret : float
        Realized return
    vol : float
        Realized volatility
    drawdown : float
        Maximum drawdown (should be negative)
    weight_return : float, default=0.3
        Weight for raw return component
    weight_sharpe : float, default=0.4
        Weight for Sharpe ratio component
    weight_dd : float, default=0.3
        Weight for drawdown penalty component
    lambda_dd : float, default=1.0
        Drawdown penalty multiplier
    clip : Tuple[float, float], default=(-1.0, 1.0)
        Final reward bounds
    
    Returns
    -------
    float
        Combined reward in range [clip[0], clip[1]]
    
    Examples
    --------
    >>> multi_objective_reward(0.02, 0.01, -0.03)
    # Combines all three components with default weights
    
    Notes
    -----
    Weights should sum to 1.0 for interpretability, but this is not enforced.
    Default weights (0.3, 0.4, 0.3) give slight preference to Sharpe ratio.
    """
    # Handle NaN
    if any(math.isnan(x) for x in [ret, vol, drawdown]):
        return 0.0
    
    # Compute individual components (unclipped)
    raw_return = ret
    sharpe = sharpe_like_reward(ret, vol, clip=(-10.0, 10.0))  # Wider clip for combination
    dd_pen = drawdown_penalized_reward(ret, drawdown, lambda_dd=lambda_dd, clip=(-1.0, 1.0))
    
    # Weighted combination
    combined = (
        weight_return * raw_return +
        weight_sharpe * sharpe * 0.05 +  # Scale down Sharpe to match return magnitude
        weight_dd * dd_pen
    )
    
    # Clip final result
    return max(clip[0], min(clip[1], combined))


# Convenience function for BanditStrategyWrapper integration
def compute_reward(
    ret: float,
    vol: Optional[float] = None,
    drawdown: Optional[float] = None,
    reward_type: str = 'sharpe'
) -> float:
    """
    Compute reward using specified type and available data.
    
    This is a convenience wrapper for use in BanditStrategyWrapper.
    
    Parameters
    ----------
    ret : float
        Realized return
    vol : Optional[float]
        Realized volatility (required for 'sharpe')
    drawdown : Optional[float]
        Maximum drawdown (required for 'drawdown')
    reward_type : str, default='sharpe'
        Type of reward: 'return', 'sharpe', 'drawdown', 'multi'
    
    Returns
    -------
    float
        Computed reward based on type
    
    Raises
    ------
    ValueError
        If required data missing for reward_type
    """
    if reward_type == 'return':
        return return_to_reward(ret)
    
    elif reward_type == 'sharpe':
        if vol is None:
            raise ValueError("volatility required for sharpe reward type")
        return sharpe_like_reward(ret, vol)
    
    elif reward_type == 'drawdown':
        if drawdown is None:
            raise ValueError("drawdown required for drawdown reward type")
        return drawdown_penalized_reward(ret, drawdown)
    
    elif reward_type == 'multi':
        if vol is None or drawdown is None:
            raise ValueError("volatility and drawdown required for multi reward type")
        return multi_objective_reward(ret, vol, drawdown)
    
    else:
        raise ValueError(f"Unknown reward_type: {reward_type}")
