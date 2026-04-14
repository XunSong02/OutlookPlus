/**
 * OutlookPlus Integration Tests
 *
 * Verifies end-to-end code pathways spanning the frontend API client
 * and the backend REST API.  Controlled by environment variables:
 *
 *   TEST_API_BASE_URL  – backend URL (default: http://localhost:8000)
 *   TEST_USER_EMAIL    – X-User-Email header for per-user DB routing
 *   TEST_IMAP_HOST / TEST_IMAP_PORT / TEST_IMAP_USERNAME / TEST_IMAP_PASSWORD
 *   TEST_SMTP_HOST / TEST_SMTP_PORT / TEST_SMTP_USERNAME / TEST_SMTP_PASSWORD
 *   TEST_GEMINI_API_KEY / TEST_GEMINI_MODEL
 *
 * Tests that need real IMAP/SMTP/Gemini credentials are skipped when
 * the relevant env vars are not set (they run only in cloud CI).
 */

import fetch from "cross-fetch";

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

const BASE =
  process.env.TEST_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://localhost:8000";

const USER_EMAIL =
  process.env.TEST_USER_EMAIL || `integration-test-${Date.now()}@test.com`;

const CLOUD = BASE.includes("execute-api") || BASE.includes("amplifyapp");

function url(path: string): string {
  return `${BASE}${path}`;
}

function headers(extra: Record<string, string> = {}): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-User-Email": USER_EMAIL,
    ...extra,
  };
}

