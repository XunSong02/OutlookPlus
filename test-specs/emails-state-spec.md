# Test Specification: `frontend/src/app/state/emails.tsx`

## File Description

Central email state management module for the OutlookPlus frontend. Provides a React Context (`EmailsProvider`) that manages all email data, fetches emails from the backend API across multiple folders, transforms raw API DTOs into typed frontend `Email` objects, and exposes operations for marking emails as read and lazy-loading individual email details. Also normalizes AI-generated suggested actions to ensure exactly 3 action cards in the UI.

## Functions

1. `normalizeSuggestedActions(input, email)`
2. `toEmail(dto)`
3. `EmailsProvider({ children })`
4. `reload(signal?)`
5. `markRead(emailId)`
6. `loadEmail(emailId)`
7. `useEmails()`

## Test Table

| Test Name | Function Under Test | Test Purpose | Test Inputs | Expected Output |
|-----------|---------------------|--------------|-------------|-----------------|
| normalize: valid mixed array is parsed and padded to 3 | `normalizeSuggestedActions` | Cover string items, reply_draft objects, suggestion objects, and padding-to-3 logic in one pass | `input = ["Archive it", { kind: "reply_draft", text: "Sounds good", draft: { to: "a@b.com", subject: "Re: Hi", body: "Ok" } }]`, `email = { sender: { email: "a@b.com" }, subject: "Hi", folder: "inbox" }` | Returns array of length 3: first is `{ kind: "suggestion", text: "Archive it" }`, second is the reply_draft object, third is a fallback `{ kind: "suggestion", text: "Ignore if no action is required." }` |
| normalize: non-array input with inbox folder returns reply_draft fallback first | `normalizeSuggestedActions` | Cover the non-array-input branch and the inbox-specific reply_draft fallback path | `input = null`, `email = { sender: { email: "a@b.com" }, subject: "Hello", folder: "inbox" }` | Returns 3 items; first is `{ kind: "reply_draft", draft: { to: "a@b.com", subject: "Re: Hello", ... } }`, remaining 2 are `{ kind: "suggestion", text: "Ignore if no action is required." }` |
| toEmail: maps full DTO and applies defaults for missing fields | `toEmail` | Cover both the happy-path mapping and the null-coalescing fallback branches | `dto = { id: "1", sender: { name: "Alice", email: "a@b.com" }, subject: "Test", preview: "Prev", body: "<p>Hi</p>", date: "2025-01-01", read: 1, folder: "inbox", labels: ["Work"], aiAnalysis: { category: "Work", sentiment: "positive", summary: "Sum", suggestedActions: ["Do A", "Do B", "Do C"] } }` | Email object with `read=true`, `labels=["Work"]`, `aiAnalysis.suggestedActions` has 3 normalized items, `sender.avatar` is `undefined` |
| EmailsProvider: renders children and provides context value | `EmailsProvider` | Verify the provider renders and context is accessible | Render `<EmailsProvider><TestConsumer /></EmailsProvider>` where `TestConsumer` calls `useEmails()` | `TestConsumer` receives object with `emails` (array), `isLoading` (boolean), `markRead` (function), `reload` (function), `loadEmail` (function) |
| reload: success fetches all 5 folders and combines results | `reload` | Cover the try-branch of reload | Mock `listEmails` to return 2 items for each of 5 folders | State `emails` has 10 items; `isLoading` becomes `false` |
| reload: API failure falls back to mock data | `reload` | Cover the catch-branch of reload | Mock `listEmails` to throw `Error("network fail")` | State `emails` equals `mockEmails`; `isLoading` is `false` |
| markRead: updates local state and calls backend API | `markRead` | Cover the optimistic update and API call | Call `markRead("email-1")` when state has `{ id: "email-1", read: false }` | State email has `read: true`; `patchEmailRead` called with `{ emailId: "email-1", read: true }` |
| loadEmail: fetches detail and merges into existing state | `loadEmail` | Cover the main fetch-and-merge path and the dedup guard | Call `loadEmail("msg-1")` when state has a stub `{ id: "msg-1", body: "" }` | `getEmail` called once with `{ emailId: "msg-1" }`; state email updated with full body; calling `loadEmail("msg-1")` again does NOT call `getEmail` a second time |
| useEmails: throws when used outside EmailsProvider | `useEmails` | Cover the error-guard branch | Render a component calling `useEmails()` WITHOUT wrapping in `EmailsProvider` | Throws `Error("useEmails must be used within EmailsProvider")` |
