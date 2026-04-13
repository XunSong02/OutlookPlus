import React, { useEffect, useState } from 'react';
import { ArrowLeft, CheckCircle2, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router';
import {
  getCredentialsStatus,
  saveCredentials,
  deleteCredentialsRaw,
  triggerIngest,
  getUserEmail,
  setUserEmail,
  type CredentialsStatus,
  type SaveCredentialsInput,
} from '../services/outlookplusApi';
import { useEmails } from '../state/emails';

type SectionStatus = 'idle' | 'saving' | 'saved' | 'error';

export function SettingsPage() {
  const navigate = useNavigate();
  const { reload, setIsFetching } = useEmails();

  // Credential status from backend
  const [status, setStatus] = useState<CredentialsStatus | null>(null);
  const [loading, setLoading] = useState(true);

  // IMAP fields
  const [imapHost, setImapHost] = useState('imap.gmail.com');
  const [imapPort, setImapPort] = useState(993);
  const [imapUsername, setImapUsername] = useState(getUserEmail() ?? '');
  const [imapPassword, setImapPassword] = useState('');
  const [imapFolder, setImapFolder] = useState('INBOX');
  const [imapStatus, setImapStatus] = useState<SectionStatus>('idle');

  // SMTP fields
  const [smtpHost, setSmtpHost] = useState('smtp.gmail.com');
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUsername, setSmtpUsername] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [smtpStatus, setSmtpStatus] = useState<SectionStatus>('idle');

  // Gemini fields
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-3-flash-preview');
  const [geminiStatus, setGeminiStatus] = useState<SectionStatus>('idle');

  // Ingest
  const [ingesting, setIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<string | null>(null);

  // Error message
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCredentialsStatus()
      .then((s) => setStatus(s))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveImap = async () => {
    if (!imapHost || !imapUsername || !imapPassword) {
      setError('Please fill in all IMAP fields');
      return;
    }
    setImapStatus('saving');
    setError(null);
    try {
      // Persist the email address BEFORE the API call so the request
      // already carries the correct X-User-Email header.
      const previousEmail = getUserEmail();
      setUserEmail(imapUsername);

      const updated = await saveCredentials({
        imap: { host: imapHost, port: imapPort, username: imapUsername, password: imapPassword, folder: imapFolder },
      });
      setStatus(updated);
      setImapStatus('saved');
      setTimeout(() => setImapStatus('idle'), 2000);

      // If the account changed, clear stale emails from the old account.
      if (previousEmail && previousEmail !== imapUsername) {
        await reload();
      }
    } catch (e: any) {
      setImapStatus('error');
      setError(e.message);
    }
  };

  const handleSaveSmtp = async () => {
    if (!smtpHost || !smtpUsername || !smtpPassword) {
      setError('Please fill in all SMTP fields');
      return;
    }
    setSmtpStatus('saving');
    setError(null);
    try {
      const updated = await saveCredentials({
        smtp: { host: smtpHost, port: smtpPort, username: smtpUsername, password: smtpPassword },
      });
      setStatus(updated);
      setSmtpStatus('saved');
      setTimeout(() => setSmtpStatus('idle'), 2000);
    } catch (e: any) {
      setSmtpStatus('error');
      setError(e.message);
    }
  };

  const handleSaveGemini = async () => {
    if (!geminiApiKey) {
      setError('Please enter the Gemini API key');
      return;
    }
    setGeminiStatus('saving');
    setError(null);
    try {
      const updated = await saveCredentials({
        gemini: { api_key: geminiApiKey, model: geminiModel },
      });
      setStatus(updated);
      setGeminiStatus('saved');
      setTimeout(() => setGeminiStatus('idle'), 2000);
    } catch (e: any) {
      setGeminiStatus('error');
      setError(e.message);
    }
  };

  const handleTriggerIngest = async () => {
    setIngesting(true);
    setIsFetching(true);
    setIngestResult(null);
    setError(null);
    try {
      const result = await triggerIngest();
      await reload();
      navigate('/inbox');
    } catch (e: any) {
      setIsFetching(false);
      // Extract readable detail from API error JSON if possible.
      let msg = e.message ?? 'Fetch failed';
      try {
        const match = msg.match(/\{.*"detail"\s*:\s*"([^"]+)"/);
        if (match) msg = match[1];
      } catch { /* keep original */ }
      setError(msg);
    } finally {
      setIngesting(false);
    }
  };

  const StatusBadge = ({ configured }: { configured: boolean }) =>
    configured ? (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
        <CheckCircle2 size={12} /> Configured
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
        <XCircle size={12} /> Not set
      </span>
    );

  const SaveButton = ({ onClick, status: s, label }: { onClick: () => void; status: SectionStatus; label: string }) => (
    <button
      type="button"
      onClick={onClick}
      disabled={s === 'saving'}
      className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
    >
      {s === 'saving' && <Loader2 size={14} className="animate-spin" />}
      {s === 'saved' && <CheckCircle2 size={14} />}
      {s === 'saving' ? 'Saving...' : s === 'saved' ? 'Saved!' : label}
    </button>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="max-w-2xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <button
            type="button"
            onClick={() => navigate('/inbox')}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}

        {/* IMAP Section */}
        <section className="mb-8 p-5 border border-gray-200 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">IMAP (Email Receiving)</h2>
            {status && <StatusBadge configured={status.imap} />}
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Host</label>
                <input type="text" value={imapHost} onChange={(e) => setImapHost(e.target.value)} placeholder="imap.gmail.com" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Port</label>
                <input type="number" value={imapPort} onChange={(e) => setImapPort(Number(e.target.value))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Username (Email)</label>
              <input type="email" value={imapUsername} onChange={(e) => setImapUsername(e.target.value)} placeholder="you@gmail.com" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Password / App Password</label>
              <input type="password" value={imapPassword} onChange={(e) => setImapPassword(e.target.value)} placeholder="App password" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Folder</label>
              <input type="text" value={imapFolder} onChange={(e) => setImapFolder(e.target.value)} placeholder="INBOX" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <SaveButton onClick={handleSaveImap} status={imapStatus} label="Save IMAP" />
          </div>
        </section>

        {/* SMTP Section */}
        <section className="mb-8 p-5 border border-gray-200 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">SMTP (Email Sending)</h2>
            {status && <StatusBadge configured={status.smtp} />}
          </div>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Host</label>
                <input type="text" value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} placeholder="smtp.gmail.com" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Port</label>
                <input type="number" value={smtpPort} onChange={(e) => setSmtpPort(Number(e.target.value))} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Username (Email)</label>
              <input type="email" value={smtpUsername} onChange={(e) => setSmtpUsername(e.target.value)} placeholder="you@gmail.com" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Password / App Password</label>
              <input type="password" value={smtpPassword} onChange={(e) => setSmtpPassword(e.target.value)} placeholder="App password" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <SaveButton onClick={handleSaveSmtp} status={smtpStatus} label="Save SMTP" />
          </div>
        </section>

        {/* Gemini Section */}
        <section className="mb-8 p-5 border border-gray-200 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Gemini AI</h2>
            {status && <StatusBadge configured={status.gemini} />}
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">API Key</label>
              <input type="password" value={geminiApiKey} onChange={(e) => setGeminiApiKey(e.target.value)} placeholder="AIzaSy..." className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Model</label>
              <input type="text" value={geminiModel} onChange={(e) => setGeminiModel(e.target.value)} placeholder="gemini-3-flash-preview" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <SaveButton onClick={handleSaveGemini} status={geminiStatus} label="Save Gemini" />
          </div>
        </section>

        {/* Trigger Ingest */}
        <section className="mb-8 p-5 border border-gray-200 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Fetch Emails</h2>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            Manually trigger an email fetch from your IMAP server using the stored credentials.
          </p>
          {ingestResult && (
            <div className="mb-3 p-2 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              {ingestResult}
            </div>
          )}
          <button
            type="button"
            onClick={handleTriggerIngest}
            disabled={ingesting || !(status?.imap)}
            className="px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {ingesting ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            {ingesting ? 'Fetching...' : 'Fetch Now'}
          </button>
        </section>

        {/* API Base URL info */}
        <section className="p-5 border border-gray-200 rounded-xl bg-gray-50">
          <h2 className="text-lg font-medium text-gray-900 mb-2">API Connection</h2>
          <p className="text-sm text-gray-600">
            Backend URL:{' '}
            <code className="bg-gray-200 px-1.5 py-0.5 rounded text-xs">
              {import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || '(using proxy / same origin)'}
            </code>
          </p>
          <p className="text-xs text-gray-500 mt-2">
            To point the frontend at an API Gateway endpoint, set <code className="bg-gray-200 px-1 rounded">VITE_API_BASE_URL</code> in your <code className="bg-gray-200 px-1 rounded">.env</code> file or environment.
          </p>
        </section>
      </div>
    </div>
  );
}
