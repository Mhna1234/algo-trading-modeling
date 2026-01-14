# PowerShell Script to Setup EventBridge for 3 Partitions
# Usage: .\setup_eventbridge_partitions.ps1

$ErrorActionPreference = "Stop"
$Region = "eu-north-1"
$Schedule = "cron(0 3 * * ? *)" # 3:00 AM UTC
$Partitions = 1, 2, 3

$AccountId = aws sts get-caller-identity --query Account --output text

Write-Host "=== Setting up EventBridge for Partitions ===" -ForegroundColor Cyan
Write-Host "Schedule: $Schedule" -ForegroundColor Yellow

foreach ($PartitionId in $Partitions) {
    $FunctionName = "benchmark-calculator-partition-$PartitionId"
    $RuleName = "benchmark-daily-trigger-partition-$PartitionId"
    
    Write-Host ""
    Write-Host "Partition $PartitionId" -ForegroundColor Yellow
    
    # 1. Put Rule
    Write-Host "  Creating/Updating Rule $RuleName..."
    aws events put-rule `
        --name $RuleName `
        --description "Daily trigger for partition $PartitionId" `
        --schedule-expression "$Schedule" `
        --state ENABLED `
        --region $Region | Out-Null
        
    # 2. Add Permission
    Write-Host "  Adding Lambda permission..."
    aws lambda add-permission `
        --function-name $FunctionName `
        --statement-id "EventBridge-$RuleName" `
        --action "lambda:InvokeFunction" `
        --principal events.amazonaws.com `
        --source-arn "arn:aws:events:${Region}:${AccountId}:rule/${RuleName}" `
        --region $Region `
        2>$null
        
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  (Permission likely exists or error)" -ForegroundColor DarkGray
    }
        
    # 3. Add Target
    Write-Host "  Setting Target..."
    $targetArn = "arn:aws:lambda:${Region}:${AccountId}:function:${FunctionName}"
    $targetJson = "[{`"Id`":`"1`",`"Arn`":`"$targetArn`"}]"
    
    aws events put-targets `
        --rule $RuleName `
        --targets $targetJson `
        --region $Region | Out-Null
        
    Write-Host "  ✓ Configured!" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
