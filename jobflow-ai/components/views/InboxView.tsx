import React from 'react';
import { Mail } from 'lucide-react';

export const InboxView = () => (
    <div className="h-[600px] flex flex-col items-center justify-center text-slate-400">
        <div className="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mb-6">
            <Mail size={40} className="text-slate-300" />
        </div>
        <h3 className="text-xl font-bold text-slate-600 mb-2">Message Hub</h3>
        <p className="max-w-xs text-center">Combine your Gmail and LinkedIn messages here with AI-powered auto-responses.</p>
    </div>
);
