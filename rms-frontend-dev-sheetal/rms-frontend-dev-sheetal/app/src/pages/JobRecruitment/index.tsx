// src/pages/JobRecruitment/index.tsx

import React from 'react';
import Layout from '../../components/layout/Layout';
import JobRecruitmentContent from './JobRecruitmentContent'; // <-- New import

/**
 * The entry point for the Job Recruitment feature.
 * It provides the overall page layout and structure.
 */
const JobRecruitmentPage: React.FC = () => {
    return (
        <Layout
            bannerTitle="Job Recruitment"
            bannerSubtitle="Track candidate progress across the hiring pipeline"
            searchPlaceholder="Search jobs..."
        >
            {/* The core logic is now encapsulated here */}
            <JobRecruitmentContent /> 
        </Layout>
    );
};

export default JobRecruitmentPage;


// // src/pages/JobRecruitment/index.tsx


// import React, { useState, useMemo, useCallback, useEffect } from 'react';
// import { useToast } from '../../context/ModalContext';
// import { 
//     Loader2, Briefcase, ChevronDown, XCircle, RefreshCw, Calendar, Clock, Zap, Users, Check,
//     AlertTriangle, Send, Star, Settings, CheckCircle, X
// } from 'lucide-react';
// import Layout from '../../components/layout/Layout';

// import { useRecruitmentData } from '../../hooks/useRecruitmentData';
// import RoundStats from '../../components/common/Roundstats';
// import CandidateListItem from '../../components/common/CandidateListItem';
// import CandidateDetailModal from '../../components/common/CandidateDetailModel';
// import clsx from 'clsx';
// import Button from '../../components/common/Button';

// // IMPORTED scheduleInterview and NEW TYPES
// import { patchCandidateStatus, scheduleInterview } from '../../api/recruitmentApi'; 
// import type { Candidate, CandidateStatus, InterviewLevel, InterviewType } from '../../api/recruitmentApi';
// import { getJobPostById } from '../../api/jobApi'; // Import to fetch Job Type


// // --- NEW INTERFACE: Email Template ---
// interface EmailTemplate {
//     subject: string;
//     body: string;
// }

// const generateDefaultEmailContent = (
//     roundName: string, 
//     jobTitle: string, 
//     interviewType: 'agent' | 'offline' | 'hybrid'
// ): EmailTemplate => {
    
//     const defaultSubject = `Interview Invitation - {JOB_TITLE} | shortlisted in {ROUND_NAME} `;

//     // src/pages/JobRecruitment/index.tsx

// // ... (around line 34)

//     const defaultBody = `Dear **{CANDIDATE_NAME}**,

// Congratulations! We are delighted to inform you that you have been shortlisted in the **{ROUND_NAME}** round for the **{JOB_TITLE}** position.


// ### Interview Schedule:

// **Position:** {JOB_TITLE}
// **Next Round:** {NEXT_ROUND_NAME}
// **Date:** {DATE}
// **Time:** {TIME}

// ### Interview Access Details:

// * **Interview Link:** {INTERVIEW_LINK}
// * **Room ID:** {INTERVIEW_TOKEN}


// Please make sure to attend the interview on time from the provided link.
// Should you have any questions or need to reschedule, please don't hesitate to reach out to us.

// Best regards,

// **Prayag RMS Team**
// `;

    
//     return {
//         subject: defaultSubject.replace(/{JOB_TITLE}/g, jobTitle).replace(/{ROUND_NAME}/g, roundName),
//         body: defaultBody,      
//     };
// };

// // --- NEW MOCK: Interface for minimal Job Details needed for the modal ---
// interface JobTypeDetails {
//     interview_type: 'agent' | 'offline' | 'hybrid';
// }

// // --- UPDATED: Schedule Interview Modal Data ---
// interface ScheduleModalData {
//     jobId: string;
//     jobTitle: string;
//     roundId: string;
//     roundName: string;
//     candidates: Candidate[];
//     jobDetails: JobTypeDetails | null; 
//     emailTemplate: EmailTemplate; // <--- ADDED
// }

// interface ScheduleInterviewModalProps {
//     data: ScheduleModalData;
//     isOpen: boolean;
//     onClose: () => void;
//     onSchedule: (scheduleData: { 
//         jobId: string, 
//         roundId: string, 
//         profileIds: string[], 
//         dateTime: string, 
//         level: InterviewLevel, 
//         type: InterviewType,
//         emailSubject: string, // <--- ADDED
//         emailBody: string // <--- ADDED
//     }) => Promise<void>;
//     isScheduling: boolean;
// }

// const ScheduleInterviewModal: React.FC<ScheduleInterviewModalProps> = ({ isOpen, data, onClose, onSchedule, isScheduling }) => {
//     // State is reset on close/open via useEffect for a clean modal state
//     const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);
    
//     // --- UPDATED STATES (Separate date/time) ---
//     const [interviewDate, setInterviewDate] = useState(''); 
//     const [interviewTime, setInterviewTime] = useState('');
//     const [emailSubject, setEmailSubject] = useState(''); 
//     const [emailBody, setEmailBody] = useState(''); 
//     const [activeConfigTab, setActiveConfigTab] = useState<'schedule' | 'email'>('schedule'); 
//     // --- END UPDATED STATES ---
//     const [localMessage, setLocalMessage] = useState<string | null>(null); 
    
//     const [level, setLevel] = useState<InterviewLevel>('Medium'); 
//     const [type, setType] = useState<InterviewType>('Agent_interview'); 
//     const [scoreFilter, setScoreFilter] = useState<number>(0); 

//     // --- ENHANCEMENT 4: Determine default interview type (Moved inside component for access to data) ---
//     const mapJobPostTypeToApiType = (jobType: JobTypeDetails['interview_type']): InterviewType => {
//         if (jobType === 'agent') return 'Agent_interview';
//         if (jobType === 'offline' || jobType === 'hybrid') return 'In_person'; 
//         return 'Agent_interview'; // Default fallback
//     };
    
//     // Set initial state based on jobDetails when data changes
//     useEffect(() => {
//         if (isOpen) {
//             const defaultJobPostType = data.jobDetails 
//                 ? mapJobPostTypeToApiType(data.jobDetails.interview_type) 
//                 : 'Agent_interview';

//             // Set default date/time for UI initialization
//             const now = new Date();
//             const tomorrow = new Date(now.setDate(now.getDate() + 1)).toISOString().substring(0, 10);
            
//             // Set initial states here to reset them on modal open
//             setType(defaultJobPostType);
//             setSelectedCandidates([]); 
//             setInterviewDate(tomorrow); // <--- Set default date
//             setInterviewTime('10:00'); // <--- Set default time for user-friendliness
//             setLevel('Medium'); 
//             setScoreFilter(0);
            
//             // Set initial email content from data prop
//             setEmailSubject(data.emailTemplate.subject); 
//             setEmailBody(data.emailTemplate.body); 
//             setActiveConfigTab('schedule');
//         }
//     }, [isOpen, data]);

