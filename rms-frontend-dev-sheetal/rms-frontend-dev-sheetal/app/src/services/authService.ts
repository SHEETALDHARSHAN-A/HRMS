import axiosInstance from '../api/axiosConfig';
import { AUTH_CONFIG } from '../constants/auth';
import type { AuthResponse } from '../types/auth';

// Define a type for the email check response data
export interface EmailCheckResponse {
  success: boolean;
  message: string;
  data?: {
    is_available: boolean; 
    user_status: 'EXIST' | 'NOT_EXIST' | 'INVALID_FORMAT';
  };
  error?: string;
}

const extractError = (error: any, defaultMsg: string): string => {
  const status = error.response?.status;
  const backendMessage = error.response?.data?.message;

  if (status === 409) {
    return AUTH_CONFIG.ERROR_MESSAGES.USER_EXISTS;
  }
  if (status === 400 && backendMessage?.toLowerCase().includes("not registered")) {
    return AUTH_CONFIG.ERROR_MESSAGES.NOT_REGISTERED;
  }
  if (status === 400 && backendMessage?.toLowerCase().includes("invalid otp")) {
    return AUTH_CONFIG.ERROR_MESSAGES.INVALID_OTP;
  }
  if (error.message === 'Network Error') {
    return AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR;
  }
  return error.message || backendMessage || defaultMsg;
};

class AuthService {
  async signInSendOTP(email: string): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.post<AuthResponse>(
        AUTH_CONFIG.API_ENDPOINTS.SIGN_IN_OTP,
        { email }
      );
      return { success: true, message: response.data.message };
    } catch (error: any) {
      const message = extractError(error, 'Sign in request failed');
      return { 
        success: false, 
        message: message, 
        error: error.message 
      };
    }
  }

  async verifyOTP(email: string, otp: string): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.post<AuthResponse>(
        AUTH_CONFIG.API_ENDPOINTS.VERIFY_OTP,
        { email, otp }
      );
      
      // ✅ FIX: Access the 'data' property of AuthResponse correctly.
      // This assumes the backend returns the User object within a 'data' field 
      // of the top-level AuthResponse structure on successful verification.
      if (response.data.success && response.data.data) {
        return { 
          success: true, 
          message: response.data.message,
          data: response.data.data // This now includes both user info and the token
        };
      } else {
        // Handle cases where verification might succeed but send no data
        return { 
          success: true, 
          message: response.data.message || 'Verification successful, but user data missing.'
        };
      }
    } catch (error: any) {
      const message = extractError(error, 'OTP verification failed');
      return { 
        success: false, 
        message: message, 
        error: error.message 
      };
    }
  }

  /**
   * Fallback check to retrieve authenticated user using server-side cookies.
   * Some environments return no token in the verify-OTP response but set an HTTP-only cookie.
   * This endpoint allows the client to fetch the current user/session after OTP verification.
   */
  async checkCookie(): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.get<AuthResponse>(AUTH_CONFIG.API_ENDPOINTS.CHECK_COOKIE);
      if (response.data.success && response.data.data) {
        return { success: true, message: response.data.message, data: response.data.data };
      }
      return { success: false, message: response.data.message || 'No session data available' };
    } catch (error: any) {
      const message = extractError(error, 'Failed to verify cookie session');
      return { success: false, message, error: error.message };
    }
  }

  async resendOTP(email: string): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.post<AuthResponse>(
        AUTH_CONFIG.API_ENDPOINTS.RESEND_OTP,
        { email }
      );
      return { success: true, message: response.data.message };
    } catch (error: any) {
      const message = extractError(error, 'Failed to resend OTP');
      return { 
        success: false, 
        message: message, 
        error: error.message 
      };
    }
  }

  async logout(): Promise<AuthResponse> {
    try {
      const response = await axiosInstance.get<AuthResponse>(AUTH_CONFIG.API_ENDPOINTS.LOGOUT);
      return response.data;
    } catch (error: any) {
      return { 
        success: false, 
        message: error.message || 'Logout request failed', 
        error: error.message 
      };
    }
  }

  // --- UPDATED METHOD ---
  async checkEmailStatus(email: string): Promise<EmailCheckResponse> {
    try {
      const response = await axiosInstance.get<EmailCheckResponse>(
        AUTH_CONFIG.API_ENDPOINTS.CHECK_EMAIL_STATUS,
        { params: { email } }
      );
      return { 
        success: true, 
        message: response.data.message, 
        data: response.data.data 
      };
    } catch (error: any) {
      const status = error.response?.status;
      const backendMessage = error.response?.data?.message;

      if (status === 409) {
        return {
          success: false,
          message: AUTH_CONFIG.ERROR_MESSAGES.USER_EXISTS,
          data: { is_available: false, user_status: 'EXIST' },
        };
      }
      if (status === 400) {
        return {
          success: false,
          message: AUTH_CONFIG.ERROR_MESSAGES.NOT_REGISTERED,
          data: { is_available: false, user_status: 'NOT_EXIST' },
        };
      }
      // Backend returns 403 when email is not registered (sign-in should be disabled)
      if (status === 403) {
        return {
          success: false,
          message: AUTH_CONFIG.ERROR_MESSAGES.NOT_REGISTERED,
          data: { is_available: false, user_status: 'NOT_EXIST' },
        };
      }
      if (backendMessage?.toLowerCase().includes("invalid format")) {
        return {
          success: false,
          message: AUTH_CONFIG.ERROR_MESSAGES.GENERIC_ERROR,
          data: { is_available: false, user_status: 'INVALID_FORMAT' },
        };
      }
      if (error.message === 'Network Error') {
        return {
          success: false,
          message: AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR,
          error: error.message,
          data: { is_available: false, user_status: 'EXIST' },
        };
      }
      // Default fallback for other errors
      const message = extractError(error, AUTH_CONFIG.ERROR_MESSAGES.GENERIC_ERROR);
      return {
        success: false,
        message,
        error: error.message,
        data: { is_available: false, user_status: 'EXIST' },
      };
    }
  }
}

export const authService = new AuthService();