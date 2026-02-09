import React, { useState } from 'react';
import { Layers, X, FileText, AlertCircle, Send, CheckCircle } from 'lucide-react';
import { Job, UserProfile, Application, AppStatus } from '../../types';
import { generateCoverLetter } from '../../geminiService';

export const GenerationModal = ({ job, user, onClose, onComplete }: {
    job: Job;
    user: UserProfile;
    onClose: () => void;
    onComplete: (app: Application) => void
}) => {
    const [generating, setGenerating] = useState(false);
    const [coverLetter, setCoverLetter] = useState('');
    const [step, setStep] = useState<'initial' | 'review'>('initial');

    const handleGenerate = async () => {
        setGenerating(true);
        const letter = await generateCoverLetter(job, user);
        setCoverLetter(letter);
        setGenerating(false);
        setStep('review');
    };

    const handleFinish = () => {
        const newApp: Application = {
            id: `a${Math.random().toString(36).substr(2, 9)}`,
            jobId: job.id,
            status: AppStatus.SENT,
            appliedDate: new Date().toISOString().split('T')[0],
            createdDate: new Date().toISOString().split('T')[0],
            lastUpdated: new Date().toISOString().split('T')[0],
            coverLetter: coverLetter,
            emailThread: []
        };
        onComplete(newApp);
    };

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
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{job.company} • {job.position}</p>
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
                                    Our AI will analyze your profile and the requirements for <span className="font-bold text-slate-700">{job.position}</span> to create a highly personalized cover letter.
                                </p>
                            </div>
                            <div className="bg-blue-50/50 p-6 rounded-[32px] border border-blue-100 flex items-start gap-4 text-left">
                                <div className="p-2 bg-blue-600 rounded-lg text-white mt-1">
                                    <AlertCircle size={16} />
                                </div>
                                <p className="text-sm text-blue-800 font-medium">
                                    We noticed your experience with <strong>React</strong> and <strong>TypeScript</strong> perfectly aligns with this role's core requirements.
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
