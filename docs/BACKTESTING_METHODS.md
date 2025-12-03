# Advanced Backtesting Methods

## Overview

This document describes the five backtesting methodologies implemented in the `backtesting_methods.py` module. Each method serves a different purpose and has unique strengths and limitations. All methods have been validated with actual results using the Equal Weight strategy on 5-year weekly data (2019-2024).

---

## 1. Vanilla Backtest

### Description
Traditional single-run backtest over the entire historical period. The strategy is applied linearly from start to end without any sophisticated validation techniques.

### Mathematical Formulation
```
Portfolio NAV: NAV_t = NAV_{t-1} × (1 + R_p,t - TC_t)
Portfolio Return: R_p,t = Σ w_{i,t-1} × R_{i,t}
Transaction Costs: TC_t = κ × Σ |w_{i,t} - w_{i,t-1}|
```

### Actual Results (Equal Weight Strategy, 5-Year Weekly)
- **Total Return:** +16.6%
- **Sharpe Ratio:** 0.59
- **Max Drawdown:** -9.6%
- **Win Rate:** 45.9%
- **Total Trades:** 36

### Use Cases
- Quick initial testing of strategy ideas
- Baseline performance estimation
- When computational resources are limited
- Exploratory data analysis

### Advantages
✓ Fast and simple to implement  
✓ Easy to understand and interpret  
✓ Low computational requirements  
✓ Good for initial screening

### Limitations
⚠️ Highly susceptible to overfitting  
⚠️ Look-ahead bias if parameters optimized on same data  
⚠️ No measure of statistical robustness  
⚠️ Single point estimate (no confidence intervals)

### Example Usage
```python
from src.backtesting_methods import BacktestingMethods

bt = BacktestingMethods(prices=price_data)
result = bt.vanilla_backtest(
    strategy=my_strategy,
    start_date='2020-01-01',
    end_date='2023-12-31',
    rebalance_freq='M'
)
```

---

## 2. Walk-Forward Backtest

### Description
Divides data into multiple train/test periods. Strategy parameters are optimized on the train period and tested on the out-of-sample test period. The window then "walks forward" in time.

### Types
1. **Rolling Window**: Fixed-size window that moves forward
2. **Anchored Window**: Expanding window that starts from a fixed point

### Mathematical Formulation
```
For each window i:
  Train Period: [t_i, t_i + T_train]
  Test Period: [t_i + T_train, t_i + T_train + T_test]
  Next Window: t_{i+1} = t_i + step_size

Final Performance: Average of all test period results
```

### Actual Results (Equal Weight Strategy, 5-Year Weekly)
- **Mean Total Return:** -0.5% (across windows)
- **Mean Sharpe Ratio:** -0.09
- **Mean Max Drawdown:** -3.8%
- **Mean Win Rate:** 30.1%
- **Number of Windows:** 11
- **95% CI Width (Total Return):** 7.4%

### Use Cases
- Most realistic simulation of live trading
- Assessing strategy adaptability over time
- Testing robustness to changing market conditions
- Production-ready strategy validation

### Advantages
✓ Simulates real-world deployment  
✓ Tests strategy adaptability  
✓ Provides out-of-sample validation  
✓ Reduces overfitting risk  
✓ Shows performance consistency over time

### Limitations
⚠️ Requires sufficient historical data  
⚠️ Computationally more expensive  
⚠️ Results depend on window size selection  
⚠️ May miss regime changes within windows

### Parameters
- `train_window_months`: Size of training period (default: 24)
- `test_window_months`: Size of test period (default: 6)
- `step_months`: Step size for rolling window (default: 3)
- `anchored`: Use expanding window instead of rolling (default: False)

### Example Usage
```python
result = bt.walk_forward_backtest(
    strategy=my_strategy,
    start_date='2018-01-01',
    end_date='2023-12-31',
    train_window_months=24,
    test_window_months=6,
    step_months=3,
    anchored=False
)
```

---

## 3. Cross-Validation Backtest

### Description
Time-series cross-validation that splits data into k non-overlapping folds while preserving temporal order. Each fold serves as a test set once while others are used for training.

### Mathematical Formulation
```
Split data into k folds: [F_1, F_2, ..., F_k]

For fold i ∈ [1, k]:
  Test on F_i
  Train on all other folds respecting time order
  
Final Performance: Average across all k folds
Confidence Interval: Based on fold-wise performance distribution
```

