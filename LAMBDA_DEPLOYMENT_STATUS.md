# Lambda Benchmark Deployment - Current Status

**Date:** January 11, 2026  
**Project:** Automated Daily Benchmark Strategy Calculations  
**Team:** Algo Trading Modeling Team

---

## 🎯 Project Goal

Deploy an AWS Lambda function that automatically runs daily to:
1. Load latest market data from S3
2. Calculate 15 benchmark strategies with 3 rebalancing frequencies (Daily, Weekly, Monthly)
3. Output results to S3 for dashboard consumption

---

## ✅ What's Completed

### 1. Lambda Function Deployment
- **Status:** ✅ Fully deployed and tested
- **Function Name:** `benchmark-daily-calculator`
- **Runtime:** Python 3.11
- **Memory:** 3GB
- **Timeout:** 15 minutes (actual runtime ~5 minutes)
- **Package Size:** 80MB
- **Region:** eu-north-1

### 2. Code Implementation
- ✅ All 15 benchmark strategies implemented (numpy-only, no scipy/cvxpy)
- ✅ Data loading from `s3://data-retrieval-output/history-data/`
- ✅ Automatic detection of latest available data
- ✅ 45 backtests (15 strategies × 3 frequencies)
- ✅ All dependencies made optional for Lambda compatibility
- ⚠️ **Currently uses vanilla backtesting** (walk-forward optimization in progress)

**Strategies Included:**
1. Buy & Hold
2. Equal Weight
3. Top-K Return
4. Top-K Sharpe
5. Quintile Momentum
6. Quintile Low Volatility
7. Mean Reversion
8. Global Min Variance
9. Inverse Volatility
10. Inverse Variance
11. Risk Parity
12. Max Decorrelation
13. Most Diversified
14. Sharpe Maximization
15. CVaR Minimization

### 3. S3 Output Structure
- ✅ Organized directory structure created
- ✅ Old scattered files cleaned up

**New Structure:**
```
s3://benchmarks-modelling-output/
├── benchmarks-output/              # 📊 Dashboard pulls from here
│   ├── latest/
│   │   └── summary.json            # Latest run (all 45 results)
│   ├── history/
│   │   └── {date}/
│   │       └── summary.json        # Historical runs
│   └── strategies/
│       └── {strategy_name}/
│           └── {frequency}/
│               └── {date}.json     # Individual strategy results
└── lambda/
    └── lambda_deployment.zip       # Deployment package
```

### 4. Test Results
- ✅ Last successful run: **2026-01-11 at 09:04 UTC**
- ✅ **45/45 backtests successful** (100% success rate)
- ✅ Results saved to organized S3 structure
- ✅ Data loaded: ~1.5 years (2024-03-27 to 2025-09-05)

---

## ⏳ Pending: Automatic Scheduling

### Current Limitation
- ❌ Lambda function does **NOT run automatically**
- ❌ Must be invoked manually
- ❌ No daily schedule configured

### What's Needed
**Waiting on:** AWS administrator to grant EventBridge permissions

**Once permissions are granted, will run:**
```bash
# Create daily schedule (3 AM UTC)
aws events put-rule --name benchmark-daily-trigger \
  --schedule-expression "cron(0 3 * * ? *)" --state ENABLED

# Connect Lambda to schedule
aws lambda add-permission --function-name benchmark-daily-calculator \
  --statement-id AllowEventBridgeInvoke --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:eu-north-1:466787509184:rule/benchmark-daily-trigger

# Set Lambda as target
aws events put-targets --rule benchmark-daily-trigger \
  --targets "Id"="1","Arn"="arn:aws:lambda:eu-north-1:466787509184:function:benchmark-daily-calculator"
```

**Scheduled Time:** 3:00 AM UTC daily (2 hours after data retrieval completes)

---

## ⚠️ In Progress: Walk-Forward Backtesting

**Current:** Using vanilla backtesting method for production stability
**Next:** Implementing walk-forward validation for more robust results

Walk-forward backtesting provides:
- Out-of-sample validation
- Reduced overfitting risk
- More realistic performance estimates

