# Benchmark Strategies Quick Reference

## Import

```python
from src.strategies.benchmarks import (
    EqualWeightBenchmark,
    InverseVolatilityBenchmark,
    InverseVarianceBenchmark,
    GlobalMinVarianceBenchmark,
    MaxDecorrelationBenchmark,
    TopKReturnBenchmark,
    TopKSharpeBenchmark,
    RiskParityBenchmark,
    MostDiversifiedBenchmark,
    list_benchmarks
)
```

## Quick Strategy Reference

| Strategy | Formula | Uses μ | Uses Σ | Iterative | Complexity |
|----------|---------|--------|--------|-----------|------------|
| Equal Weight | w = 1/N | ❌ | ❌ | ❌ | O(1) |
| Inverse Volatility | w ∝ 1/σ | ❌ | ✅ | ❌ | O(N) |
| Inverse Variance | w ∝ 1/σ² | ❌ | ✅ | ❌ | O(N) |
| Global Min Variance | w = Σ⁻¹1 / 1ᵀΣ⁻¹1 | ❌ | ✅ | ❌ | O(N³) |
| Max Decorrelation | GMVP on corr matrix | ❌ | ✅ | ❌ | O(N³) |
| Top-K Return | Top K by μ, equal wt | ✅ | ❌ | ❌ | O(N log N) |
| Top-K Sharpe | Top K by μ/σ, equal wt | ✅ | ✅ | ❌ | O(N log N) |
| Risk Parity | Equal risk contrib | ❌ | ✅ | ✅ | O(N² × iter) |
| Most Diversified | Max DR(w) | ❌ | ✅ | ✅ | O(N² × iter) |

## Usage Patterns

### Pattern 1: Simple Usage
```python
strategy = EqualWeightBenchmark(signal_generator)
weights = strategy.get_weights(date, portfolio_state)
```

### Pattern 2: With Parameters
```python
strategy = TopKReturnBenchmark(signal_generator, top_k=5)
strategy = RiskParityBenchmark(signal_generator, max_iter=500, learning_rate=0.05)
```

### Pattern 3: Direct Weight Computation
```python
import numpy as np
strategy = GlobalMinVarianceBenchmark(signal_generator)
weights = strategy.compute_weights(mu, Sigma)  # numpy arrays
```

## Parameter Guide

### EqualWeightBenchmark
```python
EqualWeightBenchmark(strategy)
# No parameters
```

### InverseVolatilityBenchmark / InverseVarianceBenchmark
```python
InverseVolatilityBenchmark(strategy, epsilon=1e-8, ridge=1e-5)
# epsilon: minimum variance threshold
# ridge: regularization parameter
```

### GlobalMinVarianceBenchmark / MaxDecorrelationBenchmark
```python
GlobalMinVarianceBenchmark(strategy, ridge=1e-5)
# ridge: regularization for matrix solve
```

### TopKReturnBenchmark / TopKSharpeBenchmark
```python
TopKReturnBenchmark(strategy, top_k=10)
# top_k: number of assets to select
```

### RiskParityBenchmark
```python
RiskParityBenchmark(strategy, max_iter=1000, learning_rate=0.05)
# max_iter: maximum iterations
# learning_rate: step size for updates
```

### MostDiversifiedBenchmark
```python
MostDiversifiedBenchmark(strategy, max_iter=1000, learning_rate=0.01)
# max_iter: maximum iterations
# learning_rate: gradient step size
```

## Common Use Cases

### 1. Naive Baseline
```python
# Simplest possible strategy
ew = EqualWeightBenchmark(strategy)
```

### 2. Risk-Based Allocation
```python
# Minimize risk without return forecasts
gmvp = GlobalMinVarianceBenchmark(strategy)
```

### 3. Risk Budgeting
```python
# Equal risk contribution
rp = RiskParityBenchmark(strategy, max_iter=500)
```

### 4. Momentum Selection
```python
# Select top performers
topk = TopKReturnBenchmark(strategy, top_k=10)
```

### 5. Diversification Focus
```python
# Maximize diversification benefits
mdp = MostDiversifiedBenchmark(strategy, max_iter=500)
```

## Validation Checklist

All strategies guarantee:
- ✅ w ≥ 0 (long-only)
- ✅ Σw = 1 (fully invested)
- ✅ No NaN/Inf
- ✅ Deterministic
- ✅ Numpy-only

## Mathematical Formulas

### Global Minimum Variance
```
minimize    w^T Σ w
subject to  w^T 1 = 1

Solution: w* = Σ^(-1) 1 / (1^T Σ^(-1) 1)
```

### Risk Parity
```
Goal: RC_i = RC_j for all i, j
where RC_i = w_i * (Σw)_i

Algorithm: Multiplicative updates
```

### Most Diversified
```
maximize    DR(w) = (w^T σ) / sqrt(w^T Σ w)
subject to  w ≥ 0, w^T 1 = 1

Algorithm: Projected gradient ascent
```

## Helper Functions

```python
# List all available benchmarks
benchmarks = list_benchmarks()

# Iterate through all
for name, cls in benchmarks.items():
    strategy = cls(signal_generator)
    weights = strategy.compute_weights(mu, Sigma)
```

## Files

- `base_benchmark.py` - Base class with utilities
- `equal_weight.py` - Equal Weight (1/N)
- `inverse_volatility.py` - Inverse Volatility
- `inverse_variance.py` - Inverse Variance
- `global_min_variance.py` - GMVP
- `max_decorrelation.py` - Max Decorrelation
- `top_k_return.py` - Top-K by Return
- `top_k_sharpe.py` - Top-K by Sharpe
- `risk_parity.py` - Risk Parity
- `most_diversified.py` - Most Diversified
- `README.md` - Full documentation

## Testing

```bash
# Run validation tests
python tests/test_benchmark_strategies.py

# Run examples
python examples/benchmark_strategies_demo.py
```

## Dependencies

**Only:** `numpy`, `numpy.linalg`

**Not used:** pandas, cvxpy, scipy, sklearn, torch
