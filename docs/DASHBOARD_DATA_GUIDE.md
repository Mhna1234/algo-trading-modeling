# Dashboard Data Guide - Benchmark Results

This guide explains the S3 data structure and file formats for integrating benchmark results into your dashboard.

## S3 Bucket Structure

```
s3://benchmarks-modelling-output/benchmarks-output/
├── latest/
│   └── summary.json                    # Latest execution (all 45 results)
├── history/
│   └── {date}/
│       └── summary.json                # Historical execution summaries
├── strategies/
│   └── {strategy_name}/
│       └── {frequency}/
│           └── {date}.json             # Complete results (metrics + time series + weights)
├── timeseries/
│   └── {strategy_name}/
│       └── {frequency}/
│           └── {date}.csv              # Daily performance data
└── weights/
    └── {strategy_name}/
        └── {frequency}/
            └── {date}.csv              # Portfolio weights (rebalance dates only)
```

## File Formats

### 1. **summary.json** - All Strategies Overview

**Location:** `benchmarks-output/latest/summary.json`

**Use Case:** Get latest results for all 45 backtests at once

**Structure:**
```json
{
  "execution_date": "2026-01-13",
  "execution_timestamp": "2026-01-13T22:00:00.000000",
  "total_strategies": 15,
  "rebalance_frequencies": ["D", "W", "M"],
  "total_backtests": 45,
  "successful": 45,
  "failed": 0,
  "results": [
    {
      "strategy_name": "equal_weight",
      "rebalance_freq": "W",
      "status": "success",
      "metrics": { ... },
      "time_series": { ... },
      "weights": { ... }
    },
    ...
  ]
}
```

**Python Example:**
```python
import boto3
import json

s3 = boto3.client('s3')
obj = s3.get_object(Bucket='benchmarks-modelling-output',
                    Key='benchmarks-output/latest/summary.json')
data = json.loads(obj['Body'].read())

# Get all successful strategies
for result in data['results']:
    if result['status'] == 'success':
        print(f"{result['strategy_name']} ({result['rebalance_freq']}): "
              f"Return={result['metrics']['total_return']:.2%}")
```

---

### 2. **timeseries CSV** - Daily Performance Data

**Location:** `benchmarks-output/timeseries/{strategy}/{freq}/{date}.csv`

**Use Case:** Plot equity curves, returns, drawdowns over time

**Columns:**
- `date` - Trading date (every day)
- `equity` - Portfolio value
- `returns` - Daily return
- `drawdowns` - Drawdown from peak

**Frequency:** **EVERY TRADING DAY** (~252 rows per year)

**Example:**
```csv
date,equity,returns,drawdowns
2024-01-01,1000000.0,0.0000,0.0000
2024-01-02,1002000.0,0.0020,-0.0015
2024-01-03,998000.0,-0.0040,-0.0025
2024-01-04,1005000.0,0.0070,0.0000
```

**Python Example:**
```python
import pandas as pd
import boto3
from io import StringIO

s3 = boto3.client('s3')
key = 'benchmarks-output/timeseries/equal_weight/W/2026-01-13.csv'
obj = s3.get_object(Bucket='benchmarks-modelling-output', Key=key)
df = pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))

# Plot equity curve
import matplotlib.pyplot as plt
df['date'] = pd.to_datetime(df['date'])
df.plot(x='date', y='equity', title='Equal Weight - Weekly Rebalancing')
plt.show()
```

---

### 3. **weights CSV** - Portfolio Positions

**Location:** `benchmarks-output/weights/{strategy}/{freq}/{date}.csv`

**Use Case:** Show portfolio composition, track rebalancing decisions

**Columns:**
- `date` - Rebalance date (NOT every day!)
- `{TICKER}` - Weight for each stock (0.0 to 1.0)
- `CASH` - Cash weight

**Frequency:**
- **Daily:** ~252 rows/year (every day)
- **Weekly:** ~52 rows/year (every 7 days)
- **Monthly:** ~12 rows/year (every 30 days)

