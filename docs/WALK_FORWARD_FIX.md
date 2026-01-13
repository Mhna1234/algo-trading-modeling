# Walk-Forward Backtesting Implementation Fix

## Problem

Walk-forward backtesting was initially attempted but failed due to insufficient data after data cleaning.

### Root Cause

**Data Cleaning Was Too Aggressive:**
- The original code used `prices.dropna(how='any')` which drops ALL rows (days) that have ANY missing values
- With 503 stocks in the universe, if even ONE stock was missing data on a given day, that entire day was removed
- Result: From 1,274 raw days → only 362 clean days (~12 months)

**Walk-Forward Requirements:**
- Minimum: 24 months training + 6 months testing = 30 months total
- With only 12 months available, walk-forward returned `None`

### Example of the Problem

```
Raw S3 Data (5 years, 2020-12 to 2025-12):
├── Total days: 1,274 days (42 months) ✓
├── Total stocks: 503
└── Completeness: 99.2% (only 5,073 missing values out of 640,822)

After Original Cleaning (dropna(how='any')):
├── Days remaining: 362 days (12 months) ✗
├── Stocks: 503
└── Problem: 62% of historical data lost!

Walk-Forward Result: FAILED (need 30+ months, have 12 months)
```

## Solution

### 1. Smarter Data Cleaning

Instead of dropping days with ANY missing values, we:
1. **Drop stocks with >10% missing data** (insufficient history for that stock)
2. Forward-fill remaining gaps (up to 5 days) to handle trading halts
3. Then drop remaining rows with NaNs

```python
# OLD: Too aggressive
prices = prices.dropna(how='any')  # Drops days with ANY missing stock

# NEW: Smart filtering
# Drop stocks with >10% missing data
missing_pct_per_stock = prices.isna().sum() / len(prices)
stocks_with_sufficient_data = missing_pct_per_stock[missing_pct_per_stock < 0.10].index
prices = prices[stocks_with_sufficient_data]

# Forward fill gaps, then drop remaining NaNs
prices = prices.fillna(method='ffill', limit=5)
prices = prices.dropna(how='any')
```

### 2. Results After Fix

```
After Smart Cleaning:
├── Days: 1,099 days (36 months) ✓
├── Stocks: 497 (6 stocks dropped with insufficient history)
├── Historical data retained: 86% vs 28% before
└── Walk-Forward: SUCCESS! (36 months > 30 months minimum)
```

### 3. Increased DATA_YEARS

Changed from 3 → 5 years to ensure sufficient buffer:
- 5 years of raw data → ~36 months clean data
- Provides enough for walk-forward (30 months) + extra buffer

## Impact

### Before Fix (Vanilla Backtest Only)
- ❌ Walk-forward: Failed (insufficient data)
- ✓ Vanilla backtest: Working
- Data range: ~12 months (362 days)
- Stocks: 503

### After Fix (Walk-Forward Working)
- ✓ Walk-forward: SUCCESS
- ✓ Vanilla backtest: Still working
- Data range: ~36 months (1,099 days)
- Stocks: 497
- **More robust results** with time-series cross-validation

## Testing

Local tests confirm:
```bash
$ python test_lambda_local.py
...
✓ All backtests completed successfully
✓ Weights are correctly filtered to rebalance dates only

Total: 4/4 tests passed
🎉 All tests passed! Ready for AWS deployment.
```

## Lambda Configuration

Updated environment variables:
```bash
DATA_YEARS=5  # Was 3
```

Expected runtime: ~10-15 minutes per execution (increased from ~5 minutes due to walk-forward optimization)

## Summary

**The Fix:**
1. Changed data cleaning from "drop days with ANY missing" → "drop stocks with >10% missing"
2. Increased DATA_YEARS from 3 → 5
3. Result: 362 days → 1,099 days of clean data (36 months)
4. Walk-forward now works with robust time-series cross-validation

**Trade-off:**
- 503 stocks → 497 stocks (6 stocks dropped with poor data coverage)
- This is acceptable - we want quality data over quantity
