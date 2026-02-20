import React, { useState } from 'react';
import { Outlet, useParams } from 'react-router';
import { Sidebar } from './Sidebar';
import { EmailList } from './EmailList';
import { ComposeModal } from './ComposeModal';
import { FolderType } from '../types';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { 
  PanelResizeHandle, 
  Panel, 
  PanelGroup 
} from 'react-resizable-panels';

export function MailLayout() {
  const { folder, emailId } = useParams();
  const currentFolder = (folder as FolderType) || 'inbox';
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const isMdUp = useMediaQuery('(min-width: 768px)');

  return (
    <div className="h-screen w-screen bg-gray-50 flex overflow-hidden font-sans relative">
      <ComposeModal 
        isOpen={isComposeOpen} 
        onClose={() => setIsComposeOpen(false)} 
      />

      {isMdUp ? (
        <PanelGroup direction="horizontal">
          {/* Sidebar */}
          <Panel defaultSize={6} minSize={4} maxSize={12} className="min-w-[80px]">
            <Sidebar onComposeClick={() => setIsComposeOpen(true)} />
          </Panel>

          <PanelResizeHandle className="w-1 bg-gray-200 hover:bg-blue-400 transition-colors cursor-col-resize z-10" />

          {/* Email List */}
          <Panel defaultSize={34} minSize={25} maxSize={40} className="min-w-[300px]">
            <EmailList folder={currentFolder} />
          </Panel>

          <PanelResizeHandle className="w-1 bg-gray-200 hover:bg-blue-400 transition-colors cursor-col-resize z-10" />

          {/* Reading Pane */}
          <Panel defaultSize={60} minSize={30}>
            <div className="h-full bg-white">
              <Outlet />
            </div>
          </Panel>
        </PanelGroup>
      ) : (
        <div className="flex h-full w-full overflow-hidden">
          <div className="w-16 shrink-0">
            <Sidebar onComposeClick={() => setIsComposeOpen(true)} className="py-3" />
          </div>

          <div className="flex-1 min-w-0 h-full bg-white">
            {emailId ? (
              <Outlet />
            ) : (
              <EmailList folder={currentFolder} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
