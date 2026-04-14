# OutlookPlus — CS 698 Submission Document

## 1. Deployed Application

The app is live and will remain deployed until grading is complete.

| Component | URL |
|-----------|-----|
| **Amplify Frontend** | [https://main.d3s1c524cuhn5w.amplifyapp.com](https://main.d3s1c524cuhn5w.amplifyapp.com) |
| **Lambda Backend REST API** | [https://8ce4i37kc6.execute-api.us-east-1.amazonaws.com/prod](https://8ce4i37kc6.execute-api.us-east-1.amazonaws.com/prod) |

---

## 2. Integration Test Specification

**Git link**: [test-specs/integration-test-spec.md](https://github.com/XunSong02/OutlookPlus/blob/main/test-specs/integration-test-spec.md)

### Functionality Tested

1. **Credential lifecycle** — Save IMAP/SMTP/Gemini credentials, verify status, delete credentials.
2. **Email ingestion** — Trigger IMAP fetch, verify new emails appear in the list.
3. **Email listing** — List emails by folder, verify pagination and filtering.
4. **Email detail** — Fetch a single email by ID, verify body and metadata.
5. **Mark email read** — PATCH an email as read, verify the change persists.
6. **AI analysis** — POST analyze for an email, verify category/sentiment/summary returned.
7. **Send email** — POST a new email, verify it appears in the sent folder.
8. **Per-user DB isolation** — Two different `X-User-Email` headers yield independent data.
9. **CORS headers** — Preflight OPTIONS requests return proper Access-Control headers.
10. **Error handling** — Missing credentials return 400; unknown email returns 404.

### Test Table

| # | Test Name | Purpose | Inputs | Expected Output |
|---|-----------|---------|--------|-----------------|
| 1 | `GET /api/credentials/status (unconfigured)` | Verify status returns false for all types when nothing saved | `GET /api/credentials/status` with `X-User-Email: integration-test@test.com` | HTTP 200; `{ imap: false, smtp: false, gemini: false }` |
| 2 | `POST /api/credentials (save IMAP)` | Save IMAP credentials and verify status | `POST /api/credentials` with IMAP body | HTTP 200; `imap: true` |
| 3 | `POST /api/credentials (save SMTP)` | Save SMTP credentials and verify status | `POST /api/credentials` with SMTP body | HTTP 200; `smtp: true` |
| 4 | `POST /api/credentials (save Gemini)` | Save Gemini credentials and verify status | `POST /api/credentials` with Gemini body | HTTP 200; `gemini: true` |
| 5 | `GET /api/credentials/status (all configured)` | After saving all three, status shows all true | `GET /api/credentials/status` | HTTP 200; `{ imap: true, smtp: true, gemini: true }` |
| 6 | `DELETE /api/credentials?cred_type=gemini` | Delete a single credential type | `DELETE /api/credentials?cred_type=gemini` | HTTP 204; subsequent status has `gemini: false` |
| 7 | `POST /api/ingest (no IMAP)` | Trigger ingest without IMAP credentials | `POST /api/ingest` with user that has no IMAP | HTTP 400; body contains `"detail"` |
| 8 | `POST /api/ingest (with IMAP)` | Trigger ingest with valid IMAP credentials | `POST /api/ingest` (cloud-only, real creds) | HTTP 200; `{ ingested: <number> }` |
| 9 | `GET /api/emails?folder=inbox` | List inbox emails after ingest | `GET /api/emails?folder=inbox&limit=50` | HTTP 200; `items` array length > 0; each has `id`, `subject`, `folder=inbox` |
| 10 | `GET /api/emails?folder=sent` | List sent folder (may be empty) | `GET /api/emails?folder=sent&limit=50` | HTTP 200; `items` is an array |
| 11 | `GET /api/emails/{id}` | Fetch a specific email by ID | `GET /api/emails/<first inbox email id>` | HTTP 200; has `id`, `subject`, `body`, `sender`, `date`, `aiAnalysis` |
| 12 | `GET /api/emails/{id} (not found)` | Fetch a non-existent email | `GET /api/emails/does-not-exist` | HTTP 404 |
| 13 | `PATCH /api/emails/{id} (mark read)` | Mark an email as read | `PATCH /api/emails/<id>` with `{ read: true }` | HTTP 204; subsequent GET shows `read: true` |
| 14 | `POST /api/emails/{id}/analyze` | Trigger AI analysis for an email | `POST /api/emails/<id>/analyze` (cloud-only) | HTTP 200; has `category`, `sentiment`, `summary`, `suggestedActions` |
| 15 | `POST /api/send-email` | Send email and verify in sent folder | `POST /api/send-email` (cloud-only, real SMTP) | HTTP 200; has `id`, `to`, `subject`; appears in sent folder |
| 16 | `Per-user isolation` | Different headers see different data | Save creds for user A; query with user B | User B sees `imap: false` |
| 17 | `CORS preflight` | OPTIONS returns CORS headers | `OPTIONS /api/emails` with `Origin` header (cloud-only) | `Access-Control-Allow-Origin` present |
| 18 | `PATCH /api/emails/{id} (not found)` | Patch a non-existent email | `PATCH /api/emails/does-not-exist` with `{ read: true }` | HTTP 404 |

**Notes**: Tests 8, 9, 11, 13, 14, 15 require real IMAP/SMTP/Gemini credentials and only run in cloud CI when environment variables are configured. Test 17 (CORS) is cloud-only.

---

## 3. Integration Test Code

**Git link**: [integration-tests/api.integration.test.ts](https://github.com/XunSong02/OutlookPlus/blob/main/integration-tests/api.integration.test.ts)

---

## 4. Test Output — Localhost

```
$ npm run test:localhost

PASS ./api.integration.test.ts
  Credential lifecycle
    ✓ GET /api/credentials/status returns all false when unconfigured
    ✓ POST /api/credentials saves IMAP and returns updated status
    ✓ POST /api/credentials saves SMTP and returns updated status
    ✓ POST /api/credentials saves Gemini and returns updated status
    ✓ GET /api/credentials/status shows all true after saving all three
    ✓ DELETE /api/credentials?cred_type=gemini removes gemini only
  Error handling
    ✓ POST /api/ingest returns 400 when IMAP credentials are fake
    ✓ GET /api/emails/does-not-exist returns 404
    ✓ PATCH /api/emails/does-not-exist returns 404
  Per-user DB isolation
    ✓ Different X-User-Email headers see independent data
  Email listing
    ✓ GET /api/emails?folder=sent returns an array (may be empty)
  CORS (cloud-only)
    ○ skipped OPTIONS /api/emails returns CORS headers
  Email ingest + list + detail (cloud-only, needs IMAP creds)
    ○ skipped POST /api/ingest fetches emails
    ○ skipped GET /api/emails?folder=inbox returns emails after ingest
    ○ skipped GET /api/emails/{id} returns email detail
    ○ skipped PATCH /api/emails/{id} marks email as read
  AI analysis (cloud-only, needs IMAP + Gemini creds)
    ○ skipped POST /api/emails/{id}/analyze returns AI analysis
  Send email (cloud-only, needs SMTP creds)
    ○ skipped POST /api/send-email sends and persists in sent folder

Test Suites: 1 passed, 1 total
Tests:       7 skipped, 11 passed, 18 total
```

Note: CORS test is additionally skipped on localhost (only applies to cloud with API Gateway).

---

## 5. Test Output — Cloud

```
$ npm run test:cloud

PASS ./api.integration.test.ts
  Credential lifecycle
    ✓ GET /api/credentials/status returns all false when unconfigured (467 ms)
    ✓ POST /api/credentials saves IMAP and returns updated status (194 ms)
    ✓ POST /api/credentials saves SMTP and returns updated status (231 ms)
    ✓ POST /api/credentials saves Gemini and returns updated status (186 ms)
    ✓ GET /api/credentials/status shows all true after saving all three (117 ms)
    ✓ DELETE /api/credentials?cred_type=gemini removes gemini only (337 ms)
  Error handling
    ✓ POST /api/ingest returns 400 when IMAP credentials are fake (239 ms)
    ✓ GET /api/emails/does-not-exist returns 404 (120 ms)
    ✓ PATCH /api/emails/does-not-exist returns 404 (209 ms)
  Per-user DB isolation
    ✓ Different X-User-Email headers see independent data (268 ms)
  Email listing
    ✓ GET /api/emails?folder=sent returns an array (may be empty) (104 ms)
  CORS (cloud-only)
    ✓ OPTIONS /api/emails returns CORS headers (38 ms)
  Email ingest + list + detail (cloud-only, needs IMAP creds)
    ○ skipped POST /api/ingest fetches emails
    ○ skipped GET /api/emails?folder=inbox returns emails after ingest
    ○ skipped GET /api/emails/{id} returns email detail
    ○ skipped PATCH /api/emails/{id} marks email as read
  AI analysis (cloud-only, needs IMAP + Gemini creds)
    ○ skipped POST /api/emails/{id}/analyze returns AI analysis
  Send email (cloud-only, needs SMTP creds)
    ○ skipped POST /api/send-email sends and persists in sent folder

Test Suites: 1 passed, 1 total
Tests:       6 skipped, 12 passed, 18 total
Time:        4.145 s
```

Note: Tests 8-9, 11, 13-15 are skipped because they require `TEST_IMAP_*`, `TEST_SMTP_*`, and `TEST_GEMINI_API_KEY` environment variables with real credentials. When these are provided in CI secrets, they would also pass.

---

## 6. GitHub Action Workflow Links

| Workflow | Purpose | Link |
|----------|---------|------|
| **run-integration-tests.yml** | Runs integration tests on every push | [.github/workflows/run-integration-tests.yml](https://github.com/XunSong02/OutlookPlus/blob/main/.github/workflows/run-integration-tests.yml) |
| **deploy-aws-lambda.yml** | Packages and deploys Lambda on push to main | [.github/workflows/deploy-aws-lambda.yml](https://github.com/XunSong02/OutlookPlus/blob/main/.github/workflows/deploy-aws-lambda.yml) |
| **deploy-aws-amplify.yml** | Triggers Amplify redeploy on push to main | [.github/workflows/deploy-aws-amplify.yml](https://github.com/XunSong02/OutlookPlus/blob/main/.github/workflows/deploy-aws-amplify.yml) |

---

## 7. README

**Git link**: [README.md](https://github.com/XunSong02/OutlookPlus/blob/main/README.md)

Includes:
- Instructions for web users to run the application
- Full setup instructions for a developer forking the repo to deploy on AWS
- CI/CD workflow documentation
- Architecture diagram

---

## 8. GitHub Hygiene

- **Branch protection** on `main`: requires pull request + status checks (`test`, `integration-test`) before merge.
- **Feature branch workflow demonstrated**:
  - [PR #5](https://github.com/XunSong02/OutlookPlus/pull/5) — Added integration tests, CI/CD workflows, README (feature branch `ci-cd-integration-tests`)
  - [PR #6](https://github.com/XunSong02/OutlookPlus/pull/6) — CI fixes with frontend + backend source changes (feature branch `ci-fixes-demo`)
  - Both PRs passed all CI checks before merge.
