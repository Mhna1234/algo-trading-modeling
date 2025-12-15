# Algorithmic Trading & Portfolio Management System

A comprehensive Python-based algorithmic trading framework featuring advanced portfolio optimization, multiple trading strategies, multi-armed bandit allocation, and robust backtesting capabilities with AWS S3 integration for market data.

## 🎯 Overview

This project provides a production-ready algorithmic trading system with:
- **12 validated benchmark strategies** (momentum, mean reversion, optimization-based, etc.)
- **Multi-Armed Bandit (MAB) strategy allocation** with UCB and Thompson Sampling algorithms
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
│   ├── bandit_strategy_wrapper.py  # MAB-based strategy allocation
│   ├── data_loader.py           # Data loading and preprocessing
│   ├── data_retrieval.py        # Market data fetching (S3/yfinance)
│   ├── evaluator.py             # Performance metrics calculation
│   ├── feature_engineering.py   # Technical indicators & features
│   ├── optimizer.py             # Portfolio optimization algorithms
│   ├── portfolio_engine.py      # Core portfolio management system
│   ├── rewards.py               # Reward calculation for bandits
│   ├── signal_generator.py      # Signal generation interface
│   ├── strategy_wrapper.py      # 12 validated benchmark strategies
│   ├── utils.py                 # Helper functions
│   └── bandits/                 # Multi-Armed Bandit implementations
│       ├── ucb_bandit.py       # Upper Confidence Bound algorithm
│       └── thompson_bandit.py  # Thompson Sampling algorithm
│
├── data/                         # Data storage
│   ├── raw/                     # Raw market data
│   └── processed/               # Processed & feature-engineered data
│
├── examples/                     # Example scripts and demos
│   ├── simple_example.py        # Quick start example
│   ├── demo_12_strategies_fast.py    # Fast demo (6 months, weekly rebalancing)
│   ├── demo_12_strategies_full.py    # Full demo (10 years, monthly rebalancing)
│   ├── demo_backtesting_methods.py   # Advanced backtesting methods
│   ├── demo_bandit_strategy_wrapper.py  # MAB strategy allocation demo
│   ├── demo_bandit_comparison.py     # UCB vs Thompson Sampling comparison
│   ├── demo_ucb_bandit.py            # UCB algorithm demo
│   ├── demo_rewards.py               # Reward calculation demo
│   └── demo_svm_regime_strategy.py   # SVM regime classification demo
│
├── notebooks/                    # Jupyter notebooks for analysis
│   └── exploratory_analysis.ipynb
│
├── scripts/                      # Utility scripts
│   ├── load_s3_data.py          # AWS S3 data loading
│   ├── prepare_data.py          # Data preparation pipeline
│   └── validate_12_benchmark_strategies.py  # Strategy validation
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

# Benchmark 12 strategies (fast mode - 6 months, weekly rebalancing)
python examples/demo_12_strategies_fast.py

# Benchmark 12 strategies (full mode - 10 years, monthly rebalancing)
python examples/demo_12_strategies_full.py

# Multi-Armed Bandit strategy allocation
python examples/demo_bandit_strategy_wrapper.py

# Compare UCB vs Thompson Sampling
python examples/demo_bandit_comparison.py

