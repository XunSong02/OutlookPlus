import React, { useState } from 'react';
import { format } from 'date-fns';
import { 
    ArrowLeft,
  Reply, 
  ReplyAll, 
  Forward, 
  Archive, 
  Trash, 
  MoreHorizontal, 
  Star, 
  Sparkles, 
  Bot, 
  Send,
  ChevronRight
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Email } from '../types';
import { toast } from 'sonner';
import { mockExecuteEmailAction, mockRunAiRequest } from '../services/mockBackend';

interface EmailDetailProps {
  email: Email;
  onClose?: () => void;
}

export function EmailDetail({ email, onClose }: EmailDetailProps) {
  const [customAction, setCustomAction] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [aiResponse, setAiResponse] = useState<string | null>(null);

    const handleActionClick = async (action: string) => {
        setIsProcessing(true);
        try {
            await mockExecuteEmailAction({ emailId: email.id, action });
            toast.success(`Action executed: ${action}`);
        } finally {
            setIsProcessing(false);
        }
    };

    const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customAction.trim()) return;

    setIsProcessing(true);
        try {
            const result = await mockRunAiRequest({ emailId: email.id, prompt: customAction });
            setAiResponse(result.responseText);
            setCustomAction('');
        } finally {
            setIsProcessing(false);
        }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white sticky top-0 z-10">
        <div className="flex items-center gap-2">
                        {onClose && (
                            <button
                                type="button"
                                onClick={onClose}
                                className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                                aria-label="Back to message list"
                                title="Back"
                            >
                                <ArrowLeft size={18} aria-hidden="true" />
                            </button>
                        )}
                        <button
                            type="button"
                            className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            aria-label="Reply"
                            title="Reply"
                        >
                                <Reply size={18} aria-hidden="true" />
                        </button>
                        <button
                            type="button"
                            className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            aria-label="Reply all"
                            title="Reply All"
                        >
                                <ReplyAll size={18} aria-hidden="true" />
                        </button>
                        <button
                            type="button"
                            className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            aria-label="Forward"
                            title="Forward"
                        >
                                <Forward size={18} aria-hidden="true" />
                        </button>
        </div>
        <div className="flex items-center gap-2">
                         <button
                             type="button"
                             className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                             aria-label="Archive"
                             title="Archive"
                         >
                                <Archive size={18} aria-hidden="true" />
                        </button>
                        <button
                            type="button"
                            className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                            aria-label="Delete"
                            title="Delete"
                        >
                                <Trash size={18} aria-hidden="true" />
                        </button>
                         <button
                             type="button"
                             className="p-2 hover:bg-gray-100 rounded-full text-gray-500 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                             aria-label="More actions"
                             title="More"
                         >
                                <MoreHorizontal size={18} aria-hidden="true" />
                        </button>
        </div>
      </div>

            <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
        {/* Main Email Content */}
                <div className="flex-1 overflow-y-auto p-4 sm:p-8 scroll-smooth">
          <div className="max-w-3xl mx-auto">
            {/* Header */}
            <div className="flex justify-between items-start mb-6">
                <h1 className="text-2xl font-bold text-gray-900 leading-tight">{email.subject}</h1>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-md">
                        {email.labels.join(', ')}
                    </span>
                    <button
                      type="button"
                      className="text-gray-400 hover:text-yellow-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                      aria-label="Star message"
                      title="Star"
                    >
                        <Star size={20} aria-hidden="true" />
                    </button>
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
                    <Sparkles size={18} aria-hidden="true" />
                    <span>AI Assistant</span>
                </div>
                <p className="text-xs text-gray-500">Powered by Agent v2.0</p>
            </div>
            
            <div className="p-6 space-y-8">
                {/* Summary Section */}
                <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Summary</h3>
                    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 text-sm text-gray-700 leading-relaxed">
                        {email.aiAnalysis.summary}
                    </div>
                </div>

                {/* Sentiment Analysis */}
                <div>
                     <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Sentiment</h3>
                     <div className="flex items-center gap-3 bg-white p-3 rounded-xl border border-gray-100 shadow-sm">
                        <div className={clsx("w-3 h-3 rounded-full", {
                             'bg-green-500': email.aiAnalysis.sentiment === 'positive',
                             'bg-gray-400': email.aiAnalysis.sentiment === 'neutral',
                             'bg-red-500': email.aiAnalysis.sentiment === 'negative',
                        })} />
                        <span className="text-sm font-medium capitalize text-gray-700">{email.aiAnalysis.sentiment}</span>
                     </div>
                </div>

                {/* Suggested Actions */}
                <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Suggested Actions</h3>
                    <div className="space-y-2">
                        {email.aiAnalysis.suggestedActions.map((action, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleActionClick(action)}
                                disabled={isProcessing}
                                className="w-full text-left p-3 bg-white hover:bg-indigo-50 border border-gray-200 hover:border-indigo-200 rounded-lg text-sm text-gray-700 transition-all flex items-center justify-between group shadow-sm"
                            >
                                <span>{action}</span>
                                <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 text-indigo-400 transition-opacity" aria-hidden="true" />
                            </button>
                        ))}
                    </div>
                </div>

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
                             {aiResponse}
                        </div>
                    )}
                </div>
            </div>
        </aside>
      </div>
    </div>
  );
}
