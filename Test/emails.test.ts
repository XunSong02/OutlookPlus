/**
 * Unit tests for frontend/src/app/state/emails.tsx
 *
 * Follows the test specification at test-specs/emails-state-spec.md exactly.
 * Mocks are used for the API layer (outlookplusApi) and mock data (mockEmails).
 */

import React from 'react';
import { render, act, waitFor, screen } from '@testing-library/react';

/* ------------------------------------------------------------------ */
/*  Mocks – must be declared before any import that touches them      */
/* ------------------------------------------------------------------ */

// Mock the API module
jest.mock('../src/app/services/outlookplusApi', () => ({
  listEmails: jest.fn(),
  getEmail: jest.fn(),
  patchEmailRead: jest.fn(),
}));

// Mock the mock-data module (used as fallback on API failure)
jest.mock('../src/app/data/mockEmails', () => ({
  mockEmails: [
    {
      id: 'mock-1',
      sender: { name: 'Mock', email: 'mock@test.com' },
      subject: 'Mock Email',
      preview: '',
      body: '',
      date: '2025-01-01T00:00:00Z',
      read: false,
      folder: 'inbox' as const,
      labels: [],
      aiAnalysis: {
        category: 'Work' as const,
        sentiment: 'neutral' as const,
        summary: '',
        suggestedActions: [],
      },
    },
  ],
}));

import {
  normalizeSuggestedActions,
  toEmail,
  EmailsProvider,
  useEmails,
} from '../src/app/state/emails';
import * as api from '../src/app/services/outlookplusApi';
import { mockEmails } from '../src/app/data/mockEmails';

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

/** A minimal valid EmailDto-like object for use with listEmails mock. */
function makeEmailDto(overrides: Record<string, unknown> = {}) {
  return {
    id: 'dto-1',
    sender: { name: 'Alice', email: 'alice@test.com' },
    subject: 'Test Subject',
    preview: 'Preview text',
    body: '<p>Body</p>',
    date: '2025-01-01T00:00:00Z',
    read: false,
    folder: 'inbox',
    labels: ['Work'],
    aiAnalysis: {
      category: 'Work',
      sentiment: 'neutral',
      summary: 'A summary',
      suggestedActions: ['Action 1', 'Action 2', 'Action 3'],
    },
    ...overrides,
  };
}

/**
 * Helper component that consumes useEmails() and exposes the context values
 * via data-testid attributes so tests can inspect them.
 */
let capturedCtx: ReturnType<typeof useEmails> | null = null;
function TestConsumer() {
  const ctx = useEmails();
  capturedCtx = ctx;
  return React.createElement('div', { 'data-testid': 'consumer' }, `emails:${ctx.emails.length}`);
}

/* ------------------------------------------------------------------ */
/*  Test suite                                                        */
/* ------------------------------------------------------------------ */

