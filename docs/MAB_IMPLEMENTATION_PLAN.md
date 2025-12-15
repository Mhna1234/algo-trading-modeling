# MAB Implementation Plan - Algo Trading Project

## 1. Motivation and Problem Statement

### Current Limitations of Static Strategy Allocation

The project currently implements 22+ trading strategies (momentum, mean reversion, risk parity, machine learning-based, etc.). In production or backtesting scenarios, users face a fundamental allocation problem:

**Problem**: How much capital should be allocated to each strategy over time?

**Current Approaches**:
- **Equal weighting**: Allocate 1/N to each of N strategies regardless of performance
- **Ex-ante optimization**: Pre-select strategies based on historical backtests
- **Manual selection**: Human judgment based on market conditions

**Why These Are Suboptimal**:
1. **Regime Blindness**: Static allocations cannot adapt when market regimes change
2. **No Learning**: Past performance information is ignored in real-time
3. **Winner's Curse**: Ex-ante optimization often selects strategies that worked historically but fail forward
4. **Opportunity Cost**: Capital remains locked in underperforming strategies
5. **No Exploration**: Manual selection misses opportunities to discover newly effective strategies

### Why Multi-Armed Bandits at the Strategy Level

MAB frameworks are designed to solve exactly this problem: **sequential decision-making under uncertainty with the exploration-exploitation trade-off**.

**Key Insight**: Each trading strategy is an "arm" of the bandit. The algorithm learns which strategies (not which assets) deliver superior risk-adjusted returns in real-time, and dynamically reallocates capital accordingly.

**Why This Level of Abstraction**:
- **Strategy-level** decisions are less noisy than asset-level decisions (strategies aggregate many assets)
- **Rebalancing frequency** can be lower (weekly/monthly vs daily), reducing transaction costs
- **Interpretability**: "Why did we allocate 40% to momentum this month?" is answerable
- **Separation of concerns**: Asset-level optimization (GMVP, CVaR, etc.) remains unchanged
- **Risk management**: Existing portfolio optimizers continue to handle asset-level risk

**Expected Benefits**:
- **Adaptive allocation**: Capital flows to strategies that work in current regime
- **Regime detection**: Automatically discovers regime changes through performance shifts
- **Reduced overfitting**: Online learning reduces dependence on fixed historical periods
- **Diversification**: Exploration ensures no strategy is permanently abandoned

---

## 2. Conceptual Model

### Meta-Portfolio Formulation

At each rebalancing time $t$, we have:

$$
\text{FinalPortfolio}_t = \sum_{k=1}^{K} \alpha_{k,t} \cdot \text{StrategyPortfolio}_{k,t}
$$

Where:
- $K$ = number of candidate strategies (e.g., 6-12)
- $\alpha_{k,t}$ = allocation weight to strategy $k$ at time $t$ (determined by MAB)
- $\text{StrategyPortfolio}_{k,t}$ = asset weight vector from strategy $k$ at time $t$
- $\sum_{k=1}^{K} \alpha_{k,t} = 1$ and $\alpha_{k,t} \geq \alpha_{\min}$ (minimum allocation constraint)

**Each Strategy Already Handles**:
- Signal generation
- Asset-level portfolio optimization (e.g., GMVP, Sharpe maximization)
- Risk management (position limits, leverage constraints)

**The MAB Layer Handles**:
- Learning which strategy family works best currently
- Allocating capital across strategies ($\alpha$ weights)
- Balancing exploration (trying uncertain strategies) vs exploitation (using proven strategies)

### Definition of Arms

**Arm** = A complete trading strategy wrapper (instance of `BaseStrategyWrapper`).

Examples:
- Momentum strategy (top 10 assets, 126-day lookback, GMVP optimizer)
- Mean reversion strategy (21-day lookback, CVaR optimizer)
- Low volatility strategy (inverse volatility weighting)
- ML-based strategy (random forest forecasting, Sharpe optimizer)

**Critical**: The arm is NOT an individual asset. The MAB does not select "buy AAPL vs MSFT". It selects "use momentum strategy vs mean reversion strategy", where each strategy already contains its own asset selection and weighting logic.

### Rewards

**Reward** = Realized risk-adjusted return of strategy $k$ over evaluation period $[t-L, t]$.

**Timing**:
1. At rebalance time $t$, MAB selects strategy allocations $\{\alpha_{k,t}\}$
2. Portfolio executes these allocations
3. At next rebalance time $t+1$, **realized returns** over $[t, t+1]$ are observed
4. Rewards are calculated and fed back to MAB to update beliefs
5. MAB selects new allocations $\{\alpha_{k,t+1}\}$ based on updated beliefs

**Lookback**: Rewards typically use a sliding window (e.g., last 12 weeks) to evaluate recent strategy performance, not just single-period returns.

### Rebalance Timing

**Frequency**: Weekly or bi-weekly (aligned with existing strategy rebalancing).

**Rationale**:
- Daily rebalancing at strategy level creates excessive turnover
- Monthly rebalancing is too slow to adapt to regime changes
- Weekly provides good balance between responsiveness and stability

---

## 3. Component Overview

### 3.1 BanditAllocator (Pure MAB Logic)

**Purpose**: Encapsulates bandit algorithm logic in a reusable, testable, strategy-agnostic class.

**Responsibilities**:
- Maintain internal state (arm statistics: means, variances, selection counts)
- Implement arm selection algorithms (UCB, Thompson Sampling, etc.)
- Update beliefs after receiving rewards
- Provide allocation weights (not just single arm selection)
- Support minimum allocation constraints
- Track selection history for diagnostics

**Explicit Non-Responsibilities**:
- No market data access
- No knowledge of what "strategies" are
- No portfolio construction logic
- No execution or rebalancing logic
- No reward calculation (receives rewards as input)

**Design Principle**: `BanditAllocator` should be testable in isolation with synthetic reward sequences, without any dependency on trading infrastructure.

---

### 3.2 BanditStrategyWrapper (Strategy Integration)

**Purpose**: Bridge between the bandit allocation logic and the existing strategy wrapper architecture.

**Responsibilities**:
- Implement `BaseStrategyWrapper` interface (drop-in replacement for any strategy)
- Own and manage a collection of child strategy instances
- Delegate to `BanditAllocator` for allocation decisions
- Aggregate child strategy weights into final portfolio weights
- Calculate rewards based on realized performance
- Expose diagnostic information (selection history, reward history, allocation evolution)

**Lifecycle**:
1. **Initialization**: Instantiate child strategies and bandit allocator
2. **Cold Start**: During burn-in period, use equal allocation or prior beliefs
3. **Selection Phase**: At each rebalance, query `BanditAllocator` for allocations
4. **Weight Aggregation**: Combine child strategy weights using bandit allocations
5. **Performance Tracking**: Monitor realized returns for each strategy allocation
6. **Reward Feedback**: Calculate and feed rewards back to `BanditAllocator`
7. **Adaptation**: Allocations evolve based on observed performance

**Integration Point**: `BanditStrategyWrapper` is registered and used exactly like `MomentumStrategy` or `MeanReversionStrategy` in demos and backtests.

---

## 4. Class Responsibilities & Interfaces

### 4.1 BanditAllocator Interface

