import React from 'react';
import { RiskLevel } from '@/types/compliance';

interface RiskBadgeProps {
    level: RiskLevel | string;
}

const RiskBadge: React.FC<RiskBadgeProps> = ({ level }) => {
    const getColors = (l: string) => {
        switch (l.toLowerCase()) {
            case 'low':
                return 'bg-emerald-100 text-emerald-700 border-emerald-200';
            case 'medium':
                return 'bg-amber-100 text-amber-700 border-amber-200';
            case 'high':
                return 'bg-rose-100 text-rose-700 border-rose-200';
            case 'critical':
                return 'bg-red-100 text-red-800 border-red-300 font-bold';
            default:
                return 'bg-gray-100 text-gray-700 border-gray-200';
        }
    };

    return (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getColors(level)} capitalize`}>
            {level} Risk
        </span>
    );
};

export default RiskBadge;