//     if (!isOpen) return null;

//     // Use the determined default type for the component's display
//     const currentJobPostType = data.jobDetails 
//         ? mapJobPostTypeToApiType(data.jobDetails.interview_type)
//         : 'Agent_interview'; 
    
//     // --- Filtered Candidates ---
//     const allShortlistedCandidates = useMemo(() => 
//         data.candidates.filter(c => c.round_status === 'shortlisted'), 
//         [data.candidates]
//     );

//     const filteredCandidates = useMemo(() => {
//         if (scoreFilter === 0) return allShortlistedCandidates;

//         return allShortlistedCandidates.filter(c => c.overall_score >= scoreFilter);
//     }, [allShortlistedCandidates, scoreFilter]);


//     const handleToggleCandidate = (profileId: string) => {
//         setSelectedCandidates(prev => {
//             if (prev.includes(profileId)) {
//                 return prev.filter(id => id !== profileId);
//             }
//             return [...prev, profileId];
//         });
//     };
    
//     const handleSelectAll = () => {
//         const allIds = filteredCandidates.map(c => c.profile_id);
//         const allCurrentlySelected = selectedCandidates.length === filteredCandidates.length && selectedCandidates.every(id => allIds.includes(id));

//         if (allCurrentlySelected) {
//             setSelectedCandidates([]); // Deselect All
//         } else {
//             setSelectedCandidates(allIds); // Select All
//         }
//     };
    
//     const handleSubmit = (e: React.FormEvent) => {
//         e.preventDefault();
        
//         const combinedDateTime = `${interviewDate}T${interviewTime}`; // <--- COMBINE DATE AND TIME
        
//         // --- UPDATED SUBMIT CHECK: Must include email content validity ---
//         if (selectedCandidates.length === 0 || !combinedDateTime || !emailSubject.trim() || !emailBody.trim() || isScheduling) return;


//         // The 'Hybrid' visual option maps to 'In_person' for the API
//         const apiType = type === 'Agent_interview' ? 'Agent_interview' : 'In_person'; 
        
//         onSchedule({
//             jobId: data.jobId,
//             roundId: data.roundId,
//             profileIds: selectedCandidates,
//             dateTime: combinedDateTime,
//             level,
//             type: apiType, // Pass the API compatible type
//             emailSubject: emailSubject.trim(), // <--- PASS NEW STATE
//             emailBody: emailBody.trim(),       // <--- PASS NEW STATE
//         });
//     };
    
//     // --- Interview Type/Level Options ---
//     const interviewLevels: InterviewLevel[] = ['Easy', 'Medium', 'Hard'];
//     const interviewTypeOptions = [
//         { value: 'Agent_interview', label: 'Agent Interview (Remote/AI)' },
//         { value: 'In_person', label: 'In Person / Offline' },
//         { value: 'Hybrid', label: 'Hybrid (Remote & In Person)' }, 
//     ];

//     // Score Filter Options for ENHANCEMENT 3
//     const scoreFilterOptions = [
//         { value: 0, label: 'All Shortlisted' },
//         { value: 25, label: '25% Score and above' },
//         { value: 50, label: '50% Score and above' },
//         { value: 75, label: '75% Score and above' },
//     ];

//     // --- UPDATED isSubmitDisabled CHECK: Use new states for validity ---
//     const isSubmitDisabled = isScheduling || selectedCandidates.length === 0 || !interviewDate.trim() || !interviewTime.trim() || !emailSubject.trim() || !emailBody.trim();
//     // Removed legacy dependency: || !dateTime.trim();
//     const isAllSelected = selectedCandidates.length === filteredCandidates.length && filteredCandidates.length > 0;
    
//     return (
//         <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
//             <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto transform transition-all duration-300 scale-100 opacity-100" onClick={(e) => e.stopPropagation()}>
//                 <form onSubmit={handleSubmit}>
//                     {/* Header */}
//                     <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center z-10">
//                         <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
//                             <Calendar size={24} className="text-indigo-600" />
//                             <span className="text-indigo-600 italic">{data.jobTitle} - {data.roundName}</span>
//                         </h2>
//                         <button type="button" onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 text-gray-500"><XCircle size={20} /></button>
//                     </div>

//                     {/* --- FIX: Dynamic Grid Layout for Email Editing --- */}
//                     <div className={clsx(
//                         "p-6 grid gap-8",
//                         // Grid configuration: 1 column when in email mode, 3 columns otherwise (1 for config, 2 for candidates)
//                         activeConfigTab === 'email' ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-3"
//                     )}>
                        
//                         {/* Column 1: Configuration (Expands on Email Tab) */}
//                         <div className={clsx(
//                              "space-y-6",
//                              // Span 3 columns when in email mode, span 1 when in schedule mode
//                              activeConfigTab === 'email' ? "lg:col-span-3" : "lg:col-span-1" 
//                         )}>
//                             <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2"><Settings size={20} className="text-gray-500"/> Configuration</h3> 
                            
//                             {/* Configuration Tabs */}
//                             <div className="flex w-full rounded-xl border-2 p-1 bg-gray-100 border-gray-200">
//                                 <button
//                                     type="button"
//                                     onClick={() => setActiveConfigTab('schedule')}
//                                     className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
//                                         activeConfigTab === 'schedule'
//                                             ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
//                                             : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
//                                     }`}
//                                 >
//                                     <Clock size={16} /> Scheduling
//                                 </button>
//                                 <button
//                                     type="button"
//                                     onClick={() => setActiveConfigTab('email')}
//                                     className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
//                                         activeConfigTab === 'email'
//                                             ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
//                                             : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
//                                     }`}
//                                 >
//                                     <Send size={16} /> Email
//                                 </button>
//                             </div>

//                             {/* Tab Content: SCHEDULING (Visible only when 'schedule' is active) */}
//                             {activeConfigTab === 'schedule' && (
//                                 <div className="space-y-6">
//                                     {/* Selected Count Summary (remains) */}
//                                     <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200 text-center">
//                                         <p className="text-xs font-medium text-indigo-700 mb-1">Candidates to Schedule</p>
//                                         <p className="text-4xl font-extrabold text-indigo-900">{selectedCandidates.length}</p>
//                                     </div>
                                    
//                                     {/* Interview Date/Time - FIX: Separate Inputs for UX */}
//                                     <div className='bg-gray-50 p-4 rounded-lg border space-y-4'>
//                                         <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Clock size={16} /> Date & Time *</label>
                                        
//                                         <div className="space-y-3">
//                                             {/* Date Picker */}
//                                             <div>
//                                                 <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
//                                                 <input
//                                                     type="date" 
//                                                     value={interviewDate}
//                                                     onChange={(e) => setInterviewDate(e.target.value)}
//                                                     min={new Date().toISOString().substring(0, 10)}
//                                                     className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
//                                                     required
//                                                 />
//                                             </div>

