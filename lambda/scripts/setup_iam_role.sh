#!/bin/bash
# Setup IAM Role for Lambda Functions
# Creates lambda-execution-role with necessary permissions

set -e

echo "=== Setting up IAM Role for Lambda ==="

AWS_REGION="eu-north-1"
ROLE_NAME="lambda-execution-role"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Check if role exists
ROLE_EXISTS=$(aws iam get-role --role-name ${ROLE_NAME} 2>&1 || echo "NOT_FOUND")

if [[ "$ROLE_EXISTS" == *"NOT_FOUND"* ]]; then
    echo "1. Creating IAM role: ${ROLE_NAME}..."

    # Create trust policy for Lambda
    cat > /tmp/lambda-trust-policy.json <<EOF
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

    # Create the role
    aws iam create-role \
        --role-name ${ROLE_NAME} \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
        --description "Execution role for benchmark Lambda functions"

    echo "2. Attaching basic Lambda execution policy..."
    aws iam attach-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    echo "3. Creating and attaching S3 access policy..."
    cat > /tmp/lambda-s3-policy.json <<EOF
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
        "arn:aws:s3:::data-retrieval-output",
        "arn:aws:s3:::data-retrieval-output/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::benchmarks-modelling-output",
        "arn:aws:s3:::benchmarks-modelling-output/*"
      ]
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name ${ROLE_NAME} \
        --policy-name lambda-s3-access \
        --policy-document file:///tmp/lambda-s3-policy.json

    echo "4. Waiting for role to propagate (10 seconds)..."
    sleep 10

    echo "✓ Role created successfully!"
else
    echo "Role ${ROLE_NAME} already exists."
fi

echo ""
echo "Role ARN: arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "You can now run: ./lambda/scripts/deploy_lambda.sh"