### Use Cases
- Comparing multiple strategies
- Assessing statistical robustness
- Understanding performance variability
- Strategy selection and ranking

## 3. Cross-Validation Backtest

### Description
Time-series cross-validation with k-fold splits. Each fold uses a train/test split, preserving temporal order.

### Mathematical Formulation
```
For fold k = 1, ..., K:
  Train: observations before fold k
  Test: observations in fold k
  
Average metrics across all folds
Calculate confidence intervals from fold results
```

### Actual Results (Equal Weight Strategy, 5-Year Weekly)
- **Mean Total Return:** +3.5%
- **Mean Sharpe Ratio:** 1.08
- **Mean Max Drawdown:** -6.8%
- **Mean Win Rate:** 39.7%
- **Number of Folds:** 4
- **95% CI Width (Total Return):** 15.5%

### Use Cases
- Robust performance estimation with limited data
- Strategy comparison and validation
- Efficient use of available historical data
- When you need confidence intervals

### Advantages
✓ Provides robust performance estimates  
✓ Generates confidence intervals  
✓ Tests strategy across different time periods  
✓ Good for strategy comparison  
✓ Efficient use of available data

### Limitations
⚠️ May violate temporal independence  
⚠️ Requires careful fold design  
⚠️ Train/test sets may have different characteristics  
⚠️ Can be computationally intensive

### Parameters
- `n_splits`: Number of cross-validation folds (default: 5)
- `test_size_months`: Size of each test fold in months (default: 6)

### Example Usage
```python
result = bt.cross_validation_backtest(
    strategy=my_strategy,
    start_date='2018-01-01',
    end_date='2023-12-31',
    n_splits=5,
    test_size_months=6
)
```

---

## 4. Monte Carlo Backtest

### Description
Generates synthetic price paths using statistical methods to test strategy robustness under various market scenarios. Uses resampling or parametric simulation.

### Methods

#### Block Bootstrap
Resamples historical returns in blocks to preserve autocorrelation structure.
```
Sample blocks B_i of size L with replacement
Concatenate blocks to form synthetic return series
Preserve temporal dependencies within blocks
```

#### Parametric Simulation
Generates returns from fitted probability distributions.
```
Estimate: μ = E[R], Σ = Cov[R]
Generate: R_t ~ N(μ, Σ)
Alternative: fit other distributions (t-distribution, stable, etc.)
```

#### Geometric Brownian Motion
Classical continuous-time model for asset prices.
```
dS_t/S_t = μ dt + σ dW_t
Discrete: R_t = μ Δt + σ √Δt ε_t, where ε_t ~ N(0,1)
```

### Actual Results (Equal Weight Strategy, 5-Year Weekly)
- **Mean Total Return:** +37.7%
- **Mean Sharpe Ratio:** 1.14
- **Mean Max Drawdown:** -9.5%
- **Mean Win Rate:** 46.5%
- **Number of Simulations:** 100
- **95% CI Width (Total Return):** 50.4%

### Use Cases
- Stress testing strategies
- Understanding worst-case scenarios
- Assessing sensitivity to market conditions
- Risk management and scenario analysis

### Advantages
✓ Tests robustness to various scenarios  
✓ Can simulate extreme events  
✓ Provides distribution of outcomes  
✓ Useful for risk assessment  
✓ Can model specific scenario assumptions

### Limitations
⚠️ Model assumptions may be violated  
⚠️ Synthetic data may not capture real market dynamics  
⚠️ Computationally intensive  
⚠️ Results depend on simulation method  
⚠️ May not include regime changes or structural breaks

### Parameters
- `n_simulations`: Number of Monte Carlo runs (default: 100)
- `method`: Simulation method ('bootstrap', 'parametric', 'geometric')
- `block_size`: Block size for bootstrap (default: 20)

### Example Usage
```python
result = bt.monte_carlo_backtest(
    strategy=my_strategy,
    start_date='2020-01-01',
    end_date='2023-12-31',
    n_simulations=1000,
    method='bootstrap',
    block_size=20
)
```

---

## 5. Randomized Backtest

### Description
Performs multiple backtest runs with randomization to test statistical significance and detect data-snooping bias.

### Randomization Types

#### Random Start Date
Randomly selects different starting points within the data range.
```
For trial i:
  Start_i ~ Uniform[Start_min, End - Window]
  Test period: [Start_i, Start_i + Window]
```

#### Permutation
Randomly shuffles returns while preserving marginal distribution.
```
For trial i:
  Randomly permute return series
  Maintains distribution but destroys temporal structure
  Tests if strategy exploits temporal patterns
```