//                                             {/* Time Picker (User-Friendly) */}
//                                             <div>
//                                                 <label className="block text-xs font-medium text-gray-600 mb-1">Time</label>
//                                                 <input
//                                                     type="time" 
//                                                     value={interviewTime}
//                                                     onChange={(e) => setInterviewTime(e.target.value)}
//                                                     step="300" 
//                                                     className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
//                                                     required
//                                                 />
//                                             </div>
//                                         </div>
//                                         <p className="text-xs text-gray-500 mt-1">Interviews must be scheduled for a future date and time.</p>
//                                     </div>
                                    
//                                     {/* Interview Type (remains) */}
//                                     <div className='bg-gray-50 p-4 rounded-lg border'>
//                                         <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Users size={16} /> Interview Type *</label>
//                                         <select
//                                             value={type}
//                                             onChange={(e) => setType(e.target.value as InterviewType)}
//                                             className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base bg-white focus:ring-indigo-500 focus:border-indigo-500"
//                                         >
//                                             {interviewTypeOptions.map(option => (
//                                                 <option key={option.value} value={option.value}>{option.label}</option>
//                                             ))}
//                                         </select>
//                                         <p className="text-xs text-gray-500 mt-1">Default type based on job post: <strong className="text-indigo-600">{currentJobPostType === 'Agent_interview' ? 'Agent Interview' : 'In Person / Offline'}</strong></p>
//                                     </div>

//                                     {/* Interview Level (remains) */}
//                                     {type === 'Agent_interview' && (
//                                         <div className="space-y-1 bg-gray-50 p-4 rounded-lg border border-yellow-200">
//                                             <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Zap size={16} /> Agent Interview Level *</label>
//                                             <select
//                                                 value={level}
//                                                 onChange={(e) => setLevel(e.target.value as InterviewLevel)}
//                                                 className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base bg-white focus:ring-yellow-500 focus:border-yellow-500"
//                                             >
//                                                 {interviewLevels.map(l => <option key={l} value={l}>{l}</option>)}
//                                             </select>
//                                             <p className="text-xs text-gray-500 mt-1">Required to set difficulty for AI interviews.</p>
//                                         </div>
//                                     )}
//                                 </div>
//                             )}

//                             {/* Tab Content: EMAIL CONFIGURATION (Visible only when 'email' is active) */}
//                             {/* Tab Content: EMAIL CONFIGURATION (Visible only when 'email' is active) */}
//                             {activeConfigTab === 'email' && (
//                                 <div className="space-y-6">
//                                     {/* Help Panel */}
//                                     <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg border border-indigo-200 p-5">
//                                         <div className="flex items-start gap-3">
//                                             <div className="flex-shrink-0 w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center">
//                                                 <AlertTriangle size={16} className="text-white" />
//                                             </div>
//                                             <div className="flex-1">
//                                                 <h4 className="text-sm font-bold text-indigo-900 mb-2">Dynamic Placeholders - How They Work</h4>
//                                                 <p className="text-xs text-indigo-800 mb-3">
//                                                     Placeholders like <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-600 text-white text-xs font-mono">{'\{CANDIDATE_NAME\}'}</span> are automatically replaced with real data when emails are sent. You can edit all content freely — just keep placeholder format exact (uppercase with braces).
//                                                 </p>
//                                                 <div className="grid grid-cols-2 gap-2 text-xs">
//                                                     <div className="flex items-center gap-1.5">
//                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{CANDIDATE_NAME\}'}</span>
                                                        
//                                                     </div>
//                                                     <div className="flex items-center gap-1.5">
//                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{JOB_TITLE\}'}</span>
                                                        
//                                                     </div>
//                                                     <div className="flex items-center gap-1.5">
//                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{ROUND_NAME\}'}</span>
                                                        
//                                                     </div>
//                                                     <div className="flex items-center gap-1.5">
//                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{DATE\}'}</span>
                                                        
//                                                     </div>
//                                                     <div className="flex items-center gap-1.5">
//                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{TIME\}'}</span>
                                                        
//                                                     </div>
//                                                     <div className="flex items-center gap-1.5">
//                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{INTERVIEW_LINK\}'}</span>
                                                       
//                                                     </div>
//                                                 </div>
//                                             </div>
//                                         </div>
//                                     </div>
                                    
//                                     {/* Email Subject */}
//                                     <div className="space-y-2">
//                                         <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
//                                             <Send size={16} className="text-indigo-600" />
//                                             Email Subject *
//                                         </label>
//                                         <div className="relative">
//                                             <input
//                                                 type="text"
//                                                 value={emailSubject}
//                                                 onChange={(e) => setEmailSubject(e.target.value)}
//                                                 placeholder="e.g., Interview Invitation for {JOB_TITLE}"
//                                                 className="w-full border-2 border-gray-300 rounded-lg px-4 py-3 text-base focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all placeholder:text-gray-400"
//                                                 required
//                                             />
//                                         </div>
//                                         {/* <p className="text-xs text-gray-500 flex items-center gap-1">
//                                             <span className="inline-block w-1.5 h-1.5 bg-indigo-600 rounded-full"></span>
//                                             Use placeholders like {'\{JOB_TITLE\}'} or {'\{ROUND_NAME\}'} for dynamic content
//                                         </p> */}
//                                     </div>
                                    
//                                     {/* Email Body with Enhanced Editor */}
//                                     <div className="space-y-2">
//                                         <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
//                                             <Settings size={16} className="text-indigo-600" />
//                                             Email Body - The preview below shows how the email will look to candidates (kindly look over for any necessary customization) *
//                                         </label>
                                        
//                                         {/* Enhanced Textarea with Better Styling */}
//                                         <div className="relative">
//                                             <textarea
//                                                 rows={16}
//                                                 value={emailBody}
//                                                 onChange={(e) => setEmailBody(e.target.value)}
//                                                 placeholder="Dear {CANDIDATE_NAME},&#10;&#10;We are pleased to inform you..."
//                                                 className="w-full p-4 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-y font-mono text-sm leading-relaxed placeholder:text-gray-400 placeholder:font-sans"
//                                                 required
//                                                 style={{
//                                                     background: 'linear-gradient(to bottom, #ffffff 0%, #fafafa 100%)',
//                                                 }}
//                                             />
//                                             {/* Character count helper */}
//                                             <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-white/80 px-2 py-1 rounded">
//                                                 {emailBody.length} characters
//                                             </div>
//                                         </div>
                                        
//                                         {/* <div className="flex items-start gap-2 text-xs text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-200">
//                                             <span className="inline-block w-1.5 h-1.5 bg-gray-400 rounded-full mt-1 flex-shrink-0"></span>
//                                             <div className="space-y-1">
//                                                 <p className="font-medium text-gray-700">Markdown Quick Reference:</p>
//                                                 <div className="grid grid-cols-2 gap-x-4 gap-y-1">
//                                                     <span><code className="bg-gray-200 px-1 rounded">**bold**</code> for <strong>bold text</strong></span>
//                                                     <span><code className="bg-gray-200 px-1 rounded">*italic*</code> for <em>italic text</em></span>
//                                                     <span><code className="bg-gray-200 px-1 rounded"># Header</code> for headers</span>
//                                                     <span><code className="bg-gray-200 px-1 rounded">* Item</code> for bullet lists</span>
//                                                     <span><code className="bg-gray-200 px-1 rounded">| Table |</code> for tables</span>
//                                                     <span><code className="bg-gray-200 px-1 rounded">---</code> for dividers</span>
//                                                 </div>
//                                             </div>
//                                         </div> */}
//                                     </div>

