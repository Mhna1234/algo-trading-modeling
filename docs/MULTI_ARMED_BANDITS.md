# Multi-Armed Bandits (MAB) for Algorithmic Trading

## Overview

Multi-Armed Bandits (MAB) is an online learning framework that solves the **exploration-exploitation dilemma**: how to balance trying new options (exploration) vs. sticking with known good options (exploitation). In trading, each "arm" represents a trading strategy, and the algorithm learns which strategies perform best over time while continuously adapting to market changes.

**Key Advantage**: MAB learns in real-time without requiring complete historical data, making it ideal for non-stationary financial markets where conditions change continuously.

---

## Why MAB for Algo Trading?

### Traditional Approach Problems
- **Equal Weighting**: Allocates same capital to all strategies regardless of performance
- **Static Allocation**: Doesn't adapt when strategies stop working
- **Lookback Bias**: Optimizes on past data that may not repeat
- **Regime Blindness**: Can't detect when market conditions change

### MAB Solutions
1. **Adaptive Allocation**: Automatically increases capital to winning strategies
2. **Continuous Learning**: Updates beliefs in real-time during backtesting/live trading
3. **Regime Detection**: Naturally adapts when strategies start/stop working
4. **Risk Management**: Can explore underperformers to avoid missing regime changes
5. **No Overfitting**: Uses only information available at decision time (no lookahead)

### Expected Benefits
- **10-30% Sharpe ratio improvement** over equal weighting (academic literature)
- **20-40% reduction in drawdown** through adaptive risk management
- **Automatic strategy selection** without manual intervention
- **Robust to regime changes** through continuous exploration

---

## Five Core MAB Algorithms

### 1. Thompson Sampling (RECOMMENDED FOR TRADING)

**Concept**: Bayesian approach that maintains probability distributions over expected returns. Sample from each distribution and pick the highest.

**Mathematics**:
```
For each strategy i:
  α_i = 1 + Σ(successes)    # Prior + wins
  β_i = 1 + Σ(failures)     # Prior + losses
  
At each decision:
  θ_i ~ Beta(α_i, β_i)      # Sample expected return
  Select i* = argmax(θ_i)   # Pick highest sample
  
After observing reward r:
  If r > threshold: α_i* += 1
  Else: β_i* += 1
```

**Why Best for Trading**:
- Naturally handles uncertainty (explores uncertain strategies more)
- No hyperparameter tuning required
- Works well with non-stationary rewards (markets)
- Computationally efficient

**Trading-Specific Adaptation**:
```
Reward = Sharpe_ratio_t or Risk_adjusted_return_t
Use discounted updates: α_i = λ*α_i + new_success
λ = 0.93-0.97 (decay factor, favors recent performance)
```

---

### 2. UCB1 (Upper Confidence Bound)

**Concept**: Deterministic algorithm that picks the strategy with highest upper confidence bound on its expected return.

**Mathematics**:
```
Q_i(t) = average_reward_i + sqrt(2*ln(t) / n_i)
         └─────┬──────┘      └────────┬────────┘
         Exploitation      Exploration bonus

Select i* = argmax(Q_i(t))

Where:
  t = total number of trials
  n_i = number of times strategy i was selected
  average_reward_i = mean historical return of strategy i
```

**Why for Trading**:
- Deterministic (reproducible backtests)
- Strong theoretical guarantees (logarithmic regret)
- Interpretable (can explain why a strategy was chosen)
- Good for risk-averse traders

**Trading Adaptation**:
```
Use tunable confidence: c*sqrt(2*ln(t) / n_i)
c = 1.0 (standard), c = 0.5 (less exploration), c = 2.0 (more exploration)

Reward = Sharpe ratio or Information ratio
```

---

### 3. EXP3 (Exponential-weight for Exploration and Exploitation)

**Concept**: Maintains probability distribution over strategies, updates exponentially based on performance. Designed for adversarial environments.

**Mathematics**:
```
Weight update:
  w_i(t+1) = w_i(t) * exp(γ * reward_i / p_i(t))
  
Probability distribution:
  p_i(t) = (1-γ) * w_i(t)/Σw_j(t) + γ/K
           └────────┬───────────┘   └─┬─┘
              Exploitation      Exploration
  
Where:
  γ = exploration rate (0.1-0.3 for trading)
  K = number of strategies
```

**Why for Trading**:
- **Best for non-stationary markets** (no assumption of independent rewards)
- Robust when market "fights back" (adaptive opponents)
- No need to model reward distributions
- Used by quantitative hedge funds

**Trading Application**:
```
Good for: High-frequency trading, competitive markets
Reward: Can use any metric (returns, Sharpe, Sortino)
γ = 0.1 (stable markets), γ = 0.3 (volatile markets)
```

---

### 4. Epsilon-Greedy

**Concept**: Simplest algorithm - exploit best strategy (1-ε)% of time, explore randomly ε% of time.

**Mathematics**:
```
With probability 1-ε:
  Select i* = argmax(Q_i)  # Best strategy
  
With probability ε:
  Select i uniformly at random  # Random exploration

Q_i = running average reward of strategy i
```

**Variants**:
```
Decaying ε-greedy: ε(t) = ε_0 / (1 + t/τ)
  Start with high exploration, reduce over time
  
Typical values:
  ε = 0.1 (stable markets)
  ε = 0.2-0.3 (volatile markets)
```

**Why for Trading**:
- Extremely simple to implement
- Good baseline for comparison
- Easy to understand and explain
- Works well with small number of strategies (<10)

