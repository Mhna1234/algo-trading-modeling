# Algorithmic Trading & Portfolio Management System

A comprehensive Python-based algorithmic trading framework featuring advanced portfolio optimization, multiple trading strategies, multi-armed bandit allocation, and robust backtesting capabilities with AWS S3 integration for market data.

## 🎯 Overview

This project provides a production-ready algorithmic trading system with:
- **12 validated benchmark strategies** (momentum, mean reversion, optimization-based, etc.)
- **Multi-Armed Bandit (MAB) strategy allocation** with UCB, Thompson Sampling, and EXP3 algorithms
- **5 advanced backtesting methods** (walk-forward, combinatorial, Monte Carlo, etc.)
- **Real-time trading capabilities** with state persistence and daily updates
- **Portfolio optimization engine** with risk management and soft rebalancing
- **Real-time performance metrics** and comprehensive evaluation
- **AWS S3 data integration** for scalable market data retrieval
- **Interactive dashboard** for strategy visualization and analysis
- **Complete state persistence** with checkpoint management and rollback capabilities

## 📁 Project Structure

```
algo-trading-modeling/
├── src/                          # Core source code
│   ├── MODULE_ORGANIZATION.md   # 📖 Module organization guide (READ THIS!)
│   ├── backtester.py            # Legacy backtesting wrapper
│   ├── backtesting_methods.py   # Advanced validation methods
│   ├── checkpoint_manager.py    # State persistence for real-time trading
│   ├── daily_trading_engine.py  # Real-time trading orchestration
│   ├── data_loader.py           # Data loading and preprocessing
│   ├── data_retrieval.py        # Market data fetching (S3/yfinance)
│   ├── evaluator.py             # Performance metrics calculation
│   ├── feature_engineering.py   # Technical indicators (RSI, MACD, etc.)
│   ├── signal_generator.py      # Signal generation & data container
│   ├── optimizer.py             # Portfolio optimization algorithms
│   ├── portfolio_engine.py      # Core portfolio management system
│   ├── rewards.py               # Reward calculation for bandits
│   ├── risk_free_asset.py       # Risk-free rate integration (FRED API)
│   ├── transaction_cost_model.py # Realistic trading cost modeling
│   ├── rebalancing_scheduler.py # Rebalancing logic and scheduling
│   ├── utils.py                 # Helper functions
│   ├── config_loader.py         # YAML configuration management
│   ├── strategies/              # 25 trading strategies (organized)
│   │   ├── base_strategy_wrapper.py    # Abstract base class
│   │   ├── benchmark_strategies.py     # 12 validated strategies
│   │   ├── advanced_strategies.py      # 13 experimental strategies
│   │   └── bandit_strategy_wrapper.py  # MAB meta-strategy
│   └── bandits/                 # Multi-Armed Bandit implementations
│       ├── base.py              # Abstract bandit interface
│       ├── ucb.py               # Upper Confidence Bound algorithm
│       ├── thompson.py          # Thompson Sampling algorithm
│       └── exp3.py              # EXP3 algorithm (adversarial bandit)
│
├── config/                      # Configuration files
│   ├── trading_config.yaml      # Main system configuration (gitignored)
│   └── trading_config.yaml.example  # Configuration template
│
├── checkpoints/                 # State persistence for real-time trading
│
├── data/                         # Data storage
│   ├── processed/                # Processed data (CSV)
│   └── raw/                      # Raw market data (CSV)
│
├── examples/                     # Example scripts and demos
│   ├── DATA_LOADING_GUIDE.md     # Data loading documentation
│   ├── simple_example.py         # Basic usage example
│   ├── dynamic_trading_demo.py   # Unified real-time trading platform
│   ├── demo_12_strategies_fast.py  # Fast 6-month comparison
│   ├── demo_12_strategies_full.py  # Full 10-year comparison
│   ├── demo_backtesting_methods.py # Validation methods demo
│   ├── demo_bandit_strategy_wrapper.py  # MAB strategy allocation demo
│   ├── demo_bandit_comparison.py     # UCB vs Thompson Sampling comparison
│   ├── mab_comparison_demo.py        # MAB vanilla backtesting comparison
│   ├── mab_walk_forward_demo.py      # MAB walk-forward evaluation (NEW)
│   ├── demo_ucb_bandit.py            # UCB algorithm demo
│   ├── demo_exp3_bandit.py           # EXP3 algorithm demo
│   ├── demo_rewards.py               # Reward calculation demo
│   ├── demo_soft_rebalancing.py      # Soft rebalancing demo
│   ├── demo_soft_rebalancing_bandits.py  # Soft rebalancing with bandits
│   ├── demo_soft_rebalancing_walkforward.py  # Walk-forward soft rebalancing
│   ├── demo_svm_regime_strategy.py   # SVM regime classification demo
│   └── visualizations/               # Output visualization examples
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
│   ├── BACKTESTING_METHODS.md   # Validation methods with results
│   ├── BACKTESTING_STRATEGIES.md # Backtesting methodology guide
│   ├── REALTIME_TRADING_IMPLEMENTATION_PLAN.md # Real-time trading implementation
│   ├── S3_DATA_RETRIEVAL.md     # AWS S3 setup guide
│   ├── TRADING_FUNDAMENTALS.md  # Trading concepts
│   ├── MAB_IMPLEMENTATION_PLAN.md # MAB implementation (completed)
│   ├── MULTI_ARMED_BANDITS.md   # MAB theory and algorithms
│   ├── RISK_FREE_ASSET_INTEGRATION.md # Risk-free rate integration
│   └── TASK_TRACKER.md          # Development roadmap
│   ├── TASKS.md                 # Development roadmap
│   ├── TASK_TRACKER.md          # Task tracking
│   └── MULTI_ARMED_BANDITS.md   # MAB theory
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

### Configuration

The system uses YAML-based configuration for flexible setup. The main configuration file is `config/trading_config.yaml`:

```yaml
# Execution mode: backtest, simulation, or live
execution:
  mode: "simulation"