//                                    {/* Preview Section */}
//                                     <div className="border-t-2 border-gray-200 pt-6">
//                                         <div className="flex items-center justify-between mb-3">
//                                             <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
//                                                 <Users size={16} className="text-indigo-600" />
//                                                 Email Preview
//                                             </label>
                                          
//                                         </div>
//                                         <div className="bg-white border-2 border-gray-200 rounded-lg overflow-hidden shadow-sm">
//                                             {/* Email Header */}
//                                             <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 border-b border-gray-200">
//                                                 <div className="space-y-2">
//                                                     <div className="flex items-start gap-3">
//                                                         <span className="text-xs font-medium text-gray-500 w-16">Subject:</span>
//                                                         <span className="flex-1 font-semibold text-gray-900 text-sm">
//                                                             {emailSubject 
//                                                                 .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
//                                                                 .replace(/{JOB_TITLE}/g, data.jobTitle)
//                                                                 .replace(/{ROUND_NAME}/g, data.roundName)
//                                                                 .replace(/{DATE}/g, 'November 20, 2025')
//                                                                 .replace(/{TIME}/g, '2:00 PM')
//                                                                 .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
//                                                                 .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
//                                                                 .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
//                                                                 .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
//                                                              || 'No subject provided'}
//                                                         </span>
//                                                     </div>
//                                                     <div className="flex items-start gap-3">
//                                                         <span className="text-xs font-medium text-gray-500 w-16">To:</span>
//                                                         <span className="flex-1 text-sm text-gray-700">sarah.johnson@email.com</span>
//                                                     </div>
//                                                 </div>
//                                             </div>
                                            
                                       
// <div className="p-6 bg-white">
//     <div 
//         className="text-sm text-gray-800 leading-relaxed"
//         style={{ 
//             fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
//             // --- FIX: Remove whiteSpace: 'pre-wrap' (it was already removed in the example, but ensure it's not present)
//             wordBreak: 'break-word'
//         }}
//     >
//         {emailBody ? (
//             <div
//                 // Use dangerouslySetInnerHTML to render the content with line breaks
//                 // Note: This is a hacky fix since a proper Markdown renderer is missing.
//                 dangerouslySetInnerHTML={{
//                     __html: emailBody
//                         .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
//                         .replace(/{JOB_TITLE}/g, data.jobTitle)
//                         .replace(/{ROUND_NAME}/g, data.roundName)
//                         .replace(/{DATE}/g, 'November 20, 2025')
//                         .replace(/{TIME}/g, '2:00 PM')
//                         .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
//                         .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
//                         .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
//                         .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
//                         // --- FIX: Manual Markdown to HTML approximation for preview ---
//                         // 1. Replace double newlines with <br><br> for spacious gaps
//                         .replace(/\n\n/g, '<br><br>') 
//                         // 2. Replace single newlines with <br>
//                         .replace(/\n/g, '<br>') 
//                         // 3. Replace Markdown bold with HTML bold (for preview only)
//                         .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
//                         // 4. Replace Markdown H3 with HTML H3 (for preview only)
//                         .replace(/### (.*?)<br>/g, '<h3>$1</h3>')
//                 }}
//             />
//         ) : (
//             <span className="text-gray-400 italic">Email body will appear here...</span>
//         )}
//     </div>
// </div>

                                            
//                                         </div>
//                                         <p className="text-xs text-gray-500 mt-3 flex items-center gap-1">
//                                             <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full"></span>
//                                             Preview shows sample data. Actual emails will use real candidate information.
//                                         </p>
//                                     </div>
//                                 </div>
//                             )}



//                         </div>
                        
//                         {/* Column 2: Candidates List (Hidden on Email Tab) */}
//                         {activeConfigTab === 'schedule' && (
//                             <div className="lg:col-span-2 space-y-4">
//                                 <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2"><Users size={20} className="text-gray-500"/> Candidates Selection</h3>

//                                 <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200 gap-3">
//                                     <p className="text-sm text-gray-700 font-medium">
//                                         <span className="font-bold text-green-600">{allShortlistedCandidates.length}</span> candidates are ready for scheduling.
//                                         <span className="ml-3 text-xs text-gray-500">Showing <strong className="text-gray-800">{filteredCandidates.length}</strong> candidates.</span>
//                                     </p>
//                                     {/* Score Filter (ENHANCEMENT 3) */}
//                                     <div className="flex items-center gap-2 text-sm flex-shrink-0">
//                                         <label className="text-gray-600 font-medium">Filter:</label>
//                                         <select 
//                                             value={scoreFilter}
//                                             onChange={(e) => setScoreFilter(Number(e.target.value))}
//                                             className="border border-gray-300 rounded-md px-2 py-1 bg-white text-sm focus:ring-indigo-500 focus:border-indigo-500"
//                                         >
//                                             {scoreFilterOptions.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
//                                         </select>
//                                     </div>
//                                 </div>
                                
//                                 {/* Select All Button (ENHANCEMENT 2) */}
//                                 <Button 
//                                     type="button" 
//                                     onClick={handleSelectAll} 
//                                     variant="outline" 
//                                     disabled={filteredCandidates.length === 0}
//                                     className="w-full py-2.5 text-sm flex items-center justify-center gap-2 text-indigo-600 border-indigo-300 hover:bg-indigo-50"
//                                 >
//                                     <Check size={16} /> 
//                                     {isAllSelected ? 'Deselect All' : `Select All (${filteredCandidates.length} filtered)`}
//                                 </Button>

