import { FilePenLine, Trash2, Loader2, RefreshCw, Plus, X, MapPin, Calendar, Menu, LayoutDashboard, Briefcase, FileText, BarChart, MessageCircle, Users, Headset, CheckSquare, ChevronDown, Check, Info, Pin, View, Combine } from "lucide-react"; 
import { useUser } from "../../context/UserContext";
import Button from "../../components/common/Button";
import { NavLink } from "react-router-dom";
import { useEffect, useState, useCallback, useMemo } from "react";
import { getAllJobPosts, getActiveJobPosts, toggleJobStatus, deleteJobPost, getCandidateStatsForJob, getMyJobPosts, getAllJobPostsAdmin } from "../../api/jobApi";
import { useToast, useModal } from "../../context/ModalContext";
import { useLocation } from "react-router-dom";
import clsx from "clsx"; 

interface JobPostsListProps {
  onAddNewJob: () => void;
  onEditJob: (jobId: string) => void;
  activeTab: 'my_jobs' | 'all_jobs'; 
}

interface SkillRequired {
  skill: string;
  weightage: number;
}

// Interview type values supported by the API
type InterviewType = "agent" | "offline" | "hybrid";

interface JobPost {
  job_id: string;
  job_title: string;
  job_description: string;
  job_location: string;
  minimum_experience: number;
  maximum_experience: number;
  skills_required: SkillRequired[];
  interview_rounds?: any[];
  interview_levels?: string[]; 
  interview_type?: InterviewType;
  work_from_home: boolean;
  role_fit: number;
  potential: number;
  location_score: number;
  is_active: boolean;
  is_pinned?: boolean;
  created_by_user_id?: string;
  owner_name?: string;
  owner_first_name?: string;
  owner_last_name?: string;
  owner_email?: string;
  creator?: {
    user_id?: string;
    first_name?: string;
    last_name?: string;
    email?: string;
    full_name?: string;
  };
  key_functionality?: { type: string; description: string }[];

  shortlisted: number;
  rejected: number;
  under_review: number;
  profile_counts?: {
    applied?: number;
    shortlisted?: number;
    rejected?: number;
    under_review?: number;
  };
  shortlisting_criteria?: number;
  rejecting_criteria?: number;
  posted_date?: string | null;
}

// Map interview type to the appropriate icon
const InterviewTypeIcon = ({ type }: { type?: InterviewType }) => {
  switch (type) {
    case 'agent':
      return <Headset size={16} className="text-gray-500" />;
    case 'offline':
      return <Users size={16} className="text-gray-500" />;
    case 'hybrid':
      return <Combine size={16} className="text-gray-500" />;
    default:
      return <Headset size={16} className="text-gray-500" />;
  }
};

// Utility to resolve the ID from the user object
const resolveUserId = (entity: any): string | undefined => {
  if (!entity) return undefined;

  return (
    entity.user_id ??
    entity.userId ??
    entity.id ??
    entity.userID ??
    (typeof entity === "object" && entity !== null ? undefined : String(entity))
  );
};

const firstNonEmptyString = (...values: unknown[]): string | undefined => {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
};

const resolveUserDisplayName = (entity: any): string | undefined => {
  if (!entity) return undefined;
  if (typeof entity === "string") return entity.trim() || undefined;

  const combinedName = entity.first_name || entity.last_name
    ? `${entity.first_name ?? ""} ${entity.last_name ?? ""}`.trim()
    : undefined;

  const directMatch = firstNonEmptyString(
    combinedName,
    entity.full_name,
    entity.fullName,
    entity.name,
    entity.display_name,
    entity.displayName,
    entity.username,
    entity.email
  );

  if (directMatch) {
    return directMatch;
  }

  if (entity.profile) {
    const profileName = resolveUserDisplayName(entity.profile);
    if (profileName) return profileName;
  }

  if (entity.user) {
    const userName = resolveUserDisplayName(entity.user);
    if (userName) return userName;
  }

  return undefined;
};

const getJobCreatorId = (job: any): string | undefined => {
  if (!job) return undefined;
  const creatorId = (
    job.created_by_user_id ??
    job.createdByUserId ??
    job.user_id ??
    job.userId ??
    job.author_id ??
    job.creator_id ??
    (job.creator ? resolveUserId(job.creator) : undefined)
  );
  return creatorId ? String(creatorId) : undefined;
};

// Normalize values so they can be compared safely as IDs
const normalizeId = (value: unknown): string =>
  value === null || value === undefined ? "" : String(value).toLowerCase().replace(/[^a-z0-9]/g, "");


