# AWS Lambda Deployment Script - Fixed for Large Layers
$FUNCTION_NAME = "algo-trading-daily"
$LAMBDA_ROLE_ARN = "arn:aws:iam::466787509184:role/lambda-algo-trading-role"
$S3_BUCKET = "sama-algo-trading-prod"
$RUNTIME = "python3.11"
$TIMEOUT = 900
$MEMORY = 3008
$LAYER_NAME = "algo-trading-dependencies"
$REGION = "us-east-1"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "AWS Lambda Deployment Script" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

function Write-Success { param($Message); Write-Host "[?] $Message" -ForegroundColor Green }
function Write-Error { param($Message); Write-Host "[?] $Message" -ForegroundColor Red }
function Write-Warning { param($Message); Write-Host "[!] $Message" -ForegroundColor Yellow }

Write-Success "Checking prerequisites..."
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) { Write-Error "AWS CLI not found"; exit 1 }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Error "Python not found"; exit 1 }
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) { Write-Error "pip not found"; exit 1 }

$WORK_DIR = Join-Path $env:TEMP "lambda-deploy-$(Get-Random)"
New-Item -ItemType Directory -Path $WORK_DIR -Force | Out-Null
Write-Success "Created working directory: $WORK_DIR"

Write-Success "Creating Lambda Layer with dependencies..."
$LAYER_DIR = Join-Path $WORK_DIR "layer\python"
New-Item -ItemType Directory -Path $LAYER_DIR -Force | Out-Null

Write-Host "Installing dependencies (this may take 5-10 minutes)..." -ForegroundColor Yellow
pip install -r lambda_requirements_minimal.txt -t $LAYER_DIR --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install dependencies"; exit 1 }
Write-Success "Installed dependencies to layer"

$LAYER_ZIP = Join-Path $WORK_DIR "layer.zip"
Write-Host "Creating layer package..."
Compress-Archive -Path (Join-Path $WORK_DIR "layer\*") -DestinationPath $LAYER_ZIP -Force
Write-Success "Created layer package: layer.zip"

$LAYER_SIZE = [math]::Round((Get-Item $LAYER_ZIP).Length / 1MB, 2)
Write-Warning "Layer size: ${LAYER_SIZE}MB (too large for direct upload)"

Write-Success "Uploading layer to S3..."
$S3_LAYER_KEY = "lambda-layers/$LAYER_NAME-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
aws s3 cp $LAYER_ZIP "s3://$S3_BUCKET/$S3_LAYER_KEY" --region $REGION
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to upload layer to S3"; exit 1 }
Write-Success "Uploaded layer to s3://$S3_BUCKET/$S3_LAYER_KEY"

Write-Success "Publishing layer from S3..."
$layerOutput = aws lambda publish-layer-version --layer-name $LAYER_NAME --content "S3Bucket=$S3_BUCKET,S3Key=$S3_LAYER_KEY" --compatible-runtimes $RUNTIME --region $REGION --query 'Version' --output text
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to publish Lambda layer"; exit 1 }
$LAYER_VERSION = $layerOutput
Write-Success "Published layer version: $LAYER_VERSION"

$ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$LAYER_ARN = "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:layer:${LAYER_NAME}:${LAYER_VERSION}"
Write-Success "Layer ARN: $LAYER_ARN"

Write-Success "Packaging Lambda function..."
$FUNCTION_DIR = Join-Path $WORK_DIR "function"
New-Item -ItemType Directory -Path $FUNCTION_DIR -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $FUNCTION_DIR "src") -Force | Out-Null

Copy-Item "lambda_function.py" -Destination $FUNCTION_DIR
Copy-Item "src\*" -Destination (Join-Path $FUNCTION_DIR "src") -Recurse -Force
New-Item -ItemType File -Path (Join-Path $FUNCTION_DIR "src\__init__.py") -Force | Out-Null

$FUNCTION_ZIP = Join-Path $WORK_DIR "function.zip"
Compress-Archive -Path (Join-Path $FUNCTION_DIR "*") -DestinationPath $FUNCTION_ZIP -Force
Write-Success "Created function package: function.zip"

$FUNC_SIZE = [math]::Round((Get-Item $FUNCTION_ZIP).Length / 1MB, 2)
Write-Success "Package sizes - Function: ${FUNC_SIZE}MB, Layer: ${LAYER_SIZE}MB"

Write-Success "Checking if Lambda function exists..."
$functionExists = $false
try { aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>$null; if ($LASTEXITCODE -eq 0) { $functionExists = $true } } catch { $functionExists = $false }

if ($functionExists) {
    Write-Warning "Function exists. Updating..."
    aws lambda update-function-code --function-name $FUNCTION_NAME --zip-file "fileb://$FUNCTION_ZIP" --region $REGION | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to update function code"; exit 1 }
    Write-Success "Updated function code"
    Start-Sleep -Seconds 5
    aws lambda update-function-configuration --function-name $FUNCTION_NAME --timeout $TIMEOUT --memory-size $MEMORY --layers $LAYER_ARN --environment "Variables={S3_BUCKET=$S3_BUCKET}" --region $REGION | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to update configuration"; exit 1 }
    Write-Success "Updated function configuration"
} else {
    Write-Success "Creating new Lambda function..."
    aws lambda create-function --function-name $FUNCTION_NAME --runtime $RUNTIME --role $LAMBDA_ROLE_ARN --handler "lambda_function.lambda_handler" --timeout $TIMEOUT --memory-size $MEMORY --zip-file "fileb://$FUNCTION_ZIP" --layers $LAYER_ARN --environment "Variables={S3_BUCKET=$S3_BUCKET}" --description "Daily algorithmic trading execution engine" --region $REGION | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create Lambda function"; exit 1 }
    Write-Success "Created Lambda function: $FUNCTION_NAME"
}

Write-Host ""
Write-Success "Deployment completed successfully!"
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Function Name: $FUNCTION_NAME"
Write-Host "Runtime: $RUNTIME"
Write-Host "Layer Version: $LAYER_VERSION"
Write-Host "Region: $REGION"
Write-Host ""
Write-Success "Running validation test..."
$testPayload = '{"action":"validate"}'
$responseFile = Join-Path $env:TEMP "lambda_test.json"
aws lambda invoke --function-name $FUNCTION_NAME --payload $testPayload --region $REGION $responseFile | Out-Null
if (Test-Path $responseFile) { 
    Write-Success "Test successful" 
    Write-Host ""
    Write-Host "Test Response:" -ForegroundColor Yellow
    Get-Content $responseFile | ConvertFrom-Json | ConvertTo-Json -Depth 10
    Remove-Item $responseFile 
}
Write-Host ""
Write-Host "Deployment complete! ??" -ForegroundColor Green
Remove-Item -Recurse -Force $WORK_DIR
