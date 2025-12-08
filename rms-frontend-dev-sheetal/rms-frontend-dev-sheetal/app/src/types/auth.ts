export interface User {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;  // Changed from 'roles' to 'role' to match backend
  remember_me_expire_days?: number;
}

export interface SignUpData {
  firstName: string;
  lastName: string;
  email: string;
}

export interface SignInData {
  email: string;
  rememberMe: boolean;
}

export interface OTPVerificationData {
  email: string;
  otp: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  data?: User & { token?: string };
  error?: string; 
}