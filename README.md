# 🚀 Algorithmic Trading & Portfolio Management System

A comprehensive, production-grade Python framework for algorithmic trading strategy development, backtesting, and portfolio management. This system features a **strategy-agnostic portfolio engine** with **10 pre-built trading strategies** ranging from basic (equal weight) to advanced (ML/DL models), complete with visualization dashboards and performance analytics.

**Version:** 2.0.0  
**Last Updated:** January 2025

## 🎯 What's New in v2.0

### 🏗️ **Strategy-Agnostic Portfolio Engine**
The new architecture separates strategy logic from portfolio execution:
- **PortfolioEngine**: Manages rebalancing, costs, metrics, and state
- **StrategyWrapper**: Abstract interface for pluggable strategies
- **Backward Compatibility**: Legacy code still works via adapter layer

### 📦 **10 Pre-Built Strategies**

**Basic Strategies:**
1. **Equal Weight**: Simple 1/N portfolio
2. **Momentum**: Price momentum with mean reversion filter
3. **Mean Reversion**: Z-score based reversion trading
4. **Inverse Volatility**: Risk parity approach

**Advanced Strategies:**
5. **CVaR Minimization**: Downside risk optimization
6. **Regime Switching**: Market regime detection (bull/bear/sideways)
7. **ML Random Forest**: Random Forest return predictions
8. **ML Gradient Boosting**: Gradient Boosting return predictions
9. **ARMA Forecast**: ARIMA time series forecasting
10. **Multi-Factor ML**: Ensemble of ML models with multiple factors

### 📊 **Real-Time Dashboard Support**
Pre-calculated metrics ready for visualization:
- Equity curves and returns
- Portfolio weights over time
- Drawdown analysis
- Rolling Sharpe/volatility
- Trade history
- VaR/CVaR tracking

### 🚀 **Quick Start Examples**
```python
# New API - Strategy-Agnostic
from src import PortfolioEngine, MomentumStrategy

strategy = MomentumStrategy(lookback=60)
engine = PortfolioEngine(prices, strategy)
result = engine.run_backtest()

# Access pre-calculated metrics
print(f"Sharpe: {result.metrics['sharpe_ratio']:.2f}")
print(f"Return: {result.metrics['total_return']:.2%}")

# Export for dashboard
dashboard_data = engine.get_dashboard_data()
```

See `examples/` folder for complete demonstrations.

## 🏗️ System Architecture

```
algo-trading-modeling/
│
├── src/                           # Core modules
│   ├── portfolio_engine.py        # Strategy-agnostic portfolio engine (NEW v2.0)
│   ├── strategy_wrapper.py        # 10 pre-built strategies (NEW v2.0)
│   ├── strategy.py                # Signal generation & ML/DL models
│   ├── optimizer.py               # Portfolio optimization algorithms
│   ├── backtester.py              # Legacy backtester (backward compatible)
│   ├── evaluator.py               # Performance evaluation
│   ├── data_loader.py             # Data download & preprocessing
│   ├── feature_engineering.py     # Technical indicators & features
│   ├── forecasting.py             # ARIMA + GARCH forecasting
│   ├── signal_generator.py        # Trading signal generation
│   ├── portfolio.py               # Advanced Portfolio class
│   ├── portfolio_adapter.py       # Legacy adapter for backward compatibility
│   ├── portfolio_manager.py       # Portfolio management system
│   ├── portfolio_optimization.py  # Portfolio optimization methods
│   └── utils.py                   # Helper functions & config
│
├── examples/                      # Example scripts (NEW v2.0)
│   ├── demo_all_strategies.py     # Demo all 10 strategies with comparison
│   └── simple_example.py          # Quick-start guide
│
├── tests/                         # Test suite (NEW v2.0)
│   └── test_portfolio_engine.py   # Unit & integration tests
│
├── docs/                          # Documentation (NEW v2.0)
│   ├── ARCHITECTURE.md            # System architecture & design
│   └── STRATEGIES.md              # Complete strategy guide (all 10)
│
├── visualizations/                # Visualization outputs
│   ├── *.png                      # Generated charts
│   └── README.md                  # Visualization documentation
│
├── data/                          # Data storage
│   ├── raw/                       # Raw downloaded data
│   └── processed/                 # Cleaned and processed data
│
├── notebooks/                     # Jupyter notebooks
│   └── exploratory_analysis.ipynb # Data exploration & analysis
│
├── main.py                        # Main pipeline orchestrator
├── visualize_portfolio.py         # Portfolio visualization dashboard
├── test_portfolio_integration.py  # Integration tests
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── PIPELINE.md                    # Pipeline documentation
├── PORTFOLIO_MANAGEMENT.md        # Portfolio system documentation
└── PORTFOLIO_INTEGRATION.md       # Integration guide
```

