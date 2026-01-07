# Benchmark Portfolio Strategies

## Overview

This module provides mathematically correct implementations of standard portfolio benchmark strategies using **only numpy and numpy.linalg**. All strategies are:

- ✅ **Long-only**: All weights `w_i >= 0`
- ✅ **Fully invested**: Weights sum to exactly 1.0
- ✅ **Numerically stable**: Proper regularization and safe linear algebra
- ✅ **Deterministic**: No randomness, reproducible results
- ✅ **Backtest-safe**: No look-ahead bias
- ✅ **Compatible**: Fully compatible with `BaseStrategyWrapper`

**No external optimization libraries** (cvxpy, scipy, sklearn, torch, etc.) are used.

---

## Strategy Categories

### 1. Heuristic Benchmarks

Simple, parameter-free or minimal-parameter strategies that serve as naive baselines.

#### Equal Weight (`EqualWeightBenchmark`)
```python
w_i = 1/N
```

**Properties:**
- Simplest possible strategy
- No parameter estimation
- Optimal under equal Sharpe ratio assumptions
- Surprisingly hard to beat in practice

**Reference:** DeMiguel et al. (2009), *Review of Financial Studies*

---

#### Top-K Equal Weight by Return (`TopKReturnBenchmark`)
```python
1. Rank assets by μ_i
2. Select top K assets
3. w_i = 1/K if i in top K, else 0
```

**Parameters:**
- `top_k`: Number of assets to select (default: 10)

**Properties:**
- Simple momentum/return-following strategy
- Ignores risk entirely
- Can be highly concentrated

---

#### Top-K Equal Weight by Sharpe Proxy (`TopKSharpeBenchmark`)
```python
1. Compute Sharpe proxy: S_i = μ_i / sqrt(Σ_ii)
2. Select top K by S_i
3. w_i = 1/K if i in top K, else 0
```

**Parameters:**
- `top_k`: Number of assets to select (default: 10)

**Properties:**
- Risk-adjusted selection
- Better than return-only
- Still ignores correlations

---

### 2. Risk-Based Benchmarks

Strategies that use covariance information but ignore expected returns.

#### Inverse Volatility (`InverseVolatilityBenchmark`)
```python
σ_i = sqrt(Σ_ii)
w_i ∝ 1/σ_i
```

**Properties:**
- Simple risk-based allocation
- Reduces exposure to volatile assets
- Ignores correlations
- More stable than inverse variance

**Reference:** Leote de Carvalho et al. (2012), *Journal of Portfolio Management*

---

#### Inverse Variance (`InverseVarianceBenchmark`)
```python
w_i ∝ 1/Σ_ii
```

**Properties:**
- Stronger penalty for volatility
- Can be concentrated in low-vol assets
- Still ignores correlations

**Reference:** Clarke et al. (2011), *Journal of Portfolio Management*

---

#### Global Minimum Variance Portfolio (`GlobalMinVarianceBenchmark`)
```python
minimize: w^T Σ w
subject to: w^T 1 = 1

Closed-form solution:
w* = Σ^(-1) 1 / (1^T Σ^(-1) 1)
```

**Implementation:**
- Uses `np.linalg.solve(Σ, 1)` instead of matrix inverse
- Adds ridge regularization for numerical stability
- Ensures Σ is positive semi-definite

**Properties:**
- Leftmost point on efficient frontier
- No return estimation required
- Immune to μ estimation error
- Uses correlation structure

**Reference:** Markowitz (1952), Clarke et al. (2006)

---

#### Maximum Decorrelation Portfolio (`MaxDecorrelationBenchmark`)
```python
1. Compute correlation matrix: C = D^(-1) Σ D^(-1)
   where D = diag(sqrt(diag(Σ)))
2. Apply GMVP to C:
   w* = C^(-1) 1 / (1^T C^(-1) 1)
```

**Properties:**
- Minimizes correlation-weighted variance
- Treats all volatilities equally
- Useful when correlations more stable than volatilities
- Related to "most uncorrelated" portfolio

**Reference:** Christoffersen et al. (2012), *Review of Financial Studies*

---

### 3. Iterative Benchmarks

