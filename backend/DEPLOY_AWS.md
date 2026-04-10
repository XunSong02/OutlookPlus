# OutlookPlus AWS Deployment Guide

## Architecture Overview

```
Browser  ──>  AWS API Gateway (REST)  ──>  AWS Lambda  ──>  SQLite (/tmp)
   │                                            │
   │                                            ├──> IMAP (Gmail)
   │                                            ├──> SMTP (Gmail)
   │                                            └──> Gemini API
   │
   └──  AWS Amplify (static frontend)
```

---

## Prerequisites

1. **AWS CLI v2** installed and configured (`aws configure`)
2. **Python 3.10+** installed locally
3. **Node.js 18+** and npm (for frontend build)
4. An **AWS account** with permissions for Lambda, API Gateway, IAM, and Amplify

---

## Step 1: Create an IAM Role for Lambda

```bash
# Create the execution role
aws iam create-role \
  --role-name OutlookPlusLambdaRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach basic Lambda execution permissions (CloudWatch logs)
aws iam attach-role-policy \
  --role-name OutlookPlusLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Note the Role ARN from the output — you'll need it next
```

---

## Step 2: Package the Lambda Code

```bash
cd OutlookPlus/backend
bash build_lambda_zip.sh
```

This creates `lambda_package.zip` (~2.8 MB) containing:
- `lambda_handler.py` — the Lambda entry point
- `outlookplus_backend/` — all backend application code
- Dependencies: fastapi, pydantic, mangum, starlette, etc.

**What's NOT in the ZIP** (by design):
- `.env` file (credentials come from Lambda env vars or the Settings page)
- `uvicorn` (Lambda uses Mangum instead)
- Test files

---

## Step 3: Deploy the Lambda Function

### Option A: One-Command Deploy (recommended)

```bash
export LAMBDA_ROLE_ARN="arn:aws:iam::<YOUR_ACCOUNT_ID>:role/OutlookPlusLambdaRole"
bash deploy_aws.sh
```

This script:
1. Builds the ZIP
2. Creates/updates the Lambda function
3. Creates a REST API in API Gateway with `{proxy+}` catch-all
4. Deploys to the `prod` stage
5. Prints the invoke URL

### Option B: Step-by-Step

#### Create the Lambda function:
```bash
aws lambda create-function \
  --function-name OutlookPlusBackend \
  --runtime python3.10 \
  --handler lambda_handler.handler \
  --role arn:aws:iam::<ACCOUNT_ID>:role/OutlookPlusLambdaRole \
  --zip-file fileb://lambda_package.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment 'Variables={OUTLOOKPLUS_DB_PATH=/tmp/data/outlookplus.db,OUTLOOKPLUS_ATTACHMENTS_DIR=/tmp/data/attachments,OUTLOOKPLUS_AUTH_MODE=A}'
```

#### Test the function with AWS CLI:
```bash
aws lambda invoke \
  --function-name OutlookPlusBackend \
  --payload '{"httpMethod":"GET","path":"/api/credentials/status","headers":{},"queryStringParameters":null,"body":null,"requestContext":{"stage":"prod"},"isBase64Encoded":false}' \
  response.json

cat response.json
# Expected: {"statusCode":200,"body":"{\"imap\":false,\"smtp\":false,\"gemini\":false}"}
```

#### Update code after changes:
```bash
bash build_lambda_zip.sh
aws lambda update-function-code \
  --function-name OutlookPlusBackend \
  --zip-file fileb://lambda_package.zip
```

---

## Step 4: Set Up API Gateway

If you used `deploy_aws.sh`, this is already done. Otherwise:

```bash
# Create REST API
API_ID=$(aws apigateway create-rest-api \
  --name OutlookPlusAPI \
  --endpoint-configuration types=REGIONAL \
  --query 'id' --output text)

# Get root resource
ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[?path==`/`].id' --output text)

# Create {proxy+} catch-all resource
PROXY_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part '{proxy+}' \
  --query 'id' --output text)

# Set up ANY method → Lambda integration
LAMBDA_ARN=$(aws lambda get-function \
  --function-name OutlookPlusBackend \
  --query 'Configuration.FunctionArn' --output text)

aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PROXY_ID \
  --http-method ANY \
  --authorization-type NONE

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PROXY_ID \
  --http-method ANY \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations"

# Grant API Gateway permission to invoke Lambda
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws lambda add-permission \
  --function-name OutlookPlusBackend \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:${ACCOUNT_ID}:${API_ID}/*"

# Deploy to prod stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod

echo "Invoke URL: https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod"
```

