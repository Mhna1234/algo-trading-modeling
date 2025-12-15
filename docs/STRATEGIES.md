# Strategy Guide - Trading Strategies v3.0

This guide provides detailed information about the **12 validated benchmark strategies** in the Portfolio Engine.

## Strategy Overview (12 Validated Benchmark Strategies)

All 12 strategies have been rigorously validated with comprehensive testing including 10-year full backtests (2015-2025) with monthly rebalancing and realistic transaction cost modeling. All strategies are implemented in `src/strategy_wrapper.py`.

**Version**: 3.0.0 | **Last Updated**: December 15, 2025

See [VALIDATION_COMPLETE.md](../VALIDATION_COMPLETE.md) for detailed validation results.

### Passive/Baseline Strategies (2)
1. **Buy & Hold** - Market cap weighted benchmark
2. **Equal Weight (1/N)** - Naive diversification baseline

### Factor-Based Strategies (3)
3. **Quintile Momentum** - Cross-sectional momentum (top 20%)
4. **Quintile Low Volatility** - Low volatility factor (bottom 20%)
5. **Mean Reversion Quintile** - Contrarian strategy

### Risk-Based Optimization (5)
6. **Global Minimum Variance (GMVP)** - Minimum portfolio volatility
7. **Inverse Volatility** - Weight inversely proportional to volatility
8. **Risk Parity** - Equal risk contribution across assets
9. **Maximum Diversification** - Maximize diversification ratio
10. **Maximum Decorrelation** - Minimize average correlation

### Return-Based Optimization (2)
11. **Sharpe Ratio Maximization** - Mean-variance optimization
12. **CVaR Minimization** - Conditional Value-at-Risk minimization

---

## Multi-Armed Bandit (MAB) Meta-Strategy

In addition to the 12 benchmark strategies, the system includes a **Multi-Armed Bandit (MAB)** meta-strategy that dynamically allocates capital across strategies:

- **UCB (Upper Confidence Bound)** - Deterministic exploration-exploitation balance
- **Thompson Sampling** - Bayesian posterior sampling approach
- **Configurable Rewards** - Returns, Sharpe ratio, or Sortino ratio
- **Soft Allocation** - Probabilistic strategy selection

See [BANDIT_EXPLANATION.md](../BANDIT_EXPLANATION.md) for details.

## Validated Performance (10-Year Monthly, 2015-2025)

**Test Configuration:**
- Period: November 2015 - November 2025 (10 years)
- Rebalancing: Monthly (121 rebalances)
- Transaction costs: 10 bps per rebalance (0.1%)
- Slippage: 1 bp
- Initial capital: $100,000
- Assets: 20 tickers

**Key Finding**: Monthly rebalancing is critical for positive returns. Daily rebalancing leads to excessive transaction costs that eliminate gains.

### 12 Benchmark Strategies Performance

| Rank | Strategy | CAGR | Total Return | Sharpe | Volatility | Max DD | Sortino | Win Rate |
|------|----------|------|--------------|--------|------------|--------|---------|----------|
| 1 | **Mean Reversion** | **28.23%** | **+1033%** | **0.968** | 27.68% | -38.84% | 1.101 | 53.2% |
| 2 | **Max Decorrelation** | **24.44%** | **+883%** | **1.052** | 21.00% | -33.03% | **1.265** | 54.7% |
| 3 | **Sharpe Maximization** | **23.90%** | **+849%** | **0.810** | 29.66% | -40.95% | 0.854 | 53.0% |
| 4 | **Buy & Hold** | 17.25% | +389% | 0.904 | 19.08% | -34.04% | 0.976 | 54.5% |
| 5 | **Equal Weight** | 17.25% | +389% | 0.826 | 19.08% | -34.04% | 0.976 | 54.5% |
| 6 | **Max Diversification** | 16.57% | +366% | 0.890 | 16.53% | -27.38% | 1.040 | 53.8% |
| 7 | **Inverse Volatility** | 14.50% | +307% | 0.795 | 16.19% | -28.59% | 0.910 | 52.2% |
| 8 | **Risk Parity** | 13.72% | +286% | 0.742 | 16.50% | -29.36% | 0.859 | 53.4% |
| 9 | **Quintile Momentum** | 10.30% | +165% | 0.427 | 26.87% | -52.21% | 0.511 | 50.3% |
| 10 | **GMVP** | 10.19% | +163% | 0.581 | 15.29% | -26.49% | 0.660 | 53.4% |
| 11 | **Quintile Low Vol** | 7.80% | +111% | 0.454 | **14.43%** | **-20.84%** | 0.563 | 47.8% |
| 12 | **CVaR Minimization** | 7.58% | +107% | 0.473 | 16.06% | -30.46% | 0.440 | 52.7% |

### Key Findings (10-Year Results)
- **Best Absolute Returns**: Mean Reversion (28.23% CAGR, 1,033% total)
- **Best Risk-Adjusted**: Max Decorrelation (1.052 Sharpe, 1.265 Sortino)
- **Lowest Risk**: Quintile Low Vol (14.43% volatility, -20.84% max DD)
- **Most Consistent**: Max Decorrelation (54.7% win rate)
- **Critical Factor**: Monthly rebalancing vs daily reduces costs by 95% and enables positive returns

---

## Note on Strategy Documentation

**⚠️ IMPORTANT**: This document contains detailed documentation for many strategies. However, only the **12 benchmark strategies listed above** have been fully validated and are production-ready in v3.0.0.

