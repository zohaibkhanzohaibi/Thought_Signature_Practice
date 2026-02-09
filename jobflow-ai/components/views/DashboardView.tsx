import React from 'react';
import {
    Briefcase,
    ArrowUpRight,
    MessageSquare,
    Clock,
    Github,
    CheckCircle,
    Plus,
    Filter,
    ChevronRight
} from 'lucide-react';
import { AppStatus, Application } from '../../types';
import { MOCK_JOBS } from '../../constants';

export const DashboardView = ({ apps, onAdd }: { apps: Application[]; onAdd: () => void }) => {
    const metrics = [
        { label: 'Total Applications', value: 42, trend: '+12%', icon: Briefcase, color: 'text-blue-600', bg: 'bg-blue-100' },
        { label: 'Response Rate', value: '28%', trend: '+4%', icon: ArrowUpRight, color: 'text-green-600', bg: 'bg-green-100' },
        { label: 'Interview Rate', value: '12%', trend: '-2%', icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-100' },
        { label: 'Active Drafts', value: 5, trend: '+1', icon: Clock, color: 'text-amber-600', bg: 'bg-amber-100' },
    ];

    const columns = [
        { id: AppStatus.DRAFT, count: apps.filter(a => a.status === AppStatus.DRAFT).length },
        { id: AppStatus.SENT, count: apps.filter(a => a.status === AppStatus.SENT).length },
        { id: AppStatus.UNDER_REVIEW, count: apps.filter(a => a.status === AppStatus.UNDER_REVIEW).length },
        { id: AppStatus.INTERVIEW, count: apps.filter(a => a.status === AppStatus.INTERVIEW).length },
        { id: AppStatus.OFFER, count: apps.filter(a => a.status === AppStatus.OFFER).length },
        { id: AppStatus.REJECTED, count: apps.filter(a => a.status === AppStatus.REJECTED).length },
    ];

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {metrics.map((m, idx) => (
                    <div key={idx} className="bg-white p-6 rounded-[32px] border border-slate-100 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all">
                        <div className="flex justify-between items-start mb-4">
                            <div className={`p-3 rounded-2xl ${m.bg} ${m.color}`}>
                                <m.icon size={20} />
                            </div>
                            <span className={`text-xs font-bold px-2 py-1 rounded-lg bg-slate-50 ${m.trend.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>
                                {m.trend}
                            </span>
                        </div>
                        <h3 className="text-3xl font-bold text-slate-800 tracking-tight">{m.value}</h3>
                        <p className="text-sm font-medium text-slate-400 mt-1">{m.label}</p>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Left: Quick Actions & Profile */}
                <div className="space-y-6">
                    <div className="bg-white rounded-[32px] p-6 border border-slate-100 shadow-sm">
                        <div className="flex justify-between items-center mb-6">
                            <h4 className="font-bold text-slate-800">Profile Completion</h4>
                            <span className="text-sm font-bold text-blue-600">85%</span>
                        </div>
                        <div className="w-full bg-slate-50 h-2.5 rounded-full overflow-hidden mb-6">
                            <div className="bg-blue-600 h-full rounded-full w-[85%]"></div>
                        </div>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100">
                                <div className="flex items-center gap-3">
                                    <Github size={18} className="text-slate-700" />
                                    <span className="text-sm font-semibold text-slate-600">GitHub Active Sync</span>
                                </div>
                                <div className="w-8 h-8 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                                    <CheckCircle size={16} />
                                </div>
                            </div>
                            <button onClick={onAdd} className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white font-bold py-4 rounded-2xl shadow-xl shadow-blue-100 hover:bg-blue-700 hover:shadow-blue-200 transition-all">
                                <Plus size={20} />
                                <span>Track New Job</span>
                            </button>
                        </div>
                    </div>

                    <div className="bg-white rounded-[32px] p-6 border border-slate-100 shadow-sm">
                        <h4 className="font-bold text-slate-800 mb-6">Career Timeline</h4>
                        <div className="space-y-6 relative ml-2">
                            <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-slate-100"></div>
                            {[
                                { title: 'Interview with StartupXYZ', time: '2h ago', status: 'interview' },
                                { title: 'Applied to TechCorp', time: '1d ago', status: 'applied' },
                                { title: 'Profile Updated', time: '3d ago', status: 'update' }
                            ].map((item, i) => (
                                <div key={i} className="flex gap-4 relative z-10">
                                    <div className={`w-4 h-4 rounded-full border-2 border-white shadow-sm mt-1 flex-shrink-0 ${item.status === 'interview' ? 'bg-purple-500' : item.status === 'applied' ? 'bg-blue-500' : 'bg-slate-300'
                                        }`}></div>
                                    <div>
                                        <p className="text-sm font-bold text-slate-700 leading-tight mb-1">{item.title}</p>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{item.time}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right: Kanban/Pipeline */}
                <div className="xl:col-span-2 space-y-4">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="font-bold text-slate-800 text-lg">Hiring Pipeline</h4>
                        <div className="flex items-center gap-2">
                            <button className="text-xs font-bold text-slate-400 hover:text-blue-600 flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-lg border border-slate-100 shadow-sm transition-colors">
                                <Filter size={14} /> View Filter
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                        {columns.map(col => (
                            <div key={col.id} className="flex flex-col gap-3">
                                <div className="flex items-center justify-between px-2">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{col.id}</span>
                                    <span className="bg-slate-100 text-slate-500 text-[10px] px-1.5 py-0.5 rounded-md font-bold border border-slate-200">{col.count}</span>
                                </div>
                                <div className="kanban-column bg-slate-100/30 p-2 rounded-[24px] border border-slate-200/50 space-y-3">
                                    {apps.filter(a => a.status === col.id).map(app => {
                                        const job = MOCK_JOBS.find(j => j.id === app.jobId);
                                        return (
                                            <div key={app.id} className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 hover:border-blue-400 hover:shadow-lg cursor-grab active:cursor-grabbing transition-all group">
                                                <div className="flex items-center gap-2 mb-3">
                                                    <img src={job?.logo} className="w-6 h-6 rounded-md border border-slate-100" />
                                                    <p className="text-[10px] font-bold text-slate-400 uppercase truncate max-w-[80px]">{job?.company}</p>
                                                </div>
                                                <h5 className="text-xs font-bold text-slate-800 mb-4 line-clamp-2 leading-snug">{job?.position}</h5>
                                                <div className="flex items-center justify-between mt-auto">
                                                    <div className="flex items-center gap-1 text-[9px] text-slate-400 font-bold">
                                                        <Clock size={10} />
                                                        <span>3D</span>
                                                    </div>
                                                    <ChevronRight size={14} className="text-slate-300 group-hover:text-blue-500 transition-colors" />
                                                </div>
                                            </div>
                                        );
                                    })}
                                    {apps.filter(a => a.status === col.id).length === 0 && (
                                        <div className="h-24 flex items-center justify-center border-2 border-dashed border-slate-200 rounded-2xl">
                                            <span className="text-[10px] font-bold text-slate-300 uppercase">Empty</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
