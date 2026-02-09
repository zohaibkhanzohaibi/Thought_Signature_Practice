import React, { useState, useEffect } from 'react';
import { Mail, RefreshCw, Power, Send } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import { io, Socket } from 'socket.io-client';

interface Email {
  id: string;
  subject: string;
  from: string;
  body: string;
  timestamp: string;
  snippet: string;
}

interface Draft {
  id: string;
  subject: string;
  to: string;
  body: string;
  timestamp: string;
  snippet: string;
}

export const InboxView = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [emails, setEmails] = useState<Email[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);

  // Connect to Google OAuth
  const googleLogin = useGoogleLogin({
    scope: 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify',
    onSuccess: async (tokenResponse) => {
      await connectToBackend(tokenResponse.access_token);
    },
    onError: () => {
      console.error('Google OAuth failed');
    },
  });

  const connectToBackend = async (accessToken: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/gmail/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: 'current-user-id', // Replace with actual user ID
          token: accessToken,
        }),
      });

      if (response.ok) {
        setIsConnected(true);
        initializeWebSocket();
      }
    } catch (error) {
      console.error('Failed to connect to backend:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const initializeWebSocket = () => {
    const newSocket = io('http://localhost:8000', {
      query: { userId: 'current-user-id' },
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
    });

    newSocket.on('gmail_update_current-user-id', (data) => {
      if (data.type === 'new_email') {
        setEmails(prev => [data.email, ...prev]);
      } else if (data.type === 'drafts_updated') {
        setDrafts(data.drafts);
      }
    });

    setSocket(newSocket);
  };

  const disconnect = async () => {
    if (socket) {
      socket.disconnect();
    }
    
    await fetch('http://localhost:8000/api/gmail/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId: 'current-user-id' }),
    });
    
    setIsConnected(false);
    setEmails([]);
    setDrafts([]);
  };

  const fetchDrafts = async () => {
    const response = await fetch('http://localhost:8000/api/gmail/drafts?userId=current-user-id');
    const data = await response.json();
    setDrafts(data.drafts);
  };

  useEffect(() => {
    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, [socket]);

  if (!isConnected) {
    return (
      <div className="p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mb-6">
                <Mail size={40} className="text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-4">Connect Your Email</h2>
              <p className="text-slate-600 mb-8 max-w-md text-center">
                Connect your Gmail account to monitor job-related emails and drafts. 
                Get AI-powered suggestions for responses.
              </p>
              <button
                onClick={() => googleLogin()}
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-8 rounded-xl flex items-center gap-3 transition-colors disabled:opacity-50"
              >
                {isLoading ? (
                  <RefreshCw size={20} className="animate-spin" />
                ) : (
                  <Mail size={20} />
                )}
                {isLoading ? 'Connecting...' : 'Connect Gmail'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-800">Email Hub</h1>
            <p className="text-slate-600">Monitor job-related emails and drafts</p>
          </div>
          <button
            onClick={disconnect}
            className="bg-red-100 hover:bg-red-200 text-red-700 font-semibold py-2 px-6 rounded-xl flex items-center gap-2 transition-colors"
          >
            <Power size={18} />
            Disconnect
          </button>
        </div>

        <div className="grid grid-cols-2 gap-8">
          {/* Recent Emails */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-slate-800">Recent Job Emails</h2>
              <span className="bg-blue-100 text-blue-700 text-sm font-semibold py-1 px-3 rounded-full">
                {emails.length} new
              </span>
            </div>
            
            <div className="space-y-4 max-h-[500px] overflow-y-auto">
              {emails.length > 0 ? (
                emails.map((email) => (
                  <div key={email.id} className="border border-slate-200 rounded-xl p-4 hover:bg-slate-50 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-slate-800">{email.subject}</h3>
                      <span className="text-sm text-slate-500">
                        {new Date(parseInt(email.timestamp)).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 mb-2">{email.from}</p>
                    <p className="text-slate-700 text-sm">{email.snippet}</p>
                    <button className="mt-3 text-blue-600 hover:text-blue-800 text-sm font-semibold">
                      View & Reply →
                    </button>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <Mail size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No recent job emails found</p>
                </div>
              )}
            </div>
          </div>

          {/* Drafts */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-slate-800">Email Drafts</h2>
              <button
                onClick={fetchDrafts}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2 px-4 rounded-xl flex items-center gap-2 transition-colors"
              >
                <RefreshCw size={16} />
                Refresh
              </button>
            </div>
            
            <div className="space-y-4 max-h-[500px] overflow-y-auto">
              {drafts.length > 0 ? (
                drafts.map((draft) => (
                  <div key={draft.id} className="border border-slate-200 rounded-xl p-4 hover:bg-slate-50 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-slate-800">{draft.subject}</h3>
                      <span className="text-sm text-slate-500">
                        To: {draft.to}
                      </span>
                    </div>
                    <p className="text-slate-700 text-sm mb-3">{draft.snippet}</p>
                    <div className="flex gap-3">
                      <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-xl flex items-center gap-2 text-sm">
                        <Send size={14} />
                        Continue Draft
                      </button>
                      <button className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold py-2 px-4 rounded-xl text-sm">
                        Get AI Suggestion
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-500">
                  <Mail size={32} className="mx-auto mb-3 opacity-50" />
                  <p>No email drafts found</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* AI Suggestions Section */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-slate-800 mb-4">AI-Powered Email Assistant</h2>
          <p className="text-slate-600 mb-6">Get smart suggestions for your email responses based on your job applications.</p>
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-white rounded-xl p-6">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <span className="text-blue-600 font-bold">✨</span>
              </div>
              <h3 className="font-bold text-slate-800 mb-2">Professional Tone</h3>
              <p className="text-slate-600 text-sm">Get professionally crafted responses suitable for recruiters.</p>
            </div>
            <div className="bg-white rounded-xl p-6">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mb-4">
                <span className="text-green-600 font-bold">⚡</span>
              </div>
              <h3 className="font-bold text-slate-800 mb-2">Quick Responses</h3>
              <p className="text-slate-600 text-sm">Generate instant replies to common interview requests.</p>
            </div>
            <div className="bg-white rounded-xl p-6">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mb-4">
                <span className="text-purple-600 font-bold">🎯</span>
              </div>
              <h3 className="font-bold text-slate-800 mb-2">Tailored Content</h3>
              <p className="text-slate-600 text-sm">Customize responses based on specific job applications.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};