describe('emails.tsx', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    capturedCtx = null;
  });

  /* ============================================================== */
  /*  Test 1 – normalizeSuggestedActions: valid mixed array          */
  /* ============================================================== */
  test('normalize: valid mixed array is parsed and padded to 3', () => {
    const input = [
      'Archive it',
      {
        kind: 'reply_draft',
        text: 'Sounds good',
        draft: { to: 'a@b.com', subject: 'Re: Hi', body: 'Ok' },
      },
    ];
    const email = {
      sender: { email: 'a@b.com' },
      subject: 'Hi',
      folder: 'inbox' as const,
    };

    const result = normalizeSuggestedActions(input, email);

    // Should always return exactly 3 items
    expect(result).toHaveLength(3);

    // First: the string "Archive it" becomes a suggestion
    expect(result[0]).toEqual({ kind: 'suggestion', text: 'Archive it' });

    // Second: the reply_draft object passes through
    expect(result[1]).toEqual({
      kind: 'reply_draft',
      text: 'Sounds good',
      draft: { to: 'a@b.com', subject: 'Re: Hi', body: 'Ok' },
    });

    // Third: padded with fallback suggestion
    expect(result[2]).toEqual({
      kind: 'suggestion',
      text: 'Ignore if no action is required.',
    });
  });

  /* ============================================================== */
  /*  Test 2 – normalizeSuggestedActions: non-array / inbox fallback */
  /* ============================================================== */
  test('normalize: non-array input with inbox folder returns reply_draft fallback first', () => {
    const email = {
      sender: { email: 'a@b.com' },
      subject: 'Hello',
      folder: 'inbox' as const,
    };

    const result = normalizeSuggestedActions(null, email);

    expect(result).toHaveLength(3);

    // First item is the inbox-specific reply_draft fallback
    expect(result[0].kind).toBe('reply_draft');
    if (result[0].kind === 'reply_draft') {
      expect(result[0].draft.to).toBe('a@b.com');
      expect(result[0].draft.subject).toBe('Re: Hello');
      expect(result[0].draft.body).toContain('Thanks for the email');
    }

    // Remaining 2 are generic suggestion fallbacks
    expect(result[1]).toEqual({
      kind: 'suggestion',
      text: 'Ignore if no action is required.',
    });
    expect(result[2]).toEqual({
      kind: 'suggestion',
      text: 'Ignore if no action is required.',
    });
  });

  /* ============================================================== */
  /*  Test 3 – toEmail: maps DTO and applies defaults                */
  /* ============================================================== */
  test('toEmail: maps full DTO and applies defaults for missing fields', () => {
    const dto = {
      id: '1',
      sender: { name: 'Alice', email: 'a@b.com' },
      subject: 'Test',
      preview: 'Prev',
      body: '<p>Hi</p>',
      date: '2025-01-01',
      read: 1,
      folder: 'inbox' as const,
      labels: ['Work'],
      aiAnalysis: {
        category: 'Work' as const,
        sentiment: 'positive' as const,
        summary: 'Sum',
        suggestedActions: ['Do A', 'Do B', 'Do C'],
      },
    };

    const result = toEmail(dto as any);

    // Scalar fields mapped correctly
    expect(result.id).toBe('1');
    expect(result.subject).toBe('Test');
    expect(result.preview).toBe('Prev');
    expect(result.body).toBe('<p>Hi</p>');
    expect(result.date).toBe('2025-01-01');
    expect(result.folder).toBe('inbox');

    // read coerced to boolean
    expect(result.read).toBe(true);

    // labels preserved as array
    expect(result.labels).toEqual(['Work']);

    // sender mapped; avatar defaults to undefined (not present on dto)
    expect(result.sender.name).toBe('Alice');
    expect(result.sender.email).toBe('a@b.com');
    expect(result.sender.avatar).toBeUndefined();

    // aiAnalysis: suggestedActions normalized to exactly 3 items
    expect(result.aiAnalysis.category).toBe('Work');
    expect(result.aiAnalysis.sentiment).toBe('positive');
    expect(result.aiAnalysis.summary).toBe('Sum');
    expect(result.aiAnalysis.suggestedActions).toHaveLength(3);
    // The three string actions become suggestions
    expect(result.aiAnalysis.suggestedActions[0]).toEqual({
      kind: 'suggestion',
      text: 'Do A',
    });
  });

  /* ============================================================== */
  /*  Test 4 – EmailsProvider: renders children and provides context */
  /* ============================================================== */
  test('EmailsProvider: renders children and provides context value', async () => {
    // Mock listEmails so the initial reload() inside the provider succeeds
    (api.listEmails as jest.Mock).mockResolvedValue({ items: [] });

    await act(async () => {
      render(
        React.createElement(EmailsProvider, null, React.createElement(TestConsumer)),
      );
    });

    // The consumer rendered (provider passed children through)
    expect(screen.getByTestId('consumer')).toBeTruthy();

    // The captured context exposes the expected shape
    expect(capturedCtx).not.toBeNull();
    expect(Array.isArray(capturedCtx!.emails)).toBe(true);
    expect(typeof capturedCtx!.isLoading).toBe('boolean');
    expect(typeof capturedCtx!.markRead).toBe('function');
    expect(typeof capturedCtx!.reload).toBe('function');
    expect(typeof capturedCtx!.loadEmail).toBe('function');
  });

  /* ============================================================== */
  /*  Test 5 – reload: success fetches all 5 folders                 */
  /* ============================================================== */
  test('reload: success fetches all 5 folders and combines results', async () => {
    // Each folder returns 2 items → 5 folders × 2 = 10 total
    (api.listEmails as jest.Mock).mockImplementation(({ folder }: { folder: string }) =>
      Promise.resolve({
        items: [
          makeEmailDto({ id: `${folder}-1`, folder }),
          makeEmailDto({ id: `${folder}-2`, folder }),
        ],
      }),
    );

    await act(async () => {
      render(
        React.createElement(EmailsProvider, null, React.createElement(TestConsumer)),
      );
    });

    // listEmails should have been called for each of the 5 folders
    expect(api.listEmails).toHaveBeenCalledTimes(5);
    const calledFolders = (api.listEmails as jest.Mock).mock.calls.map(
      (c: any[]) => c[0].folder,
    );
    expect(calledFolders.sort()).toEqual(
      ['drafts', 'inbox', 'sent', 'spam', 'trash'],
    );

    // State should contain 10 combined emails
    expect(capturedCtx!.emails).toHaveLength(10);
    expect(capturedCtx!.isLoading).toBe(false);
  });

  /* ============================================================== */
  /*  Test 6 – reload: API failure falls back to mock data           */
  /* ============================================================== */
  test('reload: API failure falls back to mock data', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    // Make the API reject so reload enters the catch branch
    (api.listEmails as jest.Mock).mockRejectedValue(new Error('network fail'));

    await act(async () => {
      render(
        React.createElement(EmailsProvider, null, React.createElement(TestConsumer)),
      );
    });

    // State should contain the mock emails from the fallback
    expect(capturedCtx!.emails).toEqual(mockEmails);
    expect(capturedCtx!.isLoading).toBe(false);

    // console.error should have been called with the failure message
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  /* ============================================================== */
  /*  Test 7 – markRead: optimistic update + backend API call        */
  /* ============================================================== */
  test('markRead: updates local state and calls backend API', async () => {
    // Seed the provider with one unread email
    (api.listEmails as jest.Mock).mockResolvedValue({
      items: [makeEmailDto({ id: 'email-1', read: false })],
    });
    (api.patchEmailRead as jest.Mock).mockResolvedValue(undefined);

    await act(async () => {
      render(
        React.createElement(EmailsProvider, null, React.createElement(TestConsumer)),
      );
    });

    // Verify the email starts as unread
    expect(capturedCtx!.emails[0].read).toBe(false);

    // Call markRead
    act(() => {
      capturedCtx!.markRead('email-1');
    });

    // State should now show the email as read (optimistic)
    expect(capturedCtx!.emails.find((e) => e.id === 'email-1')!.read).toBe(true);

    // The backend API should have been called
    expect(api.patchEmailRead).toHaveBeenCalledWith({
      emailId: 'email-1',
      read: true,
    });
  });

  /* ============================================================== */
  /*  Test 8 – loadEmail: fetch, merge, and dedup                    */
  /* ============================================================== */
  test('loadEmail: fetches detail and merges into existing state', async () => {
    // Seed with a stub email that has an empty body
    (api.listEmails as jest.Mock).mockResolvedValue({
      items: [makeEmailDto({ id: 'msg-1', body: '' })],
    });

    // getEmail returns the detailed version with a full body
    (api.getEmail as jest.Mock).mockResolvedValue(
      makeEmailDto({ id: 'msg-1', body: '<p>Full body content</p>' }),
    );

    await act(async () => {
      render(
        React.createElement(EmailsProvider, null, React.createElement(TestConsumer)),
      );
    });

    // Before loadEmail, body should be empty (from list stub)
    expect(capturedCtx!.emails[0].body).toBe('');

    // Call loadEmail for the first time
    await act(async () => {
      await capturedCtx!.loadEmail('msg-1');
    });

    // getEmail should have been called once
    expect(api.getEmail).toHaveBeenCalledTimes(1);
    expect(api.getEmail).toHaveBeenCalledWith({ emailId: 'msg-1' });

    // State email should now have the full body merged in
    expect(capturedCtx!.emails.find((e) => e.id === 'msg-1')!.body).toBe(
      '<p>Full body content</p>',
    );

    // Call loadEmail again with the same id (dedup guard)
    await act(async () => {
      await capturedCtx!.loadEmail('msg-1');
    });

    // getEmail should NOT have been called a second time
    expect(api.getEmail).toHaveBeenCalledTimes(1);
  });

  /* ============================================================== */
  /*  Test 9 – useEmails: throws outside EmailsProvider              */
  /* ============================================================== */
  test('useEmails: throws when used outside EmailsProvider', () => {
    // Suppress React error boundary console noise during the expected throw
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    function BadConsumer() {
      useEmails(); // should throw
      return null;
    }

    expect(() => {
      render(React.createElement(BadConsumer));
    }).toThrow('useEmails must be used within EmailsProvider');

    consoleSpy.mockRestore();
  });
});
