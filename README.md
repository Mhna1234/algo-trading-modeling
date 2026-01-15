# Algorithmic Trading & Portfolio Management System

A production-ready Python-based algorithmic trading framework featuring advanced portfolio optimization, 15 benchmark strategies, multi-armed bandit allocation, and AWS Lambda deployment for automated daily calculations.

## 🎯 Overview

This project provides a production-ready algorithmic trading system with:
- **15 validated benchmark strategies** deployed to AWS Lambda for daily automated calculations
- **4 Multi-Armed Bandit (MAB) algorithms** for dynamic strategy allocation (UCB, Thompson Sampling, EXP3, Epsilon-Greedy)
- **AWS Lambda deployment** with 3 partitions running daily at 3:00 AM UTC
- **Walk-forward backtesting** for robust out-of-sample validation
- **5 advanced backtesting methods** (walk-forward, combinatorial, Monte Carlo, etc.)
- **Real-time trading capabilities** with state persistence and daily updates
- **Portfolio optimization engine** with risk management and soft rebalancing
- **AWS S3 integration** for scalable market data retrieval and results storage
- **Interactive dashboard** for strategy visualization and analysis
- **Complete state persistence** with checkpoint management and rollback capabilities

## 📁 Project Structure

```
algo-trading-modeling/
├── src/                          # Core source code
│   ├── portfolio_engine.py      # Core portfolio management system
│   ├── signal_generator.py      # Signal generation & data container
│   ├── optimizer.py             # Portfolio optimization algorithms
│   ├── backtesting_methods.py   # Advanced validation methods
│   ├── checkpoint_manager.py    # State persistence for real-time trading
│   ├── daily_trading_engine.py  # Real-time trading orchestration
│   ├── data_loader.py           # Data loading and preprocessing
│   ├── data_retrieval.py        # Market data fetching (S3/yfinance)
│   ├── evaluator.py             # Performance metrics calculation
│   ├── feature_engineering.py   # Technical indicators (RSI, MACD, etc.)
│   ├── rewards.py               # Reward calculation for bandits
│   ├── risk_free_asset.py       # Risk-free rate integration (FRED API)
│   ├── transaction_cost_model.py # Realistic trading cost modeling
│   ├── rebalancing_scheduler.py # Rebalancing logic and scheduling
│   ├── config_loader.py         # YAML configuration management
│   ├── utils.py                 # Helper functions
│   ├── strategies/              # Trading strategies
│   │   ├── base_strategy_wrapper.py    # Abstract base class
│   │   ├── benchmark_strategies.py     # 12 validated strategies
│   │   ├── advanced_strategies.py      # Experimental strategies
│   │   └── bandit_strategy_wrapper.py  # MAB meta-strategy
│   └── bandits/                 # Multi-Armed Bandit implementations
│       ├── base.py              # Abstract bandit interface
│       ├── ucb.py               # Upper Confidence Bound algorithm
│       ├── thompson.py          # Thompson Sampling algorithm
│       ├── exp3.py              # EXP3 algorithm (adversarial bandit)
│       └── epsilon_greedy.py    # Epsilon-Greedy algorithm
│
├── lambda/                       # AWS Lambda deployment
│   ├── handlers/                 # Lambda function handlers
│   │   ├── lambda_function_partition_1.py  # Strategies 1-5
│   │   ├── lambda_function_partition_2.py  # Strategies 6-10
│   │   └── lambda_function_partition_3.py  # Strategies 11-15
│   ├── scripts/                  # Deployment scripts
│   │   ├── deploy_lambda.sh      # Deploy all partitions
│   │   └── setup_eventbridge.sh  # Configure daily schedule
│   ├── tests/                    # Lambda testing utilities
│   └── lambda_package/           # Bundled dependencies
│
├── config/                       # Configuration files
│   ├── trading_config.yaml       # Main system configuration (gitignored)
│   └── trading_config.yaml.example  # Configuration template
│
├── data/                         # Data storage
│   ├── processed/                # Processed data (CSV)
│   └── raw/                      # Raw market data (CSV)
│
├── examples/                     # Example scripts and demos
│   ├── comprehensive_benchmark_demo.py  # Full MAB & strategy suite
│   ├── benchmark_strategies_demo.py     # Quick benchmark comparison
│   ├── dynamic_trading_demo.py          # Real-time trading platform
│   ├── mab_walk_forward_demo.py         # MAB walk-forward evaluation
│   ├── demo_backtesting_methods.py      # Validation methods demo
│   ├── demo_mab_stress_testing.py       # MAB stress testing
│   ├── demo_rewards.py                  # Reward calculation demo
│   └── demo_soft_rebalancing.py         # Soft rebalancing demo
│
├── scripts/                      # Utility scripts
│   ├── load_s3_data.py           # AWS S3 data loading
│   ├── prepare_data.py           # Data preparation pipeline
│   └── validate_12_benchmark_strategies.py  # Strategy validation
│
├── docs/                         # Documentation (19 files)
│   ├── ARCHITECTURE.md           # System architecture
│   ├── STRATEGIES.md             # Strategy descriptions
│   ├── LAMBDA_DEPLOYMENT_STATUS.md  # Lambda deployment status
│   ├── LAMBDA_IMPLEMENTATION_SUMMARY.md  # Lambda implementation details
│   └── ...                       # Additional documentation
│
├── tests/                        # Unit tests
├── checkpoints/                  # State persistence for real-time trading
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
  type: "ucb"  # ucb, thompson, exp3, epsilon_greedy
  burn_in_periods: 12
  reward_type: "sharpe"
  epsilon: 0.1  # For epsilon-greedy algorithm

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
# Comprehensive benchmark suite (12 strategies + 4 MAB algorithms)
python examples/comprehensive_benchmark_demo.py

# Quick benchmark comparison
python examples/benchmark_strategies_demo.py

# Unified real-time trading platform (BACKTEST/SIMULATION/LIVE modes)
python examples/dynamic_trading_demo.py --mode backtest
python examples/dynamic_trading_demo.py --mode simulation
python examples/dynamic_trading_demo.py --mode live

# Multi-Armed Bandit walk-forward evaluation
python examples/mab_walk_forward_demo.py

# Advanced backtesting methods
python examples/demo_backtesting_methods.py

# MAB stress testing
python examples/demo_mab_stress_testing.py

# Soft rebalancing demonstration
python examples/demo_soft_rebalancing.py
```

