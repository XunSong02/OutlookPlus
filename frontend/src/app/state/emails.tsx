import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { Email } from '../types';
import { mockEmails } from '../data/mockEmails';

type EmailsContextValue = {
  emails: Email[];
  markRead: (emailId: string) => void;
};

const EmailsContext = createContext<EmailsContextValue | null>(null);

export function EmailsProvider({ children }: { children: React.ReactNode }) {
  const [emails, setEmails] = useState<Email[]>(mockEmails);

  const markRead = useCallback((emailId: string) => {
    setEmails((prev) =>
      prev.map((email) => (email.id === emailId ? { ...email, read: true } : email))
    );
  }, []);

  const value = useMemo<EmailsContextValue>(() => ({ emails, markRead }), [emails, markRead]);

  return <EmailsContext.Provider value={value}>{children}</EmailsContext.Provider>;
}

export function useEmails() {
  const ctx = useContext(EmailsContext);
  if (!ctx) {
    throw new Error('useEmails must be used within EmailsProvider');
  }
  return ctx;
}