// --- COMPONENT START ---
export default function JobPostsList({ onAddNewJob, onEditJob, activeTab }: JobPostsListProps) {
  const { user } = useUser();

  const currentUserIdNormalized = useMemo(() => {
    let rawId: string | undefined = resolveUserId(user);

    if (!rawId || String(rawId).toLowerCase().includes("object")) {
      try {
        rawId = localStorage.getItem("user_id") ?? undefined;
      } catch (error) {
        console.error("Failed to retrieve ID from user_id key.", error);
      }
    }

    return normalizeId(rawId);
  }, [user]);

  console.log("[JOBS_LIST] FINAL User ID for comparison:", currentUserIdNormalized);

  const userRole = user?.role;
  const isSuperAdmin = userRole === "SUPER_ADMIN" || (Array.isArray(userRole) && userRole.includes("SUPER_ADMIN"));

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [expandedJob, setExpandedJob] = useState<JobPost | null>(null);

  const ALL_ADMIN_ROLES = ["ADMIN", "SUPER_ADMIN"];
  const ALL_ROLES = [...ALL_ADMIN_ROLES, "CANDIDATE"];

  const navItems = [
    { label: "Dashboard", Icon: LayoutDashboard, path: "/dashboard", roles: ALL_ADMIN_ROLES },
    { label: "Job Posts", Icon: Briefcase, path: "/jobs", roles: ALL_ADMIN_ROLES },
    { label: "Career Page", Icon: FileText, path: "/career-page", roles: ALL_ROLES },
    { label: "Job Recruitment", Icon: BarChart, path: "/job-recruitment", roles: ALL_ADMIN_ROLES },
    { label: "Interview Results", Icon: MessageCircle, path: "/interview-results", roles: ALL_ADMIN_ROLES },
    { label: "Onboarding", Icon: Users, path: "/onboarding", roles: ALL_ADMIN_ROLES },
    { label: "Interview Agent", Icon: Headset, path: "/interview-agent", roles: ALL_ADMIN_ROLES },
  ];

  const filteredNavItems = navItems.filter(item => {
    if (!userRole) return false;
    const rolesToCheck = Array.isArray(userRole) ? userRole : [userRole];
    if (rolesToCheck.includes("SUPER_ADMIN")) return true;
    return rolesToCheck.some(role => item.roles.includes(role));
  });
  const [jobs, setJobs] = useState<JobPost[]>([]);
  const [pinnedIds, setPinnedIds] = useState<Record<string, boolean>>({});
  const [pinnedPulseIds, setPinnedPulseIds] = useState<Record<string, boolean>>({});
  const [selectedIds, setSelectedIds] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [topSelectMenuOpen, setTopSelectMenuOpen] = useState(false);
  const [bottomSelectMenuOpen, setBottomSelectMenuOpen] = useState(false);
  const selectedCount = Object.values(selectedIds).filter(Boolean).length;
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { showToast } = useToast();
  const { showConfirm, setModalProcessing } = useModal(); 
  const [pendingToggles, setPendingToggles] = useState<Record<string, boolean>>({});
  const location = useLocation();
  const [jobStats, setJobStats] = useState<Record<string, any>>({});
  const viewingOthersTab = activeTab === "all_jobs";
  const [showQuickGuide, setShowQuickGuide] = useState(false);
  
  useEffect(() => {
    async function fetchStats() {
      if (jobs.length === 0) return;
      const statsMap: Record<string, any> = {};
      await Promise.all(jobs.map(async (job) => {
        const rawCounts = job.profile_counts ?? (job as any).profileCounts ?? null;
        if (rawCounts) {
          statsMap[job.job_id] = {
            total_applied: rawCounts.applied ?? 0,
            total_selected: rawCounts.shortlisted ?? 0,
            total_rejected: rawCounts.rejected ?? 0,
            total_under_review: rawCounts.under_review ?? 0,
          };
          return;
        }

        const res = await getCandidateStatsForJob(job.job_id);
        if (res.success && res.data?.data?.profile_counts) {
          const rc = res.data.data.profile_counts;
          statsMap[job.job_id] = {
            total_applied: rc.applied ?? 0,
            total_selected: rc.shortlisted ?? 0,
            total_rejected: rc.rejected ?? 0,
            total_under_review: rc.under_review ?? 0,
          };
        } else {
          statsMap[job.job_id] = { total_applied: 0, total_selected: 0, total_rejected: 0, total_under_review: 0 };
        }
      }));
      setJobStats(statsMap);
    }
    fetchStats();
  }, [jobs]);

  const mapFetchedJob = (job: any): JobPost => {

    const src = job?.data?.job_details ?? job?.data ?? job?.job_details ?? job?.job ?? job;

    const jobId = src.job_id ?? src.jobId ?? src.id ?? "";
    const rawActive = src.is_active ?? src.isActive ?? src.active ?? src.enabled;
    const isActive =
      rawActive === undefined || rawActive === null
        ? undefined
        : typeof rawActive === "boolean"
          ? rawActive
          : typeof rawActive === "string"
            ? rawActive.toLowerCase() === "true"
            : Boolean(rawActive);

    const skillsRequired = Array.isArray(src.skills_required)
      ? src.skills_required.map((s: any) => ({
        skill: s.skill ?? s.name,
        weightage: s.weightage ?? s.weight ?? 5
      }))
      : [];

    const profileCounts = src.profile_counts ?? src.profileCounts ?? job.profile_counts ?? job.profileCounts ?? null;

    const rawCreator = src.creator
      ?? src.created_by_user
      ?? src.createdByUser
      ?? src.created_by
      ?? src.createdBy
      ?? src.owner
      ?? src.owner_details
      ?? src.ownerDetails
      ?? job.creator
      ?? job.created_by_user
      ?? job.owner
      ?? null;

    const creatorCandidateName = rawCreator ? resolveUserDisplayName(rawCreator) : undefined;

    const normalizedCreator = rawCreator
      ? {
          user_id: resolveUserId(rawCreator)
            ?? rawCreator.user_id
            ?? rawCreator.userId
            ?? rawCreator.id
            ?? src.created_by_user_id
            ?? src.user_id
            ?? src.author_id
            ?? job.created_by_user_id,
          first_name: rawCreator.first_name ?? rawCreator.firstName,
          last_name: rawCreator.last_name ?? rawCreator.lastName,
          email: rawCreator.email ?? rawCreator.emailAddress ?? rawCreator.contact_email,
          full_name: rawCreator.full_name ?? rawCreator.fullName ?? rawCreator.name ?? creatorCandidateName,
        }
      : undefined;

    const stringCandidates = [
      src.owner_name,
      src.ownerName,
      src.created_by_user_name,
      src.createdByUserName,
      src.created_by_name,
      src.createdByName,
      src.creator_name,
      src.creatorName,
      src.creatorFullName,
      job.owner_name,
      job.creator_name,
      job.user_name,
      normalizedCreator?.full_name,
      creatorCandidateName,
    ];

    const ownerName = firstNonEmptyString(...stringCandidates);

    return {
      ...src,
      job_id: jobId,
      created_by_user_id: src.created_by_user_id ?? src.user_id ?? src.author_id ?? normalizedCreator?.user_id ?? undefined,
      owner_name: ownerName,
      owner_first_name: normalizedCreator?.first_name,
      owner_last_name: normalizedCreator?.last_name,
      owner_email: normalizedCreator?.email,
      creator: normalizedCreator,
      // Keep a full rounds payload for the modal and a lightweight string list for compact display
      interview_rounds: src.interview_rounds ?? src.interview_levels ?? [],
      interview_levels: (src.interview_rounds ?? src.interview_levels ?? []).map((r: any) => (r?.level_name || r?.title || String(r))) ,
  interview_type: src.interview_type ?? "agent",
  shortlisting_criteria: src.shortlisting_criteria ?? src.shortlistingCriteria ?? 0,
  rejecting_criteria: src.rejecting_criteria ?? src.rejectingCriteria ?? 0,
  shortlisted: profileCounts?.shortlisted ?? src.shortlisted ?? src.shortlisted_count ?? 0,
  rejected: profileCounts?.rejected ?? src.rejected ?? src.rejected_count ?? 0,
  under_review: profileCounts?.under_review ?? src.under_review ?? src.underReview ?? 0,
  skills_required: skillsRequired,
  is_active: isActive as any,
  minimum_experience: src.minimum_experience ?? src.min_experience ?? 0,
  maximum_experience: src.maximum_experience ?? src.max_experience ?? 0,
  job_location: src.job_location ?? 'Not specified',
  work_from_home: src.work_from_home ?? false,
  role_fit: src.role_fit ?? 0,
  potential: src.potential_fit ?? src.potential ?? 0,
  location_score: src.location_fit ?? src.location_score ?? 0,
  posted_date: src.posted_date ?? src.postedDate ?? src.postedAt ?? null,
    };
  };

  const fetchJobs = useCallback(async () => {
    console.log(`[JOBS_LIST] Starting fetch for tab: ${activeTab}. User ID: ${currentUserIdNormalized}`); // <- ADDED LOG
    setRefreshing(true);
    try {
      // Use different endpoints based on active tab
      const response = activeTab === 'my_jobs' 
        ? await getMyJobPosts()
        : await getAllJobPostsAdmin();
        
      console.debug('[debug] Job posts response for tab', activeTab, response);
      let fetchedJobs: JobPost[] = [];

      if (response.success) {
        const data = response.data;
        const allPayload = Array.isArray(data) ? data : (data?.jobs || data?.job_details || data);

        console.log('[JOBS_LIST] Raw payload received from API:', allPayload); // <- ADDED LOG
      
        if (Array.isArray(allPayload)) {
          fetchedJobs = allPayload.map(mapFetchedJob);
        } else if (allPayload) {
          const single = mapFetchedJob(allPayload);
          fetchedJobs = [single];
        }
      } else {
        console.warn('Failed to fetch jobs for tab', activeTab, ':', response.error);
        // keep fetchedJobs empty on error; optional: showToast(response.error, 'error');
        console.warn('getAllJobPosts failed', (response as any).error);
      }

      try {
        const activeRes = await getActiveJobPosts();
        console.debug('[debug] getActiveJobPosts response', activeRes);

        if (activeRes.success) {
          const rawActivePayload = Array.isArray(activeRes.data)
            ? activeRes.data
            : (activeRes.data?.jobs || activeRes.data);

          const activePayload = Array.isArray(rawActivePayload) ? rawActivePayload : [];
          const activeIds = new Set(activePayload.map((j: any) => j.job_id ?? j.jobId ?? j.id));

          fetchedJobs = fetchedJobs.map(j => ({
            ...j,
            is_active: activeIds.has(j.job_id) ? true : (j.is_active ?? false)
          }));
        } else {
          fetchedJobs = fetchedJobs.map(j => ({ ...j, is_active: j.is_active ?? false }));
        }
      } catch (e) {
        console.error("Error reconciling active jobs:", e);
        fetchedJobs = fetchedJobs.map(j => ({ ...j, is_active: j.is_active ?? false }));
      }

      console.log(`[JOBS_LIST] Total jobs after mapping/reconciling: ${fetchedJobs.length}`); // <- ADDED LOG

      if (fetchedJobs.length === 0) {
        setJobs([]); 
      } else {
        setJobs(fetchedJobs);
      }

    } catch (err: any) {
      console.error('Failed to fetch jobs:', err);
      setJobs([]);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
      console.log('[JOBS_LIST] Job fetch complete. Final isLoading: false.'); // <- ADDED LOG
    }
  }, [activeTab, showToast]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // DEBUG: expose sample raw payloads to help diagnose missing fields
  useEffect(() => {
    if (!jobs || jobs.length === 0) return;
    try {
      console.debug('[JobPostsList] sample job raw payload:', jobs[0]);
    } catch (e) {
      // ignore
    }
  }, [jobs]);

  useEffect(() => {
    const routePaths = ["/jobs", "/jobs/"];
    if (routePaths.includes(location.pathname) && !isLoading && jobs.length === 0) {
      fetchJobs();
    }
  }, [location.pathname, fetchJobs]);

  useEffect(() => {
    const onVisibility = () => {
      const routePaths = ["/jobs", "/jobs/"];
      if (!document.hidden && routePaths.includes(location.pathname)) {
        fetchJobs();
      }
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [location.pathname, fetchJobs]);

  // Listen for job refresh events from form submissions
  useEffect(() => {
    const onJobRefresh = () => {
      console.debug('[JobPostsList] Received career_jobs_refresh event, refreshing...');
      fetchJobs();
    };
    const onStorage = (e: StorageEvent) => {
      if (e.key === 'career_jobs_refresh') {
        console.debug('[JobPostsList] Received storage event for career_jobs_refresh, refreshing...');
        fetchJobs();
      }
    };
    
    try {
      window.addEventListener('career_jobs_refresh', onJobRefresh as EventListener);
      window.addEventListener('storage', onStorage as EventListener);
    } catch (e) {
      console.warn('[JobPostsList] Failed to add event listeners:', e);
    }
    
    return () => {
      try {
        window.removeEventListener('career_jobs_refresh', onJobRefresh as EventListener);
        window.removeEventListener('storage', onStorage as EventListener);
      } catch (e) {
        console.warn('[JobPostsList] Failed to remove event listeners:', e);
      }
    };
  }, [fetchJobs]);


  const handleDelete = async (jobId: string, jobTitle: string) => {

    const confirmed = await showConfirm({
      title: "Confirm Deletion",
      message: `Are you sure you want to permanently delete the job post for "${jobTitle}"? This action cannot be undone and will affect associated candidate data.`,
      confirmText: "Delete",
      isDestructive: true,
    });

    if (!confirmed) {
      return;
    }

    try {
      setModalProcessing(true); 
      setJobs(prevJobs => prevJobs.map(j => j.job_id === jobId ? { ...j, is_deleting: true } as JobPost & { is_deleting?: boolean } : j));

      const response = await deleteJobPost(jobId);

      if (response.success) {
        setJobs(prevJobs => prevJobs.filter(job => job.job_id !== jobId));
      } else {
        showToast(response.error || `Failed to delete job post: ${jobTitle}.`, "error");
        setJobs(prevJobs => prevJobs.map(j => j.job_id === jobId ? { ...j, is_deleting: false } as JobPost & { is_deleting?: boolean } : j));
      }
    } catch (err: any) {
      showToast(`Error deleting job post: ${err.message || 'An unknown error occurred'}`, "error");
      setJobs(prevJobs => prevJobs.map(j => j.job_id === jobId ? { ...j, is_deleting: false } as JobPost & { is_deleting?: boolean } : j));
    } finally {
      setModalProcessing(false); 
    }
  };

  const toggleSelect = (jobId: string, checked: boolean) => {
    if (viewingOthersTab && !isSuperAdmin) return;
    setSelectedIds(s => ({ ...s, [jobId]: checked }));
  };

  const clearSelection = () => setSelectedIds({});

  const selectAll = () => {
    if (viewingOthersTab && !isSuperAdmin) return;
    const all = displayedJobs.reduce((acc, j) => {
      const creatorId = getJobCreatorId(j);
      const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
      const canDelete = isAuthor || isSuperAdmin;
      if (canDelete && !(j as any).is_deleting) acc[j.job_id] = true;
      return acc;
    }, {} as Record<string, boolean>);
    setSelectedIds(all);
  };

  const invertSelection = () => {
    if (viewingOthersTab && !isSuperAdmin) return;
    const inverted = displayedJobs.reduce((acc, j) => {
      const creatorId = getJobCreatorId(j);
      const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
      const canDelete = isAuthor || isSuperAdmin;
      if (!canDelete || (j as any).is_deleting) {
        acc[j.job_id] = !!selectedIds[j.job_id];
      } else {
        acc[j.job_id] = !selectedIds[j.job_id];
      }
      return acc;
    }, {} as Record<string, boolean>);
    setSelectedIds(inverted);
  };

  useEffect(() => {
    if (selectedCount === 0) {
      setTopSelectMenuOpen(false);
      setBottomSelectMenuOpen(false);
    }
  }, [selectedCount]);

  const handleDeleteSelected = async () => {
    if (viewingOthersTab && !isSuperAdmin) {
      showToast('You do not have permission to delete jobs in this view.', 'info');
      return;
    }
    const allIds = Object.keys(selectedIds).filter(id => selectedIds[id]);
    if (allIds.length === 0) {
      showToast('No jobs selected for deletion', 'info');
      return;
    }

    const jobsById = new Map(jobs.map(j => [j.job_id, j]));
    const idsToDelete = allIds.filter(id => {
      const job = jobsById.get(id);
      if (!job) return false;
      const creatorId = getJobCreatorId(job);
      const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
      return isAuthor || isSuperAdmin;
    });

    const cantDeleteCount = allIds.length - idsToDelete.length;

    if (cantDeleteCount > 0) {
      showToast(`You do not have permission to delete ${cantDeleteCount} selected job(s).`, 'info');
    }

    if (idsToDelete.length === 0) {
      showToast('No jobs selected that you can delete.', 'info');
      return;
    }

    const confirmed = await showConfirm({
      title: 'Delete Selected',
      message: `Are you sure you want to permanently delete ${idsToDelete.length} selected job(s)? This cannot be undone.`,
      confirmText: 'Delete',
      isDestructive: true,
    });

    if (!confirmed) return;

    try {
      setModalProcessing(true);
      setBulkProcessing(true);
      setJobs(prev => prev.filter(j => !idsToDelete.includes(j.job_id)));
      const { deleteJobPostsBatch } = await import('../../api/jobApi');
      const res = await deleteJobPostsBatch(idsToDelete);
      if (res.success) {
        clearSelection();
      } else {
        showToast(res.error || 'Failed to delete selected jobs', 'error');
        fetchJobs();
      }
    } catch (err: any) {
      showToast(err.message || 'Error deleting selected jobs', 'error');
      fetchJobs();
    } finally {
      setModalProcessing(false);
      setBulkProcessing(false);
    }
  };

  const handleToggleStatus = async (jobId: string, isActive: boolean) => {
    if (pendingToggles[jobId]) return;
    const newStatus = !isActive;

    setPendingToggles(p => ({ ...p, [jobId]: true }));
    setJobs(prev => prev.map(j => (j.job_id === jobId ? { ...j, is_active: newStatus } : j)));

    try {
      const response = await toggleJobStatus(jobId, newStatus);

      if (response.success && response.data?.data?.job_details) {
        const updated = response.data.data.job_details;
        setJobs(prev => prev.map(j => (j.job_id === updated.job_id ? { ...j, ...updated, is_active: updated.is_active } : j)));
        try {
          window.localStorage.setItem('career_jobs_refresh', String(Date.now()));
        } catch (e) {}
        try { window.dispatchEvent(new CustomEvent('career_jobs_refresh')); } catch (e) {}
      } else {
        setJobs(prev => prev.map(j => (j.job_id === jobId ? { ...j, is_active: isActive } : j)));
        showToast(`Failed to toggle job status.`, "error");
      }
    } catch (err: any) {
      setJobs(prev => prev.map(j => (j.job_id === jobId ? { ...j, is_active: isActive } : j)));
      showToast(`Error toggling status: ${err.message || 'An unknown error occurred'}`, "error");
    } finally {
      setPendingToggles(p => { const copy = { ...p }; delete copy[jobId]; return copy; });
    }
  }

  const openJobDetails = (job: JobPost) => {
    console.debug('[JobPostsList] openJobDetails payload:', job);
    setExpandedJob(job);
  };

  const closeJobDetails = () => setExpandedJob(null);

  const togglePin = (jobId: string) => {
    setPinnedIds(prev => {
      const copy = { ...prev };
      if (copy[jobId]) delete copy[jobId];
      else copy[jobId] = true;
      return copy;
    });
    setJobs(prev => prev.map(j => (j.job_id === jobId ? { ...j, is_pinned: !j.is_pinned } : j)));
    setPinnedPulseIds(p => ({ ...p, [jobId]: true }));
    setTimeout(() => setPinnedPulseIds(p => { const c = { ...p }; delete c[jobId]; return c; }), 700);
  };

  const displayedJobs = useMemo(() => {
    if (!jobs || jobs.length === 0) return [];
    console.log(`[JOBS_LIST-FILTER] Current User ID for comparison: ${currentUserIdNormalized}`); // <- CRITICAL LOG
    console.log(`[JOBS_LIST-FILTER] Total jobs loaded: ${jobs.length}`);


      const tabFiltered = jobs.filter(job => {
      const creatorId = getJobCreatorId(job);

      const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
      
      if (activeTab === 'my_jobs') {
        return isAuthor;
      }
      return !isAuthor;
    });

    console.log(`[JOBS_LIST] Jobs after internal filter for '${activeTab}': ${tabFiltered.length}`); // <- ADDED LOG


    const pinned: JobPost[] = [];
    const others: JobPost[] = [];
    for (const j of tabFiltered) {
      if (pinnedIds[j.job_id] || (j as any).is_pinned) pinned.push(j);
      else others.push(j);
    }
    console.log('[JOBS_LIST] Final displayed jobs count:', pinned.length + others.length); // <- ADDED LOG

    return [...pinned.reverse(), ...others];
  }, [jobs, pinnedIds, activeTab, currentUserIdNormalized]); 

  // Whether the current user can delete at least one job in the current view
  const hasDeletableJobs = useMemo(() => {
    if (!displayedJobs || displayedJobs.length === 0) return false;
    if (isSuperAdmin) return true;
    if (viewingOthersTab) return false;
    return displayedJobs.some(j => {
      const creatorId = getJobCreatorId(j);
      const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
      return isAuthor;
    });
  }, [displayedJobs, currentUserIdNormalized, isSuperAdmin, viewingOthersTab]);


  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <Loader2 size={48} className="text-[var(--color-primary-500)] animate-spin" />
        <p className="mt-4 text-gray-500">Loading job posts...</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <style>{`
        .card-pin-lift {
          transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
          transform: translateY(0);
          position: relative;
          z-index: 1;
        }
        .card-pin-lift.is-pinned {
          transform: translateY(-6px);
          box-shadow: 0 12px 28px rgba(0,0,0,0.08);
          z-index: 2;
        }

        @keyframes pinPop {
          0% { transform: scale(.6) rotate(-10deg); opacity: .0; }
          40% { transform: scale(1.15) rotate(6deg); opacity: 1; }
          70% { transform: scale(.98) rotate(-3deg); }
          100% { transform: scale(1) rotate(0deg); }
        }
        .pin-badge { display:inline-flex; align-items:center; justify-content:center; }
        .pin-badge.animate-pin-pop { animation: pinPop 560ms cubic-bezier(0.4, 0, 0.2, 1); }
      `}</style>

      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 hidden sm:block">
          {activeTab === 'my_jobs' ? 'My Job Posts' : 'Job Posts by Others'} ({displayedJobs.length})
        </h2>
        <div className="flex gap-4 items-center">
          <button className="sm:hidden p-2 rounded-md bg-white border border-gray-100 shadow-sm" onClick={() => setMobileSidebarOpen(true)} title="Menu">
            <Menu size={18} />
          </button>

          {hasDeletableJobs && (
            <div className="flex items-center gap-2 h-10 px-3 bg-white/90 border border-gray-100 rounded-md shadow-sm">
              <style>{`@keyframes badgePop { 0%{ transform: scale(.9); opacity: .6 } 60%{ transform: scale(1.06); opacity: 1 } 100%{ transform: scale(1); opacity: 1 } } .badge-burst { animation: badgePop 420ms ease; }`}</style>
              <div className="relative">
                <button
                  title="Select options"
                  onClick={() => setTopSelectMenuOpen(v => !v)}
                  className="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600 transition-colors"
                >
                  <CheckSquare size={14} />
                  <ChevronDown size={14} className={`transition-transform duration-200 ${topSelectMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                {topSelectMenuOpen && (
                  <div className="absolute right-0 top-9 bg-white rounded-md shadow-lg border border-gray-100 p-1 text-sm z-30 min-w-[120px]">
                    <button
                      className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700"
                      onClick={() => { selectAll(); setTopSelectMenuOpen(false); }}
                    >
                      <CheckSquare size={12} className="text-gray-400" />
                      Select All
                    </button>
                    <button
                      className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700"
                      onClick={() => { clearSelection(); setTopSelectMenuOpen(false); }}
                    >
                      <X size={12} className="text-gray-400" />
                      Clear
                    </button>
                    <button
                      className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700"
                      onClick={() => { invertSelection(); setTopSelectMenuOpen(false); }}
                    >
                      <RefreshCw size={12} className="text-gray-400" />
                      Invert
                    </button>
                  </div>
                )}
              </div>

              <div className={`inline-flex items-center justify-center h-6 min-w-[24px] px-2 rounded text-xs font-medium ${
                selectedCount ? 'bg-red-50 text-red-600' : 'bg-gray-50 text-gray-500'
                } badge-burst`}>
                {selectedCount}
              </div>

              <div className="h-4 w-px bg-gray-200" />

              <button
                onClick={handleDeleteSelected}
                disabled={selectedCount === 0 || bulkProcessing}
                aria-busy={bulkProcessing}
                title={selectedCount === 0 ? 'Select jobs to enable delete' : 'Delete selected jobs'}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  selectedCount === 0
                    ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                    : 'bg-red-50 text-red-600 hover:bg-red-100 active:bg-red-200'}`}
              >
                {bulkProcessing ? (
                  <>
                    <Loader2 size={12} className="animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 size={12} />
                    <span>Delete</span>
                  </>
                )}
              </button>
            </div>
          )}
          <Button
            onClick={fetchJobs}
            variant="outline"
            className="rounded-lg px-4 h-10 text-sm flex items-center justify-center"
            disabled={refreshing}
          >
            {refreshing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
          </Button>

        </div>
      </div>

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 sm:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileSidebarOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-white shadow-xl p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <img src={"/"} alt="" className="hidden" />
              <button onClick={() => setMobileSidebarOpen(false)} className="p-2 rounded-md bg-gray-100"><X size={16} /></button>
            </div>
            <nav className="flex flex-col gap-2">
              {filteredNavItems.map(({ label, Icon, path }) => (
                <NavLink key={label} to={path} onClick={() => setMobileSidebarOpen(false)} className={({ isActive }) => `flex items-center gap-3 px-3 py-2 rounded-md ${isActive ? 'bg-gray-200 text-gray-900' : 'text-gray-700 hover:bg-gray-100'}`}>
                  <Icon size={16} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </aside>
        </div>
      )}
      <div className="w-full flex flex-col gap-3">
        {displayedJobs.length === 0 ? (
          activeTab === 'my_jobs' ? (
            <div className="w-full flex flex-col items-center justify-center min-h-[400px] bg-gradient-to-br from-blue-50/50 to-indigo-50/30 rounded-xl border border-gray-100 shadow-sm">
              <div className="text-center p-8 max-w-md mx-auto">
                <div className="w-16 h-16 mx-auto mb-6 bg-blue-100 rounded-full flex items-center justify-center">
                  <Briefcase size={32} className="text-blue-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Create Your First Job Post</h3>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                  <Button 
                    onClick={() => onAddNewJob?.()} 
                    className="w-full sm:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-all duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
                  >
                    <Plus size={18} className="mr-2" />
                    Create Job Post
                  </Button>
                </div>
                <div className="mt-8 pt-6 border-t border-gray-200">
                  <p className="text-xs text-gray-500">
                    Need help getting started? Check out our 
                    <span 
                      onClick={() => setShowQuickGuide(true)} 
                      className="text-blue-600 hover:text-blue-700 cursor-pointer font-medium ml-1"
                    >
                      quick guide
                    </span>
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="w-full flex flex-col items-center justify-center min-h-[400px] bg-gradient-to-br from-gray-50/50 to-slate-50/30 rounded-xl border border-gray-100 shadow-sm">
              <div className="text-center p-8 max-w-md mx-auto">
                <div className="w-16 h-16 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
                  <Users size={32} className="text-gray-600" />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">No Job Posts Yet</h3>
                <p className="text-gray-600 mb-8 leading-relaxed">
                  There are currently no job posts from other team members. 
                  Check back later or encourage your team to start posting new opportunities.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                </div>
                <div className="mt-8 pt-6 border-t border-gray-200">
                  <p className="text-xs text-gray-500">
                    Want to contribute? 
                    <span 
                      onClick={() => onAddNewJob?.()} 
                      className="text-blue-600 hover:text-blue-700 cursor-pointer font-medium ml-1"
                    >
                      Create a job post
                    </span>
                  </p>
                </div>
              </div>
            </div>
          )
          ) : (
          displayedJobs.map((job) => {
          const creatorId = getJobCreatorId(job);
          const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
          const canManage = isAuthor || isSuperAdmin;
          const canEdit = isSuperAdmin || (!viewingOthersTab && isAuthor);
          const canDelete = isSuperAdmin || (!viewingOthersTab && isAuthor);
          const canToggle = isSuperAdmin || (!viewingOthersTab && isAuthor);
          const showActionButtons = canEdit || canDelete;
          const columnHasControls = canToggle || showActionButtons;
          const actionColumnAlignment = columnHasControls ? "items-end" : "items-center";
          const actionColumnJustify = columnHasControls ? "justify-start" : "justify-center";
          const actionColumnPadding = columnHasControls ? "pt-6" : "py-6";
          const expJustifyClass = canToggle ? "justify-end" : "justify-center";
          const expMarginClass = columnHasControls ? "mt-1" : "mt-0";
          const contentRightPaddingClass = columnHasControls ? "sm:pr-4" : "sm:pr-36";

          const ownerNameFromFields = [job.owner_first_name, job.owner_last_name]
            .filter((value) => typeof value === "string" && value.trim())
            .join(" ")
            .trim();
          const ownerNameFromCreator = job.creator
            ? [job.creator.first_name, job.creator.last_name]
                .filter((value) => typeof value === "string" && value?.trim())
                .join(" ")
                .trim()
            : "";
          const ownerName = firstNonEmptyString(
            job.owner_name,
            ownerNameFromFields || undefined,
            job.creator?.full_name,
            ownerNameFromCreator || undefined,
            job.owner_email,
            job.creator?.email,
          ) ?? (job.created_by_user_id ? `User ${String(job.created_by_user_id).slice(0, 8)}` : undefined);

          const ownerLabelText = `Created by: ${ownerName ?? "Unknown"}`;
          const ownerLabelClass = isAuthor
            ? "inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full"
            : "inline-flex items-center gap-1 text-xs font-semibold text-gray-700 bg-gray-100 border border-gray-200 px-2 py-0.5 rounded-full";
          const shouldShowOwnerLabel = viewingOthersTab || !isAuthor;
          const contentTopPaddingClass = shouldShowOwnerLabel ? "pt-8" : "pt-4";

          return (
            <div
              key={job.job_id}
              className={`relative card-pin-lift flex items-stretch w-full p-0 sm:p-0 rounded-lg transition-all duration-200 transform-gpu ${
                (job as any).is_deleting ? 'opacity-50 pointer-events-none' : ''
                } ${selectedIds[job.job_id] ? 'bg-red-50 border-l-4 border-red-400' : 'bg-white border border-gray-100'} hover:shadow-lg hover:-translate-y-0.5 overflow-hidden ${((job as any).is_pinned || pinnedIds[job.job_id]) ? 'is-pinned' : ''}`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { openJobDetails(job); } }}
            >
              <button
                onClick={(e) => { e.stopPropagation(); togglePin(job.job_id); }}
                title={((job as any).is_pinned || pinnedIds[job.job_id]) ? "Unpin from top" : "Pin to top"}
                aria-label={((job as any).is_pinned || pinnedIds[job.job_id]) ? "Unpin job" : "Pin job to top"}
                className={`absolute top-3 right-3 z-40 p-1 rounded-full transition-colors bg-transparent ${
                  ((job as any).is_pinned || pinnedIds[job.job_id]) 
                    ? 'text-red-500 hover:text-red-700' 
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Pin
                  size={18}
                  className={`pin-badge ${pinnedPulseIds[job.job_id] ? 'animate-pin-pop' : ''}`}
                  fill={((job as any).is_pinned || pinnedIds[job.job_id]) ? 'currentColor' : 'none'}
                  strokeWidth={2}
                />
              </button>
              {(!viewingOthersTab || isSuperAdmin) && (
                <div
                  className={`flex-shrink-0 flex items-center justify-center p-3 sm:p-4 transition-colors ${selectedIds[job.job_id] ? 'bg-red-100/50' : 'bg-gray-50'} border-r border-gray-100`}
                  onClick={(e) => e.stopPropagation()}
                >
                  {canDelete ? (
                    <label className="inline-flex items-center cursor-pointer" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        aria-label={`Select job ${job.job_title}`}
                        className="sr-only peer"
                        checked={!!selectedIds[job.job_id]}
                        onChange={(e) => { toggleSelect(job.job_id, e.target.checked); }}
                        onClick={(e) => e.stopPropagation()}
                      />

                      <div className={`relative flex items-center justify-center w-6 h-6 border-2 rounded transition-all duration-200 ${selectedIds[job.job_id] ? 'bg-red-50 border-red-500' : 'bg-white border-gray-300 hover:border-red-400'}`}>
                        <Check
                          className={`w-5 h-5 transition-all duration-200 ${selectedIds[job.job_id] ? 'text-red-500 opacity-100 scale-100' : 'opacity-0 scale-75'}`}
                          strokeWidth={3}
                          aria-hidden="true"
                        />
                      </div>
                    </label>
                  ) : (
                    <div className="w-6 h-6" />
                  )}
                </div>
              )}
              <div
                className="flex flex-col sm:flex-row items-start sm:items-start flex-1 p-3 sm:p-4"
                onClick={() => openJobDetails(job)}
              >
                <div className={clsx("relative w-full sm:flex-1", contentRightPaddingClass, contentTopPaddingClass)}>
                  {shouldShowOwnerLabel && (
                    <div className="absolute left-0 top-0">
                      <span className={ownerLabelClass}>{ownerLabelText}</span>
                    </div>
                  )}

                  <div className="sm:hidden">
                    <div className="py-2">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-lg font-bold text-gray-900 truncate mr-2">{job.job_title}</h3>
                        <div className="flex items-center gap-2">
                          {canToggle && (
                            <>
                              <button
                                type="button"
                                className={`relative inline-flex items-center w-10 h-5 rounded-full transition-colors duration-300 focus:outline-none ${job.is_active ? 'bg-blue-600' : 'bg-gray-300'} ${pendingToggles[job.job_id] ? 'opacity-50 cursor-not-allowed' : ''}`}
                                onClick={(e) => { e.stopPropagation(); if (!pendingToggles[job.job_id]) handleToggleStatus(job.job_id, job.is_active); }}
                                aria-pressed={job.is_active}
                                aria-disabled={pendingToggles[job.job_id]}
                                title={job.is_active ? 'This job is visible on the career page.' : 'This job is not visible on the career page.'}
                              >
                                <span
                                  className={`absolute left-1 top-0.5 w-4 h-4 rounded-full bg-white shadow-md transform transition-transform duration-300 ${job.is_active ? 'translate-x-5' : ''}`}
                                  style={{ boxShadow: job.is_active ? '0 0 8px #3b82f6' : '0 1px 4px rgba(0,0,0,0.15)' }}
                                >
                                  {job.is_active && (
                                    <svg className="w-3 h-3 text-blue-600 absolute top-0 left-0" fill="none" viewBox="0 0 20 20"><path stroke="currentColor" strokeWidth="2" d="M6 10l3 3 5-5"/></svg>
                                  )}
                                </span>
                              </button>
                              <span className={`text-xs font-semibold ${job.is_active ? 'text-blue-600' : 'text-gray-500'}`}>{job.is_active ? 'Active' : 'Inactive'}</span>
                            </>
                          )}
                        </div>
                        <span
                          title={job.is_active ? 'This job is visible on the career page.' : 'This job is not visible on the career page.'}
                          onClick={(e) => e.stopPropagation()}
                          className="ml-2"
                        >
                          <Info size={14} className="text-gray-400 cursor-pointer" aria-hidden="true" />
                        </span>
                      </div>
                      <div className="flex items-center text-sm text-gray-500 mt-3 gap-3">
                        <span className="inline-flex items-center gap-1 truncate"><MapPin size={14} className="text-gray-400" />{job.work_from_home ? 'Remote' : job.job_location}</span>
                        <span className="inline-flex items-center gap-1"><Calendar size={14} className="text-gray-400" />Posted Date: {job.posted_date ? new Date(job.posted_date).toLocaleDateString() : '—'}</span>
                      </div>
                      <div className="text-sm text-gray-700 mt-2">{job.job_description ? (job.job_description.length > 100 ? `${job.job_description.slice(0, 100)}...` : job.job_description) : 'No description available'}</div>
                      {job.key_functionality && job.key_functionality.length > 0 && (
                        <div className="mt-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">Exp: {job.minimum_experience}-{job.maximum_experience} yrs</span>
                            <span className="inline-flex items-center text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">{job.work_from_home ? 'Remote' : job.job_location}</span>
                            {job.key_functionality.slice(0, 2).map((kf, idx) => (
                              <span key={idx} title={kf.description} className="inline-flex items-center text-xs bg-blue-50 text-blue-800 px-2 py-1 rounded-full">{kf.type}</span>
                            ))}
                            {job.key_functionality.length > 2 && <div className="text-xs text-gray-400">+{job.key_functionality.length - 2} more</div>}
                          </div>
                        </div>
                      )}
                      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs text-gray-600">
                        <div className="bg-blue-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-blue-900">{jobStats[job.job_id]?.total_applied ?? 0}</div>
                          <div className="mt-0.5">Applied</div>
                        </div>
                        <div className="bg-green-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-green-900">{jobStats[job.job_id]?.total_selected ?? 0}</div>
                          <div className="mt-0.5">Shortlisted</div>
                        </div>
                        <div className="bg-red-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-red-900">{jobStats[job.job_id]?.total_rejected ?? 0}</div>
                          <div className="mt-0.5">Rejected</div>
                        </div>
                        <div className="bg-yellow-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-yellow-900">{jobStats[job.job_id]?.total_under_review ?? 0}</div>
                          <div className="mt-0.5">Review</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="hidden sm:flex items-center gap-4 flex-1 min-w-0 w-full">
                    <div className="flex-shrink-0 w-full sm:w-44 mr-4 mb-2 sm:mb-0">
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900 whitespace-normal sm:whitespace-nowrap sm:truncate max-w-full">{job.job_title}</h3>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">Exp: {job.minimum_experience}-{job.maximum_experience} yrs</span>
                        <span className="inline-flex items-center text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">Rounds: {(job.interview_rounds ? job.interview_rounds.length : 0)}</span>
                        {job.key_functionality && job.key_functionality.length > 0 && (
                          job.key_functionality.slice(0, 2).map((kf, i) => (
                            <span key={i} title={kf.description} className="inline-flex items-center text-xs bg-blue-50 text-blue-800 px-2 py-1 rounded-full">{kf.type}</span>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="flex-1 min-w-0 w-full px-0 sm:px-3">
                      <div className="flex items-center text-sm text-gray-500 mt-1 gap-3 truncate">
                        <span className="inline-flex items-center gap-1 truncate"><MapPin size={14} className="text-gray-400" /> <span className="truncate">{job.work_from_home ? 'Remote' : job.job_location}</span></span>
                        <span className="hidden sm:inline">•</span>
                        <span className="hidden sm:inline-flex items-center gap-1"><Calendar size={14} className="text-gray-400" /><span className="text-gray-400">Created Date :</span><span>{job.posted_date ? new Date(job.posted_date).toLocaleDateString() : '—'}</span></span>
                      </div>
                      <div className="text-sm text-gray-700 mt-2 max-w-full break-words overflow-hidden" style={{ maxHeight: '3.6rem' }}>
                        {job.job_description ? (job.job_description.length > 220 ? `${job.job_description.slice(0, 220)}...` : job.job_description) : 'No description available'}
                      </div>

                      {job.key_functionality && job.key_functionality.length > 0 && (
                        <div className="mt-3">
                          <p className="text-sm font-semibold text-gray-600 mb-2">Additional Descriptions</p>
                          <div className="flex flex-col sm:flex-row gap-2">
                            {job.key_functionality.slice(0, 2).map((kf, i) => (
                              <div key={i} className="flex-1 bg-gray-50 border border-gray-100 rounded-md p-2 text-sm text-gray-700">
                                <div className="text-xs font-semibold text-gray-600 truncate">{kf.type}</div>
                                <div className="text-sm text-gray-700 truncate">{kf.description ? (kf.description.length > 140 ? `${kf.description.slice(0, 140)}...` : kf.description) : ''}</div>
                              </div>
                            ))}
                            {job.key_functionality.length > 2 && (
                              <div className="flex items-center text-xs text-gray-500">+{job.key_functionality.length - 2} more</div>
                            )}
                          </div>
                        </div>
                      )}

                      <div className="mt-3 w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 text-center text-xs text-gray-600">
                        <div className="bg-blue-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-blue-900">{jobStats[job.job_id]?.total_applied ?? 0}</div>
                          <div className="mt-0.5">Applied</div>
                        </div>
                        <div className="bg-green-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-green-900">{jobStats[job.job_id]?.total_selected ?? 0}</div>
                          <div className="mt-0.5">Shortlisted</div>
                        </div>
                        <div className="bg-red-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-red-900">{jobStats[job.job_id]?.total_rejected ?? 0}</div>
                          <div className="mt-0.5">Rejected</div>
                        </div>
                        <div className="bg-yellow-50 rounded-md p-2">
                          <div className="font-semibold text-sm text-yellow-900">{jobStats[job.job_id]?.total_under_review ?? 0}</div>
                          <div className="mt-0.5">Review</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {columnHasControls ? (
                  <div className={clsx(
                    "hidden sm:flex flex-col gap-3 ml-0 sm:ml-4 mt-0 w-full sm:w-auto flex-shrink-0",
                    actionColumnAlignment,
                    actionColumnJustify,
                    actionColumnPadding
                  )}>
                    {showActionButtons && (
                      <div className="flex items-center justify-end gap-2 w-full">
                        {canEdit && (
                        <button
                          onClick={(e) => { e.stopPropagation(); onEditJob(job.job_id); }}
                          className={clsx(
                            "inline-flex items-center gap-2 p-2 rounded-md transition-all duration-150",
                            "text-gray-600 hover:text-blue-600 hover:bg-blue-50"
                          )}
                          title={`Edit ${job.job_title}`}
                          aria-label={`Edit ${job.job_title}`}
                        >
                          <FilePenLine size={16} />
                          <span className="sr-only">Edit</span>
                        </button>
                        )}

                        {canDelete && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDelete(job.job_id, job.job_title); }}
                            className={clsx(
                              "p-2 rounded-md transition-all duration-150",
                              "text-gray-500 hover:text-red-600 hover:bg-red-50"
                            )}
                            title={`Delete ${job.job_title}`}
                            aria-label={`Delete ${job.job_title}`}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    )}

                    <div className={clsx("w-full flex", expJustifyClass, expMarginClass)}>
                      <div className="bg-gray-50 px-3 py-1.5 rounded-md text-sm text-gray-600"><span className="font-semibold mr-1">Exp:</span> {job.minimum_experience}-{job.maximum_experience} yrs</div>
                    </div>

                    {canToggle && (
                      <div className="w-full flex flex-col items-center gap-1 mt-2">
                        <div className="w-full text-center text-xs font-medium text-gray-500">Add Job into Career Page</div>
                        <div className="w-full flex items-center justify-center gap-2">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              className={`relative inline-flex items-center w-10 h-5 rounded-full transition-colors duration-300 focus:outline-none ${job.is_active ? 'bg-blue-600' : 'bg-gray-300'} ${pendingToggles[job.job_id] ? 'opacity-50 cursor-not-allowed' : ''}`}
                              onClick={(e) => { e.stopPropagation(); if (!pendingToggles[job.job_id]) handleToggleStatus(job.job_id, job.is_active); }}
                              aria-pressed={job.is_active}
                              aria-disabled={pendingToggles[job.job_id]}
                              title={job.is_active ? 'Unpost from the career page' : 'Post to the career page'}
                              aria-label={`Toggle status for ${job.job_title}`}
                            >
                              <span
                                className={`absolute left-1 top-0.5 w-4 h-4 rounded-full bg-white shadow-md transform transition-transform duration-300 ${job.is_active ? 'translate-x-5' : ''}`}
                                style={{ boxShadow: job.is_active ? '0 0 8px #3b82f6' : '0 1px 4px rgba(0,0,0,0.15)' }}
                              >
                                {job.is_active && (
                                  <svg className="w-3 h-3 text-blue-600 absolute top-0 left-0" fill="none" viewBox="0 0 20 20"><path stroke="currentColor" strokeWidth="2" d="M6 10l3 3 5-5"/></svg>
                                )}
                              </span>
                            </button>
                            <span className={`text-xs font-semibold ${job.is_active ? 'text-blue-600' : 'text-gray-500'}`}>{job.is_active ? 'Active' : 'Inactive'}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
              {!columnHasControls && (
                <div className="hidden sm:flex absolute inset-y-0 right-4 pointer-events-none">
                  <div className="flex items-center h-full">
                    <div className="bg-gray-50 px-3 py-1.5 rounded-md text-sm text-gray-600"><span className="font-semibold mr-1">Exp:</span> {job.minimum_experience}-{job.maximum_experience} yrs</div>
                  </div>
                </div>
              )}
            </div>
          )
  }) )}
      </div>
    
      {hasDeletableJobs && (
        <div
          className={`fixed inset-x-0 z-50 flex justify-center transition-transform duration-300 ease-out ${selectedCount > 0 ? 'translate-y-0' : 'translate-y-40 pointer-events-none'}`}
          style={{ bottom: '2.0rem' }}
        >
        <div className="flex items-center gap-2 bg-white border border-gray-100 rounded-md shadow-lg p-2 pointer-events-auto mx-3">
          <div className="relative">
            <button
              title="Select options"
              onClick={() => setBottomSelectMenuOpen(v => !v)}
              className="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600 transition-colors"
            >
              <CheckSquare size={14} />
              <ChevronDown size={14} className={`transition-transform duration-200 ${bottomSelectMenuOpen ? 'rotate-180' : ''}`} />
            </button>

            {bottomSelectMenuOpen && (
              <div className="absolute right-0 bottom-28 bg-white rounded-md shadow-lg border border-gray-100 p-1 text-sm z-50 min-w-[140px]">
                <button className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700" onClick={() => { selectAll(); setBottomSelectMenuOpen(false); }}>
                  <CheckSquare size={12} className="text-gray-400" />
                  Select All
                </button>
                <button className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700" onClick={() => { clearSelection(); setBottomSelectMenuOpen(false); }}>
                  <X size={12} className="text-gray-400" />
                  Clear
                </button>
                <button className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700" onClick={() => { invertSelection(); setBottomSelectMenuOpen(false); }}>
                  <RefreshCw size={12} className="text-gray-400" />
                  Invert
                </button>
              </div>
            )}
          </div>

          <div className={`inline-flex items-center justify-center h-6 min-w-[24px] px-2 rounded text-xs font-medium ${selectedCount ? 'bg-red-50 text-red-600' : 'bg-gray-50 text-gray-500'}`}>
            {selectedCount}
          </div>

          <div className="h-4 w-px bg-gray-200" />

          <button
            onClick={handleDeleteSelected}
            disabled={selectedCount === 0 || bulkProcessing}
            aria-busy={bulkProcessing}
            title={selectedCount === 0 ? 'Select jobs to enable delete' : 'Delete selected jobs'}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${selectedCount === 0 ? 'bg-gray-50 text-gray-400 cursor-not-allowed' : 'bg-red-50 text-red-600 hover:bg-red-100 active:bg-red-200'}`}
          >
            {bulkProcessing ? (
              <>
                <Loader2 size={12} className="animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 size={12} />
                <span>Delete</span>
              </>
            )}
          </button>
        </div>
      </div>
      )}

      {expandedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={closeJobDetails} />
          <div
            className="relative bg-white w-[95%] max-w-4xl rounded-xl shadow-xl p-6 z-50 overflow-auto max-h-[90vh] transform transition-all duration-300 ease-out"
            style={{ animation: 'modalIn 220ms ease-out' }}
            onClick={(e) => e.stopPropagation()}
          >
            <style>{`
              @keyframes modalIn {
                from { opacity: 0; transform: translateY(-8px) scale(0.98); }
                to { opacity: 1; transform: translateY(0) scale(1); }
              }
            `}</style>

            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{expandedJob!.job_title}</h2>
                <p className="text-sm text-gray-500 mt-1">{expandedJob!.work_from_home ? 'Remote' : expandedJob!.job_location}</p>
                {expandedJob!.key_functionality && expandedJob!.key_functionality.length > 0 && (
                  <div className="text-sm text-gray-600 mt-2">{expandedJob!.key_functionality.length} Additional Descriptions</div>
                )}
                <p className="text-xs text-gray-400 mt-1">
                  Posted: {expandedJob!.posted_date ? new Date(expandedJob!.posted_date as string).toLocaleDateString() : '—'}
                </p>
              </div>
              <div className="flex gap-2">
                {(() => {
                  const creatorId = getJobCreatorId(expandedJob);
                  const isAuthor = normalizeId(creatorId) === currentUserIdNormalized;
                  const canEdit = isAuthor || isSuperAdmin;
                  return (
                    <button
                      onClick={(e) => { e.stopPropagation(); onEditJob(expandedJob.job_id); closeJobDetails(); }}
                      disabled={!canEdit} 
                      className={clsx(
                        "p-2 rounded-md transition-colors",
                        !canEdit
                          ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
                          : "bg-[var(--color-primary-500)] text-white hover:bg-[var(--color-primary-600)]"
                      )}
                      aria-label={canEdit ? "Edit job" : "View job (read-only)"}
                      title={canEdit ? "Edit" : "View Details (Read-only)"}
                    >
                      {canEdit ? <FilePenLine size={18} /> : <View size={18} />}
                    </button>
                  );
                })()}
                <button
                  onClick={(e) => { e.stopPropagation(); closeJobDetails(); }}
                  className="p-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
                  aria-label="Close details"
                  title="Close"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="space-y-4">
              <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm font-semibold text-gray-600 mb-2">Job Description</p>
                <div className="text-sm text-gray-700 whitespace-pre-line">{expandedJob!.job_description}</div>
              </div>

              {/* Show Job Details in Modal */}
              <div className="flex flex-col gap-4">

                {((expandedJob.interview_rounds && expandedJob.interview_rounds.length > 0) || (expandedJob.interview_levels && expandedJob.interview_levels.length > 0)) && (
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm font-semibold text-gray-600 mb-2">Interview Rounds</p>
                    <ol className="list-none pl-0 space-y-4">
                      {(expandedJob.interview_rounds && expandedJob.interview_rounds.length > 0 ? expandedJob.interview_rounds : expandedJob.interview_levels || []).map((level: any, i: number) => {
                        const name = level?.level_name || level?.title || String(level || `Round ${i+1}`);
                        const desc = level?.round_description || level?.description || level?.context || '';
                        const shortlisting = level?.evaluation_criteria?.shortlisting_criteria ?? level?.shortlisting_threshold ?? level?.shortlisting ?? expandedJob?.shortlisting_criteria ?? null;
                        const rejecting = level?.evaluation_criteria?.rejecting_criteria ?? level?.rejected_threshold ?? level?.rejecting_threshold ?? level?.rejecting ?? expandedJob?.rejecting_criteria ?? null;
                        const potential = level?.evaluation_criteria?.potential ?? level?.potential ?? (i === 0 ? expandedJob?.potential : null);
                        const roleFit = level?.evaluation_criteria?.role_fit ?? level?.role_fit ?? (i === 0 ? expandedJob?.role_fit : null);

                        // First round (screening) => show richer scoring cards (shortlist %, reject %, potential, role-fit)
                        if (i === 0) {
                          return (
                            <li key={i} className="text-sm text-gray-700">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-xs font-medium">{i + 1}</span>
                                  <div className="font-medium">{name} <span className="text-xs text-gray-500 ml-2">(Screening)</span></div>
                                </div>
                                <div className="text-xs text-gray-400">Round {i + 1}</div>
                              </div>
                              {desc ? <div className="text-xs text-gray-600 mt-1">{desc}</div> : null}

                              <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2">
                                <div className="p-2 bg-white rounded border border-gray-100 text-center">
                                  <div className="text-xs text-gray-500">Shortlisting %</div>
                                  <div className="text-lg font-bold text-gray-900 mt-1">{shortlisting !== null && shortlisting !== undefined ? `${shortlisting}%` : 'N/A'}</div>
                                </div>

                                <div className="p-2 bg-white rounded border border-gray-100 text-center">
                                  <div className="text-xs text-gray-500">Rejecting %</div>
                                  <div className="text-lg font-bold text-gray-900 mt-1">{rejecting !== null && rejecting !== undefined ? `${rejecting}%` : 'N/A'}</div>
                                </div>

                                <div className="p-2 bg-white rounded border border-gray-100 text-center">
                                  <div className="text-xs text-gray-500">Potential</div>
                                  <div className="text-lg font-bold text-gray-900 mt-1">{potential !== null && potential !== undefined ? `${potential}%` : (expandedJob?.potential !== undefined ? `${expandedJob.potential}%` : 'N/A')}</div>
                                </div>

                                <div className="p-2 bg-white rounded border border-gray-100 text-center">
                                  <div className="text-xs text-gray-500">Role Fit</div>
                                  <div className="text-lg font-bold text-gray-900 mt-1">{roleFit !== null && roleFit !== undefined ? `${roleFit}%` : (expandedJob?.role_fit !== undefined ? `${expandedJob.role_fit}%` : 'N/A')}</div>
                                </div>
                              </div>
                            </li>
                          );
                        }

                        // Other rounds -> show name, description and shortlist/reject as cards (same design as screening)
                        return (
                          <li key={i} className="text-sm text-gray-700">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-xs font-medium">{i + 1}</span>
                                <div className="font-medium">{name}</div>
                              </div>
                              <div className="text-xs text-gray-400">Round {i + 1}</div>
                            </div>
                            {desc ? <div className="text-xs text-gray-600 mt-1">{desc}</div> : null}

                            <div className="mt-3 grid grid-cols-2 gap-2">
                              <div className="p-2 bg-white rounded border border-gray-100 text-center">
                                <div className="text-xs text-gray-500">Shortlisting %</div>
                                <div className="text-lg font-bold text-gray-900 mt-1">{shortlisting !== null && shortlisting !== undefined ? `${shortlisting}%` : 'N/A'}</div>
                              </div>

                              <div className="p-2 bg-white rounded border border-gray-100 text-center">
                                <div className="text-xs text-gray-500">Rejecting %</div>
                                <div className="text-lg font-bold text-gray-900 mt-1">{rejecting !== null && rejecting !== undefined ? `${rejecting}%` : 'N/A'}</div>
                              </div>
                            </div>
                          </li>
                        );
                      })}
                    </ol>
                  </div>
                )}
              </div>

              <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm font-semibold text-gray-600 mb-2">Key Skills</p>
                <div className="flex flex-wrap gap-2">
                  {(expandedJob!.skills_required || []).map((s, i) => (
                    <span key={i} className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">{s.skill} ({s.weightage})</span>
                  ))}
                </div>
              </div>

              {(!((expandedJob.interview_rounds && expandedJob.interview_rounds.length > 0) || (expandedJob.interview_levels && expandedJob.interview_levels.length > 0))) && (
                <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <p className="text-sm font-semibold text-gray-600 mb-3">Scoring Metrics</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 bg-white rounded-lg border border-gray-100 text-center sm:col-span-3">
                      <div className="text-xs text-gray-500">Shortlisting %</div>
                      <div className="text-lg font-bold text-gray-900 mt-1">{expandedJob!.shortlisting_criteria ?? expandedJob!.shortlisted ?? 0}%</div>
                    </div>

                    <div className="p-3 bg-white rounded-lg border border-gray-100 text-center">
                      <div className="text-xs text-gray-500">Role Fit</div>
                      <div className="text-lg font-bold text-gray-900 mt-1">{expandedJob!.role_fit ?? 0}%</div>
                    </div>

                    <div className="p-3 bg-white rounded-lg border border-gray-100 text-center">
                      <div className="text-xs text-gray-500">Potential</div>
                      <div className="text-lg font-bold text-gray-900 mt-1">{expandedJob!.potential ?? 0}%</div>
                    </div>

                    <div className="p-3 bg-white rounded-lg border border-gray-100 text-center">
                      <div className="text-xs text-gray-500">Location Score</div>
                      <div className="text-lg font-bold text-gray-900 mt-1">{expandedJob!.location_score ?? 0}%</div>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-4 gap-3 mt-2">
                <div className="p-3 bg-blue-50 rounded-lg text-center">
                  <div className="text-lg font-bold text-blue-900">{(jobStats[expandedJob.job_id]?.total_applied ?? 0)}</div>
                  <div className="text-xs text-blue-700">Applied</div>
                </div>
                <div className="p-3 bg-green-50 rounded-lg text-center">
                  <div className="text-lg font-bold text-green-900">{(jobStats[expandedJob.job_id]?.total_selected ?? 0)}</div>
                  <div className="text-xs text-green-700">Shortlisted</div>
                </div>
                <div className="p-3 bg-red-50 rounded-lg text-center">
                  <div className="text-lg font-bold text-red-900">{(jobStats[expandedJob.job_id]?.total_rejected ?? 0)}</div>
                  <div className="text-xs text-red-700">Rejected</div>
                </div>
                <div className="p-3 bg-yellow-50 rounded-lg text-center">
                  <div className="text-lg font-bold text-yellow-900">{(jobStats[expandedJob.job_id]?.total_under_review ?? 0)}</div>
                  <div className="text-xs text-yellow-700">Review</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Guide Modal */}
      {showQuickGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowQuickGuide(false)} />
          <div
            className="relative bg-white w-[95%] max-w-2xl rounded-xl shadow-xl p-6 z-50 overflow-auto max-h-[90vh] transform transition-all duration-300 ease-out"
            style={{ animation: 'modalIn 220ms ease-out' }}
            onClick={(e) => e.stopPropagation()}
          >
            <style>{`
              @keyframes modalIn {
                from { opacity: 0; transform: translateY(-8px) scale(0.98); }
                to { opacity: 1; transform: translateY(0) scale(1); }
              }
            `}</style>

            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <FileText size={20} className="text-blue-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Quick Guide</h2>
                  <p className="text-sm text-gray-500">How to create effective job posts</p>
                </div>
              </div>
              <button
                onClick={() => setShowQuickGuide(false)}
                className="p-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                aria-label="Close guide"
                title="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-6">
              {/* Step 1 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-blue-600">1</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Start with a Clear Job Title</h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Use specific, searchable titles that candidates will recognize. Avoid internal jargon or creative names.
                  </p>
                  <div className="bg-green-50 border border-green-200 rounded-md p-3">
                    <p className="text-xs font-medium text-green-800 mb-1">✓ Good Examples:</p>
                    <p className="text-xs text-green-700">"Senior Frontend Developer", "Marketing Manager", "Data Analyst"</p>
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-blue-600">2</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Write a Compelling Description</h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Clearly describe the role, responsibilities, and what makes your company attractive to candidates.
                  </p>
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                    <p className="text-xs font-medium text-blue-800 mb-2">Include these elements:</p>
                    <ul className="text-xs text-blue-700 space-y-1">
                      <li>• Key responsibilities and daily tasks</li>
                      <li>• Company culture and values</li>
                      <li>• Growth opportunities</li>
                      <li>• Benefits and perks</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-blue-600">3</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Set Realistic Requirements</h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Be specific about required skills and experience levels. Avoid overloading with "nice-to-have" requirements.
                  </p>
                  <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                    <p className="text-xs font-medium text-amber-800 mb-1">⚡ Pro Tip:</p>
                    <p className="text-xs text-amber-700">Separate "must-have" from "nice-to-have" skills to attract more qualified candidates.</p>
                  </div>
                </div>
              </div>

              {/* Step 4 */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-blue-600">4</span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-2">Configure Interview Process</h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Set up your interview rounds and scoring criteria to streamline candidate evaluation.
                  </p>
                  <div className="bg-purple-50 border border-purple-200 rounded-md p-3">
                    <p className="text-xs font-medium text-purple-800 mb-2">Recommended structure:</p>
                    <ul className="text-xs text-purple-700 space-y-1">
                      <li>• Initial screening (30% shortlist threshold)</li>
                      <li>• Technical/Skills assessment</li>
                      <li>• Cultural fit interview</li>
                      <li>• Final decision round</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-gray-200">
              <div className="flex flex-col sm:flex-row gap-3 justify-end">
                <Button 
                  variant="outline" 
                  onClick={() => setShowQuickGuide(false)}
                  className="px-4 py-2"
                >
                  Got it, thanks!
                </Button>
                <Button 
                  onClick={() => {
                    setShowQuickGuide(false);
                    onAddNewJob?.();
                  }}
                  className="px-4 py-2"
                >
                  <Plus size={16} className="mr-2" />
                  Create Job Post
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}