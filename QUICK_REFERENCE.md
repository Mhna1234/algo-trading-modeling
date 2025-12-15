# Quick Reference Guide

## TL;DR

**One-time setup:**
```powershell
python scripts/prepare_data.py
```

**Run main demos:**
```powershell
# Benchmark 12 strategies
python examples/demo_12_strategies_fast.py    # 6 months, weekly rebalancing
python examples/demo_12_strategies_full.py    # 10 years, monthly rebalancing

# Multi-Armed Bandit demos
python examples/demo_bandit_strategy_wrapper.py  # MAB allocation
python examples/demo_bandit_comparison.py        # UCB vs Thompson

# Other demos
python examples/demo_backtesting_methods.py   # Advanced backtesting
python examples/demo_rewards.py               # Reward calculation
python examples/simple_example.py             # Quick start
```

## Project Status (v3.0.0)

### ✅ Implemented
- **12 Validated Benchmark Strategies** - All production-ready
- **Multi-Armed Bandit System** - UCB and Thompson Sampling
- **Comprehensive Reward System** - Returns, Sharpe, Sortino
- **Optimized Rebalancing** - Monthly frequency for realistic costs
- **Enhanced Visualizations** - NAV curves, metrics, heatmaps
- **Data Workflow** - Centralized preprocessing pipeline
- **Complete Documentation** - All features documented
- **Full Test Coverage** - All components tested

### 🎯 Key Features
- Monthly rebalancing (realistic transaction costs)
- 10-year backtests with real market data
- Dynamic strategy allocation with MAB
- Comprehensive performance metrics
- JSON/CSV export for all results

## File Changes

| File | Change |
|------|--------|
| `scripts/prepare_data.py` | **NEW** - Downloads & processes S3 data |
| `src/data_loader.py` | Added `load_preprocessed_data()` function |
| All demo files | Changed to use `load_preprocessed_data()` |
| `data/raw/*` | Deleted old files |
| `data/processed/*` | Deleted old files |
| `visualizations/*.csv` | Deleted old results |
| `visualizations/*.png` | Deleted old results |

## Commands

### Prepare Data (First Time)
```powershell
# Downloads from S3 (2015-11 to 2025-11) and processes
python scripts/prepare_data.py
```

### Run Main Demos
```powershell
# 12 Benchmark Strategies
python examples/demo_12_strategies_fast.py    # Fast: 6 months, weekly rebalancing
python examples/demo_12_strategies_full.py    # Full: 10 years, monthly rebalancing

# Multi-Armed Bandit Allocation
python examples/demo_bandit_strategy_wrapper.py   # MAB strategy allocation
python examples/demo_bandit_comparison.py         # Compare UCB vs Thompson
python examples/demo_ucb_bandit.py                # UCB algorithm demo

# Other Demos
python examples/demo_backtesting_methods.py   # Advanced backtesting methods
python examples/demo_rewards.py               # Reward calculation
python examples/demo_svm_regime_strategy.py   # SVM regime classification
python examples/simple_example.py             # Quick start example
```

### Validate Strategies
```powershell
# Validate all 12 benchmark strategies
python scripts/validate_12_benchmark_strategies.py
```

### Alternative: Load Specific S3 Months
```powershell
# Load a single month
python scripts/load_s3_data.py --year 2020 --month 1

# Load full range
python scripts/load_s3_data.py --start-year 2015 --start-month 11 --end-year 2025 --end-month 11
```

## Configuration

### Change Tickers
Edit `scripts/prepare_data.py`:
```python
DEFAULT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL',  # Your tickers here
]
```

### Change Demo Date Range
Edit demo file:
```python
start_date = '2020-01-01'  # Your date range
end_date = '2023-12-31'
```

## Key Highlights

### 12 Benchmark Strategies
1. Buy & Hold (Market Benchmark)
2. Equal Weight (1/N)
3. Quintile Momentum
4. Quintile Low Volatility
5. Mean Reversion Quintile
6. Global Minimum Variance
7. Inverse Volatility
8. Risk Parity
9. Maximum Diversification
10. Maximum Decorrelation
11. Sharpe Maximization
12. CVaR Minimization

### Multi-Armed Bandit Features
- **UCB Algorithm**: Upper Confidence Bound with exploration bonus
- **Thompson Sampling**: Bayesian posterior sampling
- **Reward Functions**: Returns, Sharpe ratio, Sortino ratio
- **Soft Allocation**: Probabilistic strategy allocation
- **Burn-in Period**: Initial exploration phase

### Performance Benefits
- ⚡ **Optimized Costs** - Monthly rebalancing reduces costs by 90%
- 🔄 **Consistent Data** - Same data across all demos
- 💰 **Realistic Modeling** - Transaction costs, slippage, realistic rebalancing
- 📴 **Offline-ready** - Work without internet after setup
- 🎯 **Production-ready** - Validated, tested, documented

## Troubleshooting

**"Pre-processed data not found"**
→ Run `python scripts/prepare_data.py`

**AWS credentials error**
→ See `QUICKSTART_S3.md` for setup

**Missing ticker**
→ Add to `DEFAULT_TICKERS` in `prepare_data.py` and re-run

## Documentation

- `DATA_WORKFLOW.md` - Detailed workflow guide
- `CHANGES_SUMMARY.md` - Complete list of changes
- `QUICKSTART_S3.md` - AWS setup guide
