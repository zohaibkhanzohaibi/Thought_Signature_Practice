import React from 'react';
import { Info } from 'lucide-react';

export const AIInfo = ({ text }: { text: string }) => (
    <div className="group relative inline-block ml-1 align-middle">
        <Info size={14} className="text-blue-400 cursor-help" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-3 bg-slate-800 text-white text-[10px] rounded-xl shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-50 transform group-hover:translate-y-0 translate-y-2">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-800"></div>
        </div>
    </div>
);
