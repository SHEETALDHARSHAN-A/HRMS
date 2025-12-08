// import React, { createContext, useContext } from 'react';

// export type VerifyResult = { success: boolean; message?: string; status?: number };

// export type AuthContextType = {
//   loading: boolean;
//   error?: string | null;
//   userEmail?: string | null;
//   verifyOTP: (otp: string) => Promise<VerifyResult>;
//   resendOTP: () => Promise<VerifyResult>;
//   goBackToForm: () => void;
// };

// const AuthContext = createContext<AuthContextType | undefined>(undefined);

// export const useAuthContext = () => {
//   const ctx = useContext(AuthContext);
//   if (!ctx) throw new Error('useAuthContext must be used within an AuthProvider');
//   return ctx;
// };

// export const AuthProvider: React.FC<{ value: AuthContextType; children: React.ReactNode }> = ({ value, children }) => {
//   return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
// };

// export default AuthContext;


// src/context/AuthContext.tsx (No logic change needed, confirms structure)
import React, { createContext, useContext } from 'react';
import { useAuth } from '../hooks/useAuth';

export type VerifyResult = { success: boolean; message?: string; status?: number };

// Extend the original AuthContextType to include fields from useAuth
export type AuthContextType = {
  loading: boolean;
  error?: string | null;
  userEmail?: string | null;
  verifyOTP: (otp: string) => Promise<VerifyResult>;
  resendOTP: () => Promise<VerifyResult>;
  goBackToForm: () => void;
  // Add fields from useAuth hook
  currentStep?: string;
  signIn?: (email: string, rememberMe: boolean) => Promise<any>;
  resetFlow?: () => void;
  switchToSignIn?: () => void;
  switchToSignUp?: () => void;
  isSignUpFlow?: boolean;
  logout?: () => Promise<any>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuthContext = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within an AuthProvider');
  return ctx;
};

export const AuthProvider: React.FC<{ value?: AuthContextType; children: React.ReactNode }> = ({ value, children }) => {
  const authHook = useAuth();
  
  // If no value is provided, use the useAuth hook internally
  const contextValue = value || {
    loading: authHook.loading,
    error: authHook.error,
    userEmail: authHook.userEmail,
    verifyOTP: authHook.verifyOTP,
    resendOTP: authHook.resendOTP,
    goBackToForm: authHook.goBackToForm,
    currentStep: authHook.currentStep,
    signIn: authHook.signIn,
    resetFlow: authHook.resetFlow,
    switchToSignIn: authHook.switchToSignIn,
    switchToSignUp: authHook.switchToSignUp,
    isSignUpFlow: authHook.isSignUpFlow,
    logout: authHook.logout,
  };
  
  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};

export default AuthContext;