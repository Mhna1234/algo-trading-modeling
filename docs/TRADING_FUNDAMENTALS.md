# Trading Fundamentals Guide

A comprehensive guide to algorithmic trading concepts, strategies, optimization methods, and performance metrics.

---

## Table of Contents

1. [Introduction to Algorithmic Trading](#introduction-to-algorithmic-trading)
2. [Trading Strategies Explained](#trading-strategies-explained)
3. [Portfolio Optimization Methods](#portfolio-optimization-methods)
4. [Performance Metrics and Their Importance](#performance-metrics-and-their-importance)
5. [Risk Management](#risk-management)
6. [Practical Considerations](#practical-considerations)

---

## Introduction to Algorithmic Trading

### What is Algorithmic Trading?

Algorithmic trading uses computer programs to execute trading decisions based on predefined rules and mathematical models. Instead of manual decision-making, algorithms analyze market data, identify opportunities, and automatically execute trades.

**Key Advantages:**
- **Speed**: Execute trades in milliseconds
- **Consistency**: Remove emotional bias from trading decisions
- **Backtesting**: Test strategies on historical data before risking capital
- **Diversification**: Manage multiple strategies and assets simultaneously
- **Precision**: Execute complex strategies that would be difficult manually

**Key Challenges:**
- **Overfitting**: Strategies that work perfectly on historical data may fail in live trading
- **Market Changes**: Markets evolve, and strategies may become less effective over time
- **Transaction Costs**: Frequent trading can erode profits through commissions and slippage
- **Technology Risk**: System failures, data errors, or connectivity issues

### The Algorithmic Trading Process

```
1. DATA COLLECTION
   ↓
2. SIGNAL GENERATION (Strategy identifies opportunities)
   ↓
3. PORTFOLIO CONSTRUCTION (Optimization determines position sizes)
   ↓
4. EXECUTION (Orders placed in market)
   ↓
5. MONITORING & REBALANCING (Track performance, adjust positions)
   ↓
6. EVALUATION (Measure results, refine strategies)
```

---

## Trading Strategies Explained

### 1. **Momentum Trading** 🚀

**Core Concept**: "What goes up tends to keep going up" (at least for a while)

Momentum strategies buy assets that have performed well recently and sell (or avoid) assets that have performed poorly. This exploits the tendency of price trends to persist in the short to medium term.

**How It Works:**
1. Calculate recent returns (e.g., past 3, 6, or 12 months)
2. Rank assets by performance
3. Buy top performers, avoid or short bottom performers
4. Rebalance periodically (monthly or quarterly)

**Why It Works:**
- **Behavioral Finance**: Investors underreact to news, causing trends to persist
- **Herding**: Momentum attracts more investors, reinforcing the trend
- **Information Diffusion**: News spreads gradually, not instantly

**Best Used When:**
- ✅ Markets are trending (bull or bear markets)
- ✅ There's strong directional price movement
- ✅ Asset correlations are low to moderate

**Risks:**
- ❌ Momentum crashes: Sudden reversals can cause large losses
- ❌ High turnover = high transaction costs
- ❌ Poor performance in range-bound or mean-reverting markets

**Example**: If Stock A rose 15% in the past 6 months while Stock B fell 5%, momentum strategy buys more of Stock A and less (or none) of Stock B.

---

### 2. **Mean Reversion Trading** 🔄

**Core Concept**: "What goes up must come down" (and vice versa)

Mean reversion strategies bet on price movements reversing to their historical average. When prices deviate significantly from the mean, the strategy expects them to "snap back."

**How It Works:**
1. Calculate statistical measures (moving average, z-score)
2. Identify assets trading far from their mean
3. Buy underperformers (oversold), sell outperformers (overbought)
4. Hold until prices revert to mean

**Why It Works:**
- **Overreaction**: Markets often overreact to news, creating opportunities
- **Statistical Properties**: Many financial series exhibit mean reversion
- **Market Making**: Provides liquidity to panicked or exuberant traders

**Best Used When:**
- ✅ Markets are range-bound or sideways
- ✅ High volatility creates price extremes
- ✅ Short-term trading horizons (days to weeks)

**Risks:**
- ❌ "Catching a falling knife": Prices may continue falling
- ❌ Very high turnover and transaction costs
- ❌ Fails in strong trending markets

**Example**: If Stock A normally trades around $100 but suddenly drops to $85 on no fundamental news, mean reversion strategy buys expecting a bounce back toward $100.

---

### 3. **Risk Parity / Inverse Volatility** ⚖️

**Core Concept**: "Allocate capital based on risk, not dollar amounts"

Risk parity strategies allocate more capital to low-volatility assets and less to high-volatility assets, ensuring each asset contributes equally to portfolio risk.

**How It Works:**
1. Measure each asset's volatility (standard deviation of returns)
2. Calculate weights inversely proportional to volatility
3. Low volatility = Higher weight
4. High volatility = Lower weight

**Formula:**
```
Weight_i = (1 / Volatility_i) / Σ(1 / Volatility_j)
```

**Why It Works:**
- **Risk Balance**: Prevents volatile assets from dominating portfolio risk
- **Diversification**: Naturally spreads risk across all positions
- **Lower Drawdowns**: Less exposure to high-risk assets during crashes

**Best Used When:**
- ✅ Building defensive, low-drawdown portfolios
- ✅ You have no strong views on expected returns
- ✅ You want consistent risk exposure over time

**Risks:**
- ❌ Ignores expected returns (may underweight high-return assets)
- ❌ Can underperform in strong bull markets
- ❌ Volatility estimates can be unstable

**Example**: Bond volatility = 5%, Stock volatility = 20%. Risk parity allocates 4x more capital to bonds than stocks to equalize risk contribution.

---

### 4. **Regime Switching** 🔀

**Core Concept**: "Different strategies work in different market conditions"

Regime switching strategies detect the current market environment (bull, bear, high volatility, low volatility) and adapt the trading approach accordingly.

**How It Works:**
1. Define market regimes (e.g., based on volatility, trend strength)
2. Use statistical methods to identify current regime
3. Apply appropriate strategy for that regime
4. Switch strategies when regime changes

**Common Regimes:**
- **Bull Market**: High momentum strategy
- **Bear Market**: Defensive or short positions
- **High Volatility**: Mean reversion or risk parity
- **Low Volatility**: Leverage or aggressive growth

**Why It Works:**
- **Adaptability**: No single strategy works in all conditions
- **Risk Management**: Reduce exposure during dangerous periods
- **Enhanced Returns**: Exploit unique opportunities in each regime

**Best Used When:**
- ✅ Markets exhibit distinct phases
- ✅ You can identify regime changes with reasonable accuracy
- ✅ You want dynamic risk management

**Risks:**
- ❌ Regime detection lag: May miss the start of regime changes
- ❌ Complexity: More moving parts = more potential failures
- ❌ False signals: Mistakenly switching strategies

**Example**: When market volatility spikes above 25%, switch from momentum (12-month) to mean reversion (5-day) strategy.

---

### 5. **Machine Learning Strategies** 🤖

**Core Concept**: "Let algorithms learn patterns from data"

ML strategies use advanced statistical techniques (Random Forests, Gradient Boosting, Neural Networks) to predict future returns based on multiple features.

**How It Works:**
1. Engineer features (momentum, volatility, technical indicators)
2. Train ML model on historical data
3. Model learns complex, non-linear relationships
4. Generate predictions for future returns
5. Construct portfolio based on predictions

**Common ML Approaches:**
- **Random Forests**: Ensemble of decision trees
- **Gradient Boosting**: Sequential error correction
- **Neural Networks**: Deep learning for complex patterns
- **Support Vector Machines**: Non-linear classification

**Why It Works (When It Does):**
- **Non-linearity**: Captures complex patterns traditional models miss
- **Feature Interaction**: Automatically discovers relationships between variables
- **Adaptability**: Can learn from new data

**Best Used When:**
- ✅ You have large amounts of quality data
- ✅ Relationships are non-linear and complex
- ✅ You have strong ML expertise
- ✅ You can avoid overfitting

**Risks:**
- ❌ **Overfitting**: Models memorize noise instead of signal
- ❌ **Data Snooping**: Testing too many models leads to false discoveries
- ❌ **Computational Cost**: Slow training and prediction
- ❌ **Black Box**: Difficult to interpret and debug

**Example**: Random Forest trained on 50 features (momentum, RSI, volume, correlations) predicts next month's return for each stock. Buy top 10 predicted performers.

---

## Portfolio Optimization Methods

Portfolio optimization determines how much capital to allocate to each asset to achieve specific objectives (maximize return, minimize risk, balance both).

### 1. **Mean-Variance Optimization (MVO)** 📊

**Goal**: Maximize expected return for a given level of risk (or minimize risk for a given return target)

**Mathematical Framework:**

The classic Markowitz optimization:

```
Minimize: w^T Σ w  (portfolio variance)
Subject to: w^T μ ≥ target_return
            Σw_i = 1  (fully invested)
            w_i ≥ 0   (no short selling)
```

Where:
- **w** = portfolio weights
- **Σ** = covariance matrix (asset risk relationships)
- **μ** = expected returns vector

**Key Parameters:**
- **Risk Aversion (λ)**: How much you care about risk vs return
  - High λ → Very conservative (low risk, low return)
  - Low λ → Aggressive (higher risk, higher return)

**Advantages:**
- ✅ Well-established theory (Nobel Prize-winning)
- ✅ Explicitly balances risk and return
- ✅ Incorporates asset correlations

**Limitations:**
- ❌ Sensitive to input estimates (garbage in, garbage out)
- ❌ Assumes returns are normally distributed
- ❌ Can produce extreme, concentrated positions

**When to Use:**
- You have reasonable estimates of expected returns
- You want to explicitly control risk-return tradeoff
- Your assets have meaningful correlations

---

### 2. **Sharpe Ratio Maximization** 📈

**Goal**: Maximize risk-adjusted returns (return per unit of risk)

**Formula:**
```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility

Maximize: (w^T μ - r_f) / √(w^T Σ w)
```

**Why It's Important:**
- Identifies the "best bang for your buck" in risk-taking
- Balances greed (high returns) with prudence (low volatility)
- Most widely used risk-adjusted performance metric

**Optimal Sharpe Portfolio:**
The portfolio that sits on the "efficient frontier" with the steepest slope from the risk-free rate.

**Advantages:**
- ✅ Single objective (simpler than MVO with constraints)
- ✅ Risk-adjusted (accounts for volatility)
- ✅ Comparable across strategies

**Limitations:**
- ❌ Assumes normal returns distribution
- ❌ Doesn't distinguish between upside and downside volatility
- ❌ Can be manipulated by infrequent trading

**When to Use:**
- You want maximum risk-adjusted returns
- You're comparing multiple strategies
- You don't have specific return or risk targets

---

### 3. **Risk Parity Optimization** ⚖️

**Goal**: Equalize risk contribution from each asset

**Concept**: Traditional market-cap weighting gives 80-90% of risk to equities. Risk parity spreads risk evenly.

**Mathematical Formulation:**
```
For each asset i, Risk Contribution = w_i * (Σw)_i

Optimize: Make all risk contributions equal
```

**Example:**
- Stocks: 60% allocation, 15% volatility → 9% risk contribution
- Bonds: 40% allocation, 5% volatility → 2% risk contribution

Risk parity would increase bond allocation to equalize contributions.

**Advantages:**
- ✅ Diversified risk (no single asset dominates)
- ✅ Lower portfolio volatility
- ✅ Better performance during market stress
- ✅ Doesn't require return forecasts

**Limitations:**
- ❌ May underweight high-return assets
- ❌ Requires leverage to achieve equity-like returns
- ❌ Still sensitive to correlation estimates

**When to Use:**
- You want defensive, low-drawdown portfolios
- You don't have strong return forecasts
- You have access to leverage (if needed)
- You want consistent risk exposure

---

### 4. **CVaR Minimization** 📉

**Goal**: Minimize tail risk (protect against worst-case scenarios)

**Conditional Value at Risk (CVaR)**: Average loss in the worst α% of cases

**Example:**
- 95% CVaR = Average return in worst 5% of scenarios
- If 95% CVaR = -8%, you expect to lose 8% on average during the worst 5% of days

**Mathematical Framework:**
```
Minimize: CVaR_α(w^T r)

This protects against left-tail events (crashes, large losses)
```

**Why It Matters:**
- Standard deviation treats upside and downside volatility equally
- CVaR focuses specifically on downside risk
- More aligned with investor concerns (losses hurt more than gains feel good)

**Advantages:**
- ✅ Tail risk focus (protect against crashes)
- ✅ More realistic than normal distribution assumptions
- ✅ Coherent risk measure (mathematically well-behaved)

**Limitations:**
- ❌ Computationally intensive
- ❌ Requires many historical scenarios
- ❌ May sacrifice upside to avoid downside

**When to Use:**
- You're very risk-averse (preservation of capital)
- After market crashes (avoid repeat damage)
- Managing institutional money with strict loss limits
- Trading illiquid assets (can't easily exit losers)

---

### 5. **Black-Litterman Model** 🎯

**Goal**: Combine market equilibrium with your personal views

**The Problem It Solves:**
Pure MVO is unstable—small changes in return estimates cause huge portfolio shifts. Black-Litterman provides a stable framework.

**How It Works:**
1. Start with market equilibrium (market cap weights)
2. Express your views (e.g., "I think Tech will outperform by 5%")
3. Specify confidence in each view
4. Model blends equilibrium + views → stable expected returns
5. Use these returns in MVO

**Formula:**
```
E[R] = [(τΣ)^-1 + P^T Ω^-1 P]^-1 [(τΣ)^-1 Π + P^T Ω^-1 Q]
```

Where:
- Π = Equilibrium returns (implied by market)
- P = Matrix linking views to assets
- Q = Your view on expected returns
- Ω = Uncertainty in your views

**Advantages:**
- ✅ Stable portfolios (less extreme positions)
- ✅ Incorporates market wisdom
- ✅ Allows subjective views with confidence levels
- ✅ Theoretically sound

**Limitations:**
- ❌ Complex to implement correctly
- ❌ Requires specifying view confidence (subjective)
- ❌ Still depends on covariance estimates

**When to Use:**
- You have specific market views but want stability
- You manage portfolios professionally
- You want to deviate from benchmarks systematically

---

## Performance Metrics and Their Importance

Understanding metrics is crucial for evaluating trading strategies objectively.

### 1. **Total Return** 💰

**Definition**: Percentage gain/loss from start to end of period

```
Total Return = (Ending Value - Starting Value) / Starting Value
```

**Example**: $100,000 → $125,000 = 25% total return

**Why It Matters:**
- Most intuitive measure of success
- Shows absolute profit/loss

**Limitations:**
- Ignores time (25% in 1 year ≠ 25% in 10 years)
- Ignores risk (volatile path vs smooth path)
- Can't compare strategies with different timeframes

**What's Good:**
- **Positive**: Better than cash
- **> Benchmark**: Beating the market
- **> Risk-free rate + premium**: Compensated for risk

---

### 2. **Annualized Return** 📅

**Definition**: Geometric average return per year

```
Annualized Return = (Ending Value / Starting Value)^(1/Years) - 1
```

**Example**: 46% over 2 years → (1.46)^(1/2) - 1 = 20.1% annualized

**Why It Matters:**
- Standardizes returns across different time periods
- Enables apples-to-apples comparison
- Shows sustainable growth rate

**What's Good:**
- **5-7%**: Modest, bond-like returns
- **8-12%**: Good, market-like returns
- **15%+**: Excellent (but verify risk)
- **25%+**: Exceptional (likely high risk or unsustainable)

---

### 3. **Volatility (Standard Deviation)** 📊

**Definition**: Measure of return variability

```
Volatility = √(Σ(r_i - μ)² / (n-1))

Annualized Volatility = Daily Volatility × √252
```

**Why It Matters:**
- Quantifies risk and uncertainty
- Predicts range of future outcomes
- Key input to portfolio optimization

**Interpretation:**
- **68% of returns** fall within ±1 standard deviation
- **95% of returns** fall within ±2 standard deviations

**Example**: 15% annual volatility means:
- 68% of years: Return between -5% and +25% (assuming 10% mean)
- 95% of years: Return between -20% and +40%

**What's Good:**
- **< 10%**: Low volatility (bonds, defensive stocks)
- **10-20%**: Moderate (diversified equity portfolios)
- **20-30%**: High (aggressive stocks, commodities)
- **> 30%**: Very high (options, leveraged products)

---

### 4. **Sharpe Ratio** ⭐

**Definition**: Risk-adjusted return (reward per unit of risk)

```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility
```

**Example**:
- Portfolio: 12% return, 15% volatility
- Risk-free rate: 2%
- Sharpe = (12% - 2%) / 15% = 0.67

**Why It Matters:**
- **THE** most important metric for comparing strategies
- Balances greed with prudence
- Answers: "Am I getting paid enough for the risk I'm taking?"

**Interpretation:**
- **< 0**: Losing money (worse than risk-free rate)
- **0 - 0.5**: Poor (not enough return for risk)
- **0.5 - 1.0**: Acceptable (typical for most strategies)
- **1.0 - 2.0**: Good (skilled trading)
- **2.0 - 3.0**: Excellent (very skilled or lucky)
- **> 3.0**: Exceptional (verify data—too good to be true?)

**Industry Benchmarks:**
- S&P 500: ~0.4-0.5 long-term
- Hedge funds: Target 1.0+
- Quant strategies: 1.5-2.5 is excellent

---

### 5. **Sortino Ratio** 📉

**Definition**: Risk-adjusted return using only downside volatility

```
Sortino Ratio = (Portfolio Return - Risk-Free Rate) / Downside Deviation
```

**Downside Deviation**: Only counts negative returns (below target)

**Why It Matters:**
- Better than Sharpe for asymmetric strategies
- Investors care more about downside than upside volatility
- Doesn't penalize upside volatility

**When Sortino > Sharpe:**
- Strategy has positive skew (small losses, big wins)
- Limited downside risk with unlimited upside

**What's Good:**
- Similar scale to Sharpe, but typically higher
- **> 1.0**: Good
- **> 2.0**: Excellent

---

### 6. **Maximum Drawdown** 🔻

**Definition**: Largest peak-to-trough decline

```
Max Drawdown = (Trough Value - Peak Value) / Peak Value
```

**Example**: Portfolio grows from $100k → $150k → $120k
- Peak: $150k
- Trough: $120k  
- Max DD: ($120k - $150k) / $150k = -20%

**Why It Matters:**
- **Psychological impact**: Can you stomach a 30% loss?
- **Ruin risk**: Deep drawdowns may force liquidation
- **Recovery difficulty**: -50% loss requires +100% gain to recover

**What's Tolerable:**
- **< 10%**: Conservative, low-risk
- **10-20%**: Moderate (typical balanced portfolio)
- **20-30%**: Aggressive (equity-heavy)
- **> 30%**: Very aggressive (hard to stomach psychologically)

**S&P 500 Historical Max Drawdowns:**
- 2000-2002: -49%
- 2008: -57%
- 2020 COVID: -34%

---

### 7. **Calmar Ratio** 🎯

**Definition**: Return per unit of maximum drawdown

```
Calmar Ratio = Annualized Return / |Maximum Drawdown|
```

**Example**:
- 15% annual return
- -20% max drawdown
- Calmar = 15% / 20% = 0.75

**Why It Matters:**
- Focuses on worst-case risk (not just volatility)
- Popular with hedge funds and CTAs
- Rewards strategies that limit drawdowns

**What's Good:**
- **< 0.5**: Poor drawdown control
- **0.5 - 1.0**: Acceptable
- **1.0 - 2.0**: Good
- **> 2.0**: Excellent (rare)

---

### 8. **Win Rate** 🎲

**Definition**: Percentage of profitable trades/periods

```
Win Rate = (Number of Winning Periods) / (Total Periods)
```

**Why It Matters:**
- Shows consistency
- Indicates strategy's batting average

**Interpretation:**
- **< 40%**: Low win rate (needs big wins to offset)
- **40-50%**: Typical for momentum strategies
- **50-60%**: Good, better than coin flip
- **> 60%**: High (mean reversion, market making)

**Important Note:**
Win rate alone is meaningless! A 90% win rate with small gains and 10% huge losses is terrible.

**Better Metric: Profit Factor**
```
Profit Factor = Sum(Winning Trades) / Sum(Losing Trades)
```

- **< 1.0**: Losing strategy
- **1.0 - 1.5**: Barely profitable
- **1.5 - 2.0**: Good
- **> 2.0**: Excellent

---

### 9. **Value at Risk (VaR)** 📊

**Definition**: Maximum expected loss at a given confidence level

**Example**: 95% 1-day VaR = $10,000
- Meaning: 95% confidence that daily loss won't exceed $10,000
- Or: 5% chance loss exceeds $10,000 (1 in 20 days)

**Common Confidence Levels:**
- **95%**: Standard
- **99%**: Conservative
- **99.9%**: Very conservative (stress testing)

**Why It Matters:**
- Risk budgeting and limits
- Regulatory compliance
- Capital requirements

**Limitations:**
- Doesn't tell you HOW BAD losses beyond VaR might be
- Assumes historical patterns repeat

---

### 10. **Conditional VaR (CVaR / Expected Shortfall)** 📉

**Definition**: Average loss in worst-case scenarios

**Example**: 95% CVaR = $15,000
- If you breach the 95% VaR threshold, expect to lose $15,000 on average

**Why CVaR > VaR:**
- Captures tail risk magnitude (not just frequency)
- Coherent risk measure (mathematically superior)
- More relevant for extreme events

---

## Risk Management

### Position Sizing

**Key Principle**: Never risk too much on any single trade

**Common Methods:**
1. **Fixed Percentage**: Risk 1-2% of capital per trade
2. **Kelly Criterion**: Optimal fraction based on edge and odds
3. **Volatility-Based**: Size inversely to asset volatility

### Diversification

**"Don't put all your eggs in one basket"**

**Types of Diversification:**
- **Across Assets**: Stocks, bonds, commodities, currencies
- **Across Strategies**: Momentum + mean reversion
- **Across Timeframes**: Short-term + long-term
- **Across Geographies**: US, Europe, Asia

**Correlation Matters:**
- Low correlation = Better diversification
- High correlation = Less benefit

### Stop Losses and Risk Limits

**Protect against catastrophic losses:**
- **Trade-level stops**: Exit if loss exceeds X%
- **Portfolio-level stops**: Reduce exposure if drawdown hits Y%
- **Volatility scaling**: Reduce size when volatility spikes

---

## Practical Considerations

### Transaction Costs

**Components:**
1. **Commissions**: Broker fees per trade
2. **Spread**: Bid-ask difference
3. **Slippage**: Price moves between order and execution
4. **Market Impact**: Large orders move prices against you

**Impact on Strategy:**
- High-frequency strategies need ultra-low costs
- Low turnover strategies can tolerate higher costs
- Always backtest with realistic cost assumptions

### Data Quality

**Garbage in, garbage out:**
- **Survivorship Bias**: Only looking at surviving companies
- **Look-Ahead Bias**: Using future information
- **Point-in-Time**: Use data as it was known at the time

### Overfitting

**The #1 killer of trading strategies**

**Signs of Overfitting:**
- Too many parameters (>5 parameters = red flag)
- Perfect in-sample, terrible out-of-sample
- Strategy has lots of special cases and rules
- Very high Sharpe (>3) on backtest

**Prevention:**
- Walk-forward optimization
- Out-of-sample testing
- Cross-validation
- Simplicity (Occam's Razor)

### Regime Changes

**Markets evolve:**
- What worked in 2010 may not work in 2025
- Be prepared to adapt or shut down strategies
- Monitor performance decay

---

## Conclusion

Successful algorithmic trading requires:

1. **Strong Foundation**: Understand trading concepts deeply
2. **Appropriate Strategy**: Match strategy to market conditions
3. **Proper Optimization**: Balance risk and return intelligently
4. **Rigorous Evaluation**: Use multiple metrics, not just returns
5. **Risk Management**: Protect capital first, make profits second
6. **Realistic Expectations**: Past performance ≠ future results
7. **Continuous Learning**: Markets change, keep adapting

**Remember**: The goal isn't to find the "perfect" strategy (it doesn't exist), but to build a robust, diversified approach that can survive various market conditions while generating acceptable risk-adjusted returns.

---

## Implementation in This Project

This project implements all the concepts covered in this guide:

### 20+ Trading Strategies
All strategies documented here are implemented in `src/strategy_wrapper.py`:
- **Momentum strategies** (Momentum, Time Series Momentum, MA Crossover)
- **Mean Reversion** strategies
- **Risk-based** (GMVP, CVaR, Max Diversification, Inverse Volatility)
- **Factor & ML** (Linear Regression, Random Forest, Gradient Boosting)
- **Advanced** (Regime Switching, ARMA Forecasting)

See [STRATEGIES.md](STRATEGIES.md) for full documentation and performance results.

### 5 Backtesting Methods
Comprehensive validation framework in `src/backtesting_methods.py`:
- Vanilla Backtest
- Walk-Forward Analysis
- Cross-Validation
- Monte Carlo Simulation
- Randomized Testing

See [BACKTESTING_METHODS.md](BACKTESTING_METHODS.md) for detailed methodology and actual results.

### Portfolio Optimization
Multiple optimization methods in `src/optimizer.py`:
- Mean-Variance Optimization (Sharpe maximization)
- Minimum Variance
- Risk Parity
- CVaR Minimization
- Maximum Diversification

### Real-World Considerations
- Transaction costs: 10 bps per trade
- Slippage modeling
- Proper date-specific calculations (no look-ahead bias)
- Warmup periods for all strategies
- Robust error handling

---

## Further Reading

### Books
- **"Quantitative Trading"** by Ernest Chan
- **"Advances in Financial Machine Learning"** by Marcos López de Prado
- **"Evidence-Based Technical Analysis"** by David Aronson
- **"The Man Who Solved the Market"** by Gregory Zuckerman

### Academic Papers
- Jegadeesh & Titman (1993) - Momentum
- Asness, Moskowitz & Pedersen (2013) - Value and Momentum Everywhere
- Maillard, Roncalli & Teiletche (2010) - Risk Parity
- Lo & MacKinlay (1990) - Mean Reversion

### Online Resources
- QuantConnect (quantconnect.com)
- Quantopian (archived but valuable)
- SSRN - Social Science Research Network
- arXiv - Quantitative Finance section

---

**This document is part of the algo-trading-modeling project.**  
**For implementation details, see:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and components
- [STRATEGIES.md](STRATEGIES.md) - 20+ strategy documentation with actual results
- [BACKTESTING_METHODS.md](BACKTESTING_METHODS.md) - 5 validation methods with results
- [STRATEGIES_EXTENDED.md](STRATEGIES_EXTENDED.md) - Advanced strategy details

**Version**: 3.0  
**Last Updated**: December 2024
**Test Period**: 5-year weekly backtests (2019-2024)

