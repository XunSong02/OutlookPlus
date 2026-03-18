import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type ComposeDraft = {
  to: string;
  subject: string;
  body: string;
};

type ComposeContextValue = {
  isOpen: boolean;
  draft: ComposeDraft | null;
  openNewMessage: (draft?: Partial<ComposeDraft>) => void;
  close: () => void;
};

const ComposeContext = createContext<ComposeContextValue | null>(null);

export function ComposeProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState<ComposeDraft | null>(null);

  const openNewMessage = useCallback((next?: Partial<ComposeDraft>) => {
    const normalized = next
      ? {
          to: (next.to ?? '').trim(),
          subject: (next.subject ?? '').trim(),
          body: (next.body ?? '').trim(),
        }
      : null;

    setDraft(normalized && (normalized.to || normalized.subject || normalized.body) ? normalized : null);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
    setDraft(null);
  }, []);

  const value = useMemo<ComposeContextValue>(
    () => ({ isOpen, draft, openNewMessage, close }),
    [isOpen, draft, openNewMessage, close]
  );

  return <ComposeContext.Provider value={value}>{children}</ComposeContext.Provider>;
}

export function useCompose() {
  const ctx = useContext(ComposeContext);
  if (!ctx) {
    throw new Error('useCompose must be used within ComposeProvider');
  }
  return ctx;
}