The sections below (strategies 1-12) document the 12 validated benchmark strategies. Additional strategy documentation (beyond strategy #12) represents historical development work or future planned strategies that are not currently validated.

For the current validated strategy list, see the table above or [VALIDATION_COMPLETE.md](../VALIDATION_COMPLETE.md).

---

## 1. Equal Weight

### Description
Allocates equal weight (1/N) to all assets. Simplest possible strategy, serves as baseline.

### Properties
- **Type:** Baseline
- **Complexity:** Very Low
- **Data Requirements:** Minimal
- **Turnover:** Low
- **Best For:** Benchmark, maximum diversification

### Parameters
None

### Usage
```python
from src.strategy_wrapper import EqualWeightStrategy
from src.portfolio_engine import PortfolioEngine

strategy = EqualWeightStrategy()

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
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
- No parameter tuning

❌ **Cons:**
- Ignores asset characteristics
- Treats all assets equally
- No risk management

### Research References
- DeMiguel et al. (2009) "Optimal versus naive diversification"

---

## 2. Buy and Hold

### Description
Initial equal-weight allocation, never rebalances. Pure buy-and-hold benchmark.

### Properties
- **Type:** Benchmark
- **Complexity:** Very Low
- **Data Requirements:** Minimal
- **Turnover:** Minimal (initial purchase only)
- **Best For:** Baseline comparison, cost-sensitive scenarios

### Parameters
None

### Usage
```python
from src.strategy_wrapper import BuyAndHoldStrategy

strategy = BuyAndHoldStrategy()

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='never'
)

result = engine.run_backtest()
```

### When to Use
- As a cost-aware benchmark
- Testing rebalancing vs drift
- Tax-efficient long-term investing

### Pros & Cons
✅ **Pros:**
- Zero rebalancing costs
- Tax efficient
- Captures market returns

❌ **Cons:**
- Portfolio drift
- No risk management
- Concentration risk over time

---

## 3. Momentum

### Description
Multi-period momentum strategy using cross-sectional ranking and Sharpe ratio optimization.

### Properties
- **Type:** Factor-based
- **Complexity:** Medium
- **Data Requirements:** 60+ days historical data
- **Turnover:** Medium
- **Best For:** Trending markets, medium-term horizons

### Parameters
- `lookback` (default: 60): Momentum calculation window
- `top_n` (default: None): Number of top momentum assets to hold
- `min_periods` (default: 20): Minimum data required

### Usage
```python
from src.strategy_wrapper import MomentumStrategy

