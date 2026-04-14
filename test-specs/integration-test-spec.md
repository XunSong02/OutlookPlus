# OutlookPlus Integration Test Specification

## Overview

These integration tests verify end-to-end code pathways that span the **frontend API client** (`outlookplusApi.ts`) and the **backend REST API** (FastAPI on Lambda via API Gateway). Each test makes real HTTP requests against the running backend and validates the responses match what the frontend expects.

Tests are run via Jest with `cross-fetch` for HTTP calls. The base URL is controlled by the environment variable `TEST_API_BASE_URL`:

- **Localhost**: `http://localhost:8000` (uvicorn dev server)
- **Cloud**: `https://8ce4i37kc6.execute-api.us-east-1.amazonaws.com/prod`

## Functionality to Test

1. **Credential lifecycle** -- Save IMAP/SMTP/Gemini credentials, verify status, delete credentials.
2. **Email ingestion** -- Trigger IMAP fetch, verify new emails appear in the list.
3. **Email listing** -- List emails by folder, verify pagination and filtering.
4. **Email detail** -- Fetch a single email by ID, verify body and metadata.
5. **Mark email read** -- PATCH an email as read, verify the change persists.
6. **AI analysis** -- POST analyze for an email, verify category/sentiment/summary returned.
7. **Send email** -- POST a new email, verify it appears in the sent folder.
8. **Per-user DB isolation** -- Two different `X-User-Email` headers yield independent data.
9. **CORS headers** -- Preflight OPTIONS requests return proper Access-Control headers.
10. **Error handling** -- Missing credentials return 400; unknown email returns 404.

## Test Table

| # | Test Name | Purpose | Inputs | Expected Output |
|---|-----------|---------|--------|-----------------|
| 1 | `GET /api/credentials/status (unconfigured)` | Verify status endpoint returns false for all credential types when nothing is saved | `GET /api/credentials/status` with `X-User-Email: integration-test@test.com` | HTTP 200; `{ imap: false, smtp: false, gemini: false }` |
| 2 | `POST /api/credentials (save IMAP)` | Save IMAP credentials and verify status updates | `POST /api/credentials` with body `{ imap: { host, port, username, password } }` | HTTP 200; response has `imap: true` |
| 3 | `POST /api/credentials (save SMTP)` | Save SMTP credentials and verify status updates | `POST /api/credentials` with body `{ smtp: { host, port, username, password } }` | HTTP 200; response has `smtp: true` |
| 4 | `POST /api/credentials (save Gemini)` | Save Gemini credentials and verify status updates | `POST /api/credentials` with body `{ gemini: { api_key, model } }` | HTTP 200; response has `gemini: true` |
| 5 | `GET /api/credentials/status (all configured)` | After saving all three, status shows all true | `GET /api/credentials/status` | HTTP 200; `{ imap: true, smtp: true, gemini: true }` |
| 6 | `DELETE /api/credentials?cred_type=gemini` | Delete a single credential type | `DELETE /api/credentials?cred_type=gemini` | HTTP 204; subsequent status has `gemini: false` |
| 7 | `POST /api/ingest (no IMAP)` | Trigger ingest without IMAP credentials configured | `POST /api/ingest` with a user that has no IMAP | HTTP 400; body contains `"detail"` |
| 8 | `POST /api/ingest (with IMAP)` | Trigger ingest with valid IMAP credentials | `POST /api/ingest` with `X-User-Email` of configured user | HTTP 200; `{ ingested: <number> }` |
| 9 | `GET /api/emails?folder=inbox` | List inbox emails after ingest | `GET /api/emails?folder=inbox&limit=50` | HTTP 200; `items` array length > 0; each item has `id`, `subject`, `folder=inbox` |
| 10 | `GET /api/emails?folder=sent` | List sent folder (may be empty) | `GET /api/emails?folder=sent&limit=50` | HTTP 200; `items` is an array |
| 11 | `GET /api/emails/{id}` | Fetch a specific email by ID | `GET /api/emails/<first inbox email id>` | HTTP 200; response has `id`, `subject`, `body`, `sender`, `date`, `aiAnalysis` |
| 12 | `GET /api/emails/{id} (not found)` | Fetch a non-existent email | `GET /api/emails/does-not-exist` | HTTP 404 |
| 13 | `PATCH /api/emails/{id} (mark read)` | Mark an email as read | `PATCH /api/emails/<id>` with body `{ read: true }` | HTTP 204; subsequent GET shows `read: true` |
| 14 | `POST /api/emails/{id}/analyze` | Trigger AI analysis for an email | `POST /api/emails/<id>/analyze` | HTTP 200; response has `category`, `sentiment`, `summary`, `suggestedActions` |
| 15 | `POST /api/send-email` | Send an email and verify it in sent folder | `POST /api/send-email` with `{ to, subject, body }` | HTTP 200; response has `id`, `to`, `subject`; GET /api/emails?folder=sent returns it |
| 16 | `Per-user isolation` | Different X-User-Email headers see different data | Save credentials for user A; query with user B header | User B sees `imap: false` (independent DB) |
| 17 | `CORS preflight` | OPTIONS request returns CORS headers | `OPTIONS /api/emails` with `Origin` header | Response includes `Access-Control-Allow-Origin` |
| 18 | `PATCH /api/emails/{id} (not found)` | Patch a non-existent email | `PATCH /api/emails/does-not-exist` with `{ read: true }` | HTTP 404 |

### Notes

- Tests 8, 14, and 15 require real IMAP/SMTP/Gemini credentials and are **cloud-only** (skipped on localhost unless credentials are configured via environment variables).
- Test 17 (CORS) only applies to the cloud deployment where API Gateway + Lambda handle preflight.
- All other tests can run on both localhost and cloud.
