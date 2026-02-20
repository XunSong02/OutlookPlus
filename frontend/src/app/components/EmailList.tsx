import React, { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router';
import { Search, Filter, ChevronDown } from 'lucide-react';
import { EmailThumbnail } from './EmailThumbnail';
import { useEmails } from '../state/emails';

interface EmailListProps {
  folder: string;
}

export function EmailList({ folder }: EmailListProps) {
  const navigate = useNavigate();
  const { emailId } = useParams();
  const { emails } = useEmails();
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all');

  // Use the prop 'folder' directly. It comes from the parent which gets it from URL.
  const currentFolder = folder || 'inbox';

  const filteredEmails = useMemo(() => {
    return emails
      .filter((email) => {
        if (['inbox', 'sent', 'drafts', 'trash', 'spam'].includes(currentFolder)) {
            return email.folder === currentFolder;
        }
        // Label/category view: an email can show up in multiple views.
        // Match either explicit labels OR the AI category (Work/Personal/Finance/Urgent).
        return email.labels.includes(currentFolder) || email.aiAnalysis.category === currentFolder;
      })
      .filter((email) => {
        if (filter === 'unread') return !email.read;
        if (filter === 'read') return email.read;
        return true;
      })
      .filter((email) => {
        if (!searchQuery) return true;
        const query = searchQuery.toLowerCase();
        return (
          email.subject.toLowerCase().includes(query) ||
          email.sender.name.toLowerCase().includes(query) ||
          email.preview.toLowerCase().includes(query)
        );
      })
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }, [currentFolder, emails, filter, searchQuery]);

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Search Header */}
      <div className="p-4 border-b border-gray-100 space-y-3 sticky top-0 bg-white z-10">
        <h2 className="text-xl font-bold text-gray-900 capitalize px-1">{currentFolder}</h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <label htmlFor="email-search" className="sr-only">
            Search emails
          </label>
          <input
            id="email-search"
            type="text"
            placeholder="Search emails..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all placeholder:text-gray-400"
          />
        </div>
        <div className="flex items-center justify-between text-xs text-gray-500 px-1">
            <span>{filteredEmails.length} messages</span>
            <button 
                type="button"
                onClick={() => setFilter(filter === 'all' ? 'unread' : 'all')}
                className="flex items-center gap-1 hover:text-gray-800 transition-colors"
                aria-pressed={filter !== 'all'}
            >
                <Filter size={12} />
                <span>{filter === 'all' ? 'All' : 'Unread'}</span>
                <ChevronDown size={12} />
            </button>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {filteredEmails.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            No emails found in {currentFolder}.
          </div>
        ) : (
          filteredEmails.map((email) => (
            <EmailThumbnail
              key={email.id}
              email={email}
              isActive={emailId === email.id}
              onClick={() => navigate(`/${currentFolder}/${email.id}`)}
            />
          ))
        )}
      </div>
    </div>
  );
}