strategy = MomentumStrategy(
    lookback=60,
    top_n=None  # None = use all assets with momentum weighting
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Calculates rolling returns over lookback period
- Ranks assets by momentum
- Uses Sharpe ratio optimization for weight allocation
- Includes 20-day warmup period
- Proper NaN handling for missing data

### When to Use
- Trending markets
- Medium-term trading (weeks to months)
- When markets show persistence

### Pros & Cons
✅ **Pros:**
- Well-documented factor
- Strong empirical performance
- Easy to understand

❌ **Cons:**
- Performs poorly in mean-reverting markets
- Can have large drawdowns in reversals
- Higher turnover

### Research References
- Jegadeesh and Titman (1993) "Returns to buying winners and selling losers"
- Asness et al. (2013) "Value and momentum everywhere"

---

## 4. Mean Reversion

### Description
Z-score based mean reversion with mean-variance optimization for position sizing.

### Properties
- **Type:** Statistical arbitrage
- **Complexity:** Medium
- **Data Requirements:** 20+ days historical data
- **Turnover:** High
- **Best For:** Range-bound markets, short-term trading

### Parameters
- `lookback` (default: 20): Mean reversion calculation window
- `entry_threshold` (default: 2.0): Z-score threshold for entry
- `exit_threshold` (default: 0.5): Z-score threshold for exit
- `risk_aversion` (default: 1.0): Risk penalty parameter

### Usage
```python
from src.strategy_wrapper import MeanReversionStrategy

strategy = MeanReversionStrategy(
    lookback=20,
    entry_threshold=2.0,
    exit_threshold=0.5,
    risk_aversion=1.0
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='daily',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Calculates rolling mean and standard deviation
- Z-score = (current_price - rolling_mean) / rolling_std
- Uses mean-variance optimization with risk penalty
- 10-day warmup period
- Date-specific calculation (uses only past data)

### When to Use
- Range-bound markets
- Short-term trading
- High-frequency rebalancing

### Pros & Cons
✅ **Pros:**
- Profits from price reversals
- Well-defined risk parameters
- Statistical foundation

❌ **Cons:**
- High turnover
- Fails in trending markets
- Sensitive to parameter choice

### Research References
- Gatev et al. (2006) "Pairs trading: Performance of a relative-value arbitrage rule"

---

## 5. Inverse Volatility

### Description
Risk parity approach weighting assets inversely proportional to their volatility.

### Properties
- **Type:** Risk-based
- **Complexity:** Low-Medium
- **Data Requirements:** 60+ days historical data
- **Turnover:** Low-Medium
- **Best For:** Balanced risk contribution

### Parameters
- `lookback` (default: 60): Volatility calculation window
- `min_periods` (default: 20): Minimum data required

### Usage
```python
from src.strategy_wrapper import InverseVolatilityStrategy

strategy = InverseVolatilityStrategy(
    lookback=60,
    min_periods=20
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Calculates rolling volatility (standard deviation of returns)
- Weights = 1 / volatility
- Normalizes to sum to 1.0
- Includes warmup period
- Date-specific calculation

### When to Use
- Seeking balanced risk exposure
- Volatile markets
- Long-term investing

### Pros & Cons
✅ **Pros:**
- Equal risk contribution
- Simple and intuitive
- Low turnover

❌ **Cons:**
- Ignores correlations
- May overweight low-return assets
- No expected return consideration

### Research References
- Maillard et al. (2010) "The properties of equally weighted risk contribution portfolios"

---

## 6. CVaR Minimization

### Description
Minimizes Conditional Value at Risk (CVaR), focusing on tail risk reduction.

### Properties
- **Type:** Risk-based
- **Complexity:** High
- **Data Requirements:** 60+ days historical data
- **Turnover:** Medium
- **Best For:** Risk-averse investors, downside protection

### Parameters
- `lookback` (default: 60): CVaR calculation window
- `confidence_level` (default: 0.95): CVaR confidence level (95%)
- `min_periods` (default: 30): Minimum data required

### Usage
```python
from src.strategy_wrapper import CVaRMinimizationStrategy

strategy = CVaRMinimizationStrategy(
    lookback=60,
    confidence_level=0.95,
    min_periods=30
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Uses CVXPY optimization framework
- Minimizes expected shortfall below VaR threshold
- Includes long-only constraints
- 30-day warmup period
- Robust error handling with fallback to equal weight

### When to Use
- Risk-averse portfolios
- Seeking downside protection
- Tail risk management

### Pros & Cons
✅ **Pros:**
- Focuses on tail risk
- Coherent risk measure
- Well-grounded in theory

❌ **Cons:**
- Computationally intensive
- May sacrifice upside
- Sensitive to outliers

### Research References
- Rockafellar and Uryasev (2000) "Optimization of conditional value-at-risk"

---

## 7. GMVP (Global Minimum Variance Portfolio)

### Description
Finds the portfolio with minimum variance using analytical solution.

### Properties
- **Type:** Risk-based
- **Complexity:** Medium
- **Data Requirements:** 60+ days historical data
- **Turnover:** Medium
- **Best For:** Conservative investors, stable returns

### Parameters
- `lookback` (default: 60): Covariance calculation window
- `min_periods` (default: 30): Minimum data required

### Usage
```python
from src.strategy_wrapper import GMVPStrategy

strategy = GMVPStrategy(
    lookback=60,
    min_periods=30
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Analytical solution: w = Σ^(-1) * 1 / (1^T * Σ^(-1) * 1)
- Uses Ledoit-Wolf covariance shrinkage
- Regularization for numerical stability
- 30-day warmup period

### When to Use
- Conservative investing
- Low volatility preference
- Market-neutral strategies

### Pros & Cons
✅ **Pros:**
- Stable returns
- Low volatility
- Analytical solution (fast)

❌ **Cons:**
- May underperform in bull markets
- Ignores expected returns
- Concentration risk

### Research References
- Markowitz (1952) "Portfolio selection"

---

## 8. Maximum Diversification

### Description
Maximizes diversification ratio (weighted average volatility / portfolio volatility).

### Properties
- **Type:** Risk-based
- **Complexity:** High
- **Data Requirements:** 60+ days historical data
- **Turnover:** Medium
- **Best For:** Maximizing diversification benefits

### Parameters
- `lookback` (default: 60): Statistics calculation window
- `min_periods` (default: 30): Minimum data required

### Usage
```python
from src.strategy_wrapper import MaximumDiversificationStrategy

strategy = MaximumDiversificationStrategy(
    lookback=60,
    min_periods=30
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Uses CVXPY optimization
- Objective: maximize Σ(w_i * σ_i) / σ_portfolio
- Includes long-only constraints
- Enhanced CCD algorithm for risk parity component

### When to Use
- Seeking maximum diversification
- Cross-asset allocation
- Low correlation environments

### Pros & Cons
✅ **Pros:**
- Maximizes diversification benefits
- Exploits correlation structure
- Strong theoretical foundation

❌ **Cons:**
- Computationally intensive
- May overweight volatile assets
- Sensitive to correlation estimates

### Research References
- Choueifaty and Coignard (2008) "Toward maximum diversification"

---

## 9. Maximum Decorrelation

### Description
Minimizes average pairwise correlation in the portfolio.

### Properties
- **Type:** Risk-based
- **Complexity:** High
- **Data Requirements:** 60+ days historical data
- **Turnover:** Medium
- **Best For:** Correlation-aware diversification

### Parameters
- `lookback` (default: 60): Correlation calculation window
- `min_periods` (default: 30): Minimum data required

### Usage
```python
from src.strategy_wrapper import MaximumDecorrelationStrategy

strategy = MaximumDecorrelationStrategy(
    lookback=60,
    min_periods=30
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Uses CVXPY optimization
- Objective: minimize w^T * Corr * w
- Includes long-only constraints
- Separate correlation calculation from covariance

### When to Use
- Correlation-driven diversification
- Crisis periods (decorrelation breaks down)
- Multi-asset portfolios

### Pros & Cons
✅ **Pros:**
- Focuses on correlation structure
- Crisis resilience potential
- Clear diversification goal

❌ **Cons:**
- Ignores volatility differences
- Computationally intensive
- May underweight high-return assets

---

## 10. Time Series Momentum

### Description
12-month time series momentum (absolute momentum, trend following).

### Properties
- **Type:** Trend following
- **Complexity:** Low
- **Data Requirements:** 252+ days historical data
- **Turnover:** Low
- **Best For:** Long-term trends, macro strategies

### Parameters
- `lookback` (default: 252): 12-month lookback period
- `min_periods` (default: 126): Minimum data required

### Usage
```python
from src.strategy_wrapper import TimeSeriesMomentumStrategy

strategy = TimeSeriesMomentumStrategy(
    lookback=252,
    min_periods=126
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='monthly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Simple 12-month return calculation
- Binary signal: positive momentum = full weight, negative = zero weight
- Normalizes weights to sum to 1.0
- 126-day warmup period

### When to Use
- Long-term trend following
- Macro strategies
- Risk-on/risk-off frameworks

### Pros & Cons
✅ **Pros:**
- Simple and robust
- Low turnover
- Strong empirical support

❌ **Cons:**
- Binary nature (all-or-nothing)
- Lagging indicator
- Whipsaw risk in ranging markets

### Research References
- Moskowitz et al. (2012) "Time series momentum"

---

## 11. Moving Average Crossover

### Description
50-day / 200-day moving average crossover system.

### Properties
- **Type:** Trend following
- **Complexity:** Low
- **Data Requirements:** 200+ days historical data
- **Turnover:** Low
- **Best For:** Long-term trend identification

### Parameters
- `short_window` (default: 50): Short MA period
- `long_window` (default: 200): Long MA period
- `min_periods` (default: 200): Minimum data required

### Usage
```python
from src.strategy_wrapper import MovingAverageCrossoverStrategy

strategy = MovingAverageCrossoverStrategy(
    short_window=50,
    long_window=200,
    min_periods=200
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='daily',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Calculates rolling means for short and long windows
- Signal: short_ma > long_ma = bullish, else bearish
- Binary allocation per asset
- 200-day warmup period

### When to Use
- Classic trend following
- Long-term investing
- Technical analysis enthusiasts

### Pros & Cons
✅ **Pros:**
- Very simple and intuitive
- Widely used and understood
- Low turnover

❌ **Cons:**
- Lagging indicator
- Whipsaw risk
- Binary signals (no partial positions)

### Research References
- Faber (2007) "A quantitative approach to tactical asset allocation"

---

## 12. Risk Parity

### Description
Allocates capital such that each asset contributes equally to total portfolio risk. Uses fast Cyclical Coordinate Descent algorithm for optimization.

### Properties
- **Type:** Risk-Based Optimization
- **Complexity:** Medium
- **Data Requirements:** 252+ days for covariance estimation
- **Turnover:** Low-Medium
- **Best For:** Balanced risk exposure, diversified portfolios

### Performance (10-Year Backtest)
- **CAGR**: 13.72%
- **Total Return**: +286%
- **Sharpe Ratio**: 0.742
- **Sortino Ratio**: 0.859
- **Max Drawdown**: -29.36%
- **Volatility**: 16.50%

### Parameters
- `lookback` (default: 252): Historical window for covariance estimation
- `max_weight` (default: 0.4): Maximum weight per asset (40%)
- `min_weight` (default: 0.0): Minimum weight per asset
- `target_risk` (default: None): Custom risk targets (default: equal 1/N)

### Usage
```python
from src.strategy_wrapper import RiskParityStrategy
from src.portfolio_engine import PortfolioEngine

strategy = RiskParityStrategy(
    lookback=252,
    max_weight=0.4,
    min_weight=0.0
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='monthly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Mathematical Formulation
```
Risk Contribution_i = w_i * (Σw)_i / σ_p

Objective: RC_i / Σ(RC_j) = 1/N for all assets i

Where:
- w_i = weight of asset i
- (Σw)_i = partial derivative of portfolio variance w.r.t. w_i
- σ_p = portfolio volatility
- RC_i = risk contribution of asset i
```

### Implementation Details
- Uses fast Cyclical Coordinate Descent algorithm
- Equalizes risk contributions across all assets
- Low-volatility assets receive higher allocations
- High-volatility assets receive lower allocations
- Iterative optimization with convergence criteria
- Handles degenerate covariance matrices

### When to Use
- Seeking balanced risk exposure
- Multi-asset class portfolios (stocks, bonds, commodities)
- Long-term strategic allocation
- Diversification-focused investing
- Alternative to 60/40 portfolio

### Pros & Cons
✅ **Pros:**
- More balanced than equal weight or market cap
- Low-volatility assets get proper allocation
- Performs well in balanced markets
- Intuitive risk-based framework
- Robust to outliers

❌ **Cons:**
- Ignores expected returns
- Can overweight low-volatility assets
- Sensitive to covariance estimation
- Moderate turnover during volatility regimes

### Research References
- Maillard, S., Roncalli, T., & Teïletche, J. (2010). "The properties of equally weighted risk contribution portfolios." *Journal of Portfolio Management*, 36(4), 60-70.
- Qian, E. (2011). "Risk parity and diversification." *Journal of Investing*, 20(1), 119-127.

---

## 13. Sharpe Maximization

### Description
Maximizes the Sharpe ratio (risk-adjusted returns) to find the tangency portfolio on the efficient frontier. This is the theoretically optimal portfolio for mean-variance investors.

### Properties
- **Type:** Risk-Adjusted Optimization
- **Complexity:** Medium-High
- **Data Requirements:** 252+ days for estimation
- **Turnover:** Medium-High
- **Best For:** Risk-adjusted return optimization, efficient frontier allocation

### Performance (10-Year Backtest)
- **CAGR**: 23.90%
- **Total Return**: +849%
- **Sharpe Ratio**: 0.810
- **Sortino Ratio**: 0.854
- **Max Drawdown**: -40.95%
- **Volatility**: 29.66%
- **Rank**: #3 by CAGR

### Parameters
- `lookback` (default: 252): Historical window for estimation
- `return_forecast_method` (default: 'historical'): Method to forecast returns
  - 'historical': Simple historical mean
  - 'momentum': Momentum-based forecast
  - 'capm': CAPM-based forecast
- `max_weight` (default: 0.3): Maximum weight per asset (30%)
- `min_weight` (default: 0.0): Minimum weight per asset

### Usage
```python
from src.strategy_wrapper import SharpeMaximizationStrategy
from src.portfolio_engine import PortfolioEngine

strategy = SharpeMaximizationStrategy(
    lookback=252,
    return_forecast_method='historical',
    max_weight=0.3,
    min_weight=0.0
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='monthly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Mathematical Formulation
```
maximize: (w^T μ - R_f) / sqrt(w^T Σ w)

subject to:
    Σw_i = 1           (fully invested)
    w_i ≥ 0            (long-only)
    w_i ≤ max_weight   (concentration limit)

Where:
- w = portfolio weights
- μ = expected returns vector
- R_f = risk-free rate
- Σ = covariance matrix
```

### Implementation Details
- Finds tangency portfolio on efficient frontier
- Optimal risk-adjusted returns by construction
- Uses historical or forecasted returns
- Scipy SLSQP optimization
- Proper handling of degenerate solutions
- Fallback to equal weights on optimization failure

### When to Use
- Seeking optimal risk-adjusted returns
- Mean-variance optimization framework
- When you have confident return forecasts
- Portfolio construction for Sharpe-focused investors
- Combining with other strategies in multi-strategy portfolio

### Pros & Cons
✅ **Pros:**
- Theoretically optimal risk-adjusted returns
- Tangency portfolio on efficient frontier
- Clear mathematical foundation
- Works well with good return forecasts
- High absolute returns (23.90% CAGR in 10-year test)

❌ **Cons:**
- Sensitive to return estimation error
- Higher volatility (29.66% in test)
- Moderate-high turnover
- Requires return forecasts (uncertain)
- Can concentrate in high-return estimates

### Research References
- Sharpe, W. F. (1966). "Mutual fund performance." *Journal of Business*, 39(1), 119-138.
- Markowitz, H. (1952). "Portfolio selection." *Journal of Finance*, 7(1), 77-91.

---

## 14. Linear Regression

### Description
Factor-based expected return estimation using linear regression on historical data.

### Properties
- **Type:** Factor-based / Statistical
- **Complexity:** Medium
- **Data Requirements:** 60+ days historical data
- **Turnover:** Medium
- **Best For:** Factor-driven allocation

### Parameters
- `lookback` (default: 60): Regression window
- `min_periods` (default: 30): Minimum data required

### Usage
```python
from src.strategy_wrapper import LinearRegressionStrategy

strategy = LinearRegressionStrategy(
    lookback=60,
    min_periods=30
)

engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    rebalance_frequency='weekly',
    transaction_cost_bps=10
)

result = engine.run_backtest()
```

### Implementation Details
- Fits linear regression model to historical returns
- Predicts next-period returns
- Uses Sharpe ratio optimization for allocation
- Proper NaN handling (v2.2.0 fix)
- 30-day warmup period

### When to Use
- Factor-based investing
- Predictive modeling
- Statistical arbitrage

### Pros & Cons
✅ **Pros:**
- Statistical foundation
- Adaptable to regime changes
- Factor-driven

❌ **Cons:**
- Model risk
- Overfitting potential
- Requires sufficient data

---

## 17. SVM Regime Classification Strategy

### Description
The **SVM Regime Classification Strategy** uses a Support Vector Machine (SVM) classifier to detect market regimes (Bull, Bear, or Sideways) and applies regime-specific trading strategies. This machine learning approach identifies market states based on 20+ technical features and dynamically adjusts portfolio weights based on the predicted regime.

### Properties
- **Type:** Machine Learning (Supervised Classification)
- **Complexity:** High
- **Data Requirements:** 252 days minimum (1 year) for training
- **Turnover:** Medium (~47%)
- **Computational Cost:** High (retraining overhead)
- **Best For:** All market conditions (adaptive regime-based strategies)

### How It Works
1. **Feature Engineering:** Extracts 20+ technical indicators including:
   - Trend: ADX, RSI, momentum, moving average distances
   - Volatility: Standard deviation, ATR, volatility regime
   - Market Structure: Breadth, correlation regime, price velocity
   - Statistical: Skewness, kurtosis, autocorrelation

2. **Regime Labeling:** Uses percentile-based labeling to classify historical periods:
   - **Bull Regime:** Top 33% of forward returns (aggressive momentum)
   - **Bear Regime:** Bottom 33% of forward returns (defensive positioning)
   - **Sideways Regime:** Middle 34% of returns (mean reversion)

3. **SVM Training:** Trains a Support Vector Classifier with RBF kernel on sampled historical data (every 5 days for efficiency)

4. **Regime Prediction:** Predicts current market regime using trained SVM model

5. **Weight Allocation:** Applies regime-specific strategies:
   - **Bull:** Pure momentum (long top performers)
   - **Bear:** Defensive (inverse volatility, avoid high-vol assets)
   - **Sideways:** Mean reversion (contrarian positioning)

### Parameters
```python
params = {
    'kernel': 'rbf',              # SVM kernel type (rbf, linear, poly)
    'C': 1.0,                      # Regularization parameter
    'gamma': 'scale',              # Kernel coefficient
    'retrain_frequency': 21,       # Days between model retraining (monthly)
    'lookback_window': 252,        # Historical data for training (1 year)
    'feature_lookback': 126,       # Feature calculation window (6 months)
    'regime_thresholds': {
        'bull': 0.67,              # Top 33% percentile
        'bear': 0.33               # Bottom 33% percentile
    },
    'bull_strategy': {
        'type': 'momentum',
        'n_top': 5,                # Number of assets to hold
        'equal_weight': True
    },
    'bear_strategy': {
        'type': 'inverse_volatility',
        'min_weight': 0.05,        # Minimum asset weight
        'max_weight': 0.30         # Maximum asset weight
    },
    'sideways_strategy': {
        'type': 'mean_reversion',
        'z_threshold': 1.5,        # Z-score threshold
        'lookback': 60             # Mean reversion window
    }
}
```

### Usage
```python
from src.backtester import BacktestEngine
from src.data_loader import DataLoader
from src.strategy_wrapper import create_strategy

# Load data
loader = DataLoader('data/processed')
start_date, end_date = '2019-01-01', '2024-01-01'
data = loader.load_data(start_date, end_date)

# Create strategy
strategy = create_strategy(
    'svm_regime',
    strategy_obj=loader.strategy,
    optimizer_obj=loader.optimizer,
    kernel='rbf',
    C=1.0,
    gamma='scale',
    retrain_frequency=21,  # Monthly retraining
    lookback_window=252,   # 1 year training data
    bull_n_top=5,          # Top 5 assets in bull regime
    bear_min_weight=0.05,  # Min 5% weight in bear regime
    sideways_z_threshold=1.5  # Z-score for mean reversion
)

# Run backtest
engine = BacktestEngine(data, strategy, rebalance_frequency='monthly')
result = engine.run_backtest(initial_capital=10000, transaction_cost=0.001)

# Access metrics
print(f"Total Return: {result.summary_metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {result.summary_metrics['sharpe_ratio']:.3f}")
print(f"Max Drawdown: {result.summary_metrics['max_drawdown']:.2%}")
print(f"Training Accuracy: {result.summary_metrics.get('avg_training_accuracy', 0):.2%}")

# Analyze regime detection
regime_counts = result.metadata.get('regime_distribution', {})
print(f"Regime Distribution: {regime_counts}")
```

### Implementation Details

#### Feature Engineering
The strategy uses `StrategySignalGenerator.extract_regime_features()` which calculates:
- **Trend Features:** ADX, momentum (1M, 3M, 6M), RSI, MA distances (20/50/200)
- **Volatility Features:** Realized volatility, ATR, volatility regime classification
- **Market Structure:** Breadth (% positive returns), correlation regime, trend slope
- **Statistical Features:** Price velocity, skewness, kurtosis, autocorrelation

#### Training Process
```python
# Simplified training logic
def _train_svm_model(self, prices, current_date):
    # Extract features for historical window
    features = self._extract_features(prices, self.lookback_window)
    
    # Generate regime labels (percentile-based)
    labels = self._generate_regime_labels(prices, forward_window=21)
    
    # Sample every 5 days for efficiency (5x speedup)
    train_features = features[::5]
    train_labels = labels[::5]
    
    # Standardize features
    scaled_features = self.scaler.fit_transform(train_features)
    
    # Train SVM
    self.model.fit(scaled_features, train_labels)
    
    return training_accuracy
```

#### Regime-Specific Weight Allocation
```python
def _get_regime_weights(self, prices, regime):
    if regime == 'bull':
        # Momentum: Long top 5 performers (6M momentum)
        momentum = prices.pct_change(126).iloc[-1]
        top_assets = momentum.nlargest(self.bull_n_top).index
        weights = pd.Series(1.0 / len(top_assets), index=top_assets)
        
    elif regime == 'bear':
        # Defensive: Inverse volatility, cap exposure
        volatility = prices.pct_change().std()
        inv_vol = 1.0 / volatility
        weights = inv_vol / inv_vol.sum()
        weights = weights.clip(self.bear_min_weight, self.bear_max_weight)
        weights = weights / weights.sum()
        
    elif regime == 'sideways':
        # Mean reversion: Contrarian on z-scores
        returns = prices.pct_change(self.sideways_lookback)
        z_scores = (returns.iloc[-1] - returns.mean()) / returns.std()
        # Invert z-scores: buy oversold, sell overbought
        contrarian_scores = -z_scores
        # Filter by threshold
        signals = contrarian_scores[abs(z_scores) > self.sideways_z_threshold]
        if len(signals) > 0:
            weights = (signals - signals.min()) / (signals.max() - signals.min())
            weights = weights / weights.sum()
        else:
            weights = pd.Series(1.0 / len(prices.columns), index=prices.columns)
    
    return weights
```

### When to Use
- **Adaptive Markets:** When market conditions shift between trending and mean-reverting
- **Multi-Regime Environments:** Bull/bear/sideways cycles with distinct characteristics
- **Medium-Term Trading:** Monthly rebalancing with regime persistence
- **Feature-Rich Datasets:** Assets with sufficient history for feature extraction
- **Computational Resources Available:** Can handle retraining overhead

### Pros
✅ **Pros:**
- Adaptive to market regime changes
- Feature-rich classification (20+ indicators)
- Regime-specific strategy application
- Balanced training classes (percentile-based)
- High training accuracy (68-90%)
- Risk-aware defensive positioning
- Combines momentum, mean reversion, and risk parity

### Cons
❌ **Cons:**
- High computational cost (retraining overhead)
- Overfitting risk with high-dimensional features
- Regime detection lag (1-2 rebalancing periods)
- Parameter sensitivity (C, gamma require tuning)
- Requires 252+ days of training data
- Medium turnover (~47%) increases transaction costs
- Black box decision boundaries

### Performance (5-Year Backtest: 2019-2024)
```
Total Return:        +105.15%
Annualized Return:   +15.44%
Sharpe Ratio:        0.782
Max Drawdown:        -26.75%
Turnover:            46.88%
Training Accuracy:   68-90% (varies by period)

Regime Distribution:
- Sideways: ~55%
- Bull:     ~35%
- Bear:     ~10%

Comparison to Benchmarks:
- vs. Buy & Hold (+862%):      Lower return but better risk-adjusted
- vs. Pure Momentum (0.805):   Comparable Sharpe with regime adaptation
- vs. Equal Weight (+862%):    Lower return, moderate Sharpe
- vs. Mean Reversion (0.327):  Superior Sharpe, less volatility
```

### Research References
1. **Nystrup et al. (2016)** - "Multi-period portfolio selection with drawdown control"
2. **Kritzman et al. (2012)** - "Regime Shifts: Implications for Dynamic Strategies"
3. **Ang & Bekaert (2004)** - "How Regimes Affect Asset Allocation"
4. **Cortes & Vapnik (1995)** - "Support-Vector Networks" (Original SVM paper)
5. **Chang & Lin (2011)** - "LIBSVM: A library for support vector machines"
6. **Hsu et al. (2003)** - "A Practical Guide to Support Vector Classification"

### Tips for Optimization
1. **Hyperparameter Tuning:**
   ```python
   from sklearn.model_selection import GridSearchCV
   param_grid = {
       'C': [0.1, 1.0, 10.0],
       'gamma': ['scale', 'auto', 0.001, 0.01],
       'kernel': ['rbf', 'poly', 'linear']
   }
   grid_search = GridSearchCV(SVC(), param_grid, cv=5)
   ```

2. **Feature Selection:**
   - Use correlation analysis to remove redundant features
   - Apply PCA for dimensionality reduction
   - Test feature importance with permutation importance

3. **Regime Threshold Tuning:**
   - Experiment with asymmetric thresholds (e.g., 70/30 instead of 67/33)
   - Use volatility-adjusted returns for labeling
   - Consider multi-timeframe regime detection

4. **Retraining Frequency:**
   - Daily: High accuracy, high computational cost
   - Weekly: Balanced trade-off
   - Monthly: Lower cost, may miss regime shifts

5. **Ensemble Approach:**
   - Combine SVM with other classifiers (Random Forest, XGBoost)
   - Use voting or probability averaging for regime prediction
   - Reduce variance in regime detection

---

## Strategy Comparison Matrix

| Strategy | Turnover | Complexity | Data Needs | Best Market | Sharpe (5y) | Total Return (5y) |
|----------|----------|------------|------------|-------------|-------------|-------------------|
| Equal Weight | Low | Very Low | Minimal | All | 2.25 | +862% |
| Buy and Hold | Minimal | Very Low | Minimal | Bull | 2.25 | +862% |
| Max Diversification | Medium | High | 60d | Diversified | 2.21 | +1091% |
| Momentum | Medium | Medium | 60d | Trending | 1.60 | +107% |
| CVaR Min | Medium | High | 60d | Risk-off | 1.57 | +143% |
| GMVP | Medium | Medium | 60d | Stable | 1.28 | +88% |
| Inverse Volatility | Low | Low-Med | 60d | Volatile | 1.16 | +228% |
| **SVM Regime** | **Medium** | **High** | **252d** | **Adaptive** | **0.782** | **+105%** |
| Mean Reversion | High | Medium | 20d | Range-bound | 0.52 | +2905% |
| MA Crossover | Low | Low | 200d | Long trends | 0.46 | +499% |
| Time Series Mom | Medium | Low | 252d | Macro trends | 0.24 | +25% |
| GMRP | High | High | 60d | Risk parity | 0.12 | +1389% |
| Markowitz MVO | High | High | 60d | Factor-driven | 0.09 | +198% |

**Note:** Sharpe ratios and returns from 5-year backtest (2019-2024) with 10 bps transaction costs.

---

## Combining Strategies

### Ensemble Approach
Combine multiple strategies for robustness:

```python
# Define strategy allocations
strategies = {
    'Equal Weight': (EqualWeightStrategy(), 0.20),
    'Momentum': (MomentumStrategy(lookback=60), 0.30),
    'Mean Reversion': (MeanReversionStrategy(lookback=20), 0.20),
    'GMVP': (GMVPStrategy(lookback=60), 0.30)
}

# Run each strategy
results = {}
for name, (strategy, weight) in strategies.items():
    engine = PortfolioEngine(prices, strategy)
    results[name] = engine.run_backtest()

# Combine equity curves with weights
combined_equity = sum(
    results[name].equity_history * weight 
    for name, (_, weight) in strategies.items()
)
```

### Regime-Dependent Allocation
Switch strategies based on market regime:

```python
# Calculate market volatility
volatility = prices.pct_change().std()

# Choose strategy based on regime
if volatility > threshold:
    strategy = MeanReversionStrategy()  # High vol
else:
    strategy = MomentumStrategy()  # Low vol
```

---

## Parameter Tuning Best Practices

### 1. Use Walk-Forward Optimization
- Train on historical data
- Test on out-of-sample period
- Re-optimize periodically

### 2. Avoid Overfitting
- Use simple strategies
- Limit parameter count
- Test on multiple time periods

### 3. Consider Transaction Costs
- Higher turnover = higher costs
- Optimize for net returns
- Use realistic cost assumptions (10 bps is standard)

### 4. Validate Robustness
- Test on different asset universes
- Vary time periods
- Use Monte Carlo simulation

### 5. Monitor Performance
- Track out-of-sample metrics
- Compare to benchmarks
- Rebalance/retrain as needed

---

## Conclusion

The 25 production-ready strategies provide a comprehensive toolkit for portfolio allocation:

- **Baseline:** Equal Weight, Buy and Hold
- **Trend:** Momentum, Time Series Momentum, MA Crossover
- **Mean Reversion:** Mean Reversion
- **Risk-Based:** Inverse Volatility, GMVP, GMRP, CVaR Min, Risk Parity, Max Diversification, Max Decorrelation
- **Risk-Adjusted:** Sharpe Maximization
- **Factor & ML:** Linear Regression, Multi-Factor ML, ML Random Forest, ML Gradient Boosting, SVM Regime Classification
- **Advanced:** Regime Switching, ARMA Forecast, ARIMA-GARCH, Quintile Factor (Momentum, Low Vol), Markowitz MVO

**All strategies are implemented in `src/strategy_wrapper.py`** and can be accessed via the factory function:

```python
from src.strategy_wrapper import list_available_strategies, create_strategy

# List all available strategies
available = list_available_strategies()
print(available.keys())

# Create strategy instances
strategy = create_strategy('momentum', strategy_obj, optimizer_obj, lookback=60)
strategy = create_strategy('svm_regime', strategy_obj, optimizer_obj, retrain_frequency=21)
```

All strategies have been validated with:
✅ Transaction cost modeling (10 bps)
✅ Proper warmup periods
✅ NaN handling
✅ Date-specific calculations
✅ 5-year backtests (2019-2024)
✅ Realistic slippage modeling

**Top Performing Strategies (10-Year Backtest, 2015-2025):**

By **Sharpe Ratio** (Risk-Adjusted Returns):
1. **Max Decorrelation: 1.052** (24.44% CAGR)
2. **Mean Reversion: 0.968** (28.23% CAGR)
3. Buy & Hold: 0.904 (17.25% CAGR)
4. Max Diversification: 0.890 (16.57% CAGR)
5. Equal Weight: 0.826 (17.25% CAGR)

By **Sortino Ratio** (Downside Risk-Adjusted):
1. **Max Decorrelation: 1.265** 
2. **Mean Reversion: 1.101**
3. Max Diversification: 1.040
4. Buy & Hold: 0.976
5. Equal Weight: 0.976

By **Total Return** (CAGR):
1. **Mean Reversion: 28.23%** (+1033% total)
2. **Max Decorrelation: 24.44%** (+883% total)
3. **Sharpe Maximization: 23.90%** (+849% total)
4. Buy & Hold: 17.25% (+389% total)
5. Equal Weight: 17.25% (+389% total)

By **Lowest Risk** (Volatility & Drawdown):
1. **Quintile Low Vol: 14.43% vol, -20.84% DD**
2. GMVP: 15.29% vol, -26.49% DD
3. CVaR Minimization: 16.06% vol, -30.46% DD
4. Risk Parity: 16.50% vol, -29.36% DD
5. Inverse Volatility: 16.19% vol, -28.59% DD

Choose strategies based on:
- **Market conditions** (trending vs mean-reverting vs adaptive)
- **Risk tolerance** (conservative vs aggressive)
- **Investment horizon** (short-term vs long-term)
- **Transaction cost sensitivity** (turnover)
- **Computational resources** (simple vs complex ML models)
- **Drawdown tolerance** (some strategies have extreme drawdowns)

For best results, consider ensemble approaches combining multiple strategies with complementary characteristics.

---

## Recent Updates (v4.0 - December 2025)

### New Strategies Added
1. **Risk Parity** - Equal risk contribution optimization (13.72% CAGR, 0.742 Sharpe)
2. **Sharpe Maximization** - Tangency portfolio optimization (23.90% CAGR, 0.810 Sharpe)
3. **Quintile Low Volatility** - Defensive low-volatility factor strategy (7.80% CAGR, lowest risk)

### Enhanced Testing
- **10-Year Full Backtests**: All strategies validated over 2015-2025 period
- **Monthly Rebalancing**: Realistic frequency (121 rebalances vs 2,514 daily)
- **Transaction Cost Analysis**: Comprehensive cost modeling prevents negative returns
- **Scipy Optimization Fixes**: Added error handling and iteration limits for robust optimization
- **Virtual Environment Support**: Proper environment isolation for reproducible results

### Key Insights from 10-Year Testing
- **Mean Reversion** dominated absolute returns (28.23% CAGR, +1033%)
- **Max Decorrelation** achieved best risk-adjusted returns (1.052 Sharpe, 1.265 Sortino)
- **Rebalancing Frequency Critical**: Monthly vs daily rebalancing = 10× improvement in returns
- **Advanced Optimization Works**: Max Decorrelation, Sharpe Max, Risk Parity outperformed simple strategies
- **Low Volatility Effective**: Quintile Low Vol had smallest drawdown (-20.84%) and lowest volatility (14.43%)

### Documentation Improvements
- Complete performance tables with 10-year results
- Detailed parameter descriptions for Risk Parity and Sharpe Maximization
- Mathematical formulations and research references
- Usage examples with PortfolioEngine integration
- Transaction cost analysis and rebalancing best practices

For full demo scripts and reproducible results, see:
- `examples/demo_12_strategies_fast.py` (6-month quick validation)
- `examples/demo_12_strategies_full.py` (10-year comprehensive backtest)
- `FULL_DEMO_RESULTS.md` (detailed analysis)
- `TRANSACTION_COST_ANALYSIS.md` (rebalancing frequency impact)
