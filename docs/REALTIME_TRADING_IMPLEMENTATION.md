# Real-Time Trading System Implementation Plan

## Overview

This document outlines the implementation plan for handling daily streaming data and real-time rebalancing decisions while maintaining strategy-agnostic architecture.

**Key Requirements:**
- US market (NYSE/NASDAQ trading calendar)
- End-of-day data arrives after market close (~5 PM ET)
- Forecast next N-day returns/prices
- Execute rebalancing next trading day (T+1)
- Daily checks with conditional rebalancing
- Support both paper and live trading
- Maintain PortfolioEngine strategy independence

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RealTimeOrchestrator                          │
│  Main coordinator: schedules daily tasks, manages workflow       │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ├──────────────┬──────────────┬─────────────┐
                    ▼              ▼              ▼             ▼
         ┌─────────────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
         │ MarketCalendar  │ │DataStream│ │RebalancePolicy│ │StateManager │
         │ - Trading days  │ │- Fetch   │ │- Should      │ │- Persist    │
         │ - Holidays      │ │- Validate│ │  rebalance?  │ │- Load       │
         │ - Next trade    │ │- Features│ │- Config      │ │- Export     │
         └─────────────────┘ └──────────┘ └──────────────┘ └─────────────┘
                    │              │              │
                    └──────────────┴──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
         ┌────────────────────┐        ┌───────────────────┐
         │ StrategyWrapper    │        │ PortfolioEngine   │
         │ (existing)         │        │ (existing + lag)  │
         └────────────────────┘        └───────────────────┘
```

---

## Core Components

### 1. MarketCalendar
**Purpose:** Handle US market trading days, weekends, holidays

**Implementation:**
```python
# src/market_calendar.py
import pandas_market_calendars as mcal

class MarketCalendar:
    def __init__(self, market='NYSE'):
        self.calendar = mcal.get_calendar(market)
        self._cache = {}  # Cache trading days
    
    def is_trading_day(self, date: pd.Timestamp) -> bool:
        """Check if date is valid trading day"""
        
    def next_trading_day(self, date: pd.Timestamp) -> pd.Timestamp:
        """Get next trading day after date (skips weekends/holidays)"""
        
    def previous_trading_day(self, date: pd.Timestamp) -> pd.Timestamp:
        """Get previous trading day"""
        
    def trading_days_between(self, start: pd.Timestamp, end: pd.Timestamp) -> int:
        """Count trading days in range"""
        
    def get_trading_days(self, start: str, end: str) -> pd.DatetimeIndex:
        """Get all trading days in date range"""
```

**Key Points:**
- Use `pandas_market_calendars` library (handles NYSE/NASDAQ holidays automatically)
- Cache results to avoid repeated API calls
- Handle edge cases: early closes (Thanksgiving eve), emergency closures

---

### 2. DataStreamManager
**Purpose:** Fetch, validate, and prepare daily data with feature engineering

**Implementation:**
```python
# src/data_stream_manager.py

