// src/components/common/RoundStats.tsx
import React from 'react';
import { Users, CheckCircle, TrendingUp, XCircle } from 'lucide-react';
import clsx from 'clsx';
import type { RoundOverview } from '../../api/recruitmentApi';

interface RoundStatsProps {
    round: RoundOverview;
}

const StatItem: React.FC<{ label: string; value: number; icon: React.ElementType; color: string }> = ({ label, value, icon: Icon, color }) => (
    <div className="flex items-center gap-3">
        <div className={clsx("w-10 h-10 rounded-full flex items-center justify-center", color.replace('text-', 'bg-').replace('-600', '-100').replace('-700', '-100'))}>
            <Icon size={18} className={color} />
        </div>
        <div>
            <div className="text-xs font-medium text-gray-500">{label}</div>
            <div className="text-xl font-bold text-gray-900">{value}</div>
        </div>
    </div>
);

const RoundStats: React.FC<RoundStatsProps> = ({ round }) => (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <StatItem label="Total Candidates" value={round.total_candidates} icon={Users} color="text-gray-700" />
        <StatItem label="Shortlisted" value={round.shortlisted} icon={CheckCircle} color="text-green-600" />
        <StatItem label="Under Review" value={round.under_review} icon={TrendingUp} color="text-yellow-600" />
        <StatItem label="Rejected" value={round.rejected} icon={XCircle} color="text-red-600" />
    </div>
);

export default RoundStats;