import React from 'react';
import { Github, Globe, Mail, Zap, Plus, Code, ArrowUpRight } from 'lucide-react';
import { MOCK_USER } from '../../constants';

export const ProfileView = () => {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in slide-in-from-bottom-4 duration-500">
            <div className="lg:col-span-1 space-y-6">
                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm text-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-br from-blue-500 to-purple-600"></div>
                    <div className="relative z-10 mt-12">
                        <img src="https://picsum.photos/id/1012/128/128" className="w-32 h-32 rounded-[32px] border-4 border-white shadow-2xl mx-auto mb-6" />
                        <h2 className="text-2xl font-bold text-slate-800">{MOCK_USER.name}</h2>
                        <p className="text-slate-500 font-medium mb-6">{MOCK_USER.title}</p>
                        <div className="flex justify-center gap-3 mb-8">
                            <button className="p-3 bg-slate-50 text-slate-600 rounded-2xl hover:bg-slate-100 hover:text-blue-600 transition-colors"><Github size={20} /></button>
                            <button className="p-3 bg-slate-50 text-slate-600 rounded-2xl hover:bg-slate-100 hover:text-blue-600 transition-colors"><Globe size={20} /></button>
                            <button className="p-3 bg-slate-50 text-slate-600 rounded-2xl hover:bg-slate-100 hover:text-blue-600 transition-colors"><Mail size={20} /></button>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-left">
                            <div className="p-4 bg-slate-50 rounded-2xl">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Experience</p>
                                <p className="font-bold text-slate-700">{MOCK_USER.experience}</p>
                            </div>
                            <div className="p-4 bg-slate-50 rounded-2xl">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Projects</p>
                                <p className="font-bold text-slate-700">{MOCK_USER.projects.length}</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                    <h4 className="font-bold text-slate-800 mb-6 flex items-center gap-2">
                        <Zap size={18} className="text-yellow-500" /> Top Skills
                    </h4>
                    <div className="space-y-4">
                        {MOCK_USER.skills.map(skill => (
                            <div key={skill.name}>
                                <div className="flex justify-between text-sm font-bold mb-2">
                                    <span className="text-slate-600">{skill.name}</span>
                                    <span className="text-blue-600">{skill.level}%</span>
                                </div>
                                <div className="w-full bg-slate-50 h-2 rounded-full overflow-hidden">
                                    <div className="bg-blue-600 h-full rounded-full transition-all duration-1000" style={{ width: `${skill.level}%` }}></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="lg:col-span-2 space-y-6">
                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-xl font-bold text-slate-800">Featured Projects</h3>
                        <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors"><Plus size={24} /></button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {MOCK_USER.projects.map((project, i) => (
                            <div key={i} className="group p-6 rounded-[24px] border border-slate-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all cursor-pointer">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center">
                                        <Code size={24} />
                                    </div>
                                    <ArrowUpRight size={20} className="text-slate-300 group-hover:text-blue-600 transition-colors transform group-hover:translate-x-1 group-hover:-translate-y-1" />
                                </div>
                                <h4 className="font-bold text-lg text-slate-800 mb-2">{project.name}</h4>
                                <p className="text-sm text-slate-500 mb-4 line-clamp-2">{project.description}</p>
                                <div className="flex flex-wrap gap-2">
                                    {project.tech.map(t => (
                                        <span key={t} className="px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-[10px] font-bold text-slate-600">{t}</span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