**Conceptual Public API**:

```
class BanditAllocator:
    __init__(n_arms, algorithm, min_allocation, **params)
        Initialize bandit with N arms
        
    select_allocations() -> np.ndarray
        Return allocation weights [α_1, ..., α_K]
        Respects minimum allocation constraint
        
    update(arm_id, reward)
        Update beliefs for single arm after observing reward
        (For winner-take-all selection)
        
    update_all(rewards)
        Update beliefs for all arms after observing reward vector
        (For blended allocation)
        
    get_statistics() -> dict
        Return current arm statistics (means, ucb scores, selection counts)
        
    reset()
        Reset bandit state (for testing or re-initialization)
```

**Key Design Decisions**:
- **Allocation vs Selection**: Returns full allocation vector, not just winner index
- **Minimum Allocation**: Enforced at allocation level, not at algorithm level
- **Algorithm Pluggability**: Algorithm name passed as string, factory pattern for instantiation
- **Stateful**: Maintains history and statistics across calls

**Supported Algorithms** (initial scope):
- `'ucb'`: Upper Confidence Bound (default)
- `'thompson'`: Thompson Sampling (optional)
- `'epsilon_greedy'`: Epsilon-greedy (baseline)

**Parameters**:
- `n_arms`: Number of strategies
- `algorithm`: Algorithm identifier
- `min_allocation`: Minimum weight per arm (e.g., 0.05 for 5%)
- `exploration_factor`: Algorithm-specific tuning (e.g., UCB confidence level)
- `decay_factor`: Discount factor for non-stationary environments (optional)

---

### 4.2 BanditStrategyWrapper Interface

**Conceptual Public API**:

```
class BanditStrategyWrapper(BaseStrategyWrapper):
    __init__(child_strategies, bandit_config, reward_config, rebalance_config)
        Initialize with list of child strategies and configuration
        
    get_weights(date, portfolio_state) -> pd.Series
        PRIMARY METHOD: Return asset weights for current rebalance
        - Query BanditAllocator for strategy allocations
        - Get weights from each child strategy
        - Aggregate using weighted combination
        - Track performance for reward calculation
        
    get_strategy_info() -> dict
        Return metadata (strategy name, algorithm, parameters)
        
    get_diagnostics() -> dict
        Return detailed diagnostic information:
        - Selection history (which strategies chosen when)
        - Allocation evolution over time
        - Reward history
        - Arm statistics from BanditAllocator
        - Attribution analysis (performance by strategy)
```

**Implementation Flow** (inside `get_weights`):

1. **Burn-in Check**: If in burn-in period, return equal allocation
2. **Allocation Decision**: Call `bandit_allocator.select_allocations()` → $\{\alpha_k\}$
3. **Child Strategy Weights**: For each child strategy $k$, call `child_k.get_weights(date, portfolio_state)` → $w_k$
4. **Aggregation**: Compute $w_{\text{final}} = \sum_k \alpha_k \cdot w_k$
5. **Performance Tracking**: Record current allocations for future reward calculation
6. **Return**: Return $w_{\text{final}}$ to `PortfolioEngine`

**Reward Calculation** (deferred to next rebalance):
- At time $t+1$, compute realized returns over $[t, t+1]$ for each strategy allocation
- Calculate risk-adjusted reward (see Section 6)
- Call `bandit_allocator.update_all(rewards)` or `update(arm_id, reward)`

**Thread Safety**: Not required (single-threaded backtesting assumed).

---

### 4.3 Interaction Flow

```
User Code
    ↓
PortfolioEngine.run_backtest(bandit_strategy_wrapper, ...)
    ↓
For each rebalance date t:
    PortfolioEngine calls bandit_strategy_wrapper.get_weights(date_t, portfolio_state_t)
        ↓
    BanditStrategyWrapper:
        1. Calculate rewards from previous period [t-1, t]
        2. Update BanditAllocator with rewards
        3. Query BanditAllocator.select_allocations() → {α_k}
        4. For each child strategy k:
               weights_k = child_k.get_weights(date_t, portfolio_state_t)
        5. Aggregate: weights_final = Σ α_k * weights_k
        6. Record allocation for next period's reward calculation
        7. Return weights_final
    ↓
PortfolioEngine executes weights_final, tracks returns, advances to t+1
```

**Key Point**: `PortfolioEngine` sees `BanditStrategyWrapper` as just another strategy. It does not know or care that MAB logic is happening inside.

---

## 5. Supported Bandit Algorithms (Initial Scope)

### 5.1 UCB (Upper Confidence Bound) - DEFAULT

**Algorithm**: Select allocations based on upper confidence bounds.

$$
\text{UCB}_k = \bar{r}_k + c \sqrt{\frac{2 \ln T}{n_k}}
$$

Where:
- $\bar{r}_k$ = average reward of strategy $k$
- $T$ = total number of rebalancing periods
- $n_k$ = number of times strategy $k$ was selected
- $c$ = exploration constant (default: 1.5-2.0)

**Allocation**: Apply softmax to UCB scores with minimum allocation floor.

**Rationale**:
- Deterministic (reproducible backtests)
- Strong theoretical regret bounds
- Balances exploration (untried strategies get high UCB) and exploitation (good strategies get selected)
- Interpretable (can explain why a strategy was selected)

**Tuning**:
- Increase $c$ for more exploration (volatile/changing markets)
- Decrease $c$ for more exploitation (stable markets)

---

### 5.2 Thompson Sampling - OPTIONAL

**Algorithm**: Bayesian approach with posterior sampling.

For each arm $k$:
1. Maintain Beta distribution: $\text{Beta}(\alpha_k, \beta_k)$
2. Sample: $\theta_k \sim \text{Beta}(\alpha_k, \beta_k)$
3. Select arms with highest samples

**Update Rule**:
- If reward > threshold: $\alpha_k \leftarrow \alpha_k + 1$
- If reward < threshold: $\beta_k \leftarrow \beta_k + 1$

**Rationale**:
- Naturally explores uncertain strategies (wide posterior = more exploration)
- No hyperparameters to tune
- Excellent empirical performance in non-stationary environments

**Trade-off**: Stochastic (backtests not perfectly reproducible without seed control).

---

### 5.3 Epsilon-Greedy - BASELINE

**Algorithm**: 
- With probability $1 - \epsilon$: Select best strategy (exploitation)
- With probability $\epsilon$: Select random strategy (exploration)

**Rationale**: Simple baseline for comparison. Not recommended for production due to inefficient exploration.

---

### 5.4 Extensibility (Future)

**Discounted Rewards**: Apply exponential decay to older observations for faster adaptation.

$$
\bar{r}_k(t) = \lambda \bar{r}_k(t-1) + (1 - \lambda) r_k(t)
$$

Where $\lambda \in [0.9, 0.99]$ is decay factor.

**Sliding Window**: Only consider last $W$ periods (e.g., 12 weeks) when calculating statistics.

**Contextual Bandits**: Condition selection on market state features (VIX, trend, sector rotation). This requires significant additional infrastructure and is explicitly out of scope for Phase 1.

---

## 6. Reward Design (CRITICAL)

### 6.1 Why Raw Returns Are Unsafe

**Problem**: Using raw returns $r_k = \frac{V_{t+1} - V_t}{V_t}$ as rewards creates several issues:

