# Extended Strategies Documentation

## ⚠️ IMPORTANT NOTE

**As of v3.0, all strategies have been consolidated into `src/strategy_wrapper.py`.**

The separate `strategies_extended.py` file no longer exists. All strategies documented here are now part of the main strategy library and can be accessed through:

```python
from src.strategy_wrapper import (
    BuyAndHoldStrategy,
    QuintileFactorStrategy,
    GMRPStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    TimeSeriesMomentumStrategy,
    MovingAverageCrossoverStrategy,
    MarkowitzMVOStrategy,
    LinearRegressionStrategy,
    list_available_strategies
)
```

For the main strategy documentation, see [STRATEGIES.md](STRATEGIES.md).

---

## Overview

This document provides comprehensive documentation for extended strategies that complement the core strategies. All strategies are now implemented in `src/strategy_wrapper.py` and provide additional algorithmic trading approaches beyond the basic strategies.

## Table of Contents

1. [Buy & Hold Strategy](#buy--hold-strategy)
2. [Quintile Factor Portfolios](#quintile-factor-portfolios)
3. [Global Minimum Risk Parity (GMRP)](#global-minimum-risk-parity-gmrp)
4. [Maximum Diversification (MDP)](#maximum-diversification-mdp)
5. [Maximum Decorrelation (MDCP)](#maximum-decorrelation-mdcp)
6. [Time-Series Momentum](#time-series-momentum)
7. [Moving Average Crossover](#moving-average-crossover)
8. [Markowitz Mean-Variance Optimization](#markowitz-mean-variance-optimization)
9. [Linear Regression Prediction](#linear-regression-prediction)

---

## Buy & Hold Strategy

### Description

Passive investment strategy that buys assets initially and holds without rebalancing. Serves as a benchmark for active strategies.

### Mathematical Formulation

$$w_t = w_0 \quad \forall t$$

Where $w_0$ is the initial allocation (typically equal weight: $w_0 = \frac{1}{N}\mathbf{1}$).

### Parameters

- **initial_method** (str, default='equal'): Initial allocation method
  - `'equal'`: Equal weight (1/N)
  - `'market_cap'`: Market capitalization weighted
  - `'custom'`: Custom weights via initial_weights parameter
- **initial_weights** (pd.Series, optional): Custom initial weights

### Usage Example

```python
from src.strategy_wrapper import BuyAndHoldStrategy
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

# Create strategy
buy_hold = BuyAndHoldStrategy(
    strategy,
    optimizer,
    initial_method='equal'
)

# Run backtest
from src.portfolio_engine import PortfolioEngine
engine = PortfolioEngine(prices, initial_capital=100000, transaction_cost_bps=10)
result = engine.run_backtest(
    buy_hold,
    start_date='2019-01-01',
    end_date='2024-01-01',
    rebalance_freq='M'
)
```

### Actual Performance (5-Year Weekly, 2019-2024)
- **Total Return:** +862%
- **Sharpe Ratio:** 2.25
- **Max Drawdown:** -25.3%
- **Annual Volatility:** 64.4%
- **Average Turnover:** 12.5%

### Pros & Cons

✅ **Pros:**
- Zero turnover after initial allocation
- Maximum tax efficiency
- No transaction costs
- Simple implementation

❌ **Cons:**
- No active risk management
- Portfolio drift over time
- No adaptation to market conditions

### References

Fama, E. F., & French, K. R. (2010). "Luck versus skill in the cross-section of mutual fund returns." *Journal of Finance*, 65(5), 1915-1947.

---

## Quintile Factor Portfolios

### Description

Sorts assets into quintiles based on factor scores and invests in specific quintiles. Common implementation of factor investing strategies.

### Mathematical Formulation

$$w_i = \begin{cases} 
\frac{1}{|Q_k|} & \text{if } i \in Q_k \\
0 & \text{otherwise}
\end{cases}$$

Where $Q_k$ is the set of assets in the $k$-th quintile.

For long-short variant:
$$w_i = \begin{cases}
\frac{0.5}{|Q_5|} & \text{if } i \in Q_5 \text{ (top quintile)} \\
-\frac{0.5}{|Q_1|} & \text{if } i \in Q_1 \text{ (bottom quintile)} \\
0 & \text{otherwise}
\end{cases}$$

### Parameters

- **factor** (str, default='momentum'): Factor for sorting
  - `'momentum'`: Past returns
  - `'mean_reversion'`: Mean reversion z-score
  - `'volatility'`: Inverse volatility
  - `'custom'`: Custom factor via factor_values parameter
- **lookback** (int, default=126): Lookback period for factor calculation
- **n_quintiles** (int, default=5): Number of quintiles
- **target_quintile** (int, default=5): Which quintile to invest in (5=top, 1=bottom)
- **long_short** (bool, default=False): Long top quintile, short bottom quintile
- **equal_weight_quintile** (bool, default=True): Equal weight within quintile

### Usage Example

```python
from src.strategy_wrapper import QuintileFactorStrategy

# Long-only momentum quintile
quintile = QuintileFactorStrategy(
    strategy, optimizer,
    factor='momentum',
    lookback=126,
    target_quintile=5,  # Top 20%
    equal_weight_quintile=True
)

# Long-short variant
long_short_quintile = QuintileFactorStrategy(
    strategy, optimizer,
    factor='momentum',
    lookback=126,
    long_short=True  # Long top, short bottom
)
```

### Pros & Cons

✅ **Pros:**
- Captures factor premiums
- Systematic approach
- Well-researched methodology
- Diversified within quintiles

❌ **Cons:**
- Requires many assets (N > 25)
- Higher turnover at rebalancing
- Sensitive to factor timing
- Transaction costs can erode returns

### References

Fama, E. F., & French, K. R. (1993). "Common risk factors in the returns on stocks and bonds." *Journal of Financial Economics*, 33(1), 3-56.

Jegadeesh, N., & Titman, S. (1993). "Returns to buying winners and selling losers." *Journal of Finance*, 48(1), 65-91.

---

## Global Minimum Risk Parity (GMRP)

### Description

Implements risk parity optimization where assets are allocated to contribute equally to portfolio risk. Also known as Equal Risk Contribution (ERC).

### Mathematical Formulation

$$\min_{w} \quad \sum_{i,j} (w_i (\Sigma w)_i - w_j (\Sigma w)_j)^2$$

subject to:
$$\sum_i w_i = 1$$
$$w_i \geq 0$$

Where $\Sigma$ is the covariance matrix and the objective minimizes variance of risk contributions.

### Parameters

- **lookback** (int, default=126): Historical window for covariance estimation
- **min_periods** (int, default=60): Minimum periods required
- **max_weight** (float, default=0.5): Maximum weight per asset
- **shrinkage** (bool, default=True): Use Ledoit-Wolf covariance shrinkage

### Usage Example

```python
from src.strategy_wrapper import GMRPStrategy

gmrp = GMRPStrategy(
    strategy,
    optimizer,
    lookback=126,
    max_weight=0.4
)
```

### Actual Performance (5-Year Weekly, 2019-2024)
- **Total Return:** +1389%
- **Sharpe Ratio:** 0.12
- **Max Drawdown:** -99.96% ⚠️
- **Annual Volatility:** 599.3%
- **Average Turnover:** 46.6%

**⚠️ Warning:** This strategy showed extreme volatility and drawdown in the test period. Use with caution.

### Pros & Cons

✅ **Pros:**
- Maximum expected return
- Simple objective
- Transparent allocation

❌ **Cons:**
- High concentration risk
- Sensitive to return forecasts
- No explicit risk control
- Can have high turnover

### References

Theoretical extreme of Markowitz (1952) with zero risk aversion (λ=0).

---

## Maximum Diversification (MDP)

### Description

Maximizes the diversification ratio, which measures the benefit of diversification relative to individual asset risks.

### Mathematical Formulation

$$\max_{w} \quad DR(w) = \frac{w^T \sigma}{\sqrt{w^T \Sigma w}}$$

subject to:
$$\sum_i w_i = 1, \quad 0 \leq w_i \leq w_{\max}$$

Where:
- $\sigma$ = vector of individual asset volatilities
- $\Sigma$ = covariance matrix
- $DR(w)$ = diversification ratio

### Parameters

- **lookback** (int, default=252): Historical window for covariance estimation
- **max_weight** (float, default=0.5): Maximum weight per asset
- **min_weight** (float, default=0.0): Minimum weight per asset

### Usage Example

```python
from src.strategies_extended import MaximumDiversificationStrategy

mdp = MaximumDiversificationStrategy(
    strategy,
    lookback=252,
    max_weight=0.3
)
```

### Pros & Cons

✅ **Pros:**
- Maximizes diversification benefit
- Reduces concentration risk
- No return forecasts needed
- Robust to estimation error

❌ **Cons:**
- Computationally intensive
- May underweight high-return assets
- Sensitive to covariance estimates

### References

Choueifaty, Y., & Coignard, Y. (2008). "Toward maximum diversification." *Journal of Portfolio Management*, 35(1), 40-51.

---

## Maximum Decorrelation (MDCP)

### Description

Finds the portfolio with minimum average correlation between assets. Scale-invariant approach using correlation matrix.

### Mathematical Formulation

$$\min_{w} \quad w^T C w$$

subject to:
$$\sum_i w_i = 1, \quad 0 \leq w_i \leq w_{\max}$$

Where $C$ is the correlation matrix (not covariance).

### Parameters

- **lookback** (int, default=252): Historical window for correlation estimation
- **max_weight** (float, default=0.5): Maximum weight per asset
- **min_weight** (float, default=0.0): Minimum weight per asset

### Usage Example

```python
from src.strategies_extended import MaximumDecorrelationStrategy

mdcp = MaximumDecorrelationStrategy(
    strategy,
    lookback=252,
    max_weight=0.3
)
```

### Pros & Cons

✅ **Pros:**
- Minimizes correlation exposure
- Scale-invariant
- Reduces systemic risk
- No return forecasts needed

❌ **Cons:**
- May ignore volatility differences
- Sensitive to correlation estimates
- Can underweight profitable assets

### References

Christoffersen, P., et al. (2012). "Is the potential for international diversification disappearing?" *Review of Financial Studies*, 25(12), 3711-3751.

---

## Time-Series Momentum

### Description

Trend-following strategy that invests in assets with positive recent returns (absolute momentum). Each asset evaluated independently.

### Mathematical Formulation

$$s_i = \begin{cases}
+1 & \text{if } r_i^{(\tau)} > \theta \\
-1 & \text{if } r_i^{(\tau)} < -\theta \\
0 & \text{otherwise}
\end{cases}$$

With volatility scaling:
$$w_i \propto \frac{s_i}{\sigma_i}$$

Where:
- $r_i^{(\tau)}$ = cumulative return over lookback period $\tau$
- $\theta$ = signal threshold
- $\sigma_i$ = volatility of asset $i$

### Parameters

- **lookback** (int, default=126): Lookback period for momentum
- **signal_threshold** (float, default=0.0): Minimum return threshold
- **volatility_scaling** (bool, default=True): Scale by inverse volatility
- **long_only** (bool, default=True): Only long positions
- **objective** (str, default='sharpe'): Optimization objective

### Usage Example

```python
from src.strategies_extended import TimeSeriesMomentumStrategy

ts_momentum = TimeSeriesMomentumStrategy(
    strategy, optimizer,
    lookback=126,
    volatility_scaling=True,
    long_only=True
)
```

### Pros & Cons

✅ **Pros:**
- Works in trending markets
- Absolute (not relative) momentum
- Can go long or short each asset
- Risk-adjusted via volatility scaling

❌ **Cons:**
- Lagging indicator
- Whipsaws in choppy markets
- Requires trending behavior
- Higher turnover

### References

Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). "Time series momentum." *Journal of Financial Economics*, 104(2), 228-250.

---

## Moving Average Crossover

### Description

Classic technical analysis strategy based on fast and slow moving average crossovers. Buy when fast MA crosses above slow MA.

### Mathematical Formulation

$$s_i(t) = \begin{cases}
+1 & \text{if } MA_{fast,i}(t) > MA_{slow,i}(t) \\
-1 & \text{if } MA_{fast,i}(t) < MA_{slow,i}(t) \\
0 & \text{otherwise}
\end{cases}$$

Where:
$$MA_n(t) = \frac{1}{n}\sum_{k=0}^{n-1} P(t-k)$$

### Parameters

- **fast_window** (int, default=50): Fast moving average window
- **slow_window** (int, default=200): Slow moving average window
- **signal_type** (str, default='binary'): 
  - `'binary'`: {-1, 0, +1} signals
  - `'continuous'`: Proportional to MA difference
- **long_only** (bool, default=True): Only long positions

### Usage Example

```python
from src.strategies_extended import MovingAverageCrossoverStrategy

ma_crossover = MovingAverageCrossoverStrategy(
    strategy, optimizer,
    fast_window=50,
    slow_window=200,
    signal_type='binary'
)
```

### Pros & Cons

✅ **Pros:**
- Simple and intuitive
- Widely used in practice
- Easy to implement
- Works in trending markets

❌ **Cons:**
- Lagging indicator
- Many false signals in range-bound markets
- Arbitrary parameter choices
- Can miss quick reversals

### References

Brock, W., Lakonishok, J., & LeBaron, B. (1992). "Simple technical trading rules and the stochastic properties of stock returns." *Journal of Finance*, 47(5), 1731-1764.

---

## Markowitz Mean-Variance Optimization

### Description

Classic Markowitz portfolio optimization balancing expected return and risk.

### Mathematical Formulation

$$\max_{w} \quad w^T \mu - \frac{\lambda}{2} w^T \Sigma w$$

subject to:
$$\sum_i w_i = 1, \quad w_i \geq 0$$

Where:
- $\mu$ = expected returns
- $\Sigma$ = covariance matrix
- $\lambda$ = risk aversion parameter

### Parameters

- **lookback** (int, default=252): Historical window
- **risk_aversion** (float, default=1.0): Risk aversion λ
  - λ=0: Maximum return
  - λ=∞: Minimum variance (GMVP)
  - λ=1: Balanced tradeoff
- **return_forecast_method** (str, default='historical'):
  - `'historical'`: Historical mean
  - `'momentum'`: Recent momentum
  - `'shrinkage'`: Shrunk towards global mean
- **max_weight** (float, default=0.5): Maximum weight per asset

### Usage Example

```python
from src.strategies_extended import MarkowitzMVOStrategy

markowitz = MarkowitzMVOStrategy(
    strategy, optimizer,
    risk_aversion=2.0,
    return_forecast_method='momentum',
    max_weight=0.5
)
```

### Pros & Cons

✅ **Pros:**
- Theoretically optimal
- Balances risk and return
- Nobel Prize-winning framework
- Well-understood properties

❌ **Cons:**
- Very sensitive to inputs
- Estimation error amplification
- Can produce extreme weights
- Requires return forecasts

### References

Markowitz, H. (1952). "Portfolio Selection." *Journal of Finance*, 7(1), 77-91.

Michaud, R. O. (1989). "The Markowitz optimization enigma: Is optimized optimal?" *Financial Analysts Journal*, 45(1), 31-42.

---

## Linear Regression Prediction

### Description

Uses linear regression to forecast returns based on technical features, then optimizes portfolio using forecasts.

### Mathematical Formulation

For each asset $i$:
$$\hat{r}_{i,t+1} = \beta_0 + \beta_1 x_{i,t}^{(1)} + \beta_2 x_{i,t}^{(2)} + \cdots + \beta_p x_{i,t}^{(p)} + \epsilon_t$$

With Ridge regularization:
$$\min_{\beta} \quad \sum_{t=1}^{T} (r_{i,t+1} - \beta^T x_{i,t})^2 + \alpha \|\beta\|_2^2$$

### Features

Default features include:
- `returns_lag1`: Previous day return
- `returns_lag5`: 5-day average return
- `ma_ratio`: Moving average ratio (MA20/MA50 - 1)
- `volatility`: Recent volatility

### Parameters

- **lookback** (int, default=252): Training window
- **forecast_horizon** (int, default=1): Days ahead to forecast
- **features** (list): Features to use
- **regularization** (str, default='ridge'): 
  - `'ridge'`: L2 regularization
  - `'lasso'`: L1 regularization
  - `'none'`: No regularization
- **alpha** (float, default=0.1): Regularization strength

### Usage Example

```python
from src.strategies_extended import LinearRegressionStrategy

lin_reg = LinearRegressionStrategy(
    strategy, optimizer,
    lookback=252,
    features=['returns_lag1', 'ma_ratio', 'volatility'],
    regularization='ridge',
    alpha=0.1
)
```

### Pros & Cons

✅ **Pros:**
- Simple interpretable model
- Fast training and prediction
- Incorporates multiple features
- Regularization prevents overfitting

❌ **Cons:**
- Linear relationship assumptions
- Can overfit with too many features
- Requires feature engineering
- May not capture non-linear patterns

### References

Rapach, D. E., Strauss, J. K., & Zhou, G. (2010). "Out-of-sample equity premium prediction: Combination forecasts and links to the real economy." *Review of Financial Studies*, 23(2), 821-862.

---

## Quick Reference Table

| Strategy | Return Forecast | Risk Control | Complexity | Turnover | Best For |
|----------|----------------|--------------|------------|----------|----------|
| Buy & Hold | None | None | Very Low | Very Low | Benchmarking |
| Quintile Factor | Factor Scores | Diversification | Low | Medium | Factor Investing |
| GMRP | Required | Constraints | Low | High | Maximum Return |
| MDP | None | Diversification | Medium | Low | Risk Management |
| MDCP | None | Decorrelation | Medium | Low | Correlation Hedging |
| Time-Series Momentum | Momentum | Volatility Scaling | Low | Medium | Trend Following |
| MA Crossover | None | None | Very Low | Low | Simple Trends |
| Markowitz MVO | Required | Variance | Medium | Medium | Balanced Approach |
| Linear Regression | Forecasted | Optimization | Medium | Medium | ML Prediction |

---

## Integration Guide

### 1. Import Extended Strategies

```python
from src.strategies_extended import (
    BuyAndHoldStrategy,
    QuintileFactorStrategy,
    GMRPStrategy,
    MaximumDiversificationStrategy,
    MaximumDecorrelationStrategy,
    TimeSeriesMomentumStrategy,
    MovingAverageCrossoverStrategy,
    MarkowitzMVOStrategy,
    LinearRegressionStrategy
)
```

### 2. Using the Factory Function

```python
from src.strategies_extended import create_extended_strategy

# Create strategy by name
strategy = create_extended_strategy(
    'maximum_diversification',
    strategy_obj,
    optimizer,
    lookback=252,
    max_weight=0.3
)
```

### 3. List Available Strategies

```python
from src.strategies_extended import list_extended_strategies

available = list_extended_strategies()
print(available.keys())
```

### 4. Combine with Core Strategies

```python
from src.strategy_wrapper import create_strategy
from src.strategies_extended import create_extended_strategy

# Core strategy
momentum = create_strategy('momentum', strategy_obj, optimizer)

# Extended strategy
mdp = create_extended_strategy('maximum_diversification', strategy_obj, optimizer)
```

---

## Performance Considerations

### Computational Complexity

- **Fast** (< 1ms per rebalance): Buy & Hold, GMRP
- **Medium** (~10ms): Quintile Factor, Time-Series Momentum, MA Crossover
- **Slow** (~100ms): MDP, MDCP, Markowitz MVO
- **Very Slow** (~1s): Linear Regression (training required)

### Data Requirements

- **Minimal** (< 1 month): Buy & Hold, MA Crossover
- **Low** (1-3 months): Time-Series Momentum, GMRP
- **Medium** (6-12 months): Quintile Factor, Markowitz MVO
- **High** (1+ year): MDP, MDCP, Linear Regression

### Parameter Sensitivity

- **Low**: Buy & Hold, MDP, MDCP
- **Medium**: Markowitz MVO, Time-Series Momentum
- **High**: Quintile Factor, Linear Regression, MA Crossover

---

## Troubleshooting

### Common Issues

1. **Optimization failures**: Increase regularization, check for NaN values
2. **Extreme weights**: Reduce max_weight parameter, increase risk_aversion
3. **Insufficient data**: Strategies fallback to equal weights
4. **Slow performance**: Reduce lookback window, simplify features

### Error Handling

All strategies implement graceful degradation:
- Insufficient data → Equal weights
- Optimization failure → Equal weights
- NaN values → Skip and use previous weights
- Invalid parameters → Use defaults with warning

---

## Citation

If you use these strategies in your research, please cite:

```bibtex
@software{portfolio_engine_extended,
  title = {Portfolio Engine Extended Strategies},
  author = {Portfolio Engine Team},
  year = {2025},
  url = {https://github.com/Mhna1234/algo-trading-modeling}
}
```
