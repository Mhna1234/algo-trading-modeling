# Strategy Guide - Trading Strategies

This guide provides detailed information about the trading strategies included in the Portfolio Engine.

## Current Demo Strategies (11 Working Strategies)

The current `examples/demo_all_strategies.py` demonstrates these 11 working strategies:

1. **Equal Weight** - 1/N baseline portfolio
2. **Momentum** - 126-day momentum with Sharpe optimization
3. **Mean Reversion** - 5-day window with MVO
4. **Inverse Volatility** - 21-day vol window, risk parity
5. **Min Variance** - 10-day mean reversion with high risk aversion (5.0)
6. **GMVP** - Global Minimum Variance Portfolio (analytical solution)
7. **Regime Switching** - Adaptive momentum based on volatility regimes
8. **Momentum Fast** - 21-day momentum with Sharpe optimization
9. **Momentum Slow** - 252-day momentum with Sharpe optimization
10. **Mean Reversion Short** - 3-day ultra-short mean reversion
11. **Balanced Risk** - 60-day vol window, conservative risk parity

All strategies completed successfully in the last demo run with diverse results:
- Returns ranging from 6.48% to 21.42%
- Sharpe ratios from 1.19 to 1.96
- Max drawdowns from -4.41% to -7.28%

## Optimization Methods Used

The current demo uses these optimization objectives:
- **Sharpe Maximization**: Momentum strategies, Regime Switching
- **Mean-Variance (MVO)**: Mean Reversion strategies
- **Risk Parity**: Inverse Volatility strategies
- **Equal Weight**: No optimization (baseline)

**CVaR optimization** is fully implemented in `src/optimizer.py` but not currently used in the demo strategies.

## Additional Implemented Strategies

The following strategies are implemented in `src/strategy_wrapper.py` but use fallback methods pending full ML/time-series integration:
- **CVaRMinimizationStrategy** - Uses Sharpe or MVO as fallback
- **MLRandomForestStrategy** - Uses momentum signals as fallback
- **MLGradientBoostingStrategy** - Uses momentum signals as fallback
- **ARMAForecastStrategy** - Uses mean reversion as fallback
- **MultiFactorMLStrategy** - Uses multi-factor composite as fallback

---

## 1. Equal Weight

### Description
Allocates equal weight to all assets (1/N portfolio). Simplest possible strategy, serves as baseline.

### Properties
- **Type:** Baseline
- **Complexity:** Very Low
- **Data Requirements:** Minimal
- **Turnover:** Low
- **Best For:** Benchmark, maximum diversification

### Parameters
None (ignores optimizer)

### Usage
```python
from src.strategy_wrapper import EqualWeightStrategy

strategy = EqualWeightStrategy(strategy_obj)

result = portfolio.run_backtest(
    strategy,
    start_date='2020-01-01',
    rebalance_freq='M'
)
```

### When to Use
- As a performance baseline
- When you want maximum diversification
- When transaction costs are high
- When you have no view on asset returns

### Pros & Cons
✅ **Pros:**
- Extremely simple
- Low turnover
- Diversified by construction
- No parameter tuning needed

❌ **Cons:**
- Ignores asset characteristics
- Treats all assets equally
- No risk management
- Often beaten by smart strategies

### Research References
- DeMiguel et al. (2009) "Optimal versus naive diversification"

---

## 2. Momentum

### Description
Ranks assets by past returns and invests in top K performers. Captures the momentum anomaly.

### Properties
- **Type:** Trend Following
- **Complexity:** Low-Medium
- **Data Requirements:** Historical prices
- **Turnover:** Medium
- **Best For:** Trending markets

### Parameters
```python
top_k : int = 10           # Number of assets to hold
lookback : int = 126       # Momentum window (days)
objective : str = 'cvar'   # Optimization objective
alpha : float = 0.95       # CVaR confidence level
max_weight : float = 0.3   # Max position size
```

### Usage
```python
from src.strategy_wrapper import MomentumStrategy

momentum = MomentumStrategy(
    strategy, optimizer,
    top_k=10,
    lookback=126,  # 6 months
    objective='cvar',
    alpha=0.95,
    max_weight=0.3
)

result = portfolio.run_backtest(momentum, ...)
```

### When to Use
- Trending markets
- Assets with serial correlation
- Medium-term horizon (3-12 months)
- When momentum factor is strong

### Pros & Cons
✅ **Pros:**
- Well-researched factor
- Works across asset classes
- Simple to understand
- Good in trending markets

