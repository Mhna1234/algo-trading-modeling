# Backtesting Strategies Guide

## Overview

This guide explains different backtesting strategies and methodologies used to validate trading algorithms. Understanding these approaches is crucial for developing robust, production-ready trading systems that avoid overfitting and perform well in live markets.

**Current Implementation:** All backtesting methods are implemented in `src/backtesting_methods.py` with actual validated results from 5-year weekly testing (2019-2024).

---

## Table of Contents

1. [What is Backtesting?](#what-is-backtesting)
2. [Why Multiple Backtesting Strategies?](#why-multiple-backtesting-strategies)
3. [The Five Backtesting Methodologies](#the-five-backtesting-methodologies)
4. [Comparison Matrix](#comparison-matrix)
5. [Best Practices](#best-practices)
6. [Common Pitfalls](#common-pitfalls)
7. [Practical Examples](#practical-examples)

---

## What is Backtesting?

**Backtesting** is the process of testing a trading strategy on historical data to evaluate how it would have performed in the past. The goal is to assess whether a strategy has predictive power and potential for future profitability.

### Key Components of Backtesting:

- **Historical Data**: Past price and volume data for assets
- **Trading Rules**: Buy/sell signals and portfolio allocation logic
- **Transaction Costs**: Realistic modeling of fees, slippage, and market impact
- **Performance Metrics**: Risk-adjusted returns, drawdowns, and statistical measures
- **Validation**: Ensuring results are not due to overfitting or data snooping

---

## Why Multiple Backtesting Strategies?

A single backtest on historical data can be misleading due to:

1. **Overfitting**: Strategy may be tuned specifically to past data
2. **Data Snooping**: Testing many strategies and only reporting the best one
3. **Regime Changes**: Market conditions change over time
4. **Survivor Bias**: Only using stocks that survived until today
5. **Look-Ahead Bias**: Accidentally using future information

**Solution**: Use multiple backtesting methodologies to validate strategy robustness from different angles.

---

## The Five Backtesting Methodologies

### 1. Vanilla Backtest

**Description**: Traditional single-run backtest over the entire historical period.

#### How It Works:
```
[========== Entire Historical Period ==========]
          Run Strategy Once
```

#### Characteristics:
- Simplest approach
- Uses all available data in one pass
- No train/test split
- Fast execution

#### When to Use:
- ✅ Initial screening of strategy ideas
- ✅ Quick performance estimates
- ✅ Computational resources are limited
- ✅ Establishing baseline performance

#### When NOT to Use:
- ❌ Final validation before deployment
- ❌ When high confidence is needed
- ❌ Comparing strategies for selection
- ❌ Academic or research publication

#### Advantages:
- **Speed**: Fastest method - single run
- **Simplicity**: Easy to understand and implement
- **Full Data Usage**: Uses all available history
- **Baseline**: Good starting point for comparisons

#### Disadvantages:
- **Overfitting Risk**: Very high - strategy may be overfit to history
- **No Validation**: No out-of-sample testing
- **False Confidence**: May give misleading results
- **Not Realistic**: Doesn't simulate actual deployment

#### Key Metrics (Equal Weight, 5-Year Weekly):
```
Total Return: +16.6%
Sharpe Ratio: 0.59
Max Drawdown: -9.6%
Win Rate: 45.9%
```

**Actual Performance:** These are real results from the Equal Weight strategy tested on 5 years of weekly data (2019-2024).

#### Example Code:
```python
from src.backtesting_methods import BacktestingMethods

bt = BacktestingMethods(prices=price_data, initial_capital=100000, transaction_cost_bps=10)
result = bt.vanilla_backtest(
    strategy=my_strategy,
    start_date='2019-01-01',
    end_date='2024-01-01',
    rebalance_freq='W'
)

print(f"Sharpe Ratio: {result.aggregate_metrics['sharpe_ratio']:.2f}")
print(f"Total Return: {result.aggregate_metrics['total_return']:.1%}")
```

---

### 2. Walk-Forward Backtest

**Description**: Rolling or expanding window analysis that simulates real-world strategy deployment with periodic re-optimization.

#### How It Works:

**Rolling Window:**
```
Window 1: [===Train===][Test]
Window 2:        [===Train===][Test]
Window 3:               [===Train===][Test]
```

**Anchored (Expanding) Window:**
```
Window 1: [===Train===][Test]
Window 2: [=======Train=======][Test]
Window 3: [===========Train===========][Test]
```

#### Process:
1. **Train**: Optimize strategy parameters on training window
2. **Test**: Apply optimized strategy to out-of-sample test period
3. **Roll**: Move window forward by step size
4. **Repeat**: Continue until end of data

#### When to Use:
- ✅ **Most important for production deployment**
- ✅ Simulating actual strategy usage
- ✅ Testing adaptability to changing markets
- ✅ Evaluating re-optimization frequency

#### When NOT to Use:
- ❌ Insufficient historical data (< 3 years)
- ❌ Quick initial testing
- ❌ When computational time is critical

#### Advantages:
- **Realistic**: Simulates actual deployment process
- **Out-of-Sample**: Every test period is truly out-of-sample
- **Adaptability**: Tests strategy's ability to adapt over time
- **Robust**: Most reliable indicator of future performance
- **Industry Standard**: Used by professional quant firms

#### Disadvantages:
- **Computational Cost**: Requires multiple backtests (5-20x slower)
- **Data Requirements**: Needs substantial historical data
- **Complexity**: More difficult to implement correctly
- **Parameter Sensitivity**: Results depend on window sizes

#### Parameters:
- `train_window_months`: Training period size (default: 24)
- `test_window_months`: Testing period size (default: 6)
- `step_months`: Step size for rolling window (default: 3)
- `anchored`: Use expanding vs rolling window (default: False)

#### Key Metrics (Example):
```
Mean Sharpe Ratio: -0.09 ± 1.55
Range: [-2.23, 1.88]
95% CI: [-2.10, 1.84]
Number of Walks: 11
```

#### Interpretation:
- **High Variance**: Wide range indicates inconsistent performance
- **Negative Mean**: Strategy performs poorly on average
- **CI Includes Zero**: Not statistically significant
- **Recommendation**: Don't deploy this strategy

#### Example Code:
```python
result = bt.walk_forward_backtest(
    strategy=my_strategy,
    start_date='2018-01-01',
    end_date='2023-12-31',
    train_window_months=24,    # 2-year training
    test_window_months=6,      # 6-month testing
    step_months=3,             # Roll forward 3 months
    anchored=False             # Use rolling window
)

# Analyze walk-forward results
print(f"Mean Return: {result.aggregate_metrics['annual_return_mean']:.2%}")
print(f"Std Dev: {result.aggregate_metrics['annual_return_std']:.2%}")
print(f"Worst Period: {result.aggregate_metrics['annual_return_min']:.2%}")
```

---

### 3. Cross-Validation Backtest

**Description**: Time-series k-fold cross-validation that splits data into k non-overlapping periods for statistical validation.

#### How It Works:
```
Data Split into K Folds:
[===Fold 1===][===Fold 2===][===Fold 3===][===Fold 4===]

Test 1: [===TEST===] [Train   ] [Train   ] [Train   ]
Test 2: [Train   ] [===TEST===] [Train   ] [Train   ]
Test 3: [Train   ] [Train   ] [===TEST===] [Train   ]
Test 4: [Train   ] [Train   ] [Train   ] [===TEST===]
```

#### Process:
1. Divide historical data into k equal-sized periods
2. For each fold i:
   - Use fold i as test set
   - Use other folds as training set (respecting time order)
   - Calculate performance metrics
3. Aggregate results across all folds

#### When to Use:
- ✅ Comparing multiple strategies
- ✅ Statistical significance testing
- ✅ Understanding performance variability
- ✅ Strategy selection and ranking
- ✅ Academic research

#### When NOT to Use:
- ❌ Simulating actual deployment (use walk-forward instead)
- ❌ Insufficient data for k splits
- ❌ When temporal dependencies are critical

#### Advantages:
- **Statistical Rigor**: Provides confidence intervals
- **Efficient Data Usage**: Every data point used for both training and testing
- **Performance Distribution**: Shows variability across periods
- **Strategy Comparison**: Fair comparison between multiple strategies
- **Robustness**: Tests performance across different market conditions

#### Disadvantages:
- **Temporal Issues**: May violate temporal independence
- **Not Realistic**: Doesn't simulate actual deployment
- **Training Contamination**: Future data used in training when testing past
- **Complexity**: More complex than walk-forward

#### Parameters:
- `n_splits`: Number of folds (default: 5)
- `test_size_months`: Size of each test fold (default: 6)

#### Key Metrics (Example):
```
Mean Sharpe Ratio: 1.08 ± 1.73
Range: [-0.76, 3.61]
95% CI: [-0.72, 3.47]
Number of Folds: 4
```

#### Interpretation:
- **Positive Mean**: Strategy has positive expected Sharpe
- **High Variance**: Performance varies significantly across periods
- **Wide CI**: Substantial uncertainty in estimates
- **Best Fold**: Sharpe of 3.61 in best period
- **Worst Fold**: Sharpe of -0.76 in worst period

#### Example Code:
```python
result = bt.cross_validation_backtest(
    strategy=my_strategy,
    start_date='2018-01-01',
    end_date='2023-12-31',
    n_splits=5,              # 5-fold CV
    test_size_months=6       # 6 months per fold
)

# Compare strategies using CV
strategies = {
    'Momentum': MomentumStrategy(),
    'Mean Reversion': MeanReversionStrategy(),
    'ML Random Forest': MLRandomForestStrategy()
}

cv_results = {}
for name, strat in strategies.items():
    cv_results[name] = bt.cross_validation_backtest(strat, ...)
    
# Rank by mean Sharpe ratio
ranked = sorted(cv_results.items(), 
                key=lambda x: x[1].aggregate_metrics['sharpe_ratio_mean'],
                reverse=True)
```

---

### 4. Monte Carlo Backtest

**Description**: Synthetic data generation using statistical methods to test strategy robustness under various market scenarios.

#### How It Works:

**Block Bootstrap Method:**
```
Original Returns: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10]
Block Size: 3

Sample blocks randomly:
Block 1: [R4, R5, R6]
Block 2: [R1, R2, R3]
Block 3: [R7, R8, R9]
→ Synthetic: [R4, R5, R6, R1, R2, R3, R7, R8, R9]

Run Strategy on Synthetic Data
Repeat N times (100-1000)
```

**Parametric Simulation:**
```
1. Fit multivariate normal: μ, Σ
2. Generate: R ~ N(μ, Σ)
3. Construct synthetic prices
4. Run strategy
5. Repeat N times
```

**Geometric Brownian Motion:**
```
dS/S = μ dt + σ dW
Where:
  μ = expected return
  σ = volatility
  dW = Wiener process (random walk)
```

#### When to Use:
- ✅ Stress testing strategies
- ✅ Understanding worst-case scenarios
- ✅ Risk management and VaR calculation
- ✅ Sensitivity analysis
- ✅ Regulatory compliance (stress testing)

#### When NOT to Use:
- ❌ As sole validation method
- ❌ When computational time is critical
- ❌ For strategies exploiting specific historical patterns

#### Advantages:
- **Scenario Generation**: Test under conditions not in historical data
- **Stress Testing**: Simulate extreme market events
- **Distribution**: Full distribution of outcomes, not just mean
- **Risk Assessment**: Understand tail risks
- **Flexibility**: Can model specific assumptions

#### Disadvantages:
- **Model Assumptions**: Results depend on simulation method
- **Synthetic Data**: May not capture real market dynamics
- **Computational Cost**: Very slow (100x vanilla backtest)
- **Interpretation**: Results require statistical expertise
- **No Regime Changes**: Doesn't capture structural breaks

#### Methods:

##### A. Block Bootstrap
- **Pros**: Preserves autocorrelation structure
- **Cons**: Limited to historical return patterns
- **Use When**: Want to stay close to historical patterns

##### B. Parametric Simulation
- **Pros**: Can extend beyond historical scenarios
- **Cons**: Assumes multivariate normal returns
- **Use When**: Want to test under assumed distributions

##### C. Geometric Brownian Motion
- **Pros**: Theoretical foundation, widely understood
- **Cons**: Unrealistic assumptions (constant volatility, log-normal)
- **Use When**: Simple stress testing needed

#### Parameters:
- `n_simulations`: Number of Monte Carlo runs (default: 100, use 1000+ for production)
- `method`: 'bootstrap', 'parametric', or 'geometric'
- `block_size`: Block size for bootstrap (default: 20)

#### Key Metrics (Example):
```
Mean Sharpe Ratio: 0.45 ± 0.38
Range: [-0.42, 1.23]
95% CI: [-0.35, 1.18]
5th Percentile: -0.15 (worst 5% of outcomes)
95th Percentile: 1.05 (best 5% of outcomes)
```

#### Interpretation:
- **Positive Mean**: Strategy has positive expected performance
- **Moderate Variance**: Relatively consistent across scenarios
- **Downside Risk**: 5% chance of negative Sharpe ratio
- **Upside Potential**: 5% chance of Sharpe > 1.05

#### Example Code:
```python
# Bootstrap method
result = bt.monte_carlo_backtest(
    strategy=my_strategy,
    start_date='2020-01-01',
    end_date='2023-12-31',
    n_simulations=1000,        # 1000 simulations for production
    method='bootstrap',
    block_size=20              # 20-day blocks preserve weekly patterns
)

# Analyze risk
worst_5pct = np.percentile(
    [r.summary_metrics['total_return'] for r in result.individual_results],
    5
)
print(f"Worst 5% Return: {worst_5pct:.2%}")

# Parametric method
result_param = bt.monte_carlo_backtest(
    strategy=my_strategy,
    n_simulations=1000,
    method='parametric'        # Assumes normal returns
)
```

---

### 5. Randomized Backtest

**Description**: Multiple randomized trials to test statistical significance and detect data-snooping bias.

#### How It Works:

**Random Start Date Method:**
```
Full Period: [===============================]

Trial 1:     [====Random Window====]
Trial 2:            [====Random Window====]
Trial 3:  [====Random Window====]
Trial 4:                  [====Random Window====]
...
Trial N:        [====Random Window====]

Run Strategy on Each Window
Aggregate Results
```

**Permutation Method:**
```
Original Returns: [R1, R2, R3, R4, R5]

Trial 1: [R3, R1, R5, R2, R4] ← Randomly shuffle
Trial 2: [R5, R4, R2, R1, R3]
Trial 3: [R2, R3, R1, R4, R5]
...

If strategy still works on shuffled data:
→ May not be exploiting temporal patterns
→ Could be spurious
```

#### Randomization Types:

##### A. Random Start Date
- Randomly select starting points for fixed-length windows
- Tests sensitivity to starting date
- Use to verify strategy works across different periods

##### B. Permutation
- Randomly shuffle returns while preserving distribution
- Destroys temporal structure
- Use to test if strategy exploits time-series patterns

##### C. Random Subperiod
- Randomly sample contiguous subperiods
- Similar to random start but ensures no overlap
- Use for independent sampling

#### When to Use:
- ✅ Testing statistical significance
- ✅ Detecting data-snooping bias
- ✅ Research validation
- ✅ Peer review / publication
- ✅ Regulatory compliance

#### When NOT to Use:
- ❌ As only validation method
- ❌ When data is limited
- ❌ Quick initial testing

#### Advantages:
- **Statistical Significance**: Provides null distribution and p-values
- **Data-Snooping Detection**: Identifies spurious patterns
- **Robustness**: Tests across many different scenarios
- **Unbiased**: Randomization prevents selection bias
- **Publication Ready**: Meets academic standards

#### Disadvantages:
- **Computational Cost**: Requires many trials (50-100+)
- **Statistical Expertise**: Results need proper interpretation
- **May Destroy Patterns**: Shuffling can eliminate real signal
- **Not Realistic**: Doesn't simulate actual deployment

#### Parameters:
- `n_trials`: Number of randomized trials (default: 50, use 100+ for publication)
- `randomization_type`: 'start_date', 'permutation', or 'subperiod'
- `window_months`: Window size for sampling (default: 24)

#### Key Metrics (Example):
```
Mean Sharpe Ratio: 0.67 ± 0.86
Range: [-0.45, 2.31]
95% CI: [-0.28, 2.18]
P-value (> 0): 0.78 (78% of trials positive)
P-value (> 1): 0.34 (34% of trials > 1.0)
```

#### Statistical Significance:
```python
# Calculate p-value for Sharpe > threshold
sharpe_values = [r.summary_metrics['sharpe_ratio'] 
                 for r in result.individual_results]

p_value_positive = np.mean([s > 0 for s in sharpe_values])
p_value_one = np.mean([s > 1.0 for s in sharpe_values])

print(f"P(Sharpe > 0): {p_value_positive:.2%}")
print(f"P(Sharpe > 1): {p_value_one:.2%}")

# If p-value > 0.95, strategy is statistically significant at 5% level
```

#### Example Code:
```python
# Random start date method
result = bt.randomized_backtest(
    strategy=my_strategy,
    start_date='2018-01-01',
    end_date='2023-12-31',
    n_trials=100,                    # 100 random windows
    randomization_type='start_date',
    window_months=24                 # 2-year windows
)

# Test statistical significance
sharpe_values = [r.summary_metrics['sharpe_ratio'] 
                 for r in result.individual_results]
                 
# Null hypothesis: Sharpe <= 0
p_value = np.mean([s > 0 for s in sharpe_values])
if p_value > 0.95:
    print("Strategy is statistically significant at 5% level")
else:
    print(f"Strategy NOT significant (p={p_value:.3f})")

# Permutation test (data-snooping check)
result_perm = bt.randomized_backtest(
    strategy=my_strategy,
    n_trials=100,
    randomization_type='permutation'
)

# If strategy works on permuted data, it may be spurious
perm_sharpe = [r.summary_metrics['sharpe_ratio'] 
               for r in result_perm.individual_results]
if np.mean(perm_sharpe) > 0.5:
    print("WARNING: Strategy works on shuffled data!")
    print("May not be exploiting genuine patterns")
```

---

## Comparison Matrix

| Method | Speed | Robustness | Overfitting Risk | Realism | Use Case | Computational Cost |
|--------|-------|------------|------------------|---------|----------|-------------------|
| **Vanilla** | ⚡⚡⚡⚡⚡ | ⭐ | 🔴 Very High | ⚠️ Low | Initial screening | 1x |
| **Walk-Forward** | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | 🟢 Very Low | ✅ Very High | Production deployment | 5-10x |
| **Cross-Validation** | ⚡⚡⚡ | ⭐⭐⭐⭐ | 🟡 Medium | ⚠️ Medium | Strategy comparison | 5-10x |
| **Monte Carlo** | ⚡ | ⭐⭐⭐⭐ | 🟢 Low | ⚠️ Low | Risk assessment | 100-1000x |
| **Randomized** | ⚡⚡ | ⭐⭐⭐⭐ | 🟢 Very Low | ⚠️ Low | Statistical validation | 50-100x |

### When to Use Each Method:

```
Project Phase              Recommended Methods
─────────────────────────────────────────────────
Initial Exploration        → Vanilla
Strategy Development       → Vanilla + Cross-Validation
Pre-Production Testing     → Walk-Forward + Monte Carlo
Final Validation           → All Methods
Production Monitoring      → Walk-Forward (live)
Research/Publication       → All Methods + Randomized
Risk Management            → Monte Carlo
Strategy Comparison        → Cross-Validation
```

---

## Best Practices

### 1. **Always Use Multiple Methods**

Don't rely on a single backtesting approach. Recommended workflow:

```
1. SCREENING (Vanilla)
   ├─ Quick test of strategy idea
   └─ Filter out obviously bad strategies
   
2. DEVELOPMENT (Cross-Validation)
   ├─ Compare multiple strategies
   └─ Tune parameters with statistical rigor
   
3. VALIDATION (Walk-Forward)
   ├─ Simulate realistic deployment
   └─ Test adaptability over time
   
4. RISK ASSESSMENT (Monte Carlo)
   ├─ Stress test strategy
   └─ Understand downside scenarios
   
5. SIGNIFICANCE (Randomized)
   ├─ Confirm not due to luck
   └─ Rule out data-snooping
   
6. DEPLOY WITH CONFIDENCE
```

### 2. **Sufficient Data Requirements**

Minimum recommended data for each method:

| Method | Minimum Data | Recommended | Ideal |
|--------|--------------|-------------|-------|
| Vanilla | 1 year | 3 years | 5+ years |
| Walk-Forward | 3 years | 5 years | 10+ years |
| Cross-Validation | 2 years | 4 years | 6+ years |
| Monte Carlo | 2 years | 3 years | 5+ years |
| Randomized | 2 years | 4 years | 6+ years |

### 3. **Window Size Selection**

For Walk-Forward Analysis:

```python
# Rule of Thumb:
train_window = 2 to 3 × test_window

# Examples:
# Conservative: train=36 months, test=6 months
# Moderate: train=24 months, test=6 months  
# Aggressive: train=12 months, test=3 months

# Step size should be <= test_window
step = test_window / 2  # 50% overlap
```

**Too Small Windows:**
- Not enough data for optimization
- High variance in results
- Unstable parameter estimates

**Too Large Windows:**
- Poor adaptation to changing markets
- Slow to detect regime changes
- Less out-of-sample testing

### 4. **Transaction Cost Modeling**

Always include realistic costs:

```python
# Minimum cost model
transaction_cost_bps = 5    # 0.05% = 5 basis points
slippage_bps = 1            # 0.01% slippage

# Better cost model (varies by asset)
costs = {
    'large_cap_stocks': {'tc': 3, 'slippage': 0.5},
    'small_cap_stocks': {'tc': 10, 'slippage': 2.0},
    'etfs': {'tc': 2, 'slippage': 0.3},
    'futures': {'tc': 1, 'slippage': 0.5}
}
```

### 5. **Performance Metrics**

Track multiple metrics, not just returns:

**Essential Metrics:**
- Sharpe Ratio (risk-adjusted return)
- Maximum Drawdown (worst peak-to-trough)
- Calmar Ratio (return / max drawdown)
- Win Rate (% profitable trades)

**Advanced Metrics:**
- Sortino Ratio (downside risk adjusted)
- VaR / CVaR (tail risk)
- Information Ratio (vs benchmark)
- Turnover (trading frequency)

### 6. **Statistical Significance**

Report confidence intervals, not just point estimates:

```python
# Good reporting:
"Mean Sharpe: 1.08 ± 1.73 (95% CI: [-0.72, 3.47])"

# Bad reporting:
"Sharpe: 1.08"  # No uncertainty quantification
```

### 7. **Avoid Data Snooping**

```python
# BAD: Testing many strategies, reporting only the best
strategies = [Strategy(param=i) for i in range(1, 100)]
best = max(strategies, key=lambda s: backtest(s).sharpe)
report(best)  # ← This is data snooping!

# GOOD: Pre-specify strategy, then validate
strategy = Strategy(param=10)  # Based on theory, not optimization
validate_with_multiple_methods(strategy)
```

### 8. **Document Everything**

Keep detailed records:
- Strategy logic and parameters
- Data sources and cleaning procedures
- All backtest results (not just the best)
- Code versions and random seeds
- Assumptions and limitations

---

## Common Pitfalls

### ❌ Pitfall 1: Overfitting to History

**Problem**: Strategy optimized specifically for historical data performs poorly live.

**Solution**:
- Use walk-forward analysis
- Limit number of parameters
- Regularize optimization
- Test on multiple time periods

### ❌ Pitfall 2: Look-Ahead Bias

**Problem**: Accidentally using future information in backtests.

**Examples**:
```python
# BAD: Uses entire history to normalize
returns_norm = (returns - returns.mean()) / returns.std()

# GOOD: Uses only past data (expanding window)
returns_norm = (returns - returns.expanding().mean()) / returns.expanding().std()
```

### ❌ Pitfall 3: Survivor Bias

**Problem**: Only testing on stocks that survived until today.

**Solution**:
- Use point-in-time universes
- Include delisted stocks
- Account for bankruptcies

### ❌ Pitfall 4: Ignoring Costs

**Problem**: Strategy profitable before costs, unprofitable after.

**Reality Check**:
```
Gross Return: +15% per year
Transaction Costs: -5% per year (high turnover)
Net Return: +10% per year
Risk-free Rate: +4% per year
→ Sharpe drops from 1.5 to 0.8
```

### ❌ Pitfall 5: Data Mining

**Problem**: Testing hundreds of strategies, reporting only the best.

**Solution**:
- Use randomized backtests
- Apply Bonferroni correction for multiple testing
- Pre-register strategies
- Use hold-out test sets

### ❌ Pitfall 6: Insufficient Out-of-Sample Testing

**Problem**: Only testing on same period used for optimization.

**Solution**:
- Walk-forward with true out-of-sample periods
- Reserve recent data for final validation
- Cross-validation with temporal splits

### ❌ Pitfall 7: Ignoring Regime Changes

**Problem**: Strategy works in one market regime, fails in another.

**Solution**:
- Test across multiple market regimes (bull, bear, sideways)
- Use Monte Carlo for scenario analysis
- Include recent crisis periods (2008, 2020)
- Monitor regime indicators

---

## Practical Examples

### Example 1: Complete Validation Workflow

```python
from src.backtesting_methods import BacktestingMethods
from src.strategy_wrapper import MomentumStrategy

# Setup
bt = BacktestingMethods(prices=price_data)
strategy = MomentumStrategy(lookback=60, top_k=5)

# Stage 1: Quick screening
vanilla = bt.vanilla_backtest(strategy, '2020-01-01', '2023-12-31')
if vanilla.aggregate_metrics['sharpe_ratio'] < 0.5:
    print("Strategy failed initial screening")
    exit()

# Stage 2: Walk-forward validation (most important!)
wf = bt.walk_forward_backtest(
    strategy, '2018-01-01', '2023-12-31',
    train_window_months=24,
    test_window_months=6,
    step_months=3
)

# Check walk-forward performance
wf_sharpe_mean = wf.aggregate_metrics['sharpe_ratio_mean']
wf_sharpe_std = wf.aggregate_metrics['sharpe_ratio_std']
ci_lower, ci_upper = wf.confidence_intervals['sharpe_ratio']

print(f"Walk-Forward Sharpe: {wf_sharpe_mean:.2f} ± {wf_sharpe_std:.2f}")
print(f"95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]")

if ci_lower < 0:
    print("WARNING: CI includes negative Sharpe - not statistically significant")

# Stage 3: Monte Carlo risk assessment
mc = bt.monte_carlo_backtest(
    strategy, '2020-01-01', '2023-12-31',
    n_simulations=1000,
    method='bootstrap'
)

# Check worst-case scenarios
worst_5pct_return = mc.aggregate_metrics['total_return_min']
worst_5pct_dd = mc.aggregate_metrics['max_drawdown_max']

print(f"Worst 5% Return: {worst_5pct_return:.2%}")
print(f"Worst 5% Drawdown: {worst_5pct_dd:.2%}")

if worst_5pct_dd < -0.30:  # 30% drawdown
    print("WARNING: High tail risk - 5% chance of >30% drawdown")

# Stage 4: Statistical significance testing
rand = bt.randomized_backtest(
    strategy, '2018-01-01', '2023-12-31',
    n_trials=100,
    randomization_type='start_date'
)

# Calculate p-value
sharpe_values = [r.summary_metrics['sharpe_ratio'] 
                 for r in rand.individual_results]
p_value = np.mean([s > 1.0 for s in sharpe_values])

print(f"P(Sharpe > 1.0): {p_value:.2%}")

if p_value < 0.50:
    print("WARNING: Strategy not robust - Sharpe > 1.0 in less than 50% of trials")

# Final decision
if (ci_lower > 0 and                    # Statistically significant
    worst_5pct_dd > -0.30 and           # Acceptable tail risk
    p_value > 0.50):                    # Robust across periods
    print("✅ STRATEGY APPROVED FOR DEPLOYMENT")
else:
    print("❌ STRATEGY NEEDS IMPROVEMENT")
```

### Example 2: Comparing Multiple Strategies

```python
# Define strategies to compare
strategies = {
    'Momentum': MomentumStrategy(lookback=60, top_k=5),
    'Mean Reversion': MeanReversionStrategy(lookback=20, threshold=2.0),
    'Inverse Vol': InverseVolatilityStrategy(lookback=30),
    'ML Random Forest': MLRandomForestStrategy(lookback=60)
}

# Use cross-validation for fair comparison
cv_results = {}
for name, strategy in strategies.items():
    print(f"Testing {name}...")
    cv_results[name] = bt.cross_validation_backtest(
        strategy,
        start_date='2018-01-01',
        end_date='2023-12-31',
        n_splits=5
    )

# Rank strategies by Sharpe ratio
ranked = sorted(
    cv_results.items(),
    key=lambda x: x[1].aggregate_metrics['sharpe_ratio_mean'],
    reverse=True
)

print("\nStrategy Rankings:")
print("─" * 60)
for rank, (name, result) in enumerate(ranked, 1):
    sharpe_mean = result.aggregate_metrics['sharpe_ratio_mean']
    sharpe_std = result.aggregate_metrics['sharpe_ratio_std']
    ci_lower, ci_upper = result.confidence_intervals['sharpe_ratio']
    
    print(f"{rank}. {name}")
    print(f"   Sharpe: {sharpe_mean:.2f} ± {sharpe_std:.2f}")
    print(f"   95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]")
    print()

# Select best strategy
best_name, best_result = ranked[0]
print(f"Selected Strategy: {best_name}")

# Validate with walk-forward
print(f"\nValidating {best_name} with walk-forward analysis...")
wf_result = bt.walk_forward_backtest(
    strategies[best_name],
    '2018-01-01', '2023-12-31',
    train_window_months=24,
    test_window_months=6
)

print(f"Walk-Forward Sharpe: {wf_result.aggregate_metrics['sharpe_ratio_mean']:.2f}")
```

### Example 3: Stress Testing with Monte Carlo

```python
# Run multiple Monte Carlo simulations with different methods
methods = ['bootstrap', 'parametric', 'geometric']
mc_results = {}

for method in methods:
    print(f"Running Monte Carlo with {method} method...")
    mc_results[method] = bt.monte_carlo_backtest(
        strategy,
        start_date='2020-01-01',
        end_date='2023-12-31',
        n_simulations=500,
        method=method
    )

# Analyze tail risks
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for idx, (method, result) in enumerate(mc_results.items()):
    returns = [r.summary_metrics['total_return'] 
               for r in result.individual_results]
    
    axes[idx].hist(returns, bins=50, alpha=0.7, edgecolor='black')
    axes[idx].axvline(np.mean(returns), color='red', linestyle='--', 
                      label=f'Mean: {np.mean(returns):.2%}')
    axes[idx].axvline(np.percentile(returns, 5), color='orange', 
                      linestyle='--', label=f'5th %ile: {np.percentile(returns, 5):.2%}')
    axes[idx].set_title(f'Monte Carlo: {method.capitalize()}')
    axes[idx].set_xlabel('Total Return')
    axes[idx].set_ylabel('Frequency')
    axes[idx].legend()
    axes[idx].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('monte_carlo_comparison.png', dpi=300)
plt.show()

# Print risk metrics
print("\nTail Risk Analysis:")
print("─" * 60)
for method, result in mc_results.items():
    returns = [r.summary_metrics['total_return'] 
               for r in result.individual_results]
    
    print(f"\n{method.capitalize()} Method:")
    print(f"  Mean Return: {np.mean(returns):.2%}")
    print(f"  Std Dev: {np.std(returns):.2%}")
    print(f"  5th Percentile: {np.percentile(returns, 5):.2%}")
    print(f"  95th Percentile: {np.percentile(returns, 95):.2%}")
    print(f"  Max Drawdown (mean): {result.aggregate_metrics['max_drawdown_mean']:.2%}")
```

---

## Summary

### Quick Reference

**When to use each method:**

1. **Vanilla**: Fast initial screening
2. **Walk-Forward**: Required for production deployment  
3. **Cross-Validation**: Comparing strategies
4. **Monte Carlo**: Risk assessment
5. **Randomized**: Statistical validation

**Recommended combination for production:**
```
Walk-Forward + Monte Carlo + Randomized
```

**Red flags to watch for:**
- Confidence intervals include zero
- High variance across periods
- Strategy works on shuffled data
- Extreme sensitivity to parameters
- Results change drastically with small data changes

**Green lights for deployment:**
- Consistent performance in walk-forward
- Statistically significant results (CI > 0)
- Acceptable tail risks in Monte Carlo
- Robust across randomized trials
- Clear economic rationale for strategy

---

## Further Reading

### Books
- "Advances in Financial Machine Learning" by Marcos López de Prado
- "Quantitative Trading" by Ernest Chan
- "Evidence-Based Technical Analysis" by David Aronson

### Papers
- "The Deflated Sharpe Ratio" (Bailey & López de Prado, 2014)
- "Pseudo-Mathematics and Financial Charlatanism" (Bailey et al., 2014)
- "The Probability of Backtest Overfitting" (Bailey et al., 2016)

### Related Documentation
- [BACKTESTING_METHODS.md](BACKTESTING_METHODS.md) - Technical implementation details
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [STRATEGIES.md](STRATEGIES.md) - Trading strategies guide

---

**Last Updated**: November 2025  
**Version**: 1.0  
**Author**: AI Assistant

---
