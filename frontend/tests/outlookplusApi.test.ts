/**
 * Unit tests for frontend/src/app/services/outlookplusApi.ts
 *
 * Follows the test specification at test-specs/outlookplus-api-spec.md exactly.
 *
 * The AST transformer (jest-import-meta-transformer.cjs) rewrites
 * `import.meta.env.X` → `process.env.X` at compile time, so we control
 * environment variables via `process.env` in each test.
 *
 * `fetch` is mocked globally for every test via jest.spyOn.
 */

import {
  getApiBaseUrl,
  getAuthToken,
  request,
  listEmails,
  getEmail,
  patchEmailRead,
  sendEmail,
  executeEmailAction,
  runAiRequest,
  suggestCompose,
} from '../src/app/services/outlookplusApi';

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

/** Build a minimal mock Response object accepted by the fetch mock. */
function mockResponse(overrides: {
  ok?: boolean;
  status?: number;
  statusText?: string;
  headers?: Record<string, string>;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
}): Response {
  const headers = new Headers(overrides.headers ?? {});
  return {
    ok: overrides.ok ?? true,
    status: overrides.status ?? 200,
    statusText: overrides.statusText ?? 'OK',
    headers,
    json: overrides.json ?? (() => Promise.resolve({})),
    text: overrides.text ?? (() => Promise.resolve('')),
  } as unknown as Response;
}

/* ------------------------------------------------------------------ */
/*  Test suite                                                        */
/* ------------------------------------------------------------------ */

