# AWS Lambda Benchmark Deployment Guide

## Overview

This guide covers deploying 15 benchmark strategies across 3 partitioned AWS Lambda functions for daily calculations. Each partition runs independently and in parallel, reading market data from S3, running backtests with 3 rebalancing frequencies, and outputting results for dashboard consumption.

**Status**: 🚀 **PRODUCTION READY** (v3.3.0 - January 2026)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    3 Lambda Partitions (Parallel)                   │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   Partition 1    │  │   Partition 2    │  │   Partition 3    │  │
│  │  Strategies 1-5  │  │  Strategies 6-10 │  │ Strategies 11-15 │  │
│  │                  │  │                  │  │                  │  │
│  │ • Buy & Hold     │  │ • Quintile Low   │  │ • Risk Parity    │  │
│  │ • Equal Weight   │  │   Vol            │  │ • Max Decor      │  │
│  │ • Top-K Return   │  │ • Mean Reversion │  │ • Most Diversif  │  │
│  │ • Top-K Sharpe   │  │ • GMVP           │  │ • Sharpe Max     │  │
│  │ • Quintile Mom   │  │ • Inverse Vol    │  │ • CVaR Min       │  │
│  │                  │  │ • Inverse Var    │  │                  │  │
│  │  Runtime: 5.7min │  │  Runtime: 6.1min │  │ Runtime: 14.7min │  │
│  │  15 backtests    │  │  15 backtests    │  │  15 backtests    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                      │
│  Memory: 3GB each | Timeout: 15 min | Total Runtime: ~15 min        │
└──────┬───────────────────────────────────────────────────┬──────────┘
       │                                                   │
       │ Read Data (5 years, 497 stocks)                  │ Write Results
       ▼                                                   ▼
┌──────────────────────┐                    ┌────────────────────────────┐
│   S3 Input Bucket    │                    │   S3 Output Bucket         │
│  data-retrieval-     │                    │ benchmarks-modelling-      │
│      output          │                    │        output              │
│                      │                    │                            │
│ history-data/        │                    │ benchmarks-output/         │
│  ├─ 2020-12.parquet  │                    │  ├─ strategies/            │
│  ├─ 2021-01.parquet  │                    │  │   └─ {strat}/{freq}/    │
│  ├─ ...              │                    │  │       └─ {date}.json    │
│  └─ 2025-12.parquet  │                    │  ├─ timeseries/            │
│                      │                    │  │   └─ {strat}/{freq}/    │
│                      │                    │  │       └─ {date}.csv     │
│                      │                    │  ├─ weights/               │
│                      │                    │  │   └─ {strat}/{freq}/    │
│                      │                    │  │       └─ {date}.csv     │
│                      │                    │  └─ history/               │
│                      │                    │      └─ {date}/            │
│                      │                    │          ├─ partition_1.json│
│                      │                    │          ├─ partition_2.json│
│                      │                    │          └─ partition_3.json│
└──────────────────────┘                    └────────────────────────────┘
       ▲                                                   │
       │                                                   │
┌──────────────────────┐                    ┌────────────────────────────┐
│  EventBridge Rules   │                    │        Dashboard           │
│  (3 rules)           │                    │          Team              │
│                      │                    │                            │
│ • partition-1        │                    │   Reads JSON/CSV outputs   │
│ • partition-2        │                    │   Visualizes results       │
│ • partition-3        │                    │   Aggregates partitions    │
│                      │                    │                            │
│ Daily 3:00 AM UTC    │                    │                            │
│ cron(0 3 * * ? *)    │                    │                            │
└──────────────────────┘                    └────────────────────────────┘
```

---

## Prerequisites

### 1. AWS Setup
- AWS Account with CLI configured
- IAM user with permissions:
  - `lambda:*`
  - `iam:CreateRole`, `iam:AttachRolePolicy`
  - `s3:GetObject`, `s3:PutObject`
  - `events:PutRule`, `events:PutTargets`, `events:PutPermission`
  - `logs:CreateLogGroup`, `logs:PutLogEvents`

### 2. S3 Buckets
- **Input**: `data-retrieval-output` (must exist with monthly parquet files in `history-data/`)
- **Output**: `benchmarks-modelling-output` (will be created if missing)

### 3. Local Environment
- Python 3.11+
- AWS CLI installed and configured
- Bash shell (Git Bash on Windows, native on Linux/Mac)

---

## Quick Start (< 10 minutes)

### Deploy All 3 Partitions

```bash
# 1. Clone repository (if not already done)
git clone <repo-url>
cd algo-trading-modeling

