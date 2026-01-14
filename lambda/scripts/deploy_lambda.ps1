# PowerShell Script for AWS Lambda Deployment
# Deploys benchmark calculation Lambda function
#
# Usage: .\deploy_lambda.ps1
#
# Prerequisites:
# - AWS CLI configured with credentials
# - Python 3.11 installed
# - Sufficient IAM permissions

param(
    [string]$FunctionName = "benchmark-daily-calculator",
    [string]$Runtime = "python3.11",
    [int]$Timeout = 900,  # 15 minutes
    [int]$MemorySize = 3008,  # 3GB
    [string]$RoleName = "LambdaBenchmarkExecutionRole"
)

Write-Host "=== AWS Lambda Deployment Script ===" -ForegroundColor Cyan
Write-Host "Function: $FunctionName" -ForegroundColor Yellow
Write-Host "Runtime: $Runtime" -ForegroundColor Yellow
Write-Host ""

# Step 1: Create deployment package
Write-Host "Step 1/5: Creating deployment package..." -ForegroundColor Green

# Clean previous build
if (Test-Path "lambda/lambda_package") {
    Remove-Item -Recurse -Force lambda/lambda_package
}
if (Test-Path "lambda_deployment.zip") {
    Remove-Item -Force lambda_deployment.zip
}

# Create package directory
New-Item -ItemType Directory -Path lambda/lambda_package | Out-Null

# Install dependencies
Write-Host "Installing Lambda dependencies..." -ForegroundColor Yellow
pip install -r lambda/requirements-lambda.txt -t lambda/lambda_package --upgrade --platform manylinux2014_x86_64 --only-binary=:all:

# Copy source code
Write-Host "Copying source code..." -ForegroundColor Yellow
Copy-Item lambda/handlers/lambda_function.py lambda/lambda_package/
Copy-Item -Recurse src lambda/lambda_package/