describe('outlookplusApi.ts', () => {
  /** Keep a reference so we can inspect call args. */
  let fetchMock: jest.Mock;

  beforeEach(() => {
    jest.restoreAllMocks();
    // Reset all VITE_* env vars to a known blank state
    delete process.env.VITE_API_BASE_URL;
    delete process.env.VITE_API_URL;
    delete process.env.VITE_AUTH_TOKEN;

    // Assign a fresh mock to global.fetch for every test
    fetchMock = jest.fn().mockResolvedValue(
      mockResponse({
        ok: true,
        status: 200,
        headers: { 'content-type': 'application/json' },
        json: () => Promise.resolve({ _default: true }),
      }),
    );
    globalThis.fetch = fetchMock;
  });

  /* ============================================================== */
  /*  Test 1 – getApiBaseUrl                                         */
  /* ============================================================== */
  test('getApiBaseUrl: returns env var with trailing slashes stripped', () => {
    process.env.VITE_API_BASE_URL = 'http://localhost:8000///';

    const result = getApiBaseUrl();

    expect(result).toBe('http://localhost:8000');
  });

  /* ============================================================== */
  /*  Test 2 – getAuthToken                                          */
  /* ============================================================== */
  test('getAuthToken: returns trimmed token or undefined', () => {
    process.env.VITE_AUTH_TOKEN = '  my-token  ';

    expect(getAuthToken()).toBe('my-token');
  });

  /* ============================================================== */
  /*  Test 3 – request: JSON success with auth header                */
  /* ============================================================== */
  test('request: successful JSON response is parsed and returned', async () => {
    process.env.VITE_AUTH_TOKEN = 'tok';

    fetchMock.mockResolvedValueOnce(
      mockResponse({
        ok: true,
        status: 200,
        headers: { 'content-type': 'application/json' },
        json: () => Promise.resolve({ key: 'val' }),
      }),
    );

    const result = await request('/test-path');

    expect(result).toEqual({ key: 'val' });

    // Verify fetch was called with the correct Authorization header
    const [, fetchOpts] = fetchMock.mock.calls[0];
    expect(fetchOpts.headers['Authorization']).toBe('Bearer tok');
  });

  /* ============================================================== */
  /*  Test 4 – request: non-ok status throws Error                   */
  /* ============================================================== */
  test('request: non-ok status throws Error with status and body', async () => {
    fetchMock.mockResolvedValueOnce(
      mockResponse({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: () => Promise.resolve('details'),
      }),
    );

    await expect(request('/fail')).rejects.toThrow(
      'API 500 Internal Server Error: details',
    );
  });

  /* ============================================================== */
  /*  Test 5 – request: 204 + POST body serialisation                */
  /* ============================================================== */
  test('request: 204 returns undefined and POST body is JSON-stringified', async () => {
    fetchMock.mockResolvedValueOnce(
      mockResponse({ ok: true, status: 204 }),
    );

    const result = await request('/test', { method: 'POST', body: { a: 1 } });

    // 204 branch returns undefined
    expect(result).toBeUndefined();

    // Verify fetch received the JSON-stringified body and Content-Type
    const [, fetchOpts] = fetchMock.mock.calls[0];
    expect(fetchOpts.body).toBe('{"a":1}');
    expect(fetchOpts.headers['Content-Type']).toBe('application/json');
  });

  /* ============================================================== */
  /*  Test 6 – listEmails: query param construction                  */
  /* ============================================================== */
  test('listEmails: builds query params and calls GET', async () => {
    fetchMock.mockResolvedValueOnce(
      mockResponse({
        ok: true,
        status: 200,
        headers: { 'content-type': 'application/json' },
        json: () => Promise.resolve({ items: [], nextCursor: null }),
      }),
    );

    await listEmails({
      folder: 'inbox',
      label: 'Work',
      limit: 10,
      cursor: '2025-01-01',
    });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/emails?');
    expect(url).toContain('folder=inbox');
    expect(url).toContain('label=Work');
    expect(url).toContain('limit=10');
    expect(url).toContain('cursor=2025-01-01');
    expect(opts.method).toBe('GET');
  });

  /* ============================================================== */
  /*  Test 7 – getEmail: URL-encodes the email ID                   */
  /* ============================================================== */
  test('getEmail: URL-encodes the email ID', async () => {
    await getEmail({ emailId: 'msg/1' });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/emails/msg%2F1');
    expect(opts.method).toBe('GET');
  });

  /* ============================================================== */
  /*  Test 8 – patchEmailRead: sends PATCH with read boolean         */
  /* ============================================================== */
  test('patchEmailRead: sends PATCH with read boolean', async () => {
    fetchMock.mockResolvedValueOnce(mockResponse({ ok: true, status: 204 }));

    await patchEmailRead({ emailId: 'msg-1', read: true });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/emails/msg-1');
    expect(opts.method).toBe('PATCH');
    expect(JSON.parse(opts.body)).toEqual({ read: true });
  });

  /* ============================================================== */
  /*  Test 9 – sendEmail: sends POST to /api/send-email              */
  /* ============================================================== */
  test('sendEmail: sends POST to /api/send-email', async () => {
    await sendEmail({ to: 'a@b.com', subject: 'Hi', body: 'Hello' });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/send-email');
    expect(opts.method).toBe('POST');
    const sentBody = JSON.parse(opts.body);
    expect(sentBody.to).toBe('a@b.com');
    expect(sentBody.subject).toBe('Hi');
    expect(sentBody.body).toBe('Hello');
  });

  /* ============================================================== */
  /*  Test 10 – executeEmailAction: POST /api/email-actions          */
  /* ============================================================== */
  test('executeEmailAction: sends POST to /api/email-actions', async () => {
    await executeEmailAction({ emailId: 'msg-1', action: 'archive' });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/email-actions');
    expect(opts.method).toBe('POST');
    const sentBody = JSON.parse(opts.body);
    expect(sentBody.emailId).toBe('msg-1');
    expect(sentBody.action).toBe('archive');
  });

  /* ============================================================== */
  /*  Test 11 – runAiRequest: POST /api/ai/request                   */
  /* ============================================================== */
  test('runAiRequest: sends POST to /api/ai/request', async () => {
    await runAiRequest({ emailId: 'msg-1', prompt: 'Summarize' });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/ai/request');
    expect(opts.method).toBe('POST');
    const sentBody = JSON.parse(opts.body);
    expect(sentBody.emailId).toBe('msg-1');
    expect(sentBody.prompt).toBe('Summarize');
  });

  /* ============================================================== */
  /*  Test 12 – suggestCompose: POST /api/ai/compose with all fields */
  /* ============================================================== */
  test('suggestCompose: sends POST to /api/ai/compose with all fields', async () => {
    await suggestCompose({
      to: 'a@b.com',
      cc: 'c@d.com',
      subject: 'Hi',
      body: 'Draft',
      instruction: 'Make formal',
    });

    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/ai/compose');
    expect(opts.method).toBe('POST');
    const sentBody = JSON.parse(opts.body);
    expect(sentBody.to).toBe('a@b.com');
    expect(sentBody.cc).toBe('c@d.com');
    expect(sentBody.subject).toBe('Hi');
    expect(sentBody.body).toBe('Draft');
    expect(sentBody.instruction).toBe('Make formal');
  });
});
