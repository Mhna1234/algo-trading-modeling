# MAB Integration - Technical Map

**Purpose**: Navigation guide for implementing Multi-Armed Bandit (MAB) meta-strategy  
**Date**: December 15, 2025  
**No code modifications made** - this is a reference document only

---

## 1. Strategy Wrapper Architecture

### 1.1 BaseStrategyWrapper Location

**File**: `src/strategy_wrapper.py`  
**Line**: 62  
**Class Definition**:
```python
class BaseStrategyWrapper(ABC):
```

**Abstract Methods**:
```python
@abstractmethod
def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> pd.Series:
    """
    PRIMARY HOOK POINT FOR MAB INTEGRATION
    
    This is called by PortfolioEngine at each rebalance date.
    
    Parameters:
    - date: Current rebalancing date
    - portfolio_state: PortfolioState object containing:
        * current_weights: Current position weights
        * equity: Current portfolio value
        * price_history: Historical prices up to date
        * return_history: Historical returns up to date
        * recent_sharpe, recent_vol, current_drawdown, etc.
    
    Returns:
    - pd.Series: Asset weights (must sum to ≤ 1.0)
    """
    
@abstractmethod
def get_strategy_info(self) -> Dict[str, Any]:
    """
    Return strategy metadata for logging and diagnostics.
    
    Returns:
    - dict with keys: 'name', 'type', 'parameters'
    """
```

**Constructor Pattern**:
```python
def __init__(self, name: str, strategy, optimizer, **params):
    self.name = name
    self.strategy = strategy
    self.optimizer = optimizer
    self.params = params
```

---

### 1.2 Existing Strategy Wrappers

**File**: `src/strategy_wrapper.py` (single file for all strategies)  
**Total Strategies**: 24 implemented  
**Lines**: 3468 total

**Strategy Implementations** (line ranges):
- `EqualWeightStrategy`: Lines 156-189
- `MomentumStrategy`: Lines 192-264
- `MeanReversionStrategy`: Lines 267-378
- `InverseVolatilityStrategy`: Lines 381-489
- `CVaRMinimizationStrategy`: Lines 492-589
- `GlobalMinimumVarianceStrategy`: Lines 592-712
- `GMRPStrategy`: Lines 715-834
- `RegimeSwitchingStrategy`: Lines 837-1003
- ... and 16 more strategies

**Helper Function**:
```python
def list_available_strategies() -> Dict[str, type]:
    """Line 3371 - Returns dict of all strategy classes"""
```

---

## 2. Portfolio Engine (Execution Layer)

### 2.1 PortfolioEngine Class

**File**: `src/portfolio_engine.py`  
**Line**: 142  
**Class Definition**:
```python
class PortfolioEngine:
```

**Purpose**: Strategy-agnostic portfolio management and backtesting engine.

---

### 2.2 Main Backtest Loop

**Method**: `run_backtest()`  
**Line**: 258  
**Signature**:
```python
def run_backtest(
    self,
    strategy_wrapper: 'BaseStrategyWrapper',
    start_date: str,
    end_date: Optional[str] = None,
    rebalance_freq: str = 'M',
    initial_capital: Optional[float] = None
) -> PortfolioResult:
```

**Key Parameters**:
- `strategy_wrapper`: Instance of BaseStrategyWrapper (YOUR MAB WRAPPER GOES HERE)
- `rebalance_freq`: 'D' (daily), 'W' (weekly), 'M' (monthly), 'Q' (quarterly)

**Loop Structure** (Lines 314-360):
```python
# Run backtest
for i, date in enumerate(backtest_dates):
    # Check if rebalance needed
    if date in rebalance_dates:
        # 1. Build portfolio state
        state = self._build_portfolio_state(date)
        
        # 2. CRITICAL: Get new weights from strategy
        new_weights = strategy_wrapper.get_weights(date, state)
        
        # 3. Execute rebalance
        self._execute_rebalance(date, new_weights)
        self._last_rebalance_date = date
    
    # 4. Update portfolio value and metrics
    self._update_daily(date, new_weights)
```

**HOOK POINT #1**: `strategy_wrapper.get_weights(date, state)` is called at line ~329

---

### 2.3 Rebalancing Schedule

