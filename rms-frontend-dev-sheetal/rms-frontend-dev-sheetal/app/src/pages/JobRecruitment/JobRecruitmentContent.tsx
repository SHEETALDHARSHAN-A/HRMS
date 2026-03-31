// src/pages/JobRecruitment/JobRecruitmentContent.tsx

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { useToast } from '../../context/ModalContext';
import { 
    Loader2, Briefcase, ChevronDown, RefreshCw, Calendar, X,
    AlertTriangle, CheckCircle, XCircle
} from 'lucide-react';
import RoundStats from '../../components/common/Roundstats';
import CandidateListItem from '../../components/common/CandidateListItem';
import CandidateDetailModal from '../../components/common/CandidateDetailModel';
import ScheduleInterviewModal, { generateDefaultEmailContent, type JobTypeDetails, type ScheduleModalData } from '../../components/common/ScheduleInterviewModal';
import CandidateStatusModal from '../../components/common/CandidateStatusModal';
import RescheduleInterviewModal, { type RescheduleModalData } from '../../components/common/RescheduleInterviewModal';
import clsx from 'clsx';
import Button from '../../components/common/Button';

import { useRecruitmentData } from '../../hooks/useRecruitmentData';
import { patchCandidateStatus, scheduleInterview, getScheduledInterviews, rescheduleInterview } from '../../api/recruitmentApi'; 
import { getJobPostById } from '../../api/jobApi'; 
import type { Candidate, CandidateStatus, InterviewLevel, InterviewType, ScheduleInterviewData, ScheduledInterview, RescheduleInterviewData } from '../../api/recruitmentApi';