**Timeline:** To be completed in next iteration

---

## 📊 For Dashboard Team

### How to Access Results

**Latest results (updated daily once scheduled):**
```bash
# Download all latest results
aws s3 sync s3://benchmarks-modelling-output/benchmarks-output/ ./dashboard-data/

# Or just the summary
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/latest/summary.json ./summary.json
```

**Python example:**
```python
import boto3, json

s3 = boto3.client('s3')
response = s3.get_object(
    Bucket='benchmarks-modelling-output',
    Key='benchmarks-output/latest/summary.json'
)
summary = json.loads(response['Body'].read())

print(f"Last run: {summary['execution_timestamp']}")
print(f"Successful: {summary['successful']}/{summary['total_backtests']}")
```

### File Structure
- **summary.json** (~45MB): All 45 backtest results with metrics, time series, weights
- **Individual strategy files** (~700KB each): Detailed results per strategy per frequency

### Data Accumulation
- **Daily:** 45 new files + 1 summary (one per strategy per frequency)
- **After 30 days:** 1,350 strategy files + 30 summaries
- **Storage:** ~75MB per day, ~2.3GB per month

---

## 🔄 How It Works (Once Scheduled)

### Daily Workflow
```
1. EventBridge triggers Lambda at 3:00 AM UTC
2. Lambda checks s3://data-retrieval-output/history-data/ for latest data
3. Loads last 3 years of data automatically
4. Runs 45 backtests (~5 minutes)
5. Saves to s3://benchmarks-modelling-output/benchmarks-output/
   ├── latest/summary.json (overwritten)
   ├── strategies/{strategy}/{freq}/2026-01-12.json (new)
   └── history/2026-01-12/summary.json (new)
```

### Automatic Features
- ✅ **Auto data detection:** Always uses latest available data
- ✅ **No manual trigger needed:** Runs daily automatically (once scheduled)
- ✅ **Dated files:** Historical tracking preserved
- ✅ **Latest pointer:** Dashboard always gets current results

---

## 📁 Documentation

- **[S3_OUTPUT_STRUCTURE.md](S3_OUTPUT_STRUCTURE.md):** Complete S3 structure documentation
- **[deploy_lambda.sh](deploy_lambda.sh):** Deployment script for updates
- **[setup_daily_schedule.sh](setup_daily_schedule.sh):** EventBridge schedule setup
- **[lambda_function.py](lambda_function.py):** Lambda handler with inline documentation

---

## 🚀 Next Steps

1. **Waiting:** Administrator grants EventBridge permissions to `Haya_S` user
2. **Setup:** Run EventBridge commands to create daily schedule
3. **Verify:** Confirm first automatic run tomorrow at 3:00 AM UTC
4. **Monitor:** Check CloudWatch logs and S3 output for daily runs
5. **Optimize:** Implement walk-forward backtesting for better validation

---

## 💡 Manual Testing (Until Schedule Active)

Run manually anytime:
```bash
aws lambda invoke --function-name benchmark-daily-calculator \
  --payload file://test-event.json response.json
```

---

## ⚙️ Technical Details

**Lambda Configuration:**
- Runtime: Python 3.11
- Memory: 3GB
- Timeout: 900 seconds (15 minutes)
- Role: `LambdaBenchmarkExecutionRole`
- Region: eu-north-1

**Environment Variables:**
- `OUTPUT_BUCKET`: benchmarks-modelling-output
- `OUTPUT_PREFIX`: benchmarks-output
- `DATA_YEARS`: 3

**IAM Permissions:**
- ✅ S3 read: data-retrieval-output
- ✅ S3 write: benchmarks-modelling-output
- ✅ CloudWatch Logs
- ❌ EventBridge (pending)

**Backtesting Method:**
- Current: Vanilla (simple historical backtest)
- In Progress: Walk-forward (time-series cross-validation)

---

**Status:** Production-ready with vanilla backtesting, pending automatic scheduling setup and walk-forward optimization.  
**Contact:** Haya_S for deployment questions