# Trading parameters
trading:
  initial_capital: 100000
  transaction_cost_bps: 10.0
  rebalance_frequency: "M"

# Multi-armed bandit settings
bandit:
  type: "ucb"  # ucb, thompson, exp3
  burn_in_periods: 12
  reward_type: "sharpe"

# Risk-free asset integration
risk_free:
  rate_source: "fred"  # fred, config, fallback
  maturity: "3M"
```

**Setup Configuration:**
1. Copy the example config: `cp config/trading_config.yaml.example config/trading_config.yaml`
2. Edit `config/trading_config.yaml` with your settings
3. The actual config file is gitignored for security

**Environment Variables:**
- `FRED_API_KEY`: For Federal Reserve Economic Data API access
- `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY`: For S3 data access

Set these in your shell environment or use your system's environment variable management. The system does not use .env files for security reasons.

**Security Note:** Never commit API keys or sensitive configuration to version control. Use environment variables or keep config files local.

### Basic Usage

```python
from src.portfolio_engine import PortfolioEngine
from src.strategy_wrapper import MomentumStrategy
from src.data_loader import DataLoader

# Load data
loader = DataLoader()
prices = loader.load_data('data/processed/price_data_2020-01-01_2023-12-31.csv')

# Initialize portfolio engine with soft rebalancing
portfolio = PortfolioEngine(prices, enable_soft_rebalance=True, drift_threshold=0.05)

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

# Unified real-time trading platform (BACKTEST/SIMULATION/LIVE modes)
python examples/dynamic_trading_demo.py --mode backtest
python examples/dynamic_trading_demo.py --mode simulation
python examples/dynamic_trading_demo.py --mode live

# Benchmark 12 strategies (fast mode - 6 months, weekly rebalancing)
python examples/demo_12_strategies_fast.py

# Benchmark 12 strategies (full mode - 10 years, monthly rebalancing)
python examples/demo_12_strategies_full.py

# Multi-Armed Bandit strategy allocation
python examples/demo_bandit_strategy_wrapper.py

# Compare UCB vs Thompson Sampling
python examples/demo_bandit_comparison.py

# Multi-Armed Bandit walk-forward evaluation (NEW)
python examples/mab_walk_forward_demo.py

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

All strategies are validated for mathematical correctness, integration, and performance. See [BACKTESTING_METHODS.md](docs/BACKTESTING_METHODS.md) for detailed validation results.

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