// -- MAIN JOB RECRUITMENT PAGE CONTENT COMPONENT ---
const JobRecruitmentContent: React.FC = () => {
    const {
        jobs,
        isLoading,
        expandedJobId,
        selectedRoundId,
        roundCandidates,
        candidatesLoading,
        selectedCandidate,
        setSelectedCandidate,
        handleJobToggle,
        handleRoundChange,
        fetchJobs,
    } = useRecruitmentData();

    const [statusModalCandidate, setStatusModalCandidate] = useState<Candidate | null>(null);
    const [isStatusUpdating, setIsStatusUpdating] = useState(false);
    
    const [scheduleModalData, setScheduleModalData] = useState<ScheduleModalData | null>(null);
    const [isScheduling, setIsScheduling] = useState(false);

    const [scheduledInterviews, setScheduledInterviews] = useState<ScheduledInterview[]>([]);
    const [scheduledLoading, setScheduledLoading] = useState(false);
    const [rescheduleModalData, setRescheduleModalData] = useState<RescheduleModalData | null>(null);
    const [isRescheduling, setIsRescheduling] = useState(false);

    const [lastActionMessage, setLastActionMessage] = useState<string | null>(null);
    const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
    const [actionMessageKey, setActionMessageKey] = useState(0); 
    
    const { showToast } = useToast();

    const scheduledByProfileId = useMemo(() => {
        const map = new Map<string, ScheduledInterview>();
        scheduledInterviews.forEach(interview => {
            map.set(interview.profile_id, interview);
        });
        return map;
    }, [scheduledInterviews]);

    const formatScheduleLabel = (isoString?: string) => {
        if (!isoString) return null;
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


    useEffect(() => {
        if (lastActionMessage || lastErrorMessage) {
            const timer = setTimeout(() => {
                setLastActionMessage(null);
                setLastErrorMessage(null);
            }, 5000); 
            return () => clearTimeout(timer);
        }
    }, [lastActionMessage, lastErrorMessage, actionMessageKey]);

    const fetchScheduled = useCallback(async (jobId: string, roundId: string) => {
        setScheduledLoading(true);
        try {
            const result = await getScheduledInterviews(jobId, roundId);
            if (result.success) {
                setScheduledInterviews(result.data ?? []);
            } else {
                setScheduledInterviews([]);
                showToast(result.error || 'Failed to load scheduled interviews.', 'error');
            }
        } catch (e: any) {
            setScheduledInterviews([]);
            showToast(e.message || 'Error loading scheduled interviews.', 'error');
        } finally {
            setScheduledLoading(false);
        }
    }, [showToast]);

    useEffect(() => {
        if (expandedJobId && selectedRoundId) {
            fetchScheduled(expandedJobId, selectedRoundId);
        } else {
            setScheduledInterviews([]);
        }
    }, [expandedJobId, selectedRoundId, fetchScheduled]);

    const fetchJobDetailsForModal = useCallback(async (jobId: string): Promise<JobTypeDetails | null> => {
        try {
            const result = await getJobPostById(jobId);
            if (result.success && result.data) {
                const jobPostInterviewType = result.data.interview_type || 'agent';
                const type = jobPostInterviewType as JobTypeDetails['interview_type'];
                return { interview_type: type };
            }
            return null;
        } catch (e) {
            console.error('Failed to fetch job details for scheduling:', e);
            return null;
        }
    }, []);


    // Handler for Candidate Status Update 
    const handleStatusUpdate = async (profileId: string, newStatus: CandidateStatus, reason: string) => {
        const roundId = selectedRoundId;
        const candidateName = statusModalCandidate?.candidate_name || 'Candidate';
        if (!roundId || !profileId) {
            showToast('Internal error: Missing round or profile ID.', 'error');
            return;
        }

        setIsStatusUpdating(true); 
        
        try {
            const result = await patchCandidateStatus(roundId, profileId, newStatus, reason);
            const statusLabel = newStatus.replace('_', ' ');

            if (result.success) {
               
                setLastActionMessage(`Successfully updated ${candidateName} status to ${statusLabel}. Data is refreshing...`);
                setActionMessageKey(prev => prev + 1);

                await fetchJobs();
            } else {
                setLastErrorMessage(`Failed to update status for ${candidateName}. ${result.error || ''}`);
                setActionMessageKey(prev => prev + 1);
            }
        } catch (e: any) {
             showToast(` Error updating status for ${candidateName}: ${e.message || 'Server error.'}`, 'error');
        } finally {
            setIsStatusUpdating(false); 
            setStatusModalCandidate(null);
        }
    };
    
    // Handler to open the schedule modal
    const openScheduleModal = async () => {
        if (!expandedJobId || !selectedRoundId) {
            showToast('Please select an active job and a specific round before scheduling.', 'info');
            return;
        }
        
        const shortlistedCount = roundCandidates.filter(c => c.round_status === 'shortlisted').length;
        if (shortlistedCount === 0) {
             showToast('There are no shortlisted candidates in this round to schedule interviews.', 'info');
             return;
        }

        const job = jobs.find(j => j.job_id === expandedJobId);
        const round = job?.rounds.find(r => r.round_id === selectedRoundId);

        if (job && round) {
            showToast(`Fetching job details for ${job.job_title}...`, 'info');
            const jobDetails = await fetchJobDetailsForModal(job.job_id);
            
            const jobPostInterviewType = jobDetails?.interview_type || 'agent';
            
            // Use the utility to generate the email template
            const emailContent = generateDefaultEmailContent(
                round.round_name,
                job.job_title,
                jobPostInterviewType
            );
            
            setScheduleModalData({
                jobId: job.job_id,
                jobTitle: job.job_title,
                roundId: round.round_id,
                roundName: round.round_name,
                candidates: roundCandidates, 
                jobDetails: jobDetails,
                emailTemplate: emailContent, 
            });
             showToast('Schedule configuration loaded successfully.', 'success');
        } else {
             showToast('Could not find job or round details. Please select again.', 'error');
        }
    };
    
  const handleScheduleInterview = async ({ jobId, roundId, profileIds, dateTime, level, type, emailSubject, emailBody }: { 
        jobId: string, 
        roundId: string, 
        profileIds: string[], 
        dateTime: string, 
        level: InterviewLevel, 
        type: InterviewType,
        emailSubject: string, 
        emailBody: string 
    }) => {
        setIsScheduling(true);
        

        try {
            if (!dateTime || !dateTime.includes('T')) {
                throw new Error("Invalid date time selected or format mismatch.");
            }
            
            const [interview_date, raw_time] = dateTime.split('T'); 
            const interview_time = raw_time + ':00'; 
            
            const apiType = type === 'Agent_interview' ? 'Agent_interview' : 'In_person';
            const levelOfInterview = type === 'Agent_interview' ? level.toLowerCase() : 'easy'; 

            const payload: ScheduleInterviewData = {
                job_id: jobId,
                round_id: roundId, 
                profile_id: profileIds, 
                interview_date: interview_date, 
                interview_time: interview_time, 
                interviewer_id: "", 
                interview_type: apiType as InterviewType,
                level_of_interview: levelOfInterview, 
                email_subject: emailSubject, 
                email_body: emailBody,       
            };

            const result = await scheduleInterview(payload); 

            if (result.success) {
                const candidateCount = profileIds.length;
                const currentJob = jobs.find(j => j.job_id === jobId);
                
                setLastActionMessage(`Successfully scheduled ${candidateCount} interview(s) for ${currentJob?.job_title || 'the selected job'}. Emails sent.`);
                setActionMessageKey(prev => prev + 1);
               
                if (jobId === expandedJobId && roundId === selectedRoundId) {
                    await fetchScheduled(jobId, roundId);
                }
                await fetchJobs(); 
            } else {
                showToast(result.error || 'Failed to schedule interviews.', 'error');
            }
        } catch (e: any) {
            showToast(e.message || 'Error scheduling interviews.', 'error');
        } finally {
            setIsScheduling(false);
            setScheduleModalData(null); 
        }
    };

    const openRescheduleModal = (candidate: Candidate) => {
        if (!expandedJobId || !selectedRoundId) {
            showToast('Please select a job and round before rescheduling.', 'info');
            return;
        }

        const scheduledInterview = scheduledByProfileId.get(candidate.profile_id);
        if (!scheduledInterview) {
            showToast('No scheduled interview found for this candidate.', 'info');
            return;
        }

        setRescheduleModalData({
            candidate,
            jobId: expandedJobId,
            roundId: selectedRoundId,
            scheduledInterview,
        });
    };

    const handleRescheduleInterview = async (payload: RescheduleInterviewData) => {
        if (!expandedJobId || !selectedRoundId) {
            showToast('Please select a job and round before rescheduling.', 'info');
            return;
        }

        setIsRescheduling(true);
        try {
            const result = await rescheduleInterview(payload);
            const candidateName = rescheduleModalData?.candidate.candidate_name || 'Candidate';

            if (result.success) {
                setLastActionMessage(`Successfully rescheduled interview for ${candidateName}.`);
                setActionMessageKey(prev => prev + 1);
                await fetchScheduled(expandedJobId, selectedRoundId);
            } else {
                showToast(result.error || 'Failed to reschedule interview.', 'error');
            }
        } catch (e: any) {
            showToast(e.message || 'Error rescheduling interview.', 'error');
        } finally {
            setIsRescheduling(false);
            setRescheduleModalData(null);
        }
    };

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center h-96">
                <Loader2 size={48} className="text-indigo-600 animate-spin" />
                <p className="mt-4 text-gray-500 font-medium">Loading Data...</p>
                <p className="mt-1 text-sm text-gray-400">Please wait while we fetch the latest job and candidate information.</p>
            </div>
        );
    }

    const currentJob = jobs.find(j => j.job_id === expandedJobId);
    const currentRound = currentJob?.rounds.find(r => r.round_id === selectedRoundId);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center pb-4 border-b border-gray-100">
                <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
                    <Briefcase size={24} className="text-indigo-600" />
                    Overview of Jobs with candidates
                </h1>
                <Button 
                    variant="outline" 
                    onClick={fetchJobs} 
                    disabled={isLoading}
                    className="py-2 px-4 text-sm flex items-center gap-2 text-blue-600 border-blue-300 hover:bg-blue-50"
                >
                    <RefreshCw size={16} className={clsx({ 'animate-spin': candidatesLoading || isStatusUpdating || isScheduling })} /> Refresh Data
                </Button>
            </div>

            
               {lastActionMessage && (
  <div key={actionMessageKey} className="relative z-20">
    <div className="bg-green-100 border border-green-300 text-green-800 px-6 py-4 rounded-xl shadow-md flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-300" role="status">
      <div className="flex items-center gap-3">
        <CheckCircle size={20} className="flex-shrink-0" />
        <span className="text-sm font-medium">{lastActionMessage}</span>
      </div>
      <button onClick={() => setLastActionMessage(null)} className="p-1 rounded-full text-green-700 hover:bg-green-200 transition-colors" aria-label="Dismiss notification">
        <X size={16} />
      </button>
    </div>
  </div>
)}