## 🎯 Key Features

### 🏗️ **Strategy-Agnostic Portfolio Engine** (NEW v2.0)
- **Modular Design**: Strategies are pluggable via abstract interface
- **Pre-Calculated Metrics**: All metrics computed during backtest (not after)
- **Dashboard Ready**: Structured data export for real-time visualization
- **Transaction Costs**: Realistic modeling of costs and slippage
- **State Management**: Comprehensive tracking of portfolio state over time

### 📦 **10 Pre-Built Trading Strategies** (NEW v2.0)

**Basic Strategies** (Easy to understand and implement):
- **Equal Weight**: 1/N portfolio (baseline strategy)
- **Momentum**: Buy winners, sell losers with mean reversion filter
- **Mean Reversion**: Z-score based contrarian trading
- **Inverse Volatility**: Risk parity / minimum volatility approach

**Advanced Strategies** (Incorporating ML/DL/Time Series):
- **CVaR Minimization**: Downside risk optimization using CVaR
- **Regime Switching**: Market regime detection with regime-specific portfolios
- **ML Random Forest**: Random Forest predictions for expected returns
- **ML Gradient Boosting**: Gradient Boosting for return forecasting
- **ARMA Forecast**: ARIMA time series forecasting
- **Multi-Factor ML**: Ensemble of ML models with multiple technical factors

See `docs/STRATEGIES.md` for complete documentation on all strategies.

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

Core packages:
- **Data & Analysis**: pandas, numpy, scipy, yfinance, pandas-datareader
- **Machine Learning**: scikit-learn, river, torch
- **Time Series**: statsmodels, arch (GARCH)
- **Optimization**: cvxpy, PyPortfolioOpt (optional for legacy code)
- **Visualization**: matplotlib, seaborn, plotly
- **Testing**: pytest, pytest-cov
- **Utilities**: pyyaml, tqdm, python-dotenv

## 🚀 Quick Start

### Running Example Scripts

The fastest way to see the system in action:

```bash
# Demo all 10 strategies with performance comparison
python examples/demo_all_strategies.py

# Simple momentum strategy example
python examples/simple_example.py
```

Both scripts will:
- Load sample data (AAPL, MSFT, GOOGL, AMZN, SPY)
- Run backtests
- Generate comprehensive visualizations
- Save charts to `visualizations/` folder

### Programmatic Usage - New API (v2.0)

#### Strategy-Agnostic Engine

```python
from src import PortfolioEngine, MomentumStrategy
import pandas as pd

# Load price data
prices = pd.read_csv('prices.csv', index_col=0, parse_dates=True)

# Create strategy
strategy = MomentumStrategy(
    lookback=60,           # 60-day momentum
    reversion_threshold=2.0,  # Mean reversion filter
    volatility_lookback=20
)

# Initialize engine
engine = PortfolioEngine(
    prices=prices,
    strategy=strategy,
    initial_capital=100000,
    transaction_cost=0.001,  # 10 bps
    slippage=0.0005         # 5 bps
)

# Run backtest
result = engine.run_backtest()

# Access results
print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.3f}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")

# Get dashboard data
dashboard_data = engine.get_dashboard_data()
print(dashboard_data.keys())
# ['equity_curve', 'weights_history', 'returns', 'metrics', 
#  'rolling_metrics', 'trades', 'drawdown', 'var_cvar']
```

#### Using Different Strategies

```python
from src import (
    EqualWeightStrategy,
    MeanReversionStrategy,
    MLRandomForestStrategy,
    CVaRMinimizationStrategy,
    create_strategy  # Factory function
)

# Equal Weight (Baseline)
strategy = EqualWeightStrategy()

# Mean Reversion
strategy = MeanReversionStrategy(
    lookback=20,
    entry_threshold=2.0,
    exit_threshold=0.5
)

# Machine Learning
strategy = MLRandomForestStrategy(
    lookback=60,
    n_estimators=100,
    max_depth=5
)

# CVaR Minimization
strategy = CVaRMinimizationStrategy(
    lookback=60,
    confidence_level=0.95,
    target_return=0.10
)

# Or use factory
strategy = create_strategy(
    'momentum',
    lookback=60,
    reversion_threshold=2.0
)
```

