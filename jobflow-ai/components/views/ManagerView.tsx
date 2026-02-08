import React from 'react';
import { MoreVertical } from 'lucide-react';
import { Application } from '../../types';
import { MOCK_JOBS } from '../../constants';
import { Badge } from '../common/Badge';

export const ManagerView = ({ apps }: { apps: Application[] }) => {
    return (
        <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white rounded-[32px] border border-slate-100 shadow-sm overflow-hidden">
                <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                    <div>
                        <h3 className="text-xl font-bold text-slate-800">Application Track Board</h3>
                        <p className="text-sm font-medium text-slate-400">Manage and track all your active applications</p>
                    </div>
                    <div className="flex gap-3">
                        <button className="px-4 py-2 bg-white border border-slate-200 text-slate-600 font-bold rounded-xl text-sm hover:bg-slate-50 shadow-sm">Export CSV</button>
                        <button className="px-4 py-2 bg-blue-600 text-white font-bold rounded-xl text-sm shadow-lg shadow-blue-100 hover:bg-blue-700">Add Manual</button>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-slate-50/50">
                            <tr>
                                <th className="px-8 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-widest">Company</th>
                                <th className="px-8 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-widest">Role</th>
                                <th className="px-8 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-widest">Status</th>
                                <th className="px-8 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-widest">Applied</th>
                                <th className="px-8 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-widest text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {apps.map((app) => {
                                const job = MOCK_JOBS.find(j => j.id === app.jobId);
                                return (
                                    <tr key={app.id} className="hover:bg-slate-50/50 transition-colors group">
                                        <td className="px-8 py-5">
                                            <div className="flex items-center gap-3">
                                                <img src={job?.logo} className="w-10 h-10 rounded-xl border border-slate-100 shadow-sm" />
                                                <span className="font-bold text-slate-700">{job?.company}</span>
                                            </div>
                                        </td>
                                        <td className="px-8 py-5">
                                            <span className="font-medium text-slate-600">{job?.position}</span>
                                        </td>
                                        <td className="px-8 py-5">
                                            <Badge status={app.status} />
                                        </td>
                                        <td className="px-8 py-5 text-sm font-bold text-slate-500">{app.appliedDate || 'Not sent'}</td>
                                        <td className="px-8 py-5 text-right">
                                            <button className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all opacity-0 group-hover:opacity-100">
                                                <MoreVertical size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