{lastErrorMessage && (
  <div key={actionMessageKey} className="relative z-20">
    <div className="bg-red-100 border border-red-300 text-red-800 px-6 py-4 rounded-xl shadow-md flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-300" role="status">
      <div className="flex items-center gap-3">
        <XCircle size={20} className="flex-shrink-0" />
        <span className="text-sm font-medium">{lastErrorMessage}</span>
      </div>
      <button onClick={() => setLastErrorMessage(null)} className="p-1 rounded-full text-red-700 hover:bg-red-200 transition-colors" aria-label="Dismiss notification">
        <X size={16} />
      </button>
    </div>
  </div>
)}


            {jobs.length === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-gray-300 rounded-xl bg-gray-50">
                    <Briefcase size={48} className="mx-auto text-gray-400" />
                    <h3 className="mt-4 text-lg font-semibold text-gray-700">No Active Jobs Found</h3>
                    <p className="mt-1 text-sm text-gray-500">Please create a job post</p>
                </div>
            ) : (
                jobs.map(job => (
                    <div key={job.job_id} className="border border-gray-200 rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-300">
                        
                        {/* Job Header (Clickable) */}
                        <div 
                            className={clsx(
                                "flex items-center justify-between p-4 sm:p-6 cursor-pointer transition-all duration-200",
                                expandedJobId === job.job_id ? "bg-indigo-50/70 border-b border-indigo-200" : "bg-white hover:bg-gray-50/50"
                            )}
                            onClick={() => handleJobToggle(job.job_id)}
                        >
                            <div className="flex items-center gap-4">
                                <h3 className="text-lg font-bold text-gray-900">{job.job_title}</h3>
                                <span className="px-3 py-1 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-full border border-indigo-200">
                                    Applied Candidates count:{job.total_applied} 
                                </span>
                            </div>
                            <ChevronDown size={24} className={clsx("text-gray-500 transition-transform duration-300", expandedJobId === job.job_id ? "rotate-180" : "rotate-0")} />
                        </div>

                        {/* Job Content (Expandable) */}
                        {expandedJobId === job.job_id && (
                            <div className="p-4 sm:p-6 bg-white space-y-6">
                                
                                {/* Round Tabs/Navigation */}
                                <div className="border-b border-gray-100 pb-3">
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="text-sm font-bold text-gray-700">Interview Rounds:</h4>
                                        
                                        {currentJob && currentRound && (
                                            <Button 
                                                onClick={openScheduleModal}
                                                variant="primary"
                                                className="px-4 py-2 text-sm flex items-center gap-2 rounded-full bg-green-600 hover:bg-green-700"
                                                disabled={roundCandidates.filter(c => c.round_status === 'shortlisted').length === 0}
                                                title={roundCandidates.filter(c => c.round_status === 'shortlisted').length === 0 ? `No candidates shortlisted in ${currentRound.round_name}` : `Schedule interviews for candidates in ${currentRound.round_name}`}
                                            >
                                                <Calendar size={16} /> Schedule Interview
                                            </Button>
                                        )}
                                    </div>
                                    <div className="flex flex-wrap gap-3">
                                        {job.rounds.map(round => {
                                            const isActive = selectedRoundId === round.round_id;
                                            return (
                                                <button
                                                    key={round.round_id}
                                                    onClick={() => handleRoundChange(job.job_id, round.round_id)}
                                                    className={clsx(
                                                        "px-4 py-2 text-sm font-medium rounded-lg transition-all duration-150 flex items-center gap-2 border",
                                                        isActive 
                                                            ? "bg-indigo-600 text-white border-indigo-600 shadow-md"
                                                            : "bg-white text-gray-700 hover:bg-indigo-50 border-gray-300"
                                                    )}
                                                >
                                                    {round.round_name}
                                                    <span className={clsx(
                                                        "ml-1 px-2 py-0.5 text-xs rounded-full font-bold",
                                                        isActive ? "bg-white text-indigo-600" : "bg-gray-100 text-gray-700"
                                                    )}>
                                                        {round.total_candidates}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                                
                                {/* Round Stats / Filters */}
                                {job.rounds.find(r => r.round_id === selectedRoundId) && (
                                    <RoundStats round={job.rounds.find(r => r.round_id === selectedRoundId)!} />
                                )}

                                {/* Candidate List */}
                                <div className="space-y-4">
                                    <h4 className="text-lg font-bold text-gray-800 border-b border-gray-100 pb-2">
                                        Candidates in: <span className="text-blue-600">{job.rounds.find(r => r.round_id === selectedRoundId)?.round_name ?? 'Select Round'}</span>
                                    </h4>
                                    {candidatesLoading ? (
                                        <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-lg">
                                            <Loader2 size={24} className="inline animate-spin mr-2 text-indigo-500" /> Fetching candidates for round...
                                        </div>
                                    ) : roundCandidates.length === 0 ? (
                                        <div className="text-center py-10 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
                                            <AlertTriangle size={24} className="mx-auto mb-2 text-gray-400"/>
                                            No candidates in this round yet.
                                        </div>
                                    ) : (
                                        <div className="space-y-3">
                                            {roundCandidates.map(candidate => (
                                                <CandidateListItem 
                                                    key={candidate.profile_id} 
                                                    candidate={candidate} 
                                                    scheduledLabel={formatScheduleLabel(scheduledByProfileId.get(candidate.profile_id)?.scheduled_datetime)}
                                                    canReschedule={!scheduledLoading && scheduledByProfileId.has(candidate.profile_id)}
                                                    onRescheduleClick={() => openRescheduleModal(candidate)}
                                                    onViewDetails={() => setSelectedCandidate(candidate)}
                                                    onStatusChangeClick={() => setStatusModalCandidate(candidate)}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                ))
            )}
            
            {/* Candidate Detail Modal */}
            {selectedCandidate && (
                <CandidateDetailModal candidate={selectedCandidate} onClose={() => setSelectedCandidate(null)} />
            )}

            {/* Candidate Status Update Modal */}
            {statusModalCandidate && (
                <CandidateStatusModal
                    isOpen={!!statusModalCandidate}
                    candidate={statusModalCandidate}
                    onClose={() => setStatusModalCandidate(null)}
                    onStatusUpdate={handleStatusUpdate}
                    isProcessing={isStatusUpdating}
                />

            )}
            
            {/* Schedule Interview Modal */}
            {scheduleModalData && (
                <ScheduleInterviewModal
                    isOpen={!!scheduleModalData}
                    data={scheduleModalData}
                    onClose={() => setScheduleModalData(null)}
                    onSchedule={handleScheduleInterview}
                    isScheduling={isScheduling}
                />
            )}

            {/* Reschedule Interview Modal */}
            {rescheduleModalData && (
                <RescheduleInterviewModal
                    isOpen={!!rescheduleModalData}
                    data={rescheduleModalData}
                    onClose={() => setRescheduleModalData(null)}
                    onReschedule={handleRescheduleInterview}
                    isRescheduling={isRescheduling}
                />
            )}
        </div>
    );
};

export default JobRecruitmentContent;