**Example (Weekly):**
```csv
date,AAPL,MSFT,GOOGL,AMZN,META,...,CASH
2024-01-07,0.333333,0.333333,0.333333,0.0,0.0,...,0.0
2024-01-14,0.334468,0.343579,0.321953,0.0,0.0,...,0.0
2024-01-21,0.336140,0.339832,0.324028,0.0,0.0,...,0.0
```

**Important Notes:**
- ✅ Weights saved ONLY on rebalance dates (not every day)
- ✅ Weights rounded to 6 decimal places
- ✅ All weights sum to 1.0 (including CASH)
- ❌ Between rebalances, weights are NOT in this file (use previous rebalance weights)

**Python Example:**
```python
import pandas as pd
import boto3
from io import StringIO

s3 = boto3.client('s3')
key = 'benchmarks-output/weights/equal_weight/M/2026-01-13.csv'
obj = s3.get_object(Bucket='benchmarks-modelling-output', Key=key)
df = pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))

# Get latest portfolio composition
latest_weights = df.iloc[-1]
top_holdings = latest_weights.sort_values(ascending=False).head(10)
print(f"Top 10 Holdings on {latest_weights['date']}:")
print(top_holdings)
```

---

### 4. **Strategy JSON** - Complete Results

**Location:** `benchmarks-output/strategies/{strategy}/{freq}/{date}.json`

**Use Case:** Get all data (metrics + time series + weights) in one file

**Structure:**
```json
{
  "strategy_name": "equal_weight",
  "rebalance_freq": "W",
  "status": "success",
  "metrics": {
    "total_return": 1.4084,
    "cagr": 0.0,
    "volatility": 0.0,
    "sharpe_ratio": 3.0230,
    "sortino_ratio": 4.0875,
    "max_drawdown": -0.2626,
    "calmar_ratio": 3.2137,
    "win_rate": 0.5884,
    "avg_turnover": 0.0174
  },
  "time_series": {
    "dates": ["2024-01-01", "2024-01-02", ...],
    "equity": [1000000.0, 1002000.0, ...],
    "returns": [0.0, 0.002, ...],
    "drawdowns": [0.0, -0.0015, ...]
  },
  "weights": {
    "dates": ["2024-01-07", "2024-01-14", ...],
    "weights": {
      "AAPL": [0.333333, 0.334468, ...],
      "MSFT": [0.333333, 0.343579, ...],
      ...
    }
  },
  "backtest_period": {
    "start": "2024-01-01",
    "end": "2024-12-31",
    "days": 252
  }
}
```

---

## Strategy Names

| Strategy ID | Description |
|------------|-------------|
| `buy_and_hold` | Buy & Hold Benchmark |
| `equal_weight` | Equal Weight Portfolio |
| `top_k_return` | Top-K by Return |
| `top_k_sharpe` | Top-K by Sharpe Ratio |
| `quintile_momentum` | Quintile Momentum |
| `quintile_low_vol` | Quintile Low Volatility |
| `mean_reversion` | Mean Reversion |
| `global_min_variance` | Global Minimum Variance |
| `inverse_volatility` | Inverse Volatility Weighted |
| `inverse_variance` | Inverse Variance Weighted |
| `risk_parity` | Risk Parity |
| `max_decorrelation` | Maximum Decorrelation |
| `most_diversified` | Most Diversified Portfolio |
| `sharpe_maximization` | Sharpe Ratio Maximization |
| `cvar_minimization` | CVaR Minimization |

## Rebalancing Frequencies

- `D` - Daily rebalancing (~252 rebalances/year)
- `W` - Weekly rebalancing (~52 rebalances/year)
- `M` - Monthly rebalancing (~12 rebalances/year)

---

## Common Dashboard Use Cases

### 1. **Show Latest Performance for All Strategies**

**Recommended:** Use `latest/summary.json`

**Why:** Single file contains all 45 results

