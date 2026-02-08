import React, { useState, useEffect } from 'react';
import { Plus, Sparkles, Briefcase, MapPin, Globe, Mail, ArrowRight, Loader2 } from 'lucide-react';
// 👇 Import your existing auth service
import { authService } from '../../services/auth'; 

interface PublicJob {
    id: number;
    title: string;
    company: string;
    location: string;
    description: string;
    contact_email?: string;
    source_url?: string;
}

export const JobDiscoveryView = ({ onApply }: { onApply: (job: any) => void }) => {
    // State
    const [mode, setMode] = useState<'feed' | 'create'>('feed');
    const [rawText, setRawText] = useState('');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [parsedJob, setParsedJob] = useState<Partial<PublicJob> | null>(null);
    const [publicJobs, setPublicJobs] = useState<PublicJob[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    
    // Auth State
    const [token, setToken] = useState<string | null>(null);

    // 1. Initialize: Get Token from your authService
    useEffect(() => {
        // use authService.getToken() which looks for "token"
        const storedToken = authService.getToken(); 
        
        if (storedToken) {
            setToken(storedToken);
            console.log("✅ User Logged In");
        } else {
            console.log("❌ No Token Found (User logged out)");
        }

        fetchPublicJobs();
    }, []);

    // Helper: Build headers using the token
    const getAuthHeaders = () => {
        return {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        };
    };

    const fetchPublicJobs = async () => {
        setIsLoading(true);
        try {
            const res = await fetch('http://localhost:8000/api/jobs/public/feed');
            const data = await res.json();
            setPublicJobs(data);
        } catch (e) {
            console.error("Failed to fetch jobs", e);
        } finally {
            setIsLoading(false);
        }
    };

    // 2. Handle Text Analysis
    const handleAnalyze = async () => {
        if (!rawText) return;
        
        if (!token) {
            alert("Please log in to use AI analysis.");
            return;
        }

        setIsAnalyzing(true);
        try {
            const res = await fetch('http://localhost:8000/api/jobs/parse-raw', {
                method: 'POST',
                headers: getAuthHeaders(), // Sends "Bearer <token>"
                body: JSON.stringify({ raw_text: rawText }) 
            });
            
            if (!res.ok) throw new Error("Analysis failed");
            
            const data = await res.json();
            setParsedJob(data);
        } catch (error) {
            console.error(error);
            alert("Failed to analyze job text.");
        } finally {
            setIsAnalyzing(false);
        }
    };

    // 3. Handle Saving to Database
    const handleShareJob = async () => {
        if (!parsedJob || !token) return;

        try {
            const payload = {
                title: parsedJob.title,
                company: parsedJob.company,
                location: parsedJob.location || "Remote",
                description: parsedJob.description || parsedJob.summary || "", 
                contact_email: parsedJob.contact_email,
                source_url: parsedJob.source_url
            };

            const response = await fetch('http://localhost:8000/api/jobs/public', {
                method: 'POST',
                headers: getAuthHeaders(), 
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                console.error("Save failed:", err);
                alert("Failed to save job. See console.");
                return;
            }

            // Success
            setMode('feed');
            setRawText('');
            setParsedJob(null);
            fetchPublicJobs();
        } catch (error) {
            console.error("Failed to save", error);
        }
    };

    // 4. Handle "Draft Application"
    const handleImportToProfile = async (jobId: number) => {
        if (!token) {
            alert("Please log in to apply.");
            return;
        }

        try {
            const res = await fetch(`http://localhost:8000/api/jobs/public/${jobId}/save-to-profile`, {
                method: 'POST',
                headers: getAuthHeaders() 
            });
            
            if (res.ok) {
                const data = await res.json();
                onApply(data); 
            } else {
                alert("Failed to create application draft.");
            }
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="h-full flex flex-col gap-6 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex justify-between items-center bg-white p-6 rounded-[32px] border border-slate-200 shadow-sm">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800">Community Job Board</h2>
                    <p className="text-slate-500">Discover jobs found by the community or add your own.</p>
                </div>
                <button 
                    onClick={() => setMode(mode === 'feed' ? 'create' : 'feed')}
                    className={`px-6 py-3 rounded-2xl font-bold flex items-center gap-2 transition-all ${
                        mode === 'feed' 
                        ? 'bg-slate-900 text-white hover:bg-slate-800' 
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                >
                    {mode === 'feed' ? <><Plus size={20}/> Add Manual Job</> : 'Back to Feed'}
                </button>
            </div>

            {/* CREATE MODE */}
            {mode === 'create' && (
                <div className="flex-1 flex gap-6">
                    <div className="flex-1 bg-white border border-slate-200 rounded-[32px] p-8 shadow-sm flex flex-col">
                        <label className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4">
                            Paste Job Post (LinkedIn, Email, etc.)
                        </label>
                        <textarea 
                            value={rawText}
                            onChange={(e) => setRawText(e.target.value)}
                            placeholder="Paste the entire post here..."
                            className="flex-1 w-full bg-slate-50 border-transparent rounded-2xl p-6 text-slate-600 focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none resize-none transition-all mb-4"
                        />
                        <button 
                            onClick={handleAnalyze}
                            disabled={isAnalyzing || !rawText}
                            className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl flex justify-center items-center gap-2 transition-all disabled:opacity-50"
                        >
                            {isAnalyzing ? <Loader2 className="animate-spin" /> : <Sparkles size={20} />}
                            Analyze with AI
                        </button>
                        {!token && <p className="text-xs text-red-500 text-center mt-2 font-bold">You must be logged in to analyze.</p>}
                    </div>

                    {/* Preview Panel */}
                    {parsedJob && (
                        <div className="w-1/3 bg-white border border-slate-200 rounded-[32px] p-8 shadow-xl animate-in slide-in-from-right-4">
                            <h3 className="font-bold text-lg text-slate-800 mb-6">Preview Extraction</h3>
                            <div className="space-y-4 mb-8">
                                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                                    <div className="text-xs font-bold text-slate-400 uppercase">Role</div>
                                    <div className="font-bold text-slate-700">{parsedJob.title || "Unknown"}</div>
                                </div>
                                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                                    <div className="text-xs font-bold text-slate-400 uppercase">Company</div>
                                    <div className="font-bold text-slate-700">{parsedJob.company || "Unknown"}</div>
                                </div>
                                {(parsedJob.contact_email || parsedJob.source_url) && (
                                    <div className="flex gap-2 flex-wrap">
                                        {parsedJob.contact_email && (
                                            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-xs font-bold flex items-center gap-1"><Mail size={12}/> Email Found</span>
                                        )}
                                        {parsedJob.source_url && (
                                            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs font-bold flex items-center gap-1"><Globe size={12}/> URL Found</span>
                                        )}
                                    </div>
                                )}
                            </div>
                            <button onClick={handleShareJob} className="w-full py-4 bg-slate-900 text-white font-bold rounded-2xl hover:scale-[1.02] transition-transform shadow-lg">
                                Save to Community Board
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* FEED MODE */}
            {mode === 'feed' && (
                <div className="flex-1 bg-white border border-slate-200 rounded-[32px] p-8 shadow-sm overflow-hidden flex flex-col">
                    {isLoading ? (
                        <div className="flex-1 flex justify-center items-center">
                            <Loader2 className="animate-spin text-slate-300" size={40} />
                        </div>
                    ) : (
                        <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-4">
                            {publicJobs.map((job) => (
                                <div key={job.id} className="p-6 border border-slate-100 rounded-[24px] hover:border-slate-300 hover:shadow-md transition-all group bg-slate-50/50">
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1 mr-4">
                                            <h3 className="text-xl font-bold text-slate-800">{job.title}</h3>
                                            <div className="flex items-center gap-4 mt-2 text-slate-500 font-medium text-sm flex-wrap">
                                                <span className="flex items-center gap-1"><Briefcase size={14}/> {job.company}</span>
                                                <span className="flex items-center gap-1"><MapPin size={14}/> {job.location || 'Remote'}</span>
                                                {job.contact_email && <span className="flex items-center gap-1 text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md"><Mail size={14}/> {job.contact_email}</span>}
                                            </div>
                                            <p className="mt-4 text-slate-600 line-clamp-2 text-sm">{job.description}</p>
                                        </div>
                                        <button onClick={() => handleImportToProfile(job.id)} className="px-5 py-3 bg-white border border-slate-200 text-slate-700 font-bold rounded-xl hover:bg-blue-600 hover:text-white hover:border-blue-600 transition-all shadow-sm flex items-center gap-2 group-hover:translate-x-1 whitespace-nowrap">
                                            Draft Application <ArrowRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {publicJobs.length === 0 && (
                                <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                                    <Briefcase size={48} className="mb-4 opacity-20" />
                                    <p>No jobs found. Be the first to add one!</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};