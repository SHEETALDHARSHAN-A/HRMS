// src/pages/Career/CareerPage.tsx

import { useEffect, useState, useMemo, useRef } from 'react';
import { Loader2, X, SortDesc, ChevronDown } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getActiveJobPosts } from "../../api/jobApi";
import { useToast } from '../../context/ModalContext';
import PublicLayout from "../../components/layout/PublicLayout"; 
import JobCard from "../../components/common/JobCard";
import JobDetailsModal from "../../components/common/JobDetailsModal";

// Export the type so JobCard can use it
export interface PublicJob {
  job_id: string;
  job_title: string;
  short_description: string;
  job_location: string;
  min_experience: number;
  max_experience: number;
  work_from_home: boolean;
  skills: string[];
  // Optional recommendation properties
  recommendationScore?: number;
  recommendationReasons?: string[];
}
 
const MOCK_PUBLIC_JOBS: PublicJob[] = [];
 
const CareerPage: React.FC = () => {
  const [jobs, setJobs] = useState<PublicJob[]>([]);
  const [allJobs, setAllJobs] = useState<any[]>([]); // Store full job data for modal
  const [isLoading, setIsLoading] = useState(true);
  const [sortBy, setSortBy] = useState<'latest' | 'oldest' | 'title_asc' | 'title_desc' | 'experience_low' | 'experience_high' | 'location_remote' | 'location_office' | 'skills_count'>('latest');
  const [isSortDropdownOpen, setSortDropdownOpen] = useState(false);
  const sortDropdownRef = useRef<HTMLDivElement>(null);
  
  // Modal states
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // --- UPDATED: Read new search params ---
  const [searchParams] = useSearchParams();
  const roleQuery = searchParams.get('role') || "";
  const skillsQuery = searchParams.get('skills') || "";
  const locationsQuery = searchParams.get('locations') || "";
  
  const { showToast } = useToast();
  const navigate = useNavigate();

  // Helper function for sort display names
  const getSortDisplayName = (sortValue: string) => {
    const sortNames: Record<string, string> = {
      'latest': 'Newest Jobs',
      'oldest': 'Oldest Jobs',
      'title_asc': 'Title A→Z',
      'title_desc': 'Title Z→A',
      'experience_low': 'Entry Level First',
      'experience_high': 'Senior Level First',
      'location_remote': 'Remote First',
      'location_office': 'Office First',
      'skills_count': 'Most Skills Required'
    };
    return sortNames[sortValue] || 'Latest';
  };
 
  // (fetchJobs logic remains the same)
  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const response = await getActiveJobPosts();
      let fetchedJobs: PublicJob[] = [];

      // Handle the API response shape correctly
      if (response.success) {
        const jobsPayload = Array.isArray(response.data)
          ? response.data
          : response.data?.jobs || response.data;

        if (Array.isArray(jobsPayload)) {
          // Store full job data for modal
          setAllJobs(jobsPayload);
          
          fetchedJobs = jobsPayload.map((job: any) => ({
            job_id: job.job_id,
            job_title: job.job_title,
            short_description: job.short_description || (job.job_description ? job.job_description.substring(0, 150) + '...' : 'No description available.'),
            job_location: job.job_location || 'Remote',
            min_experience: job.minimum_experience,
            max_experience: job.maximum_experience,
            work_from_home: job.work_from_home,
            skills: job.skills || job.skills_required?.map((s: any) => s.skill || s.name) || [],
          }));
        }
        setJobs(fetchedJobs.length > 0 ? fetchedJobs : MOCK_PUBLIC_JOBS);
      } else {
        setJobs(MOCK_PUBLIC_JOBS);
      }
    } catch (error) {
      console.error('Failed to fetch career jobs:', error);
      setJobs(MOCK_PUBLIC_JOBS);
      showToast('Failed to load job posts. Please try again later.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Modal handlers
  const handleJobCardClick = (jobId: string) => {
    const fullJobData = allJobs.find(job => job.job_id === jobId);
    if (fullJobData) {
      console.log('Full job data for modal:', fullJobData); // Debug log

      // Normalize skills into `skills_required` to match JobDetailsModal expectations.
      const skillsFromPayload = fullJobData.skills || fullJobData.skills_required || fullJobData.skills_required?.map((s: any) => s.skill || s.name) || [];

      // Normalize posted date - fallback to created_at or now
      const postedDate = fullJobData.posted_date || fullJobData.posted_at || fullJobData.created_at || new Date().toISOString();

      const normalizedJob = {
        ...fullJobData,
        skills_required: Array.isArray(skillsFromPayload)
          ? skillsFromPayload.map((s: any) => {
              // Keep objects as-is; convert simple strings into strings
              if (typeof s === 'string') return s;
              if (s == null) return '';
              // Try to standardize object shape
              return s.skill_name || s.skill || s.name || JSON.stringify(s);
            })
          : [],
        posted_date: postedDate,
      };

      setSelectedJob(normalizedJob);
      setIsModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedJob(null);
  };
 
  // (useEffect for fetching and refreshing remains the same)
  useEffect(() => {
    fetchJobs();
    const onCustom = () => { fetchJobs(); };
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'career_jobs_refresh') { fetchJobs(); }
    };
    window.addEventListener('career_jobs_refresh', onCustom as EventListener);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('career_jobs_refresh', onCustom as EventListener);
      window.removeEventListener('storage', onStorage);
    };
  }, []); //

  // Handle click outside to close sort dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sortDropdownRef.current && !sortDropdownRef.current.contains(event.target as Node)) {
        setSortDropdownOpen(false);
      }
    };

    if (isSortDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isSortDropdownOpen]);
 
  // A boolean to know if a search is active
  const isSearchActive = !!(roleQuery || skillsQuery || locationsQuery);

  // NOTE: Recommended jobs removed by request — previous recommendation logic was here.

  // Enhanced sorting logic with 10 comprehensive options
  const sortedJobs = useMemo(() => {
    const jobsToSort = [...jobs];
    
    switch (sortBy) {
      case 'latest':
        // Default: newest jobs first (assume API returns in chronological order)
        return jobsToSort;
        
      case 'oldest':
        // Oldest jobs first - reverse the default order
        return jobsToSort.reverse();
        
      // 'relevance' removed — fallback handled by other sort options
        
      case 'title_asc':
        // Alphabetical order A→Z
        return jobsToSort.sort((a, b) => a.job_title.localeCompare(b.job_title));
        
      case 'title_desc':
        // Reverse alphabetical order Z→A
        return jobsToSort.sort((a, b) => b.job_title.localeCompare(a.job_title));
        
      case 'experience_low':
        // Entry level first (lowest experience requirements)
        return jobsToSort.sort((a, b) => a.min_experience - b.min_experience);
        
      case 'experience_high':
        // Senior level first (highest experience requirements)
        return jobsToSort.sort((a, b) => b.min_experience - a.min_experience);
        
      case 'location_remote':
        // Remote jobs first
        return jobsToSort.sort((a, b) => {
          if (a.work_from_home && !b.work_from_home) return -1;
          if (!a.work_from_home && b.work_from_home) return 1;
          return 0;
        });
        
      case 'location_office':
        // Office jobs first
        return jobsToSort.sort((a, b) => {
          if (!a.work_from_home && b.work_from_home) return -1;
          if (a.work_from_home && !b.work_from_home) return 1;
          return 0;
        });
        
      case 'skills_count':
        // Most skills required first (complex roles)
        return jobsToSort.sort((a, b) => (b.skills?.length || 0) - (a.skills?.length || 0));
        
      default:
        return jobsToSort;
    }
  }, [jobs, sortBy]);

  // Filtered jobs logic - simplified without panel filters
  const filteredJobs = useMemo(() => {
    let jobsToFilter = isSearchActive ? jobs : sortedJobs;
    
    // Apply search filters if active
    if (isSearchActive) {
      // Prepare filter arrays from comma-separated query strings
      const roleSearch = roleQuery.toLowerCase().trim();
      const skillList = skillsQuery.toLowerCase().split(',')
        .map(s => s.trim()).filter(Boolean); // e.g., [react, python]
      const locationList = locationsQuery.toLowerCase().split(',')
        .map(l => l.trim()).filter(Boolean); // e.g., [london, remote]

      jobsToFilter = jobsToFilter.filter(job => {
        // 1. Check Role
        const roleMatch = !roleSearch || 
          job.job_title.toLowerCase().includes(roleSearch);

        // 2. Check Skills (Matches if job has AT LEAST ONE of the skills)
        const skillsMatch = skillList.length === 0 || 
          skillList.some(skill => 
            job.skills.some(jobSkill => jobSkill.toLowerCase().includes(skill))
          );
          
        // 3. Check Locations (Matches if job location is IN the list)
        const jobLocation = job.job_location.toLowerCase();
        const locationsMatch = locationList.length === 0 || 
          locationList.some(loc => 
            jobLocation.includes(loc) || 
            (loc === 'remote' && job.work_from_home)
          );

        // Job must match all three criteria
        return roleMatch && skillsMatch && locationsMatch;
      });
    }
    
    return jobsToFilter;
  }, [jobs, sortedJobs, isSearchActive, roleQuery, skillsQuery, locationsQuery]);
  
  // --- NEW: Helper to build the "results for" text ---
  const renderSearchQueryText = () => {
    const parts = [];
    if (roleQuery) parts.push(<strong key="r" className="text-[var(--color-primary-500)]">"{roleQuery}"</strong>);
    if (skillsQuery) parts.push(<span key="s">skills <strong className="text-[var(--color-primary-500)]">"{skillsQuery}"</strong></span>);
    if (locationsQuery) parts.push(<span key="l">locations <strong className="text-[var(--color-primary-500)]">"{locationsQuery}"</strong></span>);

    if (parts.length === 0) return null;
    
    // This joins them with commas and "and"
    return parts.reduce((prev, curr, i) => {
      if (i === 0) return [curr];
      if (i === parts.length - 1) return [...prev, " and ", curr];
      return [...prev, ", ", curr];
    }, [] as React.ReactNode[]);
  };
 
  return (
    <PublicLayout
        bannerTitle="Current Career Opportunities"
        bannerSubtitle="Find your next role with PRAYAG.AI"
        showHeroContent={true} 
    >
      <style>{`
        @keyframes fadeIn { 
          from { opacity: 0; transform: translateY(10px); } 
          to { opacity: 1; transform: translateY(0); } 
        }
        .animate-fade-in { 
          animation: fadeIn 0.5s ease-out forwards; 
          opacity: 0; 
        }
      `}</style>

      <div className="w-full">
        {/* Recommended jobs removed per request */}

        {isLoading ? (
          <div className="col-span-full flex justify-center items-center h-96">
            <Loader2 size={32} className="animate-spin text-[var(--color-primary-500)]" />
            <p className="ml-3 text-lg font-medium text-gray-600 dark:text-gray-300">Loading open roles...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center p-10 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 shadow-xl mt-6 animate-fade-in">
            <p className="text-xl font-semibold text-gray-700 dark:text-gray-200">No current job openings.</p>
            <p className="text-gray-500 dark:text-gray-400 mt-2">Please check back soon or connect with us on LinkedIn!</p>
          </div>
        ) : filteredJobs.length === 0 && isSearchActive ? ( // Case for "No results found"
          <div className="text-center p-10 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-800 shadow-xl mt-6 animate-fade-in">
            <p className="text-xl font-semibold text-gray-700 dark:text-gray-200">No jobs match your search</p>
            <p className="text-gray-500 dark:text-gray-400 mt-2">Try adjusting your search query or view all open roles.</p>
            <button
              onClick={() => navigate('/career-page')} // Clear search
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-white dark:bg-gray-700 px-3.5 py-2 text-sm font-semibold text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              <X size={16} />
              Clear Search
            </button>
          </div>
        ) : (
          <div className="w-full flex flex-col gap-6">


            {/* Professional Controls Section */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                
                {/* Search results header or job count */}
                {isSearchActive ? (
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                      Search Results
                    </h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Found {filteredJobs.length} matching opportunities for: {renderSearchQueryText()}
                    </p>
                  </div>
                ) : (
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Careers</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{filteredJobs.length} opportunities available</p>
                  </div>
                )}

                {/* Controls */}
                <div className="flex items-center gap-3">
                  {isSearchActive && (
                    <button
                      onClick={() => navigate('/career-page')}
                      className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 rounded-md transition-colors duration-200"
                    >
                      <X size={16} />
                      Clear Search
                    </button>
                  )}

                  {/* Premium Sort Dropdown - Always visible */}
                  <div className="relative" ref={sortDropdownRef}>
                    <button
                      onClick={() => setSortDropdownOpen(!isSortDropdownOpen)}
                      className="inline-flex items-center gap-3 px-4 py-2 rounded-md bg-white border border-gray-200 text-sm text-gray-700 hover:shadow-sm transition-shadow duration-150 min-w-[220px]"
                      aria-haspopup="true"
                      aria-expanded={isSortDropdownOpen}
                    >
                      <div className="flex-shrink-0 w-8 h-8 rounded-md bg-blue-50 flex items-center justify-center">
                        <SortDesc size={16} className="text-blue-600" />
                      </div>

                      <div className="flex-1 text-left">
                        <div className="text-xs text-gray-500 uppercase tracking-wide">Sort Jobs By</div>
                        <div className="text-sm font-semibold text-gray-900">{getSortDisplayName(sortBy)}</div>
                      </div>

                      <div className="flex-shrink-0">
                        <ChevronDown size={16} className={`text-gray-400 transition-transform duration-200 ${isSortDropdownOpen ? 'rotate-180' : ''}`} />
                      </div>
                    </button>

                    {/* Premium Dropdown Menu */}
                    {isSortDropdownOpen && (
                      <div className="absolute top-full left-0 mt-2 w-full min-w-[220px] bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200/80 dark:border-gray-700/80 z-50 overflow-hidden">
                        {/* Dropdown Header */}
                        <div className="px-3 py-2 border-b border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800">
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200">Sort Options</h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Choose how to organize job listings</p>
                            </div>
                          </div>
                        </div>

                        {/* Sort Options */}
                        <div className="py-1 max-h-64 overflow-y-auto">
                          {[
                            { value: 'latest', label: 'Newest Jobs', icon: '🕒', desc: 'Most recently posted first' },
                            { value: 'oldest', label: 'Oldest Jobs', icon: '📅', desc: 'Oldest postings first' },
                            { value: 'title_asc', label: 'Title A→Z', icon: '🔤', desc: 'Alphabetical order' },
                            { value: 'title_desc', label: 'Title Z→A', icon: '🔡', desc: 'Reverse alphabetical' },
                            { value: 'experience_low', label: 'Entry Level First', icon: '🌱', desc: 'Junior positions first' },
                            { value: 'experience_high', label: 'Senior Level First', icon: '🎯', desc: 'Senior positions first' },
                            { value: 'location_remote', label: 'Remote First', icon: '🏠', desc: 'Work from home options' },
                            { value: 'location_office', label: 'Office First', icon: '🏢', desc: 'On-site positions first' },
                            { value: 'skills_count', label: 'Most Skills Required', icon: '🛠️', desc: 'Complex roles first' }
                          ].map((option) => (
                            <button
                              key={option.value}
                              onClick={() => {
                                setSortBy(option.value as any);
                                setSortDropdownOpen(false);
                              }}
                              className={`w-full px-3 py-2 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700/60 transition-colors duration-150 ${
                                sortBy === option.value 
                                  ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' 
                                  : ''
                              }`}
                            >
                              <div className="flex-shrink-0 w-8 h-8 rounded-md bg-blue-50 flex items-center justify-center text-sm">
                                <span className="text-blue-600">{option.icon}</span>
                              </div>

                              <div className="flex-1 text-left">
                                <div className="flex items-center justify-between">
                                  <span className={`font-medium ${sortBy === option.value ? 'text-blue-700 dark:text-blue-300' : 'text-gray-800 dark:text-gray-200'}`}>
                                    {option.label}
                                  </span>
                                  {sortBy === option.value && (
                                    <span className="text-xs text-blue-600 font-semibold">Selected</span>
                                  )}
                                </div>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                  {option.desc}
                                </p>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Job List */}
            <div className="space-y-4">
              {filteredJobs.map((job, index) => (
                <JobCard 
                  key={job.job_id} 
                  job={job}
                  style={{ animationDelay: `${index * 75}ms` }}
                  className="animate-fade-in" 
                  onCardClick={() => handleJobCardClick(job.job_id)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Job Details Modal */}
      <JobDetailsModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        job={selectedJob}
      />
    </PublicLayout>
  );
};
 
export default CareerPage;