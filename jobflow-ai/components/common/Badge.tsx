import React from 'react';
import { AppStatus } from '../../types';
import { STATUS_COLORS } from '../../constants';

export const Badge = ({ status }: { status: AppStatus }) => (
    <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-sm border ${STATUS_COLORS[status]}`}>
        {status}
    </span>
);