See [MULTI_ARMED_BANDITS.md](docs/MULTI_ARMED_BANDITS.md) for detailed MAB methodology.

## 🔬 Backtesting Methods

Five advanced validation methods to ensure robust strategy performance:

1. **Walk-Forward Analysis** - Rolling window optimization
2. **Combinatorial Purged Cross-Validation** - Prevents data leakage
3. **Monte Carlo Simulation** - Randomized testing
4. **Anchored Walk-Forward** - Expanding window validation
5. **Time Series Cross-Validation** - Fixed-size splits

See `docs/BACKTESTING_METHODS.md` for mathematical formulations.

## 📈 Features

### Real-Time Trading System
- **State Persistence**: Checkpoint-based system with 7-day rollback capability
- **Daily Updates**: Incremental data loading from S3 with gap detection
- **Live Execution**: Real-time trading decisions with MAB allocation
- **System Reset**: Complete state reset for testing and strategy changes
- **Configuration Management**: YAML-based config with environment variable support

### Portfolio Engine
- Strategy-agnostic architecture with clean separation of concerns
- Real-time metric calculation during backtests
- Realistic transaction cost modeling (slippage + fees)
- Configurable rebalancing frequencies (daily, weekly, monthly, quarterly)
- **Soft rebalancing logic** (trade only when weight drift exceeds threshold)
- **Drift threshold parameter** (default 5%) for realistic trading simulation
- Position sizing and risk management
- Multiple optimization methods (mean-variance, risk parity, etc.)

### Performance Metrics
- Returns (total, annualized, CAGR)
- Risk-adjusted metrics (Sharpe, Sortino, Calmar)
- Drawdown analysis (max drawdown, recovery time)
- Win rate and profit factor
- Turnover and transaction costs
- Concentration metrics (Herfindahl-Hirschman Index)
- **Drift tracking and reporting for soft rebalancing**

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

## 🏆 Reward Functions

The system provides several reward functions for evaluating strategy performance, especially in the context of multi-armed bandit allocation. These are implemented in [src/rewards.py](src/rewards.py):

- **Simple Return Reward** (`return_to_reward`):
    - Converts raw returns to a reward, with clipping to prevent outlier domination.
    - Fast, but ignores risk and volatility.
    - Usage: `return_to_reward(ret)`

- **Sharpe-like Reward** (`sharpe_like_reward`):
    - Computes a risk-adjusted reward (return divided by volatility, with a floor to prevent division by zero).
    - Recommended default for most applications.
    - Usage: `sharpe_like_reward(ret, vol)`

- **Drawdown-Penalized Reward** (`drawdown_penalized_reward`):
    - Penalizes strategies for large drawdowns, even if they recover.
    - Usage: `drawdown_penalized_reward(ret, drawdown, lambda_dd=1.0)`

- **Multi-Objective Reward** (`multi_objective_reward`):
    - Blends return, Sharpe, and drawdown penalties with configurable weights.
    - Usage: `multi_objective_reward(ret, vol, drawdown, weight_return=0.3, weight_sharpe=0.4, weight_dd=0.3)`

- **Convenience Wrapper** (`compute_reward`):
    - Selects and computes the appropriate reward type based on input and `reward_type` argument (`'return'`, `'sharpe'`, `'drawdown'`, `'multi'`).
    - Usage: `compute_reward(ret, vol, drawdown, reward_type='sharpe')`

All reward functions handle NaN inputs gracefully and use clipping to prevent extreme values from dominating the bandit's learning process. See [src/rewards.py](src/rewards.py) for detailed docstrings and examples.

### Core Documentation
- **[README.md](README.md)** - This file: project overview and quick start
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design
- **[STRATEGIES.md](docs/STRATEGIES.md)** - Complete strategy guide (25 strategies)
- **[BACKTESTING_METHODS.md](docs/BACKTESTING_METHODS.md)** - Validation methods with results
- **[MULTI_ARMED_BANDITS.md](docs/MULTI_ARMED_BANDITS.md)** - MAB theory and implementation
- **[TASK_TRACKER.md](docs/TASK_TRACKER.md)** - Development roadmap and status