# Create ZIP file
Write-Host "Creating deployment ZIP..." -ForegroundColor Yellow
Compress-Archive -Path lambda/lambda_package/* -DestinationPath lambda/lambda_deployment.zip -Force

$zipSize = (Get-Item lambda/lambda_deployment.zip).Length / 1MB
Write-Host "Package size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Yellow

if ($zipSize -gt 250) {
    Write-Host "WARNING: Package exceeds 250MB limit!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Deployment package created" -ForegroundColor Green
Write-Host ""

# Step 2: Create/Update IAM Role
Write-Host "Step 2/5: Setting up IAM role..." -ForegroundColor Green

$roleExists = aws iam get-role --role-name $RoleName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating IAM role: $RoleName" -ForegroundColor Yellow

    # Trust policy
    $trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@

    $trustPolicy | Out-File -FilePath trust-policy.json -Encoding utf8

    aws iam create-role `
        --role-name $RoleName `
        --assume-role-policy-document file://trust-policy.json

    # Attach policies
    aws iam attach-role-policy `
        --role-name $RoleName `
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Custom S3 policy
    $s3Policy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::data-retrieval/*",
        "arn:aws:s3:::data-retrieval"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::benchmarks-modelling-output/*"
    }
  ]
}
"@

    $s3Policy | Out-File -FilePath s3-policy.json -Encoding utf8

    aws iam put-role-policy `
        --role-name $RoleName `
        --policy-name S3BenchmarkAccess `
        --policy-document file://s3-policy.json

    Write-Host "Waiting 10 seconds for IAM propagation..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    Remove-Item trust-policy.json, s3-policy.json
}

$roleArn = (aws iam get-role --role-name $RoleName --query 'Role.Arn' --output text)
Write-Host "✓ IAM Role: $roleArn" -ForegroundColor Green
Write-Host ""

# Step 3: Create/Update Lambda Function
Write-Host "Step 3/5: Deploying Lambda function..." -ForegroundColor Green

$functionExists = aws lambda get-function --function-name $FunctionName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating new Lambda function..." -ForegroundColor Yellow

    aws lambda create-function `
        --function-name $FunctionName `
        --runtime $Runtime `
        --role $roleArn `
        --handler lambda_function.lambda_handler `
        --zip-file fileb://lambda/lambda_deployment.zip `
        --timeout $Timeout `
        --memory-size $MemorySize `
        --environment "Variables={DATA_BUCKET=data-retrieval,OUTPUT_BUCKET=benchmarks-modelling-output}" `
        --description "Daily benchmark strategy calculations (15 strategies x 3 frequencies)"

} else {
    Write-Host "Updating existing Lambda function..." -ForegroundColor Yellow

    aws lambda update-function-code `
        --function-name $FunctionName `
        --zip-file fileb://lambda/lambda_deployment.zip

    Start-Sleep -Seconds 2

    aws lambda update-function-configuration `
        --function-name $FunctionName `
        --timeout $Timeout `
        --memory-size $MemorySize `
        --environment "Variables={DATA_BUCKET=data-retrieval,OUTPUT_BUCKET=benchmarks-modelling-output}"
}

Write-Host "✓ Lambda function deployed" -ForegroundColor Green
Write-Host ""

# Step 4: Create EventBridge Rule (Daily Trigger)
Write-Host "Step 4/5: Setting up daily trigger..." -ForegroundColor Green

$ruleName = "daily-benchmark-calculation"
$ruleExists = aws events describe-rule --name $ruleName 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating EventBridge rule..." -ForegroundColor Yellow

    # Daily at 9 PM UTC (adjust to your timezone)
    aws events put-rule `
        --name $ruleName `
        --schedule-expression "cron(0 21 * * ? *)" `
        --description "Trigger benchmark calculations daily at 9 PM UTC"

    # Add Lambda permission
    aws lambda add-permission `
        --function-name $FunctionName `
        --statement-id AllowEventBridgeInvoke `
        --action lambda:InvokeFunction `
        --principal events.amazonaws.com `
        --source-arn (aws events describe-rule --name $ruleName --query 'Arn' --output text)

    # Add Lambda as target
    $targets = @"
[
  {
    "Id": "1",
    "Arn": "arn:aws:lambda:REGION:ACCOUNT:function:$FunctionName"
  }
]
"@

    $functionArn = (aws lambda get-function --function-name $FunctionName --query 'Configuration.FunctionArn' --output text)

    aws events put-targets `
        --rule $ruleName `
        --targets "[{`"Id`":`"1`",`"Arn`":`"$functionArn`"}]"
}

Write-Host "✓ Daily trigger configured (9 PM UTC)" -ForegroundColor Green
Write-Host ""

# Step 5: Test Invocation
Write-Host "Step 5/5: Testing Lambda function..." -ForegroundColor Green

$testEvent = @"
{
  "test": true,
  "execution_date": "$(Get-Date -Format 'yyyy-MM-dd')"
}
"@

$testEvent | Out-File -FilePath test-event.json -Encoding utf8

Write-Host "Invoking function (this may take a few minutes)..." -ForegroundColor Yellow
aws lambda invoke `
    --function-name $FunctionName `
    --payload file://test-event.json `
    --cli-binary-format raw-in-base64-out `
    response.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Test invocation successful" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    Get-Content response.json | ConvertFrom-Json | ConvertTo-Json -Depth 4
} else {
    Write-Host "✗ Test invocation failed" -ForegroundColor Red
}

Remove-Item test-event.json, response.json

# Cleanup
Remove-Item -Recurse -Force lambda/lambda_package
# Keep lambda_deployment.zip for manual uploads if needed

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Function Name: $FunctionName" -ForegroundColor Yellow
Write-Host "Trigger: Daily at 9 PM UTC" -ForegroundColor Yellow
Write-Host "Output Bucket: s3://benchmarks-modelling-output/" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "1. Check CloudWatch Logs: aws logs tail /aws/lambda/$FunctionName --follow" -ForegroundColor White
Write-Host "2. Verify S3 output: aws s3 ls s3://benchmarks-modelling-output/latest/" -ForegroundColor White
Write-Host "3. Manual trigger: aws lambda invoke --function-name $FunctionName response.json" -ForegroundColor White
