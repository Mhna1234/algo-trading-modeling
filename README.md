# Algorithmic Trading & Portfolio Management System

A comprehensive Python-based algorithmic trading framework featuring advanced portfolio optimization, multiple trading strategies, and robust backtesting capabilities with AWS S3 integration for market data.

## 🎯 Overview

This project provides a production-ready algorithmic trading system with:
- **22 pre-built trading strategies** (momentum, mean reversion, machine learning-based, etc.)
- **5 advanced backtesting methods** (walk-forward, combinatorial, Monte Carlo, etc.)
- **Portfolio optimization engine** with risk management
- **Real-time performance metrics** and comprehensive evaluation
- **AWS S3 data integration** for scalable market data retrieval
- **Interactive dashboard** for strategy visualization and analysis

## 📁 Project Structure

```
algo-trading-modeling/
├── src/                          # Core source code
│   ├── backtester.py            # Legacy backtesting wrapper
│   ├── backtesting_methods.py   # Advanced validation methods
│   ├── data_loader.py           # Data loading and preprocessing
│   ├── data_retrieval.py        # Market data fetching
│   ├── evaluator.py             # Performance metrics calculation
│   ├── feature_engineering.py   # Technical indicators & features
│   ├── optimizer.py             # Portfolio optimization algorithms
│   ├── portfolio_engine.py      # Core portfolio management system
│   ├── signal_generator.py      # Signal generation interface
│   ├── strategy_wrapper.py      # 21 production-ready strategies
│   └── utils.py                 # Helper functions
│
├── data/                         # Data storage
│   ├── raw/                     # Raw market data
│   └── processed/               # Processed & feature-engineered data
│
├── examples/                     # Example scripts and demos
│   ├── simple_example.py        # Quick start example
│   ├── demo_12_strategies_fast.py    # Fast demo (6 months)
│   ├── demo_12_strategies_full.py    # Full demo (10 years)
│   ├── demo_benchmark_strategies.py
│   ├── demo_backtesting_methods.py
│   └── demo_svm_regime_strategy.py
│
├── notebooks/                    # Jupyter notebooks for analysis
│   └── exploratory_analysis.ipynb
│
├── scripts/                      # Utility scripts
│   └── load_s3_data.py          # AWS S3 data loading
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md          # System architecture
│   ├── STRATEGIES.md            # Strategy descriptions
│   ├── BACKTESTING_METHODS.md   # Validation methods
│   ├── S3_DATA_RETRIEVAL.md     # AWS S3 setup guide
│   └── TRADING_FUNDAMENTALS.md  # Trading concepts
│
├── tests/                        # Unit tests
├── visualizations/               # Output visualizations & results
├── dashboard.py                  # Streamlit dashboard
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11.9 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Mhna1234/algo-trading-modeling.git
cd algo-trading-modeling
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Configure AWS S3 for market data:
   - See `docs/S3_DATA_RETRIEVAL.md` for setup instructions
   - See `QUICKSTART_S3.md` for quick reference

### Basic Usage

```python
from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import MomentumStrategy
from src.data_loader import DataLoader

# Load data
loader = DataLoader()
prices = loader.load_data('data/processed/price_data_2020-01-01_2023-12-31.csv')

# Initialize portfolio engine
portfolio = PortfolioEngine(prices)

# Create and run strategy
strategy = MomentumStrategy(lookback=20, n_positions=10)
result = portfolio.run_backtest(
    strategy=strategy,
    start_date='2020-01-01',
    end_date='2023-12-31',
    initial_capital=100000
)

# Analyze results
print(f"Total Return: {result['total_return']:.2%}")
print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {result['max_drawdown']:.2%}")
```

### Run Examples

```bash
# Simple example
python examples/simple_example.py

# Benchmark multiple strategies
python examples/demo_benchmark_strategies.py

