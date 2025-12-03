# Portfolio Engine Architecture

## Overview

The Portfolio Engine is a strategy-agnostic portfolio management system designed for algorithmic trading. It separates concerns between:
1. **Signal Generation** (Strategy class)
2. **Risk Optimization** (Optimizer class)  
3. **Portfolio Execution** (PortfolioEngine class)
4. **Strategy Integration** (StrategyWrapper classes - 20+ strategies)
5. **Advanced Validation** (BacktestingMethods class)

**Current Version:** v3.0 (December 2024)
- 20+ production-ready strategies in `src/strategy_wrapper.py`
- 5 advanced backtesting methods in `src/backtesting_methods.py`
- Comprehensive transaction cost modeling
- Real-time metric calculation

## Design Principles

### 1. Strategy Independence
- Portfolio Engine doesn't know about signals or forecasts
- It only receives target weights and executes them
- Any strategy can plug in via BaseStrategyWrapper interface
- All strategies consolidated in single file (`src/strategy_wrapper.py`)

### 2. Real-Time Metric Calculation
- All metrics calculated during backtest, not after
- Enables realistic strategy decisions based on current state
- Supports adaptive strategies

### 3. Dashboard-Ready Data
- All data structured for immediate visualization
- Pre-calculated rolling metrics
- Easy export to JSON/CSV for dashboards

### 4. Multiple Validation Methods
- 5 backtesting methods for comprehensive validation
- Confidence intervals and statistical testing
- Protection against overfitting

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                    USER CODE                                │
│  - Load data                                                │
│  - Create strategy & optimizer                              │
│  - Run backtest                                             │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│              PORTFOLIO ENGINE                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  run_backtest(strategy_wrapper, dates, freq)         │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                             │
│               ▼                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  For each rebalance date:                            │  │
│  │    1. Build PortfolioState                           │  │
│  │    2. Call strategy_wrapper.get_weights()            │  │
│  │    3. Execute rebalance with costs                   │  │
│  │    4. Update metrics                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│               │                                             │
│               ▼                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Return PortfolioResult with:                        │  │
│  │    - Equity curve                                    │  │
│  │    - Weights history                                 │  │
│  │    - All metrics                                     │  │
│  │    - Dashboard data                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│              STRATEGY WRAPPER                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  get_weights(date, portfolio_state)                  │  │
│  └────────────┬─────────────────────────────────────────┘  │
│               │                                             │
│               ▼                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Call Strategy.generate_signals()                 │  │
│  │  2. Call Optimizer.optimize()                        │  │
│  │  3. Return final weights                             │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬──────────────┬────────────────────────────┘
                 │              │
      ┌──────────▼────┐    ┌────▼──────────┐
      │   STRATEGY    │    │   OPTIMIZER   │
      │ (Signals/ML)  │    │ (Risk Mgmt)   │
      └───────────────┘    └───────────────┘
```

## Core Components

### 1. PortfolioEngine (`src/portfolio_engine.py`)

**Responsibilities:**
- Execute rebalancing with transaction costs & slippage
- Track positions, cash, equity over time
- Calculate comprehensive metrics in real-time
- Export dashboard-ready data

**Key Methods:**
```python
run_backtest(strategy_wrapper, start, end, freq) -> PortfolioResult
get_dashboard_data() -> Dict
_execute_rebalance(date, weights)
_update_metrics(date)
```

**State Tracking:**
- `_equity_curve`: Portfolio value over time
- `_weights_history`: Asset weights at each date
- `_returns_history`: Daily returns
- `_drawdown_series`: Drawdown from peak
- `_rolling_sharpe`, `_rolling_vol`: Rolling metrics
- `_var_series`, `_cvar_series`: Risk metrics

### 2. StrategyWrapper (`src/strategy_wrapper.py`)

**Base Interface:**
```python
class BaseStrategyWrapper(ABC):
    @abstractmethod
    def get_weights(date, portfolio_state) -> pd.Series:
        pass
