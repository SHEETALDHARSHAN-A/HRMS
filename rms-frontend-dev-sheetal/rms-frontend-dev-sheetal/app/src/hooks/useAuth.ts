// rms-frontend-demo/app/src/hooks/useAuth.ts
// (Fully corrected for accountManager scope error)

import { useState, useCallback, useEffect } from 'react';
import { authService } from '../services/authService';
import { AUTH_CONFIG } from '../constants/auth';
import type { AuthResponse, AuthData } from '../types/auth';
import { clearAllAuthData, broadcastLogout } from '../utils/authUtils';
import MultiAccountManager from '../utils/multiAccountManager';
import { useUserUpdate } from '../context/UserContext';

// Keys for sessionStorage persistence
const EMAIL_KEY = 'authEmail';
const STEP_KEY = 'authStep';

// Helper function to read initial state from session storage
const getInitialState = () => {
    const persistedEmail = localStorage.getItem('rememberMe') === 'true' ? localStorage.getItem('authEmail') || '' : '';
    const persistedStep = persistedEmail ? AUTH_CONFIG.AUTH_STEPS.VERIFY_OTP : AUTH_CONFIG.AUTH_STEPS.SIGN_IN;

    return {
        email: persistedEmail,
        step: persistedStep,
    };
};

export const useAuth = () => {
  const initialState = getInitialState();
  const updateUser = useUserUpdate();
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(initialState.step);
  const [userEmail, setUserEmail] = useState(initialState.email);
  const [isSignUpFlow, setIsSignUpFlow] = useState(false);

  // 💡 FIX 1: Instantiate the manager at the top level of the hook
  // This makes it available to all functions within useAuth
  const accountManager = MultiAccountManager.getInstance();

  const updateStateAndPersist = useCallback((email: string, step: string) => {
    setUserEmail(email);
    setCurrentStep(step);
    sessionStorage.setItem(EMAIL_KEY, email);
    sessionStorage.setItem(STEP_KEY, step);
  }, []);

  const resetFlow = useCallback(() => {
    setCurrentStep(AUTH_CONFIG.AUTH_STEPS.SIGN_IN);
    setUserEmail('');
    setError(null);
    setIsSignUpFlow(false);
    sessionStorage.removeItem(EMAIL_KEY);
    sessionStorage.removeItem(STEP_KEY);
  }, []);

  // --- signIn (No changes) ---
  const signIn = async (email: string, rememberMe: boolean): Promise<AuthResponse> => {
    setLoading(true);
    setError(null);

    try {
      const response = await authService.signInSendOTP(email) as AuthResponse & { data?: { remember_me_expire_days?: number } };

      if (response.success === true) {
        if (rememberMe) {
          const expirationTime = Date.now() + (response.data?.remember_me_expire_days || 7) * 24 * 60 * 60 * 1000;
          localStorage.setItem('rememberMe', 'true');
          localStorage.setItem('authEmail', email);
          localStorage.setItem('rememberMeExpiry', expirationTime.toString());
        } else {
          sessionStorage.setItem('authEmail', email);
          localStorage.removeItem('rememberMe');
          localStorage.removeItem('authEmail');
          localStorage.removeItem('rememberMeExpiry');
        }

        updateStateAndPersist(email, AUTH_CONFIG.AUTH_STEPS.VERIFY_OTP);
        setIsSignUpFlow(false);
        return { success: true, message: response.message };
      } else {
        const rawMsg = response.message || response.error || 'Sign in failed';
        const isGenericServerError = /sign in request failed|bad request|400|failed to send otp|something went wrong/i.test(rawMsg);
        const errorMsg = isGenericServerError ? 'Something went wrong while requesting OTP. Please try again.' : rawMsg;
        setError(errorMsg);
        return { success: false, message: errorMsg, error: errorMsg };
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Sign in failed';
      setError(errorMessage);
      return { success: false, message: errorMessage, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const verifyOTP = async (otp: string): Promise<AuthResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authService.verifyOTP(userEmail, otp);
      const responseData = response.data as any;

      console.log('🔍 OTP Response Debug:', {
        success: response.success,
        hasData: !!responseData,
        dataKeys: responseData ? Object.keys(responseData) : [],
        token: responseData?.token ? 'present' : 'missing',
        userId: responseData?.user_id || 'missing',
        role: responseData?.role || 'missing',
        user_role: responseData?.user_role || 'missing'
      });

      if (response.success === true && responseData) {
        const authToken = responseData.token || '';
        const userRole = responseData.role || responseData.user_role;
        let userId = responseData.user_id;
        
        if (!userId && authToken) {
          try {
            const tokenPayload = JSON.parse(atob(authToken.split('.')[1]));
            userId = tokenPayload.user_id || tokenPayload.sub;
            console.log('🔧 Extracted user ID from token sub field:', userId);
          } catch (e) {
            console.warn('🔧 Failed to extract user ID from token:', e);
          }
        }
        
        const userData = {
          ...responseData,
          role: userRole,
          user_id: userId
        };
        
        // 💡 FIX 2: Remove the local const definition
        // We now use the accountManager defined at the top of the hook
        try {
          accountManager.setCurrentSession(
            authToken,
            userData,
            userRole || '',
            userId || ''
          );
          
          sessionStorage.removeItem(EMAIL_KEY);
          sessionStorage.removeItem(STEP_KEY);
          updateUser(userData);

        } catch (sessionError) {
          console.error('❌ Failed to store session:', sessionError);
          setError('Failed to save login session. Please try again.');
          return { success: false, message: 'Session storage failed' };
        }

        console.log(`🚀 OTP verification successful. Role: '${userRole}'. Redirecting...`);
        
        setTimeout(() => {
          if (userRole === 'ADMIN' || userRole === 'SUPER_ADMIN' || userRole === 'HR') {
            window.location.href = '/dashboard';
          } else {
            window.location.href = '/career-page';
          }
        }, 100);

        return { success: true, message: response.message };
      
      } else if (response.success === true && !responseData) {
        console.warn('🔍 verifyOTP returned success but no data. Falling back to checkCookie');
        const cookieResp = await authService.checkCookie();

        if (cookieResp.success && cookieResp.data) {
          const cbData = cookieResp.data as any;
          const cbUserRole = cbData.role || cbData.user_role || '';
          const cbUserId = cbData.user_id || cbData.userId || '';
          
          const cbUser = { 
            ...cbData,
            role: cbUserRole,
            user_id: cbUserId
          };
          
          const cbToken = cbData.token || ''; 

          // 💡 FIX 2 (bis): Also remove the local const definition here
          try {
            accountManager.setCurrentSession(
              cbToken,
              cbUser,
              cbUserRole,
              cbUserId
            );
            
            updateUser(cbUser);

          } catch (sessionError) {
            console.error('❌ Cookie fallback session storage failed:', sessionError);
            setError('Failed to save login session. Please try again.');
            return { success: false, message: 'Session storage failed' };
          }          
          
          sessionStorage.removeItem(EMAIL_KEY);
          sessionStorage.removeItem(STEP_KEY);
          
          console.log(`🚀 Cookie fallback successful. Role: '${cbUserRole}'. Redirecting...`);

          setTimeout(() => {
            if (cbUserRole === 'ADMIN' || cbUserRole === 'SUPER_ADMIN' || cbUserRole === 'HR') {
              window.location.href = '/dashboard';
            } else {
              window.location.href = '/career-page';
            }
          }, 100);

          return { success: true, message: cookieResp.message };
        }

        const errorMsg = cookieResp.message || 'OTP verification returned no user data';
        setError(errorMsg);
        return { success: false, message: errorMsg };
      
      } else {
        const errorMsg = response.message || response.error || 'OTP verification failed';
        setError(errorMsg);
        return { success: false, message: errorMsg };
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'OTP verification failed';
      setError(errorMessage);
      return { success: false, message: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // --- resendOTP (No changes) ---
  const resendOTP = async (): Promise<AuthResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await authService.resendOTP(userEmail);
      if (response.success === true) {
        return { success: true, message: 'OTP resent successfully' };
      } else {
        const errorMsg = response.message || response.error || 'Failed to resend OTP';
        setError(errorMsg);
        return { success: false, message: errorMsg, error: errorMsg };
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to resend OTP';
      setError(errorMessage);
      return { success: false, message: errorMessage, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // --- Other functions (No changes) ---
  const switchToSignUp = () => {
    setCurrentStep(AUTH_CONFIG.AUTH_STEPS.SIGN_UP);
    sessionStorage.removeItem(STEP_KEY); 
    setError(null);
  };

  const switchToSignIn = () => {
    setCurrentStep(AUTH_CONFIG.AUTH_STEPS.SIGN_IN);
    sessionStorage.removeItem(STEP_KEY); 
    setError(null);
  };

  const goBackToForm = () => {
    if (isSignUpFlow) {
      setCurrentStep(AUTH_CONFIG.AUTH_STEPS.SIGN_UP);
    } else {
      setCurrentStep(AUTH_CONFIG.AUTH_STEPS.SIGN_IN);
    }
    sessionStorage.removeItem(STEP_KEY); 
    setError(null);
    setLoading(false);
  }

  const logout = useCallback(async (): Promise<AuthResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      await authService.logout();
    } catch (e) {
      console.warn("Logout API call failed, proceeding with client-side clear.", e);
    }

    broadcastLogout(true);
    clearAllAuthData();
    resetFlow();
    
    localStorage.removeItem('rememberMe');
    localStorage.removeItem('authEmail');
    localStorage.removeItem('rememberMeExpiry');
    
    window.location.href = '/auth';
    
    return { success: true, message: 'Logout successful' };
  }, [resetFlow]);

  // --- useEffect (Changes) ---
  useEffect(() => {
    const rememberMeExpiry = localStorage.getItem('rememberMeExpiry');

    if (rememberMeExpiry && Date.now() > parseInt(rememberMeExpiry, 10)) {
      localStorage.removeItem('rememberMe');
      localStorage.removeItem('authEmail');
      localStorage.removeItem('rememberMeExpiry');
      
      // Now this call is valid because accountManager is in scope
      accountManager.clearCurrentSession(); 
      resetFlow();
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'logout-event') {
        clearAllAuthData();
        resetFlow();
        if (window.location.pathname !== '/auth') {
          window.location.href = '/auth';
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
    // 💡 FIX 3: Add accountManager and resetFlow to the dependency array
  }, [resetFlow, accountManager]);

  
  return {
    loading,
    error,
    currentStep,
    userEmail,
    isSignUpFlow,
    signIn,
    verifyOTP,
    resendOTP,
    logout,
    switchToSignUp,
    switchToSignIn,
    goBackToForm,
    resetFlow
  };
};