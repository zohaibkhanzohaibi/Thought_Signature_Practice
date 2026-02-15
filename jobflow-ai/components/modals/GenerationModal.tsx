import React, { useState } from 'react';
import { Layers, X, FileText, AlertCircle, Send, CheckCircle } from 'lucide-react';

export const GenerationModal = ({ job, user, onClose, onComplete }: {
    job: any; 
    user: any;
    onClose: () => void;
    onComplete: (app: any) => void
}) => {
    const [generating, setGenerating] = useState(false);
    const [coverLetter, setCoverLetter] = useState('');
    const [analysis, setAnalysis] = useState<any>(null); // Store backend analysis
    const [step, setStep] = useState<'initial' | 'review'>('initial');

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            console.log(`🚀 Sending request to backend for Job ID: ${job.id}`);
            
            const response = await fetch(`http://localhost:8000/api/jobs/${job.id}/tailor`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Backend failed to tailor resume');
            }

            const data = await response.json();
            console.log("✅ Backend Response:", data);

            // 1. Set the Cover Letter Content
            const content = data.cover_email || data.cover_letter || "No content returned.";
            setCoverLetter(content);

            // 2. Set Analysis Data (Skills found)
            if (data.jd_analysis) {
                setAnalysis(data.jd_analysis);
            }

            setStep('review');

        } catch (error: any) {
            console.error("❌ Generation Error:", error);
            setCoverLetter(`Error generating content: ${error.message}`);
            setStep('review');
        } finally {
            setGenerating(false);
        }
    };

    // Inside genrationmodal.tsx -> handleFinish()

    const handleFinish = async () => {
        try {
            // 👇 1. ADD THIS: Trigger PDF Generation on the backend first
            console.log("📄 Generating tailored PDF resume...");
            const pdfRes = await fetch(`http://localhost:8000/api/jobs/${job.id}/generate-pdf`, {
                method: 'POST'
            });

            if (!pdfRes.ok) {
                console.warn("⚠️ PDF generation failed. Email will draft without attachment.");
            } else {
                console.log("✅ PDF generated and saved to database.");
            }

            // 👇 2. Then proceed with creating the draft
            const targetEmail = job.contact_email || job.company_email || job.application_email || 'hr@company.com';

            const draftRes = await fetch(`http://localhost:8000/api/jobs/${job.id}/create-draft`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    to: targetEmail,
                    subject: `Application for ${displayTitle}`, 
                    body: coverLetter // Sends the explicitly edited UI text
                })
            });

            if (!draftRes.ok) {
                const errorData = await draftRes.json();
                throw new Error(errorData.detail || 'Failed to create Gmail draft');
            }

            // 3. Draft created successfully! Update the UI state.
            const newApp = {
                id: job.id, 
                jobId: job.id,
                status: 'drafted', 
                appliedDate: new Date().toISOString().split('T')[0],
                createdDate: new Date().toISOString().split('T')[0],
                lastUpdated: new Date().toISOString().split('T')[0],
                coverLetter: coverLetter,
                emailThread: []
            };
            
            onComplete(newApp);

        } catch (error: any) {
            console.error("❌ Draft Error:", error);
            alert(`Error creating draft: ${error.message}`);
        }
    };

    const displayTitle = job.position || job.job_title || "Unknown Role";
    const displayCompany = job.company || job.company_name || "Unknown Company";

    // Dynamic skills display (defaults to mock if not yet analyzed)
    const matchingSkills = analysis?.hard_skills?.slice(0, 3) || user.skills?.slice(0, 2).map((s: any) => s.name) || ["React", "TypeScript"];

    return (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-6 z-[200] animate-in fade-in duration-300">
            <div className="w-full max-w-2xl bg-white rounded-[40px] shadow-2xl border border-slate-100 overflow-hidden animate-in zoom-in-95 duration-500">
                <div className="p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-600 rounded-2xl text-white shadow-xl">
                            <Layers size={24} />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-slate-800">Application Builder</h3>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                                {displayCompany} • {displayTitle}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200 rounded-xl transition-all">
                        <X size={24} />
                    </button>
                </div>

                <div className="p-10">
                    {step === 'initial' ? (
                        <div className="text-center space-y-8">
                            <div className="w-24 h-24 bg-blue-50 rounded-full flex items-center justify-center mx-auto text-blue-600">
                                <FileText size={48} />
                            </div>
                            <div className="max-w-md mx-auto">
                                <h4 className="text-2xl font-bold text-slate-800 mb-4">Tailor Your Application</h4>
                                <p className="text-slate-500 leading-relaxed">
                                    Our AI will analyze your profile and the requirements for <span className="font-bold text-slate-700">{displayTitle}</span> to create a highly personalized cover letter.
                                </p>
                            </div>
                            
                            {/* This is the part that says "We noticed..." */}
                            <div className="bg-blue-50/50 p-6 rounded-[32px] border border-blue-100 flex items-start gap-4 text-left">
                                <div className="p-2 bg-blue-600 rounded-lg text-white mt-1">
                                    <AlertCircle size={16} />
                                </div>
                                <p className="text-sm text-blue-800 font-medium">
                                    We will highlight your experience with <strong>{matchingSkills.join(', ')}</strong> to align with this role's requirements.
                                </p>
                            </div>

                            <button
                                onClick={handleGenerate}
                                disabled={generating}
                                className="w-full py-5 bg-blue-600 text-white font-bold rounded-[24px] shadow-2xl shadow-blue-200 hover:bg-blue-700 transition-all flex items-center justify-center gap-3 disabled:opacity-70"
                            >
                                {generating ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        Generating Tailored Content...
                                    </>
                                ) : (
                                    <>
                                        <Send size={20} />
                                        Generate & Apply
                                    </>
                                )}
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-8">
                            <div>
                                <div className="flex justify-between items-center mb-4">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">AI Generated Cover Letter</label>
                                    <button className="text-xs font-bold text-blue-600 hover:underline">Edit Content</button>
                                </div>
                                {/* Display the generated content here */}
                                <div className="w-full p-6 bg-slate-50 border border-slate-200 rounded-[24px] text-slate-600 text-sm leading-relaxed max-h-[300px] overflow-y-auto whitespace-pre-wrap custom-scrollbar">
                                    {coverLetter}
                                </div>
                            </div>
                            <div className="flex gap-4">
                                <button
                                    onClick={() => setStep('initial')}
                                    className="flex-1 py-4 border border-slate-200 text-slate-600 font-bold rounded-[20px] hover:bg-slate-50 transition-all"
                                >
                                    Regenerate
                                </button>
                                <button
                                    onClick={handleFinish}
                                    className="flex-[2] py-4 bg-blue-600 text-white font-bold rounded-[20px] shadow-2xl shadow-blue-200 hover:bg-blue-700 transition-all flex items-center justify-center gap-2"
                                >
                                    Confirm & Submit <CheckCircle size={18} />
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};