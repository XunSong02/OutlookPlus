#!/usr/bin/env bash
# ===========================================================================
# deploy_aws.sh
#
# One-command script that:
#   1. Packages the Lambda ZIP  (calls build_lambda_zip.sh)
#   2. Creates / updates the Lambda function
#   3. Creates a REST API in API Gateway with a {proxy+} catch-all
#   4. Prints the invoke URL
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (aws configure)
#   - An IAM role for Lambda with AWSLambdaBasicExecutionRole
#
# Usage:
#   cd OutlookPlus/backend
#   bash deploy_aws.sh
#
# Environment variables you can override:
#   LAMBDA_FUNCTION_NAME   (default: OutlookPlusBackend)
#   LAMBDA_ROLE_ARN        (REQUIRED – your Lambda execution role ARN)
#   AWS_REGION             (default: us-east-1)
#   API_NAME               (default: OutlookPlusAPI)
#   STAGE_NAME             (default: prod)
# ===========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---------- Configuration ----------
FUNCTION_NAME="${LAMBDA_FUNCTION_NAME:-OutlookPlusBackend}"
REGION="${AWS_REGION:-us-east-1}"
API_NAME="${API_NAME:-OutlookPlusAPI}"
STAGE="${STAGE_NAME:-prod}"
ROLE_ARN="${LAMBDA_ROLE_ARN:-}"
ZIP_FILE="$SCRIPT_DIR/lambda_package.zip"

# AWS CLI fileb:// doesn't handle spaces in paths well on Windows.
# Copy to C:\temp (Windows-native path, no spaces).
mkdir -p /c/temp 2>/dev/null || true
cp "$ZIP_FILE" /c/temp/lambda_package.zip
SAFE_ZIP="C:\\temp\\lambda_package.zip"

if [ -z "$ROLE_ARN" ]; then
  echo "ERROR: Set LAMBDA_ROLE_ARN to your Lambda execution role ARN."
  echo "  Example:"
  echo "    export LAMBDA_ROLE_ARN=arn:aws:iam::123456789012:role/OutlookPlusLambdaRole"
  echo ""
  echo "  To create the role, run:"
  echo "    aws iam create-role \\"
  echo "      --role-name OutlookPlusLambdaRole \\"
  echo "      --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}'"
  echo ""
  echo "    aws iam attach-role-policy \\"
  echo "      --role-name OutlookPlusLambdaRole \\"
  echo "      --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  exit 1
fi

# ===================================================================
# Step 1: Package
# ===================================================================
echo ""
echo "=========================================="
echo "  Step 1: Package Lambda ZIP"
echo "=========================================="
bash "$SCRIPT_DIR/build_lambda_zip.sh"

# ===================================================================
# Step 2: Create or Update Lambda Function
# ===================================================================
# Copy ZIP to a path without spaces for AWS CLI (already done above)
cp "$ZIP_FILE" /c/temp/lambda_package.zip 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Step 2: Deploy Lambda Function"
echo "=========================================="

FUNCTION_EXISTS=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null && echo "yes" || echo "no")

if [ "$FUNCTION_EXISTS" = "yes" ]; then
  echo "==> Updating existing function: $FUNCTION_NAME"
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$SAFE_ZIP" \
    --region "$REGION" \
    --no-cli-pager

  # Wait for the update to finish before touching config
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true

  aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={OUTLOOKPLUS_DB_PATH=/tmp/data/outlookplus.db,OUTLOOKPLUS_ATTACHMENTS_DIR=/tmp/data/attachments,OUTLOOKPLUS_AUTH_MODE=A}" \
    --region "$REGION" \
    --no-cli-pager
else
  echo "==> Creating new function: $FUNCTION_NAME"
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.10 \
    --handler lambda_handler.handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://$SAFE_ZIP" \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={OUTLOOKPLUS_DB_PATH=/tmp/data/outlookplus.db,OUTLOOKPLUS_ATTACHMENTS_DIR=/tmp/data/attachments,OUTLOOKPLUS_AUTH_MODE=A}" \
    --region "$REGION" \
    --no-cli-pager

  echo "==> Waiting for function to become active..."
  aws lambda wait function-active-v2 --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || sleep 5