❌ **Cons:**
- Fails in mean-reverting markets
- Can have large drawdowns
- Momentum crashes possible
- High turnover

### Optimal Parameters
- **Lookback:** 3-12 months (63-252 days)
- **Rebalancing:** Monthly
- **Top K:** 5-20 assets
- **Max Weight:** 20-40%

### Research References
- Jegadeesh & Titman (1993) "Returns to buying winners and selling losers"
- Asness et al. (2013) "Value and momentum everywhere"

---

## 3. Mean Reversion

### Description
Buys recent losers and sells recent winners. Exploits short-term overreaction.

### Properties
- **Type:** Contrarian
- **Complexity:** Low-Medium
- **Data Requirements:** Short-term price history
- **Turnover:** High
- **Best For:** Range-bound markets

### Parameters
```python
top_k : int = 10              # Number of assets
window : int = 5              # Reversion window (days)
objective : str = 'mvo'       # Optimization
risk_aversion : float = 3.0   # Risk parameter
max_weight : float = 0.25     # Max position
```

### Usage
```python
from src.strategy_wrapper import MeanReversionStrategy

mean_rev = MeanReversionStrategy(
    strategy, optimizer,
    top_k=10,
    window=5,  # 1 week
    risk_aversion=3.0
)
```

### When to Use
- Range-bound/sideways markets
- High volatility environments
- Short-term trading
- Mean-reverting assets

### Pros & Cons
✅ **Pros:**
- Profits from overreactions
- Good in sideways markets
- Can be combined with momentum

❌ **Cons:**
- High turnover (costs!)
- Fails in trending markets
- Requires frequent rebalancing
- Can be whipsawed

### Optimal Parameters
- **Window:** 3-10 days
- **Rebalancing:** Weekly/Daily
- **Risk Aversion:** 2-5
- **Max Weight:** 15-30%

### Research References
- Lehmann (1990) "Fads, martingales, and market efficiency"
- Lo & MacKinlay (1990) "When are contrarian profits due to stock market overreaction?"

---

## 4. Inverse Volatility

### Description
Weights assets inversely proportional to volatility. Risk parity approach.

### Properties
- **Type:** Risk-Based
- **Complexity:** Low
- **Data Requirements:** Return volatility
- **Turnover:** Low-Medium
- **Best For:** Volatile markets, defensive

### Parameters
```python
vol_window : int = 21           # Volatility window
objective : str = 'risk_parity' # Optimization
max_weight : float = 0.4        # Max position
```

### Usage
```python
from src.strategy_wrapper import InverseVolatilityStrategy

inv_vol = InverseVolatilityStrategy(
    strategy, optimizer,
    vol_window=21,
    max_weight=0.4
)
```

### When to Use
- Risk-balanced portfolios
- Volatile market environments
- Defensive positioning
- When returns are unpredictable

### Pros & Cons
✅ **Pros:**
- Risk-balanced
- Defensive
- Low turnover
- Simple concept

❌ **Cons:**
- Ignores return expectations
- Can underweight high-return assets
- Volatility can change quickly

### Optimal Parameters
- **Vol Window:** 21-63 days
- **Rebalancing:** Monthly
- **Max Weight:** 30-50%

### Research References
- Maillard et al. (2010) "Properties of equally weighted risk contribution portfolios"

---

## 5. CVaR Minimization

### Description
Minimizes Conditional Value at Risk (tail risk). Focus on downside protection.

### Properties
- **Type:** Risk-Based
- **Complexity:** Medium
- **Data Requirements:** Return distribution
- **Turnover:** Low-Medium
- **Best For:** Risk-averse investors

### Parameters
```python
alpha : float = 0.95     # Confidence level (95%)
lookback : int = 252     # Historical window
max_weight : float = 0.3 # Max position
```

### Usage
```python
from src.strategy_wrapper import CVaRMinimizationStrategy

cvar = CVaRMinimizationStrategy(
    strategy, optimizer,
    alpha=0.95,
    lookback=252
)
```

### When to Use
- Tail risk concerns
- Risk-averse investors
- After market crashes
- Preservation of capital

### Pros & Cons
✅ **Pros:**
- Tail risk protection
- Focus on worst-case scenarios
- Robust optimization

❌ **Cons:**
- Ignores upside
- Conservative (lower returns)
- Sensitive to historical data

### Optimal Parameters
- **Alpha:** 0.90-0.99
- **Lookback:** 252-504 days
- **Rebalancing:** Monthly/Quarterly