#### Comparing Multiple Strategies

```python
from src import PortfolioEngine, Evaluator

strategies = {
    'Equal Weight': EqualWeightStrategy(),
    'Momentum': MomentumStrategy(lookback=60),
    'Mean Reversion': MeanReversionStrategy(lookback=20),
    'ML Random Forest': MLRandomForestStrategy(lookback=60)
}

results = {}
for name, strategy in strategies.items():
    engine = PortfolioEngine(prices, strategy)
    results[name] = engine.run_backtest()

# Compare performance
evaluator = Evaluator()
comparison = evaluator.compare_strategies(results)
evaluator.plot_comparison(results)
```

### Legacy API (Still Supported)

The original API continues to work for backward compatibility:

```python
# Legacy backtester
from src import Backtester

backtester = Backtester(prices)
results = backtester.run(initial_capital=100000)

# Legacy portfolio class
from src.portfolio import Portfolio

portfolio = Portfolio(prices)
weights = portfolio.build_target_weights_from_rule(
    rule=portfolio.equal_weight_rule(),
    schedule='M'
)
result = portfolio.rebalance(weights)
```

## 📚 Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Complete system architecture, design principles, component descriptions, data flow diagrams, extension points, and best practices (~3000 words)

- **[STRATEGIES.md](docs/STRATEGIES.md)**: Detailed guide for all 10 pre-built strategies including:
  - Strategy descriptions and theory
  - Parameter specifications
  - Usage examples
  - Pros/cons analysis
  - Optimal parameter recommendations
  - Research references
  - Performance comparison matrix
  
- **PIPELINE.md**: Original pipeline documentation

- **PORTFOLIO_MANAGEMENT.md**: Portfolio system documentation

- **PORTFOLIO_INTEGRATION.md**: Integration guide

## 🧪 Testing

Comprehensive test suite with unit and integration tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_portfolio_engine.py

# Run with verbose output
pytest -v
```

Test coverage includes:
- PortfolioEngine initialization and configuration
- Strategy execution and rebalancing
- Metric calculations (returns, Sharpe, drawdown, etc.)
- Transaction cost modeling
- Data export for dashboards
- Integration with all 10 strategies

## 📊 Visualizations

All example scripts generate comprehensive visualizations saved to `visualizations/` folder:

**From demo_all_strategies.py:**
- Strategy comparison (6-panel dashboard)
- Individual strategy performance
- Equity curves with benchmark
- Portfolio weights over time
- Drawdown analysis
- Rolling metrics (Sharpe, volatility)

**From simple_example.py:**
- Equity curve
- Portfolio weights
- Drawdown chart
- Rolling Sharpe ratio

See `visualizations/README.md` for detailed information about each visualization type.

## 🔧 Extending the System

The modular architecture makes it easy to add new strategies or customize existing ones.

### Creating a Custom Strategy

```python
from src.strategy_wrapper import BaseStrategyWrapper
import pandas as pd
import numpy as np

class MyCustomStrategy(BaseStrategyWrapper):
    """
    Custom trading strategy implementation.
    """
    
    def __init__(self, param1: float = 1.0, param2: int = 20):
        """
        Initialize strategy with parameters.
        
        Parameters
        ----------
        param1 : float
            Custom parameter 1
        param2 : int
            Custom parameter 2
        """
        self.param1 = param1
        self.param2 = param2
        
    def generate_target_weights(
        self,
        prices: pd.DataFrame,
        current_weights: pd.Series,
        current_date: pd.Timestamp
    ) -> pd.Series:
        """
        Generate target portfolio weights.
        
        Parameters
        ----------
        prices : pd.DataFrame
            Historical price data (columns=assets, index=dates)
        current_weights : pd.Series
            Current portfolio weights
        current_date : pd.Timestamp
            Current rebalancing date
        
        Returns
        -------
        pd.Series
            Target weights (must sum to 1.0)
        """
        # Your custom logic here
        # Example: Equal weight
        n_assets = len(prices.columns)
        target_weights = pd.Series(
            1.0 / n_assets,
            index=prices.columns
        )
        
        return target_weights
    
    def get_strategy_name(self) -> str:
        """Return strategy name for reporting."""
        return f"MyCustomStrategy(param1={self.param1}, param2={self.param2})"