```python
# Fetch latest summary
s3 = boto3.client('s3')
obj = s3.get_object(Bucket='benchmarks-modelling-output',
                    Key='benchmarks-output/latest/summary.json')
summary = json.loads(obj['Body'].read())

# Create performance table
for result in summary['results']:
    print(f"{result['strategy_name']:25} {result['rebalance_freq']:3} "
          f"Return: {result['metrics']['total_return']:7.2%}  "
          f"Sharpe: {result['metrics']['sharpe_ratio']:5.2f}")
```

### 2. **Plot Equity Curve for Single Strategy**

**Recommended:** Use `timeseries/{strategy}/{freq}/{date}.csv`

**Why:** Lightweight CSV, easy to plot

```python
# Download CSV
key = f'benchmarks-output/timeseries/equal_weight/W/2026-01-13.csv'
obj = s3.get_object(Bucket='benchmarks-modelling-output', Key=key)
df = pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))

# Plot
df['date'] = pd.to_datetime(df['date'])
plt.plot(df['date'], df['equity'])
plt.title('Equal Weight - Weekly Rebalancing')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
```

### 3. **Show Current Portfolio Positions**

**Recommended:** Use `weights/{strategy}/{freq}/{date}.csv`

**Why:** Latest row = current positions

```python
# Download weights
key = f'benchmarks-output/weights/equal_weight/M/2026-01-13.csv'
obj = s3.get_object(Bucket='benchmarks-modelling-output', Key=key)
df = pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))

# Get latest weights (last rebalance)
latest = df.iloc[-1]
weights = latest.drop('date').sort_values(ascending=False)

# Show top 10 holdings
print(f"Portfolio as of {latest['date']}:")
for ticker, weight in weights.head(10).items():
    if weight > 0:
        print(f"  {ticker}: {weight:.2%}")
```

### 4. **Compare Weekly vs Monthly Rebalancing**

**Recommended:** Use `timeseries/*.csv` for both frequencies

```python
# Load both
weekly = pd.read_csv(StringIO(s3.get_object(
    Bucket='benchmarks-modelling-output',
    Key='benchmarks-output/timeseries/equal_weight/W/2026-01-13.csv'
)['Body'].read().decode('utf-8')))

monthly = pd.read_csv(StringIO(s3.get_object(
    Bucket='benchmarks-modelling-output',
    Key='benchmarks-output/timeseries/equal_weight/M/2026-01-13.csv'
)['Body'].read().decode('utf-8')))

# Plot comparison
plt.plot(pd.to_datetime(weekly['date']), weekly['equity'], label='Weekly')
plt.plot(pd.to_datetime(monthly['date']), monthly['equity'], label='Monthly')
plt.legend()
```

---

## Important Notes

### Weights File Structure

⚠️ **Weights are ONLY saved on rebalance dates, not every day!**

**Example:** For Weekly rebalancing:
- ✅ Weights file has ~52 rows per year (one per week)
- ❌ Weights file does NOT have 252 rows (not daily)

**Why?**
- Weights only change when portfolio rebalances
- Between rebalances, weights stay the same (portfolio drifts with prices)
- This saves memory and accurately represents the strategy

**For Dashboard:**
- To show weights on ANY day: Use the most recent rebalance date ≤ that day
- Example: If you need weights for Jan 10, use the last rebalance before Jan 10

### Data Updates

- **Frequency:** Daily at 3:00 AM UTC
- **Processing Time:** ~10-15 minutes
- **Latest Data:** Check `latest/summary.json` for most recent execution_date

### File Sizes

| File Type | Approximate Size |
|-----------|-----------------|
| summary.json (all 45) | ~45 MB |
| Single strategy JSON | ~1 MB |
| timeseries CSV | ~30 KB |
| weights CSV (Weekly) | ~200 KB |
| weights CSV (Monthly) | ~50 KB |

---

## Need Help?

**For Questions:**
- Lambda deployment status: See [LAMBDA_DEPLOYMENT_STATUS.md](LAMBDA_DEPLOYMENT_STATUS.md)
- Implementation details: See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)

**Common Issues:**
1. **"Weights file too small"** → This is correct! Weights only on rebalance dates
2. **"Missing weights for some days"** → Use previous rebalance date's weights
3. **"Different results each day"** → Walk-forward uses rolling windows, slight variations are normal
