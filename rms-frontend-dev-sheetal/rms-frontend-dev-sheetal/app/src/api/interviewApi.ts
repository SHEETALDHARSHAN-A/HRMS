import axiosInstance from "./axiosConfig";

interface ValidateTokenPayload {
  email: string;
  token: string;
}

interface VerifyOtpPayload extends ValidateTokenPayload {
  otp: string;
}

interface ValidateTokenResponse {
  message: string;
}

interface VerifyOtpResponse {
  livekit_url: string;
  livekit_token: string;
  room_name: string;
  participant_name: string;
}

/**
 * API service for handling the public interview authentication flow.
 * Note: These endpoints do not require an auth token.
 */

// We create a new axios instance for public routes
const publicAxiosInstance = axiosInstance.create();

// Remove the auth interceptor for this instance
publicAxiosInstance.interceptors.request.use((config) => {
  delete config.headers.Authorization;
  return config;
});


export const interviewApi = {
  /**
   * Step 1: Validate email and token. Triggers an OTP send.
   */
  validateToken: (
    payload: ValidateTokenPayload
  ): Promise<ValidateTokenResponse> => {
    return publicAxiosInstance
      .post("/interview/validate-token", payload)
      .then((res) => res.data);
  },

  /**
   * Step 2: Verify the OTP. Returns LiveKit credentials on success.
   */
  verifyOtp: (payload: VerifyOtpPayload): Promise<VerifyOtpResponse> => {
    return publicAxiosInstance
      .post("/interview/verify-otp", payload)
      .then((res) => res.data);
  },
};