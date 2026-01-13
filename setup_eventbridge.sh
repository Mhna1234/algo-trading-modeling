#!/bin/bash
# EventBridge Setup Script for 3 Lambda Partitions
# Creates rules to trigger all 3 partitions daily at 3:00 AM UTC

set -e

echo "=== EventBridge Setup for Lambda Partitions ==="

AWS_REGION="eu-north-1"
SCHEDULE="cron(0 3 * * ? *)"  # Daily at 3:00 AM UTC
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

PARTITIONS=(1 2 3)
FUNCTION_NAMES=(
    "benchmark-calculator-partition-1"
    "benchmark-calculator-partition-2"
    "benchmark-calculator-partition-3"
)
RULE_NAMES=(
    "benchmark-daily-trigger-partition-1"
    "benchmark-daily-trigger-partition-2"
    "benchmark-daily-trigger-partition-3"
)

for i in "${!PARTITIONS[@]}"; do
    PARTITION=${PARTITIONS[$i]}
    FUNCTION_NAME=${FUNCTION_NAMES[$i]}
    RULE_NAME=${RULE_NAMES[$i]}

    echo ""
    echo "=== Setting up Partition $PARTITION ==="

    # Check if rule exists
    RULE_EXISTS=$(aws events describe-rule --name ${RULE_NAME} --region ${AWS_REGION} 2>&1 || echo "NOT_FOUND")

    if [[ "$RULE_EXISTS" == *"NOT_FOUND"* ]]; then
        echo "  1. Creating EventBridge rule..."
        aws events put-rule \
            --name ${RULE_NAME} \
            --description "Daily trigger for benchmark calculator partition ${PARTITION}" \
            --schedule-expression "${SCHEDULE}" \
            --state ENABLED \
            --region ${AWS_REGION}
    else
        echo "  1. Rule exists, updating..."
        aws events put-rule \
            --name ${RULE_NAME} \
            --description "Daily trigger for benchmark calculator partition ${PARTITION}" \
            --schedule-expression "${SCHEDULE}" \
            --state ENABLED \
            --region ${AWS_REGION}
    fi

    # Add Lambda permission for EventBridge to invoke
    echo "  2. Adding Lambda permission..."
    aws lambda add-permission \
        --function-name ${FUNCTION_NAME} \
        --statement-id "EventBridge-${RULE_NAME}" \
        --action "lambda:InvokeFunction" \
        --principal events.amazonaws.com \
        --source-arn "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/${RULE_NAME}" \
        --region ${AWS_REGION} \
        2>/dev/null || echo "  (Permission already exists)"

    # Add Lambda function as target
    echo "  3. Setting Lambda as target..."
    aws events put-targets \
        --rule ${RULE_NAME} \
        --targets "Id=1,Arn=arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}" \
        --region ${AWS_REGION}

    echo "  ✓ Partition $PARTITION configured!"
done

echo ""
echo "=== EventBridge Setup Complete! ==="
echo ""
echo "All 3 partitions will run daily at 3:00 AM UTC (${SCHEDULE})"
echo ""
echo "Rules created:"
for RULE_NAME in "${RULE_NAMES[@]}"; do
    echo "  - $RULE_NAME"
done
echo ""
echo "To check rule status:"
echo "  aws events list-rules --name-prefix benchmark-daily-trigger --region $AWS_REGION"
echo ""
echo "To test manually:"
echo "  aws lambda invoke --function-name benchmark-calculator-partition-1 --region $AWS_REGION response1.json"
echo "  aws lambda invoke --function-name benchmark-calculator-partition-2 --region $AWS_REGION response2.json"
echo "  aws lambda invoke --function-name benchmark-calculator-partition-3 --region $AWS_REGION response3.json"
