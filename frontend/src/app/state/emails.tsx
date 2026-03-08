import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Email } from '../types';
import { mockEmails } from '../data/mockEmails';
import { getEmail, listEmails, patchEmailRead } from '../services/outlookplusApi';

type EmailsContextValue = {
  emails: Email[];
  markRead: (emailId: string) => void;
  reload: () => Promise<void>;
  loadEmail: (emailId: string) => Promise<void>;
};

const EmailsContext = createContext<EmailsContextValue | null>(null);

export function EmailsProvider({ children }: { children: React.ReactNode }) {
  const [emails, setEmails] = useState<Email[]>([]);
  const loadedEmailIdsRef = useRef<Set<string>>(new Set());

  const reload = useCallback(async (signal?: AbortSignal) => {
    try {
      const folders: Array<Email['folder']> = ['inbox', 'sent', 'drafts', 'spam', 'trash'];
      const results = await Promise.all(
        folders.map((folder) => listEmails({ folder, limit: 200, signal }))
      );
      const combined = results.flatMap((r) => r.items) as Email[];
      setEmails(combined);
    } catch (err) {
      console.error('Failed to load emails from backend; falling back to mock data.', err);
      setEmails(mockEmails);
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

    const detailed = (await getEmail({ emailId })) as unknown as Email;
    loadedEmailIdsRef.current.add(emailId);
    setEmails((prev) => {
      const idx = prev.findIndex((e) => e.id === emailId);
      if (idx === -1) {
        return [detailed, ...prev];
      }
      return prev.map((e) => (e.id === emailId ? { ...e, ...detailed } : e));
    });
  }, []);

  const value = useMemo<EmailsContextValue>(
    () => ({ emails, markRead, reload, loadEmail }),
    [emails, markRead, reload, loadEmail]
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