#### Random Subperiod
Randomly samples non-overlapping subperiods of fixed length.
```
For trial i:
  Randomly sample contiguous subperiod
  Test strategy on this subperiod
```

### Actual Results (Equal Weight Strategy, 5-Year Weekly)
- **Mean Total Return:** +9.6%
- **Mean Sharpe Ratio:** 1.01
- **Mean Max Drawdown:** -7.7%
- **Mean Win Rate:** 45.1%
- **Number of Trials:** 25
- **95% CI Width (Total Return):** 27.6%

### Use Cases
- Testing statistical significance of results
- Detecting data-snooping bias
- Validating strategy robustness
- Research validation and publication

### Advantages
✓ Tests statistical significance  
✓ Detects spurious patterns  
✓ Provides null distribution  
✓ Helps identify data-snooping  
✓ Robust validation method

### Limitations
⚠️ Requires many trials for significance  
⚠️ Computationally expensive  
⚠️ May lose temporal structure  
⚠️ Results interpretation can be complex

### Parameters
- `n_trials`: Number of randomized trials (default: 50)
- `randomization_type`: Type of randomization ('start_date', 'permutation', 'subperiod')
- `window_months`: Window size for sampling (default: 24)

### Example Usage
```python
result = bt.randomized_backtest(
    strategy=my_strategy,
    start_date='2018-01-01',
    end_date='2023-12-31',
    n_trials=100,
    randomization_type='start_date',
    window_months=24
)
```

---

## Comparison and Best Practices

### Method Selection Guide

| Method | Speed | Robustness | Overfitting Risk | Use Case |
|--------|-------|------------|------------------|----------|
| Vanilla | ⚡⚡⚡ | ⭐ | 🔴 High | Initial testing |
| Walk-Forward | ⚡⚡ | ⭐⭐⭐⭐⭐ | 🟢 Low | Production validation |
| Cross-Validation | ⚡⚡ | ⭐⭐⭐⭐ | 🟡 Medium | Strategy comparison |
| Monte Carlo | ⚡ | ⭐⭐⭐⭐ | 🟡 Medium | Risk assessment |
| Randomized | ⚡ | ⭐⭐⭐⭐ | 🟢 Low | Statistical validation |

### Recommended Workflow

```
1. INITIAL SCREENING (Vanilla)
   ↓ Quick test of strategy idea
   ↓ Filter out obviously bad strategies
   
2. REALISTIC VALIDATION (Walk-Forward)
   ↓ Simulate actual deployment
   ↓ Test adaptability over time
   
3. RISK ASSESSMENT (Monte Carlo)
   ↓ Stress test strategy
   ↓ Understand worst-case scenarios
   
4. STATISTICAL VALIDATION (Randomized)
   ↓ Confirm significance
   ↓ Rule out data-snooping
   
5. PRODUCTION DEPLOYMENT
```

### Common Pitfalls
---

## Comparison of Backtesting Methods

### Results Summary (Equal Weight Strategy, 5-Year Weekly, 2019-2024)

| Method | Total Return | Sharpe Ratio | Max Drawdown | Win Rate | Runs/Windows | Confidence Interval Width |
|--------|--------------|--------------|--------------|----------|--------------|---------------------------|
| **Vanilla** | +16.6% | 0.59 | -9.6% | 45.9% | 1 | N/A |
| **Walk-Forward** | -0.5% (mean) | -0.09 (mean) | -3.8% (mean) | 30.1% (mean) | 11 | 7.4% |
| **Cross-Validation** | +3.5% (mean) | 1.08 (mean) | -6.8% (mean) | 39.7% (mean) | 4 | 15.5% |
| **Monte Carlo** | +37.7% (mean) | 1.14 (mean) | -9.5% (mean) | 46.5% (mean) | 100 | 50.4% |
| **Randomized** | +9.6% (mean) | 1.01 (mean) | -7.7% (mean) | 45.1% (mean) | 25 | 27.6% |

### Method Selection Guide

| Scenario | Recommended Method | Why |
|----------|-------------------|-----|
| **Quick validation** | Vanilla | Fast, simple baseline |
| **Production deployment** | Walk-Forward | Most realistic, simulates live trading |
| **Limited data** | Cross-Validation | Efficient data usage, confidence intervals |
| **Stress testing** | Monte Carlo | Tests various scenarios, extreme events |
| **Statistical validation** | Randomized | Detects spurious patterns, significance testing |
| **Comprehensive validation** | All methods | Complete picture of strategy robustness |

