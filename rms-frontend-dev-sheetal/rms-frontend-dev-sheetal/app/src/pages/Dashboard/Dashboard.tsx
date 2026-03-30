import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Briefcase,
  Calendar,
  CheckSquare,
  ChevronDown,
  FileText,
  Loader2,
  TrendingUp,
  Users,
  XSquare,
} from 'lucide-react';
import { getActiveJobPosts, getAllJobPosts, getJobCandidates } from '../../api/jobApi';
import { useToast } from '../../context/ModalContext';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { NumberTicker } from '@/components/ui/number-ticker';
import { cn } from '@/lib/utils';

interface JobPostStats {
  job_id: string;
  job_title: string;
  total_applications: number;
  shortlisted: number;
  rejected: number;
  under_review: number;
  onboarding: number;
  interviews_scheduled: number;
  is_active: boolean;
  interview_rounds: number;
  screening: number;
  l1_interview: number;
  l2_interview: number;
  l3_interview: number;
  hired: number;
  total_interviewed: number;
  total_hired: number;
}

interface DashboardData {
  total_jobs: number;
  active_jobs: number;
  total_candidates_applied: number;
  total_shortlisted: number;
  total_rejected: number;
  total_under_review: number;
  total_interviewed: number;
  total_hired: number;
}

interface StatTileProps {
  title: string;
  value: number;
  icon: React.ElementType;
  description: string;
  loading: boolean;
}

const StatTile: React.FC<StatTileProps> = ({ title, value, icon: Icon, description, loading }) => {
  return (
    <Card className="@container/card h-full">
      <CardHeader className="relative pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
          {loading ? (
            <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Loading
            </span>
          ) : (
            <NumberTicker value={value} />
          )}
        </CardTitle>
        <span className="absolute top-4 right-4 inline-flex size-8 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <Icon className="size-4" />
        </span>
      </CardHeader>
      <CardFooter className="pt-0 text-xs text-muted-foreground">{description}</CardFooter>
    </Card>
  );
};

const stageConfig = [
  { key: 'total_applications', label: 'Applied' },
  { key: 'screening', label: 'Screening' },
  { key: 'l1_interview', label: 'L1' },
  { key: 'l2_interview', label: 'L2' },
  { key: 'l3_interview', label: 'L3' },
  { key: 'shortlisted', label: 'Shortlisted' },
  { key: 'hired', label: 'Hired' },
] as const;

type StageKey = (typeof stageConfig)[number]['key'];

const isRoundEnabled = (job: JobPostStats, stageKey: StageKey): boolean => {
  if (stageKey === 'l2_interview') {
    return job.interview_rounds >= 2;
  }
  if (stageKey === 'l3_interview') {
    return job.interview_rounds >= 3;
  }
  return true;
};

const parseCandidateDate = (candidate: any): Date | null => {
  const fields = ['applied_at', 'appliedAt', 'created_at', 'createdAt', 'createdOn', 'applied_on'];

  for (const field of fields) {
    const value = candidate?.[field];
    if (!value) {
      continue;
    }

    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }
  }

  return null;
};

const candidateBelongsToStage = (candidate: any, stageKey: StageKey): boolean => {
  const status = String(candidate?.status ?? candidate?.current_status ?? candidate?.profile_status ?? '').toLowerCase();
  const roundText = String(candidate?.current_round ?? candidate?.currentRound ?? candidate?.round ?? '').toLowerCase();
  const interviews = Array.isArray(candidate?.interviews) ? candidate.interviews : [];

  if (stageKey === 'screening') {
    return status.includes('under') || status.includes('screen');
  }
  if (stageKey === 'shortlisted') {
    return status.includes('shortlist');
  }
  if (stageKey === 'hired') {
    return status.includes('hired') || status.includes('onboard');
  }
  if (stageKey === 'total_applications') {
    return true;
  }

  const roundNumber = stageKey.match(/l(\d)_interview/)?.[1];
  if (!roundNumber) {
    return false;
  }

  if (roundText.includes(`l${roundNumber}`) || roundText.includes(roundNumber)) {
    return true;
  }

  return interviews.some((interview: any) => {
    const level = String(interview?.round ?? interview?.level ?? interview?.interview_round ?? '').toLowerCase();
    return level.includes(`l${roundNumber}`) || level.includes(roundNumber);
  });
};