1. **Volatility Ignorance**: A strategy with 20% return and 40% volatility looks better than one with 15% return and 10% volatility
2. **Tail Risk**: Strategies with positive skew (small steady gains, occasional large losses) look good until they blow up
3. **Regime Overfitting**: High short-term returns in favorable regimes lead to overallocation, then losses when regime shifts
4. **No Risk Penalty**: MAB will chase returns without considering drawdowns or volatility

**Consequence**: The bandit will concentrate allocation in high-risk strategies, amplifying portfolio volatility and drawdown.

---

### 6.2 Recommended Reward Definitions

**Option 1: Risk-Adjusted Return (Recommended Default)**

$$
\text{reward}_k = \frac{\bar{r}_k}{\sigma_k + \epsilon}
$$

Where:
- $\bar{r}_k$ = average return of strategy $k$ over lookback window (e.g., last 12 weeks)
- $\sigma_k$ = standard deviation of returns over same window
- $\epsilon$ = small constant (e.g., 0.01) to avoid division by zero

**Interpretation**: This is approximately a realized Sharpe ratio (without excess return over risk-free rate).

**Benefits**:
- Penalizes volatile strategies
- Rewards consistent performance
- Scale-free (comparable across strategies)

---

**Option 2: Clipped Sharpe-Like Reward**

$$
\text{reward}_k = \text{clip}\left( \frac{\bar{r}_k - r_f}{\sigma_k + \epsilon}, -1, 3 \right)
$$

Where $r_f$ = risk-free rate (or target return).

**Benefits**:
- Bounded rewards prevent outlier domination
- Negative rewards for underperforming strategies

---

**Option 3: Multi-Objective Reward**

$$
\text{reward}_k = w_1 \cdot \frac{\bar{r}_k}{\sigma_k} + w_2 \cdot \bar{r}_k - w_3 \cdot \text{MaxDD}_k - w_4 \cdot \sigma_k
$$

Where:
- $\text{MaxDD}_k$ = maximum drawdown over lookback window
- $w_1, w_2, w_3, w_4$ = weighting factors (e.g., $[0.4, 0.3, 0.2, 0.1]$)

**Benefits**:
- Explicitly penalizes drawdowns
- Can incorporate multiple objectives (return, Sharpe, drawdown, volatility)

**Trade-off**: More complex, requires normalization and tuning of weights.

---

### 6.3 Reward Timing and Update Rules

**Timing**:
1. At time $t$, MAB selects allocations $\{\alpha_{k,t}\}$
2. Portfolio executes over period $[t, t+1]$
3. At time $t+1$, calculate realized returns for each strategy **as if it had 100% allocation**:
   $$r_k = \frac{V_{k,t+1} - V_{k,t}}{V_{k,t}}$$
4. Compute reward: $\text{reward}_k = f(r_k, \sigma_k, \text{other metrics})$
5. Update bandit: `update_all([reward_1, ..., reward_K])`

**Key Design Choice**: Rewards are based on **strategy performance**, not on allocation-weighted portfolio performance. This ensures each strategy is evaluated independently.

**Lookback Window**: Use last $L$ periods (e.g., $L = 12$ weeks) to calculate rolling Sharpe for reward.

**Frequency**: Rewards updated at each rebalancing event (weekly or bi-weekly).

---

## 7. Rebalancing & Stability Controls

### 7.1 Rebalance Frequency

**Recommendation**: Weekly or bi-weekly.

**Trade-offs**:

| Frequency | Pros | Cons |
|-----------|------|------|
| **Daily** | Fast adaptation | Excessive turnover, noisy signals |
| **Weekly** | Good balance | Moderate adaptation speed |
| **Monthly** | Low turnover | Slow to detect regime changes |

**Default**: Weekly, aligned with existing strategy rebalancing in the system.

---

### 7.2 Soft Allocation vs Winner-Take-All

**Winner-Take-All**:
- MAB selects single best strategy
- All capital allocated to that strategy
- Other strategies remain active for observation only

**Soft Allocation** (Recommended):
- MAB provides weight vector $\{\alpha_k\}$ with $\alpha_k \geq \alpha_{\min}$
- Capital distributed across multiple strategies
- Reduces concentration risk
- Smoother transitions between strategies

**Implementation**:
```
After computing UCB scores or Thompson samples:
1. Apply softmax with temperature: α_k ∝ exp(score_k / τ)
2. Enforce minimum allocation: α_k = max(α_k, α_min)
3. Renormalize to sum to 1.0
```

**Temperature Parameter** ($\tau$):
- High $\tau$ → More uniform allocation (exploration)
- Low $\tau$ → Concentrated allocation (exploitation)
- Default: $\tau = 0.5$ to 1.0

---

### 7.3 Minimum Strategy Weights

**Constraint**: Each strategy must maintain at least $\alpha_{\min}$ allocation (e.g., 5-10%).

**Rationale**:
1. **Continuous Monitoring**: Even "bad" strategies are tracked for regime changes
2. **Diversification**: Prevents over-concentration in single strategy
3. **Exploration**: Ensures all arms are periodically evaluated
4. **Regime Shifts**: Previously poor strategies may become effective in new regimes

**Implementation**: After bandit selection, enforce:
$$
\alpha_k = \max(\alpha_k^{\text{raw}}, \alpha_{\min}) \quad \forall k
$$
Then renormalize to sum to 1.0.

**Recommended Values**:
- 6 strategies: $\alpha_{\min} = 0.10$ (10%)
- 8 strategies: $\alpha_{\min} = 0.08$ (8%)
- 12 strategies: $\alpha_{\min} = 0.05$ (5%)

---

### 7.4 Turnover Control

**Issue**: Frequent reallocation between strategies creates unnecessary transaction costs.

**Mitigation**:
1. **Rebalancing Threshold**: Only rebalance if $\|\alpha_t - \alpha_{t-1}\|_1 > \delta$ (e.g., $\delta = 0.15$)
2. **Soft Updates**: Use exponential smoothing:
   $$\alpha_t = (1 - \beta) \alpha_{t-1} + \beta \alpha_t^{\text{new}}$$
   where $\beta \in [0.2, 0.5]$ controls update speed
3. **Transaction Cost Penalty**: Incorporate turnover into reward calculation

**Not Recommended for Phase 1**: Turnover control adds complexity. Start with fixed weekly rebalancing, then optimize if turnover becomes problematic in backtests.

---

## 8. Integration with Existing Pipeline

### 8.1 Strategy Registration

`BanditStrategyWrapper` is treated exactly like any other strategy wrapper.

**Example Usage**:
```python
from src.strategy_wrapper import (
    BanditStrategyWrapper,
    MomentumStrategy, 
    MeanReversionStrategy,
    GMVPStrategy
)

# Create child strategies
children = [
    MomentumStrategy(strategy, optimizer, top_k=10, lookback=126),
    MeanReversionStrategy(strategy, optimizer, lookback=21),
    GMVPStrategy(strategy, optimizer),
    # ... more strategies
]

# Create bandit meta-strategy
bandit_strategy = BanditStrategyWrapper(
    child_strategies=children,
    bandit_algorithm='ucb',
    min_allocation=0.08,
    reward_metric='risk_adjusted_return',
    lookback_periods=12
)

# Use like any other strategy
portfolio = PortfolioEngine(prices, initial_capital=100000)
result = portfolio.run_backtest(
    strategy=bandit_strategy,
    start_date='2019-01-01',
    end_date='2024-12-31',
    freq='W'
)
```

