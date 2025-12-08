// rms-frontend-dev-sheetal/app/src/api/careerApi.ts
import axiosInstance from "../api/axiosConfig";
import type { StandardResponse } from '../types/api';

// --- Data Types for Career Flow ---

/**
 * Data sent to request an OTP for a job application.
 */
export interface ApplicationOTPRequest {
  jobId: string;
  email: string;
  firstName: string;
  lastName: string;
  phone: string;
}

/**
 * Standard API response shape for the OTP request.
 */
interface OTPResponse extends StandardResponse {
  status?: number; // Add status for error handling
  error?: string;
}

/**
 * 1. Send Application OTP
 * * Calls the backend to validate candidate details, check for duplicate applications,
 * and send an OTP if the application is unique.
 */
export const sendApplicationOTP = async (data: ApplicationOTPRequest): Promise<OTPResponse> => {
  try {
    const response = await axiosInstance.post<StandardResponse>(`/career/apply/send-otp`, data);
    
    if (response.data.success) {
      return { ...response.data, status: response.status };
    } else {
      return { ...response.data, status: response.status, error: response.data.message };
    }
  } catch (err: any) {
    // Handle specific 409 Conflict error for duplicates
    if (err.response && err.response.status === 409) {
      return {
        success: false,
        status: 409,
        status_code: 409,
        message: err.response.data?.message || 'You have already applied for this job.',
        error: err.response.data?.message || 'You have already applied for this job.',
      };
    }
    // Handle other errors
    return {
      success: false,
      status: err.response?.status || 500,
      status_code: err.response?.status || 500,
      message: err.response?.data?.message || err.message,
      error: err.response?.data?.message || err.message,
    };
  }
};

/**
 * 2. Verify OTP and Submit Application
 * * Sends all application data, including the resume file and OTP,
 * to the backend for final verification and submission.
 * This must be sent as FormData.
 */
export const verifyAndSubmitApplication = async (formData: FormData): Promise<OTPResponse> => {
  try {
    const response = await axiosInstance.post<StandardResponse>(
      `/career/apply/verify-and-submit`, 
      formData, 
      {
        headers: {
          // Let axios handle the multipart/form-data boundary
          "Content-Type": "multipart/form-data",
        },
      }
    );
    
    if (response.data.success) {
      return { ...response.data, status: response.status };
    } else {
      return { ...response.data, status: response.status, error: response.data.message };
    }
  } catch (err: any) {
    // Handle 400 Bad Request (e.g., invalid OTP)
    if (err.response && err.response.status === 400) {
      return {
        success: false,
        status: 400,
        status_code: 400,
        message: err.response.data?.message || 'Invalid or expired OTP.',
        error: err.response.data?.message || 'Invalid or expired OTP.',
      };
    }
    // Handle other errors
    return {
      success: false,
      status: err.response?.status || 500,
      status_code: err.response?.status || 500,
      message: err.response?.data?.message || err.message,
      error: err.response?.data?.message || err.message,
    };
  }
};