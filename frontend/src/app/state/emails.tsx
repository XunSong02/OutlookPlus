import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Email, SuggestedAction } from '../types';
import { EmailDto, getEmail, listEmails, patchEmailRead } from '../services/outlookplusApi';

export function normalizeSuggestedActions(
  input: unknown,
  email: { sender: { email: string }; subject: string; folder: Email['folder'] }
) {
  const items = Array.isArray(input) ? input : [];
  const out: SuggestedAction[] = [];

  for (const item of items) {
    if (typeof item === 'string') {
      const text = item.trim();
      if (text) out.push({ kind: 'suggestion', text });
      continue;
    }

    if (item && typeof item === 'object') {
      const kind = (item as any).kind;
      const text = typeof (item as any).text === 'string' ? (item as any).text.trim() : '';

      if (kind === 'reply_draft') {
        const draft = (item as any).draft;
        const to = typeof draft?.to === 'string' ? draft.to.trim() : '';
        const subject = typeof draft?.subject === 'string' ? draft.subject.trim() : '';
        const body = typeof draft?.body === 'string' ? draft.body : '';

        if (text && to && subject && body) {
          out.push({ kind: 'reply_draft', text, draft: { to, subject, body } });
          continue;
        }
      }

      if (kind === 'suggestion' && text) {
        out.push({ kind: 'suggestion', text });
        continue;
      }
    }
  }

  // Return only what Gemini actually produced (up to 3).
  // No fallback padding — the UI shows "AI analyzing..." until results arrive.
  return out.slice(0, 3);
}

export function toEmail(dto: EmailDto): Email {
  const sender = {
    name: dto.sender?.name ?? '',
    email: dto.sender?.email ?? '',
    avatar: dto.sender?.avatar ?? undefined,
  };

  const subject = dto.subject ?? '';
  return {
    id: dto.id,
    sender,
    subject,
    preview: dto.preview ?? '',
    body: dto.body ?? '',
    date: dto.date,
    read: Boolean(dto.read),
    folder: dto.folder,
    labels: Array.isArray(dto.labels) ? dto.labels : [],
    aiAnalysis: {
      category: dto.aiAnalysis?.category ?? 'Work',
      sentiment: dto.aiAnalysis?.sentiment ?? 'neutral',
      summary: dto.aiAnalysis?.summary ?? '',
      suggestedActions: normalizeSuggestedActions(dto.aiAnalysis?.suggestedActions, {
        sender,
        subject,
        folder: dto.folder,
      }),
    },
  };
}

type EmailsContextValue = {
  emails: Email[];
  isLoading: boolean;
  isFetching: boolean;
  setIsFetching: (v: boolean) => void;
  markRead: (emailId: string) => void;
  reload: () => Promise<void>;
  loadEmail: (emailId: string) => Promise<void>;
  updateAiAnalysis: (emailId: string, analysis: Email['aiAnalysis']) => void;
};

const EmailsContext = createContext<EmailsContextValue | null>(null);

export function EmailsProvider({ children }: { children: React.ReactNode }) {
  const [emails, setEmails] = useState<Email[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const loadedEmailIdsRef = useRef<Set<string>>(new Set());

  const reload = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    try {
      const folders: Array<Email['folder']> = ['inbox', 'sent', 'drafts', 'spam', 'trash'];
      const results = await Promise.all(
        folders.map((folder) => listEmails({ folder, limit: 200, signal }))
      );
      const combined = results.flatMap((r) => r.items).map(toEmail);
      setEmails(combined);
    } catch (err) {
      console.error('Failed to load emails from backend.', err);
      setEmails([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);

  const markRead = useCallback((emailId: string) => {
    setEmails((prev) =>
      prev.map((email) => (email.id === emailId ? { ...email, read: true } : email))
    );

    void patchEmailRead({ emailId, read: true }).catch((err) => {
      console.error('Failed to mark email as read in backend.', err);
    });
  }, []);

  const loadEmail = useCallback(async (emailId: string) => {
    if (!emailId) return;
    if (loadedEmailIdsRef.current.has(emailId)) return;

    const detailed = toEmail(await getEmail({ emailId }));
    loadedEmailIdsRef.current.add(emailId);
    setEmails((prev) => {
      const idx = prev.findIndex((e) => e.id === emailId);
      if (idx === -1) {
        return [detailed, ...prev];
      }
      return prev.map((e) => (e.id === emailId ? { ...e, ...detailed, read: e.read } : e));
    });
  }, []);

  const updateAiAnalysis = useCallback((emailId: string, analysis: Email['aiAnalysis']) => {
    setEmails((prev) =>
      prev.map((e) => (e.id === emailId ? { ...e, aiAnalysis: analysis } : e))
    );
  }, []);

  const value = useMemo<EmailsContextValue>(
    () => ({ emails, isLoading, isFetching, setIsFetching, markRead, reload, loadEmail, updateAiAnalysis }),
    [emails, isLoading, isFetching, markRead, reload, loadEmail, updateAiAnalysis]
  );

  return <EmailsContext.Provider value={value}>{children}</EmailsContext.Provider>;
}

export function useEmails() {
  const ctx = useContext(EmailsContext);
  if (!ctx) {
    throw new Error('useEmails must be used within EmailsProvider');
  }
  return ctx;
}
