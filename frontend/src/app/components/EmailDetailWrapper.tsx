import React, { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import { EmailDetail } from './EmailDetail';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useEmails } from '../state/emails';

export function EmailDetailWrapper() {
  const { folder, emailId } = useParams();
  const navigate = useNavigate();
  const isMdUp = useMediaQuery('(min-width: 768px)');
  const { emails, markRead } = useEmails();
  const email = emails.find((e) => e.id === emailId);

  useEffect(() => {
    if (!emailId) return;
    markRead(emailId);
  }, [emailId, markRead]);

  if (!email) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
        <div className="text-lg font-medium">Email not found</div>
        <p className="text-sm">The email you are looking for does not exist or has been deleted.</p>
      </div>
    );
  }

  return (
    <EmailDetail
      email={email}
      onClose={
        isMdUp
          ? undefined
          : () => {
              navigate(`/${folder ?? 'inbox'}`);
            }
      }
    />
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