**Method**: `_get_rebalance_dates()`  
**Line**: 394  
**Signature**:
```python
def _get_rebalance_dates(
    self,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    freq: str
) -> List[pd.Timestamp]:
```

**Logic**:
- `'D'`: Every trading day
- `'W'`: Last trading day of each week
- `'M'`: Last trading day of each month (end-of-month)
- `'Q'`: Last trading day of each quarter

**Returns**: List of pd.Timestamp objects when rebalancing should occur.

---

### 2.4 Portfolio State Construction

**Method**: `_build_portfolio_state()`  
**Line**: 417  
**Signature**:
```python
def _build_portfolio_state(self, date: pd.Timestamp) -> PortfolioState:
```

**Returns**: `PortfolioState` object with:
- `date`: Current date
- `current_weights`: Series with current asset + CASH weights
- `current_shares`: Series with actual share holdings
- `equity`: Current portfolio value (float)
- `cash`: Current cash balance (float)
- `price_history`: DataFrame with prices up to `date`
- `return_history`: DataFrame with returns up to `date`
- `recent_sharpe`: Rolling 252-day Sharpe ratio
- `recent_vol`: Rolling 63-day volatility
- `current_drawdown`: Current drawdown from peak
- `portfolio_var`, `portfolio_cvar`: Risk metrics
- `total_return`: Return since inception
- `days_since_rebalance`: Days since last rebalance

**CRITICAL FOR MAB**: This object contains all data needed to:
1. Compute rewards (recent_sharpe, total_return, drawdown, vol)
2. Track performance history (return_history)
3. Calculate realized returns for each strategy

---

### 2.5 Rebalance Execution

**Method**: `_execute_rebalance()`  
**Line**: 466  
**Signature**:
```python
def _execute_rebalance(self, date: pd.Timestamp, target_weights: Series):
```

**Function**: 
1. Converts target weights to share quantities
2. Applies integer share constraints
3. Calculates trades (delta shares)
4. Calculates turnover
5. Applies transaction costs and slippage
6. Updates `_current_shares`, `_current_cash`, `_current_equity`
7. Records costs in `_transaction_costs_series`, `_slippage_costs_series`

**MAB Consideration**: Strategies never directly access execution logic. They only provide weights; PortfolioEngine handles the rest.

---

### 2.6 Daily Portfolio Update

**Method**: `_update_daily()`  
**Line**: 641  
**Signature**:
```python
def _update_daily(self, date: pd.Timestamp, rebalance_weights: Optional[Series]):
```

