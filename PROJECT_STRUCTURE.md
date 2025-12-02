# Project Structure v2.2.0

Complete file structure and module descriptions for the Algorithmic Trading System.

## 📁 Directory Overview

```
algo-trading-modeling/
│
├── src/                           # Core library modules
├── examples/                      # Example scripts and demos
├── tests/                         # Test suite
├── docs/                          # Documentation
├── data/                          # Data storage
│   ├── raw/                       # Downloaded raw data
│   └── processed/                 # Processed data files
├── notebooks/                     # Jupyter notebooks
├── visualizations/                # Generated charts and plots
└── [root files]                   # Configuration and documentation
```

## 🔧 Core Modules (`src/`)

### Portfolio Engine & Backtesting

**`portfolio_engine.py`** (853 lines) - **Production Portfolio Engine**
- Main backtesting engine for strategy evaluation
- **v2.2.0 FIX:** Corrected transaction cost calculation (line 502)
- Features:
  - Strategy-agnostic design
  - Configurable rebalancing (daily, weekly, monthly, quarterly)
  - Transaction costs: 10 bps per rebalance (FIXED - was double-counting)
  - Slippage modeling
  - Comprehensive metrics tracking
- **Key Methods:**
  - `run_backtest()` - Execute backtest
  - `_rebalance()` - Portfolio rebalancing logic
  - `_update_metrics()` - Real-time metric calculation

**`optimizer.py`** (1115 lines) - **Portfolio Optimization**
- **v2.2.0 ENHANCED:** Risk Parity CCD algorithm (90% fewer failures)
- 6 optimization methods: MVO, Sharpe, Risk Parity, CVaR, Max Diversification, GMVP

**`strategy_wrapper.py`** (2209 lines) - **12 Production Strategies**
- **v2.2.0:** All strategies validated with positive returns
- Includes warmup periods, NaN handling, date-specific calculations

## 📊 12 Validated Strategies

1. Equal Weight
2. Buy and Hold
3. Momentum
4. Mean Reversion
5. Inverse Volatility
6. CVaR Minimization
7. GMVP
8. Maximum Diversification
9. Maximum Decorrelation
10. Time Series Momentum
11. Moving Average Crossover
12. Linear Regression

## 📚 Documentation

**Key Files:**
- `README.md` - Main documentation (v2.2.0)
- `docs/STRATEGIES.md` - Strategy guide (12 strategies)
- `RELEASE_NOTES_v2.2.0.md` - v2.2.0 release notes
- `CHANGES_SUMMARY.md` - Complete change log
- `QUICK_START_LIBRARY.md` - Quick start guide

---

**Version:** 2.2.0 ✅ **Production Ready**
