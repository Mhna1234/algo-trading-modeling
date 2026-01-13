#!/bin/bash
# Lambda Deployment Script - Deploys 3 Partitioned Functions
# Each partition handles 5 strategies to stay under 15-minute timeout

set -e  # Exit on any error

echo "=== Lambda Deployment Script (3 Partitions) ==="

# Configuration
AWS_REGION="eu-north-1"
OUTPUT_BUCKET="benchmarks-modelling-output"
PARTITIONS=(1 2 3)
FUNCTION_NAMES=(
    "benchmark-calculator-partition-1"
    "benchmark-calculator-partition-2"
    "benchmark-calculator-partition-3"
)

# Clean previous builds
echo "1. Cleaning previous builds..."
rm -rf lambda_package lambda_deployment_*.zip

# Create package directory
echo "2. Creating package directory..."
mkdir -p lambda_package

# Install dependencies
echo "3. Installing dependencies (this may take a minute)..."
pip install -r requirements-lambda.txt \
    --target lambda_package \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --upgrade \
    --quiet

# Copy source code (shared across all partitions)
echo "4. Copying source code..."
cp -r src lambda_package/

# Clean unnecessary files
echo "5. Cleaning unnecessary files..."
cd lambda_package
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
cd ..

# Deploy each partition
for i in "${!PARTITIONS[@]}"; do
    PARTITION=${PARTITIONS[$i]}
    FUNCTION_NAME=${FUNCTION_NAMES[$i]}
    ZIP_FILE="lambda_deployment_partition_${PARTITION}.zip"

    echo ""
    echo "=== Partition $PARTITION - $FUNCTION_NAME ==="

    # Copy partition-specific handler
    echo "  6.$PARTITION. Copying partition $PARTITION handler..."
    cp lambda_function_partition_${PARTITION}.py lambda_package/lambda_function.py

    # Create ZIP for this partition
    echo "  7.$PARTITION. Creating deployment ZIP..."
    cd lambda_package
    python -c "
import zipfile
import os

with zipfile.ZipFile('../${ZIP_FILE}', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            zipf.write(file_path, arcname)
"
    cd ..

    # Show package size
    echo "  8.$PARTITION. Package created:"
    ls -lh ${ZIP_FILE}

    # Upload to S3
    echo "  9.$PARTITION. Uploading to S3..."
    aws s3 cp ${ZIP_FILE} s3://${OUTPUT_BUCKET}/lambda/${ZIP_FILE} --region ${AWS_REGION} --quiet

    # Check if Lambda function exists
    FUNCTION_EXISTS=$(aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} 2>&1 || echo "NOT_FOUND")

    if [[ "$FUNCTION_EXISTS" == *"NOT_FOUND"* ]]; then
        echo "  10.$PARTITION. Creating new Lambda function..."
        aws lambda create-function \
            --function-name ${FUNCTION_NAME} \
            --runtime python3.11 \
            --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
            --handler lambda_function.lambda_handler \
            --code S3Bucket=${OUTPUT_BUCKET},S3Key=lambda/${ZIP_FILE} \
            --timeout 900 \
            --memory-size 3008 \
            --region ${AWS_REGION} \
            --environment "Variables={OUTPUT_BUCKET=${OUTPUT_BUCKET},OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}" \
            --query 'State' \
            --output text
    else
        echo "  10.$PARTITION. Updating Lambda function..."
        aws lambda update-function-code \
            --function-name ${FUNCTION_NAME} \
            --s3-bucket ${OUTPUT_BUCKET} \
            --s3-key lambda/${ZIP_FILE} \
            --region ${AWS_REGION} \
            --query 'State' \
            --output text
    fi

    echo "  11.$PARTITION. Waiting for function to become active..."
    sleep 5

    # Update environment variables (in case they changed)
    aws lambda update-function-configuration \
        --function-name ${FUNCTION_NAME} \
        --environment "Variables={OUTPUT_BUCKET=${OUTPUT_BUCKET},OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}" \
        --region ${AWS_REGION} \
        --query 'State' \
        --output text > /dev/null

    echo "  ✓ Partition $PARTITION deployed!"
done

echo ""
echo "=== All Partitions Deployed Successfully! ==="
echo ""
echo "Functions created:"
for FUNCTION_NAME in "${FUNCTION_NAMES[@]}"; do
    echo "  - $FUNCTION_NAME"
done
echo ""
echo "To test a partition:"
echo "  aws lambda invoke --function-name benchmark-calculator-partition-1 --region $AWS_REGION response1.json"
echo ""
echo "To set up EventBridge triggers, run:"
echo "  ./setup_eventbridge.sh"