//                                 <div className="max-h-80 overflow-y-auto pr-2 space-y-2">
//                                     {filteredCandidates.length === 0 ? (
//                                         <div className="text-center py-10 text-gray-500 bg-gray-50 rounded-lg border border-dashed">
//                                             <AlertTriangle size={24} className="mx-auto mb-2 text-gray-400"/>
//                                             <div className="text-sm">No candidates match the current filters.</div>
//                                         </div>
//                                     ) : (
//                                         filteredCandidates.map(candidate => (
//                                             <div 
//                                                 key={candidate.profile_id} 
//                                                 onClick={() => handleToggleCandidate(candidate.profile_id)}
//                                                 className={clsx(
//                                                     "p-3 rounded-lg border cursor-pointer transition-all duration-200 flex justify-between items-center group",
//                                                     selectedCandidates.includes(candidate.profile_id) 
//                                                         ? "bg-indigo-100/70 border-indigo-400 shadow-md" 
//                                                         : "bg-white border-gray-200 hover:bg-gray-50"
//                                                 )}
//                                             >
//                                                 <div className="flex items-center gap-3">
//                                                     <div className={clsx(
//                                                         "w-5 h-5 rounded flex items-center justify-center border transition-colors flex-shrink-0",
//                                                         selectedCandidates.includes(candidate.profile_id) ? "bg-indigo-600 border-indigo-600 text-white" : "bg-white border-gray-300 group-hover:border-indigo-400"
//                                                     )}>
//                                                         {selectedCandidates.includes(candidate.profile_id) && <Check size={14} />}
//                                                     </div>
//                                                     <div>
//                                                         <span className="font-medium text-gray-900 block">{candidate.candidate_name}</span>
//                                                         <span className="text-xs text-gray-500 flex items-center gap-1 mt-0.5"><Star size={12} className="text-yellow-500"/> {candidate.overall_score}% Match</span>
//                                                     </div>
//                                                 </div>
//                                                 <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-1 rounded-full flex-shrink-0">Shortlisted</span>
//                                             </div>
//                                         ))
//                                     )}
//                                 </div>
//                             </div>
//                         )}
//                     </div>

//                     {/* Footer / Submit Button */}
//                     <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6 flex justify-end gap-3 z-10">
//                         <Button type="button" variant="secondary" onClick={onClose} disabled={isScheduling}>
//                             Cancel
//                         </Button>
//                         <Button type="submit" variant="primary" disabled={isSubmitDisabled}>
//                             {isScheduling ? (
//                                 <><Loader2 size={16} className="animate-spin mr-2" /> Submitting...</>
//                             ) : (
//                                 <><Send size={16} className="mr-2"/> Schedule {selectedCandidates.length} Interview(s)</>
//                             )}
//                         </Button>
//                     </div>

//                     {localMessage && (
//                     <div className="mt-3">
//                     <div className="bg-yellow-50 border border-yellow-300 text-yellow-800 px-4 py-2 rounded flex items-center gap-2">
//                         <AlertTriangle size={16} />
//                         <span>{localMessage}</span>
//                     </div>
//                     </div>
//                 )}
                
//                 </form>
//             </div>
//         </div>
//     );
// };


// // --- Candidate Status Modal (Enhanced UI/UX) ---

// interface CandidateStatusModalProps {
//     isOpen: boolean;
//     candidate: Candidate;
//     onClose: () => void;
//     onStatusUpdate: (candidateId: string, newStatus: CandidateStatus, reason: string) => void;
//     isProcessing: boolean;
// }

// const CandidateStatusModal: React.FC<CandidateStatusModalProps> = ({ 
//     isOpen, candidate, onClose, onStatusUpdate, isProcessing 
// }) => {
    
//     if (!isOpen) return null;
    
//     const [reason, setReason] = useState('');
//     const [statusToConfirm, setStatusToConfirm] = useState<CandidateStatus | null>(null);
//     const [localMessage, setLocalMessage] = useState<string | null>(null);
    
//     // Reset state when opening a new modal (for a new candidate)
//     useEffect(() => {
//         if(isOpen) {
//             setReason('');
//             setStatusToConfirm(null);
//         }
//     }, [isOpen, candidate.profile_id]);
    
//     const isShowingConfirmation = statusToConfirm !== null;
   

//     const allStatuses: { value: CandidateStatus, label: string, color: string, icon: React.FC<any> }[] = [
//         { value: 'shortlisted', label: 'Move to Next Round', color: 'bg-green-600 hover:bg-green-700', icon: Users }, // Re-using Users for check
//         { value: 'under_review', label: 'Mark Under Review', color: 'bg-yellow-600 hover:bg-yellow-700', icon: AlertTriangle },
//         { value: 'rejected', label: 'Reject Candidate', color: 'bg-red-600 hover:bg-red-700', icon: XCircle }, // Re-using XCircle for reject
//     ];

//     const currentStatus = candidate.round_status;

//     let allowedTransitions: CandidateStatus[] = [];
//     if (currentStatus === 'shortlisted') {
//         allowedTransitions = ['rejected'];
//     } else if (currentStatus === 'rejected') {
//         allowedTransitions = ['shortlisted'];
//     } else if (currentStatus === 'under_review') {
//         allowedTransitions = ['shortlisted', 'rejected'];
//     } else {
//         allowedTransitions = ['shortlisted', 'under_review', 'rejected'];
//     }
    
//     const displayStatuses = allStatuses
//         .map(status => {
//             const isCurrent = status.value === currentStatus;
//             const isAllowed = allowedTransitions.includes(status.value) || isCurrent;
            
//             return isAllowed ? { ...status, current: isCurrent } : null;
//         })
//         .filter((status): status is typeof allStatuses[0] & { current: boolean } => status !== null);

//     const getConfirmButtonLabel = (status: CandidateStatus) => {
//         const labelMap: Record<CandidateStatus, string> = {
//             'shortlisted': 'Confirm Move to Next Round',
//             'under_review': 'Confirm Under Review',
//             'rejected': 'Confirm Rejection',
//             'interview_scheduled': 'Cannot Update', // Placeholder - status should not be 'interview_scheduled' here
//         };
//         return labelMap[status] || 'Confirm Status Change';
//     };

//     const handleConfirmUpdate = (e: React.MouseEvent) => {
//         e.preventDefault(); 
        
//         if (isProcessing) {
//              return; 
//         }
        
//         if (!reason.trim() || !statusToConfirm) {
//             // Toast for missing reasonshowToast(`A reason is required to confirm the status change to '${getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}'.`, 'warning');
//             setLocalMessage(`A reason is required to confirm the status change to '${getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}'.`);
//             return;
//         }
//         onStatusUpdate(candidate.profile_id, statusToConfirm, reason);
//     }

// return (
//         <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
//             <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm transform transition-all duration-300 scale-100 opacity-100" onClick={(e) => e.stopPropagation()}>
//                 <div className="p-6">
//                     <div className="flex justify-between items-center mb-4 border-b pb-3">
//                         <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Send size={20} className="text-blue-600"/> Update Candidate Status</h3>
//                         <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-gray-100"><XCircle size={20} /></button>
//                     </div>

//                     <p className="text-sm text-gray-600 mb-6">
//                         Candidate: <strong className="text-blue-600">{candidate.candidate_name}</strong>
//                         <span className="block text-xs mt-1">Current Round: <strong className="font-medium text-gray-800">{candidate.round_name}</strong> | Status: <strong className={clsx("font-medium", {
//                             'text-green-600': currentStatus === 'shortlisted',
//                             'text-yellow-600': currentStatus === 'under_review',
//                             'text-red-600': currentStatus === 'rejected',
//                             'text-gray-600': currentStatus === 'interview_scheduled'
//                         })}>{currentStatus.replace('_', ' ')}</strong></span>
//                     </p>

//                     {!isShowingConfirmation ? (
//                         <div className="space-y-3">
//                             {displayStatuses.map(status => {
//                                 const Icon = status.icon;
                                