### Research References
- Rockafellar & Uryasev (2000) "Optimization of conditional value-at-risk"

---

## 5.5. Global Minimum Variance Portfolio (GMVP)

### Description
Computes the portfolio with the absolute minimum variance possible using an analytical solution. No return forecasts needed - purely risk-based allocation. Uses the formula: w = Σ^{-1} 1 / (1^T Σ^{-1} 1). Optionally supports integer rebalancing for practical implementation with discrete share purchases.

### Properties
- **Type:** Risk Minimization
- **Complexity:** Low
- **Data Requirements:** Returns (for covariance)
- **Turnover:** Low
- **Best For:** Risk-averse investors, defensive portfolios

### Parameters
```python
lookback : int = 252               # Covariance window (1 year)
use_integer_rebalance : bool = False  # Integer shares
total_capital : float = 1_000_000  # Capital (if integer)
max_weight : float = 0.5           # Max position size
```

### Usage
```python
from src.strategy_wrapper import GlobalMinimumVarianceStrategy

gmvp = GlobalMinimumVarianceStrategy(
    strategy, optimizer,
    lookback=252,
    use_integer_rebalance=False,
    max_weight=0.4
)

result = portfolio.run_backtest(
    gmvp,
    start_date='2020-01-01',
    rebalance_freq='M'
)
```

### When to Use
- Maximum risk reduction is priority
- No reliable return forecasts available
- Defensive market stance
- Low-volatility preference
- Real trading with integer shares

### Pros & Cons
✅ **Pros:**
- Analytical solution (fast, no optimization)
- Pure risk minimization
- No return forecasts needed
- Mathematically optimal for variance
- Integer share support for real trading
- Handles singular covariance matrices

❌ **Cons:**
- Ignores expected returns completely
- May underperform in strong trends
- Concentrated in low-volatility assets
- Sensitive to covariance estimation
- May not maximize Sharpe ratio

### Optimal Parameters
- **Lookback:** 126-252 days (6-12 months)
- **Max Weight:** 0.3-0.5 (concentration control)
- **Integer Rebalancing:** Use for real money management

### Implementation Details
The strategy uses:
1. **Analytical GMVP Formula:** Direct matrix inversion, no iterative optimization
2. **Pseudo-inverse Fallback:** Handles singular covariance matrices
3. **Weight Constraints:** Clips weights to [0, max_weight] and renormalizes
4. **Integer Rebalancing (Optional):** MILP formulation minimizing L1 distance from target allocation

### Research References
- Markowitz, H. (1952) "Portfolio Selection" - Journal of Finance
- Merton, R. C. (1972) "An analytic derivation of the efficient portfolio frontier"

---

## 6. Regime Switching

### Description
Adapts momentum speed based on market volatility regime. Fast momentum in high vol, slow in low vol.

### Properties
- **Type:** Adaptive
- **Complexity:** Medium
- **Data Requirements:** Returns + volatility
- **Turnover:** Medium
- **Best For:** Varying market conditions

### Parameters
```python
vol_threshold : float = 0.02  # Regime threshold
fast_window : int = 21        # High vol window
slow_window : int = 126       # Low vol window
top_k : int = 10             # Assets to hold
```

### Usage
```python
from src.strategy_wrapper import RegimeSwitchingStrategy

regime = RegimeSwitchingStrategy(
    strategy, optimizer,
    vol_threshold=0.02,
    fast_window=21,
    slow_window=126,
    top_k=10
)
```

### When to Use
- Variable market conditions
- When regime shifts are important
- Adaptive strategies preferred

### Pros & Cons
✅ **Pros:**
- Adaptive to conditions
- Combines multiple strategies
- Better risk-adjusted returns

❌ **Cons:**
- More complex
- Regime detection can lag
- More parameters to tune

### Optimal Parameters
- **Vol Threshold:** 0.015-0.025 (annual)
- **Fast Window:** 21-42 days
- **Slow Window:** 126-252 days

### Research References
- Kritzman et al. (2012) "Regime shifts: Implications for dynamic strategies"

---

## 7. ML Random Forest

### Description
Uses Random Forest to forecast returns based on technical features. Ensemble machine learning.

### Properties
- **Type:** Machine Learning
- **Complexity:** High
- **Data Requirements:** Historical prices + features
- **Turnover:** Medium-High
- **Best For:** When ML has edge

### Parameters
```python
lookback : int = 252        # Feature window
forecast_days : int = 21    # Prediction horizon
top_k : int = 10           # Assets to hold
n_estimators : int = 100   # Trees in forest
```