const mapFetchedJob = (job: any): JobPostStats => {
  const jobId = job.job_id ?? job.jobId ?? job.id ?? '';
  const rawActive = job.is_active ?? job.isActive ?? job.active ?? job.enabled;
  const isActive =
    rawActive === undefined || rawActive === null
      ? false
      : typeof rawActive === 'boolean'
        ? rawActive
        : typeof rawActive === 'string'
          ? rawActive.toLowerCase() === 'true'
          : Boolean(rawActive);

  const profileCounts = job.profile_counts ?? job.profileCounts ?? null;
  const shortlisted = profileCounts?.shortlisted ?? job.shortlisted ?? job.shortlisted_count ?? 0;
  const rejected = profileCounts?.rejected ?? job.rejected ?? job.rejected_count ?? 0;
  const underReview = profileCounts?.under_review ?? job.under_review ?? job.underReview ?? 0;
  const onboarding = profileCounts?.onboarding ?? job.onboarding ?? 0;
  const interviewsScheduled =
    profileCounts?.interviews_scheduled ??
    profileCounts?.interviews ??
    job.interviews ??
    job.interview_count ??
    job.interviews_count ??
    0;

  const totalApplications =
    profileCounts?.applied ?? job.total_applications ?? shortlisted + rejected + underReview + onboarding;

  const title = String(job.job_title || 'Untitled Job');
  const interviewRounds = title.toLowerCase().includes('senior') || title.toLowerCase().includes('lead') ? 3 : 2;

  const interviewsInProgress = Math.max(0, interviewsScheduled - onboarding);
  const l1 = Math.max(0, Math.floor(interviewsInProgress * 0.5));
  const l2 = interviewRounds >= 2 ? Math.max(0, Math.floor(interviewsInProgress * (interviewRounds === 2 ? 0.5 : 0.3))) : 0;
  const l3 = interviewRounds >= 3 ? Math.max(0, interviewsInProgress - l1 - l2) : 0;

  return {
    job_id: jobId,
    job_title: title,
    total_applications: totalApplications,
    shortlisted,
    rejected,
    under_review: underReview,
    onboarding,
    interviews_scheduled: interviewsScheduled,
    is_active: isActive,
    interview_rounds: interviewRounds,
    screening: Math.max(0, underReview),
    l1_interview: l1,
    l2_interview: l2,
    l3_interview: l3,
    hired: onboarding,
    total_interviewed: l1 + l2 + l3,
    total_hired: onboarding,
  };
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [jobs, setJobs] = useState<JobPostStats[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [jobCandidates, setJobCandidates] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const { showToast } = useToast();

  const selectedJob = useMemo(() => jobs.find((job) => job.job_id === selectedJobId) ?? null, [jobs, selectedJobId]);

  const displayMetrics = useMemo(() => {
    if (selectedJob) {
      return {
        title: selectedJob.job_title,
        applied: selectedJob.total_applications,
        underReview: selectedJob.under_review,
        interviewed: selectedJob.total_interviewed,
        shortlisted: selectedJob.shortlisted,
        rejected: selectedJob.rejected,
        hired: selectedJob.total_hired,
      };
    }

    return {
      title: 'All Active Job Posts',
      applied: data?.total_candidates_applied ?? 0,
      underReview: data?.total_under_review ?? 0,
      interviewed: data?.total_interviewed ?? 0,
      shortlisted: data?.total_shortlisted ?? 0,
      rejected: data?.total_rejected ?? 0,
      hired: data?.total_hired ?? 0,
    };
  }, [selectedJob, data]);

  const fetchJobStats = useCallback(async () => {
    setIsLoading(true);

    try {
      const [allRes, activeRes] = await Promise.all([getAllJobPosts(), getActiveJobPosts()]);

      if (!allRes.success) {
        showToast(allRes.error || 'Failed to load dashboard data.', 'error');
        setData(null);
        setJobs([]);
        return;
      }

      const allJobsRaw = Array.isArray(allRes.data) ? allRes.data : allRes.data?.jobs || allRes.data || [];
      const activeJobsRaw = activeRes.success
        ? Array.isArray(activeRes.data)
          ? activeRes.data
          : activeRes.data?.jobs || activeRes.data || []
        : [];

      const activeJobIds = new Set(activeJobsRaw.map((job: any) => job.job_id ?? job.jobId ?? job.id));

      const mappedJobs: JobPostStats[] = allJobsRaw.map((job: any) => {
        const mapped = mapFetchedJob(job);
        return {
          ...mapped,
          is_active: activeJobIds.has(mapped.job_id),
        };
      });

      const dashboardData: DashboardData = {
        total_jobs: mappedJobs.length,
        active_jobs: mappedJobs.filter((job) => job.is_active).length,
        total_candidates_applied: mappedJobs.reduce((sum, job) => sum + job.total_applications, 0),
        total_shortlisted: mappedJobs.reduce((sum, job) => sum + job.shortlisted, 0),
        total_rejected: mappedJobs.reduce((sum, job) => sum + job.rejected, 0),
        total_under_review: mappedJobs.reduce((sum, job) => sum + job.under_review, 0),
        total_interviewed: mappedJobs.reduce((sum, job) => sum + job.total_interviewed, 0),
        total_hired: mappedJobs.reduce((sum, job) => sum + job.total_hired, 0),
      };

      setData(dashboardData);
      setJobs(mappedJobs);

      if (!selectedJobId) {
        const topActiveJob = mappedJobs
          .filter((job) => job.is_active)
          .sort((a, b) => b.total_applications - a.total_applications)[0];
        if (topActiveJob) {
          setSelectedJobId(topActiveJob.job_id);
        }
      }
    } catch (error: any) {
      showToast(error?.message || 'An error occurred while fetching dashboard data.', 'error');
      setData(null);
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }, [showToast, selectedJobId]);

  const fetchCandidatesForJob = useCallback(
    async (jobId?: string | null) => {
      if (!jobId) {
        setJobCandidates([]);
        return;
      }

      setCandidatesLoading(true);
      try {
        const response = await getJobCandidates(jobId);
        if (!response.success) {
          showToast(response.error || 'Failed to fetch candidates for this job.', 'error');
          setJobCandidates([]);
          return;
        }

        const payload = response.data && response.data.data !== undefined ? response.data.data : response.data;
        const list = Array.isArray(payload) ? payload : payload?.profiles ?? payload?.candidates ?? [];
        setJobCandidates(list || []);
      } catch (error: any) {
        showToast(error?.message || 'Error fetching candidates.', 'error');
        setJobCandidates([]);
      } finally {
        setCandidatesLoading(false);
      }
    },
    [showToast]
  );

  useEffect(() => {
    fetchJobStats();
  }, [fetchJobStats]);

  useEffect(() => {
    fetchCandidatesForJob(selectedJobId);
  }, [selectedJobId, fetchCandidatesForJob]);

  const activeJobs = useMemo(() => jobs.filter((job) => job.is_active), [jobs]);

  const mostAppliedJobs = useMemo(
    () => [...jobs].sort((a, b) => b.total_applications - a.total_applications).slice(0, 5),
    [jobs]
  );

  const today = useMemo(() => {
    const value = new Date();
    value.setHours(0, 0, 0, 0);
    return value;
  }, []);

  const todayActivity = useMemo(() => {
    const countsByJob: Record<string, number> = {};

    for (const candidate of jobCandidates) {
      const date = parseCandidateDate(candidate);
      if (!date) {
        continue;
      }

      const normalized = new Date(date);
      normalized.setHours(0, 0, 0, 0);
      if (normalized.getTime() !== today.getTime()) {
        continue;
      }

      const jobId =
        candidate.job_id ?? candidate.jobId ?? candidate.job?.job_id ?? candidate.job?.id ?? selectedJob?.job_id ?? 'unknown';
      countsByJob[jobId] = (countsByJob[jobId] || 0) + 1;
    }

    return jobs.map((job) => ({
      id: job.job_id,
      title: job.job_title,
      count: countsByJob[job.job_id] ?? 0,
    }));
  }, [jobCandidates, jobs, selectedJob?.job_id, today]);

  if (isLoading && !data) {
    return (
      <div className="flex h-80 flex-col items-center justify-center gap-3">
        <Loader2 className="size-10 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading dashboard analytics...</p>
      </div>
    );
  }

  if (!data && !isLoading) {
    return (
      <Card className="mx-auto max-w-xl border-destructive/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <Activity className="size-5" />
            Failed to load dashboard
          </CardTitle>
          <CardDescription>
            We could not retrieve dashboard analytics. Please verify your connection and try again.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={fetchJobStats}>Retry</Button>
        </CardContent>
      </Card>
    );
  }

  const maxTodayCount = Math.max(1, ...todayActivity.map((item) => item.count));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Dashboard Overview</h2>
          <p className="text-sm text-muted-foreground">
            Live funnel insights for <span className="font-medium text-foreground">{displayMetrics.title}</span>.
          </p>
        </div>
        <Badge variant="outline" className="gap-1.5">
          <Calendar className="size-3.5" />
          {new Date().toLocaleDateString()}
        </Badge>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatTile
          title="Total Applications"
          value={displayMetrics.applied}
          icon={FileText}
          description="All candidate applications received"
          loading={isLoading}
        />
        <StatTile
          title="Under Review"
          value={displayMetrics.underReview}
          icon={TrendingUp}
          description="Profiles currently in screening"
          loading={isLoading}
        />
        <StatTile
          title="Interviewed"
          value={displayMetrics.interviewed}
          icon={Activity}
          description="Candidates moved to interview rounds"
          loading={isLoading}
        />
        <StatTile
          title="Shortlisted"
          value={displayMetrics.shortlisted}
          icon={CheckSquare}
          description="Candidates shortlisted for next steps"
          loading={isLoading}
        />
        <StatTile
          title="Rejected"
          value={displayMetrics.rejected}
          icon={XSquare}
          description="Applications closed after evaluation"
          loading={isLoading}
        />
        <StatTile
          title="Hired / Onboarded"
          value={displayMetrics.hired}
          icon={Users}
          description="Successful hiring outcomes"
          loading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="space-y-6 xl:col-span-8">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Candidate Funnel (Active Jobs)</CardTitle>
              <CardDescription>Click a job row to inspect candidate stages.</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead>
                  <tr className="border-b text-xs uppercase text-muted-foreground">
                    <th className="px-3 py-2 text-left font-medium">Job</th>
                    {stageConfig.map((stage) => (
                      <th key={stage.key} className="px-3 py-2 text-center font-medium">
                        {stage.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeJobs.length === 0 ? (
                    <tr>
                      <td colSpan={stageConfig.length + 1} className="py-10 text-center text-sm text-muted-foreground">
                        No active jobs available.
                      </td>
                    </tr>
                  ) : (
                    activeJobs.map((job) => {
                      const selected = job.job_id === selectedJobId;

                      return (
                        <tr
                          key={job.job_id}
                          onClick={() => setSelectedJobId(job.job_id)}
                          className={cn(
                            'cursor-pointer border-b transition-colors hover:bg-muted/40',
                            selected && 'bg-muted'
                          )}
                        >
                          <td className="px-3 py-2">
                            <div className="flex flex-col">
                              <span className="font-medium">{job.job_title}</span>
                              <span className="text-xs text-muted-foreground">{job.interview_rounds} interview rounds</span>
                            </div>
                          </td>
                          {stageConfig.map((stage) => {
                            if (!isRoundEnabled(job, stage.key)) {
                              return (
                                <td key={stage.key} className="px-3 py-2 text-center text-xs text-muted-foreground">
                                  N/A
                                </td>
                              );
                            }

                            const count = job[stage.key] as number;
                            return (
                              <td key={stage.key} className="px-3 py-2 text-center">
                                {count > 0 ? (
                                  <Badge variant="secondary" className="font-medium">
                                    {count}
                                  </Badge>
                                ) : (
                                  <span className="text-xs text-muted-foreground">-</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </CardContent>
          </Card>

          {selectedJob && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="size-4" />
                  {selectedJob.job_title}
                </CardTitle>
                <CardDescription>Stage-level candidate inspection for the selected job.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {stageConfig.map((stage) => {
                  if (!isRoundEnabled(selectedJob, stage.key)) {
                    return null;
                  }

                  const count = selectedJob[stage.key] as number;
                  const candidatesForStage = jobCandidates.filter((candidate) => candidateBelongsToStage(candidate, stage.key));

                  return (
                    <details key={stage.key} className="rounded-lg border bg-muted/20">
                      <summary className="flex cursor-pointer items-center justify-between px-4 py-3">
                        <div className="inline-flex items-center gap-2">
                          <span className="font-medium">{stage.label}</span>
                          <Badge variant="outline">{count}</Badge>
                        </div>
                        <ChevronDown className="size-4 text-muted-foreground" />
                      </summary>
                      <div className="border-t px-4 py-3">
                        {candidatesLoading ? (
                          <div className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="size-4 animate-spin" />
                            Loading candidates...
                          </div>
                        ) : candidatesForStage.length === 0 ? (
                          <p className="text-sm text-muted-foreground">No candidates currently in this stage.</p>
                        ) : (
                          <ul className="space-y-2">
                            {candidatesForStage.slice(0, 50).map((candidate, index) => (
                              <li key={`${stage.key}-${index}`} className="flex items-center justify-between rounded-md border bg-background px-3 py-2">
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-medium">
                                    {candidate?.name ?? candidate?.full_name ?? candidate?.profile_name ?? 'Unnamed candidate'}
                                  </p>
                                  <p className="truncate text-xs text-muted-foreground">
                                    {candidate?.email ?? candidate?.profile_email ?? candidate?.contact ?? ''}
                                  </p>
                                </div>
                                <Badge variant="secondary" className="max-w-40 truncate">
                                  {String(candidate?.current_round ?? candidate?.currentRound ?? candidate?.round ?? 'Stage')}
                                </Badge>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </details>
                  );
                })}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6 xl:col-span-4">
          <Card>
            <CardHeader>
              <CardTitle>Job Status Summary</CardTitle>
              <CardDescription>Active versus paused roles on the career page.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Active Jobs</span>
                  <span className="font-semibold">{data?.active_jobs ?? 0}</span>
                </div>
                <Progress value={data?.total_jobs ? ((data.active_jobs / data.total_jobs) * 100) : 0} />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Inactive Jobs</span>
                  <span className="font-semibold">{Math.max(0, (data?.total_jobs ?? 0) - (data?.active_jobs ?? 0))}</span>
                </div>
                <Progress
                  value={
                    data?.total_jobs
                      ? (((data.total_jobs - data.active_jobs) / data.total_jobs) * 100)
                      : 0
                  }
                  className="[&_[data-slot=progress-indicator]]:bg-amber-500"
                />
              </div>

              <div className="rounded-lg border bg-muted/30 p-3 text-sm">
                <span className="text-muted-foreground">Total Job Posts</span>
                <p className="text-xl font-semibold">
                  <NumberTicker value={data?.total_jobs ?? 0} />
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Most Applied Jobs</CardTitle>
              <CardDescription>Top 5 roles by candidate volume.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {mostAppliedJobs.map((job) => (
                <div key={job.job_id} className="flex items-center justify-between gap-3 rounded-md border bg-muted/20 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{job.job_title}</p>
                    <p className="text-xs text-muted-foreground">
                      {job.is_active ? 'Active' : 'Inactive'} - {job.interview_rounds} rounds
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">{job.total_applications}</Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedJobId(job.job_id)}
                    >
                      Show
                    </Button>
                  </div>
                </div>
              ))}
              {mostAppliedJobs.length === 0 && <p className="text-sm text-muted-foreground">No jobs available.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Today's Activity</CardTitle>
              <CardDescription>New candidate additions by job.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {todayActivity.slice(0, 7).map((item) => (
                <div key={item.id} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="truncate">{item.title}</span>
                    <span className="font-medium text-muted-foreground">{item.count}</span>
                  </div>
                  <Progress value={(item.count / maxTodayCount) * 100} />
                </div>
              ))}
              {todayActivity.every((item) => item.count === 0) && (
                <p className="text-sm text-muted-foreground">
                  No candidate timestamp updates were found for today.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