Strategies requiring iterative algorithms (no closed-form solution).

#### Risk Parity (`RiskParityBenchmark`)
```python
Goal: RC_i = RC_j for all i, j
where RC_i = w_i * (Σw)_i

Equivalently: Each asset contributes 1/N to total risk
```

**Algorithm:**
- Multiplicative updates: `w_i <- w_i * (target_RC / RC_i)^η`
- Project onto simplex each iteration
- Fixed iteration count (no tolerance-based early stopping)

**Parameters:**
- `max_iter`: Maximum iterations (default: 1000)
- `learning_rate`: Step size η (default: 0.05)

**Properties:**
- Equalizes risk contribution
- More diversified than market-cap or equal weight
- Popular in institutional investing
- Requires iterative solution

**Reference:** Maillard et al. (2010), *Journal of Portfolio Management*

---

#### Most Diversified Portfolio (`MostDiversifiedBenchmark`)
```python
maximize: DR(w) = (w^T σ) / sqrt(w^T Σ w)
subject to: w >= 0, w^T 1 = 1

where σ = [sqrt(Σ_11), ..., sqrt(Σ_NN)]
```

**Algorithm:**
- Projected gradient ascent on diversification ratio
- Long-only simplex projection
- Normalized gradient for stability

**Parameters:**
- `max_iter`: Maximum iterations (default: 1000)
- `learning_rate`: Step size (default: 0.01)

**Properties:**
- Maximizes weighted avg volatility / portfolio volatility
- Exploits low correlation benefits
- No return forecasts needed
- Popular risk-based strategy

**Reference:** Choueifaty & Coignard (2008), *Journal of Portfolio Management*

---

## Usage Examples

### Basic Usage
```python
from src.strategies.benchmarks import EqualWeightBenchmark, GlobalMinVarianceBenchmark

# Equal weight
ew = EqualWeightBenchmark(strategy)
weights = ew.get_weights(date, portfolio_state)

# Global minimum variance
gmvp = GlobalMinVarianceBenchmark(strategy, ridge=1e-5)
weights = gmvp.get_weights(date, portfolio_state)
```

### Direct Weight Computation
```python
import numpy as np
from src.strategies.benchmarks import RiskParityBenchmark

# Assuming you have mu and Sigma
mu = np.array([0.08, 0.10, 0.12])
Sigma = np.array([
    [0.04, 0.01, 0.02],
    [0.01, 0.09, 0.03],
    [0.02, 0.03, 0.16]
])

rp = RiskParityBenchmark(strategy, max_iter=500)
weights = rp.compute_weights(mu, Sigma)

print(f"Weights: {weights}")
print(f"Sum: {weights.sum():.6f}")
print(f"All positive: {np.all(weights >= 0)}")
```

### List All Available Benchmarks
```python
from src.strategies.benchmarks import list_benchmarks

benchmarks = list_benchmarks()
for name, cls in benchmarks.items():
    print(f"{name}: {cls.__name__}")
```

---

## Implementation Details

### Numerical Stability

All strategies use:

1. **Safe linear solve** (`_safe_solve`):
   - Uses `np.linalg.solve(A, b)` instead of `np.linalg.inv(A) @ b`
   - Adds ridge regularization: `A + ridge * I`
   - Handles singular/near-singular matrices

2. **Covariance regularization** (`_safe_cov`):
   - Ensures positive semi-definite: `Σ + ε I` if needed
   - Checks minimum eigenvalue

3. **Simplex projection** (`_project_simplex`):
   - Projects weights onto `{w: w >= 0, sum(w) = 1}`
   - Efficient sorting-based algorithm
   - Used in iterative methods

4. **Weight normalization** (`_normalize`):
   - Ensures non-negative: `w = max(w, 0)`
   - Normalizes to sum to 1.0
   - Handles degenerate cases (all zeros)

### Validation

All strategies validate output:
- ✅ `np.all(weights >= 0)` (long-only)
- ✅ `np.isclose(weights.sum(), 1.0)` (fully invested)
- ✅ No NaN or Inf values
- ✅ Deterministic (same input → same output)

---

## Mathematical Correctness