//                                 return (
//                                     <Button
//                                         key={status.value}
//                                         type="button"
//                                         onClick={() => {
//                                             setReason(''); 
//                                             setStatusToConfirm(status.value);
//                                         }}
//                                         disabled={isProcessing || status.current} 
//                                         className={clsx("w-full py-3 text-white flex items-center justify-center gap-2 font-semibold", status.color, { 'opacity-60 cursor-default': status.current })}
//                                     >
//                                         {isProcessing && !status.current ? (
//                                             <Loader2 size={16} className="animate-spin" />
//                                         ) : (
//                                             <>
//                                                 <Icon size={18} />
//                                                 {status.label}
//                                             </>
//                                         )}
//                                         {status.current && <span className="ml-2 text-xs bg-white/30 px-2 py-0.5 rounded-full">(Current)</span>}
//                                     </Button>
//                                 );
//                             })}
//                         </div>
//                     ) : (
//                         <div className="space-y-4">
//                             <p className="text-sm font-bold text-gray-700">
//                                 Reason for <span className={clsx('font-bold', { 
//                                     'text-green-600': statusToConfirm === 'shortlisted', 
//                                     'text-red-600': statusToConfirm === 'rejected', 
//                                     'text-yellow-600': statusToConfirm === 'under_review' 
//                                 })}>
//                                     {getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}
//                                 </span> *
//                             </p>
//                             <textarea
//                                 rows={3}
//                                 value={reason}
//                                 onChange={(e) => setReason(e.target.value)}
//                                 placeholder={`Enter the justification for '${getConfirmButtonLabel(statusToConfirm!).replace('Confirm ', '')}'`}
//                                 className="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm"
//                             />
//                             <Button
//                                 onClick={handleConfirmUpdate} 
//                                 disabled={isProcessing || !reason.trim()}
//                                 className={clsx("w-full py-3 text-white font-semibold flex items-center justify-center gap-2", { 
//                                     'bg-green-600 hover:bg-green-700': statusToConfirm === 'shortlisted',
//                                     'bg-red-600 hover:bg-red-700': statusToConfirm === 'rejected',
//                                     'bg-yellow-600 hover:bg-yellow-700': statusToConfirm === 'under_review',
//                                     'bg-gray-400': isProcessing || !reason.trim()
//                                 })}
//                             >
//                                 {isProcessing ? <Loader2 size={16} className="animate-spin mr-2" /> : <Check size={18} className="mr-1"/>} 
//                                 {isProcessing ? 'Updating...' : getConfirmButtonLabel(statusToConfirm!)}
//                             </Button>

//                             <div className="flex justify-between items-center pt-2">
//                                 <button
//                                     type="button"
//                                     onClick={() => setStatusToConfirm(null)}
//                                     className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
//                                 >
//                                     Back to Status
//                                 </button>
//                             </div>
//                         </div>
//                     )}
//                 </div>
//             </div>
//         </div>
//     );
// };


// // -- MAIN JOB RECRUITMENT PAGE CONTENT COMPONENT (Enhanced Toast Messages & Logic) ---
// const JobRecruitmentPageContent: React.FC = () => {
//     // ... (useRecruitmentData and states remain)
//     const {
//         jobs,
//         isLoading,
//         expandedJobId,
//         selectedRoundId,
//         roundCandidates,
//         candidatesLoading,
//         selectedCandidate,
//         setSelectedCandidate,
//         handleJobToggle,
//         handleRoundChange,
//         fetchJobs,
//     } = useRecruitmentData();

//     // NEW STATE for status update modal
//     const [statusModalCandidate, setStatusModalCandidate] = useState<Candidate | null>(null);
//     const [isStatusUpdating, setIsStatusUpdating] = useState(false);
    
//     // NEW STATE for schedule interview modal
//     const [scheduleModalData, setScheduleModalData] = useState<ScheduleModalData | null>(null);
//     const [isScheduling, setIsScheduling] = useState(false);

//     const [lastActionMessage, setLastActionMessage] = useState<string | null>(null);
//     const [actionMessageKey, setActionMessageKey] = useState(0); // To force re-render/animation

//     const [lastErrorMessage, setLastErrorMessage] = useState<string | null>(null);
//     const [localMessage, setLocalMessage] = useState<string | null>(null);
    
//     const { showToast } = useToast();


//     // 💡 NEW: Clear persistent message after timeout
// useEffect(() => {
//     if (lastActionMessage || lastErrorMessage) {
//         const timer = setTimeout(() => {
//             setLastActionMessage(null);
//             setLastErrorMessage(null);
//         }, 5000); // Show for 5 seconds
//         return () => clearTimeout(timer);
//     }
// }, [lastActionMessage, lastErrorMessage, actionMessageKey]);

//     // Helper to fetch the job details (including interview_type) for the schedule modal
//     const fetchJobDetailsForModal = useCallback(async (jobId: string): Promise<JobTypeDetails | null> => {
//         try {
//             const result = await getJobPostById(jobId);
//             if (result.success && result.data) {
//                 const jobPostInterviewType = result.data.interview_type || 'agent';
//                 const type = jobPostInterviewType as JobTypeDetails['interview_type'];
//                 return { interview_type: type };
//             }
//             return null;
//         } catch (e) {
//             console.error('Failed to fetch job details for scheduling:', e);
//             return null;
//         }
//     }, []);


//     // Handler for Candidate Status Update 
//     const handleStatusUpdate = async (profileId: string, newStatus: CandidateStatus, reason: string) => {
//         // ... (handleStatusUpdate logic remains)
//         const roundId = selectedRoundId;
//         const candidateName = statusModalCandidate?.candidate_name || 'Candidate';
//         if (!roundId || !profileId) {
//             showToast('Internal error: Missing round or profile ID.', 'error');
//             return;
//         }

//         setIsStatusUpdating(true); 
        
//         try {
//             const result = await patchCandidateStatus(roundId, profileId, newStatus, reason);
//             const statusLabel = newStatus.replace('_', ' ');

//             if (result.success && result.data) {
               
//                 setLastActionMessage(`Successfully updated ${candidateName} status to ${statusLabel}. Data is refreshing...`);
//                 setActionMessageKey(prev => prev + 1);

//                 await fetchJobs();
//             } else {
//                 setLastErrorMessage(`Failed to update status for ${candidateName}. ${result.error || ''}`);
//                 setActionMessageKey(prev => prev + 1);
//             }
//         } catch (e: any) {
//              showToast(` Error updating status for ${candidateName}: ${e.message || 'Server error.'}`, 'error');
//         } finally {
//             setIsStatusUpdating(false); 
//             setStatusModalCandidate(null);
//         }
//     };
    
//     // Handler to open the schedule modal
//     const openScheduleModal = async () => {
//         if (!expandedJobId || !selectedRoundId) {
//             showToast('Please select an active job and a specific round before scheduling.', 'info');
//             return;
//         }
        
