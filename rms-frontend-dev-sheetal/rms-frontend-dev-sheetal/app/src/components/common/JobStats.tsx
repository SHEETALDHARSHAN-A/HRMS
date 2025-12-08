import React, { useEffect, useState } from 'react';
import { fetchCandidateStats } from '../../../src/api/candidateStatsApi';

interface JobStatsProps {
  curationId: string;
}

export const JobStats: React.FC<JobStatsProps> = ({ curationId }) => {
  const [stats, setStats] = useState<{
    applied: number;
    shortlisted: number;
    rejected: number;
    under_review: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCandidateStats(curationId)
      .then((data) => setStats(data))
      .finally(() => setLoading(false));
  }, [curationId]);

  if (loading) return <div>Loading candidate stats...</div>;
  if (!stats) return <div>No stats available.</div>;

  return (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <span>Applied: {stats.applied}</span>
      <span>Shortlisted: {stats.shortlisted}</span>
      <span>Rejected: {stats.rejected}</span>
      <span>Under Review: {stats.under_review}</span>
    </div>
  );
};
