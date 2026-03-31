import React, { useEffect, useMemo, useState } from 'react';
import { Calendar, Clock, Loader2, XCircle, RefreshCw } from 'lucide-react';
import Button from './Button';
import { useToast } from '../../context/ModalContext';
import type { Candidate, RescheduleInterviewData, ScheduledInterview } from '../../api/recruitmentApi';

export interface RescheduleModalData {
    candidate: Candidate;
    jobId: string;
    roundId: string;
    scheduledInterview: ScheduledInterview;
}

interface RescheduleInterviewModalProps {
    isOpen: boolean;
    data: RescheduleModalData;
    onClose: () => void;
    onReschedule: (payload: RescheduleInterviewData) => Promise<void>;
    isRescheduling: boolean;
}

const getLocalInputParts = (isoString?: string) => {
    const now = new Date();
    const tomorrow = new Date(now.getTime());
    tomorrow.setDate(now.getDate() + 1);

    const fallbackDate = tomorrow.toISOString().substring(0, 10);
    const fallbackTime = '10:00';

    if (!isoString) {
        return { date: fallbackDate, time: fallbackTime };
    }

    const parsed = new Date(isoString);
    if (Number.isNaN(parsed.getTime())) {
        return { date: fallbackDate, time: fallbackTime };
    }

    const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000);
    return {
        date: local.toISOString().substring(0, 10),
        time: local.toISOString().substring(11, 16),
    };
};

const formatScheduleLabel = (isoString?: string) => {
    if (!isoString) return 'Not scheduled';
    const parsed = new Date(isoString);
    if (Number.isNaN(parsed.getTime())) return isoString;

    return parsed.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
};

const RescheduleInterviewModal: React.FC<RescheduleInterviewModalProps> = ({
    isOpen,
    data,
    onClose,
    onReschedule,
    isRescheduling,
}) => {
    const { showToast } = useToast();
    const [interviewDate, setInterviewDate] = useState('');
    const [interviewTime, setInterviewTime] = useState('');
    const [reason, setReason] = useState('');

    const scheduleLabel = useMemo(
        () => formatScheduleLabel(data?.scheduledInterview?.scheduled_datetime),
        [data]
    );

    useEffect(() => {
        if (isOpen) {
            const parts = getLocalInputParts(data?.scheduledInterview?.scheduled_datetime);
            setInterviewDate(parts.date);
            setInterviewTime(parts.time);
            setReason('');
        }
    }, [isOpen, data]);

    if (!isOpen) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (!interviewDate || !interviewTime) {
            showToast('Please select a valid date and time.', 'warning');
            return;
        }

        const payload: RescheduleInterviewData = {
            interview_date: interviewDate,
            interview_time: `${interviewTime}:00`,
            reason: reason.trim() || undefined,
        };

        if (data.scheduledInterview?.interview_token) {
            payload.interview_token = data.scheduledInterview.interview_token;
        } else {
            payload.job_id = data.jobId;
            payload.profile_id = data.candidate.profile_id;
            payload.round_id = data.roundId;
        }

        onReschedule(payload);
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
            <div
                className="bg-white rounded-xl shadow-2xl w-full max-w-md transform transition-all duration-300 scale-100 opacity-100"
                onClick={(e) => e.stopPropagation()}
            >
                <form onSubmit={handleSubmit}>
                    <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                        <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <RefreshCw size={18} className="text-indigo-600" />
                            Reschedule Interview
                        </h3>
                        <button
                            type="button"
                            onClick={onClose}
                            className="p-2 rounded-full text-gray-400 hover:bg-gray-100"
                        >
                            <XCircle size={20} />
                        </button>
                    </div>

                    <div className="p-6 space-y-5">
                        <div className="text-sm text-gray-600">
                            Candidate: <span className="font-semibold text-gray-900">{data.candidate.candidate_name}</span>
                            <div className="text-xs text-gray-500 mt-1">Current schedule: {scheduleLabel}</div>
                        </div>

                        <div className="grid grid-cols-1 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                                    <Calendar size={14} /> New Date
                                </label>
                                <input
                                    type="date"
                                    value={interviewDate}
                                    onChange={(e) => setInterviewDate(e.target.value)}
                                    min={new Date().toISOString().substring(0, 10)}
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                                    <Clock size={14} /> New Time
                                </label>
                                <input
                                    type="time"
                                    value={interviewTime}
                                    onChange={(e) => setInterviewTime(e.target.value)}
                                    step="300"
                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                    required
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
                            <textarea
                                rows={3}
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                placeholder="Add a reason for the reschedule"
                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-indigo-500 focus:border-indigo-500"
                            />
                        </div>

                        <Button
                            type="submit"
                            disabled={isRescheduling}
                            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white"
                        >
                            {isRescheduling ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" /> Rescheduling...
                                </>
                            ) : (
                                <>Confirm Reschedule</>
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default RescheduleInterviewModal;
