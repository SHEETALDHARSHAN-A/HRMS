// // // src/components/common/ScheduleInterviewModal.tsx

// // import React, { useState, useEffect, useMemo} from 'react';
// // import { 
// //     Loader2, Calendar, Clock, Zap, Users, Check,
// //     AlertTriangle, Send, Star, Settings,  XCircle
// // } from 'lucide-react';
// // import clsx from 'clsx';
// // import Button from './Button';
// // import { useToast } from '../../context/ModalContext'; // For internal error messages
// // import type { Candidate, InterviewLevel, InterviewType } from '../../api/recruitmentApi'; 

// // // --- NEW INTERFACE: Email Template (moved from index.tsx) ---
// // interface EmailTemplate {
// //     subject: string;
// //     body: string;
// // }

// // // --- NEW MOCK: Interface for minimal Job Details (moved from index.tsx) ---
// // interface JobTypeDetails {
// //     interview_type: 'agent' | 'offline' | 'hybrid';
// // }

// // // --- UPDATED: Schedule Interview Modal Data (moved from index.tsx) ---
// // interface ScheduleModalData {
// //     jobId: string;
// //     jobTitle: string;
// //     roundId: string;
// //     roundName: string;
// //     candidates: Candidate[];
// //     jobDetails: JobTypeDetails | null; 
// //     emailTemplate: EmailTemplate;
// // }

// // interface ScheduleInterviewModalProps {
// //     data: ScheduleModalData;
// //     isOpen: boolean;
// //     onClose: () => void;
// //     onSchedule: (scheduleData: { 
// //         jobId: string, 
// //         roundId: string, 
// //         profileIds: string[], 
// //         dateTime: string, 
// //         level: InterviewLevel, 
// //         type: InterviewType,
// //         emailSubject: string, 
// //         emailBody: string 
// //     }) => Promise<void>;
// //     isScheduling: boolean;
// // }

// // // --- Utility: Generates default email content (moved from index.tsx) ---
// // const generateDefaultEmailContent = (
// //     roundName: string, 
// //     jobTitle: string, 
// //     interviewType: 'agent' | 'offline' | 'hybrid'
// // ): EmailTemplate => {
    
// //     const defaultSubject = `Interview Invitation - {JOB_TITLE} | shortlisted in {ROUND_NAME} `;

// //     const defaultBody = `Dear **{CANDIDATE_NAME}**,

// // Congratulations! We are delighted to inform you that you have been shortlisted in the **{ROUND_NAME}** round for the **{JOB_TITLE}** position.

// // ### Interview Schedule:

// // **Position:** {JOB_TITLE}
// // **Next Round:** {NEXT_ROUND_NAME}
// // **Date:** {DATE}
// // **Time:** {TIME}

// // ### Interview Access Details:

// // * **Interview Link:** {INTERVIEW_LINK}
// // * **Room ID:** {INTERVIEW_TOKEN}


// // Please make sure to attend the interview on time from the provided link.
// // Should you have any questions or need to reschedule, please don't hesitate to reach out to us.

// // Best regards,

// // **Prayag RMS Team**
// // `;

// //     return {
// //         subject: defaultSubject.replace(/{JOB_TITLE}/g, jobTitle).replace(/{ROUND_NAME}/g, roundName),
// //         body: defaultBody,      
// //     };
// // };
// // // --- END Utilities ---


// // const ScheduleInterviewModal: React.FC<ScheduleInterviewModalProps> = ({ isOpen, data, onClose, onSchedule, isScheduling }) => {
// //     const { showToast } = useToast();
// //     const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);
// //     const [interviewDate, setInterviewDate] = useState(''); 
// //     const [interviewTime, setInterviewTime] = useState('');
// //     const [emailSubject, setEmailSubject] = useState(''); 
// //     const [emailBody, setEmailBody] = useState(''); 
// //     const [activeConfigTab, setActiveConfigTab] = useState<'schedule' | 'email'>('schedule'); 
// //     const [level, setLevel] = useState<InterviewLevel>('Medium'); 
// //     const [type, setType] = useState<InterviewType>('Agent_interview'); 
// //     const [scoreFilter, setScoreFilter] = useState<number>(0); 

// //     const mapJobPostTypeToApiType = (jobType: JobTypeDetails['interview_type']): InterviewType => {
// //         if (jobType === 'agent') return 'Agent_interview';
// //         if (jobType === 'offline' || jobType === 'hybrid') return 'In_person'; 
// //         return 'Agent_interview'; // Default fallback
// //     };
    
// //     useEffect(() => {
// //         if (isOpen) {
// //             const defaultJobPostType = data.jobDetails 
// //                 ? mapJobPostTypeToApiType(data.jobDetails.interview_type) 
// //                 : 'Agent_interview';

// //             const now = new Date();
// //             const tomorrow = new Date(now.setDate(now.getDate() + 1)).toISOString().substring(0, 10);
            
// //             setType(defaultJobPostType);
// //             setSelectedCandidates([]); 
// //             setInterviewDate(tomorrow); 
// //             setInterviewTime('10:00'); 
// //             setLevel('Medium'); 
// //             setScoreFilter(0);
// //             setEmailSubject(data.emailTemplate.subject); 
// //             setEmailBody(data.emailTemplate.body); 
// //             setActiveConfigTab('schedule');
// //         }
// //     }, [isOpen, data]);

// //     if (!isOpen) return null;

// //     const currentJobPostType = data.jobDetails 
// //         ? mapJobPostTypeToApiType(data.jobDetails.interview_type)
// //         : 'Agent_interview'; 
    
// //     const allShortlistedCandidates = useMemo(() => 
// //         data.candidates.filter(c => c.round_status === 'shortlisted'), 
// //         [data.candidates]
// //     );

// //     const filteredCandidates = useMemo(() => {
// //         if (scoreFilter === 0) return allShortlistedCandidates;
// //         return allShortlistedCandidates.filter(c => c.overall_score >= scoreFilter);
// //     }, [allShortlistedCandidates, scoreFilter]);


// //     const handleToggleCandidate = (profileId: string) => {
// //         setSelectedCandidates(prev => {
// //             if (prev.includes(profileId)) {
// //                 return prev.filter(id => id !== profileId);
// //             }
// //             return [...prev, profileId];
// //         });
// //     };
    
// //     const handleSelectAll = () => {
// //         const allIds = filteredCandidates.map(c => c.profile_id);
// //         const allCurrentlySelected = selectedCandidates.length === filteredCandidates.length && selectedCandidates.every(id => allIds.includes(id));

// //         if (allCurrentlySelected) {
// //             setSelectedCandidates([]); // Deselect All
// //         } else {
// //             setSelectedCandidates(allIds); // Select All
// //         }
// //     };
    
// //     const handleSubmit = (e: React.FormEvent) => {
// //         e.preventDefault();
        
// //         const combinedDateTime = `${interviewDate}T${interviewTime}`; 
        
// //         if (selectedCandidates.length === 0 || !combinedDateTime || !emailSubject.trim() || !emailBody.trim() || isScheduling) {
// //             showToast("Please select candidates, set a date/time, and ensure email fields are filled.", "warning");
// //             return;
// //         }

