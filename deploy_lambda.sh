#!/bin/bash
# Lambda Deployment Script
# This script reliably builds and deploys the Lambda function

set -e  # Exit on any error

echo "=== Lambda Deployment Script ==="

# Clean previous builds
echo "1. Cleaning previous builds..."
rm -rf lambda_package lambda_deployment.zip

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

# Copy source code
echo "4. Copying source code..."
cp -r src lambda_package/
cp lambda_function.py lambda_package/

# Clean unnecessary files
echo "5. Cleaning unnecessary files..."
cd lambda_package
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true

# Create ZIP (from inside lambda_package to ensure correct structure)
echo "6. Creating deployment ZIP..."
python -c "
import zipfile
import os

with zipfile.ZipFile('../lambda_deployment.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, '.')
            zipf.write(file_path, arcname)
"

cd ..

# Show package size
echo "7. Package created successfully!"
ls -lh lambda_deployment.zip

# Upload to S3
echo "8. Uploading to S3..."
aws s3 cp lambda_deployment.zip s3://benchmarks-modelling-output/lambda/lambda_deployment.zip --quiet

# Update Lambda function
echo "9. Updating Lambda function..."
aws lambda update-function-code \
    --function-name benchmark-daily-calculator \
    --s3-bucket benchmarks-modelling-output \
    --s3-key lambda/lambda_deployment.zip \
    --query 'State' \
    --output text

echo "10. Waiting for function to become active..."
sleep 10

echo ""
echo "=== Deployment Complete! ==="
echo "To test: aws lambda invoke --function-name benchmark-daily-calculator --payload file://test-event.json response.json"
