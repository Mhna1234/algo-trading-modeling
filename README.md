# 🚀 Algorithmic Trading & Portfolio Optimization System

A comprehensive, production-grade Python framework for algorithmic trading research and backtesting. This system integrates time-series forecasting, technical analysis, portfolio optimization, and performance evaluation in a modular, extensible architecture.

**Last Updated:** November 2025

## 🏗️ System Architecture

```
algo-trading-modeling/
│
├── data/                           # Data storage
│   ├── raw/                        # Raw downloaded data
│   └── processed/                  # Cleaned and processed data
│
├── src/                           # Core modules
│   ├── data_loader.py             # Data download & preprocessing
│   ├── feature_engineering.py     # Technical indicators & features
│   ├── forecasting.py             # ARIMA + GARCH forecasting
│   ├── signal_generator.py        # Trading signal generation
│   ├── optimizer.py               # Legacy portfolio optimization
│   ├── portfolio.py               # Advanced Portfolio class
│   ├── portfolio_manager.py       # Portfolio management system (NEW)
│   ├── portfolio_optimization.py  # Portfolio optimization methods
│   ├── backtester.py              # Legacy backtesting engine
│   ├── evaluator.py               # Performance evaluation
│   └── utils.py                   # Helper functions & config
│
├── notebooks/                     # Jupyter notebooks
│   └── exploratory_analysis.ipynb # Data exploration & analysis
│
├── main.py                        # Main pipeline orchestrator
├── visualize_portfolio.py         # Portfolio visualization dashboard (NEW)
├── test_portfolio_integration.py  # Integration tests (NEW)
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── PIPELINE.md                    # Pipeline documentation (NEW)
└── PORTFOLIO_MANAGEMENT.md        # Portfolio system documentation (NEW)
```

## 🎯 Key Features

### 📊 **Data Pipeline**
- **Multi-source data loading** via yfinance with robust error handling
- **Automatic data cleaning** and missing value imputation
- **Risk-free rate integration** for performance calculations
- **Efficient caching system** for faster subsequent runs

### 🔧 **Feature Engineering**
- **Technical Indicators**: MA, EMA, RSI, MACD, Bollinger Bands
- **Statistical Features**: Rolling volatility, skewness, kurtosis
- **Momentum Indicators**: Multi-period momentum calculations
- **Correlation Analysis**: Asset correlation matrices
- **Custom Feature Support**: Extensible framework for new indicators

### 🔮 **Time Series Forecasting**
- **ARIMA Models**: Autoregressive Integrated Moving Average
- **GARCH Models**: Volatility forecasting with GARCH(p,q)
- **Combined ARIMA-GARCH**: Mean and volatility forecasting
- **Automatic Order Selection**: AIC-based model selection
- **Multi-step Forecasting**: Configurable forecast horizons

### 📡 **Signal Generation**
- **Momentum Signals**: MA crossovers, MACD signals
- **Mean-Reversion Signals**: RSI, Bollinger Band strategies
- **Forecast-based Signals**: Using ARIMA-GARCH predictions
- **Volatility Breakout**: Volatility-based signal generation
- **Signal Combination**: Weighted ensemble of multiple strategies
- **Custom Strategy Support**: Easy integration of new signal generators

### 📈 **Advanced Portfolio Class** (NEW)
- **Tangency Portfolio**: Maximum Sharpe ratio optimization
- **Target Return MVO**: Mean-variance with target return constraints
- **Risk Parity**: Equal risk contribution portfolios
- **Rule-Based Construction**: Flexible custom portfolio rules
- **Cash Management**: Explicit cash position modeling with risk-free returns
- **Pure Python Implementation**: No external optimization dependencies required
- **Transaction Cost & Slippage**: Realistic cost modeling built-in

### 🔄 **Dual Backtesting Systems**
- **New Portfolio Class** (Default):
  - Comprehensive transaction cost and slippage modeling
  - Flexible rebalancing schedules (daily, weekly, monthly, quarterly)
  - Multiple optimization methods without external dependencies
  - Enhanced performance analytics
- **Legacy Backtester** (Optional):
  - Original implementation with cvxpy/PyPortfolioOpt support
  - Backward compatibility maintained
  - Available via `--use-legacy-backtester` flag

### 📊 **Performance Evaluation & Visualization**
- **Risk Metrics**: Sharpe, Sortino, Calmar ratios, CAGR
- **Drawdown Analysis**: Maximum drawdown, recovery periods
- **Value at Risk**: VaR and Conditional VaR calculations
- **Statistical Tests**: Significance testing vs benchmarks
- **Rolling Analytics**: Time-varying performance metrics
- **Comprehensive Visualizations** (NEW):
  - Interactive equity curves with benchmark comparison
  - Portfolio weight allocation over time
  - Risk analytics (drawdowns, volatility, rolling metrics)
  - Trading activity and turnover analysis
  - Correlation heatmaps and rolling correlations
  - Monthly returns heatmap

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Git

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd algo-trading-modeling

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