### Launch Dashboard

```bash
streamlit run dashboard.py
```

## 📊 Benchmark Strategies

The system includes **15 validated benchmark strategies** deployed to AWS Lambda, organized into 3 partitions:

### Partition 1: Passive & Heuristic Strategies
1. **Buy & Hold** - Market cap weighted benchmark
2. **Equal Weight (1/N)** - Naive diversification baseline
3. **Top-K Return** - Top performers by past return
4. **Top-K Sharpe** - Top performers by risk-adjusted return
5. **Quintile Momentum** - Cross-sectional momentum (top 20%)

### Partition 2: Factor & Risk-Based Strategies
6. **Quintile Low Volatility** - Low volatility factor (bottom 20%)
7. **Mean Reversion** - Contrarian strategy
8. **Global Minimum Variance (GMVP)** - Minimum portfolio volatility
9. **Inverse Volatility** - Weight inversely proportional to volatility
10. **Inverse Variance** - Weight inversely proportional to variance

### Partition 3: Optimization Strategies
11. **Risk Parity** - Equal risk contribution across assets
12. **Maximum Decorrelation** - Minimize average correlation
13. **Most Diversified** - Maximize diversification ratio
14. **Sharpe Maximization** - Mean-variance optimization
15. **CVaR Minimization** - Conditional Value-at-Risk minimization

All strategies use walk-forward backtesting with 24-month training and 6-month test windows. See [LAMBDA_DEPLOYMENT_STATUS.md](docs/LAMBDA_DEPLOYMENT_STATUS.md) for deployment details.

## 🎰 Multi-Armed Bandit (MAB) Allocation

The system includes sophisticated MAB algorithms for dynamic strategy allocation:

### Algorithms
- **Upper Confidence Bound (UCB)** - Balance exploration and exploitation with confidence bounds
- **Thompson Sampling** - Bayesian approach with posterior sampling
- **EXP3** - Adversarial bandit for non-stationary environments
- **Epsilon-Greedy** - Simple exploration with ε-greedy policy

### Features
- Configurable burn-in period for initial exploration
- Multiple reward functions (returns, Sharpe ratio, Sortino ratio)
- Soft allocation (probabilistic) or hard allocation (winner-takes-all)
- Built-in persistence and state management

See [MULTI_ARMED_BANDITS.md](docs/MULTI_ARMED_BANDITS.md) for detailed MAB methodology.

## ☁️ AWS Lambda Deployment

The system includes production-ready AWS Lambda deployment for automated daily benchmark calculations.

### Architecture
- **3 Lambda Functions** running in parallel (one per partition)
- **15 strategies × 3 frequencies** = 45 backtests per execution
- **Walk-forward optimization** with rolling windows for robust validation
- **Automatic scheduling** via EventBridge (daily at 3:00 AM UTC)

### Lambda Configuration
| Property | Value |
|----------|-------|
| Runtime | Python 3.11 |
| Memory | 3 GB per function |
| Timeout | 15 minutes |
| Region | eu-north-1 |
| Trigger | EventBridge (daily) |

### S3 Data Flow
```
Input:  s3://data-retrieval-output/history-data/     (5 years OHLCV data)
Output: s3://benchmarks-modelling-output/benchmarks-output/
        ├── strategies/{strategy}/{freq}/{date}.json  # Complete metrics
        ├── timeseries/{strategy}/{freq}/{date}.csv   # Equity curves
        ├── weights/{strategy}/{freq}/{date}.csv      # Portfolio weights
        └── history/{date}/partition_*.json           # Execution summaries
```

### Manual Lambda Invocation
```bash
# Test any partition manually
aws lambda invoke --function-name benchmark-calculator-partition-1 \
  --region eu-north-1 response.json
```