# Use custom strategy
strategy = MyCustomStrategy(param1=2.0, param2=30)
engine = PortfolioEngine(prices, strategy)
result = engine.run_backtest()
```

See `docs/ARCHITECTURE.md` for detailed extension guide with more examples.

### Adding New Optimization Methods

```python
# In optimizer.py
def custom_optimization(self, expected_returns, cov_matrix, **kwargs):
    # Your optimization logic
    return optimal_weights
```

### Adding New Performance Metrics

```python
# In portfolio_engine.py, update _update_metrics()
def _update_metrics(self):
    # Add your custom metric calculations
    self.state.custom_metric = calculate_custom_metric(...)
```

## 📊 Example Output

```
=== Portfolio Backtest Results ===

Strategy: Momentum (lookback=60, reversion_threshold=2.0)
Period: 2020-01-01 to 2024-01-01

PERFORMANCE METRICS
-------------------
Total Return:        34.56%
Annualized Return:   15.23%
Volatility:          12.45%
Sharpe Ratio:        1.22
Sortino Ratio:       1.87
Max Drawdown:        -8.34%
Calmar Ratio:        1.83

RISK METRICS
------------
Value at Risk (95%):     -1.89%
Conditional VaR (95%):   -2.76%
Downside Deviation:       8.12%

TRADE STATISTICS
----------------
Total Trades:        48
Avg Trade Cost:      $127.34
Total Costs:         $6,112.32
Portfolio Turnover:  24.3%

COMPARISON TO BENCHMARK (SPY)
------------------------------
Benchmark Return:    28.12%
Alpha:               6.44%
Beta:                0.87
Information Ratio:   0.64
Tracking Error:      4.23%
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

### Version 2.0 Features ✅
- [x] Strategy-agnostic portfolio engine
- [x] 10 pre-built trading strategies (basic to advanced)
- [x] Real-time metric calculation during backtests
- [x] Dashboard-ready data export
- [x] Comprehensive documentation (ARCHITECTURE.md, STRATEGIES.md)
- [x] Unit and integration test suite
- [x] Example scripts with visualizations
- [x] Backward compatibility with legacy code

### Planned Features 🚧
- [ ] Interactive web dashboard (Dash/Streamlit)
- [ ] Real-time data integration (WebSocket feeds)
- [ ] More ML strategies (LSTM, Transformers, Ensemble methods)
- [ ] Risk management enhancements (stop-loss, position sizing)
- [ ] Multi-asset class support (bonds, commodities, crypto)
- [ ] Options and derivatives modeling
- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation for robustness testing
- [ ] Live trading API integration (paper trading)
- [ ] Performance attribution analysis
- [ ] ESG factor integration
- [ ] Alternative data sources

## 🔬 Research & Academic Use

This framework is designed for:
- **Academic Research**: Clean, documented codebase for reproducible research
- **Strategy Development**: Rapid prototyping of new trading strategies
- **Backtesting**: Realistic simulation with transaction costs and slippage
- **Performance Analysis**: Comprehensive metrics and visualizations
- **Education**: Learn algorithmic trading concepts with working code

### Citing This Work

If you use this framework in academic research, please cite:

```bibtex
@software{algo_trading_framework,
  title = {Algorithmic Trading & Portfolio Management System},
  author = {AI Assistant},
  year = {2025},
  version = {2.0.0},
  url = {https://github.com/yourusername/algo-trading-modeling}
}
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Report Bugs**: Open an issue with detailed description
2. **Suggest Features**: Propose new strategies or improvements
3. **Submit Pull Requests**: Follow the contribution guidelines
4. **Improve Documentation**: Help make docs clearer and more comprehensive
5. **Share Results**: Share your backtesting results and insights

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all functions and classes (NumPy format)
- Include type hints where appropriate
- Write unit tests for new functionality
- Update documentation for API changes
- Run tests before submitting PRs

### Setting Up Development Environment

```bash
# Clone repository
git clone <repository-url>
cd algo-trading-modeling

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest

# Check code quality
black src/ tests/
flake8 src/ tests/
```

## ⚠️ Disclaimers

**Important Notice**: This software is for educational and research purposes only. It is not intended as financial advice or for actual trading. Past performance does not guarantee future results.

**Risk Warning**: Trading and investing involve substantial risk of loss. The authors and contributors are not responsible for any financial losses incurred through the use of this software.

**No Financial Advice**: This system is a research tool and should not be used as the sole basis for investment decisions. Always consult with qualified financial professionals.

**Data Disclaimer**: Historical data may contain errors or biases. Always validate data quality before making decisions.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

This framework builds upon excellent open-source libraries:

- **Financial Data**: [yfinance](https://github.com/ranaroussi/yfinance) for market data
- **Optimization**: [CVXPY](https://www.cvxpy.org/), [SciPy](https://scipy.org/)
- **Time Series**: [statsmodels](https://www.statsmodels.org/), [ARCH](https://arch.readthedocs.io/)
- **Machine Learning**: [scikit-learn](https://scikit-learn.org/), [PyTorch](https://pytorch.org/)
- **Visualization**: [matplotlib](https://matplotlib.org/), [seaborn](https://seaborn.pydata.org/), [plotly](https://plotly.com/)
- **Data Analysis**: [pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)

Special thanks to the quantitative finance and machine learning communities for their research and insights.

## 📚 Additional Resources

### Documentation
- [Architecture Guide](docs/ARCHITECTURE.md) - System design and extension points
- [Strategy Guide](docs/STRATEGIES.md) - Complete documentation of all 10 strategies
- [Visualization Guide](visualizations/README.md) - Chart types and customization

### Learning Resources
- **Quantitative Finance**: "Advances in Financial Machine Learning" by Marcos López de Prado
- **Portfolio Theory**: "Modern Portfolio Theory and Investment Analysis" by Elton et al.
- **Machine Learning**: "Machine Learning for Asset Managers" by Marcos López de Prado
- **Time Series**: "Time Series Analysis" by Hamilton

### Related Projects
- [QuantLib](https://www.quantlib.org/) - Quantitative finance library
- [Zipline](https://github.com/quantopian/zipline) - Backtesting library
- [Backtrader](https://www.backtrader.com/) - Python backtesting framework
- [QuantConnect](https://www.quantconnect.com/) - Algorithmic trading platform

## 📞 Support & Contact

For questions, issues, or contributions:

1. **Documentation**: Start with this README and `docs/` folder
2. **GitHub Issues**: Report bugs or request features
3. **GitHub Discussions**: Ask questions and share ideas
4. **Pull Requests**: Contribute code improvements

**Project Repository**: [GitHub Link]  
**Documentation**: [Docs Link]  
**Examples**: See `examples/` folder

---

## 🎓 Quick Reference Card

### Core Classes
```python
from src import (
    PortfolioEngine,      # Main portfolio management engine
    PortfolioResult,      # Backtest results container
    BaseStrategyWrapper,  # Abstract strategy interface
    MomentumStrategy,     # Example strategy
)
```

### Basic Workflow
```python
# 1. Load data
import yfinance as yf
prices = yf.download(['AAPL', 'MSFT', 'GOOGL'], start='2020-01-01')['Adj Close']

# 2. Create strategy
strategy = MomentumStrategy(lookback=60)

# 3. Initialize engine
engine = PortfolioEngine(prices, strategy, initial_capital=100000)

# 4. Run backtest
result = engine.run_backtest()

# 5. Analyze results
print(f"Sharpe: {result.metrics['sharpe_ratio']:.2f}")
print(f"Return: {result.metrics['total_return']:.2%}")

# 6. Get dashboard data
data = engine.get_dashboard_data()
```

### Available Strategies
```python
# Factory function
from src import create_strategy

strategies = [
    'equal_weight', 'momentum', 'mean_reversion', 
    'inverse_volatility', 'cvar_minimization',
    'regime_switching', 'ml_random_forest',
    'ml_gradient_boosting', 'arma_forecast',
    'multi_factor_ml'
]

strategy = create_strategy('momentum', lookback=60)
```

---

**Version**: 2.0.0  
**Last Updated**: January 2025  
**Status**: Production Ready ✅

**Happy Trading! 📈 Remember: Past performance is not indicative of future results.**