**Key Point**: No changes to `PortfolioEngine`, `Backtester`, or any existing infrastructure.

---

### 8.2 Demo Integration

**New Demo File**: `examples/demo_bandit_meta_strategy.py`

**Comparison Baselines**:
1. Equal-weight allocation across same child strategies
2. Best single strategy (oracle, known only in hindsight)
3. Worst single strategy (to show downside protection)

**Outputs**:
- Performance metrics comparison table
- Strategy allocation evolution over time
- Reward/regret plots
- Selection frequency histogram

---

### 8.3 Reward Feedback Mechanism

**Challenge**: `get_weights()` is called at time $t$, but rewards are only observable at time $t+1$ after returns are realized.

**Solution**: Track pending allocations and calculate rewards at next rebalance.

**Implementation Sketch**:
```
class BanditStrategyWrapper:
    def __init__(...):
        self.pending_allocations = {}  # {date: {strategy: allocation}}
        self.performance_tracker = {}  # {strategy: recent_returns}
        
    def get_weights(self, date, portfolio_state):
        # 1. If previous period exists, calculate rewards and update bandit
        if date in self.pending_allocations:
            rewards = self._calculate_rewards(date, portfolio_state)
            self.bandit_allocator.update_all(rewards)
        
        # 2. Select new allocations
        allocations = self.bandit_allocator.select_allocations()
        
        # 3. Get child weights and aggregate
        weights = self._aggregate_weights(allocations, date, portfolio_state)
        
        # 4. Store for next period's reward calculation
        self.pending_allocations[date] = allocations
        
        return weights
```

**Data Flow**: `PortfolioState` contains historical returns, which `BanditStrategyWrapper` uses to compute strategy-specific performance.

---

## 9. Configuration & Defaults

### 9.1 Recommended Default Parameters

```yaml
bandit_config:
  algorithm: 'ucb'
  min_allocation: 0.08  # 8% minimum per strategy
  exploration_factor: 1.5  # UCB confidence multiplier
  burn_in_periods: 12  # Equal allocation for first 12 weeks
  
reward_config:
  metric: 'risk_adjusted_return'  # Options: raw_return, risk_adjusted_return, multi_objective
  lookback_periods: 12  # 3 months for weekly rebalancing
  clip_range: [-1.0, 3.0]  # Clip rewards to prevent outliers
  
rebalance_config:
  frequency: 'weekly'
  day_of_week: 'monday'
  soft_allocation: true  # Use softmax blending vs winner-take-all
  temperature: 0.8  # Softmax temperature
```

---

### 9.2 Strategy Count Limits

**Recommendation**: Limit to 6-8 child strategies.

**Rationale**:
1. **Sample Efficiency**: With weekly rebalancing, 12 strategies require ~60 weeks (1 year) to explore each 5 times
2. **Diversification**: 6-8 strategies provide sufficient diversification
3. **Computation**: Each strategy evaluation has cost; limit parallelism
4. **Interpretability**: 6 strategies easier to track than 22

**Strategy Selection Heuristic**:
- Include 1-2 momentum strategies (trend following)
- Include 1-2 mean reversion strategies (contrarian)
- Include 2-3 risk-based strategies (GMVP, risk parity, low vol)
- Include 1-2 optimization-based strategies (CVaR, Sharpe maximization)

**Avoid**: Including multiple variants of the same strategy family (e.g., 5 momentum strategies with different lookbacks). This dilutes exploration.

---

## 10. Testing & Validation Plan

### 10.1 Unit Tests for BanditAllocator

**Test Suite**: `tests/test_bandit_allocator.py`

**Required Tests**:
```
test_ucb_initialization()
    - Verify initial state (all arms equal)
    
test_ucb_selection_deterministic()
    - Given fixed rewards, verify expected arm selection
    
test_ucb_exploration_bonus()
    - Verify untried arms get high UCB scores
    
test_minimum_allocation_enforcement()
    - Verify all allocations ≥ min_allocation
    
test_allocation_sum_to_one()
    - Verify Σ α_k = 1.0 always
    
test_thompson_sampling_stochastic()
    - Verify sampling behavior (with fixed seed)
    
test_reward_update()
    - Verify statistics update correctly after rewards
    
test_decay_factor()
    - Verify exponential decay applied correctly
    
test_multiple_arms_performance()
    - Simulate 100-period sequence, verify convergence to best arm
```

**Property-Based Tests**:
- Allocation weights always valid (non-negative, sum to 1)
- No runtime errors on edge cases (zero rewards, negative rewards, NaN)

---

### 10.2 Integration Tests for BanditStrategyWrapper

**Test Suite**: `tests/test_bandit_strategy_wrapper.py`

**Required Tests**:
```
test_wrapper_initialization()
    - Verify child strategies registered correctly
    
test_get_weights_returns_valid_series()
    - Verify output format matches BaseStrategyWrapper
    
test_burn_in_period()
    - Verify equal allocation during burn-in
    
test_weight_aggregation()
    - Given known child weights and allocations, verify correct aggregation
    
test_reward_calculation()
    - Mock portfolio_state, verify rewards computed correctly
    
test_bandit_update_called()
    - Verify bandit allocator updated after each rebalance
    
test_diagnostics_output()
    - Verify get_diagnostics() returns expected fields
    
test_integration_with_portfolio_engine()
    - Full backtest with mock data, verify no errors
```

---

### 10.3 Backtest Sanity Checks

**Validation Criteria**:
1. **No Lookahead Bias**: Manually inspect that rewards only use data available at decision time
2. **Convergence**: By end of backtest, allocation should concentrate on top-performing strategies
3. **Exploration**: All strategies should be selected at least once (due to min_allocation)
4. **Regime Adaptation**: In known regime changes (e.g., 2020 COVID crash), verify allocation shifts
5. **Performance**: Bandit meta-strategy should outperform equal-weight baseline in Sharpe ratio

**Red Flags**:
- Bandit performs worse than equal-weight → Reward function issue or lookback too short
- Zero exploration → Min allocation not enforced
- Excessive turnover → Need turnover control or longer lookback
- Allocation to single strategy only → Temperature too low or min_allocation not working

**Comparison Benchmarks**:
```
1. Equal-weight: Σ (1/K * child_strategy_k)
2. Best single: Best child strategy (oracle)
3. Worst single: Worst child strategy (downside protection check)
4. Random selection: Random strategy each period (worse than equal-weight expected)
```

---

## 11. Explicit Non-Goals (Phase 1)

### 11.1 No Asset-Level Bandits

**Out of Scope**: Using MAB to select individual assets (e.g., "buy AAPL vs MSFT vs GOOGL").

**Rationale**:
- Asset-level decisions are too noisy (single asset returns highly volatile)
- Require daily or intraday rebalancing (transaction costs prohibitive)
- Existing portfolio optimizers (GMVP, CVaR, Sharpe) already handle this well
- Loses diversification benefits