// //         const apiType = type === 'Agent_interview' ? 'Agent_interview' : 'In_person'; 
        
        
// //         onSchedule({
// //             jobId: data.jobId,
// //             roundId: data.roundId,
// //             profileIds: selectedCandidates,
// //             dateTime: combinedDateTime,
// //             level,
// //             type: apiType, 
// //             emailSubject: emailSubject.trim(), 
// //             emailBody: emailBody.trim(),       
// //         });
// //     };
    
// //     const interviewLevels: InterviewLevel[] = ['Easy', 'Medium', 'Hard'];
// //     const interviewTypeOptions = [
// //         { value: 'Agent_interview', label: 'Agent Interview (Remote/AI)' },
// //         { value: 'In_person', label: 'In Person / Offline' },
// //         { value: 'Hybrid', label: 'Hybrid (Remote & In Person)' }, 
// //     ];

// //     const scoreFilterOptions = [
// //         { value: 0, label: 'All Shortlisted' },
// //         { value: 25, label: '25% Score and above' },
// //         { value: 50, label: '50% Score and above' },
// //         { value: 75, label: '75% Score and above' },
// //     ];

// //     const isSubmitDisabled = isScheduling || selectedCandidates.length === 0 || !interviewDate.trim() || !interviewTime.trim() || !emailSubject.trim() || !emailBody.trim();
// //     const isAllSelected = selectedCandidates.length === filteredCandidates.length && filteredCandidates.length > 0;
    
// //     return (
// //         <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
// //             <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto transform transition-all duration-300 scale-100 opacity-100" onClick={(e) => e.stopPropagation()}>
// //                 <form onSubmit={handleSubmit}>
// //                     {/* Header */}
// //                     <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center z-10">
// //                         <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
// //                             <Calendar size={24} className="text-indigo-600" />
// //                             <span className="text-indigo-600 italic">{data.jobTitle} - {data.roundName}</span>
// //                         </h2>
// //                         <button type="button" onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 text-gray-500"><XCircle size={20} /></button>
// //                     </div>

// //                     <div className={clsx(
// //                         "p-6 grid gap-8",
// //                         activeConfigTab === 'email' ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-3"
// //                     )}>
                        
// //                         {/* Column 1: Configuration (Expands on Email Tab) */}
// //                         <div className={clsx(
// //                              "space-y-6",
// //                              activeConfigTab === 'email' ? "lg:col-span-3" : "lg:col-span-1" 
// //                         )}>
// //                             <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2"><Settings size={20} className="text-gray-500"/> Configuration</h3> 
                            
// //                             {/* Configuration Tabs */}
// //                             <div className="flex w-full rounded-xl border-2 p-1 bg-gray-100 border-gray-200">
// //                                 <button
// //                                     type="button"
// //                                     onClick={() => setActiveConfigTab('schedule')}
// //                                     className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
// //                                         activeConfigTab === 'schedule'
// //                                             ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
// //                                             : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
// //                                     }`}
// //                                 >
// //                                     <Clock size={16} /> Scheduling
// //                                 </button>
// //                                 <button
// //                                     type="button"
// //                                     onClick={() => setActiveConfigTab('email')}
// //                                     className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
// //                                         activeConfigTab === 'email'
// //                                             ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
// //                                             : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
// //                                     }`}
// //                                 >
// //                                     <Send size={16} /> Email
// //                                 </button>
// //                             </div>

// //                             {/* Tab Content: SCHEDULING */}
// //                             {activeConfigTab === 'schedule' && (
// //                                 <div className="space-y-6">
// //                                     <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200 text-center">
// //                                         <p className="text-xs font-medium text-indigo-700 mb-1">Candidates to Schedule</p>
// //                                         <p className="text-4xl font-extrabold text-indigo-900">{selectedCandidates.length}</p>
// //                                     </div>
                                    
// //                                     <div className='bg-gray-50 p-4 rounded-lg border space-y-4'>
// //                                         <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Clock size={16} /> Date & Time *</label>
                                        
// //                                         <div className="space-y-3">
// //                                             <div>
// //                                                 <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
// //                                                 <input
// //                                                     type="date" 
// //                                                     value={interviewDate}
// //                                                     onChange={(e) => setInterviewDate(e.target.value)}
// //                                                     min={new Date().toISOString().substring(0, 10)}
// //                                                     className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
// //                                                     required
// //                                                 />
// //                                             </div>

// //                                             <div>
// //                                                 <label className="block text-xs font-medium text-gray-600 mb-1">Time</label>
// //                                                 <input
// //                                                     type="time" 
// //                                                     value={interviewTime}
// //                                                     onChange={(e) => setInterviewTime(e.target.value)}
// //                                                     step="300" 
// //                                                     className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
// //                                                     required
// //                                                 />
// //                                             </div>
// //                                         </div>
// //                                         <p className="text-xs text-gray-500 mt-1">Interviews must be scheduled for a future date and time.</p>
// //                                     </div>
                                    
// //                                     <div className='bg-gray-50 p-4 rounded-lg border'>
// //                                         <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Users size={16} /> Interview Type *</label>
// //                                         <select
// //                                             value={type}
// //                                             onChange={(e) => setType(e.target.value as InterviewType)}
// //                                             className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base bg-white focus:ring-indigo-500 focus:border-indigo-500"
// //                                         >
// //                                             {interviewTypeOptions.map(option => (
// //                                                 <option key={option.value} value={option.value}>{option.label}</option>
// //                                             ))}
// //                                         </select>
// //                                         <p className="text-xs text-gray-500 mt-1">Default type based on job post: <strong className="text-indigo-600">{currentJobPostType === 'Agent_interview' ? 'Agent Interview' : 'In Person / Offline'}</strong></p>
// //                                     </div>

// //                                     {type === 'Agent_interview' && (
// //                                         <div className="space-y-1 bg-gray-50 p-4 rounded-lg border border-yellow-200">
// //                                             <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Zap size={16} /> Agent Interview Level *</label>
// //                                             <select
// //                                                 value={level}
// //                                                 onChange={(e) => setLevel(e.target.value as InterviewLevel)}
// //                                                 className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base bg-white focus:ring-yellow-500 focus:border-yellow-500"
// //                                             >
// //                                                 {interviewLevels.map(l => <option key={l} value={l}>{l}</option>)}
// //                                             </select>
// //                                             <p className="text-xs text-gray-500 mt-1">Required to set difficulty for AI interviews.</p>
// //                                         </div>
// //                                     )}
// //                                 </div>
// //                             )}

// //                             {/* Tab Content: EMAIL CONFIGURATION */}
// //                             {activeConfigTab === 'email' && (
// //                                 <div className="space-y-6">
// //                                     <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg border border-indigo-200 p-5">
// //                                         <div className="flex items-start gap-3">
// //                                             <div className="flex-shrink-0 w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center">
// //                                                 <AlertTriangle size={16} className="text-white" />
// //                                             </div>
// //                                             <div className="flex-1">
// //                                                 <h4 className="text-sm font-bold text-indigo-900 mb-2">Dynamic Placeholders - How They Work</h4>
// //                                                 <p className="text-xs text-indigo-800 mb-3">
// //                                                     Placeholders like <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-600 text-white text-xs font-mono">{'\{CANDIDATE_NAME\}'}</span> are automatically replaced with real data when emails are sent. You can edit all content freely — just keep placeholder format exact (uppercase with braces).
// //                                                 </p>
// //                                                 <div className="grid grid-cols-2 gap-2 text-xs">
// //                                                     <div className="flex items-center gap-1.5">
// //                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{CANDIDATE_NAME\}'}</span>
                                                        