# Advanced backtesting methods
python examples/demo_backtesting_methods.py
```

### Launch Dashboard

```bash
streamlit run dashboard.py
```

## 📊 Validated Benchmark Strategies

The system includes **12 validated benchmark strategies** that cover all major portfolio construction approaches:

### Passive/Baseline Strategies
1. **Buy & Hold** - Market cap weighted benchmark
2. **Equal Weight (1/N)** - Naive diversification baseline

### Factor-Based Strategies
3. **Quintile Momentum** - Cross-sectional momentum (top 20%)
4. **Quintile Low Volatility** - Low volatility factor (bottom 20%)
5. **Mean Reversion Quintile** - Contrarian strategy

### Risk-Based Optimization
6. **Global Minimum Variance Portfolio (GMVP)** - Minimum portfolio volatility
7. **Inverse Volatility** - Weight inversely proportional to volatility
8. **Risk Parity** - Equal risk contribution across assets
9. **Maximum Diversification** - Maximize diversification ratio
10. **Maximum Decorrelation** - Minimize average correlation

### Return-Based Optimization
11. **Sharpe Ratio Maximization** - Mean-variance optimization
12. **CVaR Minimization** - Conditional Value-at-Risk minimization

All strategies are validated for mathematical correctness, integration, and performance. See [VALIDATION_COMPLETE.md](VALIDATION_COMPLETE.md) for detailed validation results.

## 🎰 Multi-Armed Bandit (MAB) Allocation

The system includes sophisticated MAB algorithms for dynamic strategy allocation:

### Algorithms
- **Upper Confidence Bound (UCB)** - Balance exploration and exploitation with confidence bounds
- **Thompson Sampling** - Bayesian approach with posterior sampling

### Features
- Configurable burn-in period for initial exploration
- Multiple reward functions (returns, Sharpe ratio, Sortino ratio)
- Soft allocation (probabilistic) or hard allocation (winner-takes-all)
- Built-in persistence and state management

See [BANDIT_EXPLANATION.md](BANDIT_EXPLANATION.md) for detailed MAB methodology.

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
- Realistic transaction cost modeling (slippage + fees)
- Configurable rebalancing frequencies (daily, weekly, monthly)
- Position sizing and risk management
- Multiple optimization methods (mean-variance, risk parity, etc.)

### Performance Metrics
- Returns (total, annualized, CAGR)
- Risk-adjusted metrics (Sharpe, Sortino, Calmar)
- Drawdown analysis (max drawdown, recovery time)
- Win rate and profit factor
- Turnover and transaction costs
- Concentration metrics (Herfindahl-Hirschman Index)

### Data Management
- AWS S3 integration for scalable data storage
- Pre-processing pipeline for optimized data workflow
- Support for multiple data sources (yfinance, CSV, S3)
- Automated feature engineering
- Technical indicator calculation

### Visualization & Reporting
- NAV curves with comparative analysis
- Multi-panel performance metrics charts
- Correlation heatmaps
- Comprehensive JSON/CSV exports
- Interactive Streamlit dashboard

## 🛠️ Technology Stack

- **Core**: Python 3.11+, NumPy, Pandas
- **Optimization**: scipy, cvxpy (convex optimization)
- **Machine Learning**: scikit-learn
- **Time Series**: statsmodels
- **Cloud**: boto3 (AWS S3), pyarrow
- **Visualization**: matplotlib, seaborn
- **Dashboard**: Streamlit
- **Testing**: pytest

## 📚 Documentation

Comprehensive documentation is available:

### Core Documentation
- **[README.md](README.md)** - This file: project overview and quick start
- **[VALIDATION_COMPLETE.md](VALIDATION_COMPLETE.md)** - Strategy validation results
- **[BANDIT_EXPLANATION.md](BANDIT_EXPLANATION.md)** - Multi-Armed Bandit methodology
- **[BANDIT_INTEGRATION.md](BANDIT_INTEGRATION.md)** - MAB integration guide
- **[DATA_WORKFLOW.md](DATA_WORKFLOW.md)** - Data preparation workflow
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference
- **[QUICKSTART_S3.md](QUICKSTART_S3.md)** - S3 setup quick start

### Technical Documentation (docs/)
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- **[STRATEGIES.md](docs/STRATEGIES.md)** - Strategy descriptions
- **[BACKTESTING_METHODS.md](docs/BACKTESTING_METHODS.md)** - Validation methods
- **[S3_DATA_RETRIEVAL.md](docs/S3_DATA_RETRIEVAL.md)** - AWS S3 setup guide
- **[TRADING_FUNDAMENTALS.md](docs/TRADING_FUNDAMENTALS.md)** - Trading concepts
- **[MAB_IMPLEMENTATION_PLAN.md](docs/MAB_IMPLEMENTATION_PLAN.md)** - MAB implementation plan
- **[MULTI_ARMED_BANDITS.md](docs/MULTI_ARMED_BANDITS.md)** - MAB theory

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
pytest --cov=src tests/  # With coverage
```

## 📊 Example Results

Sample performance metrics from validated benchmark strategies (see [FULL_DEMO_RESULTS.md](FULL_DEMO_RESULTS.md) for complete results):

**Configuration**: 10-year backtest (2015-2024), monthly rebalancing, 0.1% transaction costs

| Strategy | CAGR | Sharpe | Max Drawdown | Volatility |
|----------|------|--------|--------------|------------|
| Quintile Momentum | 8.2% | 0.89 | -24.3% | 9.8% |
| Risk Parity | 6.5% | 0.92 | -18.7% | 7.2% |
| Global Min Variance | 5.8% | 0.85 | -16.2% | 7.0% |
| Equal Weight | 7.1% | 0.82 | -21.5% | 9.1% |

**Bandit Performance**: UCB bandit with Sharpe reward typically achieves 10-15% higher risk-adjusted returns by dynamically allocating to top-performing strategies.

See `visualizations/` for detailed comparison charts and metrics exports.

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

**Version**: 3.0.0 | **Last Updated**: December 15, 2025

## 🎉 Recent Updates

### Version 3.0.0 (December 2025)
- ✅ Validated and documented 12 benchmark strategies
- ✅ Implemented Multi-Armed Bandit (UCB & Thompson Sampling) for strategy allocation
- ✅ Added comprehensive reward calculation system (returns, Sharpe, Sortino)
- ✅ Optimized rebalancing frequencies (monthly for realistic transaction costs)
- ✅ Enhanced visualization and reporting capabilities
- ✅ Streamlined data workflow with pre-processing pipeline
- ✅ Complete test coverage for bandit implementations
- ✅ Production-ready codebase with full documentation
