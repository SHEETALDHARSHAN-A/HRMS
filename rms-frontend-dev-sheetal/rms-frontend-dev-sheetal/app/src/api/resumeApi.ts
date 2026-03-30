// src/api/resumeApi.ts
import axiosInstance from "./axiosConfig";

/**
 * Uploads resume file for a specific job ID.
 * @param jobId The ID of the job post.
 * @param file The File object to upload.
 */

export const uploadResume = async (jobId: string, file: File) => {
  try {
    const formData = new FormData();
    formData.append("files", file);
    // Attach uploader id when available for server-side tracing/ownership
    try {
      const storedUserId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
      if (storedUserId) {
        formData.append('user_id', storedUserId);
      } else {
        const rawUser = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (rawUser) {
          const parsed = JSON.parse(rawUser as string);
          const candidateId = parsed?.user_id ?? parsed?.id ?? parsed?.userId ?? parsed?.uid;
          if (candidateId) formData.append('user_id', String(candidateId));
        }
      }
    } catch {
      // ignore parsing errors
    }

    // Endpoint: POST /v1/upload-resumes/{job_id}
    const response = await axiosInstance.post(`/upload-resumes/${jobId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    
    return { success: true, data: response.data };
  } catch (err: any) {
    console.error("Resume upload failed:", err.response?.data || err.message);
    return { 
      success: false, 
      error: err.response?.data?.message || err.message || "An unknown error occurred during upload." 
    };
  }
};

export const BulkUpload = async (jobId: string, files: File[]) => {
  try {
    const formData = new FormData();
    files.forEach(file => {
      formData.append("files", file);
    });
    // Attach uploader id when available (helps backend associate uploads)
    try {
      const storedUserId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
      if (storedUserId) {
        formData.append('user_id', storedUserId);
      } else {
        const rawUser = localStorage.getItem('user') || sessionStorage.getItem('user');
        if (rawUser) {
          const parsed = JSON.parse(rawUser as string);
          const candidateId = parsed?.user_id ?? parsed?.id ?? parsed?.userId ?? parsed?.uid;
          if (candidateId) formData.append('user_id', String(candidateId));
        }
      }
    } catch {
      // ignore parsing errors
    }

    const response = await axiosInstance.post(`/upload-resumes/${jobId}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    // ✅ SOLUTION: Change the condition to check for the essential `task_id`.
    if (response.data.success && response.data.data?.task_id) {
      return { success: true, data: response.data.data };
    } else {
      // The error message now correctly reflects that the task ID was not received.
      return { success: false, error: "Failed to get a task ID from the server." };
    }
  } catch (err: any) {
    return {
      success: false,
      error: err.response?.data?.message || "Failed to start bulk upload."
    };
  }
};