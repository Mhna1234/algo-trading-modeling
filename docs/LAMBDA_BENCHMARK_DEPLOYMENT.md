# AWS Lambda Benchmark Deployment Guide

## Overview

This guide covers deploying 15 benchmark strategies to AWS Lambda for daily calculations. The Lambda function reads market data from S3, runs backtests with 3 rebalancing frequencies, and outputs results for dashboard consumption.

**Status**: 🧪 **Production Trial** (January 2026)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Lambda Function                      │
│              benchmark-daily-calculator                     │
│                    (Python 3.11)                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  15 Numpy-Only Benchmark Strategies                   │  │
│  │  - BuyAndHold, EqualWeight, Quintiles, etc.          │  │
│  │  - 3 Rebalancing Frequencies each (D, W, M)          │  │
│  │  - Total: 45 backtests per execution                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  Memory: 3GB | Timeout: 15 min | Runtime: ~3-5 min         │
└─────┬─────────────────────────────────────────────┬─────────┘
      │                                           │
      │ Read Data                                 │ Write Results
      ▼                                           ▼
┌──────────────────┐                    ┌────────────────────────┐
│   S3 Bucket      │                    │     S3 Bucket         │
│ data-retrieval   │                    │benchmarks-modelling-   │
│                  │                    │       output          │
│ - sp500_prices/  │                    │                        │
│ - preprocessed/  │                    │ ├─ latest/            │
│                  │                    │ │  └─ summary.json    │
│                  │                    │ ├─ {strategy}/        │
│                  │                    │ │  ├─ D/{date}.json   │
│                  │                    │ │  ├─ W/{date}.json   │
│                  │                    │ │  └─ M/{date}.json   │
│                  │                    │ └─ history/           │
│                  │                    │    └─ {date}/         │
└──────────────────┘                    └────────────────────────┘
      ▲                                           │
      │                                           │
┌──────────────────┐                    ┌────────────────────────┐
│  EventBridge     │                    │      Dashboard         │
│   Schedule       │                    │        Team            │
│                  │                    │                        │
│ Daily 9 PM UTC   │                    │   Reads JSON outputs   │
│ cron(0 21 * * ?*)│                    │   Visualizes results   │
└──────────────────┘                    └────────────────────────┘
```

---

## Prerequisites

### 1. AWS Setup
- AWS Account with CLI configured
- IAM user with permissions:
  - `lambda:*`
  - `iam:CreateRole`, `iam:AttachRolePolicy`
  - `s3:GetObject`, `s3:PutObject`
  - `events:PutRule`, `events:PutTargets`
  - `logs:CreateLogGroup`, `logs:PutLogEvents`

### 2. S3 Buckets
- **Input**: `data-retrieval` (must exist with market data)
- **Output**: `benchmarks-modelling-output` (will be created if missing)

### 3. Local Environment
- Python 3.11+
- AWS CLI installed and configured
- PowerShell (Windows) or Bash (Linux/Mac)

---

## Quick Start (< 10 minutes)

### Windows

```powershell
# 1. Clone repository (if not already done)
git clone <repo-url>
cd algo-trading-modeling

# 2. Checkout Lambda benchmarks branch
git checkout feature/complete-lambda-benchmarks

# 3. Deploy to AWS
.\deploy_lambda.ps1
```

### Linux/Mac

```bash
# 1. Clone repository
git clone <repo-url>
cd algo-trading-modeling

# 2. Checkout Lambda benchmarks branch
git checkout feature/complete-lambda-benchmarks

# 3. Make deployment script executable
chmod +x deploy_lambda.sh

# 4. Deploy to AWS
./deploy_lambda.sh
```

**That's it!** The script will:
1. Create deployment package (~150MB)
2. Set up IAM role with S3 permissions
3. Deploy Lambda function
4. Configure daily EventBridge trigger (9 PM UTC)
5. Run test invocation

---

## Manual Deployment Steps

If you prefer manual control or encounter issues with automated deployment:

### Step 1: Create Deployment Package

```bash
# Install dependencies
mkdir lambda_package
pip install -r requirements-lambda.txt \
    -t lambda_package \
    --platform manylinux2014_x86_64 \
    --only-binary=:all:

# Copy source code
cp lambda_function.py lambda_package/
cp -r src lambda_package/

# Create ZIP
cd lambda_package
zip -r ../lambda_deployment.zip .
cd ..

# Verify size (should be < 250MB)
ls -lh lambda_deployment.zip
```

### Step 2: Create IAM Role

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
      "Resource": ["arn:aws:s3:::data-retrieval/*", "arn:aws:s3:::data-retrieval"]
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

### Step 3: Create Lambda Function

```bash
# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name LambdaBenchmarkExecutionRole --query 'Role.Arn' --output text)

# Create function
aws lambda create-function \
    --function-name benchmark-daily-calculator \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_deployment.zip \
    --timeout 900 \
    --memory-size 3008 \
    --environment "Variables={DATA_BUCKET=data-retrieval,OUTPUT_BUCKET=benchmarks-modelling-output}" \
    --description "Daily benchmark strategy calculations (15 strategies x 3 frequencies)"
```

### Step 4: Set Up Daily Trigger

```bash
# Create EventBridge rule (daily 9 PM UTC)
aws events put-rule \
    --name daily-benchmark-calculation \
    --schedule-expression "cron(0 21 * * ? *)" \
    --description "Trigger benchmark calculations daily"

# Add Lambda permission
aws lambda add-permission \
    --function-name benchmark-daily-calculator \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn $(aws events describe-rule --name daily-benchmark-calculation --query 'Arn' --output text)

# Link rule to Lambda
FUNCTION_ARN=$(aws lambda get-function --function-name benchmark-daily-calculator --query 'Configuration.FunctionArn' --output text)

