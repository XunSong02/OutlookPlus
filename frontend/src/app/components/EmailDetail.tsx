import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import {
  Sparkles,
  Bot,
  Send,
  ChevronRight,
  Reply,
  Lightbulb,
  Loader2
} from 'lucide-react';
import { clsx } from 'clsx';
import { Email } from '../types';
import { toast } from 'sonner';
import { analyzeEmail, runAiRequest } from '../services/outlookplusApi';
import { normalizeSuggestedActions, useEmails } from '../state/emails';
import { useCompose } from '../state/compose';

/** Turn markdown links [text](url) and bare URLs into clickable <a> tags. */
function linkify(text: string): React.ReactNode[] {
  // Match markdown links first, then bare URLs
  const LINK_RE = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|https?:\/\/[^\s<>)]+/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = LINK_RE.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[1] && match[2]) {
      // Markdown link: [text](url)
      parts.push(
        <a key={match.index} href={match[2]} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">{match[1]}</a>
      );
    } else {
      // Bare URL
      const url = match[0];
      parts.push(
        <a key={match.index} href={url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline break-all">{url}</a>
      );
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

interface EmailDetailProps {
  email: Email;
}

export function EmailDetail({ email }: EmailDetailProps) {
  const [customAction, setCustomAction] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  // Check if global state already has real AI analysis (from a previous open).
  const cachedAnalysis = email.aiAnalysis.summary || email.aiAnalysis.suggestedActions.length > 0;
  const [aiAnalysis, setAiAnalysis] = useState(email.aiAnalysis);
  const [aiLoading, setAiLoading] = useState(!cachedAnalysis);
  const [aiFailed, setAiFailed] = useState(false);

    const { openNewMessage } = useCompose();
    const { updateAiAnalysis } = useEmails();

    // Trigger AI analysis — skip if we already have cached results.
    useEffect(() => {
      const hasCached = email.aiAnalysis.summary || email.aiAnalysis.suggestedActions.length > 0;
      if (hasCached) {
        setAiAnalysis(email.aiAnalysis);
        setAiLoading(false);
        setAiFailed(false);
        return;
      }

      setAiLoading(true);
      setAiFailed(false);
      setAiResponse(null);
      let cancelled = false;
      const controller = new AbortController();
      analyzeEmail({ emailId: email.id, signal: controller.signal })
        .then((result) => {
          if (cancelled) return;
          const analysis: Email['aiAnalysis'] = {
            category: (result.category as Email['aiAnalysis']['category']) || 'Work',
            sentiment: (result.sentiment as Email['aiAnalysis']['sentiment']) || 'neutral',
            summary: String(result.summary ?? ''),
            suggestedActions: normalizeSuggestedActions(result.suggestedActions, {
              sender: email.sender,
              subject: email.subject,
              folder: email.folder,
            }),
          };
          setAiAnalysis(analysis);
          updateAiAnalysis(email.id, analysis);
        })
        .catch(() => { if (!cancelled) setAiFailed(true); })
        .finally(() => { if (!cancelled) setAiLoading(false); });
      return () => { cancelled = true; controller.abort(); };
    }, [email.id, email.aiAnalysis, updateAiAnalysis]);

    const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customAction.trim()) return;

    setIsProcessing(true);
        try {
            const result = await runAiRequest({ emailId: email.id, prompt: customAction });
            setAiResponse(result.responseText);
            setCustomAction('');
        } catch (err) {
            console.error('Failed to run AI request via backend.', err);
            toast.error('Failed to run AI request');
        } finally {
            setIsProcessing(false);
        }
  };

  // Single source of truth: show spinner while loading OR if AI returned empty.
  const aiPending = aiLoading || (!aiAnalysis.summary && aiAnalysis.suggestedActions.length === 0);

  return (
    <div className="h-full flex flex-col bg-white">
            <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
        {/* Main Email Content */}
                <div className="flex-1 overflow-y-auto p-4 sm:p-8 scroll-smooth">
          <div className="max-w-3xl mx-auto">
            {/* Header */}
            <div className="flex justify-between items-start mb-6">
                <h1 className="text-2xl font-bold text-gray-900 leading-tight">{email.subject}</h1>
                <div className="flex items-center gap-2">
                    {aiPending ? (
                      <span className="text-sm text-gray-400 bg-gray-100 px-2 py-1 rounded-md animate-pulse">...</span>
                    ) : (
                      <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-md">
                        {aiAnalysis.category}
                      </span>
                    )}
                </div>
            </div>

            {/* Sender Info */}
            <div className="flex items-center justify-between mb-8 pb-6 border-b border-gray-100">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center text-xl font-bold shadow-sm">
                        {email.sender.name.charAt(0)}
                    </div>
                    <div>
                        <div className="font-semibold text-gray-900 text-lg">{email.sender.name}</div>
                        <div className="text-gray-500 text-sm">{email.sender.email}</div>
                    </div>
                </div>
                <div className="text-gray-400 text-sm font-medium">
                    {format(new Date(email.date), 'MMM d, yyyy, h:mm a')}
                </div>
            </div>

            {/* Body */}
            <div 
                className="prose prose-blue max-w-none text-gray-800 leading-relaxed font-serif text-lg"
                dangerouslySetInnerHTML={{ __html: email.body }}
            />
            
            {/* Attachments Placeholder */}
            {/* <div className="mt-8 pt-6 border-t border-gray-100">
                <h4 className="text-sm font-semibold text-gray-500 mb-3 uppercase tracking-wide">Attachments</h4>
                <div className="flex gap-4">
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center gap-3 cursor-pointer hover:bg-blue-50 hover:border-blue-200 transition-colors">
                        <div className="bg-red-100 text-red-600 p-2 rounded-md">
                             <File size={20} />
                        </div>
                        <div>
                            <div className="text-sm font-medium text-gray-900">Q2_Roadmap.pdf</div>
                            <div className="text-xs text-gray-500">2.4 MB</div>
                        </div>
                    </div>
                </div>
            </div> */}
          </div>
        </div>

        {/* AI Sidebar */}
        <aside className="w-full lg:w-80 border-t lg:border-t-0 lg:border-l border-gray-200 bg-gray-50 overflow-y-auto flex flex-col shadow-[inset_4px_0_12px_-4px_rgba(0,0,0,0.05)]" aria-label="AI assistant">
            <div className="p-6 sticky top-0 bg-gray-50/95 backdrop-blur z-10 border-b border-gray-200">
                <div className="flex items-center gap-2 text-indigo-600 font-semibold mb-1">
                    {aiPending ? <Loader2 size={18} className="animate-spin" aria-hidden="true" /> : <Sparkles size={18} aria-hidden="true" />}
                    <span>AI Assistant</span>
                </div>
                <p className="text-xs text-gray-500">{aiPending ? 'Analyzing email...' : 'Powered by Agent v2.0'}</p>
            </div>
            
            <div className="p-6 space-y-8">
                {aiPending ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400 space-y-3">
                    {aiFailed ? (
                      <span className="text-sm text-gray-400">AI analysis unavailable</span>
                    ) : (
                      <>
                        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
                        <span className="text-sm font-medium">AI is analyzing this email...</span>
                      </>
                    )}
                </div>
                ) : (<>
                {/* Summary Section */}
                <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Summary</h3>
                    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 text-sm text-gray-700 leading-relaxed">
                        {linkify(aiAnalysis.summary)}
                    </div>
                </div>

                {/* Sentiment Analysis */}
                <div>
                     <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Sentiment</h3>
                     <div className="flex items-center gap-3 bg-white p-3 rounded-xl border border-gray-100 shadow-sm">
                        <div className={clsx("w-3 h-3 rounded-full", {
                             'bg-green-500': aiAnalysis.sentiment === 'positive',
                             'bg-gray-400': aiAnalysis.sentiment === 'neutral',
                             'bg-red-500': aiAnalysis.sentiment === 'negative',
                        })} />
                        <span className="text-sm font-medium capitalize text-gray-700">{aiAnalysis.sentiment}</span>
                     </div>
                </div>

                {/* Suggested Actions */}
                <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Suggested Actions</h3>
                    <div className="space-y-2">
                                                {aiAnalysis.suggestedActions.map((action, idx) => {
                                                    if (action.kind === 'reply_draft') {
                                                        return (
                                                            <button
                                                                key={idx}
                                                                onClick={() => openNewMessage(action.draft)}
                                                                disabled={isProcessing}
                                                                className="w-full text-left p-3 bg-white hover:bg-indigo-50 border border-gray-200 hover:border-indigo-200 rounded-lg text-sm text-gray-700 transition-all flex flex-col gap-1.5 group shadow-sm"
                                                            >
                                                                <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600">
                                                                    <Reply size={14} />
                                                                    <span>Suggested Reply</span>
                                                                </div>
                                                                <div className="flex items-center justify-between">
                                                                    <span className="line-clamp-2">{action.text}</span>
                                                                    <ChevronRight
                                                                        size={14}
                                                                        className="opacity-0 group-hover:opacity-100 text-indigo-400 transition-opacity flex-shrink-0 ml-2"
                                                                        aria-hidden="true"
                                                                    />
                                                                </div>
                                                            </button>
                                                        );
                                                    }

                                                    return (
                                                        <div
                                                            key={idx}
                                                            className="w-full text-left p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 flex flex-col gap-1.5 shadow-sm"
                                                            aria-label="Suggestion"
                                                        >
                                                            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-600">
                                                                <Lightbulb size={14} />
                                                                <span>Suggested Action</span>
                                                            </div>
                                                            <span>{action.text}</span>
                                                        </div>
                                                    );
                                                })}
                    </div>
                </div>
                </>)}

                {/* Custom Action */}
                <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Custom Request</h3>
                    <div className="bg-white p-1 rounded-xl border border-gray-200 shadow-sm focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent transition-all">
                        <form onSubmit={handleCustomSubmit} className="relative">
                            <input
                                type="text"
                                value={customAction}
                                onChange={(e) => setCustomAction(e.target.value)}
                                placeholder="Ask AI to draft, summarize..."
                                aria-label="Ask the AI assistant"
                                className="w-full text-sm p-3 pr-10 outline-none bg-transparent placeholder:text-gray-400"
                                disabled={isProcessing}
                            />
                            <button 
                                type="submit" 
                                disabled={!customAction.trim() || isProcessing}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                aria-label="Send AI request"
                            >
                                {isProcessing ? (
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                ) : (
                                    <Send size={14} aria-hidden="true" />
                                )}
                            </button>
                        </form>
                    </div>
                    {aiResponse && (
                        <div className="mt-4 bg-indigo-50 border border-indigo-100 p-3 rounded-lg text-sm text-indigo-800 animate-in fade-in slide-in-from-top-2 duration-300">
                             <div className="flex items-center gap-2 font-semibold mb-1">
                                <Bot size={14} aria-hidden="true" />
                                <span>Agent</span>
                             </div>
                             {linkify(aiResponse)}
                        </div>
                    )}
                </div>
            </div>
        </aside>
      </div>
    </div>
  );
}
