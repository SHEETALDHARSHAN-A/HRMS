// import React, { useState, useEffect, useCallback, useMemo } from 'react';
// import {
//   Briefcase,
//   Users,
//   BarChart2,
//   CheckSquare,
//   XSquare,
//   TrendingUp,
//   Loader2,
//   Activity,
//   FileText,
// } from 'lucide-react';
// import { getAllJobPosts, getActiveJobPosts, getJobCandidates } from '../../api/jobApi'; 
// import { useToast } from '../../context/ModalContext'; 
// import { useNavigate } from 'react-router-dom'; 

// // --- Data Structures ---
// interface JobPostStats {
//   job_id: string;
//   job_title: string;
//   posted_date?: string | null;
//   total_applications: number;
//   shortlisted: number; // Final Shortlisted
//   rejected: number;     
//   under_review: number; // Screening candidates (Curation)
//   onboarding: number;
//   interviews_scheduled: number;
//   onboarding_timestamps?: string[] | null;
//   is_active: boolean;
//   // ✨ NEW FIELDS for detailed pipeline counts
//   interview_rounds: number; 
//   screening: number; 
//   l1_interview: number;
//   l2_interview: number;
//   l3_interview: number;
//   hired: number;
// }

// interface DashboardData {
//   total_jobs: number;
//   active_jobs: number;
//   // Dynamic Metrics - Initial State (Aggregates)
//   total_candidates_applied: number;
//   total_shortlisted: number;
//   total_rejected: number;
//   total_under_review: number;
//   job_stats: JobPostStats[];
// }

// interface DashboardProps {}

// // --- Helper Components (StatCard) ---
// interface StatCardProps {
//   title: string;
//   value: number | string;
//   icon: React.ElementType;
//   colorClass: string;
//   isLoading: boolean;
//   className?: string;
// }

// const StatCard: React.FC<StatCardProps> = ({ title, value, icon: Icon, colorClass, isLoading, className }) => (
//   <div
//     className={`bg-white p-5 rounded-xl shadow-sm border border-gray-100 transition-shadow duration-200 ${className}`}
//   >
//     <div className="flex items-center justify-between mb-3">
//       <h3 className="text-sm font-semibold text-gray-500">{title}</h3>
//       <div className={`p-2 rounded-lg ${colorClass.replace('text-', 'bg-').replace('-500', '-50')}`}>
//         <Icon size={18} className={`${colorClass}`} />
//       </div>
//     </div>
//     {isLoading ? (
//       <div className="h-8 bg-gray-200 rounded animate-pulse w-1/2"></div>
//     ) : (
//       <p className="text-3xl font-bold text-gray-900">{value}</p>
//     )}
//   </div>
// );


// // --- Pipeline Activity Grid (The Core Funnel View) ---
// interface PipelineGridProps {
//     jobs: JobPostStats[];
//     isLoading: boolean;
//     onJobSelect: (jobId: string) => void;
//     selectedJobId: string | null;
// }

// const getJobColorClass = (jobId: string, index: number) => {
//     const colors = [
//         'bg-pink-100 text-pink-800 border-pink-200',
//         'bg-yellow-100 text-yellow-800 border-yellow-200',
//         'bg-indigo-100 text-indigo-800 border-indigo-200',
//         'bg-green-100 text-green-800 border-green-200',
//         'bg-blue-100 text-blue-800 border-blue-200',
//         'bg-red-100 text-red-800 border-red-200',
//     ];
//     return colors[index % colors.length];
// };

// const PipelineActivityGrid: React.FC<PipelineGridProps> = ({ jobs, isLoading, onJobSelect, selectedJobId }) => {
//     const activeJobs = jobs.filter(j => j.is_active);

//     const stages = [
//         { key: 'total_applications', label: 'New Applied', countKey: 'total_applications' as keyof JobPostStats },
//         { key: 'screening', label: 'Screening (Curation)', countKey: 'screening' as keyof JobPostStats },
//         { key: 'l1_interview', label: 'L1 Interview', countKey: 'l1_interview' as keyof JobPostStats, isInterview: true },
//         { key: 'l2_interview', label: 'L2 Interview', countKey: 'l2_interview' as keyof JobPostStats, isInterview: true },
//         { key: 'l3_interview', label: 'L3 Interview', countKey: 'l3_interview' as keyof JobPostStats, isInterview: true },
//         { key: 'shortlisted', label: 'Final Shortlisted', countKey: 'shortlisted' as keyof JobPostStats },
//         { key: 'hired', label: 'Hired/Onboarded', countKey: 'hired' as keyof JobPostStats },
//     ];
    
//     return (
//         <div className="lg:col-span-8 bg-white p-6 rounded-xl shadow-lg border border-gray-100 overflow-hidden">
//             <div className="flex justify-between items-center mb-4">
//                 <h2 className="text-xl font-bold text-gray-800">Candidate Funnel (Active Jobs)</h2>
//             </div>

//             <div className="overflow-x-auto min-w-[700px]">
//                 <table className="w-full text-sm text-left text-gray-600 border-collapse">
//                     {/* Header Row */}
//                     <thead className="text-xs uppercase bg-gray-50 text-gray-500">
//                         <tr>
//                             <th scope="col" className="px-4 py-3 min-w-[200px] sticky left-0 z-10 bg-gray-50 border-r border-gray-100">Job Title (Rounds)</th>
//                             {stages.map(stage => (
//                                 <th key={stage.key} scope="col" className="px-4 py-3 text-center whitespace-nowrap">{stage.label}</th>
//                             ))}
//                         </tr>
//                     </thead>
//                     {/* Job Rows */}
//                     <tbody>
//                         {isLoading ? (
//                             <tr>
//                                 <td colSpan={stages.length + 1} className="text-center py-10 text-gray-400">
//                                     <Loader2 size={20} className="inline animate-spin mr-2" /> Loading active pipeline...
//                                 </td>
//                             </tr>
//                         ) : activeJobs.length === 0 ? (
//                             <tr>
//                                 <td colSpan={stages.length + 1} className="text-center py-10 text-gray-400">
//                                     No active jobs to display pipeline metrics.
//                                 </td>
//                             </tr>
//                         ) : (
//                             activeJobs.map((job, jobIndex) => {
//                                 const isSelected = job.job_id === selectedJobId;
                                
//                                 return (
//                                 <tr 
//                                     key={job.job_id} 
//                                     className={`border-b border-gray-100 hover:bg-gray-50/50 cursor-pointer ${isSelected ? 'bg-blue-50/70 border-l-4 border-blue-500' : ''}`}
//                                     onClick={() => onJobSelect(job.job_id)}
//                                 >
//                                     {/* Job Title Cell */}
//                                     <td className="px-4 py-3 font-medium text-gray-900 sticky left-0 z-10 bg-white/95 border-r border-gray-100 backdrop-blur-[1px]">
//                                         <div className="flex flex-col">
//                                             <span className="truncate max-w-[190px] font-semibold">{job.job_title}</span>
//                                             <span className="text-xs text-gray-500 mt-0.5">{job.interview_rounds} Interview Rounds</span>
//                                         </div>
//                                     </td>
//                                     {/* Stage Cells */}
//                                     {stages.map(stage => {
//                                         const count = job[stage.countKey] as number;
                                        
//                                         // Dynamic cell styling
//                                         let finalCellBg = 'bg-white';
//                                         let finalTextColor = 'text-gray-600';
//                                         let countBg = 'bg-gray-200';

//                                         if (stage.key === 'shortlisted' || stage.key === 'hired') {
//                                             finalCellBg = 'bg-green-50';
//                                             finalTextColor = 'text-green-800';
//                                             countBg = 'bg-green-200';
//                                         } else if (stage.key === 'screening') {
//                                             finalCellBg = 'bg-yellow-50';
//                                             finalTextColor = 'text-yellow-800';
//                                             countBg = 'bg-yellow-200';
//                                         } else if (stage.isInterview) {
//                                             finalCellBg = 'bg-indigo-50';
//                                             finalTextColor = 'text-indigo-800';
//                                             countBg = 'bg-indigo-200';
//                                         }
                                        
//                                         // Conditionally render L-rounds based on job's rounds property
//                                         const roundNumber = stage.key.match(/l(\d)_interview/)?.[1];
//                                         const isRoundNeeded = !roundNumber || parseInt(roundNumber) <= job.interview_rounds;

//                                         if (!isRoundNeeded) {
//                                             return <td key={stage.key} className="px-4 py-3 text-center bg-gray-100/50 border-r border-gray-100">
//                                                 <div className="text-gray-300 font-medium text-xs">N/A</div>
//                                             </td>
//                                         }

//                                         if (count === 0) {
//                                             return <td key={stage.key} className={`px-4 py-3 text-center ${finalCellBg.replace(/50|100/, '50')} border-r border-gray-100`}>
//                                                 <div className="text-gray-300 font-medium">—</div>
//                                             </td>
//                                         }

//                                         return (
//                                             <td 
//                                               key={stage.key} 
//                                               className={`px-4 py-3 text-center ${finalCellBg} border-r border-gray-100 transition-colors duration-200 cursor-pointer hover:shadow-inner`}
//                                             >
//                                                 <div 
//                                                     className={`inline-block px-3 py-1 rounded-md font-semibold text-xs transition-shadow ${countBg} ${finalTextColor} shadow-sm`}
//                                                 >
//                                                     {count} Candidates
//                                                 </div>
//                                             </td>
//                                         );
//                                     })}
//                                 </tr>
//                             )})
//                         )}
//                     </tbody>
//                 </table>
//             </div>
//         </div>
//     );
// };

// // --- Jobs Summary Donut Chart ---
// interface JobsSummaryProps {
//     jobs: JobPostStats[];
//     isLoading: boolean;
// }

