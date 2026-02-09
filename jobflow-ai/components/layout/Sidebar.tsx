import React from 'react';
import {
    LayoutDashboard,
    User,
    Layers,
    Mail,
    BarChart2,
    Settings,
    Search,
    LogIn
} from 'lucide-react';
import { ViewType } from '../../types';

export const Sidebar = ({ currentView, setView, onLogout }: { currentView: ViewType; setView: (v: ViewType) => void, onLogout: () => void }) => {
    const menuItems = [
        { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { id: 'discovery', icon: Search, label: 'Job Discovery' },
        { id: 'manager', icon: Layers, label: 'Applications' },
        { id: 'inbox', icon: Mail, label: 'Inbox', badge: '' },
        { id: 'profile', icon: User, label: 'Profile' },
        { id: 'analytics', icon: BarChart2, label: 'Analytics' },
        { id: 'settings', icon: Settings, label: 'Settings' },
    ];

    return (
        <div className="w-64 bg-white border-r border-slate-200 h-screen flex flex-col sticky top-0">
            <div className="p-6 flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">J</div>
                <span className="text-xl font-bold text-slate-800 tracking-tight">JobFlow AI</span>
            </div>
            <nav className="flex-1 px-4 py-4 space-y-1">
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => setView(item.id as ViewType)}
                        className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all ${currentView === item.id
                                ? 'bg-blue-50 text-blue-600 font-medium'
                                : 'text-slate-500 hover:bg-slate-50'
                            }`}
                    >
                        <div className="flex items-center gap-3">
                            <item.icon size={20} />
                            <span>{item.label}</span>
                        </div>
                        {item.badge && (
                            <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                                {item.badge}
                            </span>
                        )}
                    </button>
                ))}
            </nav>
            <div className="p-4 mt-auto">
                <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 mb-4">
                    <p className="text-xs font-semibold text-slate-400 uppercase mb-2 tracking-widest">Pro Plan</p>
                    <p className="text-sm font-medium text-slate-700 mb-3 leading-snug">Get unlimited AI application boosts</p>
                    <button className="w-full bg-blue-600 text-white text-xs font-bold py-2.5 rounded-lg hover:bg-blue-700 transition-colors shadow-lg shadow-blue-100">
                        Upgrade
                    </button>
                </div>
                <button
                    onClick={onLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all text-sm font-medium"
                >
                    <LogIn size={20} className="rotate-180" /> Logout
                </button>
            </div>
        </div>
    );
};