// //                                                     </div>
// //                                                     <div className="flex items-center gap-1.5">
// //                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{JOB_TITLE\}'}</span>
                                                        
// //                                                     </div>
// //                                                     <div className="flex items-center gap-1.5">
// //                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{ROUND_NAME\}'}</span>
                                                        
// //                                                     </div>
// //                                                     <div className="flex items-center gap-1.5">
// //                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{DATE\}'}</span>
                                                        
// //                                                     </div>
// //                                                     <div className="flex items-center gap-1.5">
// //                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{TIME\}'}</span>
                                                        
// //                                                     </div>
// //                                                     <div className="flex items-center gap-1.5">
// //                                                         <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'\{INTERVIEW_LINK\}'}</span>
                                                       
// //                                                     </div>
// //                                                 </div>
// //                                             </div>
// //                                         </div>
// //                                     </div>
                                    
// //                                     {/* Email Subject */}
// //                                     <div className="space-y-2">
// //                                         <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
// //                                             <Send size={16} className="text-indigo-600" />
// //                                             Email Subject *
// //                                         </label>
// //                                         <div className="relative">
// //                                             <input
// //                                                 type="text"
// //                                                 value={emailSubject}
// //                                                 onChange={(e) => setEmailSubject(e.target.value)}
// //                                                 placeholder="e.g., Interview Invitation for {JOB_TITLE}"
// //                                                 className="w-full border-2 border-gray-300 rounded-lg px-4 py-3 text-base focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all placeholder:text-gray-400"
// //                                                 required
// //                                             />
// //                                         </div>
// //                                     </div>
                                    
// //                                     {/* Email Body with Enhanced Editor */}
// //                                     <div className="space-y-2">
// //                                         <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
// //                                             <Settings size={16} className="text-indigo-600" />
// //                                             Email Body - The preview below shows how the email will look to candidates *
// //                                         </label>
                                        
// //                                         <div className="relative">
// //                                             <textarea
// //                                                 rows={16}
// //                                                 value={emailBody}
// //                                                 onChange={(e) => setEmailBody(e.target.value)}
// //                                                 placeholder="Dear {CANDIDATE_NAME},&#10;&#10;We are pleased to inform you..."
// //                                                 className="w-full p-4 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-y font-mono text-sm leading-relaxed placeholder:text-gray-400 placeholder:font-sans"
// //                                                 required
// //                                                 style={{
// //                                                     background: 'linear-gradient(to bottom, #ffffff 0%, #fafafa 100%)',
// //                                                 }}
// //                                             />
// //                                             <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-white/80 px-2 py-1 rounded">
// //                                                 {emailBody.length} characters
// //                                             </div>
// //                                         </div>
// //                                     </div>

// //                                    {/* Preview Section */}
// //                                     <div className="border-t-2 border-gray-200 pt-6">
// //                                         <div className="flex items-center justify-between mb-3">
// //                                             <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
// //                                                 <Users size={16} className="text-indigo-600" />
// //                                                 Email Preview
// //                                             </label>
                                          
// //                                         </div>
// //                                         <div className="bg-white border-2 border-gray-200 rounded-lg overflow-hidden shadow-sm">
// //                                             {/* Email Header */}
// //                                             <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 border-b border-gray-200">
// //                                                 <div className="space-y-2">
// //                                                     <div className="flex items-start gap-3">
// //                                                         <span className="text-xs font-medium text-gray-500 w-16">Subject:</span>
// //                                                         <span className="flex-1 font-semibold text-gray-900 text-sm">
// //                                                             {emailSubject 
// //                                                                 .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
// //                                                                 .replace(/{JOB_TITLE}/g, data.jobTitle)
// //                                                                 .replace(/{ROUND_NAME}/g, data.roundName)
// //                                                                 .replace(/{DATE}/g, 'November 20, 2025')
// //                                                                 .replace(/{TIME}/g, '2:00 PM')
// //                                                                 .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
// //                                                                 .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
// //                                                                 .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
// //                                                                 .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
// //                                                              || 'No subject provided'}
// //                                                         </span>
// //                                                     </div>
// //                                                     <div className="flex items-start gap-3">
// //                                                         <span className="text-xs font-medium text-gray-500 w-16">To:</span>
// //                                                         <span className="flex-1 text-sm text-gray-700">sarah.johnson@email.com</span>
// //                                                     </div>
// //                                                 </div>
// //                                             </div>
                                            
                                       
// // <div className="p-6 bg-white">
// //     <div 
// //         className="text-sm text-gray-800 leading-relaxed"
// //         style={{ 
// //             fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
// //             wordBreak: 'break-word'
// //         }}
// //     >
// //         {emailBody ? (
// //             <div
// //                 dangerouslySetInnerHTML={{
// //                     __html: emailBody
// //                         .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
// //                         .replace(/{JOB_TITLE}/g, data.jobTitle)
// //                         .replace(/{ROUND_NAME}/g, data.roundName)
// //                         .replace(/{DATE}/g, 'November 20, 2025')
// //                         .replace(/{TIME}/g, '2:00 PM')
// //                         .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
// //                         .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
// //                         .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
// //                         .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
// //                         .replace(/\n\n/g, '<br><br>') 
// //                         .replace(/\n/g, '<br>') 
// //                         .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
// //                         .replace(/### (.*?)<br>/g, '<h3>$1</h3>')
// //                 }}
// //             />
// //         ) : (
// //             <span className="text-gray-400 italic">Email body will appear here...</span>
// //         )}
// //     </div>
// // </div>

                                            
// //                                         </div>
// //                                         <p className="text-xs text-gray-500 mt-3 flex items-center gap-1">
// //                                             <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full"></span>
// //                                             Preview shows sample data. Actual emails will use real candidate information.
// //                                         </p>
// //                                     </div>
// //                                 </div>
// //                             )}

// //                         </div>
                        
// //                         {/* Column 2: Candidates List (Hidden on Email Tab) */}
// //                         {activeConfigTab === 'schedule' && (
// //                             <div className="lg:col-span-2 space-y-4">
// //                                 <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2"><Users size={20} className="text-gray-500"/> Candidates Selection</h3>