aws events put-targets \
    --rule daily-benchmark-calculation \
    --targets "Id=1,Arn=$FUNCTION_ARN"
```

---

## Testing & Monitoring

### Manual Invocation

```bash
# Test invocation
aws lambda invoke \
    --function-name benchmark-daily-calculator \
    --payload '{"test": true}' \
    response.json

# View response
cat response.json | jq .
```

### Check Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/benchmark-daily-calculator --follow

# View recent errors
aws logs filter-log-events \
    --log-group-name /aws/lambda/benchmark-daily-calculator \
    --filter-pattern "ERROR"
```

### Verify S3 Output

```bash
# Check latest summary
aws s3 cp s3://benchmarks-modelling-output/latest/summary.json - | jq .

# List all strategy outputs
aws s3 ls s3://benchmarks-modelling-output/ --recursive

# Download specific strategy result
aws s3 cp s3://benchmarks-modelling-output/equal_weight/M/2026-01-09.json .
```

---

## Output Format

### Summary File

Location: `s3://benchmarks-modelling-output/latest/summary.json`

```json
{
  "execution_date": "2026-01-09",
  "execution_timestamp": "2026-01-09T21:05:32.123Z",
  "total_strategies": 15,
  "rebalance_frequencies": ["D", "W", "M"],
  "total_backtests": 45,
  "successful": 45,
  "failed": 0,
  "results": [...]
}
```

### Individual Strategy Result

Location: `s3://benchmarks-modelling-output/{strategy}/{frequency}/{date}.json`

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
    "start": "2023-01-01",
    "end": "2026-01-09",
    "days": 756
  }
}
```

---

## Cost Estimate

### Lambda Costs

**Configuration:**
- Memory: 3GB
- Runtime: ~5 minutes per execution
- Executions: 30 per month (daily)

**Pricing:**
- Compute: 3GB × 300s × 30 executions = 27,000 GB-seconds
  - First 400,000 GB-seconds: FREE
  - Cost: **$0.00**

- Requests: 30 per month
  - First 1M requests: FREE
  - Cost: **$0.00**

**S3 Costs:**
- Storage: ~100KB per strategy × 15 × 3 frequencies × 30 days = 135MB/month
  - Cost: ~$0.003/month

- Requests: ~45 PUTs + 1 GET per day × 30 = 1,380 requests/month
  - Cost: ~$0.007/month

**Total Monthly Cost: < $0.01** (effectively free within AWS free tier)

**After Free Tier** (if exceeded):
- Lambda compute: ~$0.50/month
- S3: ~$0.05/month
- **Total: ~$0.55/month**

### Comparison to EC2

| Service | Monthly Cost | Setup Time | Maintenance |
|---------|-------------|-----------|-------------|
| **Lambda (This)** | **~$0.55** | **< 1 day** | **Zero** |
| EC2 t3.medium | ~$35 | 4 weeks | Weekly updates |

**Lambda saves $34.45/month (99% cost reduction)**

---

## Troubleshooting

### Issue: Deployment package > 250MB

**Solution**:
```bash
# Check what's taking space
du -sh lambda_package/*

# Ensure using requirements-lambda.txt (not requirements.txt)
pip install -r requirements-lambda.txt -t lambda_package

# Remove unnecessary files
rm -rf lambda_package/*.dist-info
rm -rf lambda_package/__pycache__
```

### Issue: Lambda timeout (15-minute limit exceeded)

**Solution**:
- Reduce number of strategies per execution
- Increase memory allocation (faster CPU)
- Split into multiple Lambdas (e.g., one per frequency)

**Check runtime**:
```bash
aws logs filter-log-events \
    --log-group-name /aws/lambda/benchmark-daily-calculator \
    --filter-pattern "Duration"
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

### Issue: Strategy calculation errors

**Check logs**:
```bash
# Find error details
aws logs filter-log-events \
    --log-group-name /aws/lambda/benchmark-daily-calculator \
    --filter-pattern "ERROR" \
    --start-time $(date -d '1 hour ago' +%s)000
```

---

## Production Readiness Checklist

- [ ] Lambda function deployed successfully
- [ ] IAM role has correct S3 permissions
- [ ] EventBridge trigger configured for daily execution
- [ ] Test invocation completes successfully
- [ ] S3 output bucket accessible by dashboard team
- [ ] CloudWatch Logs enabled and accessible
- [ ] All 45 backtests (15 strategies × 3 frequencies) complete within 15 minutes
- [ ] Output JSON format validated by dashboard team
- [ ] Error handling tested (missing data, API failures, etc.)
- [ ] Cost monitoring set up (AWS Cost Explorer)
- [ ] Documentation shared with dashboard team

---

## Next Steps

1. **Week 1**: Deploy and monitor daily executions
2. **Week 2**: Validate output quality with dashboard team
3. **Week 3**: Optimize performance (reduce runtime/memory if possible)
4. **Week 4**: Decision point - promote to production or fall back to EC2

**If successful**: This becomes the permanent deployment
**If issues**: Migrate to EC2 with full-featured strategies (see EC2_DEPLOYMENT_PLAN.md)

---

## Related Documentation

- **Lambda Deployment Guide**: [LAMBDA_DEPLOYMENT_GUIDE.md](../src/strategies/benchmarks/LAMBDA_DEPLOYMENT_GUIDE.md) - Technical comparison
- **Implementation Status**: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) - Current trial status
- **EC2 Fallback Plan**: [EC2_DEPLOYMENT_PLAN.md](EC2_DEPLOYMENT_PLAN.md) - Alternative deployment
- **Strategy Reference**: [benchmarks/README.md](../src/strategies/benchmarks/README.md) - All 15 strategies

---

**Author**: Algo Trading Team
**Date**: January 2026
**Status**: Production Trial
