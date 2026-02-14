import React, { useState, useEffect, useCallback } from 'react';
import { Mail, Power, Loader2, Clock, Send, FileText, MessageSquare } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import { useSocketIO } from '../../contexts/SocketIOContext';

interface Draft {
    id: string;
    subject: string;
    to: string;
    body: string;
    timestamp: string;
    snippet: string;
    is_reply: boolean;
}

interface DraftCardProps {
    draft: Draft;
    type: 'reply' | 'application';
    onView: (d: Draft) => void;
}

// Utility: Simple date formatter
const formatTime = (dateString: string) => {
    if (!dateString) return '';
    const date = new Date(parseInt(dateString));
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
    }).format(date);
};

interface InboxViewProps {
    userId: string;
}

const InboxView: React.FC<InboxViewProps> = ({ userId }) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isCheckingAuth, setIsCheckingAuth] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [drafts, setDrafts] = useState<Draft[]>([]);
    const { socket } = useSocketIO();

    // Split drafts into reply vs application types for rendering
    const replyDrafts = drafts.filter(d => Boolean(d.is_reply));
    const applicationDrafts = drafts.filter(d => !d.is_reply);

    const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [showQuoted, setShowQuoted] = useState(false);

    const openDraftModal = (d: Draft) => {
        setSelectedDraft(d);
        setIsModalOpen(true);
    };

    const closeDraftModal = () => {
        setSelectedDraft(null);
        setIsModalOpen(false);
        setShowQuoted(false);
    };

    const extractReplyOnly = (body: string) => {
        if (!body) return '';

        // Look for common separators that indicate start of quoted original
        const separators = [/\nOn .*wrote:/i, /\n> /, /\nFrom:\s/i, /----Original Message----/i];
        let idx = -1;
        for (const sep of separators) {
            const m = body.search(sep);
            if (m >= 0 && (idx === -1 || m < idx)) idx = m;
        }

        if (idx >= 0) return body.slice(0, idx).trim();
        return body.trim();
    };

    const handleSendDraft = async (d: Draft) => {
        try {
            const res = await fetch('http://localhost:8000/api/gmail/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, to: d.to, subject: d.subject, body: d.body })
            });

            if (res.ok) {
                // Remove sent draft from UI
                setDrafts(prev => prev.filter(x => x.id !== d.id));
                closeDraftModal();
            } else {
                console.error('Failed to send draft:', res.status);
            }
        } catch (err) {
            console.error('Error sending draft:', err);
        }
    };

    const handleDeleteDraft = async (d: Draft) => {
        try {
            const res = await fetch(`http://localhost:8000/api/gmail/draft/${userId}/${d.id}`, { method: 'DELETE' });
            if (res.ok) {
                setDrafts(prev => prev.filter(x => x.id !== d.id));
                closeDraftModal();
            } else {
                console.error('Failed to delete draft:', res.status);
            }
        } catch (err) {
            console.error('Error deleting draft:', err);
        }
    };

    const fetchDrafts = useCallback(async () => {
        try {
            const response = await fetch(`http://localhost:8000/api/gmail/drafts/${userId}`);
            if (response.ok) {
                const data = await response.json();
                setDrafts(data.drafts);
            } else {
                console.error('Failed to fetch drafts:', response.status);
            }
        } catch (error) {
            console.error('Error fetching drafts:', error);
        }
    }, [userId]);

    useEffect(() => {
        const checkAuthStatus = async () => {
            setIsCheckingAuth(true);
            try {
                const response = await fetch(`http://localhost:8000/api/gmail/status/${userId}`);
                const data = await response.json();

                if (data.connected) {
                    setIsConnected(true);
                    fetchDrafts();
                }
            } catch (error) {
                console.error("Failed to check auth status:", error);
            } finally {
                setIsCheckingAuth(false);
            }
        };

        checkAuthStatus();
    }, [userId, fetchDrafts]);

    // Setup socket listeners once socket connects
    useEffect(() => {
        if (!socket || !socket.connected) return;

        socket.on(`gmail_update_${userId}`, (data) => {
            if (data.type === 'drafts_updated') {
                setDrafts(data.drafts);
            } else if (data.type === 'disconnected') {
                setIsConnected(false);
                setDrafts([]);
            }
        });

        return () => {
            socket.off(`gmail_update_${userId}`);
        };
    }, [socket, userId]);

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
                fetchDrafts();
            }
        } catch (error) {
            console.error('Failed to connect to backend:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const disconnect = async () => {
        try {
            await fetch(`http://localhost:8000/api/gmail/disconnect/${userId}`, { method: 'DELETE' });
        } catch (error) {
            console.error("Error disconnecting:", error);
        }
        setIsConnected(false);
        setDrafts([]);
    };

    // Loading Screen
    if (isCheckingAuth) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50">
                <Loader2 className="animate-spin text-blue-600 mb-4" size={48} />
                <p className="text-slate-500 font-medium">Checking Gmail connection...</p>
            </div>
        );
    }

    // Connect Screen
    if (!isConnected) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
                <div className="bg-white p-8 rounded-2xl shadow-xl border border-slate-100 max-w-md w-full text-center">
                    <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Mail className="text-blue-600" size={32} />
                    </div>
                    <h1 className="text-2xl font-bold text-slate-800 mb-2">Connect Your Inbox</h1>
                    <p className="text-slate-500 mb-8">
                        Connect your Gmail account to let the agent draft emails and manage job applications for you.
                    </p>
                    <button
                        onClick={() => googleLogin()}
                        disabled={isLoading}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-xl flex items-center justify-center gap-3 transition-all transform active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed shadow-lg shadow-blue-200"
                    >
                        {isLoading ? <Loader2 className="animate-spin" size={20} /> : <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="G" className="w-5 h-5 bg-white rounded-full p-0.5" />}
                        {isLoading ? 'Connecting...' : 'Sign in with Google'}
                    </button>
                </div>
            </div>
        );
    }

    // Connected View
    return (
        <div className="min-h-screen bg-slate-50 p-6 md:p-12">
            <div className="max-w-5xl mx-auto">

                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">Email Drafts</h1>
                        <p className="text-slate-500 mt-1">Review drafts created by your agent before sending.</p>
                    </div>
                    <button
                        onClick={disconnect}
                        className="bg-white hover:bg-red-50 text-slate-600 hover:text-red-600 border border-slate-200 hover:border-red-200 font-medium py-2 px-5 rounded-lg flex items-center gap-2 transition-all shadow-sm"
                    >
                        <Power size={18} />
                        Disconnect
                    </button>
                </div>

                <div className="grid lg:grid-cols-2 gap-8">

                    {/* Reply Drafts Column */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="p-2 bg-purple-100 rounded-lg text-purple-700">
                                <MessageSquare size={20} />
                            </div>
                            <h2 className="text-xl font-bold text-slate-800">Reply Drafts</h2>
                            <span className="ml-auto bg-slate-200 text-slate-600 text-xs font-bold px-2 py-1 rounded-full">{replyDrafts.length}</span>
                        </div>

                        <div className="space-y-4">
                            {replyDrafts.length > 0 ? (
                                replyDrafts.map(draft => (
                                    <DraftCard key={draft.id} draft={draft} type="reply" onView={openDraftModal} />
                                ))
                            ) : (
                                <EmptyState label="No reply drafts found" />
                            )}
                        </div>
                    </div>

                    {/* Application Drafts Column */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="p-2 bg-blue-100 rounded-lg text-blue-700">
                                <FileText size={20} />
                            </div>
                            <h2 className="text-xl font-bold text-slate-800">Application Drafts</h2>
                            <span className="ml-auto bg-slate-200 text-slate-600 text-xs font-bold px-2 py-1 rounded-full">{applicationDrafts.length}</span>
                        </div>

                        <div className="space-y-4">
                            {applicationDrafts.length > 0 ? (
                                applicationDrafts.map(draft => (
                                    <DraftCard key={draft.id} draft={draft} type="application" onView={openDraftModal} />
                                ))
                            ) : (
                                <EmptyState label="No application drafts found" />
                            )}
                        </div>
                    </div>

                </div>
            </div>
            {/* Draft View Modal */}
            {isModalOpen && selectedDraft && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-2xl max-w-3xl w-full p-6 m-4 shadow-lg">
                        <div className="relative mb-4">
                            <div>
                                <h3 className="text-xl font-bold text-slate-800">{selectedDraft.subject || '(No Subject)'}</h3>
                                <div className="text-sm text-slate-500">To: {selectedDraft.to}</div>
                            </div>
                            <button onClick={closeDraftModal} className="absolute top-0 right-0 text-slate-400 hover:text-slate-600">✕</button>
                        </div>

                        <div className="prose max-h-72 overflow-auto whitespace-pre-wrap text-slate-700 mb-4">
                            {extractReplyOnly(selectedDraft.body)}
                        </div>

                        {/* Show quoted toggle */}
                        {selectedDraft.body && extractReplyOnly(selectedDraft.body) !== selectedDraft.body && (
                            <div className="text-sm text-slate-500 mb-4">
                                <button
                                    onClick={() => setShowQuoted(prev => !prev)}
                                    className="underline text-slate-600"
                                >
                                    {showQuoted ? 'Hide quoted original' : 'Show quoted original'}
                                </button>
                            </div>
                        )}

                        {showQuoted && (
                            <div className="prose max-h-56 overflow-auto whitespace-pre-wrap text-slate-500 italic mb-6 border rounded p-3 bg-slate-50">
                                {selectedDraft.body}
                            </div>
                        )}

                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => handleDeleteDraft(selectedDraft)}
                                className="bg-white border border-red-200 text-red-600 px-4 py-2 rounded-lg hover:bg-red-50"
                            >
                                Delete
                            </button>
                            <button
                                onClick={() => handleSendDraft(selectedDraft)}
                                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                            >
                                Send
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// Sub-components for cleaner code

const DraftCard: React.FC<DraftCardProps> = ({ draft, type, onView }) => {
    const isReply = type === 'reply';

    // Handler to open view modal
    const handleView = (e: React.MouseEvent) => {
        e.stopPropagation();
        onView(draft);
    };

    return (
        <div className="group bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-md transition-all relative overflow-hidden">
            {/* Color strip on the left */}
            <div className={`absolute top-0 left-0 w-1 h-full ${isReply ? 'bg-purple-500' : 'bg-blue-500'}`} />

            {/* Header: Subject & Date */}
            <div className="flex justify-between items-start mb-2 pl-3">
                <h3 className="font-semibold text-slate-800 text-lg leading-tight truncate pr-4" title={draft.subject}>
                    {draft.subject || "(No Subject)"}
                </h3>
                {draft.timestamp && (
                    <span className="flex items-center text-xs text-slate-400 whitespace-nowrap bg-slate-50 px-2 py-1 rounded">
                        <Clock size={12} className="mr-1" />
                        {formatTime(draft.timestamp)}
                    </span>
                )}
            </div>

            {/* Body: To & Snippet */}
            <div className="pl-3 mb-3">
                <div className="flex items-center text-sm text-slate-500 mb-2">
                    <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded mr-2 font-medium">To</span>
                    <span className="truncate">{draft.to}</span>
                </div>
                <p className="text-slate-600 text-sm leading-relaxed line-clamp-3 bg-slate-50 p-3 rounded-lg border border-slate-100 italic">
                    "{draft.snippet}"
                </p>
            </div>

            {/* Footer: Action Button */}
            <div className="pl-3 flex justify-end">
                <button
                    onClick={handleView}
                    className="text-blue-600 text-sm font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity hover:underline"
                >
                    View <Send size={14} />
                </button>
            </div>
        </div>
    );
};

// Modal is rendered inside the parent component via state, not here.

const EmptyState = ({ label }: { label: string }) => (
    <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
        <div className="bg-white p-3 rounded-full shadow-sm mb-3">
            <Mail size={24} className="text-slate-300" />
        </div>
        <p className="text-slate-400 font-medium text-sm">{label}</p>
    </div>
);

// Modal is placed here so it has access to handlers via closure in the parent component
// Note: JSX rendering for modal requires the parent to render it, so we add a small helper
// The modal uses `selectedDraft`, `isModalOpen`, `handleSendDraft`, `handleDeleteDraft`, `closeDraftModal`
// which are defined in the parent component scope above.

// To ensure TypeScript/JSX sees the variables, we export default at file end (unchanged).

export default InboxView;