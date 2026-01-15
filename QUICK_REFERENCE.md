# Quick Reference Guide

## TL;DR

**One-time setup:**
```bash
python scripts/prepare_data.py
```

**Run main demos:**
```bash
# Comprehensive benchmark (12 strategies + 4 MAB algorithms)
python examples/comprehensive_benchmark_demo.py

# Quick benchmark comparison
python examples/benchmark_strategies_demo.py

# Real-time trading platform
python examples/dynamic_trading_demo.py --mode backtest
```

**Launch dashboard:**
```bash
streamlit run dashboard.py
```

---

## Project Status (v3.3.0)

### Current State: Production Ready

| Component | Status |
|-----------|--------|
| Lambda Deployment | **Operational** - 3 partitions running daily |
| Benchmark Strategies | 15 strategies validated |
| MAB Algorithms | 4 algorithms (UCB, Thompson, EXP3, Epsilon-Greedy) |
| Walk-Forward Backtesting | Implemented (24-mo train, 6-mo test) |
| EventBridge Scheduling | Active (3:00 AM UTC daily) |
| S3 Integration | Input + Output pipelines working |

### Lambda Test Results (January 14, 2026)
- **Partition 1:** 15/15 backtests successful (5.7 min)
- **Partition 2:** 15/15 backtests successful (6.1 min)
- **Partition 3:** 15/15 backtests successful (14.7 min)
- **Total:** 45/45 backtests, 100% success rate

---

## Commands

### Data Preparation
```bash
# Download and process S3 data (2015-2025)
python scripts/prepare_data.py

# Load specific month range
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2025 --end-month 12
```

### Run Demos
```bash
# Comprehensive benchmark suite (all strategies + MAB)
python examples/comprehensive_benchmark_demo.py

# Quick benchmark comparison
python examples/benchmark_strategies_demo.py

# Real-time trading platform
python examples/dynamic_trading_demo.py --mode backtest
python examples/dynamic_trading_demo.py --mode simulation
python examples/dynamic_trading_demo.py --mode live

# MAB walk-forward evaluation
python examples/mab_walk_forward_demo.py

# Advanced backtesting methods
python examples/demo_backtesting_methods.py

# Other demos
python examples/demo_mab_stress_testing.py
python examples/demo_rewards.py
python examples/demo_soft_rebalancing.py
```

### Validate Strategies
```bash
python scripts/validate_12_benchmark_strategies.py
```

### Launch Dashboard
```bash
streamlit run dashboard.py
```

---

## AWS Lambda Commands

### Manual Invocation
```bash
# Test individual partitions
aws lambda invoke --function-name benchmark-calculator-partition-1 \
  --region eu-north-1 response1.json

aws lambda invoke --function-name benchmark-calculator-partition-2 \
  --region eu-north-1 response2.json

aws lambda invoke --function-name benchmark-calculator-partition-3 \
  --region eu-north-1 response3.json
```

### Check Status
```bash
# View EventBridge rules
aws events list-rules --name-prefix benchmark-daily-trigger --region eu-north-1

# View Lambda logs
aws logs tail /aws/lambda/benchmark-calculator-partition-1 --since 1h --region eu-north-1
```

### Download Results
```bash
# Sync all results to local
aws s3 sync s3://benchmarks-modelling-output/benchmarks-output/ ./dashboard-data/

# Download specific partition summary
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/history/2026-01-14/partition_1_summary.json ./
```

---

## 15 Benchmark Strategies

### Partition 1: Passive & Heuristic
1. Buy & Hold
2. Equal Weight (1/N)
3. Top-K Return
4. Top-K Sharpe
5. Quintile Momentum

### Partition 2: Factor & Risk-Based
6. Quintile Low Volatility
7. Mean Reversion
8. Global Minimum Variance
9. Inverse Volatility
10. Inverse Variance

### Partition 3: Optimization
11. Risk Parity
12. Max Decorrelation
13. Most Diversified
14. Sharpe Maximization
15. CVaR Minimization

---

## Multi-Armed Bandit Algorithms

| Algorithm | Description | Best For |
|-----------|-------------|----------|
| **UCB** | Upper Confidence Bound | Balanced exploration/exploitation |
| **Thompson Sampling** | Bayesian posterior sampling | Stationary environments |
| **EXP3** | Adversarial bandit | Non-stationary markets |
| **Epsilon-Greedy** | Simple ε-exploration | Quick testing |

---

## Configuration

### Setup Config File
```bash
cp config/trading_config.yaml.example config/trading_config.yaml
```

### Key Configuration Options
```yaml
execution:
  mode: "simulation"  # backtest, simulation, or live

trading:
  initial_capital: 100000
  transaction_cost_bps: 10.0
  rebalance_frequency: "M"  # D, W, M, or Q

bandit:
  type: "ucb"  # ucb, thompson, exp3, epsilon_greedy
  burn_in_periods: 12
  reward_type: "sharpe"
```

### Environment Variables
```bash
# AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=eu-north-1

# FRED API (optional)
export FRED_API_KEY=your_fred_key
```

---

## S3 Output Structure

```
s3://benchmarks-modelling-output/benchmarks-output/
├── strategies/{strategy}/{freq}/{date}.json  # Complete metrics & time series
├── timeseries/{strategy}/{freq}/{date}.csv   # Equity curve, returns, drawdowns
├── weights/{strategy}/{freq}/{date}.csv      # Portfolio weights
└── history/{date}/partition_*.json           # Execution summaries
```

---

## Troubleshooting

**"Pre-processed data not found"**
→ Run `python scripts/prepare_data.py`

**AWS credentials error**
→ Set environment variables or check ~/.aws/credentials

**Lambda timeout**
→ Partition 3 runs ~15 min. Check CloudWatch logs for errors.

**Missing ticker**
→ Add to `DEFAULT_TICKERS` in `prepare_data.py` and re-run

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Project overview |
| [LAMBDA_DEPLOYMENT_STATUS.md](docs/LAMBDA_DEPLOYMENT_STATUS.md) | Lambda status & test results |
| [STRATEGIES.md](docs/STRATEGIES.md) | Strategy descriptions |
| [MULTI_ARMED_BANDITS.md](docs/MULTI_ARMED_BANDITS.md) | MAB algorithms |
| [DASHBOARD_DATA_GUIDE.md](docs/DASHBOARD_DATA_GUIDE.md) | S3 output format |

---

**Version:** 3.3.0 | **Last Updated:** January 15, 2026
