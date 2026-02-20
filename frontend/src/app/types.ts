export interface Email {
  id: string;
  sender: {
    name: string;
    email: string;
    avatar?: string;
  };
  subject: string;
  preview: string; // Short text for the list view
  body: string; // Full HTML or text content
  date: string; // ISO string
  read: boolean;
  folder: 'inbox' | 'sent' | 'drafts' | 'trash' | 'spam';
  labels: string[];
  aiAnalysis: {
    category: 'Work' | 'Personal' | 'Finance' | 'Social' | 'Promotions' | 'Urgent';
    sentiment: 'positive' | 'neutral' | 'negative';
    summary: string;
    suggestedActions: string[];
  };
}

export type FolderType = 'inbox' | 'sent' | 'drafts' | 'trash' | 'spam';