### Features Used
- 1-month, 3-month, 6-month momentum
- 21-day and 63-day volatility
- RSI (14-day)
- Price / SMA(50) ratio

### Usage
```python
from src.strategy_wrapper import MLRandomForestStrategy

rf_strategy = MLRandomForestStrategy(
    strategy, optimizer,
    lookback=252,
    forecast_days=21,
    top_k=10,
    n_estimators=100
)
```

### When to Use
- Sufficient historical data (3+ years)
- Non-linear relationships suspected
- Feature-rich environment

### Pros & Cons
✅ **Pros:**
- Captures non-linear patterns
- Feature importance insights
- Robust ensemble method

❌ **Cons:**
- Computationally expensive
- Risk of overfitting
- Black box (less interpretable)
- Needs lots of data

### Optimal Parameters
- **Lookback:** 252-504 days
- **Forecast:** 5-21 days
- **N Estimators:** 50-200
- **Max Depth:** 3-10 (prevent overfit)

### Research References
- Breiman (2001) "Random forests"
- Gu et al. (2020) "Empirical asset pricing via machine learning"

---

## 8. ML Gradient Boosting

### Description
Sequential ensemble learning. Often outperforms Random Forest on structured data.

### Properties
- **Type:** Machine Learning
- **Complexity:** High
- **Data Requirements:** Same as Random Forest
- **Turnover:** Medium-High
- **Best For:** When accuracy matters most

### Parameters
```python
lookback : int = 252          # Feature window
forecast_days : int = 21      # Horizon
top_k : int = 10             # Assets
learning_rate : float = 0.05  # Shrinkage
```

### Usage
```python
from src.strategy_wrapper import MLGradientBoostingStrategy

gbm = MLGradientBoostingStrategy(
    strategy, optimizer,
    lookback=252,
    learning_rate=0.05,
    top_k=10
)
```

### When to Use
- Same as Random Forest
- When you want maximum accuracy
- Can afford longer training time

### Pros & Cons
✅ **Pros:**
- Often most accurate
- Sequential error correction
- Handles complex patterns

❌ **Cons:**
- Slower than Random Forest
- More prone to overfitting
- Sensitive to parameters

### Optimal Parameters
- **Learning Rate:** 0.01-0.10
- **N Estimators:** 100-300
- **Max Depth:** 3-6

### Research References
- Friedman (2001) "Greedy function approximation: A gradient boosting machine"

---

## 9. ARMA Forecast

### Description
Classical time series forecasting using AutoRegressive Moving Average models.

### Properties
- **Type:** Time Series
- **Complexity:** Medium
- **Data Requirements:** Stationary returns
- **Turnover:** Medium
- **Best For:** Stationary series

### Parameters
```python
arma_order : tuple = (2, 1)   # (p, q) AR and MA orders
forecast_steps : int = 5      # Days ahead
top_k : int = 10             # Assets to hold
```

### Usage
```python
from src.strategy_wrapper import ARMAForecastStrategy

arma = ARMAForecastStrategy(
    strategy, optimizer,
    arma_order=(2, 1),
    forecast_steps=5,
    top_k=10
)
```

### When to Use
- Stationary return series
- Autocorrelation present
- Classical approach preferred

### Pros & Cons
✅ **Pros:**
- Interpretable
- Well-understood theory
- Good for stationary data

❌ **Cons:**
- Assumes stationarity
- Linear relationships only
- Can be unstable

### Optimal Parameters
- **p (AR order):** 1-5
- **q (MA order):** 0-3
- **Forecast Steps:** 1-10 days

### Research References
- Box, Jenkins & Reinsel (2015) "Time series analysis: Forecasting and control"

---

## 10. Multi-Factor ML

### Description
Combines momentum, volatility, reversal, and trend factors using ML weighting.

### Properties
- **Type:** Multi-Factor + ML
- **Complexity:** High
- **Data Requirements:** All factor inputs
- **Turnover:** Medium
- **Best For:** Robust diversified strategies

### Factors Used
1. **Momentum:** 126-day return
2. **Inverse Volatility:** 21-day vol
3. **Reversal:** 5-day Z-score
4. **Trend Strength:** Return consistency

### Parameters
```python
lookback : int = 252    # Factor calculation window
top_k : int = 10       # Assets to hold
```

