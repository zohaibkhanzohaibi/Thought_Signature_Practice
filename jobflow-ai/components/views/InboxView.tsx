import React, { useState, useEffect } from 'react';
import { Mail, Power } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import io, { type Socket } from 'socket.io-client';

interface Draft {
  id: string;
  subject: string;
  to: string;
  body: string;
  timestamp: string;
  snippet: string;
  is_reply: boolean; // Flag from backend
}

// Utility: generate/retrieve user ID
const getUserId = (): string => {
  const STORAGE_KEY = 'marathon_user_id';
  let userId = localStorage.getItem(STORAGE_KEY);
  if (!userId) {
    userId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
    localStorage.setItem(STORAGE_KEY, userId);
  }
  return userId;
};

const InboxView = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [userId] = useState<string>(getUserId());

  // Google OAuth login
  const googleLogin = useGoogleLogin({
    scope: 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify',
    onSuccess: async (tokenResponse) => {
      await connectToBackend(tokenResponse.access_token);
    },
    onError: () => console.error('Google OAuth failed'),
  });

  const connectToBackend = async (accessToken: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/gmail/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, token: { access_token: accessToken } }),
      });
      if (response.ok) {
        setIsConnected(true);
        initializeWebSocket();
        fetchDrafts();
      }
    } catch (error) {
      console.error('Failed to connect to backend:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const initializeWebSocket = () => {
    const newSocket = io('http://localhost:8000', { query: { userId } });
    newSocket.on('connect', () => console.log('WebSocket connected'));
    newSocket.on(`gmail_update_${userId}`, (data) => {
      if (data.type === 'drafts_updated') {
        setDrafts(data.drafts);
      }
    });
    setSocket(newSocket);
  };

  const disconnect = async () => {
    if (socket) socket.disconnect();
    await fetch('http://localhost:8000/api/gmail/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    setIsConnected(false);
    setDrafts([]);
  };

  const fetchDrafts = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/gmail/drafts/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setDrafts(data.drafts);
      } else console.error('Failed to fetch drafts:', response.status);
    } catch (error) {
      console.error('Error fetching drafts:', error);
    }
  };

  // Split drafts by is_reply flag
  const replyDrafts = drafts.filter(d => d.is_reply);
  const applicationDrafts = drafts.filter(d => !d.is_reply);

  useEffect(() => {
    return () => { if (socket) socket.disconnect(); };
  }, [socket]);

  if (!isConnected) {
    return (
      <div className="p-8 flex justify-center">
        <button
          onClick={() => googleLogin()}
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-xl flex items-center gap-3"
        >
          {isLoading ? 'Connecting...' : 'Connect Gmail'}
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Email Drafts</h1>
        <button
          onClick={disconnect}
          className="bg-red-100 hover:bg-red-200 text-red-700 font-semibold py-2 px-6 rounded-xl flex items-center gap-2"
        >
          <Power size={18} />
          Disconnect
        </button>
      </div>

      {/* Reply Drafts */}
      <h2 className="text-xl font-bold text-slate-800 mb-4">Reply Drafts</h2>
      <div className="space-y-4 mb-8">
        {replyDrafts.length > 0 ? (
          replyDrafts.map(draft => (
            <div key={draft.id} className="border border-slate-200 rounded-xl p-4 hover:bg-slate-50 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-slate-800">{draft.subject}</h3>
                <span className="text-sm text-slate-500">To: {draft.to}</span>
              </div>
              <p className="text-slate-700 text-sm">{draft.snippet}</p>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-slate-500">
            <Mail size={32} className="mx-auto mb-3 opacity-50" />
            <p>No reply drafts found</p>
          </div>
        )}
      </div>

      {/* Application Drafts */}
      <h2 className="text-xl font-bold text-slate-800 mb-4">Application Drafts</h2>
      <div className="space-y-4">
        {applicationDrafts.length > 0 ? (
          applicationDrafts.map(draft => (
            <div key={draft.id} className="border border-slate-200 rounded-xl p-4 hover:bg-slate-50 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-slate-800">{draft.subject}</h3>
                <span className="text-sm text-slate-500">To: {draft.to}</span>
              </div>
              <p className="text-slate-700 text-sm">{draft.snippet}</p>
            </div>
          ))
        ) : (
          <div className="text-center py-8 text-slate-500">
            <Mail size={32} className="mx-auto mb-3 opacity-50" />
            <p>No application drafts found</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default InboxView;
