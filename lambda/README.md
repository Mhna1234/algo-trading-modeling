# Lambda Deployment Directory

This directory contains all AWS Lambda-related files for the benchmark calculation system.

## Directory Structure

```
lambda/
├── handlers/                           # Lambda function handlers
│   ├── lambda_function.py             # Original single function (deprecated)
│   ├── lambda_function_partition_1.py # Partition 1: Strategies 1-5
│   ├── lambda_function_partition_2.py # Partition 2: Strategies 6-10
│   └── lambda_function_partition_3.py # Partition 3: Strategies 11-15
├── scripts/                            # Deployment and setup scripts
│   ├── deploy_lambda.sh               # Main deployment script (bash)
│   ├── trigger_all.sh                 # Trigger all partitions manually
│   └── setup_eventbridge.sh           # EventBridge trigger setup
├── tests/                              # Test files
│   ├── test_lambda_local.py           # Local testing (original function)
│   ├── test_lambda_partition.py       # Partition testing
│   ├── response1.json                 # Test output from partition 1
│   ├── response2.json                 # Test output from partition 2
│   └── response3.json                 # Test output from partition 3
├── requirements-lambda.txt             # Lambda-specific dependencies
└── README.md                           # This file
```

## Quick Start

### Deploy All 3 Partitions

From the **project root directory**:

```bash
./lambda/scripts/deploy_lambda.sh
```

This will:
1. Install dependencies from `lambda/requirements-lambda.txt`
2. Package source code from `src/`
3. Create 3 deployment ZIPs (one per partition)
4. Upload to S3 and deploy to AWS Lambda
5. Configure environment variables

### Set Up EventBridge Triggers

```bash
./lambda/scripts/setup_eventbridge.sh
```

This will:
1. Create 3 EventBridge rules (one per partition)
2. Schedule all to run daily at 3:00 AM UTC
3. Add Lambda invocation permissions

## Testing

### Test Locally

```bash
# Test original function (deprecated)
python lambda/tests/test_lambda_local.py

# Test all 3 partitions
python lambda/tests/test_lambda_partition.py
```

### Test on AWS

```bash
# Test Partition 1
aws lambda invoke \
    --function-name benchmark-calculator-partition-1 \
    --region eu-north-1 \
    lambda/tests/response1.json

# Test Partition 2
aws lambda invoke \
    --function-name benchmark-calculator-partition-2 \
    --region eu-north-1 \
    lambda/tests/response2.json

# Test Partition 3
aws lambda invoke \
    --function-name benchmark-calculator-partition-3 \
    --region eu-north-1 \
    lambda/tests/response3.json
```

## Lambda Functions

### Partition 1: Passive + Heuristic (Strategies 1-5)
- **Function**: `benchmark-calculator-partition-1`
- **Strategies**: Buy & Hold, Equal Weight, Top-K Return, Top-K Sharpe, Quintile Momentum
- **Runtime**: ~5.7 minutes
- **Memory**: 3GB
- **Handler**: `lambda/handlers/lambda_function_partition_1.py`

### Partition 2: Factor + Risk-Based (Strategies 6-10)
- **Function**: `benchmark-calculator-partition-2`
- **Strategies**: Quintile Low Vol, Mean Reversion, GMVP, Inverse Vol, Inverse Variance
- **Runtime**: ~6.1 minutes
- **Memory**: 3GB
- **Handler**: `lambda/handlers/lambda_function_partition_2.py`

### Partition 3: Risk-Based + Optimization (Strategies 11-15)
- **Function**: `benchmark-calculator-partition-3`
- **Strategies**: Risk Parity, Max Decorrelation, Most Diversified, Sharpe Max, CVaR Min
- **Runtime**: ~14.7 minutes
- **Memory**: 3GB
- **Handler**: `lambda/handlers/lambda_function_partition_3.py`

## Configuration

### Environment Variables

All Lambda functions use these environment variables:

```bash
OUTPUT_BUCKET=benchmarks-modelling-output
OUTPUT_PREFIX=benchmarks-output
DATA_YEARS=5
```