// const DonutChart: React.FC<{ data: { label: string, value: number, color: string }[], total: number }> = ({ data, total }) => {
//     // Placeholder SVG for visualization
//     return (
//         <div className="relative w-40 h-40 mx-auto mb-4">
//             <svg viewBox="0 0 100 100" className="w-full h-full">
//                 <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" strokeWidth="10" />
//                 {data.map((item, index) => {
//                     const startAngle = data.slice(0, index).reduce((sum, d) => sum + d.value, 0) * 360 / total;
//                     const endAngle = startAngle + item.value * 360 / total;
//                     const largeArcFlag = item.value * 360 / total > 180 ? 1 : 0;
                    
//                     const startX = 50 + 45 * Math.cos((startAngle - 90) * Math.PI / 180);
//                     const startY = 50 + 45 * Math.sin((startAngle - 90) * Math.PI / 180);
//                     const endX = 50 + 45 * Math.cos((endAngle - 90) * Math.PI / 180);
//                     const endY = 50 + 45 * Math.sin((endAngle - 90) * Math.PI / 180);
                    
//                     return (
//                         <path
//                             key={item.label}
//                             d={`M 50 50 L ${startX} ${startY} A 45 45 0 ${largeArcFlag} 1 ${endX} ${endY} Z`}
//                             fill="none"
//                             stroke={item.color}
//                             strokeWidth="10"
//                             strokeLinecap="round"
//                             style={{ transition: 'all 0.5s' }}
//                         />
//                     );
//                 })}
//                 <text x="50" y="50" textAnchor="middle" dominantBaseline="middle" className="text-xl font-bold fill-gray-900">
//                     {total}
//                 </text>
//                 <text x="50" y="65" textAnchor="middle" dominantBaseline="middle" className="text-xs fill-gray-500">
//                     TOTAL POSTS
//                 </text>
//             </svg>
//         </div>
//     );
// };

// const JobsSummaryCard: React.FC<JobsSummaryProps> = ({ jobs, isLoading }) => {
//     if (isLoading) {
//         return (
//              <div className="lg:col-span-4 bg-white p-6 rounded-xl shadow-lg border border-gray-100 min-h-[300px] flex items-center justify-center">
//                  <Loader2 size={24} className="animate-spin text-gray-400" />
//              </div>
//         )
//     }
    
//     const activeJobs = jobs.filter(j => j.is_active).length;
//     const inactiveJobs = jobs.filter(j => !j.is_active).length;
    
//     const chartData = [
//         { label: 'Active on Career Page', value: activeJobs, color: '#10B981' },
//         { label: 'Inactive (On Hold)', value: inactiveJobs, color: '#FCD34D' },
//     ];
    
//     return (
//         <div className="lg:col-span-4 bg-white p-6 rounded-xl shadow-lg border border-gray-100 min-h-[400px]">
//             <h2 className="text-xl font-bold text-gray-800 mb-4">Job Status Summary</h2>
            
//             <DonutChart data={chartData} total={jobs.length} />
            
//             <div className="space-y-3 mt-4">
//                 {chartData.map((item, index) => (
//                     <div key={item.label} className="flex items-center justify-between text-sm text-gray-700">
//                         <div className="flex items-center gap-2">
//                             <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
//                             <span className="font-medium">{item.label}</span>
//                         </div>
//                         <span className="font-bold">{item.value}</span>
//                     </div>
//                 ))}
//                 <div className="flex items-center justify-between text-base pt-2 border-t border-gray-100 font-bold text-gray-800">
//                      <span>Total Job Posts</span>
//                      <span>{jobs.length}</span>
//                  </div>
//             </div>
//         </div>
//     );
// };


// // --- Utility: Robust job mapping (MOCK Interview Rounds) ---
// function mapFetchedJob(job: any): JobPostStats {
//   const jobId = job.job_id ?? job.jobId ?? job.id ?? "";
//   const rawActive = job.is_active ?? job.isActive ?? job.active ?? job.enabled;
//   const isActive =
//     rawActive === undefined || rawActive === null
//       ? false
//       : typeof rawActive === "boolean"
//         ? rawActive
//         : typeof rawActive === "string"
//           ? rawActive.toLowerCase() === "true"
//           : Boolean(rawActive);

//   // Prefer aggregated counts returned under `profile_counts` 
//   const profileCounts = job.profile_counts ?? job.profileCounts ?? null;
//   const shortlisted = profileCounts?.shortlisted ?? job.shortlisted ?? job.shortlisted_count ?? 0;
//   const rejected = profileCounts?.rejected ?? job.rejected ?? job.rejected_count ?? 0;
//   const under_review = profileCounts?.under_review ?? job.under_review ?? job.underReview ?? 0;
//   const onboarding = profileCounts?.onboarding ?? job.onboarding ?? 0;
//   const interviews_scheduled = profileCounts?.interviews_scheduled ?? profileCounts?.interviews ?? job.interviews ?? job.interview_count ?? job.interviews_count ?? 0;
//   const onboarding_timestamps = profileCounts?.onboarding_timestamps ?? profileCounts?.onboarding_dates ?? job.onboarding_timestamps ?? job.onboarding_dates ?? null;
//   const total_applications = profileCounts?.applied ?? job.total_applications ?? (shortlisted + rejected + under_review + onboarding);
  
//   // ✨ MOCK: Derive Interview Rounds (Rounds are mocked: 3 for Senior/Lead, 2 for others)
//   const isSenior = job.job_title.toLowerCase().includes('senior') || job.job_title.toLowerCase().includes('lead');
//   const interview_rounds = isSenior ? 3 : 2; 

//   // Distribute interviews across L1, L2, L3 based on the job's rounds
//   const interviewsInProgress = Math.max(0, interviews_scheduled - onboarding); 
//   let l1_interview = 0;
//   let l2_interview = 0;
//   let l3_interview = 0;
  
//   // Simple distribution logic: e.g., 50% L1, 30% L2, 20% L3
//   if (interview_rounds >= 1) l1_interview = Math.floor(interviewsInProgress * (interview_rounds === 1 ? 1 : 0.5));
//   if (interview_rounds >= 2) l2_interview = Math.floor(interviewsInProgress * (interview_rounds === 2 ? 0.5 : 0.3));
//   if (interview_rounds >= 3) l3_interview = Math.max(0, interviewsInProgress - l1_interview - l2_interview);
  
//   // Screening is defined as candidates in 'Under Review' status
//   const screening_in_progress = Math.max(0, under_review);
//   const hired = onboarding;


//   return {
//     job_id: jobId,
//     job_title: job.job_title || 'Untitled Job',
//     posted_date: job.posted_date || null,
//     total_applications,
//     shortlisted,
//     rejected,
//     under_review,
//     onboarding,
//     interviews_scheduled,
//     onboarding_timestamps,
//     is_active: isActive,
//     // ✨ NEW MOCKED / DERIVED FIELDS
//     interview_rounds,
//     screening: Math.max(0, screening_in_progress),
//     l1_interview: Math.max(0, l1_interview),
//     l2_interview: Math.max(0, l2_interview),
//     l3_interview: Math.max(0, l3_interview),
//     hired: hired,
//   };
// }


// // --- Main Dashboard Component ---
// export default function Dashboard() {
//   const [data, setData] = useState<DashboardData | null>(null);
//   const [sortedJobs, setSortedJobs] = useState<JobPostStats[]>([]);
//   // State to track which job is selected from the funnel chart
//   const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
//   const [isLoading, setIsLoading] = useState(true);
//   const { showToast } = useToast();
//   const navigate = useNavigate();

//   // Determine the job whose metrics should be shown in the top row
//   const selectedJob = useMemo(() => {
//       return sortedJobs.find(job => job.job_id === selectedJobId) || null;
//   }, [sortedJobs, selectedJobId]);

//   // Aggregate metrics or selected job's metrics
//   const displayMetrics = useMemo(() => {
//     if (selectedJob) {
//         return {
//             title: selectedJob.job_title,
//             applied: selectedJob.total_applications,
//             shortlisted: selectedJob.shortlisted,
//             underReview: selectedJob.under_review,
//             rejected: selectedJob.rejected,
//         };
//     }
//     // Fallback to aggregated totals (initial view)
//     return {
//         title: 'All Active Job Posts',
//         applied: data?.total_candidates_applied ?? 0,
//         shortlisted: data?.total_shortlisted ?? 0,
//         underReview: data?.total_under_review ?? 0,
//         rejected: data?.total_rejected ?? 0,
//     };
//   }, [selectedJob, data]);

//   // Fetch and process data 
//   const fetchJobStats = useCallback(async () => {
//     setIsLoading(true);
//     try {
//       const [allRes, activeRes] = await Promise.all([
//         getAllJobPosts(),
//         getActiveJobPosts()
//       ]);
//       if (allRes.success) {
//         const allJobsRaw = Array.isArray(allRes.data) ? allRes.data : (allRes.data?.jobs || allRes.data);
//         const activeJobIds = new Set((activeRes.data?.jobs || activeRes.data || []).map((j: any) => j.job_id ?? j.jobId ?? j.id));
        
//         const jobs: JobPostStats[] = allJobsRaw.map((job: any) => {
//           const mapped = mapFetchedJob(job);
//           return {
//             ...mapped,
//             is_active: activeJobIds.has(mapped.job_id)
//           };
//         });

//         // Calculate aggregate numbers 
//         const total_applications_agg = jobs.reduce((sum, j) => sum + j.total_applications, 0);
//         const total_shortlisted_agg = jobs.reduce((sum, j) => sum + j.shortlisted, 0);
//         const total_rejected_agg = jobs.reduce((sum, j) => sum + j.rejected, 0);
//         const total_under_review_agg = jobs.reduce((sum, j) => sum + j.under_review, 0);
        
//         setSortedJobs(jobs);
//         setData({
//           total_jobs: jobs.length,
//           active_jobs: jobs.filter(j => j.is_active).length,
//           total_candidates_applied: total_applications_agg,
//           total_shortlisted: total_shortlisted_agg,
//           total_rejected: total_rejected_agg,
//           total_under_review: total_under_review_agg,
//           job_stats: jobs,
//         });
        