# Advanced backtesting methods
python examples/demo_backtesting_methods.py
```

### Launch Dashboard

```bash
streamlit run dashboard.py
```

## 📊 Available Strategies

The system includes 22 production-ready strategies organized by category:

### Basic Strategies
- Equal Weight (1/N baseline)
- Buy and Hold (benchmark)
- Inverse Volatility (risk parity)

### Momentum & Trend
- Momentum Strategy (multi-period)
- Time Series Momentum (12-month)
- Moving Average Crossover (50/200 day)

### Mean Reversion
- Mean Reversion Strategy (Z-score based)

### Risk-Based Optimization
- Global Minimum Variance Portfolio (GMVP)
- Global Maximum Return Portfolio (GMRP)
- CVaR Minimization
- Maximum Diversification
- Maximum Decorrelation

### Machine Learning & Factor-Based
- Linear Regression (factor-based)
- Multi-Factor ML
- Random Forest Strategy
- Gradient Boosting Strategy
- SVM Regime Classification

### Advanced Strategies
- Regime Switching (volatility-based)
- ARMA Forecast
- ARIMA-GARCH (time series + volatility)
- Quintile Factor
- Markowitz MVO (mean-variance)

See `docs/STRATEGIES.md` for detailed descriptions and parameters.

## 🔬 Backtesting Methods

Five advanced validation methods to ensure robust strategy performance:

1. **Walk-Forward Analysis** - Rolling window optimization
2. **Combinatorial Purged Cross-Validation** - Prevents data leakage
3. **Monte Carlo Simulation** - Randomized testing
4. **Anchored Walk-Forward** - Expanding window validation
5. **Time Series Cross-Validation** - Fixed-size splits

See `docs/BACKTESTING_METHODS.md` for mathematical formulations.

## 📈 Features

### Portfolio Engine
- Strategy-agnostic architecture
- Real-time metric calculation
- Transaction cost modeling (slippage + fees)
- Position sizing and risk management
- Multiple optimization methods (mean-variance, risk parity, etc.)

### Performance Metrics
- Returns (total, annualized, rolling)
- Risk-adjusted metrics (Sharpe, Sortino, Calmar)
- Drawdown analysis
- Win rate and profit factor
- Turnover and transaction costs

### Data Management
- AWS S3 integration for scalable data storage
- Support for multiple data sources (yfinance, CSV, S3)
- Automated feature engineering
- Technical indicator calculation (50+ indicators)

## 🛠️ Technology Stack

- **Core**: Python 3.8+, NumPy, Pandas
- **Machine Learning**: scikit-learn, River (online learning), stable-baselines3 (RL)
- **Time Series**: statsmodels, arch
- **Cloud**: boto3 (AWS S3), pyarrow
- **Visualization**: matplotlib, seaborn, plotly
- **Dashboard**: Streamlit
- **Testing**: pytest, pytest-cov

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **ARCHITECTURE.md** - System design and components
- **STRATEGIES.md** - Strategy implementations and parameters
- **BACKTESTING_METHODS.md** - Validation methodology
- **S3_DATA_RETRIEVAL.md** - AWS S3 setup and usage
- **TRADING_FUNDAMENTALS.md** - Trading concepts and theory

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
pytest --cov=src tests/  # With coverage
```

## 📊 Example Results

Sample performance metrics from benchmark strategies (5-year backtest):

| Strategy | Total Return | Sharpe Ratio | Max Drawdown |
|----------|-------------|--------------|--------------|
| Momentum | 45.2% | 1.23 | -18.5% |
| Mean Reversion | 32.8% | 1.05 | -12.3% |
| SVM Regime | 51.6% | 1.41 | -15.2% |

See `visualizations/` for detailed comparison charts.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- New features include documentation
- Commit messages are descriptive

## 📝 License

This project is available for educational and research purposes.

## 🔗 Links

- **Repository**: https://github.com/Mhna1234/algo-trading-modeling
- **Issues**: https://github.com/Mhna1234/algo-trading-modeling/issues

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Trading involves substantial risk of loss. Always conduct your own research and consult with qualified financial advisors before making investment decisions.

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

---

**Version**: 2.2.0 | **Last Updated**: December 2025
