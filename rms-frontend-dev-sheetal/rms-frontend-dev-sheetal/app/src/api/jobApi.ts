// Frontend API wrapper for job-post endpoints (FastAPI backend at http://localhost:8000)
import type { AxiosError } from 'axios';
import axiosInstance from './axiosConfig';

// Generic API result type
export type ApiResult<T> =
  | { success: true; data: T; status?: number }
  | { success: false; error: string; status?: number };

// Interface for search suggestions response
export interface SearchSuggestions {
  job_titles: string[];
  skills: string[];
  locations: string[];
}

// Interface for public job search
export interface PublicJobSearchParams {
  role?: string;
  skills?: string;
  locations?: string;
}

// Helper to normalize API errors into a readable string
const extractApiErrorMessage = (err: unknown): string => {
  if (!err){
    console.error('[API] An unknown error occurred with no error object.');
    return 'An unknown error occurred';
  }
  const maybeAxios = err as AxiosError<any>;
  if (maybeAxios.response) {
    const data = maybeAxios.response.data;
    const status = maybeAxios.response.status;
    let message = `Request failed with status ${status}`;
    if (typeof data === 'string') message = data;
    else if (data?.message) message = String(data.message);
    else if (data?.detail) message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    else {
      try { message = JSON.stringify(data); } catch { message = String(data); }
    }
    console.error(`[API] Server Error (${status}): ${message}`, maybeAxios.response); // <- ADDED LOG
    return message;
  }
  

   
  // Non-response (network / timeout / other)
  // @ts-ignore
  
 const networkMessage = (maybeAxios && maybeAxios.message) || String(err);
  console.error(`[API] Network/Client Error: ${networkMessage}`, err); // <- ADDED LOG
  return networkMessage;
};

// Upload a JD file (PDF/DOCX) to POST /job-post/upload
// Helper: try multiple endpoint paths when backend route prefixes vary (e.g., /api/v1)
const requestWithFallback = async (
  method: 'get' | 'post' | 'patch' | 'delete',
  paths: string[],
  body?: any,
  config?: any
) => {
  let lastError: any = null;
  for (const p of paths) {
    try {
      const response = await (axiosInstance as any)[method](p, body, config);
      return { success: true, response };
    } catch (err: any) {
      lastError = err;
      const status = err?.response?.status ?? null;
      // if not 404, return immediately (auth/validation server error)
      if (status && status !== 404) {
        return { success: false, error: err };
      }
      // otherwise continue to next path
    }
  }
  return { success: false, error: lastError };
};

export const uploadJobJD = async (file: File, options?: { onUploadProgress?: (p: ProgressEvent) => void }): Promise<ApiResult<any>> => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    // common endpoint variants to try
    const paths = [
      '/job-post/upload',
      '/job-posts/upload',
      '/jobs/upload',
    ];

    const { success, response, error } = await requestWithFallback('post', paths, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: options?.onUploadProgress,
    });

    // If any of the attempted endpoints returned a non-404 error,
    // requestWithFallback returns success=false with the last error.
    // Ensure a 401 triggers the global auth flow so the session-ended
    // confirmation modal is shown (covers edge cases where interceptors
    // might have been bypassed).
    if (success) return { success: true, data: response.data, status: response.status };

    // If the error indicates unauthorized, dispatch the global auth-error
    // event so `AuthErrorHandler` shows the login/session-ended modal.
    try {
      const status = error?.response?.status ?? null;
      if (status === 401 || status === 403) {
        window.dispatchEvent(new CustomEvent('auth-error', {
          detail: {
            status,
            message: status === 401 ? 'Your session has expired. Please sign in again.' : 'Access denied. Please sign in again.',
          }
        }));
      }
    } catch (e) {
      // swallow - best-effort only
    }

    throw error;
  } catch (err: any) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// Create or update a job post via POST /job-post/update