//         // Default to showing the top performing active job's metrics if none selected
//         if (!selectedJobId) {
//              const topJob = jobs.filter(j => j.is_active).sort((a, b) => b.total_applications - a.total_applications)[0];
//              if (topJob) setSelectedJobId(topJob.job_id);
//         }

//       } else {
//         showToast(allRes.error || 'Failed to load dashboard data.', 'error');
//         setData(null);
//       }
//     } catch (error: any) {
//       showToast(error.message || 'An error occurred while fetching data.', 'error');
//       setData(null);
//     } finally {
//       setIsLoading(false);
//     }
//   }, [showToast, selectedJobId]);

//   // Fetch data on component mount
//   useEffect(() => {
//     fetchJobStats();
//   }, [fetchJobStats]);

  
//   // --- Render Logic ---
//   if (isLoading && !data) {
//     return (
//       <div className="flex flex-col items-center justify-center h-96">
//         <Loader2 size={48} className="text-[var(--color-primary-500)] animate-spin" />
//         <p className="mt-4 text-gray-500">Loading Dashboard Data...</p>
//       </div>
//     );
//   }

//   if (!data && !isLoading) {
//       return (
//           <div className="flex flex-col items-center justify-center h-96 bg-white p-6 rounded-lg shadow-sm border border-red-200">
//               <Activity size={48} className="text-red-500 mb-4" />
//               <h1 className="text-xl font-bold text-red-700">Failed to Load Dashboard</h1>
//               <p className="text-gray-500 mt-2 text-center">
//                   Could not retrieve job statistics. Please check your connection or try again later.
//               </p>
//               <button
//                   onClick={fetchJobStats}
//                   className="mt-6 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
//               >
//                   Retry Loading
//               </button>
//           </div>
//       );
//   }


//   // --- Main Dashboard Layout ---
//   return (
//     <>
//       {/* 1. Dynamic Metric Cards (The new Top Tabs) */}
//       <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
//         <div className="lg:col-span-12">
//             <h2 className="text-2xl font-bold text-gray-800 mb-4 truncate" title={displayMetrics.title}>
//                 Dashboard Overview: <span className="text-[var(--color-primary-500)]">{displayMetrics.title}</span>
//             </h2>
//         </div>
//         <div className="lg:col-span-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4 sm:gap-6">
//           <StatCard 
//             title="Total Candidates Applied" 
//             value={displayMetrics.applied} 
//             icon={FileText} 
//             colorClass="text-indigo-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-600" 
//           />
//           <StatCard 
//             title="Under Review (Screening)" 
//             value={displayMetrics.underReview} 
//             icon={TrendingUp} 
//             colorClass="text-yellow-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-700" 
//           />
//           <StatCard 
//             title="Shortlisted Candidates" 
//             value={displayMetrics.shortlisted} 
//             icon={CheckSquare} 
//             colorClass="text-green-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-800" 
//           />
//           <StatCard 
//             title="Rejected Candidates" 
//             value={displayMetrics.rejected} 
//             icon={XSquare} 
//             colorClass="text-red-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-900" 
//           />
//         </div>
        
//         {/* 2. Jobs Summary + Pipeline Activity Grid */}
//         <div className="lg:col-span-12 grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
//             <JobsSummaryCard jobs={sortedJobs} isLoading={isLoading} />
//             <PipelineActivityGrid 
//                 jobs={sortedJobs} 
//                 isLoading={isLoading} 
//                 onJobSelect={setSelectedJobId}
//                 selectedJobId={selectedJobId}
//             />
//         </div>
//       </div>
//     </>
//   );
// }







// import React, { useState, useEffect, useCallback, useMemo } from 'react';
// import {
//   Briefcase,
//   Users,
//   BarChart2,
//   CheckSquare,
//   XSquare,
//   TrendingUp,
//   Loader2,
//   Activity,
//   FileText,
// } from 'lucide-react';
// import { getAllJobPosts, getActiveJobPosts, getJobCandidates } from '../../api/jobApi'; 
// import { useToast } from '../../context/ModalContext'; 
// import { useNavigate } from 'react-router-dom'; 

// // --- Data Structures (Unchanged) ---
// interface JobPostStats {
//   job_id: string;
//   job_title: string;
//   posted_date?: string | null;
//   total_applications: number;
//   shortlisted: number; // Final Shortlisted
//   rejected: number;     
//   under_review: number; // Screening candidates (Curation)
//   onboarding: number;
//   interviews_scheduled: number;
//   onboarding_timestamps?: string[] | null;
//   is_active: boolean;
//   // ✨ NEW FIELDS for detailed pipeline counts
//   interview_rounds: number; 
//   screening: number; 
//   l1_interview: number;
//   l2_interview: number;
//   l3_interview: number;
//   hired: number;
// }

// interface DashboardData {
//   total_jobs: number;
//   active_jobs: number;
//   // Dynamic Metrics - Initial State (Aggregates)
//   total_candidates_applied: number;
//   total_shortlisted: number;
//   total_rejected: number;
//   total_under_review: number;
//   job_stats: JobPostStats[];
// }

// interface DashboardProps {}

// // --- Helper Components (StatCard - Unchanged) ---
// interface StatCardProps {
//   title: string;
//   value: number | string;
//   icon: React.ElementType;
//   colorClass: string;
//   isLoading: boolean;
//   className?: string;
// }

// const StatCard: React.FC<StatCardProps> = ({ title, value, icon: Icon, colorClass, isLoading, className }) => (
//   <div
//     className={`bg-white p-5 rounded-xl shadow-sm border border-gray-100 transition-shadow duration-200 ${className}`}
//   >
//     <div className="flex items-center justify-between mb-3">
//       <h3 className="text-sm font-semibold text-gray-500">{title}</h3>
//       <div className={`p-2 rounded-lg ${colorClass.replace('text-', 'bg-').replace('-500', '-50')}`}>
//         <Icon size={18} className={`${colorClass}`} />
//       </div>
//     </div>
//     {isLoading ? (
//       <div className="h-8 bg-gray-200 rounded animate-pulse w-1/2"></div>
//     ) : (
//       <p className="text-3xl font-bold text-gray-900">{value}</p>
//     )}
//   </div>
// );


// // --- Pipeline Activity Grid (The Core Funnel View - Unchanged) ---
// interface PipelineGridProps {
//     jobs: JobPostStats[];
//     isLoading: boolean;
//     onJobSelect: (jobId: string) => void;
//     selectedJobId: string | null;
// }

// const getJobColorClass = (jobId: string, index: number) => {
//     const colors = [
//         'bg-pink-100 text-pink-800 border-pink-200',
//         'bg-yellow-100 text-yellow-800 border-yellow-200',
//         'bg-indigo-100 text-indigo-800 border-indigo-200',
//         'bg-green-100 text-green-800 border-green-200',
//         'bg-blue-100 text-blue-800 border-blue-200',
//         'bg-red-100 text-red-800 border-red-200',
//     ];
//     return colors[index % colors.length];
// };

// const PipelineActivityGrid: React.FC<PipelineGridProps> = ({ jobs, isLoading, onJobSelect, selectedJobId }) => {
//     const activeJobs = jobs.filter(j => j.is_active);

//     const stages = [
//         { key: 'total_applications', label: 'New Applied', countKey: 'total_applications' as keyof JobPostStats },
//         { key: 'screening', label: 'Screening (Curation)', countKey: 'screening' as keyof JobPostStats },
//         { key: 'l1_interview', label: 'L1 Interview', countKey: 'l1_interview' as keyof JobPostStats, isInterview: true },
//         { key: 'l2_interview', label: 'L2 Interview', countKey: 'l2_interview' as keyof JobPostStats, isInterview: true },
//         { key: 'l3_interview', label: 'L3 Interview', countKey: 'l3_interview' as keyof JobPostStats, isInterview: true },
//         { key: 'shortlisted', label: 'Final Shortlisted', countKey: 'shortlisted' as keyof JobPostStats },
//         { key: 'hired', label: 'Hired/Onboarded', countKey: 'hired' as keyof JobPostStats },
//     ];
    
//     return (
//         <div className="lg:col-span-8 bg-white p-6 rounded-xl shadow-lg border border-gray-100 overflow-hidden">
//             <div className="flex justify-between items-center mb-4">
//                 <h2 className="text-xl font-bold text-gray-800">Candidate Funnel (Active Jobs)</h2>
//             </div>

//             <div className="overflow-x-auto min-w-[700px]">
//                 <table className="w-full text-sm text-left text-gray-600 border-collapse">
//                     {/* Header Row */}
//                     <thead className="text-xs uppercase bg-gray-50 text-gray-500">
//                         <tr>
//                             <th scope="col" className="px-4 py-3 min-w-[200px] sticky left-0 z-10 bg-gray-50 border-r border-gray-100">Job Title (Rounds)</th>
//                             {stages.map(stage => (
//                                 <th key={stage.key} scope="col" className="px-4 py-3 text-center whitespace-nowrap">{stage.label}</th>
//                             ))}
//                         </tr>
//                     </thead>
//                     {/* Job Rows */}
//                     <tbody>
//                         {isLoading ? (
//                             <tr>
//                                 <td colSpan={stages.length + 1} className="text-center py-10 text-gray-400">
//                                     <Loader2 size={20} className="inline animate-spin mr-2" /> Loading active pipeline...
//                                 </td>
//                             </tr>
//                         ) : activeJobs.length === 0 ? (
//                             <tr>
//                                 <td colSpan={stages.length + 1} className="text-center py-10 text-gray-400">
//                                     No active jobs to display pipeline metrics.
//                                 </td>
//                             </tr>
//                         ) : (
//                             activeJobs.map((job, jobIndex) => {
//                                 const isSelected = job.job_id === selectedJobId;
                                
