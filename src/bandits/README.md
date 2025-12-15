# Bandits Module

Multi-Armed Bandit algorithms for dynamic strategy allocation.

## Overview

This module provides bandit algorithms for learning which trading strategies to allocate capital to, balancing exploration (trying uncertain strategies) with exploitation (using proven strategies).

**Key Design Principles:**
- **Zero dependencies** on market data, pandas, or trading logic
- **Pure algorithms** that operate on arm indices and scalar rewards
- **Deterministic** for reproducible backtests
- **Numerically stable** for production use
- **Well-tested** with comprehensive unit tests

## Architecture

```
src/bandits/
├── __init__.py          # Public API
├── base.py              # BanditAllocator abstract base class
└── ucb.py               # UCB1 algorithm implementation

tests/
├── test_bandit_allocator.py  # Base class tests
└── test_ucb_bandit.py         # UCB algorithm tests

examples/
└── demo_ucb_bandit.py         # Usage demonstration
```

## Installation

The module is part of the algo-trading-modeling project. No additional dependencies required.

```bash
# Run tests to verify installation
python -m pytest tests/test_bandit_allocator.py tests/test_ucb_bandit.py -v
```

## Usage

### Basic Example

```python
from src.bandits import UCBBandit

# Initialize bandit with 5 strategies
bandit = UCBBandit(n_arms=5, exploration_constant=1.0)

# Main loop
for t in range(100):
    # Select strategy to use
    strategy_idx = bandit.select_arm(t)
    
    # Execute strategy and observe performance
    # (In real system, this comes from portfolio returns)
    reward = get_strategy_performance(strategy_idx)
    
    # Update bandit's beliefs
    bandit.update(strategy_idx, reward)

# Get statistics
stats = bandit.get_arm_statistics()
print(f"Selection counts: {stats['counts']}")
print(f"Average rewards: {stats['values']}")
```

### State Persistence

```python
# Save bandit state
state = bandit.get_state()
import json
with open('bandit_state.json', 'w') as f:
    json.dump(state, f)

# Restore bandit state
with open('bandit_state.json', 'r') as f:
    state = json.load(f)
    
new_bandit = UCBBandit(n_arms=5)
new_bandit.set_state(state)
```

## Algorithms

### UCB1 (Upper Confidence Bound) - DEFAULT

**Formula:**
```
UCB_k = mean_k + c * sqrt(2 * ln(t) / n_k)
```

Where:
- `mean_k`: average reward for strategy k
- `c`: exploration constant (default 1.0)
- `t`: total number of selections
- `n_k`: number of times strategy k was selected

**Properties:**
- ✅ Deterministic (reproducible backtests)
- ✅ Forces exploration of untried arms
- ✅ Numerically stable
- ✅ Strong theoretical regret bounds
- ✅ No hyperparameters to tune (c=1.0 works well)

**Parameters:**
- `exploration_constant`: Higher = more exploration (try 0.5-2.0)
  - 0.5: More exploitation (prefer proven strategies)
  - 1.0: Balanced (recommended default)
  - 2.0: More exploration (try uncertain strategies)

**When to use:**
- Default choice for most scenarios
- When you need deterministic, reproducible results
- When you want interpretable decision-making

## API Reference

### BanditAllocator (Base Class)

Abstract base class defining the bandit interface.

**Methods:**
- `__init__(n_arms: int)`: Initialize with N arms
- `select_arm(t: int) -> int`: Select arm at time t
- `update(arm: int, reward: float) -> None`: Update after observing reward
- `get_state() -> dict`: Get serializable state
- `set_state(state: dict) -> None`: Restore from state
- `reset() -> None`: Reset to initial state

**Constraints:**
- `n_arms` must be ≥ 2
- `arm` must be in range [0, n_arms-1]
- `reward` can be any float (negative, zero, positive)

### UCBBandit

UCB1 algorithm implementation.

