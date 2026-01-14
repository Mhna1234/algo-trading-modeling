#!/bin/bash
# Setup Daily EventBridge Schedule for Lambda
# Runs 2 hours after data retrieval completes

set -e

FUNCTION_NAME="benchmark-daily-calculator"
RULE_NAME="benchmark-daily-trigger"

# Default: Run at 3:00 AM UTC (2 hours after typical 1 AM data retrieval)
# Customize this based on when your data retrieval completes
SCHEDULE_HOUR=${1:-3}  # Pass hour as argument, default 3 AM UTC
SCHEDULE_EXPRESSION="cron(0 $SCHEDULE_HOUR * * ? *)"

echo "=== Setting Up Daily Lambda Schedule ==="
echo ""
echo "Function: $FUNCTION_NAME"
echo "Schedule: Daily at $SCHEDULE_HOUR:00 UTC"
echo "          (Runs 2 hours after data retrieval)"
echo ""
echo "To change the time, run: ./lambda/scripts/setup_daily_schedule.sh <hour>"
echo "Example for 5 AM UTC: ./lambda/scripts/setup_daily_schedule.sh 5"
echo ""

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Configuration.FunctionArn' --output text)
REGION=$(aws configure get region)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Lambda ARN: $LAMBDA_ARN"
echo "Region: $REGION"
echo ""

# Create EventBridge rule
echo "Creating EventBridge rule..."
aws events put-rule \
    --name $RULE_NAME \
    --description "Trigger benchmark calculations daily at $SCHEDULE_HOUR:00 UTC (2hrs after data retrieval)" \
    --schedule-expression "$SCHEDULE_EXPRESSION" \
    --state ENABLED

# Add Lambda permission for EventBridge
echo "Adding Lambda permission for EventBridge..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id AllowEventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/$RULE_NAME \
    2>/dev/null || echo "  (Permission already exists)"

# Add Lambda as target
echo "Adding Lambda as EventBridge target..."
aws events put-targets \
    --rule $RULE_NAME \
    --targets "Id"="1","Arn"="$LAMBDA_ARN"

echo ""
echo "=== Schedule Created Successfully! ==="
echo ""
echo "✅ Lambda will run daily at $SCHEDULE_HOUR:00 UTC"
echo ""
echo "Next execution will:"
echo "  1. Check s3://data-retrieval-output/history-data/ for latest data"
echo "  2. Load last 3 years of data"
echo "  3. Run 45 backtests (15 strategies × 3 frequencies)"
echo "  4. Save results to s3://benchmarks-modelling-output/benchmarks-output/"
echo ""
echo "Useful commands:"
echo "  Check schedule:  aws events describe-rule --name $RULE_NAME"
echo "  Disable:         aws events disable-rule --name $RULE_NAME"
echo "  Enable:          aws events enable-rule --name $RULE_NAME"
echo "  Delete:          aws events remove-targets --rule $RULE_NAME --ids 1 && aws events delete-rule --name $RULE_NAME"
