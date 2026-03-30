// src/hooks/useRecruitmentData.ts
import { useState, useEffect, useCallback } from 'react';
import { useToast } from '../context/ModalContext';
import { getJobRoundOverview, getCandidatesForRound } from '../api/recruitmentApi';
import type { JobWithRounds, Candidate, RoundOverview } from '../api/recruitmentApi';

export const useRecruitmentData = () => {
    const [jobs, setJobs] = useState<JobWithRounds[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
    const [selectedRoundId, setSelectedRoundId] = useState<string | null>(null);
    const [roundCandidates, setRoundCandidates] = useState<Candidate[]>([]);
    const [candidatesLoading, setCandidatesLoading] = useState(false);
    const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
    const { showToast } = useToast();

    // 1. Fetch and Group Job/Round Overview
    const fetchJobs = useCallback(async () => {
        setIsLoading(true);
        try {
            const overview = await getJobRoundOverview();
            if (overview.success && overview.data) {
                // Group the flattened list into jobs with nested rounds
                const jobsMap = new Map<string, JobWithRounds>();
                overview.data.job_round_overview.forEach(round => {
                    if (!jobsMap.has(round.job_id)) {
                        jobsMap.set(round.job_id, {
                            job_id: round.job_id,
                            job_title: round.job_title,
                            total_applied: 0,
                            rounds: [] as RoundOverview[]
                        });
                    }
                    jobsMap.get(round.job_id)?.rounds.push(round);
                });
                
                const finalJobs = Array.from(jobsMap.values()).map(job => {
                    job.rounds.sort((a, b) => a.round_order - b.round_order);
                    // Total candidates is the count from the first round (Initial Screening)
                    job.total_applied = job.rounds[0]?.total_candidates ?? 0;
                    return job;
                });

                setJobs(finalJobs);
            } else {
                showToast(overview.error || 'Failed to load job overview.', 'error');
            }
        } catch (error: any) {
            showToast(error.message || 'Error fetching job overview.', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [showToast]);

    // 2. Fetch Candidates for a specific round
    const fetchCandidates = useCallback(async (jobId: string, roundId: string) => {
        setCandidatesLoading(true);
        try {
            const candidates = await getCandidatesForRound(jobId, roundId);
            if (candidates.success) {
                setRoundCandidates(candidates.data ?? []);
            } else {
                showToast(candidates.error || 'Failed to load candidates.', 'error');
                setRoundCandidates([]);
            }
        } catch (error: any) {
            showToast(error.message || 'Error fetching candidates.', 'error');
            setRoundCandidates([]);
        } finally {
            setCandidatesLoading(false);
        }
    }, [showToast]);

    useEffect(() => {
        fetchJobs();
    }, [fetchJobs]);

    // 3. Handlers for UI interaction
    const handleJobToggle = useCallback((jobId: string) => {
        setExpandedJobId(prev => {
            if (prev === jobId) {
                setSelectedRoundId(null);
                setRoundCandidates([]);
                return null;
            } else {
                const job = jobs.find(j => j.job_id === jobId);
                const firstRound = job?.rounds[0]?.round_id ?? null;
                setSelectedRoundId(firstRound);
                setRoundCandidates([]); 
                if (firstRound) {
                    fetchCandidates(jobId, firstRound);
                }
                return jobId;
            }
        });
    }, [jobs, fetchCandidates]);

    const handleRoundChange = useCallback((jobId: string, roundId: string) => {
        setSelectedRoundId(roundId);
        fetchCandidates(jobId, roundId);
    }, [fetchCandidates]);

    return {
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
    };
};