// //                                 <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200 gap-3">
// //                                     <p className="text-sm text-gray-700 font-medium">
// //                                         <span className="font-bold text-green-600">{allShortlistedCandidates.length}</span> candidates are ready for scheduling.
// //                                         <span className="ml-3 text-xs text-gray-500">Showing <strong className="text-gray-800">{filteredCandidates.length}</strong> candidates.</span>
// //                                     </p>
// //                                     <div className="flex items-center gap-2 text-sm flex-shrink-0">
// //                                         <label className="text-gray-600 font-medium">Filter:</label>
// //                                         <select 
// //                                             value={scoreFilter}
// //                                             onChange={(e) => setScoreFilter(Number(e.target.value))}
// //                                             className="border border-gray-300 rounded-md px-2 py-1 bg-white text-sm focus:ring-indigo-500 focus:border-indigo-500"
// //                                         >
// //                                             {scoreFilterOptions.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
// //                                         </select>
// //                                     </div>
// //                                 </div>
                                
// //                                 <Button 
// //                                     type="button" 
// //                                     onClick={handleSelectAll} 
// //                                     variant="outline" 
// //                                     disabled={filteredCandidates.length === 0}
// //                                     className="w-full py-2.5 text-sm flex items-center justify-center gap-2 text-indigo-600 border-indigo-300 hover:bg-indigo-50"
// //                                 >
// //                                     <Check size={16} /> 
// //                                     {isAllSelected ? 'Deselect All' : `Select All (${filteredCandidates.length} filtered)`}
// //                                 </Button>

// //                                 <div className="max-h-80 overflow-y-auto pr-2 space-y-2">
// //                                     {filteredCandidates.length === 0 ? (
// //                                         <div className="text-center py-10 text-gray-500 bg-gray-50 rounded-lg border border-dashed">
// //                                             <AlertTriangle size={24} className="mx-auto mb-2 text-gray-400"/>
// //                                             <div className="text-sm">No candidates match the current filters.</div>
// //                                         </div>
// //                                     ) : (
// //                                         filteredCandidates.map(candidate => (
// //                                             <div 
// //                                                 key={candidate.profile_id} 
// //                                                 onClick={() => handleToggleCandidate(candidate.profile_id)}
// //                                                 className={clsx(
// //                                                     "p-3 rounded-lg border cursor-pointer transition-all duration-200 flex justify-between items-center group",
// //                                                     selectedCandidates.includes(candidate.profile_id) 
// //                                                         ? "bg-indigo-100/70 border-indigo-400 shadow-md" 
// //                                                         : "bg-white border-gray-200 hover:bg-gray-50"
// //                                                 )}
// //                                             >
// //                                                 <div className="flex items-center gap-3">
// //                                                     <div className={clsx(
// //                                                         "w-5 h-5 rounded flex items-center justify-center border transition-colors flex-shrink-0",
// //                                                         selectedCandidates.includes(candidate.profile_id) ? "bg-indigo-600 border-indigo-600 text-white" : "bg-white border-gray-300 group-hover:border-indigo-400"
// //                                                     )}>
// //                                                         {selectedCandidates.includes(candidate.profile_id) && <Check size={14} />}
// //                                                     </div>
// //                                                     <div>
// //                                                         <span className="font-medium text-gray-900 block">{candidate.candidate_name}</span>
// //                                                         <span className="text-xs text-gray-500 flex items-center gap-1 mt-0.5"><Star size={12} className="text-yellow-500"/> {candidate.overall_score}% Match</span>
// //                                                     </div>
// //                                                 </div>
// //                                                 <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-1 rounded-full flex-shrink-0">Shortlisted</span>
// //                                             </div>
// //                                         ))
// //                                     )}
// //                                 </div>
// //                             </div>
// //                         )}
// //                     </div>

// //                     {/* Footer / Submit Button */}
// //                     <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6 flex justify-end gap-3 z-10">
// //                         <Button type="button" variant="secondary" onClick={onClose} disabled={isScheduling}>
// //                             Cancel
// //                         </Button>
// //                         <Button type="submit" variant="primary" disabled={isSubmitDisabled}>
// //                             {isScheduling ? (
// //                                 <><Loader2 size={16} className="animate-spin mr-2" /> Submitting...</>
// //                             ) : (
// //                                 <><Send size={16} className="mr-2"/> Schedule {selectedCandidates.length} Interview(s)</>
// //                             )}
// //                         </Button>
// //                     </div>
// //                 </form>
// //             </div>
// //         </div>
// //     );
// // };

// // export default ScheduleInterviewModal;
// // export { generateDefaultEmailContent, type JobTypeDetails, type ScheduleModalData };


// // src/components/common/ScheduleInterviewModal.tsx

// import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
// import { 
//     Loader2, Calendar, Clock, Zap, Users, Check,
//     AlertTriangle, Send, Star, Settings, CheckCircle, XCircle, X
// } from 'lucide-react';
// import clsx from 'clsx';
// import Button from './Button';
// import { useToast } from '../../context/ModalContext'; // For internal error messages
// import type { Candidate, InterviewLevel, InterviewType } from '../../api/recruitmentApi'; 

// // --- NEW INTERFACE: Email Template (moved from index.tsx) ---
// interface EmailTemplate {
//     subject: string;
//     body: string;
// }

// // --- NEW MOCK: Interface for minimal Job Details (moved from index.tsx) ---
// interface JobTypeDetails {
//     interview_type: 'agent' | 'offline' | 'hybrid';
// }

// // --- UPDATED: Schedule Interview Modal Data (moved from index.tsx) ---
// interface ScheduleModalData {
//     jobId: string;
//     jobTitle: string;
//     roundId: string;
//     roundName: string;
//     candidates: Candidate[];
//     jobDetails: JobTypeDetails | null; 
//     emailTemplate: EmailTemplate;
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
//         emailSubject: string, 
//         emailBody: string 
//     }) => Promise<void>;
//     isScheduling: boolean;
// }

// // --- Utility: Generates default email content (FIXED TO BE PLAIN TEXT) ---
// const generateDefaultEmailContent = (
//     roundName: string, 
//     jobTitle: string, 
//     interviewType: 'agent' | 'offline' | 'hybrid'
// ): EmailTemplate => {
    
//     const defaultSubject = `Interview Invitation - {JOB_TITLE} | shortlisted in {ROUND_NAME} `;

//     // FIX: Removed all ** and ### symbols. Use simple formatting.
//     const defaultBody = `Dear {CANDIDATE_NAME},

// Congratulations! We are delighted to inform you that you have been shortlisted in the {ROUND_NAME} round for the {JOB_TITLE} position.

// --- Interview Schedule ---

// Position: {JOB_TITLE}
// Next Round: {NEXT_ROUND_NAME}
// Date: {DATE}
// Time: {TIME}

// --- Interview Access Details ---

// - Interview Link: {INTERVIEW_LINK}
// - Room ID: {INTERVIEW_TOKEN}


// Please make sure to attend the interview on time from the provided link.
// Should you have any questions or need to reschedule, please don't hesitate to reach out to us.

// Best regards,

// Prayag RMS Team
// `;

//     return {
//         subject: defaultSubject.replace(/{JOB_TITLE}/g, jobTitle).replace(/{ROUND_NAME}/g, roundName),
//         body: defaultBody,      
//     };
// };
// // --- END Utilities ---


