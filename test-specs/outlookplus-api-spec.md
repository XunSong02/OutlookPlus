# Test Specification: `frontend/src/app/services/outlookplusApi.ts`

## File Description

Sole API communication layer for the OutlookPlus frontend. Provides a generic `request()` function that handles HTTP calls with authentication, error handling, and content-type parsing, plus 7 domain-specific exported functions that each delegate to `request()` with the appropriate endpoint, method, and parameters.

## Functions

1. `getApiBaseUrl()`
2. `getAuthToken()`
3. `request<T>(path, opts)`
4. `listEmails(input)`
5. `getEmail(input)`
6. `patchEmailRead(input)`
7. `sendEmail(input)`
8. `executeEmailAction(input)`
9. `runAiRequest(input)`
10. `suggestCompose(input)`

## Test Table

| Test Name | Function Under Test | Test Purpose | Test Inputs | Expected Output |
|-----------|---------------------|--------------|-------------|-----------------|
| getApiBaseUrl: returns env var with trailing slashes stripped | `getApiBaseUrl` | Verify URL resolution and normalization | `VITE_API_BASE_URL = "http://localhost:8000///"` | Returns `"http://localhost:8000"` |
| getAuthToken: returns trimmed token or undefined | `getAuthToken` | Verify token retrieval and whitespace handling | `VITE_AUTH_TOKEN = "  my-token  "` | Returns `"my-token"` |
| request: successful JSON response is parsed and returned | `request` | Cover happy path: URL construction, auth header, JSON parsing | Mock `fetch` returns `{ ok: true, status: 200, headers: { "content-type": "application/json" }, json: () => ({ key: "val" }) }`, `VITE_AUTH_TOKEN = "tok"` | Returns `{ key: "val" }`; `fetch` called with `Authorization: "Bearer tok"` |
| request: non-ok status throws Error with status and body | `request` | Cover the error branch for non-2xx responses | Mock `fetch` returns `{ ok: false, status: 500, statusText: "Internal Server Error", text: () => "details" }` | Throws `Error("API 500 Internal Server Error: details")` |
| request: 204 returns undefined and POST body is JSON-stringified | `request` | Cover 204 no-content branch and body serialization | Call `request("/test", { method: "POST", body: { a: 1 } })`, mock `fetch` returns `{ ok: true, status: 204 }` | Returns `undefined`; `fetch` called with `body: '{"a":1}'`, `Content-Type: "application/json"` |
| listEmails: builds query params and calls GET | `listEmails` | Verify URL parameter construction | `{ folder: "inbox", label: "Work", limit: 10, cursor: "2025-01-01" }` | `request` called with path containing `folder=inbox&label=Work&limit=10&cursor=2025-01-01`, method GET |
| getEmail: URL-encodes the email ID | `getEmail` | Verify correct endpoint URL | `{ emailId: "msg/1" }` | `request` called with path `/api/emails/msg%2F1`, method GET |
| patchEmailRead: sends PATCH with read boolean | `patchEmailRead` | Verify method and payload | `{ emailId: "msg-1", read: true }` | `request` called with method PATCH, body `{ read: true }` |
| sendEmail: sends POST to /api/send-email | `sendEmail` | Verify endpoint and payload | `{ to: "a@b.com", subject: "Hi", body: "Hello" }` | `request` called with path `/api/send-email`, method POST, body has all 3 fields |
| executeEmailAction: sends POST to /api/email-actions | `executeEmailAction` | Verify endpoint and payload | `{ emailId: "msg-1", action: "archive" }` | `request` called with path `/api/email-actions`, method POST |
| runAiRequest: sends POST to /api/ai/request | `runAiRequest` | Verify endpoint and payload | `{ emailId: "msg-1", prompt: "Summarize" }` | `request` called with path `/api/ai/request`, method POST |
| suggestCompose: sends POST to /api/ai/compose with all fields | `suggestCompose` | Verify full payload construction including optional fields | `{ to: "a@b.com", cc: "c@d.com", subject: "Hi", body: "Draft", instruction: "Make formal" }` | `request` called with path `/api/ai/compose`, body has `to`, `cc`, `subject`, `body`, `instruction` |