```

**20+ Pre-Built Strategies:**

**Core Strategies:**
1. **EqualWeightStrategy** - Naive 1/N baseline
2. **BuyAndHoldStrategy** - Passive benchmark
3. **MomentumStrategy** - Trend following with Sharpe optimization
4. **MeanReversionStrategy** - Contrarian with MVO
5. **InverseVolatilityStrategy** - Risk parity

**Risk-Based Strategies:**
6. **GlobalMinimumVarianceStrategy (GMVP)** - Minimum variance portfolio
7. **GMRPStrategy** - Global minimum risk parity
8. **CVaRMinimizationStrategy** - Tail risk minimization
9. **MaximumDiversificationStrategy** - Diversification ratio maximization
10. **MaximumDecorrelationStrategy** - Correlation minimization

**Trend & Momentum:**
11. **TimeSeriesMomentumStrategy** - 12-month absolute momentum
12. **MovingAverageCrossoverStrategy** - 50/200 MA crossover

**Factor & Prediction:**
13. **LinearRegressionStrategy** - Factor-based regression
14. **QuintileFactorStrategy** - Factor quintile portfolios
15. **MarkowitzMVOStrategy** - Mean-variance optimization

**Machine Learning:**
16. **MLRandomForestStrategy** - Random forest predictions
17. **MLGradientBoostingStrategy** - Gradient boosting predictions
18. **MultiFactorMLStrategy** - Multi-factor ML combination

**Advanced:**
19. **RegimeSwitchingStrategy** - Volatility regime detection
20. **ARMAForecastStrategy** - ARMA time series forecasting
21. **ARIMAGARCHForecastingStrategy** - ARIMA-GARCH forecasting

**Strategy Factory:**
```python
from src.strategy_wrapper import list_available_strategies, create_strategy

# List all strategies
strategies = list_available_strategies()  # Returns dict of 20+ strategies

# Create strategy instance
strategy = create_strategy('momentum', strategy_obj, optimizer_obj, lookback=60)
```

### 3. BacktestingMethods (`src/backtesting_methods.py`)

**Five Validation Methods:**
1. **Vanilla Backtest** - Traditional single-run backtest
2. **Walk-Forward Backtest** - Rolling/expanding window with train/test
3. **Cross-Validation Backtest** - K-fold time-series validation
4. **Monte Carlo Backtest** - Bootstrap/parametric simulation
5. **Randomized Backtest** - Random start dates for significance testing

**Key Features:**
- Confidence intervals for all methods
- Statistical significance testing
- Comprehensive comparison framework
- Protection against overfitting

### 4. PortfolioState (Data Structure)

Contains everything a strategy needs to make decisions:

```python
@dataclass
class PortfolioState:
    date: pd.Timestamp
    current_weights: Series        # Current positions
    current_shares: Series         # Actual shares
    cash: float
    equity: float
    price_history: DataFrame       # Full historical prices
    return_history: DataFrame      # Full historical returns
    recent_sharpe: float          # Rolling metrics
    recent_vol: float
    current_drawdown: float
    portfolio_var: float
    portfolio_cvar: float
```

### 4. PortfolioResult (Output)

Complete backtest results:

```python
@dataclass
class PortfolioResult:
    equity_curve: Series
    weights_history: DataFrame
    trades_history: DataFrame
    returns_series: Series
    summary_metrics: Dict
    rolling_metrics: DataFrame
    drawdown_series: Series
    position_pnl: DataFrame
    turnover_history: Series
    transaction_costs: Series
    slippage_costs: Series
    cash_history: Series
    benchmark_comparison: DataFrame
    strategy_name: str
```

## Data Flow

### 1. Initialization Phase
```python
# User creates components
prices = load_data(...)
strategy = Strategy(prices)
optimizer = PortfolioOptimizer(...)
portfolio = PortfolioEngine(prices)
strategy_wrapper = MomentumStrategy(strategy, optimizer, ...)
```

### 2. Backtest Execution
```python
result = portfolio.run_backtest(strategy_wrapper, start, end, freq)
```

**Inside run_backtest:**
```
For each date in backtest:
    If rebalance_date:
        state = build_portfolio_state(date)
        new_weights = strategy_wrapper.get_weights(date, state)
        execute_rebalance(date, new_weights)
    
    update_portfolio_value(date)
    update_metrics(date)

return PortfolioResult(...)
```

### 3. Strategy Execution
```python
def get_weights(date, portfolio_state):
    # 1. Generate signals
    signals = strategy.ml_random_forest_forecast()
    
    # 2. Initial weights from signals
    initial_weights = strategy.generate_initial_weights(
        method='ml_random_forest',
        top_n=10
    )
    
    # 3. Optimize
    final_weights = optimizer.optimize(
        initial_weights,
        objective='cvar',
        alpha=0.95
    )
    
    return final_weights