async function api(
  path: string,
  opts: { method?: string; body?: unknown; headers?: Record<string, string> } = {}
) {
  const res = await fetch(url(path), {
    method: opts.method ?? "GET",
    headers: headers(opts.headers),
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  return res;
}

/* ------------------------------------------------------------------ */
/*  Credential tests                                                  */
/* ------------------------------------------------------------------ */

describe("Credential lifecycle", () => {
  // Test 1
  test("GET /api/credentials/status returns all false when unconfigured", async () => {
    const res = await api("/api/credentials/status");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ imap: false, smtp: false, gemini: false });
  });

  // Test 2
  test("POST /api/credentials saves IMAP and returns updated status", async () => {
    const res = await api("/api/credentials", {
      method: "POST",
      body: {
        imap: {
          host: "imap.test.com",
          port: 993,
          username: "user@test.com",
          password: "pass123",
        },
      },
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.imap).toBe(true);
  });

  // Test 3
  test("POST /api/credentials saves SMTP and returns updated status", async () => {
    const res = await api("/api/credentials", {
      method: "POST",
      body: {
        smtp: {
          host: "smtp.test.com",
          port: 587,
          username: "user@test.com",
          password: "pass123",
        },
      },
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.smtp).toBe(true);
  });

  // Test 4
  test("POST /api/credentials saves Gemini and returns updated status", async () => {
    const res = await api("/api/credentials", {
      method: "POST",
      body: {
        gemini: { api_key: "fake-key-for-test", model: "gemini-3-flash-preview" },
      },
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.gemini).toBe(true);
  });

  // Test 5
  test("GET /api/credentials/status shows all true after saving all three", async () => {
    const res = await api("/api/credentials/status");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({ imap: true, smtp: true, gemini: true });
  });

  // Test 6
  test("DELETE /api/credentials?cred_type=gemini removes gemini only", async () => {
    const delRes = await fetch(url("/api/credentials?cred_type=gemini"), {
      method: "DELETE",
      headers: headers(),
    });
    expect([200, 204]).toContain(delRes.status);

    const statusRes = await api("/api/credentials/status");
    const body = await statusRes.json();
    expect(body.gemini).toBe(false);
    expect(body.imap).toBe(true);
    expect(body.smtp).toBe(true);
  });
});

/* ------------------------------------------------------------------ */
/*  Error handling                                                    */
/* ------------------------------------------------------------------ */

describe("Error handling", () => {
  // Test 7
  test("POST /api/ingest returns 400 when IMAP credentials are fake", async () => {
    // The test user has IMAP creds from above (fake host), so ingest
    // should fail with a connection error → 502, OR if we use a fresh
    // user with no IMAP at all → 400.
    const freshUser = `no-imap-${Date.now()}@test.com`;
    const res = await fetch(url("/api/ingest"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Email": freshUser },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.detail).toBeDefined();
  });

  // Test 12
  test("GET /api/emails/does-not-exist returns 404", async () => {
    const res = await api("/api/emails/does-not-exist");
    expect(res.status).toBe(404);
  });

  // Test 18
  test("PATCH /api/emails/does-not-exist returns 404", async () => {
    const res = await api("/api/emails/does-not-exist", {
      method: "PATCH",
      body: { read: true },
    });
    expect(res.status).toBe(404);
  });
});

/* ------------------------------------------------------------------ */
/*  Per-user isolation                                                */
/* ------------------------------------------------------------------ */

describe("Per-user DB isolation", () => {
  // Test 16
  test("Different X-User-Email headers see independent data", async () => {
    // User A saved credentials above
    const userA = USER_EMAIL;
    const resA = await fetch(url("/api/credentials/status"), {
      headers: headers({ "X-User-Email": userA }),
    });
    const bodyA = await resA.json();
    expect(bodyA.imap).toBe(true);

    // User B is completely fresh — should see nothing
    const userB = `isolated-user-${Date.now()}@test.com`;
    const resB = await fetch(url("/api/credentials/status"), {
      headers: headers({ "X-User-Email": userB }),
    });
    const bodyB = await resB.json();
    expect(bodyB.imap).toBe(false);
    expect(bodyB.smtp).toBe(false);
    expect(bodyB.gemini).toBe(false);
  });
});

/* ------------------------------------------------------------------ */
/*  Email listing (empty folder)                                      */
/* ------------------------------------------------------------------ */

describe("Email listing", () => {
  // Test 10
  test("GET /api/emails?folder=sent returns an array (may be empty)", async () => {
    const res = await api("/api/emails?folder=sent&limit=50");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.items)).toBe(true);
  });
});

/* ------------------------------------------------------------------ */
/*  CORS (cloud-only)                                                 */
/* ------------------------------------------------------------------ */

const describeCloud = CLOUD ? describe : describe.skip;

describeCloud("CORS (cloud-only)", () => {
  // Test 17
  test("OPTIONS /api/emails returns CORS headers", async () => {
    const res = await fetch(url("/api/emails"), {
      method: "OPTIONS",
      headers: {
        Origin: "https://example.com",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-User-Email",
      },
    });
    // FastAPI CORSMiddleware responds to preflight
    expect([200, 204]).toContain(res.status);
    const acao = res.headers.get("access-control-allow-origin");
    expect(acao).toBeTruthy();
  });
});

/* ------------------------------------------------------------------ */
/*  Cloud-only: full ingest → list → detail → analyze → send pipeline */
/*                                                                    */
/*  These tests require real IMAP/SMTP/Gemini credentials set via     */
/*  environment variables. Skipped when those are absent.              */
/* ------------------------------------------------------------------ */

const hasImapCreds = !!(
  process.env.TEST_IMAP_HOST &&
  process.env.TEST_IMAP_USERNAME &&
  process.env.TEST_IMAP_PASSWORD
);
const hasSmtpCreds = !!(
  process.env.TEST_SMTP_HOST &&
  process.env.TEST_SMTP_USERNAME &&
  process.env.TEST_SMTP_PASSWORD
);
const hasGeminiKey = !!process.env.TEST_GEMINI_API_KEY;

const LIVE_USER =
  process.env.TEST_IMAP_USERNAME || "live-test@test.com";

const describeIngest = hasImapCreds ? describe : describe.skip;
const describeAnalyze = hasImapCreds && hasGeminiKey ? describe : describe.skip;
const describeSend = hasSmtpCreds ? describe : describe.skip;

// Helper: save real credentials for the live user
async function seedLiveCredentials() {
  const h = {
    "Content-Type": "application/json",
    "X-User-Email": LIVE_USER,
  };
  if (hasImapCreds) {
    await fetch(url("/api/credentials"), {
      method: "POST",
      headers: h,
      body: JSON.stringify({
        imap: {
          host: process.env.TEST_IMAP_HOST,
          port: Number(process.env.TEST_IMAP_PORT || 993),
          username: process.env.TEST_IMAP_USERNAME,
          password: process.env.TEST_IMAP_PASSWORD,
        },
      }),
    });
  }
  if (hasSmtpCreds) {
    await fetch(url("/api/credentials"), {
      method: "POST",
      headers: h,
      body: JSON.stringify({
        smtp: {
          host: process.env.TEST_SMTP_HOST,
          port: Number(process.env.TEST_SMTP_PORT || 587),
          username: process.env.TEST_SMTP_USERNAME,
          password: process.env.TEST_SMTP_PASSWORD,
        },
      }),
    });
  }
  if (hasGeminiKey) {
    await fetch(url("/api/credentials"), {
      method: "POST",
      headers: h,
      body: JSON.stringify({
        gemini: {
          api_key: process.env.TEST_GEMINI_API_KEY,
          model: process.env.TEST_GEMINI_MODEL || "gemini-3-flash-preview",
        },
      }),
    });
  }
}

let firstEmailId: string | null = null;

describeIngest("Email ingest + list + detail (cloud-only, needs IMAP creds)", () => {
  beforeAll(async () => {
    await seedLiveCredentials();
  });

  // Test 8
  test("POST /api/ingest fetches emails", async () => {
    const res = await fetch(url("/api/ingest"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Email": LIVE_USER,
      },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(typeof body.ingested).toBe("number");
  });

  // Test 9
  test("GET /api/emails?folder=inbox returns emails after ingest", async () => {
    const res = await fetch(url("/api/emails?folder=inbox&limit=50"), {
      headers: { "X-User-Email": LIVE_USER },
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.items.length).toBeGreaterThan(0);

    const first = body.items[0];
    expect(first.id).toBeDefined();
    expect(first.subject).toBeDefined();
    expect(first.folder).toBe("inbox");

    firstEmailId = first.id;
  });

  // Test 11
  test("GET /api/emails/{id} returns email detail", async () => {
    expect(firstEmailId).not.toBeNull();
    const res = await fetch(
      url(`/api/emails/${encodeURIComponent(firstEmailId!)}`),
      { headers: { "X-User-Email": LIVE_USER } }
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.id).toBe(firstEmailId);
    expect(body.sender).toBeDefined();
    expect(body.date).toBeDefined();
    expect(body.aiAnalysis).toBeDefined();
  });

  // Test 13
  test("PATCH /api/emails/{id} marks email as read", async () => {
    expect(firstEmailId).not.toBeNull();
    const patchRes = await fetch(
      url(`/api/emails/${encodeURIComponent(firstEmailId!)}`),
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-User-Email": LIVE_USER },
        body: JSON.stringify({ read: true }),
      }
    );
    expect(patchRes.status).toBe(204);

    // Verify by re-fetching
    const getRes = await fetch(
      url(`/api/emails/${encodeURIComponent(firstEmailId!)}`),
      { headers: { "X-User-Email": LIVE_USER } }
    );
    const body = await getRes.json();
    expect(body.read).toBe(true);
  });
});

describeAnalyze("AI analysis (cloud-only, needs IMAP + Gemini creds)", () => {
  // Test 14
  test("POST /api/emails/{id}/analyze returns AI analysis", async () => {
    expect(firstEmailId).not.toBeNull();
    const res = await fetch(
      url(`/api/emails/${encodeURIComponent(firstEmailId!)}/analyze`),
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Email": LIVE_USER },
        body: JSON.stringify({}),
      }
    );
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.category).toBeDefined();
    expect(body.sentiment).toBeDefined();
    expect(typeof body.summary).toBe("string");
    expect(Array.isArray(body.suggestedActions)).toBe(true);
  });
});

describeSend("Send email (cloud-only, needs SMTP creds)", () => {
  // Test 15
  test("POST /api/send-email sends and persists in sent folder", async () => {
    const res = await fetch(url("/api/send-email"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Email": LIVE_USER },
      body: JSON.stringify({
        to: LIVE_USER,
        subject: `Integration test ${Date.now()}`,
        body: "This is an automated integration test email.",
      }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.id).toBeDefined();
    expect(body.subject).toContain("Integration test");

    // Verify in sent folder
    const sentRes = await fetch(url("/api/emails?folder=sent&limit=5"), {
      headers: { "X-User-Email": LIVE_USER },
    });
    const sent = await sentRes.json();
    expect(sent.items.some((e: any) => e.id === body.id)).toBe(true);
  });
});