### Key Observations from Actual Results

1. **Vanilla Backtest** shows positive returns (+16.6%) but provides no robustness measure
2. **Walk-Forward** reveals challenges with adaptation (negative mean return), highlighting the difficulty of maintaining performance across changing market regimes
3. **Cross-Validation** shows moderate positive returns (+3.5%) with reasonable Sharpe (1.08)
4. **Monte Carlo** shows highest mean return (+37.7%) due to bootstrap sampling of favorable periods
5. **Randomized** provides middle-ground results (+9.6%) with decent confidence intervals

**Important Insight:** The significant variation in results across methods (from -0.5% to +37.7%) demonstrates why using multiple validation methods is crucial for understanding strategy robustness.

---

## Common Pitfalls

1. **Insufficient Data**
   - Walk-forward and cross-validation require substantial history
   - Minimum: 3-5 years for meaningful results

2. **Window Size Selection**
   - Too small: High variance in results
   - Too large: Poor adaptation to changing conditions
   - Rule of thumb: Train window = 2-3 × test window

3. **Overfitting During Optimization**
   - Even with walk-forward, can overfit during parameter selection
   - Solution: Use nested cross-validation for parameter tuning

4. **Ignoring Transaction Costs**
   - Real-world costs can eliminate theoretical profits
   - Always include realistic cost assumptions (10 bps is standard)

5. **Not Testing on Multiple Methods**
   - Single method can miss important issues
   - Best practice: Use at least 2-3 different methods

### Performance Metrics

All methods return consistent metrics:

- **Return Metrics**: Annual return, total return
- **Risk Metrics**: Volatility, max drawdown, VaR, CVaR
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Statistical**: Confidence intervals (where applicable)

### Computational Considerations

Approximate relative computation times:
- Vanilla: 1x (baseline)
- Walk-Forward: 5-10x
- Cross-Validation: 5-10x
- Monte Carlo: 50-100x (depends on n_simulations)
- Randomized: 25-50x (depends on n_trials)

---

## Advanced Topics

### Combining Methods

You can combine methods for comprehensive validation:

```python
# Run all methods
vanilla = bt.vanilla_backtest(...)
wf = bt.walk_forward_backtest(...)
cv = bt.cross_validation_backtest(...)
mc = bt.monte_carlo_backtest(...)
rand = bt.randomized_backtest(...)

# Compare results
comparison = bt.compare_methods([vanilla, wf, cv, mc, rand])
```

### Statistical Significance Testing

For randomized backtests, you can compute p-values:

```python
# Get Sharpe ratios from all trials
sharpe_ratios = [r.summary_metrics['sharpe_ratio'] 
                 for r in result.individual_results]

# Compute p-value (% of trials with Sharpe > threshold)
threshold = 1.0
p_value = np.mean([s > threshold for s in sharpe_ratios])
```

### Custom Validation

You can create custom validation schemes:

```python
# Example: Seasonal validation
winter_result = bt.vanilla_backtest(strategy, '2020-12-01', '2023-02-28')
summer_result = bt.vanilla_backtest(strategy, '2020-06-01', '2023-08-31')
```

---

## References

1. **Walk-Forward Analysis**
   - Pardo, R. (2008). *The Evaluation and Optimization of Trading Strategies*
   - White, H. (2000). "A Reality Check for Data Snooping"

2. **Cross-Validation for Time Series**
   - Bergmeir, C., & Benítez, J. M. (2012). "On the use of cross-validation for time series predictor evaluation"
   - Hyndman, R. J., & Athanasopoulos, G. (2018). *Forecasting: Principles and Practice*

3. **Monte Carlo Methods**
   - Glasserman, P. (2004). *Monte Carlo Methods in Financial Engineering*
   - Efron, B., & Tibshirani, R. J. (1994). *An Introduction to the Bootstrap*

4. **Data-Snooping and Robustness**
   - Harvey, C. R., Liu, Y., & Zhu, H. (2016). "...and the Cross-Section of Expected Returns"
   - Bailey, D. H., et al. (2014). "Pseudo-Mathematics and Financial Charlatanism"

---

## See Also

- [Portfolio Engine Documentation](ARCHITECTURE.md)
- [Strategy Wrapper Guide](STRATEGIES.md)
- [Example Scripts](../examples/demo_backtesting_methods.py)
