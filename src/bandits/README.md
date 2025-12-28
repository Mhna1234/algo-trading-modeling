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
├── __init__.py              # Public API
├── base.py                  # BanditAllocator abstract base class
├── ucb.py                   # UCB1 algorithm implementation
├── thompson.py              # Thompson Sampling implementation
├── exp3.py                  # EXP3 algorithm implementation
├── epsilon_greedy.py        # ε-Greedy algorithm implementation
└── README.md                # This documentation

tests/
├── test_bandit_allocator.py     # Base class tests
├── test_ucb_bandit.py           # UCB algorithm tests
├── test_thompson_bandit.py      # Thompson Sampling tests
├── test_exp3_bandit.py          # EXP3 algorithm tests
└── test_epsilon_greedy_bandit.py # ε-Greedy algorithm tests

examples/
├── mab_comparison_demo.py       # Comprehensive algorithm comparison
└── simple_example.py            # Basic usage examples
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
from src.bandits import UCBBandit, ThompsonSamplingBandit, EXP3Bandit, EpsilonGreedy

# Initialize different bandit algorithms
algorithms = {
    'UCB': UCBBandit(n_arms=5, exploration_constant=1.0),
    'Thompson': ThompsonSamplingBandit(n_arms=5, random_seed=42),
    'EXP3': EXP3Bandit(n_arms=5, gamma=0.1),
    'EpsilonGreedy': EpsilonGreedy(n_arms=5, epsilon=0.1)
}

# Main loop for each algorithm
for name, bandit in algorithms.items():
    print(f"\n=== {name} Algorithm ===")
    for t in range(20):
        # Select strategy to use
        strategy_idx = bandit.select_arm(t)
        
        # Execute strategy and observe performance
        # (In real system, this comes from portfolio returns)
        reward = get_strategy_performance(strategy_idx)
        
        # Update bandit's beliefs
        bandit.update(strategy_idx, reward)
    
    # Get statistics
    if hasattr(bandit, 'get_arm_statistics'):
        stats = bandit.get_arm_statistics()
        print(f"Selection counts: {stats['counts']}")
        if 'means' in stats:
            print(f"Average rewards: {stats['means']}")
        elif 'values' in stats:
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

### Thompson Sampling (Bayesian)

**Algorithm:**
1. Maintain posterior distribution N(μ_k, σ²_k) for each arm
2. Sample θ_k ~ N(μ_k, σ²_k) from each posterior
3. Select arm with highest sample: argmax_k θ_k

**Properties:**
- ✅ Excellent empirical performance
- ✅ Natural exploration (wide posterior = more sampling)
- ✅ Handles noisy continuous rewards well
- ✅ No hyperparameters to tune
- ⚠️ Stochastic (requires random seed for reproducibility)

**Parameters:**
- `prior_mean`: Prior belief about arm means (default 0.0)
- `prior_std`: Prior standard deviation (default 1.0)
- `known_reward_std`: Known reward standard deviation (default 1.0)
- `random_seed`: Seed for reproducibility (default None)

**When to use:**
- When rewards are noisy/continuous
- When you want faster convergence to best arm
- When you don't need perfect reproducibility (or can set seed)
- For non-stationary environments (adapts quickly)

### EXP3 (Exponential-weight algorithm for Exploration and Exploitation)

**Algorithm:**
1. Maintain probability distribution p_k over arms
2. Sample arm according to p_k
3. Update weights using exponential update rule

**Formula:**
```
p_k = (1-γ) * w_k / sum(w_j) + γ/n_arms
w_k *= exp(γ * estimated_reward_k / n_arms)
```

**Properties:**
- ✅ Handles adversarial/non-stationary environments
- ✅ No reward distribution assumptions
- ✅ Good for changing reward landscapes
- ⚠️ More complex parameter tuning

**Parameters:**
- `gamma`: Exploration parameter (0 < gamma < 1)
  - 0.01-0.1: Conservative exploration
  - 0.1-0.3: Balanced
  - 0.3-0.5: Aggressive exploration

**When to use:**
- When the environment may be adversarial
- When rewards change over time (non-stationary)
- When you want robustness to changing conditions

### ε-Greedy

**Algorithm:**
1. With probability ε: explore (select random arm)
2. With probability 1-ε: exploit (select best arm so far)

**Properties:**
- ✅ Simple and intuitive
- ✅ Easy to understand and implement
- ✅ Good baseline algorithm
- ⚠️ Can be suboptimal in some scenarios

**Parameters:**
- `epsilon`: Exploration probability (0 ≤ epsilon ≤ 1)
  - 0.0: Pure exploitation
  - 0.1: 10% exploration (recommended)
  - 0.2: 20% exploration

