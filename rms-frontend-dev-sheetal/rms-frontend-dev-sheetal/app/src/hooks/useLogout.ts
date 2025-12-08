import { useState } from 'react';
import { authService } from '../services/authService';
import { clearAllAuthData } from '../utils/authUtils';
import MultiAccountManager from '../utils/multiAccountManager';

export const useLogout = () => {
  const [loading, setLoading] = useState(false);

  const logout = async () => {
    setLoading(true);
    
    try {
      // Call backend logout endpoint (clears HTTP-only cookies)
      const response = await authService.logout();
      
      // Clear current tab session from multi-account manager
      const accountManager = MultiAccountManager.getInstance();
      accountManager.clearCurrentSession();
      
      // Also clear legacy storage data
      clearAllAuthData(false);
      
      // Redirect to auth page
      window.location.href = '/auth';
      
      return { success: true, message: response.message || 'Logged out successfully' };
      
    } catch (error) {
      // Even if backend fails, clear current tab session
      const accountManager = MultiAccountManager.getInstance();
      accountManager.clearCurrentSession();
      clearAllAuthData(false);
      
      window.location.href = '/auth';
      
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Logout failed' 
      };
    } finally {
      setLoading(false);
    }
  };

  return { logout, loading };
};

export default useLogout;