**Function** (HOOK POINT #2 - Realized Returns):
1. Gets current prices for `date`
2. Calculates position values: `position_values = self._current_shares * current_prices`
3. Calculates total portfolio value: `total_value = position_values.sum() + self._current_cash`
4. **Computes daily return**: `daily_return = (total_value / prev_equity) - 1.0` (Line 654)
5. Records state:
   - `self._equity_curve.loc[date] = total_value`
   - `self._returns_history.loc[date] = daily_return` (CRITICAL FOR REWARDS)
   - `self._weights_history` (actual weights over time)
   - `self._cash_history`, `self._shares_history`
6. Updates rolling metrics:
   - `self._rolling_sharpe` (252-day window)
   - `self._rolling_vol` (63-day window)
   - `self._rolling_sortino` (252-day window)
   - `self._var_series`, `self._cvar_series` (21-day minimum)
7. Calculates drawdown: `drawdown = (total_value / peak) - 1.0`

**CRITICAL FOR MAB REWARD CALCULATION**:
- `self._returns_history`: Contains daily portfolio returns
- `self._equity_curve`: Contains portfolio NAV over time
- These are accessible via `portfolio_state` at next rebalance

**Strategy-Specific Returns**: To compute rewards for **each child strategy independently**, you need to:
1. Track which strategy was selected at each rebalance
2. Calculate "what if" returns: "What would return be if this strategy had 100% allocation?"
3. This requires maintaining separate tracking in `BanditStrategyWrapper`

---

### 2.7 Metrics Calculation

**Method**: `_calculate_summary_metrics()`  
**Line**: 816  
**Signature**:
```python
def _calculate_summary_metrics(self) -> Dict[str, float]:
```

**Returns** (HOOK POINT #3 - Metrics for Rewards):
```python
{
    'total_return': float,
    'annual_return': float,
    'annual_volatility': float,
    'sharpe_ratio': float,
    'sortino_ratio': float,
    'max_drawdown': float,
    'max_drawdown_duration_days': int,
    'calmar_ratio': float,
    'win_rate': float,
    'profit_factor': float,
    'var_95': float,
    'cvar_95': float,
    'total_trades': int,
    'avg_turnover': float,
    'total_transaction_costs': float,
    'total_slippage': float,
    'total_costs': float,
    'final_equity': float,
    'n_trading_days': int
}
```

**Rolling Metrics** (calculated daily):
- `_calculate_rolling_sharpe(window)`: Line 723
- `_calculate_rolling_sortino(window)`: Line 731
- `_calculate_rolling_vol(window)`: Line 740
- `_calculate_var_cvar(alpha)`: Line 754

**MAB Usage**: 
- Use `_returns_history` to calculate rolling Sharpe for each strategy
- Use `_equity_curve` to calculate drawdowns
- Access these via `portfolio_state.return_history` at each rebalance

---

### 2.8 Result Object

**Method**: `_build_result()`  
**Line**: 769  
**Returns**: `PortfolioResult` dataclass

**Contents**:
```python
PortfolioResult(
    equity_curve: pd.Series,
    weights_history: pd.DataFrame,
    trades_history: pd.DataFrame,
    returns_series: pd.Series,          # CRITICAL FOR BACKTEST ANALYSIS
    summary_metrics: Dict[str, float],  # CRITICAL FOR PERFORMANCE COMPARISON
    rolling_metrics: pd.DataFrame,
    drawdown_series: pd.Series,
    position_pnl: pd.DataFrame,
    turnover_history: pd.Series,
    transaction_costs: pd.Series,
    slippage_costs: pd.Series,
    cash_history: pd.Series,
    benchmark_comparison: Optional[pd.DataFrame],
    strategy_name: str
)
```

---

## 3. Demo/Backtest Entry Points

### 3.1 Demo Files Location

**Folder**: `examples/`

**Available Demos**:
- `demo_benchmark_strategies_fast.py` - Weekly rebalancing, 5 years
- `demo_benchmark_strategies.py` - Monthly rebalancing, 10 years
- `demo_12_strategies_fast.py` - Fast comparison of 12 strategies
- `demo_12_strategies_full.py` - Full comparison
- `demo_backtesting_methods.py` - Walk-forward, Monte Carlo, etc.
- `demo_svm_regime_strategy.py` - SVM-based regime switching
- `simple_example.py` - Basic usage example

**Most Relevant for MAB**: `demo_benchmark_strategies_fast.py`

---

### 3.2 Typical Demo Structure

**Example**: `examples/demo_benchmark_strategies_fast.py`

**Flow** (Lines 180-529):
```python
# 1. Load data
from src.data_loader import load_preprocessed_data
_, prices = load_preprocessed_data(start='2019-01-01', end='2024-01-01')

# 2. Create strategy and optimizer instances
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer

strategy = Strategy(prices)
optimizer = PortfolioOptimizer(strategy.get_return_matrix())

# 3. Instantiate child strategies
child_strategies = [
    MomentumStrategy(strategy, optimizer, top_k=10, lookback=126),
    MeanReversionStrategy(strategy, optimizer, lookback=21),
    # ... more strategies
]

# 4. Create portfolio engine
from src.portfolio_engine import PortfolioEngine
portfolio = PortfolioEngine(
    prices, 
    initial_capital=100000,
    transaction_cost_bps=5.0,
    slippage_bps=1.0
)

# 5. Run backtest
result = portfolio.run_backtest(
    strategy_wrapper=momentum_strategy,  # <-- YOUR MAB WRAPPER HERE
    start_date='2019-01-01',
    end_date='2024-01-01',
    rebalance_freq='W'  # Weekly
)

# 6. Access results
print(result.summary_metrics)
print(f"Sharpe: {result.summary_metrics['sharpe_ratio']:.2f}")
result.equity_curve.plot()
```

---

### 3.3 Strategy Registry

**Function**: `list_available_strategies()`  
**File**: `src/strategy_wrapper.py`  
**Line**: 3371

**Returns**: Dictionary mapping strategy names to classes

**Usage in Demos**:
```python
from src.strategy_wrapper import list_available_strategies

# Get all available strategies
strategies = list_available_strategies()

# Validate user-selected strategies
available = list(list_available_strategies().keys())
valid_strategies = [s for s in user_selection if s in available]
```

---

## 4. Implementation Hooks for MAB

### 4.1 Hook Point #1: Compute Weights (Strategy Selection)

**Where**: `BanditStrategyWrapper.get_weights(date, portfolio_state)`  
**Called By**: `PortfolioEngine.run_backtest()` at line ~329  
**Frequency**: Once per rebalance (weekly, monthly, etc.)

**Implementation Pattern**:
```python
class BanditStrategyWrapper(BaseStrategyWrapper):
    def get_weights(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> pd.Series:
        # 1. Calculate rewards from previous period
        if self.has_previous_period():
            rewards = self._calculate_rewards(date, portfolio_state)
            self.bandit_allocator.update_all(rewards)
        
        # 2. Select strategy allocations using MAB
        allocations = self.bandit_allocator.select_allocations()
        
        # 3. Get weights from each child strategy
        child_weights = {}
        for i, strategy in enumerate(self.child_strategies):
            child_weights[i] = strategy.get_weights(date, portfolio_state)
        
        # 4. Aggregate using bandit allocations
        final_weights = self._aggregate(allocations, child_weights)
        
        # 5. Store for next period's reward calculation
        self._store_allocations(date, allocations)
        
        return final_weights
```

---

### 4.2 Hook Point #2: Realized Returns (Reward Calculation)

**Where**: `BanditStrategyWrapper._calculate_rewards()`  
**Data Source**: `portfolio_state.return_history`  
**Timing**: At rebalance time $t$, calculate rewards for period $[t-L, t]$

**Access Points**:
```python
def _calculate_rewards(self, date: pd.Timestamp, portfolio_state: PortfolioState) -> np.ndarray:
    # Get recent returns for lookback window (e.g., 12 weeks)
    recent_returns = portfolio_state.return_history.iloc[-self.lookback_periods:]
    
    # Calculate metrics for each strategy
    rewards = []
    for i, strategy in enumerate(self.child_strategies):
        # Strategy-specific returns (requires separate tracking)
        strategy_returns = self._get_strategy_returns(i, recent_returns)
        
        # Calculate risk-adjusted reward
        mean_return = strategy_returns.mean()
        std_return = strategy_returns.std()
        sharpe = mean_return / (std_return + 1e-10)
        
        # Option 1: Simple Sharpe
        reward = sharpe
        
        # Option 2: Multi-objective (from implementation plan)
        max_dd = self._calculate_max_drawdown(strategy_returns)
        reward = 0.4*sharpe + 0.3*mean_return - 0.2*max_dd - 0.1*std_return
        
        rewards.append(reward)
    
    return np.array(rewards)
```

**Challenge**: PortfolioEngine tracks **aggregate portfolio returns**, not strategy-specific returns.

**Solution**: `BanditStrategyWrapper` must maintain:
```python
self._strategy_tracking = {
    strategy_id: {
        'dates': [],
        'allocations': [],
        'weights': [],
        'hypothetical_returns': []  # What return would be if 100% allocated
    }
}
```

---

### 4.3 Hook Point #3: Metrics Recording (Diagnostics)

**Where**: `BanditStrategyWrapper.get_strategy_info()` and custom diagnostics  
**Called By**: `PortfolioEngine.run_backtest()` at line ~298  
**Purpose**: Logging, dashboard, debugging

**Implementation Pattern**:
```python
def get_strategy_info(self) -> Dict[str, Any]:
    return {
        'name': 'Multi-Armed Bandit Meta-Strategy',
        'type': 'BanditStrategyWrapper',
        'algorithm': self.mab_algorithm,
        'n_strategies': len(self.child_strategies),
        'child_strategies': [s.name for s in self.child_strategies],
        'lookback_periods': self.lookback_periods,
        'min_allocation': self.min_allocation
    }

def get_diagnostics(self) -> Dict[str, Any]:
    """Additional diagnostic information"""
    return {
        'selection_history': self._selection_history,  # [(date, strategy_id, name)]
        'allocation_evolution': self._allocation_history,  # DataFrame
        'reward_history': self._reward_history,  # [(date, strategy_id, reward)]
        'arm_statistics': self.bandit_allocator.get_statistics(),
        'selection_counts': self._get_selection_counts(),
        'current_probabilities': self.bandit_allocator.get_arm_probabilities()
    }
```

---

## 5. Data Flow Summary

### 5.1 Initialization Phase

```
User Code
  ↓
Creates child strategies (Momentum, MeanReversion, etc.)
  ↓
Creates BanditStrategyWrapper(child_strategies, ...)
  ↓
Creates PortfolioEngine(prices, ...)
```

---

### 5.2 Backtest Loop (per rebalance date)

```
PortfolioEngine.run_backtest()
  ↓
For each date in rebalance_dates:
    ↓
    [1] _build_portfolio_state(date) → PortfolioState
        Contains: price_history, return_history, recent_sharpe, etc.
    ↓
    [2] strategy_wrapper.get_weights(date, portfolio_state) → pd.Series
        ↓
        BanditStrategyWrapper:
            a) Calculate rewards from previous period using portfolio_state
            b) Update BanditAllocator with rewards
            c) Get allocations from BanditAllocator
            d) Query each child strategy for weights
            e) Aggregate weights using allocations
            f) Store allocations for next period
            g) Return final weights
    ↓
    [3] _execute_rebalance(date, weights)
        Converts weights to shares, applies costs, updates positions
    ↓
    [4] _update_daily(date, weights)
        Calculates daily returns, updates metrics
        Records in _returns_history, _equity_curve, etc.
    ↓
Next rebalance date (weights at t-1 have now generated returns at t)
```

---

### 5.3 Result Access

```
result = portfolio.run_backtest(...)
  ↓
PortfolioResult object with:
  - result.equity_curve: Portfolio NAV over time
  - result.returns_series: Daily returns
  - result.summary_metrics: Dict with Sharpe, drawdown, etc.
  - result.weights_history: Asset allocation over time
  ↓
MAB-specific diagnostics:
  - bandit_wrapper.get_diagnostics()
  - Contains selection history, allocation evolution, rewards
```

---

## 6. Key Files Reference

| Component | File | Key Lines |
|-----------|------|-----------|
| **BaseStrategyWrapper** | `src/strategy_wrapper.py` | 62-130 |
| **All Strategy Implementations** | `src/strategy_wrapper.py` | 156-3370 |
| **PortfolioEngine** | `src/portfolio_engine.py` | 142-965 |
| **Backtest Loop** | `src/portfolio_engine.py` | 258-360 |
| **Portfolio State** | `src/portfolio_engine.py` | 417-465 |
| **Rebalance Execution** | `src/portfolio_engine.py` | 466-640 |
| **Daily Update (Returns)** | `src/portfolio_engine.py` | 641-721 |
| **Metrics Calculation** | `src/portfolio_engine.py` | 816-887 |
| **Demo Entry Point** | `examples/demo_benchmark_strategies_fast.py` | 180-529 |
| **Data Loading** | `src/data_loader.py` | (entire file) |
| **Signal Generator** | `src/signal_generator.py` | (entire file) |
| **Optimizer** | `src/optimizer.py` | (entire file) |

---

## 7. Critical Observations for MAB Implementation

### 7.1 PortfolioEngine is Strategy-Agnostic
- PortfolioEngine ONLY knows about `BaseStrategyWrapper` interface
- It calls `get_weights()` and executes the result
- All strategy selection logic must be inside `BanditStrategyWrapper`
- PortfolioEngine does NOT need modification

### 7.2 Reward Calculation Challenge
- PortfolioEngine tracks **aggregate portfolio returns**, not per-strategy returns
- `portfolio_state.return_history` contains blended returns from all allocations
- To reward individual strategies, `BanditStrategyWrapper` must:
  1. Track which strategy was allocated what percentage at each date
  2. Calculate "as-if" returns: "What would return be if 100% allocated to strategy k?"
  3. Maintain separate performance history for each child strategy
  4. OR: Use portfolio returns as proxy but weight by allocation percentage

### 7.3 Timing Synchronization
- **t**: Rebalance date, MAB selects allocations
- **[t, t+1]**: Portfolio executes with those allocations
- **t+1**: Next rebalance, rewards calculated using data from [t, t+1]
- **Critical**: Rewards use `portfolio_state.return_history`, which contains past returns up to current date

### 7.4 No Lookahead Bias
- `portfolio_state` only contains data up to current `date`
- `price_history` and `return_history` are sliced at `date`
- PortfolioEngine ensures no future data leakage
- MAB implementation must NOT access future data

### 7.5 Transaction Costs
- PortfolioEngine handles costs automatically
- Turnover is calculated from weight changes
- Costs are deducted from equity in `_execute_rebalance()`
- MAB doesn't need to model costs explicitly (but can consider turnover in rewards)

---

## 8. Implementation Checklist

### Phase 1: Core Components
- [ ] Create `src/bandit_allocator.py` with:
  - [ ] `BanditAllocator` abstract base class
  - [ ] `UCB1Allocator` implementation
  - [ ] `ThompsonSamplingAllocator` implementation
  - [ ] `EpsilonGreedyAllocator` implementation

- [ ] Extend `src/strategy_wrapper.py` with:
  - [ ] `BanditStrategyWrapper(BaseStrategyWrapper)` class
  - [ ] Implements `get_weights(date, portfolio_state)`
  - [ ] Implements `_calculate_rewards(date, portfolio_state)`
  - [ ] Implements `_aggregate_weights(allocations, child_weights)`
  - [ ] Implements `get_diagnostics()`

### Phase 2: Testing
- [ ] Create `tests/test_bandit_allocator.py`
- [ ] Create `tests/test_bandit_strategy_wrapper.py`
- [ ] Create `examples/demo_mab_strategy.py`

### Phase 3: Integration
- [ ] Add to `list_available_strategies()`
- [ ] Update demo scripts
- [ ] Add to dashboard

---

## 9. Quick Start Template

**Minimal Working Example** (conceptual):

```python
# File: examples/demo_mab_minimal.py

from src.data_loader import load_preprocessed_data
from src.portfolio_engine import PortfolioEngine
from src.signal_generator import Strategy
from src.optimizer import PortfolioOptimizer
from src.strategy_wrapper import MomentumStrategy, MeanReversionStrategy
from src.bandit_strategy_wrapper import BanditStrategyWrapper  # NEW

# 1. Load data
_, prices = load_preprocessed_data('2019-01-01', '2024-01-01')

# 2. Create signal generator and optimizer
strategy = Strategy(prices)
optimizer = PortfolioOptimizer(strategy.get_return_matrix())

# 3. Create child strategies
children = [
    MomentumStrategy(strategy, optimizer, top_k=10),
    MeanReversionStrategy(strategy, optimizer, lookback=21)
]

# 4. Create MAB wrapper
mab_strategy = BanditStrategyWrapper(
    child_strategies=children,
    mab_algorithm='ucb',
    reward_metric='risk_adjusted_return',
    lookback_periods=12,
    min_allocation=0.08
)

# 5. Run backtest
portfolio = PortfolioEngine(prices, initial_capital=100000)
result = portfolio.run_backtest(
    strategy_wrapper=mab_strategy,  # MAB wrapper, not individual strategy
    start_date='2019-01-01',
    end_date='2024-01-01',
    rebalance_freq='W'
)

# 6. Analyze results
print(f"Sharpe: {result.summary_metrics['sharpe_ratio']:.2f}")
print(mab_strategy.get_diagnostics()['selection_counts'])
```

---

## 10. Contact & Support

**For questions about**:
- Strategy wrapper interface → See `src/strategy_wrapper.py` lines 62-130
- Portfolio state structure → See `src/portfolio_engine.py` lines 25-75
- Backtest execution flow → See `src/portfolio_engine.py` lines 258-360
- Demo patterns → See `examples/demo_benchmark_strategies_fast.py`

**Next Step**: Begin implementation with Phase 1 (Core Components) from checklist above.

---

**Document Version**: 1.0  
**Created**: December 15, 2025  
**Purpose**: Navigation guide for MAB implementation - NO CODE CHANGES MADE
