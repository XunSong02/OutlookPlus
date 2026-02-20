import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Email } from '../types';

interface EmailThumbnailProps {
  email: Email;
  isActive?: boolean;
  onClick?: () => void;
  className?: string;
}

const sentimentColor = {
  positive: 'bg-green-500',
  neutral: 'bg-gray-400',
  negative: 'bg-red-500',
};

const categoryColor = {
  Work: 'bg-purple-100 text-purple-800',
  Personal: 'bg-green-100 text-green-800',
  Finance: 'bg-yellow-100 text-yellow-800',
  Social: 'bg-blue-100 text-blue-800',
  Promotions: 'bg-pink-100 text-pink-800',
  Urgent: 'bg-red-100 text-red-800',
};

export function EmailThumbnail({ email, isActive, onClick, className }: EmailThumbnailProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={twMerge(
        "w-full text-left cursor-pointer p-4 border-b border-gray-100 transition-colors hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
        isActive ? "bg-blue-50 border-l-4 border-l-blue-500" : "bg-white border-l-4 border-l-transparent",
        className
      )}
      aria-current={isActive ? 'page' : undefined}
      aria-label={`Open email: ${email.subject} from ${email.sender.name}`}
    >
      <div className="flex justify-between items-start mb-1">
        <div className="flex items-center gap-2">
            {email.sender.avatar ? (
                <img src={email.sender.avatar} alt={email.sender.name} className="w-6 h-6 rounded-full object-cover" />
            ) : (
                <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600">
                    {email.sender.name.charAt(0)}
                </div>
            )}
            <span className={clsx("text-sm font-medium truncate max-w-[120px]", isActive ? "text-blue-900" : "text-gray-900")}>
                {email.sender.name}
            </span>
        </div>
        <span className="text-xs text-gray-500 whitespace-nowrap ml-2">
          {formatDistanceToNow(new Date(email.date), { addSuffix: true }).replace('about ', '')}
        </span>
      </div>

      <div className={clsx("text-sm font-semibold mb-1 truncate", !email.read && "text-black")}>
        {email.subject}
      </div>

      <div className="text-xs text-gray-500 line-clamp-2 mb-3 leading-relaxed">
        {email.aiAnalysis.summary}
      </div>

      <div className="flex flex-wrap items-center gap-2 mt-2">
        {/* Category Badge */}
        <span className={clsx(
            "text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wide border border-transparent",
            categoryColor[email.aiAnalysis.category] || "bg-gray-100 text-gray-600"
        )}>
            {email.aiAnalysis.category}
        </span>

        {/* User Labels */}
        {email.labels.map((label) => (
             <span key={label} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200">
                {label}
             </span>
        ))}
        
        {/* Sentiment Indicator */}
        <div className="flex items-center gap-1 ml-auto" title={`Sentiment: ${email.aiAnalysis.sentiment}`}>
            <div className={clsx("w-2 h-2 rounded-full", sentimentColor[email.aiAnalysis.sentiment])} />
        </div>
      </div>
    </button>
  );
}