// const ScheduleInterviewModal: React.FC<ScheduleInterviewModalProps> = ({ isOpen, data, onClose, onSchedule, isScheduling }) => {
//     const { showToast } = useToast();
//     const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);
//     const [interviewDate, setInterviewDate] = useState(''); 
//     const [interviewTime, setInterviewTime] = useState('');
//     const [emailSubject, setEmailSubject] = useState(''); 
//     const [emailBody, setEmailBody] = useState(''); 
//     const [activeConfigTab, setActiveConfigTab] = useState<'schedule' | 'email'>('schedule'); 
//     const [level, setLevel] = useState<InterviewLevel>('Medium'); 
//     const [type, setType] = useState<InterviewType>('Agent_interview'); 
//     const [scoreFilter, setScoreFilter] = useState<number>(0); 

//     const mapJobPostTypeToApiType = (jobType: JobTypeDetails['interview_type']): InterviewType => {
//         if (jobType === 'agent') return 'Agent_interview';
//         if (jobType === 'offline' || jobType === 'hybrid') return 'In_person'; 
//         return 'Agent_interview'; // Default fallback
//     };
    
//     useEffect(() => {
//         if (isOpen) {
//             const defaultJobPostType = data.jobDetails 
//                 ? mapJobPostTypeToApiType(data.jobDetails.interview_type) 
//                 : 'Agent_interview';

//             const now = new Date();
//             const tomorrow = new Date(now.setDate(now.getDate() + 1)).toISOString().substring(0, 10);
            
//             setType(defaultJobPostType);
//             setSelectedCandidates([]); 
//             setInterviewDate(tomorrow); 
//             setInterviewTime('10:00'); 
//             setLevel('Medium'); 
//             setScoreFilter(0);
//             setEmailSubject(data.emailTemplate.subject); 
//             setEmailBody(data.emailTemplate.body); 
//             setActiveConfigTab('schedule');
//         }
//     }, [isOpen, data]);

//     if (!isOpen) return null;

//     const currentJobPostType = data.jobDetails 
//         ? mapJobPostTypeToApiType(data.jobDetails.interview_type)
//         : 'Agent_interview'; 
    
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
        
//         const combinedDateTime = `${interviewDate}T${interviewTime}`; 
        
//         if (selectedCandidates.length === 0 || !combinedDateTime || !emailSubject.trim() || !emailBody.trim() || isScheduling) {
//             showToast("Please select candidates, set a date/time, and ensure email fields are filled.", "warning");
//             return;
//         }

//         const apiType = type === 'Agent_interview' ? 'Agent_interview' : 'In_person'; 
        
//         onSchedule({
//             jobId: data.jobId,
//             roundId: data.roundId,
//             profileIds: selectedCandidates,
//             dateTime: combinedDateTime,
//             level,
//             type: apiType, 
//             emailSubject: emailSubject.trim(), 
//             emailBody: emailBody.trim(),       
//         });
//     };
    
//     const interviewLevels: InterviewLevel[] = ['Easy', 'Medium', 'Hard'];
//     const interviewTypeOptions = [
//         { value: 'Agent_interview', label: 'Agent Interview (Remote/AI)' },
//         { value: 'In_person', label: 'In Person / Offline' },
//         { value: 'Hybrid', label: 'Hybrid (Remote & In Person)' }, 
//     ];

//     const scoreFilterOptions = [
//         { value: 0, label: 'All Shortlisted' },
//         { value: 25, label: '25% Score and above' },
//         { value: 50, label: '50% Score and above' },
//         { value: 75, label: '75% Score and above' },
//     ];

//     const isSubmitDisabled = isScheduling || selectedCandidates.length === 0 || !interviewDate.trim() || !interviewTime.trim() || !emailSubject.trim() || !emailBody.trim();
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

//                     <div className={clsx(
//                         "p-6 grid gap-8",
//                         activeConfigTab === 'email' ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-3"
//                     )}>
                        
//                         {/* Column 1: Configuration (Expands on Email Tab) */}
//                         <div className={clsx(
//                              "space-y-6",
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

//                             {/* Tab Content: SCHEDULING */}
//                             {activeConfigTab === 'schedule' && (
//                                 <div className="space-y-6">
//                                     <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200 text-center">
//                                         <p className="text-xs font-medium text-indigo-700 mb-1">Candidates to Schedule</p>
//                                         <p className="text-4xl font-extrabold text-indigo-900">{selectedCandidates.length}</p>
//                                     </div>
                                    
//                                     <div className='bg-gray-50 p-4 rounded-lg border space-y-4'>
//                                         <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Clock size={16} /> Date & Time *</label>
                                        
//                                         <div className="space-y-3">
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

//                             {/* Tab Content: EMAIL CONFIGURATION */}
//                             {activeConfigTab === 'email' && (
//                                 <div className="space-y-6">
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
//                                     </div>
                                    
//                                     {/* Email Body with Enhanced Editor */}
//                                     <div className="space-y-2">
//                                         <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
//                                             <Settings size={16} className="text-indigo-600" />
//                                             Email Body - The preview below shows how the email will look to candidates *
//                                         </label>
                                        
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
//                                             <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-white/80 px-2 py-1 rounded">
//                                                 {emailBody.length} characters
//                                             </div>
//                                         </div>
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
//         // FIX: Remove manual Markdown conversion and instead use white-space to preserve line breaks from the clean template.
//         style={{ 
//             fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
//             wordBreak: 'break-word',
//             whiteSpace: 'pre-wrap', // <-- CRITICAL FIX for preview display
//         }}
//     >
//         {emailBody ? (
//             // Now we send the emailBody content directly as text for preview, relying on pre-wrap
//             emailBody
//                 .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
//                 .replace(/{JOB_TITLE}/g, data.jobTitle)
//                 .replace(/{ROUND_NAME}/g, data.roundName)
//                 .replace(/{DATE}/g, 'November 20, 2025')
//                 .replace(/{TIME}/g, '2:00 PM')
//                 .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
//                 .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
//                 .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
//                 .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
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
//                 </form>
//             </div>
//         </div>
//     );
// };

// export default ScheduleInterviewModal;
// export { generateDefaultEmailContent, type JobTypeDetails, type ScheduleModalData };





// src/components/common/ScheduleInterviewModal.tsx

import React, { useState, useEffect, useMemo} from 'react';
import { 
    Loader2, Calendar, Clock, Zap, Users, Check,
    AlertTriangle, Send, Star, Settings,  XCircle
} from 'lucide-react';
import clsx from 'clsx';
import Button from './Button';
import { useToast } from '../../context/ModalContext'; // For internal error messages
import type { Candidate, InterviewLevel, InterviewType } from '../../api/recruitmentApi'; 

// --- NEW INTERFACE: Email Template (moved from index.tsx) ---
interface EmailTemplate {
    subject: string;
    body: string;
}

// --- NEW MOCK: Interface for minimal Job Details (moved from index.tsx) ---
interface JobTypeDetails {
    interview_type: 'agent' | 'offline' | 'hybrid';
}

// --- UPDATED: Schedule Interview Modal Data (moved from index.tsx) ---
interface ScheduleModalData {
    jobId: string;
    jobTitle: string;
    roundId: string;
    roundName: string;
    candidates: Candidate[];
    jobDetails: JobTypeDetails | null; 
    emailTemplate: EmailTemplate;
}

