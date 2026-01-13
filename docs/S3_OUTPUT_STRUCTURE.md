# Benchmark Results S3 Output Structure

## Overview

All benchmark calculation results are now organized under the `benchmarks-output/` directory in the S3 bucket for easy dashboard access.

## Directory Structure

```
s3://benchmarks-modelling-output/
├── benchmarks-output/                    # 📊 ALL BENCHMARK RESULTS (Dashboard pulls from here)
│   ├── latest/
│   │   └── summary.json                  # Latest execution summary with all 45 backtest results
│   ├── history/
│   │   ├── 2026-01-10/
│   │   │   └── summary.json              # Historical execution from 2026-01-10
│   │   ├── 2026-01-11/
│   │   │   └── summary.json              # Historical execution from 2026-01-11
│   │   └── ...
│   └── strategies/
│       ├── buy_and_hold/
│       │   ├── D/
│       │   │   ├── 2026-01-10.json       # Daily frequency results
│       │   │   ├── 2026-01-11.json
│       │   │   └── ...
│       │   ├── W/
│       │   │   └── 2026-01-10.json       # Weekly frequency results
│       │   └── M/
│       │       └── 2026-01-10.json       # Monthly frequency results
│       ├── equal_weight/
│       │   └── ... (same structure)
│       ├── top_k_return/
│       ├── top_k_sharpe/
│       ├── quintile_momentum/
│       ├── quintile_low_vol/
│       ├── mean_reversion/
│       ├── global_min_variance/
│       ├── inverse_volatility/
│       ├── inverse_variance/
│       ├── risk_parity/
│       ├── max_decorrelation/
│       ├── most_diversified/
│       ├── sharpe_maximization/
│       └── cvar_minimization/
│           └── ... (same structure)
└── lambda/
    └── lambda_deployment.zip             # Lambda deployment package

```

## File Contents

### Summary File (`latest/summary.json`)

Contains aggregated results for all 45 backtests (15 strategies × 3 frequencies):

```json
{
  "execution_date": "2026-01-10",
  "execution_timestamp": "2026-01-10T22:12:55.047772",
  "total_strategies": 15,
  "rebalance_frequencies": ["D", "W", "M"],
  "total_backtests": 45,
  "successful": 45,
  "failed": 0,
  "results": [
    {
      "strategy_name": "buy_and_hold",
      "rebalance_freq": "D",
      "status": "success",
      "metrics": {
        "total_return": 0.15,
        "cagr": 0.12,
        "volatility": 0.18,
        "sharpe_ratio": 0.67,
        "sortino_ratio": 0.89,
        "max_drawdown": -0.25,
        "calmar_ratio": 0.48,
        "win_rate": 0.55,
        "avg_turnover": 0.02
      },
      "time_series": {
        "dates": ["2024-03-27", "2024-03-28", ...],
        "equity": [1000000, 1001500, ...],
        "returns": [0.0, 0.0015, ...],
        "drawdowns": [0.0, -0.001, ...]
      },
      "weights": {
        "dates": ["2024-03-27", ...],
        "weights": {"AAPL": [0.02, ...], "MSFT": [0.02, ...], ...}
      },
      "backtest_period": {
        "start": "2024-03-27",
        "end": "2025-09-05",
        "days": 362
      }
    },
    ... (44 more strategy results)
  ]
}
```

### Individual Strategy File (`strategies/{strategy}/{freq}/{date}.json`)

Contains detailed results for a single strategy + frequency combination:

```json
{
  "strategy_name": "equal_weight",
  "rebalance_freq": "M",
  "status": "success",
  "metrics": { ... },
  "time_series": { ... },
  "weights": { ... },
  "backtest_period": { ... }
}
```

## Dashboard Access

### Quick Start: Get Latest Results

```bash
# Download all latest benchmark results
aws s3 sync s3://benchmarks-modelling-output/benchmarks-output/latest/ ./dashboard/data/latest/
```

### Get Latest Summary Only

```bash
# Download just the summary file
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/latest/summary.json ./summary.json
```

### Get Specific Strategy Results

```bash
# Get all results for a specific strategy
aws s3 sync s3://benchmarks-modelling-output/benchmarks-output/strategies/equal_weight/ ./equal_weight/

# Get specific frequency for a strategy
aws s3 sync s3://benchmarks-modelling-output/benchmarks-output/strategies/equal_weight/D/ ./equal_weight_daily/
```

### Get Historical Results

```bash
# Get specific date's results
aws s3 sync s3://benchmarks-modelling-output/benchmarks-output/history/2026-01-10/ ./historical/2026-01-10/

# List all available dates
aws s3 ls s3://benchmarks-modelling-output/benchmarks-output/history/
```

## Python Access Example

```python
import boto3
import json

s3 = boto3.client('s3')

# Get latest summary
response = s3.get_object(
    Bucket='benchmarks-modelling-output',
    Key='benchmarks-output/latest/summary.json'
)
summary = json.loads(response['Body'].read())

print(f"Last run: {summary['execution_timestamp']}")
print(f"Successful backtests: {summary['successful']}/{summary['total_backtests']}")

# Access individual strategy
response = s3.get_object(
    Bucket='benchmarks-modelling-output',
    Key='benchmarks-output/strategies/equal_weight/D/2026-01-10.json'
)
strategy_data = json.loads(response['Body'].read())
print(f"Equal Weight Daily Sharpe: {strategy_data['metrics']['sharpe_ratio']}")
```

## Update Frequency

- Lambda runs daily (scheduled via EventBridge)
- New results are written to `benchmarks-output/latest/` (overwrites previous)
- Historical results are preserved in `benchmarks-output/history/{date}/`
- Individual strategy files accumulate over time (one per day per strategy per frequency)

## Storage Notes

- Summary files: ~45MB each (includes all 45 strategy results)
- Individual strategy files: ~700KB each
- Total daily output: ~45MB + (45 × 700KB) = ~75MB
- Monthly accumulation: ~2.3GB (if running daily)

## Migration from Old Structure

Old files (at root level) will remain but new executions use the organized structure:

```
Old: s3://benchmarks-modelling-output/buy_and_hold/D/2026-01-10.json
New: s3://benchmarks-modelling-output/benchmarks-output/strategies/buy_and_hold/D/2026-01-11.json
```

To clean up old files:
```bash
# List old structure files
aws s3 ls s3://benchmarks-modelling-output/ | grep -v "benchmarks-output\|lambda"

# Delete old structure (CAUTION: Review before running)
# aws s3 rm s3://benchmarks-modelling-output/buy_and_hold/ --recursive
# aws s3 rm s3://benchmarks-modelling-output/equal_weight/ --recursive
# ... etc
```