class DataStreamManager:
    def __init__(self, assets: List[str], lookback_window: int = 252):
        self.assets = assets
        self.lookback_window = lookback_window
        self._price_buffer = None  # Rolling window of recent prices
        self._feature_cache = None
    
    def fetch_latest_data(self, date: pd.Timestamp) -> Dict[str, Any]:
        """
        Fetch end-of-day data for given date
        Returns: {'prices': Series, 'volume': Series, 'valid': bool}
        """
        
    def validate_data(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate data quality:
        - No missing prices
        - Reasonable price movements (<20% single day)
        - Volume checks
        Returns: (is_valid, error_messages)
        """
        
    def update_price_buffer(self, date: pd.Timestamp, prices: pd.Series):
        """Add new day to rolling price buffer (hybrid approach)"""
        self._price_buffer = pd.concat([
            self._price_buffer.iloc[-(self.lookback_window-1):],
            pd.DataFrame([prices], index=[date])
        ])
    
    def calculate_features(self) -> pd.DataFrame:
        """
        Calculate features on current price buffer
        Uses existing feature_engineering.py functions
        """
        from src.feature_engineering import add_technical_features
        return add_technical_features(self._price_buffer)
    
    def get_latest_features(self) -> pd.Series:
        """Get features for most recent date"""
        features = self.calculate_features()
        return features.iloc[-1]
```

**Key Points:**
- **Hybrid approach**: Keep 252-day rolling window in memory, recalculate features daily
- Reuse existing `feature_engineering.py` functions
- Data validation prevents bad trades on erroneous data
- Handle missing data: skip asset or use forward-fill with warning

**Error Handling:**
- Missing data → Log warning, use last known price or skip asset
- Suspicious data → Alert and require manual confirmation
- Fetch failure → Retry 3x, then skip day and alert

---

### 3. RebalancePolicy
**Purpose:** Decide if rebalancing should occur (strategy-agnostic rules + custom logic)

**Implementation:**
```python
# src/rebalance_policy.py

@dataclass
class RebalancePolicyConfig:
    """Configurable thresholds"""
    weight_drift_threshold: float = 0.10  # 10% total weight drift
    max_days_between: int = 20  # Force rebalance after N days
    min_days_between: int = 1  # Cooldown period
    volatility_spike_threshold: float = 2.0  # Rebalance if vol > 2x normal
    enable_cost_benefit_analysis: bool = True
    cost_benefit_ratio: float = 2.0  # Expected benefit must be 2x cost

class RebalancePolicy:
    def __init__(self, config: RebalancePolicyConfig = None):
        self.config = config or RebalancePolicyConfig()
    
    def should_rebalance(
        self, 
        state: PortfolioState,
        target_weights: pd.Series,
        forecast: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Determine if rebalancing should occur
        Returns: (should_rebalance: bool, reason: str)
        """
        # 1. Cooldown check
        if state.days_since_rebalance < self.config.min_days_between:
            return False, "Cooldown period"
        
        # 2. Force rebalance after max days
        if state.days_since_rebalance >= self.config.max_days_between:
            return True, f"Max days exceeded ({self.config.max_days_between})"
        
        # 3. Weight drift check
        current_weights = state.current_weights.drop('CASH', errors='ignore')
        weight_drift = abs(target_weights - current_weights).sum()
        if weight_drift > self.config.weight_drift_threshold:
            return True, f"Weight drift {weight_drift:.2%}"
        
        # 4. Volatility regime change
        if state.recent_vol > 0:
            historical_vol = 0.15  # TODO: Calculate from history
            vol_ratio = state.recent_vol / historical_vol
            if vol_ratio > self.config.volatility_spike_threshold:
                return True, f"Volatility spike {vol_ratio:.2f}x"
        
        # 5. Cost-benefit analysis (if enabled and forecast available)
        if self.config.enable_cost_benefit_analysis and forecast:
            benefit = self._estimate_benefit(state, target_weights, forecast)
            cost = self._estimate_cost(state, target_weights)
            if benefit > cost * self.config.cost_benefit_ratio:
                return True, f"Positive cost-benefit {benefit:.4f} vs {cost:.4f}"
        
        return False, "No rebalancing condition met"
    
    def _estimate_benefit(self, state, target_weights, forecast) -> float:
        """Estimate expected alpha from rebalancing"""
        # Simple implementation: forecast N-day returns weighted by position change
        pass
    
    def _estimate_cost(self, state, target_weights) -> float:
        """Estimate transaction costs"""
        current_weights = state.current_weights.drop('CASH', errors='ignore')
        turnover = abs(target_weights - current_weights).sum()
        return turnover * (state.equity * 0.0006)  # 6 bps total cost
```

**Strategy-Specific Overrides:**
```python
# Strategies can override default policy
class MomentumStrategy(BaseStrategyWrapper):
    def custom_rebalance_check(self, state, target_weights) -> Tuple[bool, str]:
        """Momentum rebalances monthly only"""
        if state.days_since_rebalance >= 20:
            return True, "Monthly rebalance"
        return False, "Not month-end"
```

**Key Points:**
- Default policy with configurable thresholds
- Strategies can override with custom logic
- Always returns reason (for logging/debugging)
- Cost-benefit analysis is optional but recommended

---

### 4. StateManager
**Purpose:** Persist and load portfolio state for dashboard and recovery

**Implementation:**
```python
# src/state_manager.py

class StateManager:
    def __init__(self, state_dir: str = 'data/realtime_state'):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, date: pd.Timestamp, state: Dict[str, Any]):
        """
        Save current state to JSON
        Structure:
        - current_positions.json: Latest positions, cash, equity
        - daily_metrics.json: Daily append of key metrics
        - full_history.parquet: Complete equity/weights history
        """
        # Current snapshot
        snapshot = {
            'date': date.isoformat(),
            'equity': state['equity'],
            'cash': state['cash'],
            'positions': state['positions'].to_dict(),
            'weights': state['weights'].to_dict(),
            'last_rebalance': state['last_rebalance'].isoformat(),
            'performance': {
                'total_return': state['total_return'],
                'sharpe': state['sharpe'],
                'max_drawdown': state['max_drawdown']
            }
        }
        
        with open(self.state_dir / 'current_state.json', 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        # Append to daily log
        self._append_daily_metrics(date, state)
    
    def load_state(self) -> Optional[Dict]:
        """Load last saved state"""
        state_file = self.state_dir / 'current_state.json'
        if not state_file.exists():
            return None
        
        with open(state_file, 'r') as f:
            return json.load(f)
    
    def export_for_dashboard(self) -> Dict:
        """Export data in dashboard-ready format"""
        # Load full history and format for visualization
        pass
```

**Key Points:**
- JSON for current state (human-readable)
- Parquet for historical data (efficient)
- Atomic writes to prevent corruption
- Dashboard export includes all visualization data

---

### 5. RealTimeOrchestrator
**Purpose:** Main coordinator that runs daily workflow

**Implementation:**
```python
# src/realtime_orchestrator.py

class RealTimeOrchestrator:
    def __init__(
        self,
        strategy_wrapper: BaseStrategyWrapper,
        assets: List[str],
        market_calendar: MarketCalendar,
        initial_capital: float = 1_000_000,
        rebalance_policy: RebalancePolicy = None,
        forecast_horizon: int = 5  # N-day forecast
    ):
        self.strategy = strategy_wrapper
        self.calendar = market_calendar
        self.data_manager = DataStreamManager(assets)
        self.policy = rebalance_policy or RebalancePolicy()
        self.state_manager = StateManager()
        self.forecast_horizon = forecast_horizon
        
        # Initialize or load state
        self._initialize_state(initial_capital)
        
        # Portfolio engine (modified for execution lag)
        self.portfolio = PortfolioEngine(
            prices=None,  # Will be updated dynamically
            initial_capital=initial_capital
        )
    
    def run_daily_cycle(self, date: pd.Timestamp):
        """
        Execute one day's trading cycle
        Called by scheduler (cron job, or loop)
        """
        logger.info(f"=== Daily Cycle: {date.date()} ===")
        
        # 1. Check if trading day
        if not self.calendar.is_trading_day(date):
            logger.info(f"{date.date()} is not a trading day, skipping")
            return
        
        # 2. Fetch latest data (end-of-day T's close)
        try:
            data = self.data_manager.fetch_latest_data(date)
            is_valid, errors = self.data_manager.validate_data(data)
            
            if not is_valid:
                logger.error(f"Invalid data: {errors}")
                # Keep current positions
                return
            
            # Update price buffer
            self.data_manager.update_price_buffer(date, data['prices'])
            
        except Exception as e:
            logger.error(f"Data fetch failed: {e}", exc_info=True)
            return
        
        # 3. Calculate features
        try:
            features = self.data_manager.get_latest_features()
        except Exception as e:
            logger.error(f"Feature calculation failed: {e}")
            return
        
        # 4. Generate forecast for next N days
        try:
            forecast = self.strategy.generate_forecast(
                date, 
                features, 
                horizon=self.forecast_horizon
            )
        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            forecast = None
        
        # 5. Calculate target weights
        state = self._build_current_state(date)
        try:
            target_weights = self.strategy.get_weights(date, state, forecast)
        except Exception as e:
            logger.error(f"Weight calculation failed: {e}")
            target_weights = state.current_weights.drop('CASH', errors='ignore')
        
        # 6. Decide: Should rebalance?
        should_rebal, reason = self.policy.should_rebalance(
            state, target_weights, forecast
        )
        
        logger.info(f"Rebalance decision: {should_rebal} - {reason}")
        
        # 7. If rebalancing, queue for next trading day
        if should_rebal:
            next_trade_date = self.calendar.next_trading_day(date)
            self._queue_rebalance(next_trade_date, target_weights)
            logger.info(f"Rebalance queued for {next_trade_date.date()}")
        
        # 8. Save state
        self.state_manager.save_state(date, self._export_state())
        
        logger.info(f"Daily cycle complete. Equity: ${state.equity:,.2f}")
    
    def execute_queued_trades(self, execution_date: pd.Timestamp):
        """
        Execute trades queued from previous day
        Called at market open of T+1
        """
        if not hasattr(self, '_queued_trades') or not self._queued_trades:
            logger.info(f"No trades queued for {execution_date.date()}")
            return
        
        logger.info(f"Executing {len(self._queued_trades)} rebalances")
        
        # Execute via portfolio engine with T+1 prices
        # ... implementation
        
        self._queued_trades = {}
```

**Key Points:**
- Handles entire daily workflow
- Robust error handling at each step
- Logging for debugging and monitoring
- State persistence for recovery
- Execution lag: decide on T, execute on T+1

---

## PortfolioEngine Modifications

**Add execution_lag parameter to existing `run_backtest`:**

```python
# In src/portfolio_engine.py

def run_backtest(
    self,
    strategy_wrapper: 'BaseStrategyWrapper',
    start_date: str,
    end_date: Optional[str] = None,
    rebalance_freq: str = 'M',
    initial_capital: Optional[float] = None,
    execution_lag: int = 0,  # NEW: 0=same day, 1=next day
    execution_time: str = 'close'  # NEW: 'open' or 'close'
) -> PortfolioResult:
    """
    execution_lag: Days between decision and execution
        0: Decide on T using T's data, execute at T close (current behavior)
        1: Decide on T using T's data, execute at T+1 open/close (realistic)
    
    execution_time: 'open' or 'close' (only relevant if execution_lag > 0)
    """
    # ... existing code ...
    
    # Modified rebalancing logic:
    for i, date in enumerate(backtest_dates):
        if date in rebalance_dates:
            # Generate weights on date T
            new_weights = strategy_wrapper.get_weights(date, state)
            
            if execution_lag > 0:
                # Execute on T+lag day
                execution_date = backtest_dates[i + execution_lag]
                if execution_time == 'open':
                    execution_prices = self._prices.loc[execution_date]
                else:
                    execution_prices = self._prices.loc[execution_date]
                
                # Rebalance at execution date with execution prices
                self._execute_rebalance(execution_date, new_weights)
            else:
                # Execute immediately (current behavior)
                self._execute_rebalance(date, new_weights)
```

**Key Points:**
- Backward compatible (execution_lag=0 is current behavior)
- Simulates realistic T → T+1 lag
- Automatically skips to next trading day if weekend/holiday

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
**Priority: HIGH**

1. **MarketCalendar** (`src/market_calendar.py`)
   - Install: `pip install pandas-market-calendars`
   - Implement all methods
   - Unit tests with known holidays

2. **StateManager** (`src/state_manager.py`)
   - JSON save/load
   - Schema validation
   - Recovery testing

3. **Add execution_lag to PortfolioEngine**
   - Modify `run_backtest` method
   - Test with existing strategies
   - Verify no regression

**Validation:** Run existing backtests with execution_lag=1, compare results

---

### Phase 2: Data Pipeline (Week 2-3)
**Priority: HIGH**

1. **DataStreamManager** (`src/data_stream_manager.py`)
   - Implement fetch_latest_data (use yfinance or your data source)
   - Data validation rules
   - Hybrid feature calculation
   - Handle missing data gracefully

2. **Integrate with feature_engineering.py**
   - Ensure features work on rolling window
   - Test feature consistency: backtest vs real-time

**Validation:** Historical replay - fetch historical data day-by-day, verify features match backtest

---

### Phase 3: Decision Logic (Week 3-4)
**Priority: MEDIUM**

1. **RebalancePolicy** (`src/rebalance_policy.py`)
   - Implement base policy with configurable thresholds
   - Cost-benefit analysis
   - Strategy override mechanism

2. **Update BaseStrategyWrapper**
   - Add optional `generate_forecast()` method
   - Add optional `custom_rebalance_check()` method

**Validation:** Backtest with RebalancePolicy, compare performance vs fixed-frequency

---

### Phase 4: Orchestration (Week 4-5)
**Priority: HIGH**

1. **RealTimeOrchestrator** (`src/realtime_orchestrator.py`)
   - Implement full daily cycle
   - Error handling at each step
   - Logging with different levels

2. **Scheduler Integration**
   - Use `schedule` library or cron
   - Daily trigger at 5:30 PM ET
   - Execution trigger at 9:35 AM ET next day

**Validation:** Paper trading for 1 week, compare vs backtest on same period

---

### Phase 5: Monitoring & Dashboard (Week 5-6)
**Priority: MEDIUM**

1. **Logging System**
   - Structured logging (JSON format)
   - Critical alerts (email/SMS on errors)
   - Performance tracking

2. **Dashboard Integration**
   - Real-time data feed
   - Export format for your dashboard
   - Historical comparison view

3. **Testing & Documentation**
   - Integration tests
   - User guide for deployment
   - Runbook for common issues

---

## Testing Strategy

### 1. Unit Tests
- Each component isolated
- Mock external dependencies
- Edge cases: holidays, missing data, errors

### 2. Integration Tests
- Full pipeline with synthetic data
- Historical replay (fetch data day-by-day from past)
- Compare features: backtest vs real-time

### 3. Paper Trading
- Run live for 2-4 weeks without real money
- Compare vs backtest on same period
- Validate execution timing and costs

### 4. Validation Checklist
```
□ MarketCalendar correctly identifies US holidays
□ Features match between backtest and real-time (±0.01%)
□ Execution lag properly simulates T→T+1 in backtest
□ Rebalance policy triggers expected number of trades
□ State persists correctly across restarts
□ Dashboard displays real-time data
□ Error handling prevents bad trades
□ Logging captures all critical events
```

---

## Deployment Configuration

**Recommended Setup:**

```python
# config/realtime_config.py

REALTIME_CONFIG = {
    'market': 'NYSE',
    'assets': ['AAPL', 'MSFT', 'GOOGL', ...],  # Your universe
    'data_fetch_time': '17:00',  # 5 PM ET
    'execution_time': '09:35',  # 9:35 AM ET next day
    'forecast_horizon': 5,  # 5-day forecast
    'rebalance_policy': {
        'weight_drift_threshold': 0.10,
        'max_days_between': 20,
        'min_days_between': 1,
        'enable_cost_benefit': True
    },
    'logging': {
        'level': 'INFO',
        'file': 'logs/realtime_trading.log',
        'alerts': ['email@example.com']  # Critical alerts
    },
    'state_persistence': {
        'directory': 'data/realtime_state',
        'backup_frequency': 'daily'
    }
}
```

**Scheduler (using `schedule` library):**

```python
# scripts/run_realtime.py

import schedule
import time
from src.realtime_orchestrator import RealTimeOrchestrator

orchestrator = RealTimeOrchestrator(...)

# Daily data fetch and decision
schedule.every().day.at("17:00").do(
    lambda: orchestrator.run_daily_cycle(pd.Timestamp.now())
)

# Execute queued trades
schedule.every().day.at("09:35").do(
    lambda: orchestrator.execute_queued_trades(pd.Timestamp.now())
)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

---

## Key Design Principles

1. **Strategy Agnostic**: PortfolioEngine remains pure execution, all strategy logic in wrappers
2. **Fail-Safe**: Errors → keep current positions, never panic sell
3. **Auditable**: Every decision logged with reasoning
4. **Testable**: Historical replay mode for validation
5. **Recoverable**: State persistence allows restart from any point
6. **Extensible**: Easy to add new data sources, policies, or strategies

---

## Next Steps

1. **Review this plan** - Any modifications needed?
2. **Prioritize phases** - Which components are most critical for your use case?
3. **Set up development environment** - Install dependencies
4. **Start with Phase 1** - MarketCalendar and execution_lag testing
5. **Iterative development** - Build, test, validate each phase before moving on

---

## Questions to Resolve Before Implementation

- [ ] What is your data source? (yfinance, Alpha Vantage, broker API, other?)
- [ ] N-day forecast: What is N for your strategy? (5 days? 10 days?)
- [ ] Do you need intraday monitoring, or just end-of-day?
- [ ] Alert preferences: Email, SMS, dashboard notifications?
- [ ] Backup strategy: If system is down, manual intervention protocol?

---

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Planning Phase - Ready for Implementation