**Clarification**: The MAB selects strategies, and each strategy handles its own asset selection using existing optimizers.

---

### 11.2 No Direct Execution Logic

**Out of Scope**: `BanditAllocator` or `BanditStrategyWrapper` does not interact with execution layer, broker APIs, or order management.

**Rationale**: Separation of concerns. Execution is handled by `PortfolioEngine` after weights are returned.

---

### 11.3 No Deep RL or Policy Gradients

**Out of Scope**: Advanced reinforcement learning methods (DQN, PPO, A3C, policy gradients).

**Rationale**:
- MAB is simpler, more interpretable, and requires less data
- Deep RL requires extensive hyperparameter tuning and infrastructure
- MAB sufficient for strategy-level allocation problem

**Future Consideration**: If MAB proves successful, contextual bandits (linear or neural) may be explored in Phase 2.

---

### 11.4 No Real-Time Market Data in BanditAllocator

**Out of Scope**: `BanditAllocator` receiving live market data, prices, or order book information.

**Rationale**: BanditAllocator is pure allocation logic. It receives rewards (summary statistics), not raw market data. This keeps it testable and modular.

---

### 11.5 No Multi-Objective Optimization Beyond Reward

**Out of Scope**: Pareto-optimal frontiers, constraint optimization, or multi-objective programming within MAB.

**Rationale**: Risk management is handled via reward function design (e.g., risk-adjusted return). Keep MAB focused on single scalar reward maximization.

---

## 12. Summary and Next Steps

### 12.1 Key Takeaways

1. **MAB is a meta-strategy**: It allocates capital across existing strategies, not across assets
2. **Two new components**: `BanditAllocator` (pure logic) and `BanditStrategyWrapper` (integration)
3. **No changes to existing code**: Strategies, optimizers, and execution layer remain untouched
4. **Risk-adjusted rewards**: Use Sharpe-like rewards to avoid chasing volatility
5. **Soft allocation with minimums**: Blend multiple strategies with minimum allocation floor
6. **Weekly rebalancing**: Balance adaptation speed with transaction costs

---

### 12.2 Implementation Checklist

**Phase 1 (Weeks 1-2): Core Implementation**
- [ ] Implement `BanditAllocator` class with UCB and Thompson Sampling
- [ ] Implement `BanditStrategyWrapper` class
- [ ] Write unit tests for `BanditAllocator`
- [ ] Write integration tests for `BanditStrategyWrapper`

**Phase 2 (Week 3): Validation**
- [ ] Create demo script comparing bandit vs baselines
- [ ] Run 5-year backtest on historical data
- [ ] Validate performance improvement over equal-weight
- [ ] Check for lookahead bias and implementation errors

**Phase 3 (Week 4): Production Readiness**
- [ ] Add configuration file support
- [ ] Integrate into benchmark suite
- [ ] Add diagnostic visualizations (allocation evolution, reward plots)
- [ ] Document usage in README and examples

---

### 12.3 Success Metrics

**Minimum Acceptable Performance** (vs equal-weight baseline):
- Sharpe ratio improvement: ≥ 10%
- Drawdown reduction: ≥ 10%
- No worse than best single strategy in any 2-year period

**Target Performance**:
- Sharpe ratio improvement: 15-25%
- Drawdown reduction: 20-30%
- Allocation concentrates on top 2-3 strategies by end of backtest

---

### 12.4 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Overfitting to recent data** | Use 12-week lookback, risk-adjusted rewards |
| **Slow regime detection** | Decay factor or sliding window for faster adaptation |
| **Over-concentration** | Minimum allocation constraint (5-8%) |
| **Excessive turnover** | Weekly (not daily) rebalancing, soft allocation |
| **Lookahead bias** | Strict reward calculation using only past data |
| **Poor exploration** | UCB/Thompson naturally explore; min allocation enforces it |

---

### 12.5 Documentation Requirements

**Files to Create**:
1. `src/bandit_allocator.py` - Core MAB logic
2. `src/bandit_strategy_wrapper.py` - Strategy integration (or extend `strategy_wrapper.py`)
3. `examples/demo_bandit_meta_strategy.py` - Demo script
4. `tests/test_bandit_allocator.py` - Unit tests
5. `tests/test_bandit_strategy_wrapper.py` - Integration tests
6. `config/bandit_config.yaml` - Default configuration

**Files to Update**:
1. `docs/STRATEGIES.md` - Add bandit meta-strategy description
2. `docs/ARCHITECTURE.md` - Add MAB layer to architecture diagram
3. `README.md` - Mention bandit meta-strategy in features list

---

## References

**Academic Literature**:
- Auer, P., Cesa-Bianchi, N., & Fischer, P. (2002). Finite-time analysis of the multiarmed bandit problem. *Machine Learning*, 47(2), 235-256.
- Russo, D. et al. (2018). A tutorial on Thompson sampling. *Foundations and Trends in Machine Learning*, 11(1), 1-96.
- Shen, W. et al. (2015). Thompson sampling for portfolio selection. *arXiv preprint*.

**Industry Practice**:
- AQR Capital: Factor timing using online learning
- Two Sigma: Adaptive strategy allocation
- Systematic trend-following funds: Regime-aware allocation

**Internal Documentation**:
- `docs/MULTI_ARMED_BANDITS.md` - MAB theory and algorithms
- `docs/STRATEGIES.md` - Existing strategy documentation
- `docs/ARCHITECTURE.md` - System architecture overview

---

**Document Version**: 2.0  
**Last Updated**: December 15, 2025  
**Authors**: Quantitative Engineering Team

---

## Implementation Roadmap

### Phase 1: Core MAB Implementation (Week 1-2)

#### Task 1.1: Create MAB Base Classes
**File**: `src/mab_framework.py` (NEW)

**Classes to implement**:
```python
class MultiArmedBandit(ABC):
    """Abstract base class for MAB algorithms"""
    @abstractmethod
    def select_arm(self) -> int:
        pass
    
    @abstractmethod
    def update(self, arm_id: int, reward: float):
        pass
    
    @abstractmethod
    def get_arm_probabilities(self) -> np.ndarray:
        pass

class ThompsonSamplingMAB(MultiArmedBandit):
    """Thompson Sampling implementation for strategy selection"""
    
    def __init__(self, n_arms: int, decay_factor: float = 0.95):
        self.n_arms = n_arms
        self.alpha = np.ones(n_arms)  # Success counts
        self.beta = np.ones(n_arms)   # Failure counts
        self.decay = decay_factor
        
    def select_arm(self) -> int:
        # Sample from Beta distributions
        samples = np.random.beta(self.alpha, self.beta)
        return np.argmax(samples)
    
    def update(self, arm_id: int, reward: float):
        # Update beliefs with decay
        self.alpha *= self.decay
        self.beta *= self.decay
        
        # Reward > 0 is success, < 0 is failure
        if reward > 0:
            self.alpha[arm_id] += 1
        else:
            self.beta[arm_id] += 1
```

**Deliverable**: `mab_framework.py` with ThompsonSamplingMAB, UCB1, and EpsilonGreedy classes.

---

#### Task 1.2: Create Meta-Strategy Wrapper
**File**: `src/strategy_wrapper.py` (EXTEND)

