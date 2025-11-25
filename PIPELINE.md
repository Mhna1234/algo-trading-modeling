# Trading System Pipeline Documentation

**Last Updated:** November 2025

This document provides a comprehensive overview of the algorithmic trading system's execution pipeline, data flow, and component interactions.

## 📋 Table of Contents

1. [Pipeline Overview](#pipeline-overview)
2. [Data Flow Architecture](#data-flow-architecture)
3. [Component Interactions](#component-interactions)
4. [Execution Stages](#execution-stages)
5. [Configuration System](#configuration-system)
6. [Portfolio Management Flow](#portfolio-management-flow)
7. [Error Handling & Fallbacks](#error-handling--fallbacks)
8. [Performance Optimization](#performance-optimization)

---

## Pipeline Overview

The trading system follows a sequential pipeline architecture that transforms raw market data into actionable portfolio weights and performance analytics.

### High-Level Pipeline Flow

```
┌─────────────────────┐
│   Configuration     │
│    (config.yaml)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  1. Data Loading    │◄─── yfinance API
│  (data_loader.py)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Feature Eng.     │
│ (feature_eng.py)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. Forecasting      │
│ (forecasting.py)    │
│ ARIMA + GARCH       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. Signal Gen.      │
│ (signal_gen.py)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. Portfolio Opt.   │
│ (portfolio_mgr.py)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 6. Backtesting      │
│ (portfolio.py)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 7. Evaluation       │
│ (evaluator.py)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 8. Visualization    │
│   & Reporting       │
└─────────────────────┘
```

---

## Data Flow Architecture

### 1. Input Layer: Market Data

**Module:** `src/data_loader.py`

**Inputs:**
- Ticker symbols (e.g., AAPL, MSFT, SPY)
- Date range (start_date, end_date)
- Benchmark ticker

**Process:**
```python
load_data(tickers, start, end)
├── Download OHLCV data from yfinance
├── Handle missing data (forward fill, interpolation)
├── Align dates across all assets
└── Return: (full_data, price_data)
```

**Outputs:**
- `full_data`: Complete OHLCV DataFrame
- `price_data`: Adjusted close prices only
- Cached data for faster subsequent runs

**Data Quality Checks:**
- Missing value detection and imputation
- Outlier detection (>3 std deviations)
- Date alignment across assets
- Minimum data requirements (20+ days)

---

### 2. Feature Layer: Technical Indicators

**Module:** `src/feature_engineering.py`

**Inputs:** Price data (DataFrame)

**Process:**
```python
make_features(prices)
├── Returns calculation (log & simple)
├── Moving averages (MA, EMA)
├── Technical indicators
│   ├── RSI (Relative Strength Index)
│   ├── MACD (Moving Average Convergence Divergence)
│   └── Bollinger Bands
├── Statistical features
│   ├── Rolling volatility
│   ├── Skewness & Kurtosis
│   └── Correlation matrix
└── Momentum indicators
```

**Outputs:**
- `returns`: Daily returns DataFrame
- `ma_short`, `ma_long`: Moving averages
- `rsi`: RSI indicator
- `macd`, `macd_signal`: MACD indicators
- `volatility`: Rolling volatility
- `correlation`: Asset correlation matrix

**Feature Parameters:**
- MA windows: 20, 50, 200 days
- RSI period: 14 days
- MACD: (12, 26, 9) parameters
- Volatility window: 20 days

---

### 3. Forecasting Layer: Time Series Models

**Module:** `src/forecasting.py`

**Class:** `ARIMAGARCHForecaster`

**Inputs:**
- Historical returns (DataFrame)
- Forecast horizon (default: 1 day)

**Process:**
```python
ARIMAGARCHForecaster.forecast_portfolio(returns, steps)
├── For each asset:
│   ├── ARIMA model fitting
│   │   ├── Auto order selection (AIC)
│   │   ├── Parameter estimation
│   │   └── Mean forecast generation
│   └── GARCH model fitting
│       ├── Volatility modeling
│       ├── Parameter estimation
│       └── Volatility forecast
└── Combine forecasts
```

**Outputs:**
- `mean_forecasts`: Expected return forecasts (DataFrame)
- `vol_forecasts`: Volatility forecasts (DataFrame)

**Model Parameters:**
- ARIMA order: (1, 0, 1) or auto-selected
- GARCH order: (1, 1)
- Minimum data requirement: 30 observations
- Forecast steps: 1-5 days ahead

**Fallback Strategy:**
If model fails: Use historical mean/std as forecasts

---

### 4. Signal Layer: Trading Signals

**Module:** `src/signal_generator.py`

**Class:** `SignalGenerator`

**Inputs:**
- Price data
- Technical indicators
- Forecasts (optional)

**Process:**
```python
SignalGenerator.generate_signals(data, strategies)
├── MA Crossover signals
│   └── Short MA crosses Long MA
├── MACD signals
│   └── MACD line crosses signal line
├── RSI signals
│   ├── Oversold (RSI < 30): Buy
│   └── Overbought (RSI > 70): Sell
├── Forecast-based signals
│   └── Positive forecast: Buy weight
└── Combine signals (weighted average)
```

**Outputs:**
- `signals`: DataFrame of trading signals (-1 to +1)
  - +1: Strong buy
  - 0: Neutral
  - -1: Strong sell

**Signal Parameters:**
- Signal threshold: 0.0 (configurable)
- Volatility scaling: On/Off
- Signal smoothing: 3-day window
- Strategy weights: Equal or custom

---

### 5. Portfolio Layer: Weight Optimization

**Module:** `src/portfolio_manager.py`

**Classes:**
- `ForecastManager`: Forecast-driven optimization
- `SignalManager`: Signal-driven weights
- `ConfigManager`: Configuration translation

**Inputs:**
- Forecasts (mean & volatility)
- Signals
- Historical data
- Optimization parameters

**Process:**

#### ForecastManager Flow:
```python
ForecastManager.generate_weights_from_forecasts()
├── Create forecast rule
├── For each rebalancing date:
│   ├── Get forecast window
│   ├── Run ARIMA-GARCH forecasts
│   ├── Apply optimization method:
│   │   ├── Tangency (Max Sharpe)
│   │   ├── Target Return MVO
│   │   └── Risk Parity
│   └── Apply constraints
│       ├── Long-only
│       ├── Leverage cap
│       └── Position limits
└── Return: target_weights (DataFrame)
```

#### SignalManager Flow:
```python
SignalManager.generate_weights_from_signals()
├── Create signal rule
├── For each rebalancing date:
│   ├── Filter signals by threshold
│   ├── Weight by signal strength
│   └── Normalize to sum = 1
└── Return: target_weights (DataFrame)
```

**Outputs:**
- `target_weights`: Time series of portfolio weights

**Optimization Methods:**
1. **Tangency Portfolio:**
   - Maximize: Sharpe Ratio
   - Formula: `max (μ - rf) / √(w'Σw)`

2. **Target Return MVO:**
   - Target: Specified return
   - Formula: `min w'Σw s.t. w'μ >= target`

3. **Risk Parity:**
   - Equal risk contribution
   - Formula: `w_i ∝ 1/σ_i`

---

### 6. Backtesting Layer: Portfolio Execution

**Module:** `src/portfolio.py`

**Class:** `Portfolio`

**Inputs:**
- Price data
- Target weights
- Initial capital
- Cost parameters

**Process:**
```python
Portfolio.rebalance(target_weights, initial_equity)
├── Initialize portfolio
│   ├── Cash position
│   └── Initial weights
├── For each trading day:
│   ├── Check rebalancing schedule
│   ├── If rebalancing date:
│   │   ├── Calculate trades needed
│   │   ├── Apply transaction costs
│   │   ├── Apply slippage
│   │   └── Update positions
│   ├── Calculate daily returns
│   ├── Update portfolio value
│   └── Track metrics
└── Compute performance analytics
```

**Cost Modeling:**
- Transaction costs: 10 bps (default)
- Slippage: 2 bps (default)
- Bid-ask spread modeling
- Realistic execution simulation

**Outputs:**
- `PortfolioResult` containing:
  - Equity curve (NAV over time)
  - Portfolio weights history
  - Trading activity
  - Performance metrics

**Rebalancing Frequencies:**
- Daily (D)
- Weekly (W)
- Monthly (M) - Default
- Quarterly (Q)

---

### 7. Evaluation Layer: Performance Analytics

**Module:** `src/evaluator.py`

**Class:** `PerformanceEvaluator`

**Inputs:**
- Portfolio returns
- Benchmark returns
- Risk-free rate

**Process:**
```python
PerformanceEvaluator.generate_report()
├── Return Metrics
│   ├── Total return
│   ├── Annualized return (CAGR)
│   └── Excess return vs benchmark
├── Risk Metrics
│   ├── Volatility (annualized std)
│   ├── Maximum drawdown
│   ├── VaR (95%)
│   ├── CVaR (95%)
│   └── Downside deviation
├── Risk-Adjusted Metrics
│   ├── Sharpe ratio
│   ├── Sortino ratio
│   ├── Calmar ratio
│   └── Information ratio
└── Benchmark Comparison
    ├── Beta
    ├── Alpha
    └── Tracking error
```

**Outputs:**
- Formatted performance report (string)
- Metrics dictionary
- Comparison tables

**Key Metrics Formulas:**

**Sharpe Ratio:**
```
SR = (R_p - R_f) / σ_p
```

**Sortino Ratio:**
```
Sortino = (R_p - R_f) / σ_downside
```

**Maximum Drawdown:**
```
MDD = max((Peak_t - Trough_t) / Peak_t)
```

**Information Ratio:**
```
IR = (R_p - R_b) / TE
where TE = tracking error
```

---

### 8. Visualization Layer: Analytics & Reporting

**Module:** `visualize_portfolio.py`

**Inputs:**
- BacktestResult
- Price data
- Benchmark data

**Process:**
```python
Visualization Pipeline
├── Equity Curves
│   ├── Portfolio NAV
│   ├── Benchmark NAV
│   └── Performance annotations
├── Portfolio Weights
│   ├── Stacked area chart
│   └── Average allocation bars
├── Risk Analytics
│   ├── Drawdown chart
│   ├── Rolling volatility
│   ├── Rolling Sharpe
│   └── Cumulative returns
├── Trading Activity
│   ├── Daily turnover
│   └── Cumulative trades
├── Correlation Analysis
│   ├── Correlation heatmap
│   └── Rolling correlations
└── Monthly Returns
    └── Calendar heatmap
```

**Outputs:**
- High-resolution PNG files (300 DPI)
- Interactive plots (optional)
- Performance dashboard

---

## Component Interactions

### Module Dependencies

```
utils.py (TradingConfig)
    │
    ├──► data_loader.py
    │       │
    │       ▼
    ├──► feature_engineering.py
    │       │
    │       ▼
    ├──► forecasting.py
    │       │
    │       ▼
    ├──► signal_generator.py
    │       │
    │       ▼
    ├──► portfolio_manager.py
    │       │
    │       ▼
    ├──► portfolio.py
    │       │
    │       ▼
    ├──► evaluator.py
    │       │
    │       ▼
    └──► visualize_portfolio.py
```

### Data Passing Between Components

1. **Data Loader → Feature Engineering**
   - Price data (DataFrame)
   - OHLCV data (optional)

2. **Feature Engineering → Forecasting**
   - Returns (DataFrame)
   - Volatility (Series)

3. **Forecasting → Signal Generation**
   - Mean forecasts (DataFrame)
   - Volatility forecasts (DataFrame)

4. **Forecasting + Signals → Portfolio Manager**
   - Mean/vol forecasts
   - Signal data
   - Configuration

5. **Portfolio Manager → Portfolio**
   - Target weights (DataFrame)
   - Price data
   - Configuration

6. **Portfolio → Evaluator**
   - PortfolioResult object
   - Benchmark data

7. **All → Visualization**
   - Complete backtest results
   - Price history
   - Performance metrics

---

## Execution Stages

### Stage 1: Initialization

```python
# Load configuration
config = TradingConfig()
config.tickers = ['AAPL', 'MSFT', 'GOOGL']
config.start_date = '2020-01-01'
config.end_date = '2024-01-01'

# Initialize pipeline
pipeline = AlgorithmicTradingPipeline(config)
```

**Duration:** < 1 second

---

### Stage 2: Data Acquisition

```python
pipeline.load_and_prepare_data()
```

**Operations:**
- Download data from yfinance
- Clean and align data
- Load benchmark
- Cache results

**Duration:** 5-30 seconds (depending on data range)

---

### Stage 3: Feature Engineering

```python
pipeline.engineer_features()
```

**Operations:**
- Calculate returns
- Compute technical indicators
- Calculate statistical features

**Duration:** 1-5 seconds

---

### Stage 4: Forecasting

```python
pipeline.generate_forecasts()
```

**Operations:**
- Fit ARIMA models (per asset)
- Fit GARCH models (per asset)
- Generate forecasts

**Duration:** 10-60 seconds (depending on assets)

---

### Stage 5: Signal Generation

```python
pipeline.generate_trading_signals()
```

**Operations:**
- Calculate strategy signals
- Combine multiple strategies
- Apply thresholds

**Duration:** 1-3 seconds

---

### Stage 6: Portfolio Optimization

```python
pipeline.optimize_portfolio()
```

**Operations:**
- Initialize Portfolio class
- Create ForecastManager/SignalManager
- Generate target weights
- Apply constraints

**Duration:** 5-20 seconds

---

### Stage 7: Backtesting

```python
pipeline.run_backtest()
```

**Operations:**
- Simulate trading
- Apply costs and slippage
- Calculate daily returns
- Track positions

**Duration:** 2-10 seconds

---

### Stage 8: Evaluation & Reporting

```python
pipeline.evaluate_performance()
pipeline.plot_results()
```

**Operations:**
- Calculate performance metrics
- Generate report
- Create visualizations

**Duration:** 2-5 seconds

---

## Configuration System

### TradingConfig Structure

```python
@dataclass
class TradingConfig:
    # Data parameters
    tickers: List[str]
    start_date: str
    end_date: str
    benchmark: str
    
    # Model parameters
    arima_order: Tuple[int, int, int]
    garch_order: Tuple[int, int]
    auto_order_selection: bool
    forecast_horizon: int
    
    # Signal parameters
    signal_threshold: float
    volatility_scaling: bool
    signal_smoothing: bool
    smoothing_window: int
    
    # Portfolio parameters
    optimization_method: str  # 'sharpe', 'mean_variance', 'risk_parity'
    risk_free_rate: float
    max_weight: float
    min_weight: float
    transaction_cost: float
    slippage_bps: float
    rebalance_frequency: str  # 'daily', 'weekly', 'monthly', 'quarterly'
    
    # Backtesting parameters
    initial_capital: float
    use_portfolio_class: bool
    long_only: bool
    leverage_cap: float
    
    # Advanced parameters
    lookback_window: int
    ridge_regularization: float
    min_var_regularization: float
    cash_symbol: str
```

### Configuration Files

**YAML Format:**
```yaml
# config.yaml
tickers: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
start_date: '2020-01-01'
end_date: '2024-01-01'
benchmark: 'SPY'

optimization_method: 'sharpe'
rebalance_frequency: 'monthly'
initial_capital: 100000.0
transaction_cost: 0.001
slippage_bps: 2.0
```

**Loading:**
```python
config = TradingConfig.load('config.yaml')
```

---

## Portfolio Management Flow

### Detailed ForecastManager Workflow

```
Input: Forecaster, Configuration
│
├─► Create Forecast Rule
│   │
│   └─► Rule Function(date, past_returns)
│       │
│       ├─► Get historical data window
│       │
│       ├─► Generate ARIMA-GARCH forecasts
│       │   ├─► Mean forecast (expected returns)
│       │   └─► Volatility forecast
│       │
│       ├─► Apply optimization
│       │   ├─► If 'tangency': Maximize Sharpe
│       │   ├─► If 'mean_variance': Target return
│       │   └─► If 'risk_parity': Equal risk
│       │
│       └─► Apply constraints
│           ├─► Long-only check
│           ├─► Leverage cap
│           └─► Position limits
│
├─► Build Target Weights Schedule
│   │
│   └─► For each rebalancing date:
│       ├─► Apply rule function
│       ├─► Validate weights (sum = 1)
│       └─► Store in DataFrame
│
└─► Output: target_weights (DataFrame)
```

### SignalManager Integration

```
Input: Signals Data, Configuration
│
├─► Create Signal Rule
│   │
│   └─► Rule Function(date, past_returns)
│       │
│       ├─► Get signals for date
│       │
│       ├─► Filter by threshold
│       │
│       ├─► Weight by signal strength
│       │   ├─► Normalize signal magnitudes
│       │   └─► Proportional allocation
│       │
│       └─► Distribute remaining weight
│
├─► Build Target Weights Schedule
│   │
│   └─► For each rebalancing date:
│       └─► Apply signal rule
│
└─► Output: target_weights (DataFrame)
```

---

## Error Handling & Fallbacks

### Data Loading Errors

**Problem:** Missing data, API failures

**Fallback:**
1. Use cached data if available
2. Forward-fill missing values
3. Skip problematic tickers
4. Log warnings

### Forecasting Errors

**Problem:** Model convergence failures

**Fallback:**
1. Use historical mean/std
2. Try simpler model orders
3. Reduce data requirements
4. Equal weight portfolio

### Optimization Errors

**Problem:** Numerical instability, infeasible constraints

**Fallback:**
1. Add ridge regularization
2. Relax constraints slightly
3. Use equal weights
4. Log error and continue

### Backtest Errors

**Problem:** Data misalignment, weight issues

**Fallback:**
1. Align dates carefully
2. Forward-fill weights
3. Default to equal weights
4. Continue with available data

---

## Performance Optimization

### Computational Bottlenecks

1. **ARIMA-GARCH Fitting:** 60-70% of runtime
   - **Optimization:** Parallel processing per asset
   - **Caching:** Store fitted models

2. **Weight Optimization:** 15-20% of runtime
   - **Optimization:** Use closed-form solutions
   - **Avoid:** Iterative solvers when possible

3. **Data Loading:** 10-15% of runtime
   - **Optimization:** Caching system
   - **Batch downloads:** Multiple tickers at once

### Memory Management

- **Lazy loading:** Load data only when needed
- **Efficient data types:** Use appropriate dtypes
- **Garbage collection:** Clear unused DataFrames
- **Chunking:** Process large datasets in chunks

### Scalability

**Current System:**
- Assets: Up to 50 (tested)
- Time period: Up to 10 years
- Rebalancing: Monthly recommended

**Scaling Strategies:**
- Use database for historical data
- Implement incremental updates
- Parallelize across assets
- Use GPU for matrix operations (advanced)

---

## Pipeline Execution Example

### Complete Run

```bash
python main.py --tickers AAPL MSFT GOOGL AMZN SPY \
               --start 2020-01-01 \
               --end 2024-01-01 \
               --method sharpe \
               --rebalance monthly
```

**Console Output:**
```
============================================================
Starting full algorithmic trading pipeline
============================================================

[INFO] Loading data for ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
[INFO] Date range: 2020-01-01 to 2024-01-01
[TIMING] load_and_prepare_data completed in 8.23s
[INFO] Loaded data: 1008 days, 5 assets

[INFO] Computing technical indicators and features
[TIMING] engineer_features completed in 2.15s
[INFO] Generated 12 feature sets

[INFO] Generating ARIMA+GARCH forecasts
[TIMING] generate_forecasts completed in 45.67s
[INFO] Generated forecasts for 5 assets

[INFO] Generating trading signals
[INFO] Strategies: ['ma_crossover', 'macd', 'rsi', 'forecast']
[TIMING] generate_trading_signals completed in 1.89s
[INFO] Generated 3421 non-zero signals

[INFO] Optimizing portfolio weights
[INFO] Using Portfolio class for optimization
[TIMING] optimize_portfolio completed in 12.34s
[INFO] Generated Portfolio class weights for 48 periods

[INFO] Running backtest simulation
[INFO] Using new Portfolio class for backtesting
[TIMING] run_backtest completed in 3.56s
[INFO] Backtest completed successfully

[INFO] Evaluating strategy performance
[TIMING] evaluate_performance completed in 1.23s

============================================================
PERFORMANCE REPORT: ARIMA-GARCH Algorithmic Strategy
============================================================

BASIC PERFORMANCE METRICS
------------------------------
Total Return................. 45.67%
Annualized Return............ 18.23%
Volatility................... 16.45%
Sharpe Ratio................. 1.108
Max Drawdown................. -12.34%
Calmar Ratio................. 1.477

... [full report] ...

[INFO] Generating result plots
[TIMING] plot_results completed in 2.78s

============================================================
PIPELINE EXECUTION SUMMARY
============================================================
Strategy completed successfully!
Total Return: 45.67%
Sharpe Ratio: 1.108
============================================================

Total pipeline execution time: 78.34s
```

---

## Troubleshooting Guide

### Common Issues

1. **Import Errors**
   - Solution: Install all dependencies from `requirements.txt`
   - Check Python version (3.8+)

2. **Data Download Failures**
   - Solution: Check internet connection
   - Verify ticker symbols are valid
   - Try reducing date range

3. **Memory Errors**
   - Solution: Reduce number of assets
   - Decrease lookback window
   - Use shorter time period

4. **Slow Performance**
   - Solution: Enable caching
   - Use monthly rebalancing
   - Reduce forecast complexity

5. **Numerical Warnings**
   - Solution: Increase regularization
   - Check for data quality issues
   - Review constraint settings

---

## Best Practices

### Pipeline Configuration

1. **Start small:** Test with 3-5 assets first
2. **Monthly rebalancing:** Good balance of performance and costs
3. **Realistic costs:** Use 10-20 bps transaction costs
4. **Lookback period:** 60-252 days for covariance
5. **Ridge regularization:** ~1e-4 for numerical stability

### Data Management

1. **Cache data:** Speeds up repeated runs
2. **Quality checks:** Always validate input data
3. **Benchmark selection:** Use appropriate market index
4. **Date alignment:** Ensure all assets have common dates

### Model Selection

1. **ARIMA orders:** (1,0,1) is a good starting point
2. **GARCH orders:** (1,1) is standard
3. **Auto-selection:** Enable for best fit
4. **Forecast horizon:** 1-day for daily rebalancing

### Optimization

1. **Method selection:**
   - `sharpe`: Best for risk-adjusted returns
   - `mean_variance`: When you have target return
   - `risk_parity`: For balanced risk exposure

2. **Constraints:**
   - `long_only`: True for most strategies
   - `leverage_cap`: 1.0 for unleveraged
   - `max_weight`: 0.3-0.4 to avoid concentration

---

## Summary

The algorithmic trading pipeline provides a complete, production-ready system for:

✅ **Data Management:** Robust loading and preprocessing  
✅ **Feature Engineering:** Comprehensive technical indicators  
✅ **Forecasting:** ARIMA-GARCH time series models  
✅ **Signal Generation:** Multiple strategy integration  
✅ **Portfolio Optimization:** Advanced optimization methods  
✅ **Backtesting:** Realistic cost modeling  
✅ **Evaluation:** Comprehensive performance analytics  
✅ **Visualization:** Professional reporting and charts  

The modular design allows easy customization and extension while maintaining reliability and performance.

---

**For more information, see:**
- [README.md](README.md) - System overview and installation
- [PORTFOLIO_MANAGEMENT.md](PORTFOLIO_MANAGEMENT.md) - Portfolio management system details

**Questions or Issues?**
- Check the troubleshooting section
- Review component documentation
- Examine log files for detailed error messages
