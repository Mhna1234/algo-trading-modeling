#!/bin/bash
# Bash Script for AWS Lambda Deployment
# Deploys benchmark calculation Lambda function
#
# Usage: ./deploy_lambda.sh
#
# Prerequisites:
# - AWS CLI configured with credentials
# - Python 3.11 installed
# - Sufficient IAM permissions

set -e  # Exit on error

# Configuration
FUNCTION_NAME="benchmark-daily-calculator"
RUNTIME="python3.11"
TIMEOUT=900  # 15 minutes
MEMORY_SIZE=3008  # 3GB
ROLE_NAME="LambdaBenchmarkExecutionRole"

echo "=== AWS Lambda Deployment Script ==="
echo "Function: $FUNCTION_NAME"
echo "Runtime: $RUNTIME"
echo ""

# Step 1: Create deployment package
echo "Step 1/5: Creating deployment package..."

# Clean previous build
rm -rf lambda_package
rm -f lambda_deployment.zip

# Create package directory
mkdir -p lambda_package

# Install dependencies
echo "Installing Lambda dependencies..."
pip install -r requirements-lambda.txt \
    -t lambda_package \
    --upgrade \
    --platform manylinux2014_x86_64 \
    --only-binary=:all:

# Copy source code
echo "Copying source code..."
cp lambda_function.py lambda_package/
cp -r src lambda_package/

# Create ZIP file
echo "Creating deployment ZIP..."
cd lambda_package
zip -r ../lambda_deployment.zip . -q
cd ..

ZIP_SIZE=$(du -h lambda_deployment.zip | cut -f1)
echo "Package size: $ZIP_SIZE"

# Check size limit
if [ $(stat -f%z lambda_deployment.zip 2>/dev/null || stat -c%s lambda_deployment.zip) -gt 262144000 ]; then
    echo "WARNING: Package exceeds 250MB limit!"
    exit 1
fi

echo "✓ Deployment package created"
echo ""

# Step 2: Create/Update IAM Role
echo "Step 2/5: Setting up IAM role..."

if ! aws iam get-role --role-name $ROLE_NAME &>/dev/null; then
    echo "Creating IAM role: $ROLE_NAME"

    # Trust policy
    cat > trust-policy.json <<EOF
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
EOF

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json

    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Custom S3 policy
    cat > s3-policy.json <<EOF
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
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name S3BenchmarkAccess \
        --policy-document file://s3-policy.json

    echo "Waiting 10 seconds for IAM propagation..."
    sleep 10

    rm trust-policy.json s3-policy.json
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "✓ IAM Role: $ROLE_ARN"
echo ""

# Step 3: Create/Update Lambda Function
echo "Step 3/5: Deploying Lambda function..."

if ! aws lambda get-function --function-name $FUNCTION_NAME &>/dev/null; then
    echo "Creating new Lambda function..."

    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://lambda_deployment.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --environment "Variables={DATA_BUCKET=data-retrieval,OUTPUT_BUCKET=benchmarks-modelling-output}" \
        --description "Daily benchmark strategy calculations (15 strategies x 3 frequencies)"

else
    echo "Updating existing Lambda function..."

    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_deployment.zip

    sleep 2

    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout $TIMEOUT \
        --memory-size $MEMORY_SIZE \
        --environment "Variables={DATA_BUCKET=data-retrieval,OUTPUT_BUCKET=benchmarks-modelling-output}"
fi

echo "✓ Lambda function deployed"
echo ""

# Step 4: Create EventBridge Rule (Daily Trigger)
echo "Step 4/5: Setting up daily trigger..."

RULE_NAME="daily-benchmark-calculation"

if ! aws events describe-rule --name $RULE_NAME &>/dev/null; then
    echo "Creating EventBridge rule..."

    # Daily at 9 PM UTC (adjust to your timezone)
    aws events put-rule \
        --name $RULE_NAME \
        --schedule-expression "cron(0 21 * * ? *)" \
        --description "Trigger benchmark calculations daily at 9 PM UTC"

    # Add Lambda permission
    RULE_ARN=$(aws events describe-rule --name $RULE_NAME --query 'Arn' --output text)

    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id AllowEventBridgeInvoke \
        --action lambda:InvokeFunction \
        --principal events.amazonaws.com \
        --source-arn $RULE_ARN 2>/dev/null || true

    # Add Lambda as target
    FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text)

    aws events put-targets \
        --rule $RULE_NAME \
        --targets "Id=1,Arn=$FUNCTION_ARN"
fi

echo "✓ Daily trigger configured (9 PM UTC)"
echo ""

# Step 5: Test Invocation
echo "Step 5/5: Testing Lambda function..."

cat > test-event.json <<EOF
{
  "test": true,
  "execution_date": "$(date +%Y-%m-%d)"
}
EOF

echo "Invoking function (this may take a few minutes)..."
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload file://test-event.json \
    --cli-binary-format raw-in-base64-out \
    response.json

if [ $? -eq 0 ]; then
    echo "✓ Test invocation successful"
    echo ""
    echo "Response:"
    cat response.json | jq .
else
    echo "✗ Test invocation failed"
fi

rm test-event.json response.json

# Cleanup
rm -rf lambda_package
# Keep lambda_deployment.zip for manual uploads if needed

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Function Name: $FUNCTION_NAME"
echo "Trigger: Daily at 9 PM UTC"
echo "Output Bucket: s3://benchmarks-modelling-output/"
echo ""
echo "Next Steps:"
echo "1. Check CloudWatch Logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo "2. Verify S3 output: aws s3 ls s3://benchmarks-modelling-output/latest/"
echo "3. Manual trigger: aws lambda invoke --function-name $FUNCTION_NAME response.json"
