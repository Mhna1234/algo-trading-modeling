# Quick Reference: New Data Workflow

## TL;DR

**One-time setup:**
```powershell
python scripts/prepare_data.py
```

**Run demos:**
```powershell
python examples/demo_backtesting_methods.py
python examples/demo_benchmark_strategies.py
python examples/demo_benchmark_strategies_fast.py
python examples/demo_svm_regime_strategy.py
```

## What Changed?

### ✅ Before
- Each demo downloaded its own data from yfinance
- Slow, redundant downloads
- Different tickers per demo

### ✅ Now
- Download S3 data once (2015-11 to 2025-11)
- Process once, use everywhere
- Consistent tickers across all demos
- Much faster demo execution

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

### Run Demos
```powershell
# All demos now use pre-processed data
python examples/demo_backtesting_methods.py
python examples/demo_benchmark_strategies.py
python examples/demo_benchmark_strategies_fast.py
python examples/demo_svm_regime_strategy.py
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

## Benefits

- ⚡ **Faster** - No downloads during demo execution
- 🔄 **Consistent** - Same data across all demos
- 💰 **Cost-efficient** - One S3 download instead of multiple yfinance calls
- 📴 **Offline-ready** - Work without internet after setup
- 🎯 **Centralized** - Easy to manage tickers and dates

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