```

## Key Features

### 1. Transaction Costs & Slippage
```python
turnover = |new_weights - old_weights|
one_way_cost = transaction_cost_bps / 2 / 10000
slippage = slippage_bps / 10000
total_cost = turnover * (one_way_cost + slippage) * portfolio_value
```

### 2. Metric Calculation

**Calculated Daily:**
- Equity, returns, cash
- Drawdown from peak
- Position P&L

**Calculated with Rolling Window:**
- Sharpe ratio (252-day)
- Sortino ratio (252-day)
- Volatility (63-day)
- VaR/CVaR (21-day)

**Calculated at End:**
- Total/annual return
- Max drawdown & duration
- Calmar ratio
- Win rate, profit factor

### 3. Dashboard Data Export

```python
dashboard_data = portfolio.get_dashboard_data()

# Returns dict with:
{
    'equity_curve': Series,
    'weights_history': DataFrame,
    'summary_metrics': Dict,
    'rolling_metrics': DataFrame,
    'drawdown_series': Series,
    'returns_distribution': Series,
    'turnover': Series,
    'costs': {'transaction_costs', 'slippage', 'total'},
    'position_pnl': DataFrame,
    'risk_metrics': {'var_series', 'cvar_series', 'volatility'},
    'trades': DataFrame,
    'cash': Series
}
```

## Extension Points

### Adding New Strategies

1. **Create Strategy Wrapper:**
```python
class MyCustomStrategy(BaseStrategyWrapper):
    def __init__(self, strategy, optimizer, **params):
        super().__init__("My Strategy", strategy, optimizer, **params)
    
    def get_weights(self, date, portfolio_state):
        # Your logic here
        signals = custom_signal_generation()
        weights = optimizer.optimize(signals, ...)
        return weights
```

2. **Use in Backtest:**
```python
my_strategy = MyCustomStrategy(strategy, optimizer, param1=value1)
result = portfolio.run_backtest(my_strategy, ...)
```

### Adding New Metrics

Modify `PortfolioEngine._calculate_summary_metrics()`:
```python
def _calculate_summary_metrics(self):
    metrics = {...}  # existing metrics
    
    # Add custom metric
    metrics['my_custom_metric'] = self._calculate_my_metric()
    
    return metrics
```

## Performance Considerations

### 1. Memory Management
- Price history grows with time
- Use `.loc[]` for efficient slicing
- Consider data windowing for very long backtests

### 2. Computation Speed
- ML models can be slow - cache predictions
- Covariance calculation is O(n²) - use shrinkage
- Vectorize operations where possible

### 3. Optimization
- Daily metric updates are fast (incremental)
- Strategy execution is bottleneck (ML/optimization)
- Consider parallel execution for multiple strategies

## Testing Strategy

### Unit Tests
- Individual component functionality
- Edge cases (empty data, NaN handling)
- Metric calculation accuracy

### Integration Tests
- Full backtest workflow
- Strategy wrapper integration
- Data export correctness

### Performance Tests
- Large dataset handling
- Memory usage
- Execution speed

## Best Practices

### 1. Strategy Development
- Start with simple baseline (Equal Weight)
- Add complexity incrementally
- Always test on out-of-sample data
- Document assumptions

### 2. Parameter Tuning
- Use walk-forward optimization
- Avoid over-fitting to historical data
- Consider transaction costs
- Test robustness across periods

### 3. Production Deployment
- Log all rebalances
- Monitor execution slippage
- Track live vs backtest performance
- Implement circuit breakers

## Common Pitfalls

### 1. Look-Ahead Bias
❌ **Wrong:**
```python
# Uses future data!
mean = prices.mean()  # Includes future prices
```

✅ **Correct:**
```python
# Only uses past data
mean = portfolio_state.price_history.mean()
```

### 2. Survivorship Bias
- Only backtest on assets that existed entire period
- Or handle delisting/additions properly

### 3. Over-fitting
- Too many parameters
- Optimizing on same data used for testing
- Ignoring transaction costs

### 4. Unrealistic Assumptions
- Assuming perfect liquidity
- Ignoring market impact
- Using closing prices (use realistic execution)

## Conclusion

The Portfolio Engine architecture provides:
- ✅ Clean separation of concerns
- ✅ Strategy independence
- ✅ Real-time metrics
- ✅ Dashboard-ready data
- ✅ Easy extensibility
- ✅ Production-ready code

This design enables rapid strategy development and robust backtesting while maintaining code quality and maintainability.