# 2. Make deployment script executable
chmod +x lambda/scripts/deploy_lambda.sh

# 3. Deploy all 3 Lambda partitions
./lambda/scripts/deploy_lambda.sh
```

**This will:**
1. Create 3 deployment packages (~80MB each)
2. Upload to S3
3. Create/update 3 Lambda functions:
   - `benchmark-calculator-partition-1`
   - `benchmark-calculator-partition-2`
   - `benchmark-calculator-partition-3`
4. Set up IAM permissions

### Set Up EventBridge Triggers

```bash
# Configure automatic daily execution for all 3 partitions
./lambda/scripts/setup_eventbridge.sh
```

**This will:**
1. Create 3 EventBridge rules (one per partition)
2. Schedule all to run at 3:00 AM UTC
3. Add Lambda invocation permissions

**That's it!** The system is now fully automated and will run daily at 3:00 AM UTC.

---

## Manual Deployment Steps

If you prefer manual control or encounter issues with automated deployment:

### Step 1: Create Deployment Packages (All 3 Partitions)

```bash
# Install dependencies (shared across all partitions)
rm -rf lambda_package
mkdir lambda_package
pip install -r lambda/requirements-lambda.txt \
    --target lambda_package \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade

# Copy source code (shared)
cp -r src lambda_package/

# Clean unnecessary files
cd lambda_package
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
# Remove test directories (pandas/pyarrow only, keep numpy/tests)
rm -rf pandas/tests pyarrow/tests 2>/dev/null || true
# IMPORTANT: Remove conftest.py to prevent numpy import error
rm -f numpy/conftest.py
cd ..

# Create ZIP for Partition 1
cp lambda/handlers/lambda_function_partition_1.py lambda_package/lambda_function.py
cd lambda_package
zip -r ../lambda/lambda_deployment_partition_1.zip . -q
cd ..

# Create ZIP for Partition 2
cp lambda/handlers/lambda_function_partition_2.py lambda_package/lambda_function.py
cd lambda_package
zip -r ../lambda/lambda_deployment_partition_2.zip . -q
cd ..

# Create ZIP for Partition 3
cp lambda/handlers/lambda_function_partition_3.py lambda_package/lambda_function.py
cd lambda_package
zip -r ../lambda/lambda_deployment_partition_3.zip . -q
cd ..

# Verify sizes (each should be ~80MB)
ls -lh lambda/lambda_deployment_partition_*.zip
```

### Step 2: Create IAM Role (One Time)

```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create role
aws iam create-role \
    --role-name LambdaBenchmarkExecutionRole \
    --assume-role-policy-document file://trust-policy.json

# Attach basic execution policy
aws iam attach-role-policy \
    --role-name LambdaBenchmarkExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create S3 access policy