Core packages installed:
- **Data & Analysis**: pandas, numpy, scipy
- **Financial Data**: yfinance, pandas-datareader  
- **Time Series**: statsmodels, arch (GARCH)
- **Optimization**: cvxpy (optional), PyPortfolioOpt (optional)
  - *Note: New Portfolio class eliminates need for external optimizers*
- **Machine Learning**: scikit-learn, river
- **Reinforcement Learning**: gymnasium, stable-baselines3, torch
- **Visualization**: matplotlib, seaborn, plotly
- **Configuration**: pyyaml
- **Development**: jupyter, pytest, black, flake8
- **Utilities**: tqdm, python-dotenv

## 🚀 Quick Start

### Basic Usage

```bash
# Run with default settings (uses new Portfolio class)
python main.py

# Custom tickers and date range
python main.py --tickers AAPL MSFT GOOGL AMZN SPY --start 2020-01-01 --end 2024-01-01

# Different optimization methods
python main.py --method sharpe --rebalance monthly

# Use legacy backtester (optional)
python main.py --use-legacy-backtester

# Custom configuration file
python main.py --config my_config.yaml

# Generate comprehensive visualizations
python visualize_portfolio.py
```

### Command Line Options

```bash
python main.py [OPTIONS]

Options:
  --config PATH                     Configuration file path (.yaml or .json)
  --tickers [TICKERS ...]           List of ticker symbols (default: AAPL MSFT SPY QQQ IWM)
  --start DATE                      Start date YYYY-MM-DD (default: 2020-01-01)
  --end DATE                        End date YYYY-MM-DD (default: 2024-01-01)
  --benchmark TICKER                Benchmark ticker (default: SPY)
  --method {sharpe,mean_variance,risk_parity}  Optimization method
  --rebalance {daily,weekly,monthly,quarterly}  Rebalancing frequency
  --log-level {DEBUG,INFO,WARNING,ERROR}        Logging verbosity
  --no-plots                        Skip plot generation
  --use-legacy-backtester           Use legacy backtester instead of Portfolio class (NEW)
```

### Programmatic Usage

#### Using the Full Pipeline

```python
from src.utils import TradingConfig
from main import AlgorithmicTradingPipeline

# Create configuration
config = TradingConfig()
config.tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
config.start_date = '2020-01-01'
config.end_date = '2024-01-01'
config.optimization_method = 'sharpe'
config.rebalance_frequency = 'monthly'
config.use_portfolio_class = True  # Use new Portfolio class (default)

# Run pipeline
pipeline = AlgorithmicTradingPipeline(config)
results = pipeline.run_full_pipeline()

# Access results
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.3f}")
print(f"Max Drawdown: {results.max_drawdown:.2%}")
```

#### Using Portfolio Class Directly (NEW)

```python
from src.portfolio import Portfolio
import pandas as pd

# Load price data
prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)

# Initialize Portfolio
portfolio = Portfolio(
    prices=prices,
    rf=0.02/252,  # 2% annual risk-free rate (daily)
    trading_cost_bps=10.0,  # 10 basis points trading costs
    slippage_bps=2.0  # 2 basis points slippage
)

# Create equal weight strategy
equal_weight_rule = portfolio.equal_weight_rule()
weights = portfolio.build_target_weights_from_rule(
    rule=equal_weight_rule,
    schedule='M'  # Monthly rebalancing
)

# Run backtest
result = portfolio.rebalance(weights, initial_equity=100000)
print(f"Annual Return: {result.perf['ann_return']:.2%}")
print(f"Sharpe Ratio: {result.perf['sharpe']:.3f}")
print(f"Max Drawdown: {result.perf['max_drawdown']:.2%}")
```

## 🧮 Mathematical Framework

### Time Series Forecasting

**ARIMA(p,d,q) Model:**
```
r_t = φ₁r_{t-1} + φ₂r_{t-2} + ... + φₚr_{t-p} + θ₁ε_{t-1} + ... + θₑε_{t-q} + ε_t
```

**GARCH(p,q) Model:**
```
σ²_t = ω + α₁ε²_{t-1} + ... + αₚε²_{t-p} + β₁σ²_{t-1} + ... + βₑσ²_{t-q}
```

### Portfolio Optimization

**Sharpe Ratio Maximization:**
```
max (w^T μ - R_f) / √(w^T Σ w)
s.t. Σw_i = 1, w_min ≤ w_i ≤ w_max
```

**Mean-Variance Optimization:**
```
max w^T μ - λ w^T Σ w
s.t. Σw_i = 1, w_i ≥ 0
```

### Performance Metrics

**Sharpe Ratio:**
```
SR = (E[R] - R_f) / σ(R)
```

**Maximum Drawdown:**
```
MDD = max{(Peak_t - Trough_t) / Peak_t}
```

**Information Ratio:**
```
IR = E[R - R_benchmark] / σ(R - R_benchmark)
```

## 📝 Configuration

### Configuration File Example (config.yaml)