**Initialization:**
```python
UCBBandit(
    n_arms: int,                      # Number of strategies
    exploration_constant: float = 1.0 # Exploration bonus (> 0)
)
```

**Additional Methods:**
- `get_arm_statistics() -> dict`: Get detailed statistics
  - Returns: `{'counts': [...], 'values': [...], 'ucb_scores': [...]}`

**Attributes:**
- `counts`: Selection count per arm
- `values`: Average reward per arm
- `total_selections`: Total selections made

## Testing

### Run All Tests

```bash
# Run all bandit tests
python -m pytest tests/test_bandit_allocator.py tests/test_ucb_bandit.py -v

# Run with coverage
python -m pytest tests/test_bandit_allocator.py tests/test_ucb_bandit.py --cov=src/bandits --cov-report=term-missing
```

### Test Categories

**Base Class Tests (15 tests):**
- Initialization validation
- Arm index validation
- State persistence
- Interface compliance

**UCB Algorithm Tests (24 tests):**
- Forced exploration
- Exploitation after exploration
- Numerical stability
- Deterministic behavior
- Convergence properties
- Edge cases

All tests:
- ✅ Fast (<2 seconds total)
- ✅ Deterministic (no randomness)
- ✅ Pure (no I/O, no pandas, no market data)

## Integration with Trading System

The bandits module is designed to be used by `BanditStrategyWrapper` (to be implemented) which will:

1. Own a collection of child strategies
2. Use `BanditAllocator` to decide which strategy to allocate capital to
3. Calculate rewards based on strategy performance (risk-adjusted returns)
4. Update the bandit after each rebalancing period

**Key Separation:**
- **Bandits module**: Pure algorithm logic (this module)
- **BanditStrategyWrapper**: Trading integration (future implementation)

This separation enables:
- Testing algorithms in isolation
- Reusing algorithms across different trading frameworks
- Swapping algorithms without changing trading logic

## Design Constraints

### Zero Market Data Dependencies

```python
# ✓ GOOD: Pure bandit logic
bandit = UCBBandit(n_arms=5)
arm = bandit.select_arm(t=10)
bandit.update(arm, reward=0.15)

# ✗ BAD: Don't do this in bandit module
bandit.update_with_prices(arm, prices_df)  # NO PANDAS
bandit.calculate_sharpe(returns)           # NO MARKET LOGIC
```

The bandit receives **scalar rewards** only. All market data processing happens in the strategy wrapper layer.

### Determinism

All algorithms must be deterministic for backtesting reproducibility:
- Same inputs → same outputs
- No randomness without seed control
- Stable numerical algorithms

### Performance

Algorithms must be fast enough for real-time trading:
- O(n_arms) per selection
- O(1) per update
- Minimal memory allocation

## Future Extensions

Potential algorithms to add (not in current scope):

1. **Thompson Sampling**: Bayesian approach with Beta distributions
2. **Epsilon-Greedy**: Simple baseline for comparison
3. **Sliding Window UCB**: Forget old observations for non-stationary environments
4. **Discounted UCB**: Exponential decay for recent performance weighting

All extensions should follow the same design principles:
- Implement `BanditAllocator` interface
- Add comprehensive unit tests
- Maintain zero external dependencies
- Ensure deterministic behavior

## References

- **Academic**: Auer et al. (2002), "Finite-time Analysis of the Multi-armed Bandit Problem"
- **Implementation Plan**: `docs/MAB_IMPLEMENTATION_PLAN.md`
- **Technical Map**: `docs/MAB_TECHNICAL_MAP.md`
- **Theory**: `docs/MULTI_ARMED_BANDITS.md`

## Support

For questions or issues:
1. Check unit tests for usage examples
2. Run `examples/demo_ucb_bandit.py` for demonstration
3. Review implementation plan in `docs/`

---

**Version**: 1.0  
**Last Updated**: December 15, 2025  
**Status**: Production Ready
