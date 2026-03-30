// src/components/common/CandidateStatusModal.tsx

import React, { useState, useEffect, useMemo } from 'react';
import { Loader2, XCircle, Send, Users, AlertTriangle, Check } from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import { useToast } from '../../context/ModalContext'; // For internal error messages
import type { Candidate, CandidateStatus } from '../../api/recruitmentApi'; 

interface CandidateStatusModalProps {
    isOpen: boolean;
    candidate: Candidate;
    onClose: () => void;
    // onStatusUpdate is passed up to the parent component (JobRecruitmentContent) to perform the API call
    onStatusUpdate: (candidateId: string, newStatus: CandidateStatus, reason: string) => Promise<void>; 
    isProcessing: boolean;
}

const CandidateStatusModal: React.FC<CandidateStatusModalProps> = ({ 
    isOpen, candidate, onClose, onStatusUpdate, isProcessing 
}) => {
    const { showToast } = useToast();
    const [reason, setReason] = useState('');
    const [statusToConfirm, setStatusToConfirm] = useState<CandidateStatus | null>(null);
    
    // Reset state when opening a new modal
    useEffect(() => {
        if(isOpen) {
            setReason('');
            setStatusToConfirm(null);
        }
    }, [isOpen, candidate.profile_id]);

    const isShowingConfirmation = statusToConfirm !== null;
    const currentStatus = candidate.round_status;

    const allStatuses: { value: CandidateStatus, label: string, color: string, icon: React.ElementType }[] = useMemo(() => [
        { value: 'shortlisted', label: 'Move to Next Round', color: 'bg-green-600 hover:bg-green-700', icon: Users },
        { value: 'under_review', label: 'Mark Under Review', color: 'bg-yellow-600 hover:bg-yellow-700', icon: AlertTriangle },
        { value: 'rejected', label: 'Reject Candidate', color: 'bg-red-600 hover:bg-red-700', icon: XCircle },
    ], []);

    const allowedTransitions: CandidateStatus[] = useMemo(() => {
        if (currentStatus === 'shortlisted') return ['rejected'];
        if (currentStatus === 'rejected') return ['shortlisted'];
        if (currentStatus === 'under_review') return ['shortlisted', 'rejected'];
        return ['shortlisted', 'under_review', 'rejected'];
    }, [currentStatus]);

    if (!isOpen) return null;
    
    const displayStatuses = allStatuses
        .map(status => {
            const isCurrent = status.value === currentStatus;
            const isAllowed = allowedTransitions.includes(status.value) || isCurrent;
            
            return isAllowed ? { ...status, current: isCurrent } : null;
        })
        .filter((status): status is typeof allStatuses[0] & { current: boolean } => status !== null);

    const getConfirmButtonLabel = (status: CandidateStatus) => {
        const labelMap: Record<CandidateStatus, string> = {
            'shortlisted': 'Confirm Move to Next Round',
            'under_review': 'Confirm Under Review',
            'rejected': 'Confirm Rejection',
        };
        return labelMap[status] || 'Confirm Status Change';
    };

    const handleConfirmUpdate = (e: React.MouseEvent) => {
        e.preventDefault(); 
        
        if (isProcessing) {
             return; 
        }
        
        if (!reason.trim() || !statusToConfirm) {
            showToast(`A reason is required to confirm the status change to '${getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}'.`, 'warning');
            return;
        }
        onStatusUpdate(candidate.profile_id, statusToConfirm, reason);
    }

return (
        <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm transform transition-all duration-300 scale-100 opacity-100" onClick={(e) => e.stopPropagation()}>
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4 border-b pb-3">
                        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Send size={20} className="text-blue-600"/> Update Candidate Status</h3>
                        <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-gray-100"><XCircle size={20} /></button>
                    </div>

                    <p className="text-sm text-gray-600 mb-6">
                        Candidate: <strong className="text-blue-600">{candidate.candidate_name}</strong>
                        <span className="block text-xs mt-1">Current Round: <strong className="font-medium text-gray-800">{candidate.round_name}</strong> | Status: <strong className={clsx("font-medium", {
                            'text-green-600': currentStatus === 'shortlisted',
                            'text-yellow-600': currentStatus === 'under_review',
                            'text-red-600': currentStatus === 'rejected',
                            'text-gray-600': currentStatus === 'interview_scheduled'
                        })}>{currentStatus.replace('_', ' ')}</strong></span>
                    </p>

                    {!isShowingConfirmation ? (
                        <div className="space-y-3">
                            {displayStatuses.map(status => {
                                const Icon = status.icon;
                                
                                return (
                                    <Button
                                        key={status.value}
                                        type="button"
                                        onClick={() => {
                                            setReason(''); 
                                            setStatusToConfirm(status.value);
                                        }}
                                        disabled={isProcessing || status.current} 
                                        className={clsx("w-full py-3 text-white flex items-center justify-center gap-2 font-semibold", status.color, { 'opacity-60 cursor-default': status.current })}
                                    >
                                        {isProcessing && !status.current ? (
                                            <Loader2 size={16} className="animate-spin" />
                                        ) : (
                                            <>
                                                <Icon size={18} />
                                                {status.label}
                                            </>
                                        )}
                                        {status.current && <span className="ml-2 text-xs bg-white/30 px-2 py-0.5 rounded-full">(Current)</span>}
                                    </Button>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-sm font-bold text-gray-700">
                                Reason for <span className={clsx('font-bold', { 
                                    'text-green-600': statusToConfirm === 'shortlisted', 
                                    'text-red-600': statusToConfirm === 'rejected', 
                                    'text-yellow-600': statusToConfirm === 'under_review' 
                                })}>
                                    {getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}
                                </span> *
                            </p>
                            <textarea
                                rows={3}
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                placeholder={`Enter the justification for '${getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}'`}
                                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm"
                            />
                            <Button
                                onClick={handleConfirmUpdate} 
                                disabled={isProcessing || !reason.trim()}
                                className={clsx("w-full py-3 text-white font-semibold flex items-center justify-center gap-2", { 
                                    'bg-green-600 hover:bg-green-700': statusToConfirm === 'shortlisted',
                                    'bg-red-600 hover:bg-red-700': statusToConfirm === 'rejected',
                                    'bg-yellow-600 hover:bg-yellow-700': statusToConfirm === 'under_review',
                                    'bg-gray-400': isProcessing || !reason.trim()
                                })}
                            >
                                {isProcessing ? <Loader2 size={16} className="animate-spin mr-2" /> : <Check size={18} className="mr-1"/>} 
                                {isProcessing ? 'Updating...' : getConfirmButtonLabel(statusToConfirm!)}
                            </Button>

                            <div className="flex justify-between items-center pt-2">
                                <button
                                    type="button"
                                    onClick={() => setStatusToConfirm(null)}
                                    className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                                >
                                    Back to Status
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CandidateStatusModal;