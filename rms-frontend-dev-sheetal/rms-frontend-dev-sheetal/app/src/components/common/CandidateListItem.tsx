// // src/components/common/CandidateListItem.tsx
// import React from 'react';
// import { Mail, Zap, Edit, Search } from 'lucide-react';
// import clsx from 'clsx';
// import Button from './Button';
// import type { Candidate } from '../../api/recruitmentApi';

// interface CandidateListItemProps {
//     candidate: Candidate;
//     onViewDetails: () => void;
//     onStatusChangeClick: (candidate: Candidate) => void;
// }

// const CandidateListItem: React.FC<CandidateListItemProps> = ({ 
//     candidate, 
//     onViewDetails, 
//     onStatusChangeClick 
// }) => {
//     const statusClasses = {
//         shortlisted: 'bg-green-100 text-green-700 border-green-300',
//         under_review: 'bg-yellow-100 text-yellow-700 border-yellow-300',
//         rejected: 'bg-red-100 text-red-700 border-red-300',
//     };
//     const statusText = candidate.round_status.replace('_', ' ').split(' ').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ');
//     const statusStyle = statusClasses[candidate.round_status];

//     return (
//         <div 
//             // 💡 FIX 1: Add onClick to the main div to open the details modal
//             onClick={onViewDetails} 
//             className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer"
//         >
//             <div className="flex items-center gap-4 min-w-0">
//                 <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold flex-shrink-0">
//                     {candidate.candidate_name.charAt(0).toUpperCase()}
//                 </div>
//                 <div className="min-w-0">
//                     <h5 className="text-md font-semibold text-gray-900 truncate">{candidate.candidate_name}</h5>
//                     <p className="text-sm text-gray-500 truncate flex items-center gap-1">
//                         <Mail size={12} />
//                         {candidate.candidate_email}
//                     </p>
//                 </div>
//             </div>
            
//             <div className="flex items-center gap-4 flex-shrink-0">
//                 {/* Score */}
//                 <div className="flex items-center gap-2 min-w-[70px] justify-end">
//                     <Zap size={16} className="text-amber-500" />
//                     <span className="text-lg font-bold text-gray-900">{candidate.overall_score}%</span>
//                 </div>
                
//                 {/* Status */}
//                 <div className="flex items-center gap-2">
//                     <span className={clsx("px-3 py-1 text-xs font-medium rounded-full border min-w-[100px] text-center", statusStyle)}>
//                         {statusText}
//                     </span>
                    
//                     {/* 💡 FIX 2: Add e.stopPropagation() to interactive buttons to prevent modal opening */}
//                     <button
//                         onClick={(e) => { e.stopPropagation(); onStatusChangeClick(candidate); }}
//                         className="p-1.5 rounded-full text-gray-500 hover:bg-gray-100 hover:text-blue-600 transition-colors"
//                         title="Change Candidate Status"
//                     >
//                         <Edit size={16} />
//                     </button>
//                 </div>
                
//                 {/* 💡 FIX 3: Add e.stopPropagation() to the explicit Details button */}
//                 <Button 
//                     variant="outline" 
//                     onClick={(e) => { e.stopPropagation(); onViewDetails(); }} 
//                     className="px-3 py-1.5 text-xs"
//                 >
//                     <Search size={14} /> Details
//                 </Button>
//             </div>
//         </div>
//     );
// };

// export default CandidateListItem;



// src/components/common/CandidateListItem.tsx
import React from 'react';
import { Mail, Zap, Edit, Search } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import type { Candidate } from '../../api/recruitmentApi';

interface CandidateListItemProps {
    candidate: Candidate;
    onViewDetails: () => void;
    onStatusChangeClick: (candidate: Candidate) => void;
}

const CandidateListItem: React.FC<CandidateListItemProps> = ({ 
    candidate, 
    onViewDetails, 
    onStatusChangeClick 
}) => {
    const statusClasses = {
        shortlisted: 'bg-green-100 text-green-700 border-green-300',
        under_review: 'bg-yellow-100 text-yellow-700 border-yellow-300',
        rejected: 'bg-red-100 text-red-700 border-red-300',
    };
    const statusText = candidate.round_status.replace('_', ' ').split(' ').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(' ');
    const statusStyle = statusClasses[candidate.round_status];

    return (
        <div 
            // 💡 Clicking anywhere on the row opens the details modal
            onClick={onViewDetails} 
            className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer"
        >
            <div className="flex items-center gap-4 min-w-0">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold flex-shrink-0">
                    {candidate.candidate_name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                    <h5 className="text-md font-semibold text-gray-900 truncate">{candidate.candidate_name}</h5>
                    <p className="text-sm text-gray-500 truncate flex items-center gap-1">
                        <Mail size={12} />
                        {candidate.candidate_email}
                    </p>
                </div>
            </div>
            
            <div className="flex items-center gap-4 flex-shrink-0">
                {/* Score */}
                <div className="flex items-center gap-2 min-w-[70px] justify-end">
                    <Zap size={16} className="text-amber-500" />
                    <span className="text-lg font-bold text-gray-900">{candidate.overall_score}%</span>
                </div>
                
                {/* Status */}
                <div className="flex items-center gap-2">
                    <span className={clsx("px-3 py-1 text-xs font-medium rounded-full border min-w-[100px] text-center", statusStyle)}>
                        {statusText}
                    </span>
                    
                    {/* 💡 FIX: Edit Status Button (Calls status modal function) */}
                    <button
                        onClick={(e) => { 
                            e.stopPropagation(); 
                            console.log(`[CANDIDATE LIST] Edit Status click detected for ${candidate.profile_id}`); // Debugging log
                            onStatusChangeClick(candidate); 
                        }}
                        className="p-1.5 rounded-full text-gray-500 hover:bg-gray-100 hover:text-blue-600 transition-colors"
                        title="Change Candidate Status"
                    >
                        <Edit size={16} />
                    </button>
                </div>
                
                {/* Details Button */}
                <Button 
                    variant="outline" 
                    onClick={(e) => { e.stopPropagation(); onViewDetails(); }} 
                    className="px-3 py-1.5 text-xs"
                >
                    <Search size={14} /> Details
                </Button>
            </div>
        </div>
    );
};

export default CandidateListItem;