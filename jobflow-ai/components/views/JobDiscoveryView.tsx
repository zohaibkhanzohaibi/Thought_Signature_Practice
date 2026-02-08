import React, { useState } from 'react';
import { Search, Filter, ArrowUpRight, ExternalLink, MoreVertical } from 'lucide-react';
import { Job } from '../../types';
import { MOCK_JOBS } from '../../constants';
import { AIInfo } from '../common/AIInfo';

export const JobDiscoveryView = ({ onApply }: { onApply: (job: Job) => void }) => {
    const [selectedJob, setSelectedJob] = useState<Job | null>(MOCK_JOBS[0]);

    return (
        <div className="flex h-[calc(100vh-140px)] gap-6 animate-in slide-in-from-bottom-4 duration-500">
            {/* Filters (Simplified for this version) */}
            <div className="w-64 flex-shrink-0 bg-white border border-slate-200 rounded-[32px] p-8 hidden lg:block overflow-y-auto shadow-sm">
                <h4 className="font-bold text-slate-800 mb-8">Refine Search</h4>
                <div className="space-y-8">
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 block">Job Type</label>
                        <div className="space-y-3">
                            {['Full-time', 'Contract', 'Remote'].map(t => (
                                <label key={t} className="flex items-center gap-3 text-sm font-medium text-slate-600 cursor-pointer hover:text-blue-600 transition-colors">
                                    <input type="checkbox" className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 transition-all" />
                                    {t}
                                </label>
                            ))}
                        </div>
                    </div>
                    <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 block">Match Level</label>
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold text-slate-400">75%</span>
                            <span className="text-[10px] font-bold text-blue-600">100%</span>
                        </div>
                        <input type="range" className="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" />
                    </div>
                </div>
            </div>

            <div className="flex-1 flex flex-col gap-6 overflow-hidden">
                <div className="bg-white border border-slate-200 rounded-[24px] p-4 flex items-center gap-4 shadow-sm">
                    <div className="flex-1 relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input type="text" placeholder="Search by title, stack, or company..." className="w-full pl-12 pr-4 py-3 bg-slate-50 border-transparent rounded-2xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition-all" />
                    </div>
                    <button className="flex items-center gap-2 px-5 py-3 bg-slate-50 hover:bg-slate-100 rounded-2xl text-sm font-bold text-slate-600 transition-colors">
                        <Filter size={18} /> Filters
                    </button>
                </div>

                <div className="flex-1 flex gap-6 overflow-hidden">
                    <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                        {MOCK_JOBS.map(job => (
                            <div
                                key={job.id}
                                onClick={() => setSelectedJob(job)}
                                className={`p-6 rounded-[32px] border transition-all cursor-pointer relative overflow-hidden ${selectedJob?.id === job.id
                                        ? 'border-blue-600 ring-4 ring-blue-50 bg-blue-50/20'
                                        : 'bg-white border-slate-100 hover:border-slate-300 hover:shadow-lg'
                                    }`}
                            >
                                {selectedJob?.id === job.id && <div className="absolute top-0 right-0 w-24 h-24 bg-blue-600/5 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2"></div>}

                                <div className="flex justify-between items-start mb-4 relative z-10">
                                    <div className="flex gap-4">
                                        <img src={job.logo} className="w-14 h-14 rounded-2xl shadow-sm border border-slate-100" />
                                        <div>
                                            <h4 className="font-bold text-slate-800 text-xl leading-tight mb-1">{job.position}</h4>
                                            <p className="text-sm font-semibold text-slate-500">{job.company} • {job.location}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="inline-flex items-center px-3 py-1.5 rounded-xl bg-blue-50 text-blue-700 text-[10px] font-bold border border-blue-100 shadow-sm">
                                            {job.matchScore}% MATCH <AIInfo text="Our AI verified your skills match this role's tech stack and experience requirements." />
                                        </div>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2 mb-6 relative z-10">
                                    {job.techStack.map(t => (
                                        <span key={t} className="px-3 py-1.5 bg-slate-50 text-slate-600 rounded-xl text-[10px] font-bold border border-slate-100">{t}</span>
                                    ))}
                                </div>
                                <div className="flex justify-between items-center pt-5 border-t border-slate-100 relative z-10">
                                    <p className="text-lg font-bold text-slate-800">{job.salary}</p>
                                    <div className="flex items-center gap-3">
                                        <button className="px-4 py-2.5 text-xs font-bold text-slate-400 hover:bg-slate-50 rounded-xl transition-colors">Save Job</button>
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onApply(job); }}
                                            className="px-6 py-2.5 bg-blue-600 text-white text-xs font-bold rounded-xl shadow-xl shadow-blue-100 hover:bg-blue-700 hover:shadow-blue-200 transition-all"
                                        >
                                            Auto-Apply
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {selectedJob && (
                        <div className="w-[500px] bg-white border border-slate-200 rounded-[32px] overflow-hidden flex flex-col hidden xl:flex shadow-xl">
                            <div className="p-8 border-b border-slate-100 bg-slate-50/50">
                                <div className="flex items-center justify-between mb-8">
                                    <img src={selectedJob.logo} className="w-20 h-20 rounded-[28px] border-4 border-white shadow-xl" />
                                    <div className="flex gap-3">
                                        <button className="p-3 bg-white text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all shadow-sm"><ExternalLink size={20} /></button>
                                        <button className="p-3 bg-white text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all shadow-sm"><MoreVertical size={20} /></button>
                                    </div>
                                </div>
                                <h3 className="text-2xl font-bold text-slate-800 leading-tight mb-2 tracking-tight">{selectedJob.position}</h3>
                                <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">{selectedJob.company} • {selectedJob.location}</p>
                            </div>
                            <div className="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
                                <div>
                                    <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4">The Opportunity</h4>
                                    <p className="text-base text-slate-600 leading-relaxed font-medium">{selectedJob.description}</p>
                                </div>
                                <div className="p-8 bg-blue-600 rounded-[32px] text-white shadow-2xl shadow-blue-200 relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 group-hover:scale-150 transition-transform duration-700"></div>
                                    <div className="flex items-center gap-3 mb-4">
                                        <ArrowUpRight className="text-blue-200" size={24} />
                                        <h5 className="font-bold text-xl">AI Application Boost</h5>
                                    </div>
                                    <p className="text-sm text-blue-100 leading-relaxed mb-8 font-medium">
                                        We've matched your <strong>React</strong> and <strong>Node.js</strong> projects with their platform goals. Applying now increases your response chance by 40%.
                                    </p>
                                    <button
                                        onClick={() => onApply(selectedJob)}
                                        className="w-full py-4 bg-white text-blue-600 font-bold rounded-2xl shadow-xl hover:bg-blue-50 transition-all active:scale-95"
                                    >
                                        Generate Application Now
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
