import React from 'react';
import { Search, Sun, Moon, Bell } from 'lucide-react';
import { MOCK_USER } from '../../constants';

export const Header = ({ darkMode, setDarkMode }: { darkMode: boolean; setDarkMode: (d: boolean) => void }) => {
    return (
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-10">
            <div className="flex-1 max-w-xl">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search jobs, applications, or companies..."
                        className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-transparent rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white focus:border-blue-500 outline-none transition-all"
                    />
                </div>
            </div>
            <div className="flex items-center gap-4 ml-8">
                <button onClick={() => setDarkMode(!darkMode)} className="p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
                    {darkMode ? <Sun size={20} /> : <Moon size={20} />}
                </button>
                <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors relative">
                    <Bell size={20} />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 border-2 border-white rounded-full"></span>
                </button>
                <div className="h-8 w-px bg-slate-200 mx-2"></div>
                <div className="flex items-center gap-3">
                    <div className="text-right hidden sm:block">
                        <p className="text-sm font-bold text-slate-800 leading-none mb-1">{MOCK_USER.name}</p>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{MOCK_USER.title}</p>
                    </div>
                    <img src="https://picsum.photos/id/1012/64/64" className="w-10 h-10 rounded-xl border-2 border-white shadow-sm" alt="User avatar" />
                </div>
            </div>
        </header>
    );
};