interface ScheduleInterviewModalProps {
    data: ScheduleModalData;
    isOpen: boolean;
    onClose: () => void;
    onSchedule: (scheduleData: { 
        jobId: string, 
        roundId: string, 
        profileIds: string[], 
        dateTime: string, 
        level: InterviewLevel, 
        type: InterviewType,
        emailSubject: string, 
        emailBody: string 
    }) => Promise<void>;
    isScheduling: boolean;
}

// --- Utility: Generates default email content (moved from index.tsx) ---
const generateDefaultEmailContent = (
    roundName: string, 
    jobTitle: string, 
    interviewType: 'agent' | 'offline' | 'hybrid'
): EmailTemplate => {
    
    const defaultSubject = `Interview Invitation - {JOB_TITLE} | shortlisted in {ROUND_NAME} `;
    const interviewModeLabel =
        interviewType === 'agent'
            ? 'AI Agent Interview'
            : interviewType === 'hybrid'
                ? 'Hybrid Interview'
                : 'In-Person Interview';

    const defaultBody = `Dear {CANDIDATE_NAME},

Congratulations! We are delighted to inform you that you have been shortlisted in the {ROUND_NAME} round for the {JOB_TITLE} position.

--- Interview Schedule ---

Position: {JOB_TITLE}
Next Round: {NEXT_ROUND_NAME}
Interview Mode: ${interviewModeLabel}
Date: {DATE}
Time: {TIME}

--- Interview Access Details ---

- Interview Link: {INTERVIEW_LINK}
- Room ID: {INTERVIEW_TOKEN}

Please make sure to attend the interview on time from the provided link.
Should you have any questions or need to reschedule, please don't hesitate to reach out to us.

Best regards,

RMS Team
`;

    return {
        subject: defaultSubject.replace(/{JOB_TITLE}/g, jobTitle).replace(/{ROUND_NAME}/g, roundName),
        body: defaultBody,      
    };
};
// --- END Utilities ---


