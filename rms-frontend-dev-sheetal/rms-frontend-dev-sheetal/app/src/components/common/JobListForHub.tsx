// src/pages/ControlHub/components/JobListForHub.tsx
import { useEffect, useState, useCallback } from 'react';
import { Loader2, MapPin, Calendar, UploadCloud, ArrowRight } from 'lucide-react';
import { getAllJobPosts, getActiveJobPosts, getCandidateStatsForJob } from '../../api/jobApi';

// Define the structure for a JobPost
interface JobPost {
  job_id: string;
  job_title: string;
  job_location: string;
  work_from_home: boolean;
  posted_date?: string | null;
  shortlisted: number;
  rejected: number;
  under_review: number;
  applied?: number;
  is_active?: boolean;
}

interface JobListForHubProps {
  onJobSelect: (job: JobPost) => void;
}

const JobListForHub: React.FC<JobListForHubProps> = ({ onJobSelect }) => {
  const [jobs, setJobs] = useState<JobPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getAllJobPosts();
      let fetchedJobs: any[] = [];

      let allPayload: any[] = [];
      if (response.success) {
        allPayload = Array.isArray(response.data) ? response.data : (response.data?.jobs || response.data);
        if (Array.isArray(allPayload)) {
          fetchedJobs = allPayload;
        }
      }

      // Reconcile with active jobs endpoint so we reliably know which jobs are active
      try {
        const activeRes = await getActiveJobPosts();
        let activePayload: any[] = [];
        if (activeRes.success) {
          activePayload = Array.isArray(activeRes.data) ? activeRes.data : (activeRes.data?.jobs || activeRes.data);
          if (Array.isArray(activePayload)) {
            const activeIds = new Set(activePayload.map((j: any) => j.job_id ?? j.jobId ?? j.id));
            fetchedJobs = fetchedJobs.map(j => ({ ...j, is_active: activeIds.has(j.job_id) }));
          } else {
            fetchedJobs = fetchedJobs.map(j => ({ ...j, is_active: j.is_active ?? false }));
          }
        } else {
          fetchedJobs = fetchedJobs.map(j => ({ ...j, is_active: j.is_active ?? false }));
        }
      } catch (e) {
        console.error('Error reconciling active jobs for Control Hub:', e);
        fetchedJobs = fetchedJobs.map(j => ({ ...j, is_active: j.is_active ?? false }));
      }

      // Enrich each job with candidate stats (applied/shortlisted/rejected/under_review)
      try {
        const jobsWithStats = await Promise.all(fetchedJobs.map(async (j) => {
          try {
            const statsResp = await getCandidateStatsForJob(j.job_id);
            if (statsResp.success && statsResp.data && statsResp.data.data && statsResp.data.data.profile_counts) {
              const pc = statsResp.data.data.profile_counts;
              return {
                ...j,
                applied: pc.applied ?? j.applied ?? 0,
                shortlisted: pc.shortlisted ?? j.shortlisted ?? 0,
                rejected: pc.rejected ?? j.rejected ?? 0,
                under_review: pc.under_review ?? j.under_review ?? 0,
              };
            }
          } catch (e) {
            // ignore per-job stats errors and return original job
            console.debug('Failed to fetch candidate stats for job', j.job_id, e);
          }
          return {
            ...j,
            applied: j.applied ?? 0,
            shortlisted: j.shortlisted ?? 0,
            rejected: j.rejected ?? 0,
            under_review: j.under_review ?? 0,
          };
        }));
        setJobs(jobsWithStats);
      } catch (e) {
        console.error('Failed to enrich jobs with candidate stats', e);
      }
    } catch (err) {
                // Enrich each job with candidate stats (applied/shortlisted/rejected/under_review)
    } finally {
      setIsLoading(false);
    }
  }, []);

  // useEffect to fetch jobs on mount
  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <Loader2 size={48} className="text-[var(--color-primary-500)] animate-spin" />
        <p className="mt-4 text-gray-500">Loading job posts...</p>
      </div>
    );
  }

  // UPDATED: Grid layout changed to 3 columns on large screens
  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      
      {/* Filter for active jobs and map to new vertical card */}
      {jobs.filter(j => j.is_active === true).map((job) => (
        <div
          key={job.job_id}
          // UPDATED: Card is now flex-col
          className="flex flex-col rounded-2xl bg-white border border-gray-200 shadow-sm transition-all duration-300 transform hover:shadow-xl hover:border-gray-300"
          role="button"
          tabIndex={0}
        >
          {/* CARD BODY: Clicks here select the job.
            Added `flex-grow` to push the button to the bottom.
          */}
          <div 
            className="flex-grow p-6 cursor-pointer"
            onClick={() => onJobSelect(job)}
          >
            {/* Top Icon/Image */}
            <div className="w-14 h-14 mb-5 bg-blue-100 text-[var(--color-primary-500)] rounded-xl flex items-center justify-center">
              <UploadCloud size={28} />
            </div>

            {/* Job Title */}
            <h3 className="text-lg font-bold text-gray-900 mb-2 h-14 line-clamp-2">
              {job.job_title}
            </h3>
            
            {/* Metadata (Location & Date) */}
            <div className="flex items-center text-sm text-gray-500 mb-5 gap-4">
              <span className="flex items-center gap-1.5">
                <MapPin size={14} />
                {job.work_from_home ? 'Remote' : job.job_location}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar size={14} />
                {job.posted_date ? new Date(job.posted_date).toLocaleDateString() : 'N/A'}
              </span>
            </div>

            {/* Stats */}
            <div className="flex w-full justify-start items-center gap-4 pt-4 border-t border-gray-100">
              <div className="text-left">
                <div className="font-bold text-2xl text-[var(--color-primary-500)]">
                  {job.applied ?? ((job.shortlisted ?? 0) + (job.rejected ?? 0) + (job.under_review ?? 0))}
                </div>
                <div className="text-xs text-gray-500">Total Applied</div>
              </div>
              <div className="text-left">
                <div className="font-bold text-2xl text-green-600">
                  {job.shortlisted ?? 0}
                </div>
                <div className="text-xs text-gray-500">Shortlisted</div>
              </div>
            </div>
          </div>

          {/* CARD FOOTER: Contains the new "glitter" button.
            This area is separate from the main click handler.
          */}
          <div className="p-6 pt-0">
            {/* NEW: Glitter Button
              - `btn-glitter-wrapper` provides the overflow clipping and the `::before` pseudo-element.
              - `btn-glitter` is the button itself that gets the lift and background transitions.
            */}
            <div className="btn-glitter-wrapper">
              <button
                type="button"
                onClick={() => onJobSelect(job)}
                className="btn-glitter w-full h-12 flex items-center justify-center gap-2 rounded-xl bg-[var(--color-primary-500)] text-white font-semibold text-base shadow-lg"
              >
                <span>Upload Resumes</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default JobListForHub;