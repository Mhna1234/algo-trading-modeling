# Module Organization Guide

This document clarifies the roles and responsibilities of key modules in the trading system to avoid code duplication and maintain clear separation of concerns.

## Core Data & Feature Modules

### `feature_engineering.py` - Technical Indicator Computation
**Role:** CANONICAL source for technical indicator computation

**Responsibilities:**
- Compute raw technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Calculate statistical features for ML models
- Provide consistent, well-tested implementations
- Output DataFrames with indicator VALUES (not signals)

**NOT responsible for:**
- Generating trading signals (that's signal_generator.py)
- Portfolio optimization (that's optimizer.py)
- Backtesting (that's portfolio_engine.py)

**Example:**
```python
from src.feature_engineering import FeatureEngineer

fe = FeatureEngineer()
rsi = fe.compute_rsi(prices, period=14)  # Returns RSI values (0-100)
macd = fe.compute_macd(prices)  # Returns MACD line, signal, histogram
```

---

### `signal_generator.py` - Signal Generation & Data Container
**Role:** Converts indicators to trading signals AND serves as data container

**Responsibilities:**
- **Data Container:** Holds price/return data for strategy wrappers
- **Signal Generation:** Converts indicators to trading signals (-1, 0, +1)
- **Initial Weights:** Generates initial portfolio weights
- **Data Access:** Provides return matrices, covariance, etc. to strategies

**Key distinction:**
- `feature_engineering.py` computes RSI values → `[45, 32, 68, ...]`
- `signal_generator.py` converts to signals → `[0, +1, -1, ...]`

**Example:**
```python
from src.signal_generator import StrategySignalGenerator

# Create data container
strategy = StrategySignalGenerator(prices)

# Generate signals (not raw indicators)
rsi_signals = strategy.mean_reversion_rsi()  # Returns signals: -1, 0, +1
macd_signals = strategy.momentum_macd()  # Returns signals: -1, 0, +1

# Access data methods
returns = strategy.get_return_matrix()
cov = strategy.get_covariance_matrix()
```

---

## Strategy & Optimization Modules

### `strategies/` folder - Trading Strategy Implementations
**Role:** High-level trading strategies that combine signals + optimization

**Contains:**
- `base_strategy_wrapper.py` - Abstract base class
- `benchmark_strategies.py` - 12 validated production strategies
- `advanced_strategies.py` - 13 experimental/ML strategies
- `bandit_strategy_wrapper.py` - Multi-armed bandit meta-strategy

**Responsibilities:**
- Use `signal_generator` for data access and signals
- Use `optimizer` for portfolio optimization
- Implement complete trading logic: signal → optimize → weights

**Example:**
```python
from src.strategies import MomentumStrategy
from src.signal_generator import StrategySignalGenerator
from src.optimizer import PortfolioOptimizer

strategy = StrategySignalGenerator(prices)  # Data container
optimizer = PortfolioOptimizer()

momentum = MomentumStrategy(strategy, optimizer, top_k=10)
weights = momentum.get_weights(date, portfolio_state)
```

---

### `optimizer.py` - Portfolio Optimization
**Role:** Convert raw signals/forecasts into optimal portfolio weights

**Responsibilities:**
- Risk-based optimization (CVaR, Sharpe, MVO, Risk Parity)
- Apply constraints (long-only, max weight, etc.)
- Handle numerical issues in optimization

**Example:**
```python
from src.optimizer import PortfolioOptimizer

optimizer = PortfolioOptimizer()
optimal_weights = optimizer.optimize(
    initial_weights,
    objective='cvar',
    alpha=0.95,
    long_only=True,
    returns_data=returns_window
)
```

---

## Execution & Backtesting Modules

### `portfolio_engine.py` - Portfolio Management & Backtesting
**Role:** Execute strategies and manage portfolio lifecycle

**Responsibilities:**
- Run backtests with transaction costs and rebalancing
- Track portfolio state (NAV, positions, cash)
- Calculate performance metrics
- Handle position management

### `backtester.py` - Legacy Compatibility Wrapper
**Role:** Backward compatibility with old API

**Status:** Maintained for compatibility, use `portfolio_engine.py` for new code

### `backtesting_methods.py` - Advanced Backtesting Methods
**Role:** Walk-forward, k-fold cross-validation, expanding window

---

## Data & Utilities

### `data_loader.py` - Data Loading & Preprocessing
- Download price data
- Clean and preprocess
- Save/load processed data

### `utils.py` - Helper Functions
- Performance metrics (Sharpe, Sortino, etc.)
- Date utilities
- Configuration management

---

## Decision Tree: Which Module to Use?

```
Need to compute technical indicators (RSI, MACD)?
├─ YES → feature_engineering.py (FeatureEngineer)
└─ NO
   └─ Need to generate trading signals from indicators?
      ├─ YES → signal_generator.py (StrategySignalGenerator)
      └─ NO
         └─ Need to optimize portfolio weights?
            ├─ YES → optimizer.py (PortfolioOptimizer)
            └─ NO
               └─ Need complete trading strategy?
                  ├─ YES → strategies/ (MomentumStrategy, etc.)
                  └─ NO
                     └─ Need to backtest?
                        └─ YES → portfolio_engine.py
```

---

## Common Patterns

### Pattern 1: Using Pre-computed Indicators in Signals
```python
# Compute indicators (feature engineering)
fe = FeatureEngineer()
rsi_values = fe.compute_rsi(prices)

# Convert to signals (signal generation)
signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
signals[rsi_values < 30] = 1  # Oversold
signals[rsi_values > 70] = -1  # Overbought
```

### Pattern 2: Complete Strategy Pipeline
```python
# 1. Data container
strategy = StrategySignalGenerator(prices)

# 2. Optimizer
optimizer = PortfolioOptimizer()

# 3. Strategy
momentum = MomentumStrategy(strategy, optimizer, top_k=10)

# 4. Backtest
engine = PortfolioEngine(prices)
result = engine.run_backtest(
    strategy_wrapper=momentum,
    start_date='2020-01-01',
    rebalance_frequency='monthly'
)
```

### Pattern 3: Custom Strategy with FeatureEngineer
```python
class MyCustomStrategy(BaseStrategyWrapper):
    def get_weights(self, date, portfolio_state):
        # Use FeatureEngineer for complex indicators
        fe = FeatureEngineer()
        rsi = fe.compute_rsi(self.strategy.prices)
        macd = fe.compute_macd(self.strategy.prices)
        
        # Custom signal logic
        signals = combine_indicators(rsi, macd)
        
        # Optimize
        weights = self.optimizer.optimize(signals)
        return weights
```

---

## Summary

| Module | Purpose | Output |
|--------|---------|--------|
| `feature_engineering.py` | Compute indicators | Indicator values (DataFrames) |
| `signal_generator.py` | Generate signals + data container | Trading signals (-1, 0, +1) |
| `optimizer.py` | Optimize portfolios | Portfolio weights (0-1) |
| `strategies/` | Complete strategies | Portfolio weights (0-1) |
| `portfolio_engine.py` | Execute & backtest | Performance results |

**Key Principle:** Each module has ONE clear responsibility. No duplication!