export const createOrUpdateJob = async (jobDetails: Record<string, any>): Promise<ApiResult<any>> => {
  try {
  const resp = await axiosInstance.post('/job-post/update', jobDetails, {
      headers: { 'Content-Type': 'application/json' },
    });
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// --- Backwards-compatible wrappers for existing codebase ---
// Previously the project used these function names; keep them to avoid breaking imports.
export const uploadJobPost = async (file: File): Promise<ApiResult<any>> => {
  return uploadJobJD(file);
};

export const updateJobPost = async (jobPostData: any): Promise<ApiResult<any>> => {
  return createOrUpdateJob(jobPostData);
};

// Analyze Job Post (JSON data) - POST /job-post/analyze
export const analyzeJobPost = async (jobPostData: any): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.post('/job-post/analyze', jobPostData, {
      headers: { 'Content-Type': 'application/json' },
    });
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// Get job post by ID - GET /job-post/get-job-by-id/{job_id}
export const getJobPostById = async (jobId: string): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.get(`/job-post/get-job-by-id/${jobId}`);
    // Some backends nest data differently; keep compatibility with prior shape
    const job = resp.data?.data?.job ?? resp.data?.job ?? resp.data;
    return { success: true, data: job, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// Get public job details by ID - GET /job-post/public/job/{job_id}
export const getPublicJobById = async (jobId: string): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.get(`/job-post/public/job/${jobId}`);
    // Some backends nest data differently; keep compatibility with prior shape
    const job = resp.data?.data?.job ?? resp.data?.job ?? resp.data;
    return { success: true, data: job, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// Optional: basic helper to set auth token on axios instance
export const setAuthToken = (token: string | null) => {
  if (token) axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  else delete axiosInstance.defaults.headers.common['Authorization'];
};

export default axiosInstance;

// --- Additional helpers kept for compatibility with existing pages ---
export const getAllJobPosts = async (): Promise<ApiResult<any>> => {
  try {
    const paths = [
      '/job-post/all',
      '/job-posts/get_all_job_posts',
      '/job-posts',
      '/jobs',
    ];
    const { success, response, error } = await requestWithFallback('get', paths);
    if (!success) throw error;
    const resp = response;
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const getActiveJobPosts = async (): Promise<ApiResult<any>> => {
  try {
    const paths = [
      '/job-post/active',
      '/job-posts/public/active-jobs',
      '/jobs/active',
    ];
    const { success, response, error } = await requestWithFallback('get', paths);
    if (!success) throw error;
    const resp = response;
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const deleteJobPost = async (jobId: string): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.delete(`/job-post/delete-job-by-id/${jobId}`);
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const deleteJobPostsBatch = async (jobIds: string[]): Promise<ApiResult<any>> => {
  try {
    // Updated to match the new controller expectation
    const resp = await axiosInstance.post('/job-post/delete-batch', { job_ids: jobIds });
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const toggleJobStatus = async (jobId: string, isActive: boolean): Promise<ApiResult<any>> => {
  try {
    const params = new URLSearchParams({ is_active: String(isActive) });
    const resp = await axiosInstance.patch(`/job-post/${jobId}/toggle-status?${params.toString()}`, {});
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const getCandidateStatsForJob = async (jobId: string): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.get(`/job-post/candidate-stats/${jobId}`);
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const getJobCandidates = async (jobId: string, status?: string): Promise<ApiResult<any>> => {
  try {
    // Correct endpoint: /shortlist/{job_id}/candidates
    const url = status ? `/shortlist/${jobId}/candidates?status=${encodeURIComponent(status)}` : `/shortlist/${jobId}/candidates`;
    const resp = await axiosInstance.get(url);
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// --- Search API functions ---
export const getSearchSuggestions = async (): Promise<ApiResult<SearchSuggestions>> => {
  try {
    const resp = await axiosInstance.get('/job-post/public/search-suggestions');
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

export const searchPublicJobs = async (params: PublicJobSearchParams): Promise<ApiResult<any>> => {
  try {
    const searchParams = new URLSearchParams();
    if (params.role) searchParams.append('role', params.role);
    if (params.skills) searchParams.append('skills', params.skills);
    if (params.locations) searchParams.append('locations', params.locations);
    
    const resp = await axiosInstance.get(`/job-post/public/search?${searchParams.toString()}`);
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// --- New API functions for job ownership separation ---
export const getMyJobPosts = async (): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.get('/job-post/my-jobs');
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    console.log('[API] getMyJobPosts Success Response Payload:', payload);
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    const status = maybe?.response?.status;
    // ... (auth-error event dispatch) ...
    return { success: false, error: extractApiErrorMessage(err), status };
  }
};

export const getAllJobPostsAdmin = async (): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.get('/job-post/all');
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    console.log('[API] getAllJobPostsAdmin Success Response Payload:', payload); // <- ADDED LOG
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

// --- ADD THESE NEW FUNCTIONS ---

/**
 * Fetches only the jobs owned by the current user that are
 * marked with `is_agent_interview = true`.
 * Used by the Agent Hub page.
 */
export const getMyAgentJobs = async (): Promise<ApiResult<any>> => {
  try {
    const resp = await axiosInstance.get('/job-post/my-agent-jobs');
    const payload = resp.data && resp.data.data !== undefined ? resp.data.data : resp.data;
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};

/**
 * Saves the configuration for all rounds of an agent-enabled job.
 * @param jobId The ID of the job being configured
 * @param agentRounds The array of round configuration objects
 */
export const saveAgentConfig = async (jobId: string, agentRounds: any[]): Promise<ApiResult<any>> => {
  try {
    // Backend endpoint expects an object: {"agentRounds": [...]}
    const payload = { agentRounds: agentRounds };
    const resp = await axiosInstance.post(`/agent-config/job/${jobId}`, payload);
    return { success: true, data: resp.data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};