**Add new class**:
```python
class MultiArmedBanditMetaStrategy(BaseStrategyWrapper):
    """
    Meta-strategy that uses MAB to select among child strategies.
    
    Parameters
    ----------
    child_strategies : List[BaseStrategyWrapper]
        List of strategy instances to choose from (12 strategies)
    mab_algorithm : str
        MAB algorithm to use ('thompson', 'ucb1', 'epsilon_greedy')
    reward_metric : str
        Metric to optimize ('sharpe', 'returns', 'multi_objective')
    lookback_periods : int
        Number of periods to calculate reward over (21 for 1 month weekly)
    min_allocation : float
        Minimum allocation per strategy (0.05 for 5%)
    decay_factor : float
        Discount factor for recent performance (0.95 recommended)
    burn_in_periods : int
        Equal allocation for first N periods (12 recommended)
    """
    
    def __init__(
        self,
        child_strategies: List[BaseStrategyWrapper],
        mab_algorithm: str = 'thompson',
        reward_metric: str = 'multi_objective',
        lookback_periods: int = 12,  # 3 months weekly
        min_allocation: float = 0.05,
        decay_factor: float = 0.95,
        burn_in_periods: int = 12
    ):
        self.strategies = child_strategies
        self.n_strategies = len(child_strategies)
        self.lookback = lookback_periods
        self.min_alloc = min_allocation
        self.burn_in = burn_in_periods
        
        # Initialize MAB
        if mab_algorithm == 'thompson':
            self.mab = ThompsonSamplingMAB(self.n_strategies, decay_factor)
        elif mab_algorithm == 'ucb1':
            self.mab = UCB1MAB(self.n_strategies)
        else:
            self.mab = EpsilonGreedyMAB(self.n_strategies, epsilon=0.2)
        
        # Tracking
        self.period_count = 0
        self.selection_history = []
        self.reward_history = []
        self.strategy_returns = {s.name: [] for s in self.strategies}
        
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> pd.Series:
        """
        Select best strategy using MAB and return its weights.
        """
        self.period_count += 1
        
        # COLD START: Equal allocation during burn-in
        if self.period_count <= self.burn_in:
            selected_idx = self.period_count % self.n_strategies
            logger.info(f"Burn-in period {self.period_count}/{self.burn_in}: "
                       f"Using {self.strategies[selected_idx].name}")
        else:
            # MAB SELECTION
            selected_idx = self.mab.select_arm()
        
        selected_strategy = self.strategies[selected_idx]
        self.selection_history.append((date, selected_idx, selected_strategy.name))
        
        # Get weights from selected strategy
        weights = selected_strategy.get_weights(date, portfolio_state)
        
        # UPDATE MAB (after sufficient history)
        if len(self.selection_history) > self.lookback:
            reward = self._calculate_reward(selected_idx, portfolio_state)
            self.mab.update(selected_idx, reward)
            self.reward_history.append((date, selected_idx, reward))
        
        return weights
    
    def _calculate_reward(self, strategy_idx: int, portfolio_state: PortfolioState) -> float:
        """
        Calculate reward for strategy based on recent performance.
        Uses multi-objective function.
        """
        # Get recent returns (last lookback periods)
        recent_returns = portfolio_state.return_history.iloc[-self.lookback:]
        portfolio_returns = recent_returns.mean(axis=1)  # Assume equal weight for calculation
        
        # Calculate metrics
        sharpe = self._calculate_sharpe(portfolio_returns)
        total_return = (1 + portfolio_returns).prod() - 1
        max_dd = self._calculate_max_drawdown(portfolio_returns)
        volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Normalize to 0-1 scale (approximate)
        norm_sharpe = np.clip(sharpe / 3.0, -1, 1)  # Sharpe 3.0 = perfect
        norm_return = np.clip(total_return * 4, -1, 1)  # 25% return = perfect
        norm_dd = np.clip(max_dd / 0.3, 0, 1)  # 30% DD = worst
        norm_vol = np.clip(volatility / 0.4, 0, 1)  # 40% vol = worst
        
        # Multi-objective reward (based on requirements)
        reward = (
            0.40 * norm_sharpe +
            0.30 * norm_return -
            0.20 * norm_dd -
            0.10 * norm_vol
        )
        
        return reward
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return MAB configuration and selection statistics."""
        return {
            'name': 'Multi-Armed Bandit Meta-Strategy',
            'algorithm': self.mab.__class__.__name__,
            'n_strategies': self.n_strategies,
            'child_strategies': [s.name for s in self.strategies],
            'selection_counts': self._get_selection_counts(),
            'current_probabilities': self.mab.get_arm_probabilities(),
            'lookback_periods': self.lookback,
            'min_allocation': self.min_alloc
        }
    
    def _get_selection_counts(self) -> Dict[str, int]:
        """Count how many times each strategy was selected."""
        counts = {s.name: 0 for s in self.strategies}
        for _, idx, name in self.selection_history:
            counts[name] += 1
        return counts
```

**Deliverable**: New `MultiArmedBanditMetaStrategy` class added to `strategy_wrapper.py`.

---

### Phase 2: Testing & Validation (Week 2-3)

#### Task 2.1: Unit Tests
**File**: `tests/test_mab_framework.py` (NEW)

**Tests to implement**:
```python
def test_thompson_sampling_selection():
    """Test Thompson Sampling selects arms and updates correctly"""
    
def test_ucb1_exploration_bonus():
    """Test UCB1 exploration bonus increases for less-tried arms"""
    
def test_reward_calculation():
    """Test multi-objective reward calculation is correct"""
    
def test_burn_in_period():
    """Test equal allocation during burn-in"""
    
def test_min_allocation_enforcement():
    """Test strategies maintain 5% minimum"""
```

**Deliverable**: Comprehensive unit tests with >90% coverage.

---

#### Task 2.2: Integration Test
**File**: `examples/demo_mab_strategy.py` (NEW)