See [LAMBDA_DEPLOYMENT_STATUS.md](docs/LAMBDA_DEPLOYMENT_STATUS.md) for complete deployment documentation.

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
- **[STRATEGIES.md](docs/STRATEGIES.md)** - Complete strategy guide
- **[BACKTESTING_METHODS.md](docs/BACKTESTING_METHODS.md)** - Validation methods with results
- **[MULTI_ARMED_BANDITS.md](docs/MULTI_ARMED_BANDITS.md)** - MAB theory and implementation

### AWS Lambda Documentation
- **[LAMBDA_DEPLOYMENT_STATUS.md](docs/LAMBDA_DEPLOYMENT_STATUS.md)** - Current deployment status and test results
- **[LAMBDA_IMPLEMENTATION_SUMMARY.md](docs/LAMBDA_IMPLEMENTATION_SUMMARY.md)** - Implementation details
- **[LAMBDA_PARTITIONS.md](docs/LAMBDA_PARTITIONS.md)** - Partition architecture
- **[DASHBOARD_DATA_GUIDE.md](docs/DASHBOARD_DATA_GUIDE.md)** - S3 output structure for dashboard

### Additional Documentation
- **[S3_DATA_RETRIEVAL.md](docs/S3_DATA_RETRIEVAL.md)** - AWS S3 data integration guide
- **[TRADING_FUNDAMENTALS.md](docs/TRADING_FUNDAMENTALS.md)** - Trading and finance fundamentals
- **[RISK_FREE_ASSET_INTEGRATION.md](docs/RISK_FREE_ASSET_INTEGRATION.md)** - FRED API integration

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
pytest --cov=src tests/  # With coverage
```

## 📊 Example Results

Sample performance metrics from validated benchmark strategies (see `results/` directory for complete results):

**Configuration**: 10-year backtest (2015-01-01 to 2024-12-31), quarterly rebalancing, 0.10% transaction costs, 5% soft rebalancing drift threshold

### Top Individual Strategies (by Sharpe Ratio)

| Rank | Strategy | Sharpe | Total Return | Max Drawdown | Final Value |
|------|----------|--------|--------------|--------------|-------------|
| 1 | Low Volatility | 1.94 | +8.7% | -3.1% | $108,737 |
| 2 | Max Diversification | 1.86 | +6.8% | -3.7% | $106,847 |
| 3 | Risk Parity | 1.63 | +6.1% | -5.1% | $106,082 |
| 4 | Global Min Variance | 1.58 | +5.2% | -2.4% | $105,205 |
| 5 | Inverse Volatility | 1.55 | +5.9% | -5.4% | $105,889 |
| 6 | Quintile Momentum | 1.50 | +14.5% | -14.3% | $114,536 |

### Multi-Armed Bandit Algorithms

All 4 MAB algorithms (UCB, Thompson Sampling, EXP3, Epsilon-Greedy) dynamically allocate across the 12 benchmark strategies, typically achieving enhanced risk-adjusted returns through adaptive strategy selection.

**Key Insights**:
- Risk-based strategies (Low Vol, Risk Parity, GMVP) deliver superior Sharpe ratios with lower drawdowns
- Momentum strategy achieves highest absolute returns but with higher volatility
- MAB algorithms adapt to changing market conditions and exploit top-performing strategies

See `results/comprehensive_benchmark_results.json` and `visualizations/` for complete analysis.

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

**Version**: 3.3.0 | **Last Updated**: January 15, 2026

## 🎉 Recent Updates

### Version 3.3.0 (January 2026) - Lambda Production Release
- ✅ **AWS Lambda Deployment** - 3 partitions running daily at 3:00 AM UTC
- ✅ **15 Benchmark Strategies** - Extended from 12 to 15 strategies (added Top-K Return, Top-K Sharpe, Inverse Variance)
- ✅ **Walk-Forward Backtesting** - Rolling 24-month training, 6-month test windows, 8 folds
- ✅ **EventBridge Automation** - Automatic daily execution with no manual intervention
- ✅ **S3 Results Pipeline** - Organized output structure for dashboard consumption
- ✅ **100% Success Rate** - All 45 backtests (15 strategies × 3 frequencies) passing
- ✅ **Lambda optimizations** - numpy-only implementations for Lambda compatibility

### Version 3.1.0 (January 2026)
- ✅ **Comprehensive Benchmark Suite** - Unified demo testing all strategies + 4 MAB algorithms
- ✅ **Epsilon-Greedy Algorithm** - Added 4th MAB algorithm with configurable exploration rate
- ✅ **Enhanced Visualizations** - Complete dashboard with NAV curves, drawdowns, allocation heatmaps

### Version 3.0.0 (December 2025)
- ✅ Validated and documented 12 benchmark strategies
- ✅ Implemented Multi-Armed Bandit algorithms (UCB, Thompson Sampling, EXP3, Epsilon-Greedy)
- ✅ Real-time trading system with state persistence and checkpoint management
- ✅ FRED API integration for dynamic risk-free rate updates
- ✅ Production-ready codebase with full documentation