**When to use:**
- As a simple baseline for comparison
- When you want very simple, interpretable behavior
- For educational purposes or initial testing

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

### ThompsonSamplingBandit

Thompson Sampling with Bayesian normal model.

**Initialization:**
```python
ThompsonSamplingBandit(
    n_arms: int,                      # Number of strategies
    prior_mean: float = 0.0,          # Prior belief about means
    prior_std: float = 1.0,           # Prior standard deviation (> 0)
    known_reward_std: float = 1.0,    # Known reward standard deviation (> 0)
    random_seed: Optional[int] = None # Seed for reproducibility
)
```

**Additional Methods:**
- `get_arm_statistics() -> dict`: Get detailed statistics
  - Returns: `{'counts': [...], 'means': [...], 'variances': [...], 'std_devs': [...]}`

**Attributes:**
- `counts`: Selection count per arm
- `sums`: Sum of rewards per arm
- `random_state`: Random number generator

### EXP3Bandit

Exponential-weight algorithm for Exploration and Exploitation.

**Initialization:**
```python
EXP3Bandit(
    n_arms: int,              # Number of strategies
    gamma: float = 0.1        # Exploration parameter (0 < gamma < 1)
)
```

**Additional Methods:**
- `get_arm_statistics() -> dict`: Get detailed statistics
  - Returns: `{'counts': [...], 'weights': [...], 'probabilities': [...]}`

**Attributes:**
- `weights`: Exponential weights per arm
- `probabilities`: Selection probabilities per arm

### EpsilonGreedy

ε-Greedy algorithm with simple exploration/exploitation balance.

**Initialization:**
```python
EpsilonGreedy(
    n_arms: int,          # Number of strategies
    epsilon: float = 0.1  # Exploration probability (0 <= epsilon <= 1)
)
```

**Additional Methods:**
- `get_arm_statistics() -> dict`: Get detailed statistics
  - Returns: `{'counts': [...], 'means': [...], 'visits': [...], 'satisfaction': [...]}`

**Attributes:**
- `visits`: Selection count per arm
- `satisfaction`: Sum of rewards per arm

## Testing

### Run All Tests

```bash
# Run all bandit tests
python -m pytest tests/test_bandit_allocator.py tests/test_ucb_bandit.py tests/test_thompson_bandit.py tests/test_epsilon_greedy_bandit.py -v

# Run with coverage
python -m pytest tests/test_bandit_allocator.py tests/test_ucb_bandit.py tests/test_thompson_bandit.py tests/test_epsilon_greedy_bandit.py --cov=src/bandits --cov-report=term-missing
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

**Thompson Sampling Tests (28 tests):**
- Reproducibility with seed
- Stochastic behavior
- Posterior mean/variance updates
- Exploration of uncertain arms
- Exploitation of good arms
- Noisy reward handling
- Edge cases

**ε-Greedy Algorithm Tests (10 tests):**
- Pure exploration/exploitation modes
- Mixed strategy behavior
- Reward tracking accuracy
- Parameter validation
- Edge cases

All tests:
- ✅ Fast (<3 seconds total)
- ✅ Comprehensive (77 tests)
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

## Comparison: All Algorithms

| Feature | UCB | Thompson Sampling | EXP3 | ε-Greedy |
|---------|-----|------------------|------|-----------|
| **Exploration** | Confidence bounds | Posterior sampling | Probability weights | Random chance |
| **Deterministic** | Yes | No (requires seed) | No (stochastic) | No (stochastic) |
| **Convergence** | Moderate | Fast | Adaptive | Slow |
| **Noisy rewards** | Good | Excellent | Good | Fair |
| **Hyperparameters** | 1 (exploration_constant) | 3 (priors) | 1 (gamma) | 1 (epsilon) |
| **Interpretability** | High (UCB scores) | Moderate (posterior) | Low (weights) | High (simple) |
| **Best for** | Backtests, stability | Real-time, adaptation | Adversarial envs | Simple baseline |
| **Complexity** | Medium | High | Medium | Low |

Run `examples/mab_comparison_demo.py` to see all algorithms in action.

## Future Extensions

Potential algorithms to add:

1. **Sliding Window UCB**: Forget old observations for non-stationary environments
2. **Discounted Thompson Sampling**: Exponential decay for recent performance weighting
3. **Contextual Bandits**: Condition on market state features
4. **LinUCB**: Linear UCB for contextual bandits
5. **Softmax/Gibbs Sampling**: Alternative exploration strategies

All extensions should follow the same design principles:
- Implement `BanditAllocator` interface
- Add comprehensive unit tests
- Maintain zero external dependencies
- Reproducible behavior (deterministic or seeded)

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

**Version**: 1.1  
**Last Updated**: December 28, 2025  
**Status**: Production Ready
