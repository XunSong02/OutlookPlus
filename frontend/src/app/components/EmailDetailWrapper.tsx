import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { Loader2 } from 'lucide-react';
import { EmailDetail } from './EmailDetail';
import { useEmails } from '../state/emails';

export function EmailDetailWrapper() {
  const { emailId } = useParams();
  const { emails, markRead, loadEmail } = useEmails();
  const [isLoading, setIsLoading] = useState(false);
  const email = emails.find((e) => e.id === emailId);

  useEffect(() => {
    if (!emailId) return;
    markRead(emailId);
  }, [emailId, markRead]);

  useEffect(() => {
    if (!emailId) return;

    setIsLoading(true);
    loadEmail(emailId)
      .catch((err) => {
        console.error('Failed to load email detail from backend.', err);
      })
      .finally(() => setIsLoading(false));
  }, [emailId, loadEmail]);

  if (!email) {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <div className="text-lg font-medium">Loading email…</div>
          <p className="text-sm">Fetching message details from the server.</p>
        </div>
      );
    }

    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
        <div className="text-lg font-medium">Email not found</div>
        <p className="text-sm">The email you are looking for does not exist or has been deleted.</p>
      </div>
    );
  }

  return (
    <EmailDetail email={email} />
  );
}

export function EmailDetailPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-gray-50/50">
      <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
        <svg
          className="w-12 h-12 text-gray-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
      </div>
      <h3 className="text-xl font-medium text-gray-900 mb-2">Select an email to read</h3>
      <p className="text-gray-500 max-w-sm text-center">
        Choose from the list on the left to view details, AI summaries, and suggested actions.
      </p>
    </div>
  );
}