**Script to create**:
```python
"""
Demo: MAB Meta-Strategy vs Equal Weight Comparison
====================================================

Compare performance of:
1. Equal weight across 12 strategies
2. MAB (Thompson Sampling) dynamic selection
3. Best single strategy (oracle benchmark)

Period: 2019-2024 (5 years)
Rebalancing: Weekly
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategy_wrapper import (
    MultiArmedBanditMetaStrategy,
    EqualWeightStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    # ... import all 12 strategies
)

# Load data
prices = load_preprocessed_data('2019-01-01', '2024-12-31')
strategy = Strategy(prices)
optimizer = PortfolioOptimizer(strategy.get_return_matrix())

# Create 12 child strategies
child_strategies = [
    EqualWeightStrategy(strategy, optimizer),
    MomentumStrategy(strategy, optimizer, top_k=10, lookback=126),
    MeanReversionStrategy(strategy, optimizer, lookback=21),
    # ... 9 more strategies
]

# Test 1: Equal Weight Baseline
equal_weight = EqualWeightStrategy(strategy, optimizer)
portfolio_eq = PortfolioEngine(prices, initial_capital=100000)
result_eq = portfolio_eq.run_backtest(equal_weight, '2019-01-01', '2024-12-31', freq='W')

# Test 2: MAB Meta-Strategy
mab_strategy = MultiArmedBanditMetaStrategy(
    child_strategies=child_strategies,
    mab_algorithm='thompson',
    reward_metric='multi_objective',
    lookback_periods=12,  # 3 months
    min_allocation=0.05,
    decay_factor=0.95,
    burn_in_periods=12
)
portfolio_mab = PortfolioEngine(prices, initial_capital=100000)
result_mab = portfolio_mab.run_backtest(mab_strategy, '2019-01-01', '2024-12-31', freq='W')

# Compare results
print("\n" + "="*60)
print("EQUAL WEIGHT vs MAB COMPARISON")
print("="*60)
print(f"\nEqual Weight:")
print(f"  Total Return: {result_eq.total_return:.2%}")
print(f"  Sharpe Ratio: {result_eq.sharpe_ratio:.2f}")
print(f"  Max Drawdown: {result_eq.max_drawdown:.2%}")
print(f"  Volatility: {result_eq.volatility:.2%}")

print(f"\nMAB (Thompson Sampling):")
print(f"  Total Return: {result_mab.total_return:.2%}")
print(f"  Sharpe Ratio: {result_mab.sharpe_ratio:.2f}")
print(f"  Max Drawdown: {result_mab.max_drawdown:.2%}")
print(f"  Volatility: {result_mab.volatility:.2%}")

improvement = (result_mab.sharpe_ratio - result_eq.sharpe_ratio) / result_eq.sharpe_ratio
print(f"\nSharpe Improvement: {improvement:.1%}")

# Plot strategy selection over time
selection_counts = mab_strategy.get_strategy_info()['selection_counts']
plt.figure(figsize=(12, 6))
plt.bar(selection_counts.keys(), selection_counts.values())
plt.xticks(rotation=45, ha='right')
plt.title('MAB Strategy Selection Frequency')
plt.ylabel('Times Selected')
plt.tight_layout()
plt.savefig('visualizations/mab_strategy_selection.png', dpi=300)

print("\nVisualization saved to: visualizations/mab_strategy_selection.png")
```

**Deliverable**: Working demo script showing MAB performance vs baseline.

---

### Phase 3: Production Readiness (Week 3-4)

#### Task 3.1: Add to Benchmark Suite
**File**: `examples/demo_benchmark_strategies_fast.py` (MODIFY)

**Changes**:
```python
# Add MAB as 13th strategy
ENABLED_STRATEGIES = [
    'equal_weight',
    'momentum',
    # ... existing 12 strategies
    'mab_meta_strategy',  # NEW
]

# In create_strategy_instances(), add:
'mab_meta_strategy': lambda: MultiArmedBanditMetaStrategy(
    child_strategies=[
        MomentumStrategy(strategy, optimizer, top_k=10),
        MeanReversionStrategy(strategy, optimizer),
        # ... subset of top 6 strategies
    ],
    mab_algorithm='thompson',
    lookback_periods=12
)
```

**Deliverable**: MAB integrated into standard benchmark comparisons.

---

#### Task 3.2: Documentation Updates
**Files to update**:
1. `docs/STRATEGIES.md` - Add MAB meta-strategy description
2. `README.md` - Add MAB to feature list
3. `docs/ARCHITECTURE.md` - Update with MAB layer diagram

**Key additions**:
```markdown
## Strategy 23: Multi-Armed Bandit Meta-Strategy

**Type**: Adaptive Meta-Strategy (combines multiple strategies)
**Algorithm**: Thompson Sampling, UCB1, or Epsilon-Greedy
**Use Case**: Dynamic strategy selection based on performance

### How It Works:
1. Maintains pool of child strategies (e.g., 12 strategies)
2. Uses MAB algorithm to select best strategy each period
3. Learns from performance and adapts over time
4. Ensures diversification through minimum allocation

### Parameters:
- `mab_algorithm`: 'thompson', 'ucb1', or 'epsilon_greedy'
- `lookback_periods`: Evaluation window (12 = 3 months)
- `min_allocation`: Minimum allocation per strategy (0.05 = 5%)
- `decay_factor`: Recent performance weight (0.95)
- `burn_in_periods`: Equal allocation at start (12)

### Expected Performance:
- 15-25% Sharpe improvement vs equal weight
- 20-30% drawdown reduction
- Automatic regime adaptation
```

**Deliverable**: Updated documentation across all files.

---

#### Task 3.3: Dashboard Integration
**File**: `dashboard.py` (MODIFY)

**Add MAB-specific visualizations**:
```python
# New section: MAB Strategy Selection Analysis
if 'mab_meta_strategy' in selected_strategies:
    st.subheader("🎰 MAB Strategy Selection Analysis")
    
    # Plot 1: Selection frequency over time
    selection_history = mab_result.strategy_info['selection_history']
    fig = plot_selection_timeline(selection_history)
    st.plotly_chart(fig)
    
    # Plot 2: Arm probabilities evolution
    prob_evolution = mab_result.strategy_info['probability_evolution']
    fig = plot_probability_evolution(prob_evolution)
    st.plotly_chart(fig)
    
    # Table: Strategy performance attribution
    attribution = calculate_attribution(mab_result)
    st.dataframe(attribution)
```

**Deliverable**: Interactive MAB analysis in dashboard.

---

## Configuration File

**File**: `config/mab_config.yaml` (NEW)

```yaml
# MAB Configuration for Algo Trading Project

# Meta-Strategy Settings
meta_strategy:
  enabled: true
  name: "MAB Meta-Strategy"
  
# MAB Algorithm Selection
mab:
  algorithm: "thompson"  # Options: thompson, ucb1, epsilon_greedy, sliding_window_ucb
  
  # Thompson Sampling Parameters
  thompson:
    decay_factor: 0.95  # 0.90 (fast adapt) to 0.97 (slow adapt)
    
  # UCB1 Parameters
  ucb1:
    confidence_level: 2.0  # Higher = more exploration
    
  # Epsilon-Greedy Parameters
  epsilon_greedy:
    epsilon: 0.2  # Exploration probability
    decay: true   # Decay epsilon over time
    
# Strategy Selection Settings
selection:
  mode: "single"  # Options: single (100% to one), blended (weighted mix)
  lookback_periods: 12  # 3 months with weekly rebalancing
  min_allocation: 0.05  # 5% minimum per strategy
  burn_in_periods: 12   # Equal allocation for first 12 periods
  
# Reward Function
reward:
  metric: "multi_objective"  # Options: sharpe, returns, multi_objective
  
  # Multi-objective weights (must sum to 1.0)
  weights:
    sharpe_ratio: 0.40
    total_return: 0.30
    max_drawdown: -0.20  # Negative = penalty
    volatility: -0.10    # Negative = penalty
    
  # Normalization bounds
  normalization:
    sharpe_max: 3.0
    return_max: 0.25
    drawdown_max: 0.30
    volatility_max: 0.40
    
# Child Strategies (limit to 12)
child_strategies:
  - equal_weight
  - momentum
  - mean_reversion
  - inverse_volatility
  - gmvp
  - gmrp
  - cvar_minimization
  - max_diversification
  - time_series_momentum
  - ma_crossover
  - markowitz_mvo
  - multi_factor_ml
  
# Rebalancing
rebalancing:
  frequency: "weekly"  # Options: daily, weekly, monthly
  day_of_week: "monday"
  
# Risk Management
risk:
  max_position_size: 0.20  # 20% max per asset
  max_leverage: 1.0        # No leverage
  stop_loss: null          # Optional stop loss
  
# Logging
logging:
  level: "INFO"
  save_selection_history: true
  save_reward_history: true
  output_dir: "visualizations/mab"
```