```yaml
# Data parameters
start_date: '2020-01-01'
end_date: '2024-01-01'
tickers: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY']
benchmark: 'SPY'

# Model parameters
arima_order: [1, 0, 1]
garch_order: [1, 1]
auto_order_selection: true
forecast_horizon: 1

# Signal parameters
signal_threshold: 0.0
volatility_scaling: true
signal_smoothing: true
smoothing_window: 3

# Portfolio parameters
optimization_method: 'sharpe'
risk_free_rate: 0.02
max_weight: 0.3
min_weight: 0.0
transaction_cost: 0.001
rebalance_frequency: 'monthly'

# Backtesting parameters
initial_capital: 100000.0
```

## 📊 Example Output

```
============================================================
PERFORMANCE REPORT: ARIMA-GARCH Algorithmic Strategy
============================================================

BASIC PERFORMANCE METRICS
------------------------------
Total Return................. 15.23%
Annualized Return............ 12.45%
Volatility................... 14.67%
Sharpe Ratio................. 0.847
Max Drawdown................. -8.34%
Calmar Ratio................. 1.492
Benchmark Return............. 10.12%
Excess Return................ 2.33%
Information Ratio............ 0.421

RISK METRICS
------------------------------
VaR 95%...................... -2.14%
CVaR 95%..................... -3.28%
Sortino Ratio................ 1.234
Downside Deviation........... 10.89%

DRAWDOWN ANALYSIS
------------------------------
Maximum Drawdown............. -8.34%
Number of DD Periods......... 3
Average Drawdown............. -3.21%
Average DD Duration.......... 23.4 days
============================================================
```

## 🧪 Testing & Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_backtester.py
```

### Code Quality

```bash
# Format code
black src/ main.py

# Lint code
flake8 src/ main.py

# Type checking (optional)
mypy src/
```

## 🔧 Extending the System

### Adding New Indicators

```python
# In feature_engineering.py
def compute_custom_indicator(self, prices, **kwargs):
    # Your indicator logic here
    return indicator_values

# Usage in pipeline
features['custom_indicator'] = engineer.compute_custom_indicator(prices)
```

### Adding New Optimization Methods

```python
# In optimizer.py
def custom_optimization(self, expected_returns, cov_matrix, **kwargs):
    # Your optimization logic here
    return optimal_weights

# Usage
optimizer.optimize_portfolio_forecasted(
    mean_forecast, cov_matrix, method='custom'
)
```

### Adding New Signal Strategies

```python
# In signal_generator.py
def custom_strategy_signals(self, data, **kwargs):
    # Your signal generation logic here
    return signals

# Usage
signal_generator.generate_signals(
    data, strategies=['custom_strategy']
)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes
- Include unit tests for new functionality
- Update documentation for any API changes

## 📋 Roadmap

### Current Features ✅
- [x] Data loading and preprocessing
- [x] Technical indicator computation
- [x] ARIMA + GARCH forecasting
- [x] Signal generation framework
- [x] Portfolio optimization (dual systems)
- [x] Advanced Portfolio class with multiple optimization methods
- [x] Backtesting engine (legacy and new)
- [x] Performance evaluation
- [x] Comprehensive visualization dashboard
- [x] Portfolio class integration with adapters
- [x] Comprehensive documentation
- [x] Integration testing suite

### Planned Features 🚧
- [ ] Black-Litterman optimization integration
- [ ] Advanced online learning models
- [ ] Reinforcement learning agents
- [ ] Real-time trading simulation
- [ ] Live trading API integration
- [ ] Alternative data integration
- [ ] Multi-asset class support (equities, bonds, commodities)
- [ ] Options and derivatives modeling
- [ ] ESG factor integration
- [ ] Performance attribution analysis
- [ ] Interactive web dashboard

## ⚠️ Disclaimers

**Important Notice**: This software is for educational and research purposes only. It is not intended as financial advice or for actual trading. Past performance does not guarantee future results.

**Risk Warning**: Trading and investing involve substantial risk of loss. The authors and contributors are not responsible for any financial losses incurred through the use of this software.

**No Financial Advice**: This system is a research tool and should not be used as the sole basis for investment decisions. Always consult with qualified financial professionals.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Financial Data**: Powered by [yfinance](https://github.com/ranaroussi/yfinance)
- **Optimization**: Built with [CVXPY](https://www.cvxpy.org/) and [PyPortfolioOpt](https://pyportfolioopt.readthedocs.io/)
- **Time Series**: Using [statsmodels](https://www.statsmodels.org/) and [ARCH](https://arch.readthedocs.io/)
- **Machine Learning**: Leveraging [scikit-learn](https://scikit-learn.org/) and [River](https://riverml.xyz/)

## 📞 Support

For questions, issues, or contributions:

1. **Documentation**: Check this README and inline code documentation
2. **Issues**: Open an issue on GitHub with detailed description
3. **Discussions**: Use GitHub Discussions for general questions
4. **Pull Requests**: Contributions are welcome!

---

**Happy Trading! 📈**