//                                 return (
//                                 <tr 
//                                     key={job.job_id} 
//                                     className={`border-b border-gray-100 hover:bg-gray-50/50 cursor-pointer ${isSelected ? 'bg-blue-50/70 border-l-4 border-blue-500' : ''}`}
//                                     onClick={() => onJobSelect(job.job_id)}
//                                 >
//                                     {/* Job Title Cell */}
//                                     <td className="px-4 py-3 font-medium text-gray-900 sticky left-0 z-10 bg-white/95 border-r border-gray-100 backdrop-blur-[1px]">
//                                         <div className="flex flex-col">
//                                             <span className="truncate max-w-[190px] font-semibold">{job.job_title}</span>
//                                             <span className="text-xs text-gray-500 mt-0.5">{job.interview_rounds} Interview Rounds</span>
//                                         </div>
//                                     </td>
//                                     {/* Stage Cells */}
//                                     {stages.map(stage => {
//                                         const count = job[stage.countKey] as number;
                                        
//                                         // Dynamic cell styling
//                                         let finalCellBg = 'bg-white';
//                                         let finalTextColor = 'text-gray-600';
//                                         let countBg = 'bg-gray-200';

//                                         if (stage.key === 'shortlisted' || stage.key === 'hired') {
//                                             finalCellBg = 'bg-green-50';
//                                             finalTextColor = 'text-green-800';
//                                             countBg = 'bg-green-200';
//                                         } else if (stage.key === 'screening') {
//                                             finalCellBg = 'bg-yellow-50';
//                                             finalTextColor = 'text-yellow-800';
//                                             countBg = 'bg-yellow-200';
//                                         } else if (stage.isInterview) {
//                                             finalCellBg = 'bg-indigo-50';
//                                             finalTextColor = 'text-indigo-800';
//                                             countBg = 'bg-indigo-200';
//                                         }
                                        
//                                         // Conditionally render L-rounds based on job's rounds property
//                                         const roundNumber = stage.key.match(/l(\d)_interview/)?.[1];
//                                         const isRoundNeeded = !roundNumber || parseInt(roundNumber) <= job.interview_rounds;

//                                         if (!isRoundNeeded) {
//                                             return <td key={stage.key} className="px-4 py-3 text-center bg-gray-100/50 border-r border-gray-100">
//                                                 <div className="text-gray-300 font-medium text-xs">N/A</div>
//                                             </td>
//                                         }

//                                         if (count === 0) {
//                                             return <td key={stage.key} className={`px-4 py-3 text-center ${finalCellBg.replace(/50|100/, '50')} border-r border-gray-100`}>
//                                                 <div className="text-gray-300 font-medium">—</div>
//                                             </td>
//                                         }

//                                         return (
//                                             <td 
//                                               key={stage.key} 
//                                               className={`px-4 py-3 text-center ${finalCellBg} border-r border-gray-100 transition-colors duration-200 cursor-pointer hover:shadow-inner`}
//                                             >
//                                                 <div 
//                                                     className={`inline-block px-3 py-1 rounded-md font-semibold text-xs transition-shadow ${countBg} ${finalTextColor} shadow-sm`}
//                                                 >
//                                                     {count} Candidates
//                                                 </div>
//                                             </td>
//                                         );
//                                     })}
//                                 </tr>
//                             )})
//                         )}
//                     </tbody>
//                 </table>
//             </div>
//         </div>
//     );
// };

// // --- Jobs Summary Donut Chart (Rewritten for Professional Appearance) ---
// interface JobsSummaryProps {
//     jobs: JobPostStats[];
//     isLoading: boolean;
// }

// const DonutChart: React.FC<{ data: { label: string, value: number, color: string }[], total: number }> = ({ data, total }) => {
//     const radius = 45;
//     const strokeWidth = 10;
//     const circumference = 2 * Math.PI * radius;
    
//     // The visual starting point is at 12 o'clock (via -rotate-90 on the SVG)
//     let cumulativePercentage = 0; 

//     return (
//         <div className="relative w-40 h-40 mx-auto mb-4">
//             <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
//                 {/* Background Track (Inactive/Total) */}
//                 <circle
//                     cx="50"
//                     cy="50"
//                     r={radius}
//                     fill="transparent"
//                     stroke="#e5e7eb" // Tailwind gray-200
//                     strokeWidth={strokeWidth}
//                 />
                
//                 {/* Segments - Overlapping circles with controlled dashes */}
//                 {data.map((item, index) => {
//                     const percentage = total > 0 ? item.value / total : 0;
//                     const segmentLength = circumference * percentage;
                    
//                     // The rotation offset determines the starting point of the segment.
//                     // We need to rotate by the sum of all *previous* segments.
//                     const rotateAngle = cumulativePercentage * 360;

//                     // Update cumulative percentage for the next segment
//                     cumulativePercentage += percentage;
                    
//                     return (
//                         <circle
//                             key={item.label}
//                             cx="50"
//                             cy="50"
//                             r={radius}
//                             fill="transparent"
//                             stroke={item.color}
//                             strokeWidth={strokeWidth + 0.5} // Slightly thicker for visual pop
//                             strokeLinecap="round"
//                             // stroke-dasharray defines the segment (length, circumference - length)
//                             strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
//                             // stroke-dashoffset initially set to 0, or controlled by rotation
//                             strokeDashoffset={0} 
//                             // Position the segment by rotating the entire circle around the center
//                             style={{ 
//                                 transition: 'transform 0.5s',
//                                 transform: `rotate(${rotateAngle}deg)`,
//                                 transformOrigin: '50% 50%',
//                                 zIndex: index + 1,
//                             }}
//                         />
//                     );
//                 })}

//                 {/* Center Content (Rotate back the text) */}
//                 <text 
//                     x="50" 
//                     y="50" 
//                     textAnchor="middle" 
//                     dominantBaseline="middle" 
//                     className="text-xl font-bold fill-gray-900 transform rotate-90"
//                 >
//                     {total}
//                 </text>
//                 <text 
//                     x="50" 
//                     y="65" 
//                     textAnchor="middle" 
//                     dominantBaseline="middle" 
//                     className="text-xs fill-gray-500 transform rotate-90"
//                 >
//                     TOTAL POSTS
//                 </text>
//             </svg>
//         </div>
//     );
// };

// const JobsSummaryCard: React.FC<JobsSummaryProps> = ({ jobs, isLoading }) => {
//     if (isLoading) {
//         return (
//              <div className="lg:col-span-4 bg-white p-6 rounded-xl shadow-lg border border-gray-100 min-h-[300px] flex items-center justify-center">
//                  <Loader2 size={24} className="animate-spin text-gray-400" />
//              </div>
//         )
//     }
    
//     const activeJobs = jobs.filter(j => j.is_active).length;
//     const inactiveJobs = jobs.filter(j => !j.is_active).length;
    
//     const chartData = [
//         { label: 'Active on Career Page', value: activeJobs, color: '#10B981' }, // Green
//         { label: 'Inactive (On Hold)', value: inactiveJobs, color: '#FCD34D' }, // Yellow/Amber
//     ];
    
//     return (
//         <div className="lg:col-span-4 bg-white p-6 rounded-xl shadow-lg border border-gray-100 min-h-[400px]">
//             <h2 className="text-xl font-bold text-gray-800 mb-4">Job Status Summary</h2>
            
//             <DonutChart data={chartData} total={jobs.length} />
            
//             <div className="space-y-3 mt-4">
//                 {chartData.map((item, index) => (
//                     <div key={item.label} className="flex items-center justify-between text-sm text-gray-700">
//                         <div className="flex items-center gap-2">
//                             <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
//                             <span className="font-medium">{item.label}</span>
//                         </div>
//                         <span className="font-bold">{item.value}</span>
//                     </div>
//                 ))}
//                 <div className="flex items-center justify-between text-base pt-2 border-t border-gray-100 font-bold text-gray-800">
//                      <span>Total Job Posts</span>
//                      <span>{jobs.length}</span>
//                  </div>
//             </div>
//         </div>
//     );
// };


// // --- Utility: Robust job mapping (MOCK Interview Rounds) ---
// function mapFetchedJob(job: any): JobPostStats {
//   const jobId = job.job_id ?? job.jobId ?? job.id ?? "";
//   const rawActive = job.is_active ?? job.isActive ?? job.active ?? job.enabled;
//   const isActive =
//     rawActive === undefined || rawActive === null
//       ? false
//       : typeof rawActive === "boolean"
//         ? rawActive
//         : typeof rawActive === "string"
//           ? rawActive.toLowerCase() === "true"
//           : Boolean(rawActive);

//   // Prefer aggregated counts returned under `profile_counts` 
//   const profileCounts = job.profile_counts ?? job.profileCounts ?? null;
//   const shortlisted = profileCounts?.shortlisted ?? job.shortlisted ?? job.shortlisted_count ?? 0;
//   const rejected = profileCounts?.rejected ?? job.rejected ?? job.rejected_count ?? 0;
//   const under_review = profileCounts?.under_review ?? job.under_review ?? job.underReview ?? 0;
//   const onboarding = profileCounts?.onboarding ?? job.onboarding ?? 0;
//   const interviews_scheduled = profileCounts?.interviews_scheduled ?? profileCounts?.interviews ?? job.interviews ?? job.interview_count ?? job.interviews_count ?? 0;
//   const onboarding_timestamps = profileCounts?.onboarding_timestamps ?? profileCounts?.onboarding_dates ?? job.onboarding_timestamps ?? job.onboarding_dates ?? null;
//   const total_applications = profileCounts?.applied ?? job.total_applications ?? (shortlisted + rejected + under_review + onboarding);
  
//   // ✨ MOCK: Derive Interview Rounds (Rounds are mocked: 3 for Senior/Lead, 2 for others)
//   const isSenior = job.job_title.toLowerCase().includes('senior') || job.job_title.toLowerCase().includes('lead');
//   const interview_rounds = isSenior ? 3 : 2; 

//   // Distribute interviews across L1, L2, L3 based on the job's rounds
//   const interviewsInProgress = Math.max(0, interviews_scheduled - onboarding); 
//   let l1_interview = 0;
//   let l2_interview = 0;
//   let l3_interview = 0;
  