const ScheduleInterviewModal: React.FC<ScheduleInterviewModalProps> = ({ isOpen, data, onClose, onSchedule, isScheduling }) => {
    const { showToast } = useToast();
    const [selectedCandidates, setSelectedCandidates] = useState<string[]>([]);
    const [interviewDate, setInterviewDate] = useState(''); 
    const [interviewTime, setInterviewTime] = useState('');
    const [emailSubject, setEmailSubject] = useState(''); 
    const [emailBody, setEmailBody] = useState(''); 
    const [activeConfigTab, setActiveConfigTab] = useState<'schedule' | 'email'>('schedule'); 
    const [level, setLevel] = useState<InterviewLevel>('Medium'); 
    const [type, setType] = useState<InterviewType>('Agent_interview'); 
    const [scoreFilter, setScoreFilter] = useState<number>(0); 

    const mapJobPostTypeToApiType = (jobType: JobTypeDetails['interview_type']): InterviewType => {
        if (jobType === 'agent') return 'Agent_interview';
        if (jobType === 'offline' || jobType === 'hybrid') return 'In_person'; 
        return 'Agent_interview'; // Default fallback
    };
    
    useEffect(() => {
        if (isOpen) {
            const defaultJobPostType = data.jobDetails 
                ? mapJobPostTypeToApiType(data.jobDetails.interview_type) 
                : 'Agent_interview';

            const now = new Date();
            const tomorrow = new Date(now.setDate(now.getDate() + 1)).toISOString().substring(0, 10);
            
            setType(defaultJobPostType);
            setSelectedCandidates([]); 
            setInterviewDate(tomorrow); 
            setInterviewTime('10:00'); 
            setLevel('Medium'); 
            setScoreFilter(0);
            setEmailSubject(data.emailTemplate.subject); 
            setEmailBody(data.emailTemplate.body); 
            setActiveConfigTab('schedule');
        }
    }, [isOpen, data]);

    const currentJobPostType = data.jobDetails 
        ? mapJobPostTypeToApiType(data.jobDetails.interview_type)
        : 'Agent_interview'; 
    
    const allShortlistedCandidates = useMemo(() => 
        data.candidates.filter(c => c.round_status === 'shortlisted'), 
        [data.candidates]
    );

    const filteredCandidates = useMemo(() => {
        if (scoreFilter === 0) return allShortlistedCandidates;
        return allShortlistedCandidates.filter(c => c.overall_score >= scoreFilter);
    }, [allShortlistedCandidates, scoreFilter]);

    if (!isOpen) return null;


    const handleToggleCandidate = (profileId: string) => {
        setSelectedCandidates(prev => {
            if (prev.includes(profileId)) {
                return prev.filter(id => id !== profileId);
            }
            return [...prev, profileId];
        });
    };
    
    const handleSelectAll = () => {
        const allIds = filteredCandidates.map(c => c.profile_id);
        const allCurrentlySelected = selectedCandidates.length === filteredCandidates.length && selectedCandidates.every(id => allIds.includes(id));

        if (allCurrentlySelected) {
            setSelectedCandidates([]); // Deselect All
        } else {
            setSelectedCandidates(allIds); // Select All
        }
    };
    
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        
        const combinedDateTime = `${interviewDate}T${interviewTime}`; 
        
        if (selectedCandidates.length === 0 || !combinedDateTime || !emailSubject.trim() || !emailBody.trim() || isScheduling) {
            showToast("Please select candidates, set a date/time, and ensure email fields are filled.", "warning");
            return;
        }

        const apiType = type === 'Agent_interview' ? 'Agent_interview' : 'In_person'; 
        
        
        onSchedule({
            jobId: data.jobId,
            roundId: data.roundId,
            profileIds: selectedCandidates,
            dateTime: combinedDateTime,
            level,
            type: apiType, 
            emailSubject: emailSubject.trim(), 
            emailBody: emailBody.trim(),       
        });
    };
    
    const interviewLevels: InterviewLevel[] = ['Easy', 'Medium', 'Hard'];
    const interviewTypeOptions = [
        { value: 'Agent_interview', label: 'Agent Interview (Remote/AI)' },
        { value: 'In_person', label: 'In Person / Offline' },
        { value: 'Hybrid', label: 'Hybrid (Remote & In Person)' }, 
    ];

    const scoreFilterOptions = [
        { value: 0, label: 'All Shortlisted' },
        { value: 25, label: '25% Score and above' },
        { value: 50, label: '50% Score and above' },
        { value: 75, label: '75% Score and above' },
    ];

    const isSubmitDisabled = isScheduling || selectedCandidates.length === 0 || !interviewDate.trim() || !interviewTime.trim() || !emailSubject.trim() || !emailBody.trim();
    const isAllSelected = selectedCandidates.length === filteredCandidates.length && filteredCandidates.length > 0;
    
    return (
        <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto transform transition-all duration-300 scale-100 opacity-100" onClick={(e) => e.stopPropagation()}>
                <form onSubmit={handleSubmit}>
                    {/* Header */}
                    <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center z-10">
                        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                            <Calendar size={24} className="text-indigo-600" />
                            <span className="text-indigo-600 italic">{data.jobTitle} - {data.roundName}</span>
                        </h2>
                        <button type="button" onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 text-gray-500"><XCircle size={20} /></button>
                    </div>

                    <div className={clsx(
                        "p-6 grid gap-8",
                        activeConfigTab === 'email' ? "grid-cols-1" : "grid-cols-1 lg:grid-cols-3"
                    )}>
                        
                        {/* Column 1: Configuration (Expands on Email Tab) */}
                        <div className={clsx(
                             "space-y-6",
                             activeConfigTab === 'email' ? "lg:col-span-3" : "lg:col-span-1" 
                        )}>
                            <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2"><Settings size={20} className="text-gray-500"/> Configuration</h3> 
                            
                            {/* Configuration Tabs */}
                            <div className="flex w-full rounded-xl border-2 p-1 bg-gray-100 border-gray-200">
                                <button
                                    type="button"
                                    onClick={() => setActiveConfigTab('schedule')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                                        activeConfigTab === 'schedule'
                                            ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
                                            : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                                    }`}
                                >
                                    <Clock size={16} /> Scheduling
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setActiveConfigTab('email')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                                        activeConfigTab === 'email'
                                            ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
                                            : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                                    }`}
                                >
                                    <Send size={16} /> Email
                                </button>
                            </div>

                            {/* Tab Content: SCHEDULING */}
                            {activeConfigTab === 'schedule' && (
                                <div className="space-y-6">
                                    <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200 text-center">
                                        <p className="text-xs font-medium text-indigo-700 mb-1">Candidates to Schedule</p>
                                        <p className="text-4xl font-extrabold text-indigo-900">{selectedCandidates.length}</p>
                                    </div>
                                    
                                    <div className='bg-gray-50 p-4 rounded-lg border space-y-4'>
                                        <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Clock size={16} /> Date & Time *</label>
                                        
                                        <div className="space-y-3">
                                            <div>
                                                <label className="block text-xs font-medium text-gray-600 mb-1">Date</label>
                                                <input
                                                    type="date" 
                                                    value={interviewDate}
                                                    onChange={(e) => setInterviewDate(e.target.value)}
                                                    min={new Date().toISOString().substring(0, 10)}
                                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
                                                    required
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-xs font-medium text-gray-600 mb-1">Time</label>
                                                <input
                                                    type="time" 
                                                    value={interviewTime}
                                                    onChange={(e) => setInterviewTime(e.target.value)}
                                                    step="300" 
                                                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
                                                    required
                                                />
                                            </div>
                                        </div>
                                        <p className="text-xs text-gray-500 mt-1">Interviews must be scheduled for a future date and time.</p>
                                    </div>
                                    
                                    <div className='bg-gray-50 p-4 rounded-lg border'>
                                        <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Users size={16} /> Interview Type *</label>
                                        <select
                                            value={type}
                                            onChange={(e) => setType(e.target.value as InterviewType)}
                                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base bg-white focus:ring-indigo-500 focus:border-indigo-500"
                                        >
                                            {interviewTypeOptions.map(option => (
                                                <option key={option.value} value={option.value}>{option.label}</option>
                                            ))}
                                        </select>
                                        <p className="text-xs text-gray-500 mt-1">Default type based on job post: <strong className="text-indigo-600">{currentJobPostType === 'Agent_interview' ? 'Agent Interview' : 'In Person / Offline'}</strong></p>
                                    </div>

                                    {type === 'Agent_interview' && (
                                        <div className="space-y-1 bg-gray-50 p-4 rounded-lg border border-yellow-200">
                                            <label className="block text-sm font-bold text-gray-700 mb-2 flex items-center gap-2"><Zap size={16} /> Agent Interview Level *</label>
                                            <select
                                                value={level}
                                                onChange={(e) => setLevel(e.target.value as InterviewLevel)}
                                                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base bg-white focus:ring-yellow-500 focus:border-yellow-500"
                                            >
                                                {interviewLevels.map(l => <option key={l} value={l}>{l}</option>)}
                                            </select>
                                            <p className="text-xs text-gray-500 mt-1">Required to set difficulty for AI interviews.</p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Tab Content: EMAIL CONFIGURATION */}
                            {activeConfigTab === 'email' && (
                                <div className="space-y-6">
                                    <div className="bg-gradient-to-r from-indigo-50 to-blue-50 rounded-lg border border-indigo-200 p-5">
                                        <div className="flex items-start gap-3">
                                            <div className="flex-shrink-0 w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center">
                                                <AlertTriangle size={16} className="text-white" />
                                            </div>
                                            <div className="flex-1">
                                                <h4 className="text-sm font-bold text-indigo-900 mb-2">Dynamic Placeholders - How They Work</h4>
                                                <p className="text-xs text-indigo-800 mb-3">
                                                    Placeholders like <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-600 text-white text-xs font-mono">{'{CANDIDATE_NAME}'}</span> are automatically replaced with real data when emails are sent. You can edit all content freely - just keep placeholder format exact (uppercase with braces).
                                                </p>
                                                <div className="grid grid-cols-2 gap-2 text-xs">
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'{CANDIDATE_NAME}'}</span>
                                                        
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'{JOB_TITLE}'}</span>
                                                        
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'{ROUND_NAME}'}</span>
                                                        
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'{DATE}'}</span>
                                                        
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'{TIME}'}</span>
                                                        
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="inline-block px-1.5 py-0.5 bg-indigo-600 text-white rounded text-[10px] font-mono">{'{INTERVIEW_LINK}'}</span>
                                                       
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    {/* Email Subject */}
                                    <div className="space-y-2">
                                        <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
                                            <Send size={16} className="text-indigo-600" />
                                            Email Subject *
                                        </label>
                                        <div className="relative">
                                            <input
                                                type="text"
                                                value={emailSubject}
                                                onChange={(e) => setEmailSubject(e.target.value)}
                                                placeholder="e.g., Interview Invitation for {JOB_TITLE}"
                                                className="w-full border-2 border-gray-300 rounded-lg px-4 py-3 text-base focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all placeholder:text-gray-400"
                                                required
                                            />
                                        </div>
                                    </div>
                                    
                                    {/* Email Body with Enhanced Editor */}
                                    <div className="space-y-2">
                                        <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
                                            <Settings size={16} className="text-indigo-600" />
                                            Email Body - The preview below shows how the email will look to candidates *
                                        </label>
                                        
                                        <div className="relative">
                                            <textarea
                                                rows={16}
                                                value={emailBody}
                                                onChange={(e) => setEmailBody(e.target.value)}
                                                placeholder="Dear {CANDIDATE_NAME},&#10;&#10;We are pleased to inform you..."
                                                className="w-full p-4 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-y font-mono text-sm leading-relaxed placeholder:text-gray-400 placeholder:font-sans"
                                                required
                                                style={{
                                                    background: 'linear-gradient(to bottom, #ffffff 0%, #fafafa 100%)',
                                                }}
                                            />
                                            <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-white/80 px-2 py-1 rounded">
                                                {emailBody.length} characters
                                            </div>
                                        </div>
                                    </div>

                                   {/* Preview Section */}
                                    <div className="border-t-2 border-gray-200 pt-6">
                                        <div className="flex items-center justify-between mb-3">
                                            <label className="flex items-center gap-2 text-sm font-bold text-gray-800">
                                                <Users size={16} className="text-indigo-600" />
                                                Email Preview
                                            </label>
                                          
                                        </div>
                                        <div className="bg-white border-2 border-gray-200 rounded-lg overflow-hidden shadow-sm">
                                            {/* Email Header */}
                                            <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-6 py-4 border-b border-gray-200">
                                                <div className="space-y-2">
                                                    <div className="flex items-start gap-3">
                                                        <span className="text-xs font-medium text-gray-500 w-16">Subject:</span>
                                                        <span className="flex-1 font-semibold text-gray-900 text-sm">
                                                            {emailSubject 
                                                                .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
                                                                .replace(/{JOB_TITLE}/g, data.jobTitle)
                                                                .replace(/{ROUND_NAME}/g, data.roundName)
                                                                .replace(/{DATE}/g, 'November 20, 2025')
                                                                .replace(/{TIME}/g, '2:00 PM')
                                                                .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
                                                                .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
                                                                .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
                                                                .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
                                                             || 'No subject provided'}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-start gap-3">
                                                        <span className="text-xs font-medium text-gray-500 w-16">To:</span>
                                                        <span className="flex-1 text-sm text-gray-700">sarah.johnson@email.com</span>
                                                    </div>
                                                </div>
                                            </div>
                                            
                                       