cat > s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::data-retrieval-output/*",
        "arn:aws:s3:::data-retrieval-output"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::benchmarks-modelling-output/*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name LambdaBenchmarkExecutionRole \
    --policy-name S3BenchmarkAccess \
    --policy-document file://s3-policy.json
```

### Step 3: Create Lambda Functions (3 Partitions)

```bash
# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name LambdaBenchmarkExecutionRole --query 'Role.Arn' --output text)

# Create Partition 1
aws lambda create-function \
    --function-name benchmark-calculator-partition-1 \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_deployment_partition_1.zip \
    --timeout 900 \
    --memory-size 3008 \
    --region eu-north-1 \
    --environment "Variables={OUTPUT_BUCKET=benchmarks-modelling-output,OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}" \
    --description "Benchmark strategies 1-5 (Passive + Heuristic)"

# Create Partition 2
aws lambda create-function \
    --function-name benchmark-calculator-partition-2 \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_deployment_partition_2.zip \
    --timeout 900 \
    --memory-size 3008 \
    --region eu-north-1 \
    --environment "Variables={OUTPUT_BUCKET=benchmarks-modelling-output,OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}" \
    --description "Benchmark strategies 6-10 (Factor + Risk-Based)"

# Create Partition 3
aws lambda create-function \
    --function-name benchmark-calculator-partition-3 \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_deployment_partition_3.zip \
    --timeout 900 \
    --memory-size 3008 \
    --region eu-north-1 \
    --environment "Variables={OUTPUT_BUCKET=benchmarks-modelling-output,OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}" \
    --description "Benchmark strategies 11-15 (Risk-Based + Optimization)"
```

### Step 4: Set Up Daily Triggers (3 Rules)

```bash
# Create EventBridge rules for each partition (all at 3:00 AM UTC)
for i in 1 2 3; do
    aws events put-rule \
        --name benchmark-daily-trigger-partition-${i} \
        --schedule-expression "cron(0 3 * * ? *)" \
        --state ENABLED \
        --region eu-north-1 \
        --description "Trigger benchmark partition ${i} daily at 3 AM UTC"

    # Add Lambda permission
    aws lambda add-permission \
        --function-name benchmark-calculator-partition-${i} \
        --statement-id AllowEventBridgeInvoke \
        --action lambda:InvokeFunction \
        --principal events.amazonaws.com \
        --region eu-north-1 \
        --source-arn $(aws events describe-rule --name benchmark-daily-trigger-partition-${i} --region eu-north-1 --query 'Arn' --output text)

    # Link rule to Lambda
    FUNCTION_ARN=$(aws lambda get-function --function-name benchmark-calculator-partition-${i} --region eu-north-1 --query 'Configuration.FunctionArn' --output text)

    aws events put-targets \
        --rule benchmark-daily-trigger-partition-${i} \
        --region eu-north-1 \
        --targets "Id=1,Arn=$FUNCTION_ARN"
done
```

---

## Testing & Monitoring

### Manual Invocation (Test Each Partition)

```bash
# Test Partition 1
aws lambda invoke \
    --function-name benchmark-calculator-partition-1 \
    --region eu-north-1 \
    response1.json

cat response1.json | jq .

# Test Partition 2
aws lambda invoke \
    --function-name benchmark-calculator-partition-2 \
    --region eu-north-1 \
    response2.json

cat response2.json | jq .

# Test Partition 3
aws lambda invoke \
    --function-name benchmark-calculator-partition-3 \
    --region eu-north-1 \
    response3.json

cat response3.json | jq .
```

### Check Logs

```bash
# Tail logs in real-time for each partition
aws logs tail /aws/lambda/benchmark-calculator-partition-1 --region eu-north-1 --follow
aws logs tail /aws/lambda/benchmark-calculator-partition-2 --region eu-north-1 --follow
aws logs tail /aws/lambda/benchmark-calculator-partition-3 --region eu-north-1 --follow

# View recent errors for all partitions
for i in 1 2 3; do
    echo "=== Partition $i Errors ==="
    aws logs filter-log-events \
        --log-group-name /aws/lambda/benchmark-calculator-partition-${i} \
        --region eu-north-1 \
        --filter-pattern "ERROR" | jq .
done
```

### Verify S3 Output

```bash
# Check partition summaries for today
TODAY=$(date +%Y-%m-%d)
aws s3 ls s3://benchmarks-modelling-output/benchmarks-output/history/${TODAY}/

# Download partition summaries
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/history/${TODAY}/partition_1_summary.json - | jq .
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/history/${TODAY}/partition_2_summary.json - | jq .
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/history/${TODAY}/partition_3_summary.json - | jq .

# List all strategy outputs
aws s3 ls s3://benchmarks-modelling-output/benchmarks-output/strategies/ --recursive

# Download specific strategy result
aws s3 cp s3://benchmarks-modelling-output/benchmarks-output/strategies/equal_weight/M/${TODAY}.json .
```

### Check EventBridge Status

```bash
# List all benchmark rules
aws events list-rules \
    --name-prefix benchmark-daily-trigger \
    --region eu-north-1 \
    --query 'Rules[].{Name:Name, State:State, Schedule:ScheduleExpression}'

# Check targets for each rule
for i in 1 2 3; do
    echo "=== Partition $i Targets ==="
    aws events list-targets-by-rule \
        --rule benchmark-daily-trigger-partition-${i} \
        --region eu-north-1
done
```

---

## Output Format

### Partition Summary Files

Location: `s3://benchmarks-modelling-output/benchmarks-output/history/{date}/partition_{1,2,3}_summary.json`

```json
{
  "statusCode": 200,
  "partition_id": 1,
  "execution_date": "2026-01-14",
  "duration_seconds": 343.8,
  "total_backtests": 15,
  "successful": 15,
  "failed": 0,
  "strategies": ["buy_and_hold", "equal_weight", "top_k_return", "top_k_sharpe", "quintile_momentum"],
  "results": [...]
}
```

### Individual Strategy Result

Location: `s3://benchmarks-modelling-output/benchmarks-output/strategies/{strategy}/{frequency}/{date}.json`

```json
{
  "strategy_name": "equal_weight",
  "rebalance_freq": "M",
  "status": "success",
  "metrics": {
    "total_return": 2.347,
    "cagr": 0.156,
    "volatility": 0.182,
    "sharpe_ratio": 0.857,
    "sortino_ratio": 1.203,
    "max_drawdown": -0.187,
    "calmar_ratio": 0.834,
    "win_rate": 0.623,
    "avg_turnover": 0.045
  },
  "time_series": {
    "dates": ["2023-01-01", "2023-01-02", ...],
    "equity": [1000000, 1005234, ...],
    "returns": [0.0, 0.005234, ...],
    "drawdowns": [0.0, -0.003, ...]
  },
  "weights": {
    "dates": ["2023-01-01", "2023-02-01", ...],
    "weights": {
      "AAPL": [0.02, 0.021, ...],
      "MSFT": [0.02, 0.019, ...]
    }
  },
  "backtest_period": {
    "start": "2021-04-14",
    "end": "2025-07-14",
    "days": 1552
  }
}
```

---

## Cost Estimate

### Lambda Costs (3 Partitions)

**Configuration:**
- Memory: 3GB per partition
- Runtime: Partition 1: 5.7 min, Partition 2: 6.1 min, Partition 3: 14.7 min
- Executions: 30 per month per partition (daily)

**Pricing (per month):**
- Partition 1: 3GB × 342s × 30 = 30,780 GB-seconds
- Partition 2: 3GB × 366s × 30 = 32,940 GB-seconds
- Partition 3: 3GB × 882s × 30 = 79,380 GB-seconds
- **Total**: 143,100 GB-seconds/month

**Cost Calculation:**
- First 400,000 GB-seconds: FREE
- Cost: **$0.00** (within free tier)

- Requests: 90 per month (3 partitions × 30 days)
  - First 1M requests: FREE
  - Cost: **$0.00**

**S3 Costs:**
- Storage: ~50MB per day × 30 days = 1.5GB/month
  - Cost: ~$0.035/month

- Requests: ~45 PUTs × 3 partitions × 30 days = 4,050 requests/month
  - Cost: ~$0.020/month

**Total Monthly Cost: ~$0.055** (within AWS free tier for Lambda)

**After Free Tier** (if exceeded):
- Lambda compute: ~$2.20/month ($0.0000166667 per GB-second × 143,100)
- Requests: ~$0.02/month
- S3: ~$0.055/month
- **Total: ~$2.28/month**

### Comparison

| Service | Monthly Cost | Setup Time | Maintenance | Success Rate |
|---------|-------------|-----------|-------------|--------------|
| **Lambda (3 Partitions)** | **~$2.28** | **< 1 day** | **Zero** | **100%** |
| Lambda (1 Function) | ~$2.40 | < 1 day | Zero | **0% (timeout)** |
| EC2 t3.medium | ~$35 | 4 weeks | Weekly | 100% |

**Lambda Partitions saves $32.72/month (93% cost reduction vs. EC2)**

---

## Troubleshooting

### Issue: Partition times out

**Solution**:
- Check which partition is timing out (likely Partition 3)
- Consider splitting Partition 3 further (3 strategies each)
- Reduce `DATA_YEARS` from 5 to 3
- Remove daily rebalancing frequency

**Check runtime**:
```bash
aws logs filter-log-events \
    --log-group-name /aws/lambda/benchmark-calculator-partition-3 \
    --region eu-north-1 \
    --filter-pattern "Duration"
```

### Issue: Partition missing from S3

**Solution**:
```bash
# Check which partition failed
aws lambda list-functions --region eu-north-1 \
    --query 'Functions[?contains(FunctionName, `partition`)].{Name:FunctionName, LastModified:LastModified}'

# Check logs for errors
for i in 1 2 3; do
    echo "=== Checking Partition $i ==="
    aws logs filter-log-events \
        --log-group-name /aws/lambda/benchmark-calculator-partition-${i} \
        --region eu-north-1 \
        --filter-pattern "ERROR" --max-items 5
done
```

### Issue: S3 Access Denied

**Solution**:
```bash
# Verify IAM role has correct policies
aws iam list-attached-role-policies --role-name LambdaBenchmarkExecutionRole
aws iam list-role-policies --role-name LambdaBenchmarkExecutionRole

# Check bucket policy
aws s3api get-bucket-policy --bucket benchmarks-modelling-output
```

### Issue: EventBridge not triggering

**Solution**:
```bash
# Check rule status
aws events describe-rule --name benchmark-daily-trigger-partition-1 --region eu-north-1

# Check targets
aws events list-targets-by-rule --rule benchmark-daily-trigger-partition-1 --region eu-north-1

# Manually trigger to test
aws events put-events --entries "[{\"Source\": \"manual\", \"DetailType\": \"test\", \"Detail\": \"{}\"}]"
```

### Issue: numpy import error "importing from source directory"

This error occurs when `numpy/conftest.py` is included in the deployment package:
```
Runtime.ImportModuleError: Unable to import module 'lambda_function':
numpy: Error importing numpy: you should not try to import numpy from its source directory
```

**Solution**:
```bash
# The deploy_lambda.sh script handles this automatically
# If you see this error, re-run deployment:
./lambda/scripts/deploy_lambda.sh

# Or manually remove the file from lambda_package before zipping:
rm -f lambda_package/numpy/conftest.py
```

---

## Production Readiness Checklist

- [x] All 3 Lambda partitions deployed successfully
- [x] IAM role has correct S3 permissions
- [x] EventBridge triggers configured for all 3 partitions
- [x] Test invocations complete successfully (100% success rate)
- [x] S3 output bucket accessible by dashboard team
- [x] CloudWatch Logs enabled and accessible
- [x] All 45 backtests (15 strategies × 3 frequencies) complete successfully
- [x] Output JSON/CSV format validated
- [x] Walk-forward backtesting operational (8 folds per backtest)
- [x] Automatic date detection working (`get_latest_available_month()`)
- [x] Error handling tested
- [x] Cost monitoring configured
- [x] Documentation complete

**Status**: ✅ **PRODUCTION READY**

---

## Related Documentation

- **Implementation Summary**: [LAMBDA_IMPLEMENTATION_SUMMARY.md](LAMBDA_IMPLEMENTATION_SUMMARY.md) - Complete details
- **Partition Architecture**: [LAMBDA_PARTITIONS.md](LAMBDA_PARTITIONS.md) - Strategy distribution
- **Deployment Status**: [LAMBDA_DEPLOYMENT_STATUS.md](LAMBDA_DEPLOYMENT_STATUS.md) - Current status
- **Dashboard Integration**: [DASHBOARD_DATA_GUIDE.md](DASHBOARD_DATA_GUIDE.md) - S3 output guide
- **Implementation Status**: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) - Overall project status

---

**Author**: Algo Trading Team
**Last Updated**: January 14, 2026
**Version**: v3.3.0
**Status**: Production Ready
