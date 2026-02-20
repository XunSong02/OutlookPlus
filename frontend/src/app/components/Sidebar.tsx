import React from 'react';
import { NavLink } from 'react-router';
import { 
  Inbox, 
  Send, 
  File, 
  Trash2, 
  AlertOctagon, 
  Settings, 
  Plus, 
  BrainCircuit
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useEmails } from '../state/emails';

interface SidebarProps {
  className?: string;
  onComposeClick?: () => void;
}

const navItems = [
  { icon: Inbox, label: 'Inbox', path: '/inbox', folder: 'inbox' },
  { icon: Send, label: 'Sent', path: '/sent', folder: 'sent' },
  { icon: File, label: 'Drafts', path: '/drafts', folder: 'drafts' },
  { icon: AlertOctagon, label: 'Spam', path: '/spam', folder: 'spam' },
  { icon: Trash2, label: 'Trash', path: '/trash', folder: 'trash' },
] as const;


export function Sidebar({ className, onComposeClick }: SidebarProps) {
  const { emails } = useEmails();

  const getUnreadCount = (folder: string) => {
    return emails.filter((e) => e.folder === folder && !e.read).length;
  };

  return (
    <div className={twMerge("flex flex-col h-full bg-gray-50 border-r border-gray-200 w-full items-center py-4", className)}>
      {/* Header */}
      <div className="mb-6 flex flex-col items-center gap-1 shrink-0">
        <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-sm transition-transform hover:scale-105">
          <BrainCircuit size={24} aria-hidden="true" />
        </div>
      </div>

      {/* Compose Button */}
      <div className="mb-6 px-2 w-full flex justify-center shrink-0">
        <button 
          type="button"
          onClick={onComposeClick}
          className="w-12 h-12 bg-white text-blue-600 border border-blue-100 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 rounded-2xl flex items-center justify-center transition-all shadow-sm hover:shadow group relative"
          title="New Message"
          aria-label="Compose new message"
        >
          <Plus size={24} strokeWidth={2.5} aria-hidden="true" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 w-full px-2 space-y-2 overflow-y-auto flex flex-col items-center scrollbar-hide" aria-label="Mail folders">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              clsx(
                "relative flex flex-col items-center justify-center w-full py-3 rounded-xl transition-all group shrink-0",
                isActive
                  ? "bg-white text-blue-600 shadow-sm"
                  : "text-gray-500 hover:bg-gray-200/50 hover:text-gray-900"
              )
            }
          >
            <div className="relative">
              <item.icon size={22} strokeWidth={2} aria-hidden="true" />
              {(() => {
                const unreadCount = getUnreadCount(item.folder);
                return (
                <span className={clsx(
                  "absolute -top-2 -right-2.5 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center border-2 border-gray-50 group-hover:border-gray-100 z-10",
                  unreadCount > 0 ? "bg-red-500" : "bg-gray-400"
                )}>
                  {unreadCount}
                </span>
                );
              })()}
            </div>
            <span className="text-[10px] font-medium mt-1 text-center leading-tight">{item.label}</span>
          </NavLink>
        ))}

        <div className="w-10 h-px bg-gray-200 my-2 shrink-0" />

        {['Work', 'Personal', 'Finance', 'Urgent'].map((label) => (
            <NavLink 
                key={label} 
                to={`/${label}`}
                className={({ isActive }) =>
                  clsx(
                    "flex flex-col items-center justify-center w-full py-2 rounded-xl transition-colors group shrink-0",
                     isActive
                      ? "bg-gray-100"
                      : "hover:bg-gray-100"
                  )
                }
                title={label}
            >
                <span aria-hidden="true" className={clsx("w-3 h-3 rounded-full border-2 border-white shadow-sm mb-1", {
                    'bg-purple-500': label === 'Work',
                    'bg-green-500': label === 'Personal',
                    'bg-yellow-500': label === 'Finance',
                    'bg-red-500': label === 'Urgent',
                })}></span>
                <span className="text-[9px] text-gray-500 font-medium truncate max-w-full px-1">{label}</span>
            </NavLink>
        ))}
      </nav>

      {/* User Footer */}
      <div className="mt-auto pt-4 pb-2 w-full flex flex-col items-center gap-4 border-t border-gray-200 shrink-0">
        <button type="button" className="text-gray-400 hover:text-gray-600 transition-colors" aria-label="Settings" title="Settings">
            <Settings size={20} aria-hidden="true" />
        </button>
        <div className="w-10 h-10 rounded-full overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all">
           <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150" alt="Current user profile photo" className="w-full h-full object-cover" />
        </div>
      </div>
    </div>
  );
}