//   // Simple distribution logic: e.g., 50% L1, 30% L2, 20% L3
//   if (interview_rounds >= 1) l1_interview = Math.floor(interviewsInProgress * (interview_rounds === 1 ? 1 : 0.5));
//   if (interview_rounds >= 2) l2_interview = Math.floor(interviewsInProgress * (interview_rounds === 2 ? 0.5 : 0.3));
//   if (interview_rounds >= 3) l3_interview = Math.max(0, interviewsInProgress - l1_interview - l2_interview);
  
//   // Screening is defined as candidates in 'Under Review' status
//   const screening_in_progress = Math.max(0, under_review);
//   const hired = onboarding;


//   return {
//     job_id: jobId,
//     job_title: job.job_title || 'Untitled Job',
//     posted_date: job.posted_date || null,
//     total_applications,
//     shortlisted,
//     rejected,
//     under_review,
//     onboarding,
//     interviews_scheduled,
//     onboarding_timestamps,
//     is_active: isActive,
//     // ✨ NEW MOCKED / DERIVED FIELDS
//     interview_rounds,
//     screening: Math.max(0, screening_in_progress),
//     l1_interview: Math.max(0, l1_interview),
//     l2_interview: Math.max(0, l2_interview),
//     l3_interview: Math.max(0, l3_interview),
//     hired: hired,
//   };
// }


// // --- Main Dashboard Component ---
// export default function Dashboard() {
//   const [data, setData] = useState<DashboardData | null>(null);
//   const [sortedJobs, setSortedJobs] = useState<JobPostStats[]>([]);
//   // State to track which job is selected from the funnel chart
//   const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
//   const [isLoading, setIsLoading] = useState(true);
//   const { showToast } = useToast();
//   const navigate = useNavigate();

//   // Determine the job whose metrics should be shown in the top row
//   const selectedJob = useMemo(() => {
//       return sortedJobs.find(job => job.job_id === selectedJobId) || null;
//   }, [sortedJobs, selectedJobId]);

//   // Aggregate metrics or selected job's metrics
//   const displayMetrics = useMemo(() => {
//     if (selectedJob) {
//         return {
//             title: selectedJob.job_title,
//             applied: selectedJob.total_applications,
//             shortlisted: selectedJob.shortlisted,
//             underReview: selectedJob.under_review,
//             rejected: selectedJob.rejected,
//         };
//     }
//     // Fallback to aggregated totals (initial view)
//     return {
//         title: 'All Active Job Posts',
//         applied: data?.total_candidates_applied ?? 0,
//         shortlisted: data?.total_shortlisted ?? 0,
//         underReview: data?.total_under_review ?? 0,
//         rejected: data?.total_rejected ?? 0,
//     };
//   }, [selectedJob, data]);

//   // Fetch and process data 
//   const fetchJobStats = useCallback(async () => {
//     setIsLoading(true);
//     try {
//       const [allRes, activeRes] = await Promise.all([
//         getAllJobPosts(),
//         getActiveJobPosts()
//       ]);
//       if (allRes.success) {
//         const allJobsRaw = Array.isArray(allRes.data) ? allRes.data : (allRes.data?.jobs || allRes.data);
//         const activeJobIds = new Set((activeRes.data?.jobs || activeRes.data || []).map((j: any) => j.job_id ?? j.jobId ?? j.id));
        
//         const jobs: JobPostStats[] = allJobsRaw.map((job: any) => {
//           const mapped = mapFetchedJob(job);
//           return {
//             ...mapped,
//             is_active: activeJobIds.has(mapped.job_id)
//           };
//         });

//         // Calculate aggregate numbers 
//         const total_applications_agg = jobs.reduce((sum, j) => sum + j.total_applications, 0);
//         const total_shortlisted_agg = jobs.reduce((sum, j) => sum + j.shortlisted, 0);
//         const total_rejected_agg = jobs.reduce((sum, j) => sum + j.rejected, 0);
//         const total_under_review_agg = jobs.reduce((sum, j) => sum + j.under_review, 0);
        
//         setSortedJobs(jobs);
//         setData({
//           total_jobs: jobs.length,
//           active_jobs: jobs.filter(j => j.is_active).length,
//           total_candidates_applied: total_applications_agg,
//           total_shortlisted: total_shortlisted_agg,
//           total_rejected: total_rejected_agg,
//           total_under_review: total_under_review_agg,
//           job_stats: jobs,
//         });
        
//         // Default to showing the top performing active job's metrics if none selected
//         if (!selectedJobId) {
//              const topJob = jobs.filter(j => j.is_active).sort((a, b) => b.total_applications - a.total_applications)[0];
//              if (topJob) setSelectedJobId(topJob.job_id);
//         }

//       } else {
//         showToast(allRes.error || 'Failed to load dashboard data.', 'error');
//         setData(null);
//       }
//     } catch (error: any) {
//       showToast(error.message || 'An error occurred while fetching data.', 'error');
//       setData(null);
//     } finally {
//       setIsLoading(false);
//     }
//   }, [showToast, selectedJobId]);

//   // Fetch data on component mount
//   useEffect(() => {
//     fetchJobStats();
//   }, [fetchJobStats]);

  
//   // --- Render Logic ---
//   if (isLoading && !data) {
//     return (
//       <div className="flex flex-col items-center justify-center h-96">
//         <Loader2 size={48} className="text-[var(--color-primary-500)] animate-spin" />
//         <p className="mt-4 text-gray-500">Loading Dashboard Data...</p>
//       </div>
//     );
//   }

//   if (!data && !isLoading) {
//       return (
//           <div className="flex flex-col items-center justify-center h-96 bg-white p-6 rounded-lg shadow-sm border border-red-200">
//               <Activity size={48} className="text-red-500 mb-4" />
//               <h1 className="text-xl font-bold text-red-700">Failed to Load Dashboard</h1>
//               <p className="text-gray-500 mt-2 text-center">
//                   Could not retrieve job statistics. Please check your connection or try again later.
//               </p>
//               <button
//                   onClick={fetchJobStats}
//                   className="mt-6 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
//               >
//                   Retry Loading
//               </button>
//           </div>
//       );
//   }


//   // --- Main Dashboard Layout ---
//   return (
//     <>
//       {/* 1. Dynamic Metric Cards (The new Top Tabs) */}
//       <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
//         <div className="lg:col-span-12">
//             <h2 className="text-2xl font-bold text-gray-800 mb-4 truncate" title={displayMetrics.title}>
//                <span className="text-[var(--color-primary-500)]">{displayMetrics.title}</span>
//             </h2>
//         </div>
//         <div className="lg:col-span-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4 sm:gap-6">
//           <StatCard 
//             title="Total Candidates Applied" 
//             value={displayMetrics.applied} 
//             icon={FileText} 
//             colorClass="text-indigo-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-600" 
//           />
        
//           <StatCard 
//             title="Shortlisted Candidates" 
//             value={displayMetrics.shortlisted} 
//             icon={CheckSquare} 
//             colorClass="text-green-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-800" 
//           />

//             <StatCard 
//             title="Under Review" 
//             value={displayMetrics.underReview} 
//             icon={TrendingUp} 
//             colorClass="text-yellow-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-700" 
//           />
//           <StatCard 
//             title="Rejected Candidates" 
//             value={displayMetrics.rejected} 
//             icon={XSquare} 
//             colorClass="text-red-500" 
//             isLoading={isLoading} 
//             className="animate-fade-in animate-delay-900" 
//           />
//         </div>
        
//         {/* 2. Jobs Summary + Pipeline Activity Grid */}
//         <div className="lg:col-span-12 grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
//             <JobsSummaryCard jobs={sortedJobs} isLoading={isLoading} />
//             <PipelineActivityGrid 
//                 jobs={sortedJobs} 
//                 isLoading={isLoading} 
//                 onJobSelect={setSelectedJobId}
//                 selectedJobId={selectedJobId}
//             />
//         </div>
//       </div>
//     </>
//   );
// }


import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Briefcase,
  Users,
  CheckSquare,
  XSquare,
  TrendingUp,
  Loader2,
  Activity,
  FileText,
  ChevronDown,
  Calendar,
} from 'lucide-react';
import { getAllJobPosts, getActiveJobPosts, getJobCandidates } from '../../api/jobApi'; 
import { useToast } from '../../context/ModalContext'; 

// --- Data Structures ---
interface JobPostStats {
  job_id: string;
  job_title: string;
  posted_date?: string | null;
  total_applications: number;
  shortlisted: number; // Final Shortlisted
  rejected: number;     
  under_review: number; // Screening candidates (Curation)
  onboarding: number;
  interviews_scheduled: number;
  onboarding_timestamps?: string[] | null;
  is_active: boolean;
  // ✨ NEW FIELDS for detailed pipeline counts
  interview_rounds: number; 
  screening: number; 
  l1_interview: number;
  l2_interview: number;
  l3_interview: number;
  hired: number;
  // Data for StatCard source
  total_interviewed: number; // Added for StatCard source
  total_hired: number;       // Added for StatCard source
}

interface DashboardData {
  total_jobs: number;
  active_jobs: number;
  // Dynamic Metrics - Initial State (Aggregates)
  total_candidates_applied: number;
  total_shortlisted: number;
  total_rejected: number;
  total_under_review: number;
  // ✨ ADDED: New Aggregates for Top Bar
  total_interviewed: number;
  total_hired: number;
  job_stats: JobPostStats[];
}

// (no explicit props required)

// --- Helper Components (StatCard - Unchanged) ---
interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ElementType;
  colorClass: string;
  isLoading: boolean;
  className?: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon: Icon, colorClass, isLoading, className }) => (
  <div
    className={`bg-white p-5 rounded-xl shadow-sm border border-gray-100 transition-shadow duration-200 ${className}`}
  >
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-semibold text-gray-500">{title}</h3>
      <div className={`p-2 rounded-lg ${colorClass.replace('text-', 'bg-').replace('-500', '-50')}`}>
        <Icon size={18} className={`${colorClass}`} />
      </div>
    </div>
    {isLoading ? (
      <div className="h-8 bg-gray-200 rounded animate-pulse w-1/2"></div>
    ) : (
      <p className="text-3xl font-bold text-gray-900">{value}</p>
    )}
  </div>
);