#### Test the API:
```bash
curl https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod/api/credentials/status
# Expected: {"imap":false,"smtp":false,"gemini":false}
```

---

## Step 5: Update the Frontend

### Point frontend at API Gateway:

Create `frontend/.env`:
```
VITE_API_BASE_URL=https://<API_ID>.execute-api.us-east-1.amazonaws.com/prod
```

### Build for production:
```bash
cd OutlookPlus/frontend
npm install
npm run build
```

The `dist/` folder is ready for deployment.

### Deploy with AWS Amplify:

1. Push your code to GitHub
2. Go to AWS Amplify Console → **New app** → **Host web app**
3. Connect your GitHub repository
4. Set the build settings:
   - Build command: `cd frontend && npm install && npm run build`
   - Output directory: `frontend/dist`
5. Add environment variable: `VITE_API_BASE_URL=https://<API_ID>.execute-api...`
6. Deploy

---

## Step 6: Configure Credentials

After deployment, open the app in your browser and go to **Settings** (gear icon in the sidebar).

Enter your credentials:
- **IMAP**: Gmail host/port/email/app-password
- **SMTP**: Gmail host/port/email/app-password
- **Gemini**: API key and model name

These are saved in the backend database and persist across Lambda invocations (within the same warm container). For a fresh cold start, re-enter credentials via Settings or set them as Lambda environment variables.

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `OUTLOOKPLUS_DB_PATH` | `/tmp/data/outlookplus.db` | SQLite database location |
| `OUTLOOKPLUS_ATTACHMENTS_DIR` | `/tmp/data/attachments` | Attachment storage |
| `OUTLOOKPLUS_AUTH_MODE` | `A` | Auth mode: A=demo, B=dev-token |
| `GEMINI_API_KEY` | *(none)* | Gemini API key (optional if set via Settings) |
| `OUTLOOKPLUS_IMAP_HOST` | *(none)* | IMAP server (optional if set via Settings) |
| `OUTLOOKPLUS_IMAP_USERNAME` | *(none)* | IMAP username (optional if set via Settings) |
| `OUTLOOKPLUS_IMAP_PASSWORD` | *(none)* | IMAP password (optional if set via Settings) |
| `OUTLOOKPLUS_SMTP_HOST` | *(none)* | SMTP server (optional if set via Settings) |
| `OUTLOOKPLUS_SMTP_USERNAME` | *(none)* | SMTP username (optional if set via Settings) |
| `OUTLOOKPLUS_SMTP_PASSWORD` | *(none)* | SMTP password (optional if set via Settings) |

---

## Important Notes

- **Lambda /tmp is ephemeral**: SQLite data stored in `/tmp` persists only while the container is warm. For production persistence, use Amazon EFS or switch to DynamoDB.
- **Cold start**: First invocation may take 2-3 seconds. Subsequent invocations are faster (~200ms).
- **ZIP size limit**: Lambda supports up to 50 MB (zipped) or 250 MB (unzipped). Current package is ~2.8 MB.
- **CORS**: Already configured in the FastAPI app (`allow_origins=["*"]`).

---

## File Structure After Changes

```
backend/
├── lambda_handler.py          # Lambda entry point (Mangum wrapper)
├── build_lambda_zip.sh        # ZIP packaging script
├── deploy_aws.sh              # Full deploy script (Lambda + API Gateway)
├── lambda_package.zip          # Generated ZIP (after running build script)
├── requirements.txt           # Lambda dependencies (fastapi, pydantic, mangum)
├── requirements-dev.txt       # Local dev extras (uvicorn, pytest, httpx)
├── run_api.py                 # Local dev entry point (unchanged)
├── run_worker.py              # Local worker entry point (unchanged)
├── DEPLOY_AWS.md              # This file
└── outlookplus_backend/
    ├── credentials.py         # NEW: credential store (DB + env fallback)
    ├── api/
    │   ├── routes.py          # MODIFIED: credential endpoints + ingest
    │   └── models.py          # MODIFIED: credential DTOs
    ├── imap/client.py         # MODIFIED: accepts credential params
    ├── smtp/client.py         # MODIFIED: accepts credential params
    ├── llm/gemini.py          # MODIFIED: accepts credential params
    └── wiring.py              # MODIFIED: credential-aware service builders
```
