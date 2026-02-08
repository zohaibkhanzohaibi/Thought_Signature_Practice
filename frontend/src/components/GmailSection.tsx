import { useState } from 'react';
import { api } from '../api';

interface Props {
  userId: string;
  showToast: (message: string, type?: 'success' | 'error') => void;
}

interface EmailThread {
  id: string;
  subject?: string;
  last_sender?: string;
  last_snippet?: string;
  status: string;
  message_count: number;
}

export default function GmailSection({ userId, showToast }: Props) {
  const [loading, setLoading] = useState(false);
  const [threads, setThreads] = useState<EmailThread[]>([]);
  const [checkResults, setCheckResults] = useState<Record<string, unknown>[]>([]);

  const handleConnect = async () => {
    setLoading(true);
    try {
      const result = await api.getGmailAuthUrl(userId);
      window.open(result.auth_url, '_blank');
      showToast('Opening Gmail authorization...');
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckEmails = async () => {
    setLoading(true);
    try {
      const result = await api.checkEmails(userId);
      setCheckResults(result.results || []);
      showToast(result.message);
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadThreads = async () => {
    setLoading(true);
    try {
      const result = await api.getEmailThreads(userId);
      setThreads(result as EmailThread[]);
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-gray-100 text-gray-800',
      needs_reply: 'bg-red-100 text-red-800',
      replied: 'bg-green-100 text-green-800',
      waiting: 'bg-yellow-100 text-yellow-800',
      closed: 'bg-blue-100 text-blue-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">📧 Gmail Integration</h2>

      {/* Connect Gmail */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Gmail OAuth</h3>
        <p className="text-gray-600 mb-4">
          Connect your Gmail account to enable email drafts and automated reply monitoring.
        </p>
        <button onClick={handleConnect} className="btn-primary" disabled={loading}>
          🔗 Connect Gmail
        </button>
      </div>

      {/* Check Emails */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Check for New Emails</h3>
        <p className="text-gray-600 mb-4">
          Scan your inbox for job-related emails and generate draft replies using AI.
        </p>
        <button onClick={handleCheckEmails} className="btn-secondary" disabled={loading}>
          {loading ? 'Checking...' : '📥 Check Emails'}
        </button>
        
        {checkResults.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="font-medium text-gray-700">Results:</h4>
            {checkResults.map((result, index) => (
              <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm">
                <pre className="whitespace-pre-wrap text-gray-600">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Email Threads */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Email Threads</h3>
          <button onClick={handleLoadThreads} className="btn-secondary text-sm" disabled={loading}>
            🔄 Refresh
          </button>
        </div>

        {threads.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No email threads tracked yet. Check emails to start monitoring.
          </p>
        ) : (
          <div className="space-y-3">
            {threads.map((thread) => (
              <div
                key={thread.id}
                className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-gray-800">
                      {thread.subject || '(No subject)'}
                    </h4>
                    <p className="text-sm text-gray-600">
                      From: {thread.last_sender || 'Unknown'}
                    </p>
                    {thread.last_snippet && (
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {thread.last_snippet}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-xs px-2 py-1 rounded-full ${getStatusBadge(thread.status)}`}>
                      {thread.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-500">
                      {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