//         const shortlistedCount = roundCandidates.filter(c => c.round_status === 'shortlisted').length;
//         if (shortlistedCount === 0) {
//              showToast('There are no shortlisted candidates in this round to schedule interviews.', 'info');
//              return;
//         }

//         const job = jobs.find(j => j.job_id === expandedJobId);
//         const round = job?.rounds.find(r => r.round_id === selectedRoundId);

//         if (job && round) {
//             showToast(`Fetching job details for ${job.job_title}...`, 'info');
//             const jobDetails = await fetchJobDetailsForModal(job.job_id);
            
//             // --- FIX: GENERATE EMAIL TEMPLATE ---
//             const emailContent = generateDefaultEmailContent(
//                 round.round_name,
//                 job.job_title,
//                 jobDetails?.interview_type || 'agent'
//             );
//             // --- END FIX ---

//             setScheduleModalData({
//                 jobId: job.job_id,
//                 jobTitle: job.job_title,
//                 roundId: round.round_id,
//                 roundName: round.round_name,
//                 candidates: roundCandidates, // Pass the currently fetched list
//                 jobDetails: jobDetails,
//                 emailTemplate: emailContent, // <--- PASS GENERATED TEMPLATE
//             });
//              showToast('Schedule configuration loaded successfully.', 'success');
//         } else {
//              showToast('Could not find job or round details. Please select again.', 'error');
//         }
//     };
    
//   const handleScheduleInterview = async ({ jobId, roundId, profileIds, dateTime, level, type, emailSubject, emailBody }: { 
//         jobId: string, 
//         roundId: string, 
//         profileIds: string[], 
//         dateTime: string, 
//         level: InterviewLevel, 
//         type: InterviewType,
//         emailSubject: string, // <--- NEW PARAMETER
//         emailBody: string // <--- NEW PARAMETER
//     }) => {
//         setIsScheduling(true);
        

//         try {
          
//             // FIX: Explicitly split the local datetime-local string (YYYY-MM-DDTHH:MM) 
//             // into Date and Time components, adhering to the user's requirement to send 
//             // the local browser time straight to the backend.
//             if (!dateTime || !dateTime.includes('T')) {
//                 throw new Error("Invalid date time selected or format mismatch.");
//             }
            
//             // 1. Separate Date and Time (e.g., ["2024-08-15", "17:00"])
//             const [interview_date, raw_time] = dateTime.split('T'); 
            
//             // 2. Format Time to HH:MM:SS (e.g., "17:00:00")
//             const interview_time = raw_time + ':00'; 
            
//             // Ensure interview type is either 'Agent_interview' or 'In_person' for the API, 
//             const apiType = type === 'Agent_interview' ? 'Agent_interview' : 'In_person';

//             // Only include level if the interview type is Agent_interview, 
//             const levelOfInterview = type === 'Agent_interview' ? level.toLowerCase() : 'easy'; 

//             // Convert to backend payload format (matching expected formats)
//             const payload = {
//                 job_id: jobId,
//                 round_id: roundId, // <--- ADDED roundId
//                 profile_id: profileIds, // List of profile_ids
//                 interview_date: interview_date, // <-- Local Date: YYYY-MM-DD
//                 interview_time: interview_time, // <-- Local Time: HH:MM:SS
//                 interviewer_id: "", // Placeholder - not available in UI
//                 interview_type: apiType, 
//                 level_of_interview: levelOfInterview, 
//                 email_subject: emailSubject, // <--- ADDED emailSubject
//                 email_body: emailBody,       // <--- ADDED emailBody
//             };


//             const result = await scheduleInterview(payload); // API call

//             if (result.success) {
//                 const candidateCount = profileIds.length;
//                 const currentJob = jobs.find(j => j.job_id === jobId);
                
//                 setLastActionMessage(`Successfully scheduled ${candidateCount} interview(s) for ${currentJob?.job_title || 'the selected job'}. Emails sent.`);
//                 setActionMessageKey(prev => prev + 1);
               

//                 await fetchJobs(); 
//             } else {
//                 showToast(result.error || 'Failed to schedule interviews.', 'error');
//             }
//         } catch (e: any) {
//             showToast(e.message || 'Error scheduling interviews.', 'error');
//         } finally {
//             setIsScheduling(false);
//             setScheduleModalData(null); // Close the modal
//         }
//     };

//     if (isLoading) {
//         return (
//             <div className="flex flex-col items-center justify-center h-96">
//                 <Loader2 size={48} className="text-indigo-600 animate-spin" />
//                 <p className="mt-4 text-gray-500 font-medium">Loading Data...</p>
//                 <p className="mt-1 text-sm text-gray-400">Please wait while we fetch the latest job and candidate information.</p>
//             </div>
//         );
//     }

//     const currentJob = jobs.find(j => j.job_id === expandedJobId);
//     const currentRound = currentJob?.rounds.find(r => r.round_id === selectedRoundId);

//     return (
//         <div className="space-y-6">
//             <div className="flex justify-between items-center pb-4 border-b border-gray-100">
//                 <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
//                     <Briefcase size={24} className="text-indigo-600" />
//                     Overview of Jobs with candidates
//                 </h1>
//                 <Button 
//                     variant="outline" 
//                     onClick={fetchJobs} 
//                     disabled={isLoading}
//                     className="py-2 px-4 text-sm flex items-center gap-2 text-blue-600 border-blue-300 hover:bg-blue-50"
//                 >
//                     <RefreshCw size={16} className={clsx({ 'animate-spin': candidatesLoading || isStatusUpdating || isScheduling })} /> Refresh Data
//                 </Button>
//             </div>

//             {/* 💡 NEW: Persistent Action Success/Feedback Banner */}
            
//                {lastActionMessage && (
//   <div key={actionMessageKey} className="relative z-20">
//     <div className="bg-green-100 border border-green-300 text-green-800 px-6 py-4 rounded-xl shadow-md flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-300" role="status">
//       <div className="flex items-center gap-3">
//         <CheckCircle size={20} className="flex-shrink-0" />
//         <span className="text-sm font-medium">{lastActionMessage}</span>
//       </div>
//       <button onClick={() => setLastActionMessage(null)} className="p-1 rounded-full text-green-700 hover:bg-green-200 transition-colors" aria-label="Dismiss notification">
//         <X size={16} />
//       </button>
//     </div>
//   </div>
// )}

// {lastErrorMessage && (
//   <div key={actionMessageKey} className="relative z-20">
//     <div className="bg-red-100 border border-red-300 text-red-800 px-6 py-4 rounded-xl shadow-md flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-300" role="status">
//       <div className="flex items-center gap-3">
//         <XCircle size={20} className="flex-shrink-0" />
//         <span className="text-sm font-medium">{lastErrorMessage}</span>
//       </div>
//       <button onClick={() => setLastErrorMessage(null)} className="p-1 rounded-full text-red-700 hover:bg-red-200 transition-colors" aria-label="Dismiss notification">
//         <X size={16} />
//       </button>
//     </div>
//   </div>
// )}