// --- Pipeline Activity Grid (The Core Funnel View - Unchanged) ---
interface PipelineGridProps {
    jobs: JobPostStats[];
    isLoading: boolean;
    onJobSelect: (jobId: string) => void;
    selectedJobId: string | null;
}

// job color helper removed (not used right now)

const PipelineActivityGrid: React.FC<PipelineGridProps> = ({ jobs, isLoading, onJobSelect, selectedJobId }) => {
    const activeJobs = jobs.filter(j => j.is_active);

    const stages = [
        { key: 'total_applications', label: 'New Applied', countKey: 'total_applications' as keyof JobPostStats },
        { key: 'screening', label: 'Screening (Curation)', countKey: 'screening' as keyof JobPostStats },
        { key: 'l1_interview', label: 'L1 Interview', countKey: 'l1_interview' as keyof JobPostStats, isInterview: true },
        { key: 'l2_interview', label: 'L2 Interview', countKey: 'l2_interview' as keyof JobPostStats, isInterview: true },
        { key: 'l3_interview', label: 'L3 Interview', countKey: 'l3_interview' as keyof JobPostStats, isInterview: true },
        { key: 'shortlisted', label: 'Final Shortlisted', countKey: 'shortlisted' as keyof JobPostStats },
        { key: 'hired', label: 'Hired/Onboarded', countKey: 'hired' as keyof JobPostStats },
    ];
    
    return (
        <div className="lg:col-span-8 bg-white p-6 rounded-xl shadow-lg border border-gray-100 overflow-hidden">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800">Candidate Funnel (Active Jobs)</h2>
            </div>

            <div className="overflow-x-auto min-w-[700px]">
                <table className="w-full text-sm text-left text-gray-600 border-collapse">
                    {/* Header Row */}
                    <thead className="text-xs uppercase bg-gray-50 text-gray-500">
                        <tr>
                            <th scope="col" className="px-4 py-3 min-w-[200px] sticky left-0 z-10 bg-gray-50 border-r border-gray-100">Job Title (Rounds)</th>
                            {stages.map(stage => (
                                <th key={stage.key} scope="col" className="px-4 py-3 text-center whitespace-nowrap">{stage.label}</th>
                            ))}
                        </tr>
                    </thead>
                    {/* Job Rows */}
                    <tbody>
                        {isLoading ? (
                            <tr>
                                <td colSpan={stages.length + 1} className="text-center py-10 text-gray-400">
                                    <Loader2 size={20} className="inline animate-spin mr-2" /> Loading active pipeline...
                                </td>
                            </tr>
                        ) : activeJobs.length === 0 ? (
                            <tr>
                                <td colSpan={stages.length + 1} className="text-center py-10 text-gray-400">
                                    No active jobs to display pipeline metrics.
                                </td>
                            </tr>
            ) : (
              activeJobs.map((job) => {
                                const isSelected = job.job_id === selectedJobId;
                                
                                return (
                                <tr 
                                    key={job.job_id} 
                                    className={`border-b border-gray-100 hover:bg-gray-50/50 cursor-pointer ${isSelected ? 'bg-blue-50/70 border-l-4 border-blue-500' : ''}`}
                                    onClick={() => onJobSelect(job.job_id)}
                                >
                                    {/* Job Title Cell */}
                                    <td className="px-4 py-3 font-medium text-gray-900 sticky left-0 z-10 bg-white/95 border-r border-gray-100 backdrop-blur-[1px]">
                                        <div className="flex flex-col">
                                            <span className="truncate max-w-[190px] font-semibold">{job.job_title}</span>
                                            <span className="text-xs text-gray-500 mt-0.5">{job.interview_rounds} Interview Rounds</span>
                                        </div>
                                    </td>
                                    {/* Stage Cells */}
                                    {stages.map(stage => {
                                        const count = job[stage.countKey] as number;
                                        
                                        // Dynamic cell styling
                                        let finalCellBg = 'bg-white';
                                        let finalTextColor = 'text-gray-600';
                                        let countBg = 'bg-gray-200';

                                        if (stage.key === 'shortlisted' || stage.key === 'hired') {
                                            finalCellBg = 'bg-green-50';
                                            finalTextColor = 'text-green-800';
                                            countBg = 'bg-green-200';
                                        } else if (stage.key === 'screening') {
                                            finalCellBg = 'bg-yellow-50';
                                            finalTextColor = 'text-yellow-800';
                                            countBg = 'bg-yellow-200';
                                        } else if (stage.isInterview) {
                                            finalCellBg = 'bg-indigo-50';
                                            finalTextColor = 'text-indigo-800';
                                            countBg = 'bg-indigo-200';
                                        }
                                        
                                        // Conditionally render L-rounds based on job's rounds property
                                        const roundNumber = stage.key.match(/l(\d)_interview/)?.[1];
                                        const isRoundNeeded = !roundNumber || parseInt(roundNumber) <= job.interview_rounds;

                                        if (!isRoundNeeded) {
                                            return <td key={stage.key} className="px-4 py-3 text-center bg-gray-100/50 border-r border-gray-100">
                                                <div className="text-gray-300 font-medium text-xs">N/A</div>
                                            </td>
                                        }

                                        if (count === 0) {
                                            return <td key={stage.key} className={`px-4 py-3 text-center ${finalCellBg.replace(/50|100/, '50')} border-r border-gray-100`}>
                                                <div className="text-gray-300 font-medium">—</div>
                                            </td>
                                        }

                                        return (
                                            <td 
                                              key={stage.key} 
                                              className={`px-4 py-3 text-center ${finalCellBg} border-r border-gray-100 transition-colors duration-200 cursor-pointer hover:shadow-inner`}
                                            >
                                                <div 
                                                    className={`inline-block px-3 py-1 rounded-md font-semibold text-xs transition-shadow ${countBg} ${finalTextColor} shadow-sm`}
                                                >
                                                    {count} Candidates
                                                </div>
                                            </td>
                                        );
                                    })}
                                </tr>
                            )})
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// --- Jobs Summary Donut Chart (Rewritten for Professional Appearance - Unchanged) ---
interface JobsSummaryProps {
    jobs: JobPostStats[];
    isLoading: boolean;
}

const DonutChart: React.FC<{ data: { label: string, value: number, color: string }[], total: number }> = ({ data, total }) => {
    const radius = 45;
    const strokeWidth = 10;
    const circumference = 2 * Math.PI * radius;
    let cumulativePercentage = 0; 

    return (
        <div className="relative w-40 h-40 mx-auto mb-4">
            <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
                <circle
                    cx="50"
                    cy="50"
                    r={radius}
                    fill="transparent"
                    stroke="#e5e7eb" // Tailwind gray-200
                    strokeWidth={strokeWidth}
                />
                {data.map((item, index) => {
                    const percentage = total > 0 ? item.value / total : 0;
                    const segmentLength = circumference * percentage;
                    const rotateAngle = cumulativePercentage * 360;
                    cumulativePercentage += percentage;
                    
                    return (
                        <circle
                            key={item.label}
                            cx="50"
                            cy="50"
                            r={radius}
                            fill="transparent"
                            stroke={item.color}
                            strokeWidth={strokeWidth + 0.5} // Slightly thicker for visual pop
                            strokeLinecap="round"
                            strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
                            strokeDashoffset={0} 
                            style={{ 
                                transition: 'transform 0.5s',
                                transform: `rotate(${rotateAngle}deg)`,
                                transformOrigin: '50% 50%',
                                zIndex: index + 1,
                            }}
                        />
                    );
                })}
                <text 
                    x="50" 
                    y="50" 
                    textAnchor="middle" 
                    dominantBaseline="middle" 
                    className="text-xl font-bold fill-gray-900 transform rotate-90"
                >
                    {total}
                </text>
                <text 
                    x="50" 
                    y="65" 
                    textAnchor="middle" 
                    dominantBaseline="middle" 
                    className="text-xs fill-gray-500 transform rotate-90"
                >
                    TOTAL POSTS
                </text>
            </svg>
        </div>
    );
};

const JobsSummaryCard: React.FC<JobsSummaryProps> = ({ jobs, isLoading }) => {
    if (isLoading) {
        return (
             <div className="lg:col-span-4 bg-white p-6 rounded-xl shadow-lg border border-gray-100 min-h-[300px] flex items-center justify-center">
                 <Loader2 size={24} className="animate-spin text-gray-400" />
             </div>
        )
    }
    
    const activeJobs = jobs.filter(j => j.is_active).length;
    const inactiveJobs = jobs.filter(j => !j.is_active).length;
    
    const chartData = [
        { label: 'Active on Career Page', value: activeJobs, color: '#10B981' },
        { label: 'Inactive (On Hold)', value: inactiveJobs, color: '#FCD34D' },
    ];
    
    return (
        <div className="lg:col-span-4 bg-white p-6 rounded-xl shadow-lg border border-gray-100 min-h-[400px]">
            <h2 className="text-xl font-bold text-gray-800 mb-4">Job Status Summary</h2>
            
            <DonutChart data={chartData} total={jobs.length} />
            
            <div className="space-y-3 mt-4">
                {chartData.map((item) => (
                    <div key={item.label} className="flex items-center justify-between text-sm text-gray-700">
                        <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }}></span>
                            <span className="font-medium">{item.label}</span>
                        </div>
                        <span className="font-bold">{item.value}</span>
                    </div>
                ))}
                <div className="flex items-center justify-between text-base pt-2 border-t border-gray-100 font-bold text-gray-800">
                     <span>Total Job Posts</span>
                     <span>{jobs.length}</span>
                 </div>
            </div>
        </div>
    );
};

// --- Small helpers used in expanded panels ---
function capitalize(s: string) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function parseCandidateDate(c: any): Date | null {
  const fields = ['applied_at', 'appliedAt', 'created_at', 'createdAt', 'createdOn', 'applied_on', 'applied_on'];
  for (const f of fields) {
    const v = c[f];
    if (!v) continue;
    const d = new Date(v);
    if (!isNaN(d.getTime())) return d;
  }
  return null;
}

const TodaysActivityChart: React.FC<{ jobs: JobPostStats[]; candidates: any[] }> = ({ jobs, candidates }) => {
  // Aggregate today's new application count per job (best-effort based on candidate timestamps)
  const today = new Date();
  today.setHours(0,0,0,0);

  const countsByJob: Record<string, number> = {};

  (candidates || []).forEach((c) => {
    const d = parseCandidateDate(c);
    if (!d) return;
    const d0 = new Date(d);
    d0.setHours(0,0,0,0);
    if (d0.getTime() !== today.getTime()) return;
    const jobId = c.job_id ?? c.jobId ?? c.job?.job_id ?? c.job?.id ?? 'unknown';
    countsByJob[jobId] = (countsByJob[jobId] || 0) + 1;
  });

  // Fallback: if no candidate-level timestamps, try approximating from jobs (not possible reliably)
  const items = jobs.map(j => ({ id: j.job_id, title: j.job_title, count: countsByJob[j.job_id] ?? 0 }));
  const max = Math.max(1, ...items.map(i => i.count));

  return (
    <div className="space-y-3">
      {items.slice(0, 7).map(it => (
        <div key={it.id} className="flex items-center gap-3">
          <div className="min-w-0">
            <div className="text-sm font-medium truncate">{it.title}</div>
            <div className="text-xs text-gray-500">{it.count} new</div>
          </div>
          <div className="flex-1 h-3 bg-gray-100 rounded overflow-hidden">
            <div className="h-3 bg-blue-500 rounded" style={{ width: `${(it.count / max) * 100}%` }} />
          </div>
        </div>
      ))}
      {items.every(i => i.count === 0) && (
        <div className="text-sm text-gray-500">No activity recorded for today (data depends on candidate timestamps).</div>
      )}
    </div>
  );
};


// --- Utility: Robust job mapping (MOCK Interview Rounds) ---
function mapFetchedJob(job: any): JobPostStats {
  const jobId = job.job_id ?? job.jobId ?? job.id ?? "";
  const rawActive = job.is_active ?? job.isActive ?? job.active ?? job.enabled;
  const isActive =
    rawActive === undefined || rawActive === null
      ? false
      : typeof rawActive === "boolean"
        ? rawActive
        : typeof rawActive === "string"
          ? rawActive.toLowerCase() === "true"
          : Boolean(rawActive);

  // Prefer aggregated counts returned under `profile_counts` 
  const profileCounts = job.profile_counts ?? job.profileCounts ?? null;
  const shortlisted = profileCounts?.shortlisted ?? job.shortlisted ?? job.shortlisted_count ?? 0;
  const rejected = profileCounts?.rejected ?? job.rejected ?? job.rejected_count ?? 0;
  const under_review = profileCounts?.under_review ?? job.under_review ?? job.underReview ?? 0;
  const onboarding = profileCounts?.onboarding ?? job.onboarding ?? 0;
  const interviews_scheduled = profileCounts?.interviews_scheduled ?? profileCounts?.interviews ?? job.interviews ?? job.interview_count ?? job.interviews_count ?? 0;
  const onboarding_timestamps = profileCounts?.onboarding_timestamps ?? profileCounts?.onboarding_dates ?? job.onboarding_timestamps ?? job.onboarding_dates ?? null;
  const total_applications = profileCounts?.applied ?? job.total_applications ?? (shortlisted + rejected + under_review + onboarding);
  
  // ✨ MOCK: Derive Interview Rounds (Rounds are mocked: 3 for Senior/Lead, 2 for others)
  const isSenior = job.job_title.toLowerCase().includes('senior') || job.job_title.toLowerCase().includes('lead');
  const interview_rounds = isSenior ? 3 : 2; 

  // Distribute interviews across L1, L2, L3 based on the job's rounds
  const interviewsInProgress = Math.max(0, interviews_scheduled - onboarding); 
  let l1_interview = 0;
  let l2_interview = 0;
  let l3_interview = 0;
  
  // Simple distribution logic: e.g., 50% L1, 30% L2, 20% L3
  if (interview_rounds >= 1) {
    const factor = interview_rounds <= 1 ? 1 : 0.5;
    l1_interview = Math.floor(interviewsInProgress * factor);
  }
  if (interview_rounds >= 2) l2_interview = Math.floor(interviewsInProgress * (interview_rounds === 2 ? 0.5 : 0.3));
  if (interview_rounds >= 3) l3_interview = Math.max(0, interviewsInProgress - l1_interview - l2_interview);
  
  // Screening is defined as candidates in 'Under Review' status
  const screening_in_progress = Math.max(0, under_review);
  const hired = onboarding;

  // Total Interviewed for StatCard Source
  const total_interviewed_for_job = l1_interview + l2_interview + l3_interview;
  const total_hired_for_job = hired;


  return {
    job_id: jobId,
    job_title: job.job_title || 'Untitled Job',
    posted_date: job.posted_date || null,
    total_applications,
    shortlisted,
    rejected,
    under_review,
    onboarding,
    interviews_scheduled,
    onboarding_timestamps,
    is_active: isActive,
    // ✨ NEW MOCKED / DERIVED FIELDS
    interview_rounds,
    screening: Math.max(0, screening_in_progress),
    l1_interview: Math.max(0, l1_interview),
    l2_interview: Math.max(0, l2_interview),
    l3_interview: Math.max(0, l3_interview),
    hired: hired,
    total_interviewed: total_interviewed_for_job,
    total_hired: total_hired_for_job,
  };
}


// --- Main Dashboard Component ---
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [sortedJobs, setSortedJobs] = useState<JobPostStats[]>([]);
  const [jobCandidates, setJobCandidates] = useState<any[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  // State to track which job is selected from the funnel chart
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { showToast } = useToast();
  

  // Determine the job whose metrics should be shown in the top row
  const selectedJob = useMemo(() => {
      return sortedJobs.find(job => job.job_id === selectedJobId) || null;
  }, [sortedJobs, selectedJobId]);

  // Aggregate metrics or selected job's metrics
  const displayMetrics = useMemo(() => {
    // Calculate total interview and hired counts for the selected job/aggregate
    const interviewedCount = selectedJob ? selectedJob.total_interviewed : (data?.total_interviewed ?? 0);
    const hiredCount = selectedJob ? selectedJob.total_hired : (data?.total_hired ?? 0);
    
    // Total Candidates in Pipeline (Applied + Interviewing + Shortlisted + Rejected + Hired)
    // The safest and most inclusive "Total Candidates" is simply the `applied` count,
    // since all other statuses are a subset of or derived from the applied pool.
    const totalPipelineCount = (data?.total_candidates_applied ?? 0); 

    if (selectedJob) {
        return {
            title: selectedJob.job_title,
            applied: selectedJob.total_applications,
            underReview: selectedJob.under_review,
            shortlisted: selectedJob.shortlisted,
            rejected: selectedJob.rejected,
            interviewed: interviewedCount,
            hired: hiredCount,
            totalPipeline: selectedJob.total_applications,
        };
    }
    // Fallback to aggregated totals (initial view)
    return {
        title: 'All Active Job Posts',
        applied: data?.total_candidates_applied ?? 0,
        underReview: data?.total_under_review ?? 0,
        shortlisted: data?.total_shortlisted ?? 0,
        rejected: data?.total_rejected ?? 0,
        interviewed: interviewedCount,
        hired: hiredCount,
        totalPipeline: totalPipelineCount,
    };
  }, [selectedJob, data]);

  // Fetch and process data 
  const fetchJobStats = useCallback(async () => {
    setIsLoading(true);
    try {
      const [allRes, activeRes] = await Promise.all([
        getAllJobPosts(),
        getActiveJobPosts()
      ]);
      if (allRes.success) {
        const allJobsRaw = Array.isArray(allRes.data) ? allRes.data : (allRes.data?.jobs || allRes.data);
        const activeJobIds = new Set((activeRes.data?.jobs || activeRes.data || []).map((j: any) => j.job_id ?? j.jobId ?? j.id));
        
        const jobs: JobPostStats[] = allJobsRaw.map((job: any) => {
          const mapped = mapFetchedJob(job);
          return {
            ...mapped,
            is_active: activeJobIds.has(mapped.job_id)
          };
        });

        // Calculate aggregate numbers 
        const total_applications_agg = jobs.reduce((sum, j) => sum + j.total_applications, 0);
        const total_shortlisted_agg = jobs.reduce((sum, j) => sum + j.shortlisted, 0);
        const total_rejected_agg = jobs.reduce((sum, j) => sum + j.rejected, 0);
        const total_under_review_agg = jobs.reduce((sum, j) => sum + j.under_review, 0);
        const total_interviewed_agg = jobs.reduce((sum, j) => sum + j.total_interviewed, 0);
        const total_hired_agg = jobs.reduce((sum, j) => sum + j.total_hired, 0);
        
        setSortedJobs(jobs);
        setData({
          total_jobs: jobs.length,
          active_jobs: jobs.filter(j => j.is_active).length,
          total_candidates_applied: total_applications_agg,
          total_shortlisted: total_shortlisted_agg,
          total_rejected: total_rejected_agg,
          total_under_review: total_under_review_agg,
          total_interviewed: total_interviewed_agg,
          total_hired: total_hired_agg,
          job_stats: jobs,
        });
        
        // Default to showing the top performing active job's metrics if none selected
        if (!selectedJobId) {
             const topJob = jobs.filter(j => j.is_active).sort((a, b) => b.total_applications - a.total_applications)[0];
             if (topJob) setSelectedJobId(topJob.job_id);
        }

      } else {
        showToast(allRes.error || 'Failed to load dashboard data.', 'error');
        setData(null);
      }
    } catch (error: any) {
      showToast(error.message || 'An error occurred while fetching data.', 'error');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [showToast, selectedJobId]);

  // Fetch candidates for selected job (expandable details)
  const fetchCandidatesForJob = useCallback(async (jobId?: string | null) => {
    if (!jobId) return setJobCandidates([]);
    setCandidatesLoading(true);
    try {
      // Use jobApi.getJobCandidates
      const res = await getJobCandidates(jobId);
      if (res.success) {
        // Normalize payload: backend may wrap actual array under data.data or data.profiles
        const payload = res.data && res.data.data !== undefined ? res.data.data : res.data;
        const list = Array.isArray(payload) ? payload : (payload?.profiles ?? payload?.candidates ?? []);
        setJobCandidates(list || []);
      } else {
        showToast(res.error || 'Failed to fetch candidates for job', 'error');
        setJobCandidates([]);
      }
    } catch (err: any) {
      showToast(err?.message || 'Error fetching candidates', 'error');
      setJobCandidates([]);
    } finally {
      setCandidatesLoading(false);
    }
  }, [showToast]);

  // Fetch data on component mount
  useEffect(() => {
    fetchJobStats();
  }, [fetchJobStats]);

  useEffect(() => {
    // whenever selected job changes fetch its candidates for expanded view
    fetchCandidatesForJob(selectedJobId);
  }, [selectedJobId, fetchCandidatesForJob]);

  
  // --- Render Logic ---
  if (isLoading && !data) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <Loader2 size={48} className="text-[var(--color-primary-500)] animate-spin" />
        <p className="mt-4 text-gray-500">Loading Dashboard Data...</p>
      </div>
    );
  }

  if (!data && !isLoading) {
      return (
          <div className="flex flex-col items-center justify-center h-96 bg-white p-6 rounded-lg shadow-sm border border-red-200">
              <Activity size={48} className="text-red-500 mb-4" />
              <h1 className="text-xl font-bold text-red-700">Failed to Load Dashboard</h1>
              <p className="text-gray-500 mt-2 text-center">
                  Could not retrieve job statistics. Please check your connection or try again later.
              </p>
              <button
                  onClick={fetchJobStats}
                  className="mt-6 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                  Retry Loading
              </button>
          </div>
      );
  }


  // --- Main Dashboard Layout ---
  return (
    <>
      {/* 1. Dynamic Metric Cards (The new Top Tabs) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
        <div className="lg:col-span-12">
            <h2 className="text-2xl font-bold text-gray-800 mb-4 truncate" title={displayMetrics.title}>
                Dashboard Overview: <span className="text-[var(--color-primary-500)]">{displayMetrics.title}</span>
            </h2>
        </div>
        
        {/* Expanded 6-column grid for full pipeline view */}
        <div className="lg:col-span-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 sm:gap-6">
          <StatCard
            title="Total Job Applications" 
            value={displayMetrics.applied} 
            icon={FileText} 
            colorClass="text-indigo-500" 
            isLoading={isLoading} 
            className="animate-fade-in animate-delay-600" 
          />
          <StatCard 
            title="Under Review (Screening)" 
            value={displayMetrics.underReview} 
            icon={TrendingUp} 
            colorClass="text-yellow-500" 
            isLoading={isLoading} 
            className="animate-fade-in animate-delay-700" 
          />
          <StatCard 
            title="Candidates Interviewed" 
            value={displayMetrics.interviewed} 
            icon={Activity} 
            colorClass="text-emerald-500" 
            isLoading={isLoading} 
            className="animate-fade-in animate-delay-800" 
          />
          <StatCard 
            title="Shortlisted Candidates" 
            value={displayMetrics.shortlisted} 
            icon={CheckSquare} 
            colorClass="text-green-500" 
            isLoading={isLoading} 
            className="animate-fade-in animate-delay-900" 
          />
          <StatCard 
            title="Rejected Candidates" 
            value={displayMetrics.rejected} 
            icon={XSquare} 
            colorClass="text-red-500" 
            isLoading={isLoading} 
            className="animate-fade-in animate-delay-1000" 
          />
          <StatCard 
            title="Total Hired/Onboarded" 
            value={displayMetrics.hired} 
            icon={Users} 
            colorClass="text-purple-500" 
            isLoading={isLoading} 
            className="animate-fade-in animate-delay-1100" 
          />
        </div>
        
        {/* 2. Jobs Summary + Pipeline Activity Grid + Right column with analytics */}
        <div className="lg:col-span-12 grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8">
            <div className="lg:col-span-8">
                <PipelineActivityGrid 
                    jobs={sortedJobs} 
                    isLoading={isLoading} 
                    onJobSelect={setSelectedJobId}
                    selectedJobId={selectedJobId}
                />

                {/* Expanded details panel for selected job */}
                {selectedJobId && (
                  <div className="mt-6 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Briefcase className="text-gray-500" />
                        <h3 className="text-lg font-semibold">Job Details</h3>
                      </div>
                      <div className="text-sm text-gray-500">Click a row to switch job</div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <div className="p-3 bg-gray-50 rounded">
                        <div className="text-xs text-gray-500">Total Applied</div>
                        <div className="font-bold text-lg">{selectedJob?.total_applications ?? '—'}</div>
                      </div>
                      <div className="p-3 bg-gray-50 rounded">
                        <div className="text-xs text-gray-500">Interviews (all levels)</div>
                        <div className="font-bold text-lg">{selectedJob?.total_interviewed ?? '—'}</div>
                      </div>
                      <div className="p-3 bg-gray-50 rounded">
                        <div className="text-xs text-gray-500">Hired / Onboarded</div>
                        <div className="font-bold text-lg">{selectedJob?.total_hired ?? '—'}</div>
                      </div>
                    </div>

                    {/* Per-level expandable lists */}
                    <div className="space-y-3">
                      {['screening', 'l1_interview', 'l2_interview', 'l3_interview', 'shortlisted', 'hired'].map((key) => {
                        const labelMap: any = {
                          screening: 'Screening',
                          l1_interview: 'L1 Interview',
                          l2_interview: 'L2 Interview',
                          l3_interview: 'L3 Interview',
                          shortlisted: 'Shortlisted',
                          hired: 'Hired',
                        };
                        const count = (selectedJob as any)?.[key] ?? 0;
                        // find candidates matching this level from fetched jobCandidates
                        const candidatesForLevel = jobCandidates.filter(c => {
                          // defensive checks for various shapes
                          const status = (c.status ?? c.current_status ?? c.profile_status ?? '').toString().toLowerCase();
                          const interviews = c.interviews ?? c.interview_rounds ?? [];
                          if (key === 'screening') return status.includes('under') || status.includes('screen');
                          if (key === 'shortlisted') return status.includes('shortlist') || status.includes('shortlisted');
                          if (key === 'hired') return status.includes('hired') || status.includes('onboard');
                          if (key.startsWith('l') && interviews && Array.isArray(interviews)) {
                            // match by interview round present or candidate.current_round
                            const roundMatch = (c.current_round ?? c.currentRound ?? c.round ?? null);
                            if (roundMatch) return String(roundMatch).includes(key.match(/l(\d)/)?.[1] ?? '');
                            // else fallback: if candidate has interview objects, check any interview.level
                            return interviews.some((iv: any) => String(iv.round ?? iv.level ?? iv.interview_round ?? '').includes(key.match(/l(\d)/)?.[1] ?? ''));
                          }
                          return false;
                        });

                        return (
                          <details key={key} className="border border-gray-100 rounded">
                            <summary className="px-4 py-3 flex items-center justify-between cursor-pointer">
                              <div className="flex items-center gap-3">
                                <span className="font-medium text-gray-700">{labelMap[key]}</span>
                                <span className="text-xs text-gray-500">{count} candidates</span>
                              </div>
                              <ChevronDown className="text-gray-400" />
                            </summary>
                            <div className="px-4 pb-3">
                              {candidatesLoading ? (
                                <div className="py-4 text-center text-gray-500"><Loader2 className="animate-spin inline mr-2"/>Loading candidates...</div>
                              ) : candidatesForLevel.length === 0 ? (
                                <div className="p-4 text-sm text-gray-500">No candidates available for this stage.</div>
                              ) : (
                                <ul className="space-y-2">
                                  {candidatesForLevel.slice(0, 50).map((c, idx) => (
                                    <li key={idx} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                                      <div className="min-w-0">
                                        <div className="font-medium text-sm truncate">{c.name ?? c.full_name ?? c.profile_name ?? 'Unnamed candidate'}</div>
                                        <div className="text-xs text-gray-500">{c.email ?? c.profile_email ?? c.contact ?? ''}</div>
                                      </div>
                                      <div className="text-xs text-gray-500">{capitalize(String(c.current_round ?? c.currentRound ?? c.round ?? ''))}</div>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          </details>
                        );
                      })}
                    </div>
                  </div>
                )}
            </div>

            <div className="lg:col-span-4">
                <JobsSummaryCard jobs={sortedJobs} isLoading={isLoading} />

                {/* Most applied jobs */}
                <div className="mt-6 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-md font-semibold">Most Applied Jobs</h4>
                    <span className="text-xs text-gray-500">Top 5</span>
                  </div>
                  <div className="space-y-3">
                    {sortedJobs.slice().sort((a,b) => b.total_applications - a.total_applications).slice(0,5).map(j => (
                      <div key={j.job_id} className="flex items-center justify-between">
                        <div className="min-w-0 pr-3">
                          <div className="font-medium text-sm truncate">{j.job_title}</div>
                          <div className="text-xs text-gray-500">{j.is_active ? 'Active' : 'Inactive'} • {j.interview_rounds} rounds</div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">{j.total_applications}</div>
                          <button onClick={() => setSelectedJobId(j.job_id)} className="text-xs text-blue-600 hover:underline">Show</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Today's activity */}
                <div className="mt-6 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-md font-semibold">Today's Activity</h4>
                    <div className="text-xs text-gray-500 flex items-center gap-2"><Calendar size={14}/> {new Date().toLocaleDateString()}</div>
                  </div>
                  <TodaysActivityChart jobs={sortedJobs} candidates={jobCandidates} />
                </div>
            </div>
        </div>
      </div>
    </>
  );
}