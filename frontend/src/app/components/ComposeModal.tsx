import React, { useCallback, useEffect, useState } from 'react';
import { X, Paperclip, Send, Mic, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { sendEmail, suggestCompose } from '../services/outlookplusApi';
import { useEmails } from '../state/emails';

interface ComposeModalProps {
  isOpen: boolean;
  onClose: () => void;
  draft?: {
    to?: string | null;
    subject?: string | null;
    body?: string | null;
  } | null;
}

export function ComposeModal({ isOpen, onClose, draft }: ComposeModalProps) {
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isAssisting, setIsAssisting] = useState(false);
  const { reload } = useEmails();

  const resetForm = useCallback(() => {
    setTo('');
    setSubject('');
    setBody('');
    setIsSending(false);
    setIsAssisting(false);
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const nextTo = (draft?.to ?? '').trim();
    const nextSubject = (draft?.subject ?? '').trim();
    const nextBody = (draft?.body ?? '').trim();

    // Treat opens without a draft as a fresh "New Message".
    if (!nextTo && !nextSubject && !nextBody) {
      resetForm();
      return;
    }

    setTo(nextTo);
    setSubject(nextSubject);
    setBody(nextBody);
    setIsSending(false);
    setIsAssisting(false);
  }, [isOpen, draft, resetForm]);

  useEffect(() => {
    if (!isOpen) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        resetForm();
        onClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose, resetForm]);

  if (!isOpen) return null;

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSending) return;
    if (!to || !subject || !body) {
      toast.error('Please fill in all fields');
      return;
    }

    setIsSending(true);
    try {
      await sendEmail({ to, subject, body });
      await reload();
      toast.success('Email sent successfully!');
      resetForm();
      onClose();
    } catch (err) {
      console.error('Failed to send email via backend.', err);
      toast.error('Failed to send email');
    } finally {
      setIsSending(false);
    }
  };

  const handleDiscard = () => {
    resetForm();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end sm:items-center sm:justify-center p-4 bg-black/50 backdrop-blur-sm transition-opacity">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="compose-title"
        className="bg-white w-full max-w-3xl rounded-xl shadow-2xl flex flex-col h-[85vh] sm:h-[85vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200"
      >
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50/50">
          <h2 id="compose-title" className="font-semibold text-gray-800">New Message</h2>
          <button 
            type="button"
            onClick={handleDiscard}
            className="p-1 rounded-full hover:bg-gray-200 text-gray-500 transition-colors"
            aria-label="Close compose window"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSend} className="flex-1 flex flex-col overflow-hidden">
          <div className="px-4 py-2 border-b border-gray-100">
            <label htmlFor="compose-to" className="sr-only">To</label>
            <input
              id="compose-to"
              type="text"
              placeholder="To"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="w-full py-1 text-sm outline-none placeholder:text-gray-400"
              autoFocus
            />
          </div>
          
          <div className="px-4 py-2 border-b border-gray-100">
            <label htmlFor="compose-subject" className="sr-only">Subject</label>
            <input
              id="compose-subject"
              type="text"
              placeholder="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full py-1 text-sm font-medium outline-none placeholder:text-gray-400"
            />
          </div>

          <div className="flex-1 p-4 overflow-y-auto relative">
            <label htmlFor="compose-body" className="sr-only">Message body</label>
            <textarea
              id="compose-body"
              placeholder="Write your message..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full h-full resize-none outline-none text-sm leading-relaxed placeholder:text-gray-400"
            />
            
            {/* AI Assistant Button */}
            <button
                type="button"
                disabled={isAssisting}
                className="absolute bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-600 rounded-full text-xs font-medium hover:bg-blue-100 transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
                onClick={async () => {
                  if (isAssisting) return;
                  const draft = body.trim();
                  if (!draft) {
                    toast.error('Please write something first');
                    return;
                  }

                  setIsAssisting(true);
                  try {
                    const res = await suggestCompose({
                      to: to.trim() || undefined,
                      subject: subject.trim() || undefined,
                      body: draft,
                    });

                    if (res.revisedText && res.revisedText.trim()) {
                      setBody(res.revisedText);
                    }

                    if (res.source === 'gemini') {
                      toast.info('AI suggestion applied!');
                    } else {
                      toast.info('AI not configured; set GEMINI_API_KEY');
                    }
                  } catch (err) {
                    console.error('AI assist failed.', err);
                    toast.error('AI assist failed');
                  } finally {
                    setIsAssisting(false);
                  }
                }}
              aria-label="Add an AI writing suggestion"
            >
              <Sparkles size={14} aria-hidden="true" />
                <span>{isAssisting ? 'Working...' : 'AI Assist'}</span>
            </button>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-100 flex items-center justify-between bg-gray-50/30">
            <div className="flex items-center gap-2">
              <button type="button" className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors" aria-label="Attach a file">
                <Paperclip size={18} aria-hidden="true" />
              </button>
              <button type="button" className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors" aria-label="Record audio">
                <Mic size={18} aria-hidden="true" />
              </button>
            </div>

            <div className="flex items-center gap-3">
              <button 
                type="button" 
                onClick={handleDiscard}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Discard
              </button>
              <button 
                type="submit" 
                disabled={isSending}
                className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg shadow-sm transition-all disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isSending ? (
                  <>Sending...</>
                ) : (
                  <>
                    <span>Send</span>
                    <Send size={16} aria-hidden="true" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