**Limitations**:
- Random exploration is inefficient (wastes capital)
- Doesn't model uncertainty (treats all unexplored strategies equally)
- Requires manual tuning of ε

---

### 5. Sliding Window UCB (Time-Decayed)

**Concept**: Extension of UCB1 that only considers recent performance through sliding window. Forgets old data.

**Mathematics**:
```
Q_i(t) = avg_reward_i(last W periods) + c*sqrt(2*ln(W) / n_i)

Where:
  W = sliding window size (e.g., 60 trading days)
  Only rewards in [t-W, t] are counted
  
After each period:
  Drop oldest observation
  Add newest observation
  Recompute averages
```

**Why for Trading**:
- **Perfect for regime changes** (forgets irrelevant old data)
- More responsive than standard UCB1
- Simple modification of UCB1
- Good balance of simplicity and adaptiveness

**Trading Parameters**:
```
W = 60 days (2-3 months) for moderate adaptation
W = 20 days for fast adaptation (volatile markets)
W = 120 days for slow adaptation (stable markets)
```

---

## Algorithm Comparison for Trading

| Algorithm | Best For | Pros | Cons | Computational Cost |
|-----------|----------|------|------|-------------------|
| **Thompson Sampling** | Most scenarios | Optimal exploration, no tuning | Bayesian complexity | Medium |
| **UCB1** | Risk-averse, stable markets | Deterministic, theoretical guarantees | Sensitive to outliers | Low |
| **EXP3** | Adversarial, HFT | Robust to non-stationarity | Requires tuning γ | Low |
| **ε-Greedy** | Baseline, simple cases | Easy implementation | Inefficient exploration | Very Low |
| **Sliding Window UCB** | Regime changes | Adapts quickly, simple | Window size tuning | Low |

---

## MAB in Portfolio Management

### Standard Approach (Current)
```
12 strategies → Equal allocation (8.33% each) → Fixed weights
```
**Problem**: Wastes capital on underperforming strategies

### MAB Approach (Proposed)
```
12 strategies → MAB selection → Dynamic allocation based on performance
                 ↓
           Thompson Sampling
                 ↓
    Best strategy gets 100% (or weighted blend)
```
**Benefit**: Capital flows to winners automatically

### Meta-Strategy Architecture
```
PortfolioEngine
    ↓
MultiArmedBanditMetaStrategy
    ↓
[Strategy1, Strategy2, ..., Strategy12]
    ↓
Backtester evaluates performance
    ↓
MAB learns and adapts
```

---

## Key Concepts

### Regret
**Definition**: Difference between optimal strategy (if known in advance) and MAB performance.

```
Regret(T) = T*μ* - Σ(rewards earned)
Where μ* = best possible average reward
```

**Goal**: Minimize regret (MAB should converge to best strategy)

**Theoretical Bounds**:
- ε-Greedy: O(T) - linear regret (bad)
- UCB1: O(log T) - logarithmic regret (optimal)
- Thompson Sampling: O(√T log T) - near-optimal in practice

### Exploration-Exploitation Trade-off
```
Exploit: Use best known strategy (maximize short-term gain)
Explore: Try uncertain strategies (maximize long-term information)

Optimal: Balance both (MAB algorithms do this automatically)
```

### Non-Stationarity
**Problem**: In finance, best strategy changes over time (regime changes).

**Solution**: Use discounting or sliding windows
```
Discounted reward: R_t = λ*R_{t-1} + (1-λ)*r_t
λ = 0.93-0.97 (favor recent performance)
```

---

## Practical Considerations

### Reward Definition
```python
# Simple: Sharpe ratio
reward = sharpe_ratio

# Multi-objective (recommended)
reward = 0.4*sharpe + 0.3*returns - 0.2*drawdown - 0.1*volatility

# Risk-adjusted utility
reward = returns - risk_aversion*variance
```

### Cold Start
**Problem**: No historical data at beginning.

**Solutions**:
1. Equal allocation for first N periods (burn-in)
2. Use prior beliefs (initialize based on strategy type)
3. Optimistic initialization (assume all strategies are good)

### Minimum Allocation
**Why needed**: Exploration requires trying all strategies periodically.

**Implementation**:
```python
allocation[i] = max(min_allocation, mab_weight[i])
# e.g., min_allocation = 5% ensures diversification
```

---

## References

**Academic**:
- Russo et al. (2018): "A Tutorial on Thompson Sampling" - Foundation paper
- Shen et al. (2015): "Thompson Sampling for Online Portfolio Selection" - 30% Sharpe improvement
- Auer et al. (2002): "UCB Algorithm" - Original UCB1 paper with regret bounds

**Industry**:
- AQR Capital Management: Factor timing with online learning
- Two Sigma: Contextual bandits for strategy selection
- Quantopian Research: MAB for parameter optimization

**Books**:
- Lattimore & Szepesvári (2020): "Bandit Algorithms" - Comprehensive reference
- Sutton & Barto (2018): "Reinforcement Learning" - Chapter 2 on MAB

---

## Next Steps

1. Implement `MultiArmedBanditMetaStrategy` wrapper class
2. Start with Thompson Sampling (simplest, best performance)
3. Use Sharpe ratio as reward metric
4. Weekly rebalancing with 3-month evaluation window
5. Maintain 5% minimum allocation per strategy (diversification)
6. Compare against equal-weight baseline

**Expected timeline**: 2-4 weeks for initial implementation and validation.