<div className="p-6 bg-white">
    <div 
        className="text-sm text-gray-800 leading-relaxed"
        // FIX: Remove manual Markdown conversion and instead use white-space to preserve line breaks from the clean template.
        style={{ 
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
            wordBreak: 'break-word',
            whiteSpace: 'pre-wrap', // <-- CRITICAL FIX for preview display
        }}
    >
        {emailBody ? (
            // Now we send the emailBody content directly as text for preview, relying on pre-wrap
            emailBody
                .replace(/{CANDIDATE_NAME}/g, 'Sarah Johnson')
                .replace(/{JOB_TITLE}/g, data.jobTitle)
                .replace(/{ROUND_NAME}/g, data.roundName)
                .replace(/{DATE}/g, 'November 20, 2025')
                .replace(/{TIME}/g, '2:00 PM')
                .replace(/{INTERVIEW_TYPE}/g, 'Virtual Interview')
                .replace(/{INTERVIEW_LINK}/g, 'https://meet.company.com/interview-abc123')
                .replace(/{INTERVIEW_TOKEN}/g, 'ABC-123-XYZ')
                .replace(/{NEXT_ROUND_NAME}/g, 'Final Round')
        ) : (
            <span className="text-gray-400 italic">Email body will appear here...</span>
        )}
    </div>
</div>

                                            
                                        </div>
                                        <p className="text-xs text-gray-500 mt-3 flex items-center gap-1">
                                            <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                                            Preview shows sample data. Actual emails will use real candidate information.
                                        </p>
                                    </div>
                                </div>
                            )}

                        </div>
                        
                        {/* Column 2: Candidates List (Hidden on Email Tab) */}
                        {activeConfigTab === 'schedule' && (
                            <div className="lg:col-span-2 space-y-4">
                                <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2"><Users size={20} className="text-gray-500"/> Candidates Selection</h3>

                                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200 gap-3">
                                    <p className="text-sm text-gray-700 font-medium">
                                        <span className="font-bold text-green-600">{allShortlistedCandidates.length}</span> candidates are ready for scheduling.
                                        <span className="ml-3 text-xs text-gray-500">Showing <strong className="text-gray-800">{filteredCandidates.length}</strong> candidates.</span>
                                    </p>
                                    <div className="flex items-center gap-2 text-sm flex-shrink-0">
                                        <label className="text-gray-600 font-medium">Filter:</label>
                                        <select 
                                            value={scoreFilter}
                                            onChange={(e) => setScoreFilter(Number(e.target.value))}
                                            className="border border-gray-300 rounded-md px-2 py-1 bg-white text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                        >
                                            {scoreFilterOptions.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
                                        </select>
                                    </div>
                                </div>
                                
                                <Button 
                                    type="button" 
                                    onClick={handleSelectAll} 
                                    variant="outline" 
                                    disabled={filteredCandidates.length === 0}
                                    className="w-full py-2.5 text-sm flex items-center justify-center gap-2 text-indigo-600 border-indigo-300 hover:bg-indigo-50"
                                >
                                    <Check size={16} /> 
                                    {isAllSelected ? 'Deselect All' : `Select All (${filteredCandidates.length} filtered)`}
                                </Button>

                                <div className="max-h-80 overflow-y-auto pr-2 space-y-2">
                                    {filteredCandidates.length === 0 ? (
                                        <div className="text-center py-10 text-gray-500 bg-gray-50 rounded-lg border border-dashed">
                                            <AlertTriangle size={24} className="mx-auto mb-2 text-gray-400"/>
                                            <div className="text-sm">No candidates match the current filters.</div>
                                        </div>
                                    ) : (
                                        filteredCandidates.map(candidate => (
                                            <div 
                                                key={candidate.profile_id} 
                                                onClick={() => handleToggleCandidate(candidate.profile_id)}
                                                className={clsx(
                                                    "p-3 rounded-lg border cursor-pointer transition-all duration-200 flex justify-between items-center group",
                                                    selectedCandidates.includes(candidate.profile_id) 
                                                        ? "bg-indigo-100/70 border-indigo-400 shadow-md" 
                                                        : "bg-white border-gray-200 hover:bg-gray-50"
                                                )}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={clsx(
                                                        "w-5 h-5 rounded flex items-center justify-center border transition-colors flex-shrink-0",
                                                        selectedCandidates.includes(candidate.profile_id) ? "bg-indigo-600 border-indigo-600 text-white" : "bg-white border-gray-300 group-hover:border-indigo-400"
                                                    )}>
                                                        {selectedCandidates.includes(candidate.profile_id) && <Check size={14} />}
                                                    </div>
                                                    <div>
                                                        <span className="font-medium text-gray-900 block">{candidate.candidate_name}</span>
                                                        <span className="text-xs text-gray-500 flex items-center gap-1 mt-0.5"><Star size={12} className="text-yellow-500"/> {candidate.overall_score}% Match</span>
                                                    </div>
                                                </div>
                                                <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-1 rounded-full flex-shrink-0">Shortlisted</span>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer / Submit Button */}
                    <div className="sticky bottom-0 bg-white border-t border-gray-200 p-6 flex justify-end gap-3 z-10">
                        <Button type="button" variant="secondary" onClick={onClose} disabled={isScheduling}>
                            Cancel
                        </Button>
                        <Button type="submit" variant="primary" disabled={isSubmitDisabled}>
                            {isScheduling ? (
                                <><Loader2 size={16} className="animate-spin mr-2" /> Submitting...</>
                            ) : (
                                <><Send size={16} className="mr-2"/> Schedule {selectedCandidates.length} Interview(s)</>
                            )}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ScheduleInterviewModal;
export { generateDefaultEmailContent, type JobTypeDetails, type ScheduleModalData };
