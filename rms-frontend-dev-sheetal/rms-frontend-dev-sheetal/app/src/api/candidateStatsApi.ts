import axios from './axiosConfig';

export async function fetchCandidateStats(curationId: string) {
  // axiosConfig already sets baseURL to <BACKEND_URL>/api/v1, so use the relative path here
  const res = await axios.get(`/job-post/candidate-stats/${curationId}`);
  return res.data.data.profile_counts;
}