### AWS Configuration

- **Region**: eu-north-1 (Stockholm)
- **Runtime**: Python 3.11
- **Memory**: 3008 MB (3GB)
- **Timeout**: 900 seconds (15 minutes)
- **IAM Role**: LambdaBenchmarkExecutionRole

## Deployment Details

### Package Size
Each partition creates an ~80MB deployment ZIP containing:
- Python 3.11 dependencies (numpy, pandas, boto3, etc.)
- Source code from `src/` directory
- Partition-specific handler

### Deployment Process
1. Dependencies installed to `lambda/lambda_package/` (created in project root during build) using pip
2. Source code copied from `src/`
3. Handler copied from `lambda/handlers/lambda_function_partition_N.py` to `lambda/lambda_package/lambda_function.py`
4. ZIP created and uploaded to S3
5. Lambda function updated with new code

**Note:** `lambda/lambda_package/` is a temporary build artifact created in the project root during deployment and is excluded from git via `.gitignore`.

### S3 Buckets
- **Input**: `data-retrieval-output` (reads market data)
- **Output**: `benchmarks-modelling-output` (writes results)
- **Deployment**: `benchmarks-modelling-output/lambda/` (stores deployment ZIPs)

## Monitoring

### Check Deployment Status

```bash
# List all partition functions
aws lambda list-functions --region eu-north-1 \
    --query 'Functions[?contains(FunctionName, `partition`)].{Name:FunctionName, Runtime:Runtime, LastModified:LastModified}'

# Check EventBridge rules
aws events list-rules --name-prefix benchmark-daily-trigger --region eu-north-1
```

### View Logs

```bash
# Real-time logs for partition 1
aws logs tail /aws/lambda/benchmark-calculator-partition-1 --region eu-north-1 --follow

# Recent errors for all partitions
for i in 1 2 3; do
    echo "=== Partition $i Errors ==="
    aws logs filter-log-events \
        --log-group-name /aws/lambda/benchmark-calculator-partition-${i} \
        --region eu-north-1 \
        --filter-pattern "ERROR"
done
```

## Documentation

For more details, see:
- **[Implementation Summary](../docs/LAMBDA_IMPLEMENTATION_SUMMARY.md)** - Complete implementation details
- **[Deployment Guide](../docs/LAMBDA_BENCHMARK_DEPLOYMENT.md)** - Step-by-step deployment
- **[Partition Architecture](../docs/LAMBDA_PARTITIONS.md)** - Architecture and strategy distribution
- **[Deployment Status](../docs/LAMBDA_DEPLOYMENT_STATUS.md)** - Current production status

## Troubleshooting

### Deployment fails with "command not found"

All scripts should be run from the project root directory:
```bash
cd /path/to/algo-trading-modeling

# Deploy all Lambda partitions
./lambda/scripts/deploy_lambda.sh

# Trigger all partitions manually
./lambda/scripts/trigger_all.sh

# Setup EventBridge triggers
./lambda/scripts/setup_eventbridge.sh

# Setup IAM role (first-time setup)
./lambda/scripts/setup_iam_role.sh

# Setup custom daily schedule
./lambda/scripts/setup_daily_schedule.sh 5  # for 5 AM UTC
```

### Import error: numpy "importing from source directory"

This error occurs when `numpy/conftest.py` is included in the deployment package. The deployment script automatically removes this file. If you see this error:
```bash
# Re-run deployment to rebuild package with fix
./lambda/scripts/deploy_lambda.sh
```

### Package size > 250MB

The package should be ~80MB. If larger:
```bash
# Check what's taking space
du -sh lambda/lambda_package/*

# Clean and rebuild
rm -rf lambda/lambda_package
./lambda/scripts/deploy_lambda.sh
```

### Lambda timeout

Partition 3 runs close to the 15-minute limit. If it times out:
- Reduce `DATA_YEARS` from 5 to 3
- Remove daily (D) rebalancing frequency
- Split Partition 3 into 2 smaller partitions

---

**Last Updated**: January 14, 2026
**Version**: v3.3.0
**Status**: Production Ready