### Global Minimum Variance Portfolio

**Derivation:**
```
minimize    (1/2) w^T Σ w
subject to  w^T 1 = 1

Lagrangian: L = (1/2) w^T Σ w - λ(w^T 1 - 1)

FOC: Σ w = λ 1
     w^T 1 = 1

Solution: w = λ Σ^(-1) 1
          1^T w = λ (1^T Σ^(-1) 1) = 1
          => λ = 1 / (1^T Σ^(-1) 1)
          => w* = Σ^(-1) 1 / (1^T Σ^(-1) 1)
```

**Implementation:**
```python
# Solve Σ w = 1 instead of w = Σ^(-1) 1
w_unnorm = np.linalg.solve(Sigma, ones)
w = w_unnorm / w_unnorm.sum()
```

### Risk Parity Portfolio

**Risk Contribution:**
```
RC_i = ∂/∂w_i (w^T Σ w) * w_i
     = w_i * (Σ w)_i

Percentage Risk Contribution:
PRC_i = RC_i / sqrt(w^T Σ w)
```

**Equal Risk Contribution:**
```
RC_i = c for all i
=> w_i * (Σ w)_i = c
=> PRC_i = 1/N
```

### Most Diversified Portfolio

**Diversification Ratio:**
```
DR(w) = (Σ w_i σ_i) / sqrt(w^T Σ w)
```

**Gradient:**
```
∂DR/∂w = σ / sqrt(w^T Σ w) - DR(w) * Σ w / sqrt(w^T Σ w)
```

---

## Why These Benchmarks?

These strategies serve as:

1. **Baselines**: Compare sophisticated strategies against simple alternatives
2. **Robustness checks**: Strategies robust to estimation error
3. **Building blocks**: Components for more complex strategies
4. **Academic standards**: Well-studied and documented in literature

### Common Findings in Literature

- Equal weight often beats mean-variance optimization (estimation error)
- Risk-based strategies (GMVP, RP, MDP) competitive with return-based
- Simple strategies provide good risk-adjusted returns
- Diversification more important than return forecasting

---

## Input Assumptions

All strategies assume:

- `mu`: Vector of expected returns (N,)
- `Sigma`: Covariance matrix (N, N)
  - Symmetric
  - Positive semi-definite (enforced by `_safe_cov`)
  - Returns are in same frequency (e.g., daily)

**Note:** Most risk-based strategies **ignore μ** entirely (GMVP, IV, IVar, MaxDecorr, RP, MDP).

---

## Constraints

All strategies enforce:

1. **Long-only**: `w_i >= 0` for all i
2. **Fully invested**: `Σ w_i = 1`

No short-selling or leverage is allowed. Cash allocation (if needed) is handled by the portfolio engine.

---

## References

1. **DeMiguel, V., Garlappi, L., & Uppal, R. (2009).** "Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy?" *Review of Financial Studies*, 22(5), 1915-1953.

2. **Markowitz, H. (1952).** "Portfolio Selection." *Journal of Finance*, 7(1), 77-91.

3. **Clarke, R., De Silva, H., & Thorley, S. (2006).** "Minimum-Variance Portfolios in the U.S. Equity Market." *Journal of Portfolio Management*, 33(1), 10-24.

4. **Maillard, S., Roncalli, T., & Teiletche, J. (2010).** "The Properties of Equally Weighted Risk Contribution Portfolios." *Journal of Portfolio Management*, 36(4), 60-70.

5. **Choueifaty, Y., & Coignard, Y. (2008).** "Toward Maximum Diversification." *Journal of Portfolio Management*, 35(1), 40-51.

6. **Leote de Carvalho, R., Lu, X., & Moulin, P. (2012).** "Demystifying Equity Risk-Based Strategies: A Simple Alpha Plus Beta Description." *Journal of Portfolio Management*, 38(3), 56-70.

7. **Christoffersen, P., Errunza, V., Jacobs, K., & Langlois, H. (2012).** "Is the Potential for International Diversification Disappearing?" *Review of Financial Studies*, 25(12), 3711-3751.

---

## Author

Algo Trading Team  
January 2026

---

## License

Part of the algo-trading-modeling project.
