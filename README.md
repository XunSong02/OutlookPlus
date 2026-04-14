# OutlookPlus

AI-powered email client with Gmail IMAP/SMTP integration and Gemini-powered analysis.

**Course**: SP26-CS698004 (NJIT)

## Live Demo

| Component | URL |
|-----------|-----|
| **Frontend** | [https://main.d3s1c524cuhn5w.amplifyapp.com](https://main.d3s1c524cuhn5w.amplifyapp.com) |
| **Backend API** | `https://8ce4i37kc6.execute-api.us-east-1.amazonaws.com/prod` |

## Using the App

1. Open the frontend URL.
2. Click **Settings** in the sidebar.
3. Enter your **IMAP** credentials (Gmail: `imap.gmail.com`, port `993`, your email, [App Password](https://myaccount.google.com/apppasswords)).
4. Enter your **SMTP** credentials (Gmail: `smtp.gmail.com`, port `587`, same email/app-password).
5. Enter your **Gemini API key** ([Google AI Studio](https://aistudio.google.com/apikey)), model `gemini-3-flash-preview`.
6. Click **Fetch Now** — emails load and you're redirected to Inbox.
7. Click any email to view it. The AI sidebar analyzes it on first open (summary, sentiment, suggested actions).

## Architecture

```
Browser  →  AWS Amplify (React + Vite)
               ↓ HTTPS
         API Gateway (REST)
               ↓
         AWS Lambda (FastAPI + Mangum, Python 3.12)
               ↓ boto3
         S3 (per-user SQLite databases)
               ↕
         Gmail IMAP/SMTP  ·  Gemini API
```

Each email account gets its own isolated SQLite database in S3, identified by the `X-User-Email` header.

## Project Structure

```
OutlookPlus/
├── frontend/          # React + Vite (TypeScript)
├── backend/           # FastAPI + Mangum (Python)
├── integration-tests/ # Jest E2E integration tests
├── Test/              # Backend unit tests (Python unittest)
├── test-specs/        # Test specifications
└── .github/workflows/ # CI/CD pipelines
```

---

## Development Setup

### Prerequisites

- Node.js 20+
- Python 3.12+
- AWS CLI configured with credentials

### Backend

```bash
cd backend
pip install -r requirements.txt

# Set environment variables or create .env:
export OUTLOOKPLUS_DB_PATH=data/outlookplus.db
export OUTLOOKPLUS_AUTH_MODE=A

uvicorn outlookplus_backend.api.app:create_app --factory --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173 (proxies /api to localhost:8000)
```

---

## Running Tests

### Frontend Unit Tests

```bash
cd frontend
npm install
npm test                 # run tests
npm run test:coverage    # with coverage
```

Test files: `frontend/tests/`

### Backend Unit Tests

```bash
# From project root:
PYTHONPATH=backend python -m pytest Test/ -v

# With coverage:
PYTHONPATH=backend coverage run --source=outlookplus_backend -m pytest Test/
coverage report -m
```

Test files: `Test/`

### Integration Tests

```bash
cd integration-tests
npm install

# Against cloud deployment:
npm run test:cloud

# Against localhost (start backend first):
npm run test:localhost
```

Test files: `integration-tests/api.integration.test.ts`

Some tests require real credentials via environment variables and only run in cloud CI:
- `TEST_IMAP_HOST`, `TEST_IMAP_USERNAME`, `TEST_IMAP_PASSWORD`
- `TEST_SMTP_HOST`, `TEST_SMTP_USERNAME`, `TEST_SMTP_PASSWORD`
- `TEST_GEMINI_API_KEY`

---

## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [`run-frontend-tests.yml`](.github/workflows/run-frontend-tests.yml) | Every push | Jest unit tests for React frontend |
| [`run-backend-tests.yml`](.github/workflows/run-backend-tests.yml) | Every push | Python unittest for backend |
| [`run-integration-tests.yml`](.github/workflows/run-integration-tests.yml) | Every push | End-to-end API integration tests |
| [`deploy-aws-lambda.yml`](.github/workflows/deploy-aws-lambda.yml) | Push to `main` | Package and deploy Lambda |
| [`deploy-aws-amplify.yml`](.github/workflows/deploy-aws-amplify.yml) | Push to `main` | Trigger Amplify redeploy |

---

## Deploying to AWS (Fork Setup Guide)

### 1. S3 Bucket

```bash
aws s3 mb s3://your-outlookplus-data
```

### 2. Lambda (Backend)

1. Create IAM role `OutlookPlusLambdaRole` with `AWSLambdaBasicExecutionRole` + inline S3 policy:
   ```json
   {
     "Effect": "Allow",
     "Action": ["s3:GetObject", "s3:PutObject"],
     "Resource": "arn:aws:s3:::your-outlookplus-data/*"
   }
   ```

2. Build and create the function:
   ```bash
   cd backend && bash build_lambda_zip.sh
   aws lambda create-function \
     --function-name OutlookPlusBackend \
     --runtime python3.12 \
     --handler lambda_handler.handler \
     --role arn:aws:iam::<ACCOUNT_ID>:role/OutlookPlusLambdaRole \
     --zip-file fileb://lambda_package.zip \
     --timeout 120 --memory-size 256 \
     --environment 'Variables={OUTLOOKPLUS_DB_PATH=/tmp/data/outlookplus.db,OUTLOOKPLUS_ATTACHMENTS_DIR=/tmp/data/attachments,OUTLOOKPLUS_AUTH_MODE=A,OUTLOOKPLUS_S3_BUCKET=your-outlookplus-data}'
   ```

### 3. API Gateway

1. Create a REST API with `{proxy+}` resource, `ANY` method, `AWS_PROXY` integration to your Lambda.
2. Deploy to a `prod` stage.

### 4. Amplify (Frontend)

1. Connect your GitHub repo to AWS Amplify.
2. Set app root to `frontend/`.
3. Add environment variable: `VITE_API_BASE_URL` = your API Gateway invoke URL.

### 5. GitHub Secrets (for CI/CD)

Add to your repo (Settings → Secrets → Actions):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### 6. Branch Protection

In GitHub Settings → Branches → Add classic protection rule for `main`:
- ✅ Require pull request before merging
- ✅ Require status checks to pass: `Frontend Tests`, `Backend Tests`, `Integration Tests`