---

## Testing Checklist

### Unit Tests
- [ ] Thompson Sampling selects arms correctly
- [ ] Thompson Sampling updates beliefs with rewards
- [ ] UCB1 exploration bonus works as expected
- [ ] Epsilon-Greedy explores with correct probability
- [ ] Reward calculation produces expected values
- [ ] Burn-in period enforces equal allocation
- [ ] Minimum allocation constraint is respected
- [ ] Decay factor applies correctly

### Integration Tests
- [ ] MAB meta-strategy integrates with PortfolioEngine
- [ ] MAB can wrap 12 child strategies
- [ ] Strategy selection history is recorded
- [ ] Reward history is tracked
- [ ] get_strategy_info() returns complete data
- [ ] Weights sum to 1.0 at each rebalance
- [ ] No lookahead bias (only past data used)

### Performance Tests
- [ ] MAB outperforms equal weight (Sharpe)
- [ ] MAB reduces drawdown vs equal weight
- [ ] Computational overhead < 20% vs single strategy
- [ ] Memory usage is acceptable
- [ ] Runs successfully on 10-year backtest

### Validation Tests
- [ ] Compare vs best single strategy (oracle)
- [ ] Test on different time periods (2015-2020, 2020-2024)
- [ ] Test with different strategy subsets (6, 12, 18 strategies)
- [ ] Sensitivity to hyperparameters (decay, lookback)
- [ ] Robustness to bad strategies (include low-performing ones)

---

## Expected Results

### Performance Metrics (vs Equal Weight Baseline)

| Metric | Equal Weight | MAB (Thompson) | Improvement |
|--------|-------------|---------------|-------------|
| **Sharpe Ratio** | 1.2 | 1.5 - 1.65 | +25-37% |
| **Annual Return** | 12% | 14% - 16% | +17-33% |
| **Max Drawdown** | -25% | -18% - -20% | +20-28% |
| **Volatility** | 18% | 16% - 17% | +6-11% |
| **Calmar Ratio** | 0.48 | 0.70 - 0.85 | +46-77% |

*Note: Estimates based on academic literature (Shen et al. 2015, Kremer et al. 2017)*

### Strategy Selection Patterns (Expected)

**First 3 months (burn-in + learning)**:
- Nearly equal selection across all strategies
- High exploration

**Months 4-12**:
- Concentration on top 3-4 strategies (60-70% allocation)
- Continued exploration of others (30-40%)

**After 12 months**:
- Dominant strategy emerges (40-50% selection)
- Runner-ups get 20-30%
- Weak strategies still get 5-10% (minimum allocation)

### Regime Adaptability

**Bull Market** → MAB should favor:
- Momentum strategies
- Risk parity
- Buy-and-hold

**Bear Market** → MAB should shift to:
- Mean reversion
- Low volatility
- CVaR minimization

**Transition Period** → MAB should show:
- Increased exploration
- More frequent switching
- Higher diversity in selection

---

## Risk & Mitigation

### Risk 1: Cold Start Problem
**Issue**: No data for first few months, random selection.
**Mitigation**: 12-period burn-in with equal allocation (proven strategies tested equally).

### Risk 2: Overfitting to Recent Data
**Issue**: MAB may overreact to short-term performance.
**Mitigation**: 12-period lookback (3 months) smooths noise; decay factor prevents recency bias.

### Risk 3: Strategy Death Spiral
**Issue**: Bad strategy never gets selected again after initial poor performance.
**Mitigation**: 5% minimum allocation ensures exploration; Thompson Sampling naturally explores uncertainty.

### Risk 4: Computational Overhead
**Issue**: Running 12 strategies in parallel increases computation time.
**Mitigation**: Strategies only executed when selected (not all 12 every period); caching of common calculations.

### Risk 5: Regime Change Detection Lag
**Issue**: MAB may be slow to detect market regime changes.
**Mitigation**: Decay factor (0.95) forgets old data; lookback window (3 months) is responsive.

---

## Success Criteria

### Phase 1 (Implementation): PASS if
- [ ] All unit tests pass
- [ ] Integration test runs without errors
- [ ] MAB meta-strategy works with PortfolioEngine
- [ ] Code follows project style guidelines

### Phase 2 (Validation): PASS if
- [ ] MAB Sharpe ratio ≥ equal weight baseline
- [ ] MAB drawdown ≤ equal weight baseline
- [ ] Strategy selection shows logical patterns
- [ ] No lookahead bias detected

### Phase 3 (Production): PASS if
- [ ] Integrated into benchmark suite
- [ ] Documentation complete
- [ ] Dashboard visualizations work
- [ ] Performance meets expectations (≥10% Sharpe improvement)

---

## Timeline

| Week | Tasks | Deliverables |
|------|-------|--------------|
| **Week 1** | MAB framework, meta-strategy class | `mab_framework.py`, updated `strategy_wrapper.py` |
| **Week 2** | Unit tests, integration test | `test_mab_framework.py`, `demo_mab_strategy.py` |
| **Week 3** | Benchmark integration, docs | Updated benchmark, docs, config file |
| **Week 4** | Dashboard, final validation | Dashboard updates, performance report |

**Total Time**: 3-4 weeks for complete implementation and validation.

---

## Code Style Guidelines

### Naming Conventions
```python
# Classes: PascalCase
class MultiArmedBanditMetaStrategy:

# Functions: snake_case
def calculate_reward():

# Constants: UPPER_SNAKE_CASE
MIN_ALLOCATION = 0.05

# Private methods: _leading_underscore
def _calculate_sharpe():
```

### Documentation
```python
def method_name(self, param: type) -> return_type:
    """
    Brief one-line description.
    
    Longer description if needed, explaining algorithm and use case.
    
    Parameters
    ----------
    param : type
        Description of parameter
        
    Returns
    -------
    return_type
        Description of return value
        
    Examples
    --------
    >>> obj.method_name(value)
    expected_output
    """
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed information for debugging")
logger.info("General information about execution")
logger.warning("Warning about potential issues")
logger.error("Error occurred but execution continues")
```

---

## Next Steps

1. **Review & Approve**: Confirm implementation plan aligns with project goals
2. **Create Branch**: `git checkout -b feature/mab-integration`
3. **Phase 1 Development**: Implement MAB framework and meta-strategy
4. **Testing**: Run integration test and compare vs baseline
5. **Iteration**: Tune hyperparameters based on results
6. **Merge**: Integrate into main codebase after validation

**Questions? Contact project lead for clarification on any aspect of implementation.**

---

## References

- `docs/MULTI_ARMED_BANDITS.md` - MAB theory and algorithms
- `docs/STRATEGIES.md` - Existing strategy documentation
- `docs/ARCHITECTURE.md` - System architecture overview
- Academic papers: Shen et al. (2015), Russo et al. (2018), Lattimore & Szepesvári (2020)