fi

# Get the Lambda ARN for API Gateway integration
LAMBDA_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Configuration.FunctionArn' --output text)
echo "==> Lambda ARN: $LAMBDA_ARN"

# ===================================================================
# Step 3: Create REST API in API Gateway
# ===================================================================
echo ""
echo "=========================================="
echo "  Step 3: Set up API Gateway"
echo "=========================================="

# Check if API already exists
EXISTING_API_ID=$(aws apigateway get-rest-apis --region "$REGION" --query "items[?name=='$API_NAME'].id" --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_API_ID" ] && [ "$EXISTING_API_ID" != "None" ]; then
  API_ID="$EXISTING_API_ID"
  echo "==> Using existing API: $API_ID"
else
  echo "==> Creating new REST API: $API_NAME"
  API_ID=$(aws apigateway create-rest-api \
    --name "$API_NAME" \
    --description "OutlookPlus Backend API" \
    --endpoint-configuration types=REGIONAL \
    --region "$REGION" \
    --query 'id' --output text)
  echo "==> Created API: $API_ID"
fi

# Get the root resource ID
ROOT_ID=$(aws apigateway get-resources --rest-api-id "$API_ID" --region "$REGION" --query 'items[?path==`/`].id' --output text)

# Create {proxy+} resource if it doesn't exist
PROXY_ID=$(aws apigateway get-resources --rest-api-id "$API_ID" --region "$REGION" --query "items[?pathPart=='{proxy+}'].id" --output text 2>/dev/null || echo "")

if [ -z "$PROXY_ID" ] || [ "$PROXY_ID" = "None" ]; then
  echo "==> Creating {proxy+} resource..."
  PROXY_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_ID" \
    --path-part '{proxy+}' \
    --region "$REGION" \
    --query 'id' --output text)
fi

# Set up ANY method on {proxy+}
echo "==> Configuring ANY method on {proxy+}..."
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$PROXY_ID" \
  --http-method ANY \
  --authorization-type NONE \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || true

# Integrate with Lambda
LAMBDA_URI="arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations"

aws apigateway put-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$PROXY_ID" \
  --http-method ANY \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "$LAMBDA_URI" \
  --region "$REGION" \
  --no-cli-pager

# Also set up the root resource (/) for health checks etc.
echo "==> Configuring ANY method on root /..."
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$ROOT_ID" \
  --http-method ANY \
  --authorization-type NONE \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || true

aws apigateway put-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$ROOT_ID" \
  --http-method ANY \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "$LAMBDA_URI" \
  --region "$REGION" \
  --no-cli-pager

# Grant API Gateway permission to invoke Lambda
echo "==> Granting API Gateway → Lambda permission..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "apigateway-invoke-$(date +%s)" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" \
  --region "$REGION" \
  --no-cli-pager 2>/dev/null || true

# ===================================================================
# Step 4: Deploy the API
# ===================================================================
echo ""
echo "=========================================="
echo "  Step 4: Deploy API to stage '$STAGE'"
echo "=========================================="

aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE" \
  --region "$REGION" \
  --no-cli-pager

# ===================================================================
# Done!
# ===================================================================
INVOKE_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/${STAGE}"

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "  Lambda Function:  $FUNCTION_NAME"
echo "  API Gateway ID:   $API_ID"
echo "  Invoke URL:       $INVOKE_URL"
echo ""
echo "  Test it:"
echo "    curl ${INVOKE_URL}/api/credentials/status"
echo ""
echo "  Set this in your frontend .env:"
echo "    VITE_API_BASE_URL=${INVOKE_URL}"
echo ""
echo "  To invoke Lambda directly via CLI:"
echo "    aws lambda invoke --function-name $FUNCTION_NAME --payload '{\"httpMethod\":\"GET\",\"path\":\"/api/credentials/status\",\"headers\":{},\"queryStringParameters\":null,\"body\":null}' response.json && cat response.json"
echo ""