//             {jobs.length === 0 ? (
//                 <div className="text-center py-20 border-2 border-dashed border-gray-300 rounded-xl bg-gray-50">
//                     <Briefcase size={48} className="mx-auto text-gray-400" />
//                     <h3 className="mt-4 text-lg font-semibold text-gray-700">No Active Jobs Found</h3>
//                     <p className="mt-1 text-sm text-gray-500">Please create a job post</p>
//                 </div>
//             ) : (
//                 jobs.map(job => (
//                     <div key={job.job_id} className="border border-gray-200 rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-300">
                        
//                         {/* Job Header (Clickable) */}
//                         <div 
//                             className={clsx(
//                                 "flex items-center justify-between p-4 sm:p-6 cursor-pointer transition-all duration-200",
//                                 expandedJobId === job.job_id ? "bg-indigo-50/70 border-b border-indigo-200" : "bg-white hover:bg-gray-50/50"
//                             )}
//                             onClick={() => handleJobToggle(job.job_id)}
//                         >
//                             <div className="flex items-center gap-4">
//                                 <h3 className="text-lg font-bold text-gray-900">{job.job_title}</h3>
//                                 <span className="px-3 py-1 text-xs font-medium bg-indigo-100 text-indigo-700 rounded-full border border-indigo-200">
//                                     Applied Candidates count:{job.total_applied} 
//                                 </span>
//                             </div>
//                             <ChevronDown size={24} className={clsx("text-gray-500 transition-transform duration-300", expandedJobId === job.job_id ? "rotate-180" : "rotate-0")} />
//                         </div>

//                         {/* Job Content (Expandable) */}
//                         {expandedJobId === job.job_id && (
//                             <div className="p-4 sm:p-6 bg-white space-y-6">
                                
//                                 {/* Round Tabs/Navigation */}
//                                 <div className="border-b border-gray-100 pb-3">
//                                     <div className="flex justify-between items-center mb-2">
//                                         <h4 className="text-sm font-bold text-gray-700">Interview Rounds:</h4>
                                        
//                                         {currentJob && currentRound && (
//                                             <Button 
//                                                 onClick={openScheduleModal}
//                                                 variant="primary"
//                                                 className="px-4 py-2 text-sm flex items-center gap-2 rounded-full bg-green-600 hover:bg-green-700"
//                                                 disabled={roundCandidates.filter(c => c.round_status === 'shortlisted').length === 0}
//                                                 title={roundCandidates.filter(c => c.round_status === 'shortlisted').length === 0 ? `No candidates shortlisted in ${currentRound.round_name}` : `Schedule interviews for candidates in ${currentRound.round_name}`}
//                                             >
//                                                 <Calendar size={16} /> Schedule Interview
//                                             </Button>
//                                         )}
//                                     </div>
//                                     <div className="flex flex-wrap gap-3">
//                                         {job.rounds.map(round => {
//                                             const isActive = selectedRoundId === round.round_id;
//                                             return (
//                                                 <button
//                                                     key={round.round_id}
//                                                     onClick={() => handleRoundChange(job.job_id, round.round_id)}
//                                                     className={clsx(
//                                                         "px-4 py-2 text-sm font-medium rounded-lg transition-all duration-150 flex items-center gap-2 border",
//                                                         isActive 
//                                                             ? "bg-indigo-600 text-white border-indigo-600 shadow-md"
//                                                             : "bg-white text-gray-700 hover:bg-indigo-50 border-gray-300"
//                                                     )}
//                                                 >
//                                                     {round.round_name}
//                                                     <span className={clsx(
//                                                         "ml-1 px-2 py-0.5 text-xs rounded-full font-bold",
//                                                         isActive ? "bg-white text-indigo-600" : "bg-gray-100 text-gray-700"
//                                                     )}>
//                                                         {round.total_candidates}
//                                                     </span>
//                                                 </button>
//                                             );
//                                         })}
//                                     </div>
//                                 </div>
                                
//                                 {/* Round Stats / Filters */}
//                                 {job.rounds.find(r => r.round_id === selectedRoundId) && (
//                                     <RoundStats round={job.rounds.find(r => r.round_id === selectedRoundId)!} />
//                                 )}

//                                 {/* Candidate List */}
//                                 <div className="space-y-4">
//                                     <h4 className="text-lg font-bold text-gray-800 border-b border-gray-100 pb-2">
//                                         Candidates in: <span className="text-blue-600">{job.rounds.find(r => r.round_id === selectedRoundId)?.round_name ?? 'Select Round'}</span>
//                                     </h4>
//                                     {candidatesLoading ? (
//                                         <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-lg">
//                                             <Loader2 size={24} className="inline animate-spin mr-2 text-indigo-500" /> Fetching candidates for round...
//                                         </div>
//                                     ) : roundCandidates.length === 0 ? (
//                                         <div className="text-center py-10 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
//                                             <AlertTriangle size={24} className="mx-auto mb-2 text-gray-400"/>
//                                             No candidates in this round yet.
//                                         </div>
//                                     ) : (
//                                         <div className="space-y-3">
//                                             {roundCandidates.map(candidate => (
//                                                 <CandidateListItem 
//                                                     key={candidate.profile_id} 
//                                                     candidate={candidate} 
//                                                     onViewDetails={() => setSelectedCandidate(candidate)}
//                                                     onStatusChangeClick={() => setStatusModalCandidate(candidate)}
//                                                 />
//                                             ))}
//                                         </div>
//                                     )}
//                                 </div>
//                             </div>
//                         )}
//                     </div>
//                 ))
//             )}
            
//             {/* Candidate Detail Modal */}
//             {selectedCandidate && (
//                 <CandidateDetailModal candidate={selectedCandidate} onClose={() => setSelectedCandidate(null)} />
//             )}

//             {/* Candidate Status Update Modal */}
//             {statusModalCandidate && (
//                 <CandidateStatusModal
//                     isOpen={!!statusModalCandidate}
//                     candidate={statusModalCandidate}
//                     onClose={() => setStatusModalCandidate(null)}
//                     onStatusUpdate={handleStatusUpdate}
//                     isProcessing={isStatusUpdating}
//                 />

//             )}
            
//             {/* Schedule Interview Modal */}
//             {scheduleModalData && (
//                 <ScheduleInterviewModal
//                     isOpen={!!scheduleModalData}
//                     data={scheduleModalData}
//                     onClose={() => setScheduleModalData(null)}
//                     onSchedule={handleScheduleInterview}
//                     isScheduling={isScheduling}
//                 />
//             )}
//         </div>
//     );
// };


// // --- WRAPPER FOR LAYOUT INTEGRATION (Default Export) ---
// const JobRecruitmentPage: React.FC = () => {
//     return (
//         <Layout
//             bannerTitle="Job Recruitment"
//             bannerSubtitle="Track candidate progress across the hiring pipeline"
//             searchPlaceholder="Search jobs..."
//         >
//             <JobRecruitmentPageContent />
//         </Layout>
//     );
// };

// export default JobRecruitmentPage;