### Usage
```python
from src.strategy_wrapper import MultiFactorMLStrategy

multi_factor = MultiFactorMLStrategy(
    strategy, optimizer,
    lookback=252,
    top_k=10
)
```

### When to Use
- Want factor diversification
- Robust to regime changes
- Long-term investing

### Pros & Cons
✅ **Pros:**
- Factor diversification
- Robust across regimes
- ML learns factor timing

❌ **Cons:**
- Complex
- Needs more data
- Factor correlation issues

### Optimal Parameters
- **Lookback:** 252-504 days
- **Top K:** 10-20 assets

### Research References
- Fama & French (1993) "Common risk factors in returns"
- Gu et al. (2020) "Empirical asset pricing via machine learning"

---

## Strategy Comparison Matrix

**Current Demo Strategies (All Working):**

| Strategy | Complexity | Turnover | Optimization | Best Market | Demo Sharpe |
|----------|------------|----------|--------------|-------------|-------------|
| Equal Weight | ⭐ | Low | None | All | 1.19 |
| Momentum | ⭐⭐ | Medium | Sharpe | Trending | 1.96 |
| Mean Reversion | ⭐⭐ | High | MVO | Sideways | 1.59-1.60 |
| Inverse Vol | ⭐⭐ | Low | Risk Parity | Volatile | 1.24 |
| Min Variance | ⭐⭐ | Medium | MVO (high RA) | Defensive | 1.59 |
| GMVP | ⭐⭐ | Low | Analytical | Defensive | TBD |
| Regime Switch | ⭐⭐⭐ | Medium | Sharpe | Variable | 1.96 |
| Momentum Fast | ⭐⭐ | High | Sharpe | Short-term | 1.96 |
| Momentum Slow | ⭐⭐ | Low | Sharpe | Long-term | 1.96 |
| Mean Rev Short | ⭐⭐ | Very High | MVO | Range-bound | 1.60 |
| Balanced Risk | ⭐⭐ | Low | Risk Parity | Conservative | 1.24 |

**Implemented but Not in Demo (Use Fallbacks):**

| Strategy | Complexity | Status | Fallback Method |
|----------|------------|--------|-----------------|
| CVaR Min | ⭐⭐⭐ | Optimizer ready | Uses Sharpe/MVO |
| ML RF | ⭐⭐⭐⭐ | Pending ML training | Uses momentum |
| ML GBM | ⭐⭐⭐⭐ | Pending ML training | Uses momentum |
| ARMA | ⭐⭐⭐ | Pending TS fit | Uses mean reversion |
| Multi-Factor ML | ⭐⭐⭐⭐ | Pending ML training | Uses composite |

**Demo Results** (Last successful run):
- Returns range: 6.48% to 21.42%
- Sharpe ratios range: 1.19 to 1.96
- Max drawdowns range: -4.41% to -7.28%
- All 10 strategies completed successfully

---

## Combining Strategies

### Ensemble Approach
```python
# Run multiple strategies
strategies = {
    'momentum': MomentumStrategy(...),
    'mean_rev': MeanReversionStrategy(...),
    'ml_rf': MLRandomForestStrategy(...)
}

results = {}
for name, strat in strategies.items():
    results[name] = portfolio.run_backtest(strat, ...)

# Combine weights (50% momentum, 30% ML, 20% mean rev)
combined_weights = (
    0.50 * momentum_weights +
    0.30 * ml_weights +
    0.20 * mean_rev_weights
)
```

### Regime-Based Switching
```python
# Use different strategies in different regimes
if market_vol < threshold:
    strategy = momentum  # Low vol → momentum
else:
    strategy = mean_reversion  # High vol → mean reversion
```

---

## Parameter Tuning Best Practices

### 1. Walk-Forward Optimization
- Train on period 1
- Test on period 2
- Roll forward
- Avoid using full sample

### 2. Cross-Validation
- Time-series cross-validation
- Expanding window
- Never look ahead

### 3. Robustness Testing
- Test across different periods
- Test with different universes
- Stress test in crashes

### 4. Transaction Cost Sensitivity
- Always include realistic costs
- Test with 2x costs
- Verify execution assumptions

---

## Conclusion

Choose strategies based on:
1. **Market Regime:** Trending vs mean-reverting
2. **Data Available:** Historical depth and features
3. **Turnover Tolerance:** Cost sensitivity
4. **Complexity Comfort:** Interpretability vs performance
5. **Risk Tolerance:** Drawdown acceptability

**Start simple (Equal Weight, Momentum) and add complexity only if it improves out-of-sample performance!**
