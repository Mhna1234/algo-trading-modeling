# MAB Implementation Plan - Algo Trading Project

## Executive Summary

**Objective**: Integrate Multi-Armed Bandit (MAB) framework to dynamically allocate capital across 12 existing strategies, improving risk-adjusted returns through adaptive learning.

**Approach**: Meta-strategy wrapper using Thompson Sampling for strategy selection with single-strategy allocation per rebalancing period.

**Expected Impact**: 15-25% Sharpe ratio improvement, 20-30% drawdown reduction vs. equal-weight baseline.

---

## Project Specifications (Based on Requirements)

### Configuration Parameters
```yaml
Strategy Selection: Option A (100% allocation to single strategy per period)
Evaluation Window: 1-3 months (moderate adaptation)
Exploration Budget: 15-25% (medium risk tolerance)
Cold Start: Equal allocation across all strategies
Minimum Allocation: 5% (never-die policy for diversification)
Number of Strategies: 12 (from current benchmark)
MAB Algorithm: Thompson Sampling (recommended)
Update Frequency: Weekly (aligned with current rebalancing)
Reward Metric: Multi-objective (Sharpe + Returns - Drawdown - Volatility)
```

### Design Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Allocation Mode** | Single strategy (100%) | Simple, clear attribution, lower transaction costs |
| **Algorithm** | Thompson Sampling | No tuning, handles uncertainty, best for non-stationary markets |
| **Adaptation Speed** | Moderate (1-3 months) | Balance responsiveness vs. noise |
| **Exploration** | Medium (15-25%) | Enough to detect regime changes, not wasteful |
| **Diversification** | 5% minimum per strategy | Ensure no strategy fully eliminated (regime changes) |

---

## Architecture Integration

### Current Architecture
```
User Code
    ↓
PortfolioEngine.run_backtest()
    ↓
Individual Strategy Wrapper (e.g., MomentumStrategy)
    ↓
Signal Generator + Optimizer
    ↓
Returns target weights
```

### New Architecture (Non-Invasive)
```
User Code
    ↓
PortfolioEngine.run_backtest()
    ↓
MultiArmedBanditMetaStrategy ← NEW LAYER
    ↓
[Strategy1, Strategy2, ..., Strategy12] ← EXISTING
    ↓
MAB selects best strategy dynamically
    ↓
Returns selected strategy's weights
```

**Key Benefit**: Zero changes to existing code. MAB is just another strategy wrapper.

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
