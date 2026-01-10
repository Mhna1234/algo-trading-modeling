# Manual AWS Lambda Deployment Guide

Since your AWS user has limited IAM permissions, follow these steps to deploy via AWS Console.

## Prerequisites

✅ **Deployment package ready**: `lambda_deployment.zip` (101MB) - Already created!

## Step-by-Step Deployment

### Step 1: Create IAM Role (Ask AWS Administrator)

Ask your AWS administrator to create an IAM role with these settings:

**Role Name**: `LambdaBenchmarkExecutionRole`

**Trust Policy** (who can assume this role):
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

**Attached Policies**:
1. `AWSLambdaBasicExecutionRole` (managed policy for CloudWatch Logs)
2. Custom inline policy named `S3BenchmarkAccess`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::data-retrieval/*",
        "arn:aws:s3:::data-retrieval"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::benchmarks-modelling-output/*"
    }
  ]
}
```

### Step 2: Create Lambda Function (AWS Console)

1. **Go to AWS Lambda Console**: https://console.aws.amazon.com/lambda/
2. Click **"Create function"**
3. Select **"Author from scratch"**
4. Configure:
   - **Function name**: `benchmark-daily-calculator`
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
   - **Permissions**: Choose "Use an existing role" → Select `LambdaBenchmarkExecutionRole`
5. Click **"Create function"**

### Step 3: Upload Deployment Package

1. In the Lambda function page, scroll to **"Code source"**
2. Click **"Upload from"** → **".zip file"**
3. Click **"Upload"** and select `lambda_deployment.zip` (101MB)
4. Wait for upload to complete (~1-2 minutes)
5. Click **"Save"**

### Step 4: Configure Function Settings

1. Go to **"Configuration"** tab
2. Click **"General configuration"** → **"Edit"**:
   - **Memory**: 3008 MB (3 GB)
   - **Timeout**: 15 min 0 sec
   - Click **"Save"**

3. Click **"Environment variables"** → **"Edit"** → **"Add environment variable"**:
   - Key: `DATA_BUCKET`, Value: `data-retrieval`
   - Key: `OUTPUT_BUCKET`, Value: `benchmarks-modelling-output`
   - Click **"Save"**

### Step 5: Test the Function

1. Go to **"Test"** tab
2. Create new test event:
   - **Event name**: `test-benchmark`
   - **Event JSON**:
   ```json
   {
     "test": true,
     "execution_date": "2026-01-09"
   }
   ```
3. Click **"Save"**
4. Click **"Test"**
5. Wait 2-5 minutes for execution
6. Check results in **"Execution results"** tab

### Step 6: Set Up Daily Trigger (EventBridge)

1. Go to **"Function overview"**
2. Click **"Add trigger"**
3. Select **"EventBridge (CloudWatch Events)"**
4. Configure:
   - **Rule**: Create a new rule
   - **Rule name**: `daily-benchmark-calculation`
   - **Rule description**: `Trigger benchmark calculations daily at 9 PM UTC`
   - **Rule type**: Schedule expression
   - **Schedule expression**: `cron(0 21 * * ? *)`
     *(Daily at 9 PM UTC)*
5. Click **"Add"**

### Step 7: Verify Deployment

1. **Check S3 Output**:
   ```bash
   aws s3 ls s3://benchmarks-modelling-output/latest/
   ```

2. **Check CloudWatch Logs**:
   - Go to CloudWatch Logs console
   - Find log group: `/aws/lambda/benchmark-daily-calculator`
   - View recent executions

3. **Check Function Status**:
   ```bash
   aws lambda get-function --function-name benchmark-daily-calculator
   ```

## Expected Results

After first execution, you should see:
- ✅ 45 JSON files in S3 (15 strategies × 3 frequencies)
- ✅ Summary file at `s3://benchmarks-modelling-output/latest/summary.json`
- ✅ CloudWatch Logs showing successful execution
- ✅ Execution time: ~2-5 minutes
- ✅ Memory used: ~500-1000 MB

## Troubleshooting

### Test Fails with "No preprocessed data found"

**Problem**: S3 bucket `data-retrieval` doesn't have preprocessed data

**Solution**: Ensure data exists at `s3://data-retrieval/preprocessed/*.parquet`

### Test Fails with "Access Denied"

**Problem**: IAM role doesn't have S3 permissions

**Solution**: Ask administrator to verify the S3 policy in Step 1

### Timeout Error (15 minutes exceeded)

**Problem**: Too much data or slow strategies

**Solution**:
- Check CloudWatch Logs to see which strategy timed out
- Contact support to investigate

## Next Steps

Once deployed successfully:
1. Monitor first few daily executions
2. Validate output quality with dashboard team
3. Set up CloudWatch alarms for failures
4. Document S3 output structure for dashboard integration

---

**Contact**: Ask your AWS administrator if you encounter permission issues

**Documentation**: [LAMBDA_BENCHMARK_DEPLOYMENT.md](docs/LAMBDA_BENCHMARK_DEPLOYMENT.md)
