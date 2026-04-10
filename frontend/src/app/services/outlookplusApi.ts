/** OutlookPlus API client – handles all frontend-to-backend communication. */
type HttpMethod = 'GET' | 'POST' | 'PATCH';

export function getApiBaseUrl(): string {
  const raw =
    (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
    (import.meta.env.VITE_API_URL as string | undefined) ||
    '';
  return raw.replace(/\/+$/, '');
}

export function getAuthToken(): string | undefined {
  const token = import.meta.env.VITE_AUTH_TOKEN as string | undefined;
  return token && token.trim() ? token.trim() : undefined;
}

export async function request<T>(
  path: string,
  opts: {
    method?: HttpMethod;
    body?: unknown;
    signal?: AbortSignal;
    headers?: Record<string, string>;
  } = {}
): Promise<T> {
  const apiBase = getApiBaseUrl();
  const url = apiBase ? `${apiBase}${path}` : path;

  const headers: Record<string, string> = {
    ...opts.headers,
  };

  const authToken = getAuthToken();
  if (authToken) {
    headers['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;
  }

  let body: BodyInit | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = headers['Content-Type'] ?? 'application/json';
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(url, {
    method: opts.method ?? 'GET',
    headers,
    body,
    signal: opts.signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status} ${res.statusText}${text ? `: ${text}` : ''}`);
  }

  // 204 / no body
  if (res.status === 204) {
    return undefined as unknown as T;
  }

  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await res.json()) as T;
  }

  return (await res.text()) as unknown as T;
}

export type Folder = 'inbox' | 'sent' | 'drafts' | 'trash' | 'spam';

export type EmailSenderDto = {
  name: string;
  email: string;
  avatar?: string | null;
};

export type SuggestedActionDraftDto = {
  to: string;
  subject: string;
  body: string;
};

export type SuggestedActionDto =
  | {
      kind: 'reply_draft';
      text: string;
      draft: SuggestedActionDraftDto;
    }
  | {
      kind: 'suggestion';
      text: string;
    };

export type AiAnalysisDto = {
  category: 'Work' | 'Personal' | 'Finance' | 'Social' | 'Promotions' | 'Urgent';
  sentiment: 'positive' | 'neutral' | 'negative';
  summary: string;
  suggestedActions: Array<string | SuggestedActionDto>;
};

export type EmailDto = {
  id: string;
  sender: EmailSenderDto;
  subject: string;
  preview: string;
  body: string;
  date: string;
  read: boolean;
  folder: Folder;
  labels: string[];
  aiAnalysis: AiAnalysisDto;
};

export type EmailListResponse = {
  items: EmailDto[];
  nextCursor?: string | null;
};

export async function listEmails(input: {
  folder: Folder;
  label?: string;
  limit?: number;
  cursor?: string;
  signal?: AbortSignal;
}): Promise<EmailListResponse> {
  const params = new URLSearchParams();
  params.set('folder', input.folder);
  if (input.label) params.set('label', input.label);
  if (input.limit) params.set('limit', String(input.limit));
  if (input.cursor) params.set('cursor', input.cursor);

  return request<EmailListResponse>(`/api/emails?${params.toString()}`, {
    method: 'GET',
    signal: input.signal,
  });
}

export async function getEmail(input: {
  emailId: string;
  signal?: AbortSignal;
}): Promise<EmailDto> {
  return request<EmailDto>(`/api/emails/${encodeURIComponent(input.emailId)}`, {
    method: 'GET',
    signal: input.signal,
  });
}

export async function patchEmailRead(input: {
  emailId: string;
  read: boolean;
  signal?: AbortSignal;
}): Promise<void> {
  await request<void>(`/api/emails/${encodeURIComponent(input.emailId)}`, {
    method: 'PATCH',
    body: { read: input.read },
    signal: input.signal,
  });
}

export async function sendEmail(input: {
  to: string;
  subject: string;
  body: string;
  signal?: AbortSignal;
}): Promise<{ id: string; to: string; subject: string }> {
  return request<{ id: string; to: string; subject: string }>(`/api/send-email`, {
    method: 'POST',
    body: input,
    signal: input.signal,
  });
}

export async function executeEmailAction(input: {
  emailId: string;
  action: string;
  signal?: AbortSignal;
}): Promise<{ emailId: string; action: string; status: 'ok' }> {
  return request<{ emailId: string; action: string; status: 'ok' }>(`/api/email-actions`, {
    method: 'POST',
    body: input,
    signal: input.signal,
  });
}

export async function runAiRequest(input: {
  emailId: string;
  prompt: string;
  signal?: AbortSignal;
}): Promise<{ emailId: string; responseText: string }> {
  return request<{ emailId: string; responseText: string }>(`/api/ai/request`, {
    method: 'POST',
    body: input,
    signal: input.signal,
  });
}

export async function suggestCompose(input: {
  to?: string;
  cc?: string;
  subject?: string;
  body: string;
  instruction?: string;
  signal?: AbortSignal;
}): Promise<{ revisedText: string; source: 'gemini' | 'default' }> {
  return request<{ revisedText: string; source: 'gemini' | 'default' }>(`/api/ai/compose`, {
    method: 'POST',
    body: {
      to: input.to,
      cc: input.cc,
      subject: input.subject,
      body: input.body,
      instruction: input.instruction,
    },
    signal: input.signal,
  });
}

// ---------------------------------------------------------------------------
// Credentials management
// ---------------------------------------------------------------------------

export type CredentialsStatus = {
  imap: boolean;
  smtp: boolean;
  gemini: boolean;
};

export type ImapCredentialsInput = {
  host: string;
  port: number;
  username: string;
  password: string;
  folder?: string;
};

export type SmtpCredentialsInput = {
  host: string;
  port: number;
  username: string;
  password: string;
};

export type GeminiCredentialsInput = {
  api_key: string;
  model?: string;
};

export type SaveCredentialsInput = {
  imap?: ImapCredentialsInput;
  smtp?: SmtpCredentialsInput;
  gemini?: GeminiCredentialsInput;
};

export async function getCredentialsStatus(
  signal?: AbortSignal,
): Promise<CredentialsStatus> {
  return request<CredentialsStatus>('/api/credentials/status', { signal });
}

export async function saveCredentials(
  input: SaveCredentialsInput,
  signal?: AbortSignal,
): Promise<CredentialsStatus> {
  return request<CredentialsStatus>('/api/credentials', {
    method: 'POST',
    body: input,
    signal,
  });
}

export async function deleteCredentials(
  credType?: 'imap' | 'smtp' | 'gemini',
  signal?: AbortSignal,
): Promise<void> {
  const params = credType ? `?cred_type=${credType}` : '';
  await request<void>(`/api/credentials${params}`, {
    method: 'POST',             // Using POST with _method override via DELETE
    signal,
  });
  // Actually use DELETE method:
}

export async function deleteCredentialsRaw(
  credType?: 'imap' | 'smtp' | 'gemini',
  signal?: AbortSignal,
): Promise<void> {
  const apiBase = getApiBaseUrl();
  const params = credType ? `?cred_type=${credType}` : '';
  const url = apiBase ? `${apiBase}/api/credentials${params}` : `/api/credentials${params}`;

  const headers: Record<string, string> = {};
  const authToken = getAuthToken();
  if (authToken) {
    headers['Authorization'] = authToken.startsWith('Bearer ') ? authToken : `Bearer ${authToken}`;
  }

  const res = await fetch(url, { method: 'DELETE', headers, signal });
  if (!res.ok && res.status !== 204) {
    throw new Error(`API ${res.status} ${res.statusText}`);
  }
}

export async function triggerIngest(
  signal?: AbortSignal,
): Promise<{ ingested: number }> {
  return request<{ ingested: number }>('/api/ingest', {
    method: 'POST',
    body: {},
    signal,
  });
}
