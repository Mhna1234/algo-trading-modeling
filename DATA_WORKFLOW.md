# Data Workflow Guide

This guide explains the new streamlined data workflow for the algo trading project.

## Overview

The project now uses a centralized data preparation approach:

1. **Download once** - Historical data from S3 (Nov 2015 - Nov 2025) is downloaded once
2. **Process once** - Data is cleaned and processed once
3. **Reuse everywhere** - All demo scripts use the pre-processed data

## Quick Start

### Step 1: Prepare Data (One-Time Setup)

Run the data preparation script to download and process all historical data:

```powershell
python scripts/prepare_data.py
```

This will:
- Download raw data from S3 (Nov 2015 - Nov 2025)
- Process and clean the data
- Save both raw and processed versions to disk
- Use the top 20 tickers by volume (configurable in the script)

**Output files:**
- `data/raw/raw_data_2015-11_2025-11.csv` - Raw OHLCV data
- `data/processed/full_data_2015-11_2025-11.csv` - Processed OHLCV data
- `data/processed/price_data_2015-11_2025-11.csv` - Processed price data (close prices)

### Step 2: Run Demos

After preparing the data, you can run any demo script:

```powershell
# Run backtesting methods demo
python examples/demo_backtesting_methods.py

# Run benchmark strategies comparison
python examples/demo_benchmark_strategies.py

# Run fast benchmark strategies (weekly rebalancing)
python examples/demo_benchmark_strategies_fast.py

# Run SVM regime switching strategy
python examples/demo_svm_regime_strategy.py
```

All demos now automatically load the pre-processed data and filter to their required date ranges.

## Data Sources

### S3 Data
- **Source:** AWS S3 bucket `data-retrieval-output`
- **Available range:** November 2015 - November 2025
- **Format:** Parquet files (one per month)
- **Path pattern:** `history-data/YYYY-MM.parquet`

### Pre-processed Data
- **Default tickers:** Top 20 stocks by volume (AAPL, MSFT, GOOGL, etc.)
- **Format:** CSV files with MultiIndex columns
- **Location:** `data/processed/`

## Customization

### Using Different Tickers

Edit `scripts/prepare_data.py` and modify the `DEFAULT_TICKERS` list:

```python
DEFAULT_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL',  # Your custom tickers
    # ... add more
]
```

Then re-run the preparation script.

### Using Different Date Ranges

The demos automatically filter the pre-processed data to their required date ranges. You can modify the date ranges in each demo file:

```python
# In demo file
start_date = '2020-01-01'  # Change as needed
end_date = '2023-12-31'    # Change as needed
```

### Loading Custom Date Ranges in Code

```python
from src.data_loader import load_preprocessed_data

# Load all pre-processed data
full_data, price_data = load_preprocessed_data()

# Load specific date range
full_data, price_data = load_preprocessed_data(
    start='2020-01-01',
    end='2023-12-31'
)
```

## Alternative: Load Individual Months from S3

You can still download individual months directly from S3 if needed:

```powershell
# Load a single month
python scripts/load_s3_data.py --year 2020 --month 1

# Load a date range
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 3

# Load full available range
python scripts/load_s3_data.py --start-year 2015 --start-month 11 --end-year 2025 --end-month 11
```

## Benefits of This Approach

1. **Faster demos** - No need to download data from yfinance every time
2. **Consistent data** - All demos use the same dataset
3. **Cost efficient** - Download from S3 once instead of multiple yfinance API calls
4. **Better control** - Easy to manage which tickers and date ranges to use
5. **Offline work** - Once data is prepared, no internet needed to run demos

## Troubleshooting

### "Pre-processed data not found" error

Run the data preparation script:
```powershell
python scripts/prepare_data.py
```

### AWS credentials error

Make sure your AWS credentials are configured. See `QUICKSTART_S3.md` for details.

### Missing ticker in results

The ticker might not be in the top 20 by volume. Edit `DEFAULT_TICKERS` in `scripts/prepare_data.py` to include it.

## Project Structure

```
algo-trading-modeling/
├── data/
│   ├── raw/                    # Raw S3 data (after prepare_data.py)
│   └── processed/              # Processed data (after prepare_data.py)
├── scripts/
│   ├── prepare_data.py         # Main data preparation script
│   └── load_s3_data.py         # Alternative: load specific S3 months
├── examples/
│   ├── demo_backtesting_methods.py
│   ├── demo_benchmark_strategies.py
│   ├── demo_benchmark_strategies_fast.py
│   └── demo_svm_regime_strategy.py
└── src/
    └── data_loader.py          # Contains load_preprocessed_data()
```

## Migration Notes

### Old Workflow
```python
# Old way - downloads from yfinance every time
from src.data_loader import load_data
full_data, price_data = load_data(tickers, start_date, end_date)
```

### New Workflow
```python
# New way - uses pre-processed data
from src.data_loader import load_preprocessed_data
full_data, price_data = load_preprocessed_data(start=start_date, end=end_date)
```

The old `load_data()` function still works if you need to download fresh data from yfinance for specific tickers.