### Additional Documentation
- **[BACKTESTING_STRATEGIES.md](docs/BACKTESTING_STRATEGIES.md)** - Backtesting methodology concepts
- **[TRADING_FUNDAMENTALS.md](docs/TRADING_FUNDAMENTALS.md)** - Trading and finance fundamentals
- **[S3_DATA_RETRIEVAL.md](docs/S3_DATA_RETRIEVAL.md)** - AWS S3 data integration guide
- **[MAB_IMPLEMENTATION_PLAN.md](docs/MAB_IMPLEMENTATION_PLAN.md)** - MAB implementation details

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
pytest --cov=src tests/  # With coverage
```

## 📊 Example Results

Sample performance metrics from validated benchmark strategies (see `results/` directory for complete results):

**Configuration**: 10-year backtest (2015-2024), monthly rebalancing, 0.1% transaction costs

| Strategy | CAGR | Sharpe | Max Drawdown | Volatility |
|----------|------|--------|--------------|------------|
| Quintile Momentum | 8.2% | 0.89 | -24.3% | 9.8% |
| Risk Parity | 6.5% | 0.92 | -18.7% | 7.2% |
| Global Min Variance | 5.8% | 0.85 | -16.2% | 7.0% |
| Equal Weight | 7.1% | 0.82 | -21.5% | 9.1% |

**Bandit Performance**: UCB bandit with Sharpe reward typically achieves 10-15% higher risk-adjusted returns by dynamically allocating to top-performing strategies.

See `visualizations/` for detailed comparison charts and metrics exports.

## 📖 Code Organization

**IMPORTANT**: Before contributing or modifying code, read [src/MODULE_ORGANIZATION.md](src/MODULE_ORGANIZATION.md)

This guide explains:
- Role of each module (feature_engineering vs signal_generator vs strategies)
- How to avoid code duplication
- Common patterns and decision trees
- Which module to use for what purpose

Key principles:
- `feature_engineering.py` - Computes technical indicators (RSI, MACD values)
- `signal_generator.py` - Converts indicators to trading signals (-1, 0, +1)
- `strategies/` - Complete trading strategies combining signals + optimization
- `optimizer.py` - Portfolio optimization
- `portfolio_engine.py` - Backtesting and execution

## 🤝 Contributing

Contributions are welcome! Please ensure:
- **Read [src/MODULE_ORGANIZATION.md](src/MODULE_ORGANIZATION.md) first**
- Code follows PEP 8 style guidelines
- All tests pass
- New features include documentation
- Commit messages are descriptive
- No code duplication between modules

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

**Version**: 3.0.1 | **Last Updated**: December 28, 2025

## 🎉 Recent Updates

### Version 3.0.1 (December 2025)
- ✅ **Fixed walk-forward backtesting bug** - Resolved KeyError issues preventing out-of-sample evaluation
- ✅ **Added MAB walk-forward demo** - New `mab_walk_forward_demo.py` for proper out-of-sample MAB validation
- ✅ **Cleaned up logging in demos** - Fixed placeholder logging statements with proper f-string formatting
- ✅ **Updated documentation** - Corrected docstrings and added new demo to project structure

### Version 3.0.0 (December 2025)
- ✅ Validated and documented 12 benchmark strategies
- ✅ Implemented Multi-Armed Bandit (UCB, Thompson Sampling, EXP3) for strategy allocation
- ✅ Added comprehensive reward calculation system (returns, Sharpe, Sortino, drawdown-penalized)
- ✅ **Real-time trading system with state persistence and daily updates**
- ✅ **Checkpoint management with 7-day rollback capability**
- ✅ **Daily trading engine for incremental portfolio updates**
- ✅ **Dynamic trading demo supporting BACKTEST/SIMULATION/LIVE modes**
- ✅ **FRED API integration for dynamic risk-free rate updates**
- ✅ **Enhanced configuration system with YAML validation**
- ✅ Optimized rebalancing frequencies (monthly, quarterly, with soft rebalancing)
- ✅ **Soft rebalancing and drift threshold logic implemented in portfolio engine**
- ✅ Enhanced visualization and reporting capabilities
- ✅ Streamlined data workflow with pre-processing pipeline
- ✅ Complete test coverage for bandit implementations
- ✅ Production-ready codebase with full documentation
- ✅ **Enhanced config validation with comprehensive parameter checking and environment variable support**
