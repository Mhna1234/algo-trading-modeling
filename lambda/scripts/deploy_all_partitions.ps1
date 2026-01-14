# PowerShell Script to Deploy All 3 Lambda Partitions
# Usage: .\deploy_all_partitions.ps1

$ErrorActionPreference = "Stop"

$Region = "eu-north-1"
$Bucket = "benchmarks-modelling-output"
$Partitions = 1, 2, 3

Write-Host "=== Deploying All 3 Lambda Partitions ===" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Bucket: $Bucket" -ForegroundColor Yellow
Write-Host ""

# Step 1: Prepare Build Directory
Write-Host "Step 1: Preparing build directory..." -ForegroundColor Green

if (Test-Path "lambda/lambda_package") {
    Remove-Item -Recurse -Force lambda/lambda_package
}
Remove-Item lambda/lambda_deployment_*.zip -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path lambda/lambda_package | Out-Null

# Step 2: Install Dependencies
Write-Host "Step 2: Installing dependencies..." -ForegroundColor Green
# Ensure we use the venv pip if available, otherwise assume pip is in path
if (Test-Path "venv/Scripts/pip.exe") {
    & ./venv/Scripts/pip.exe install -r lambda/requirements-lambda.txt -t lambda/lambda_package --upgrade --platform manylinux2014_x86_64 --only-binary=:all: --quiet
}
else {
    pip install -r lambda/requirements-lambda.txt -t lambda/lambda_package --upgrade --platform manylinux2014_x86_64 --only-binary=:all: --quiet
}

# Step 3: Copy Source Code
Write-Host "Step 3: Copying source code..." -ForegroundColor Green
Copy-Item -Recurse src lambda/lambda_package/

# Clean cleanup
Get-ChildItem -Path lambda/lambda_package -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path lambda/lambda_package -Recurse -Filter "*.pyc" | Remove-Item -Force

# Step 4: Deploy Each Partition
foreach ($PartitionId in $Partitions) {
    $FunctionName = "benchmark-calculator-partition-$PartitionId"
    $ZipFile = "lambda/lambda_deployment_partition_$PartitionId.zip"
    $HandlerSource = "lambda/handlers/lambda_function_partition_$PartitionId.py"
    
    Write-Host ""
    Write-Host "=== Partition ${PartitionId}: ${FunctionName} ===" -ForegroundColor Cyan
    
    # Copy Handler
    Write-Host "  Copying handler..."
    Copy-Item $HandlerSource lambda/lambda_package/lambda_function.py
    
    # Zip
    Write-Host "  Creating ZIP..."
    # PowerShell's Compress-Archive can be slow and might include root folder if not careful.
    # We want contents of lambda_package to be at root of zip.
    # The safest way in PS without 3rd party tools:
    
    $compressionLevel = "Optimal"
    $sourceDir = "lambda/lambda_package"
    
    # Remove old zip if exists
    if (Test-Path $ZipFile) { Remove-Item $ZipFile }
    
    # We use .NET API for better control or just Compress-Archive with * wildcard
    Compress-Archive -Path "$sourceDir/*" -DestinationPath $ZipFile -Force
    
    $zipSize = (Get-Item $ZipFile).Length / 1MB
    Write-Host "  Size: $([math]::Round($zipSize, 2)) MB"
    
    # Upload to S3
    Write-Host "  Uploading to S3..."
    aws s3 cp $ZipFile "s3://$Bucket/lambda/$(Split-Path $ZipFile -Leaf)" --region $Region --quiet
    
    # Deploy Function
    Write-Host "  Updating Lambda function..."
    
    $funcExists = aws lambda get-function --function-name $FunctionName --region $Region 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Function not found, creating..."
        $accountId = aws sts get-caller-identity --query Account --output text
        
        aws lambda create-function `
            --function-name $FunctionName `
            --runtime python3.11 `
            --role "arn:aws:iam::${accountId}:role/LambdaBenchmarkExecutionRole" `
            --handler lambda_function.lambda_handler `
            --code "S3Bucket=$Bucket,S3Key=lambda/$(Split-Path $ZipFile -Leaf)" `
            --timeout 900 `
            --memory-size 3008 `
            --region $Region `
            --environment "Variables={OUTPUT_BUCKET=$Bucket,OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}"
    }
    else {
        aws lambda update-function-code `
            --function-name $FunctionName `
            --s3-bucket $Bucket `
            --s3-key "lambda/$(Split-Path $ZipFile -Leaf)" `
            --region $Region | Out-Null
            
        # Wait for update
        aws lambda wait function-updated --function-name $FunctionName --region $Region
        
        # Update config
        aws lambda update-function-configuration `
            --function-name $FunctionName `
            --environment "Variables={OUTPUT_BUCKET=$Bucket,OUTPUT_PREFIX=benchmarks-output,DATA_YEARS=5}" `
            --region $Region | Out-Null
    }
    
    Write-Host "  Waiting for function to be active..."
    aws lambda wait function-active --function-name $FunctionName --region $Region
    
    Write-Host "  ✓ Partition $PartitionId Deployed" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Cyan
