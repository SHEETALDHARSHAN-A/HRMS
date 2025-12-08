// Utility functions for authentication management

/**
 * Optional function to broadcast logout event to all tabs
 * This triggers the storage event listener in other tabs
 */
export const broadcastLogout = (allTabs: boolean = false): void => {
  if (allTabs) {
    // Set a logout flag in localStorage to trigger storage event in other tabs
    localStorage.setItem('logout-event', Date.now().toString());
    // Remove it immediately (the event is already dispatched)
    localStorage.removeItem('logout-event');
  }
  // If not broadcasting to all tabs, we just handle the current tab logout
};

/**
 * Clears all authentication-related data from storage
 * This includes localStorage items, sessionStorage items, and cookies
 * @param clearSharedStorage - Whether to clear localStorage (shared across tabs). Default: false for better multi-account support
 */
export const clearAllAuthData = (clearSharedStorage: boolean = false): void => {
  // Always clear sessionStorage (current tab only)
  sessionStorage.removeItem('user');
  sessionStorage.removeItem('userRole');
  sessionStorage.removeItem('authToken');
  sessionStorage.removeItem('refreshToken');
  sessionStorage.removeItem('authEmail');
  sessionStorage.removeItem('authStep');
  sessionStorage.removeItem('rememberMe');
  sessionStorage.removeItem('user_id');
  
  // Only clear localStorage if explicitly requested (for complete logout)
  if (clearSharedStorage) {
    localStorage.removeItem('user');
    localStorage.removeItem('userRole');
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('authEmail');
    localStorage.removeItem('rememberMe');
    localStorage.removeItem('user_id');
  }
  
  // Clear all cookies (especially authentication cookies)
  document.cookie.split(";").forEach((cookie) => {
    const cookieName = cookie.split("=")[0].trim();
    // Set cookie to expire in the past to delete it
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname};`;
  });

  console.log('✅ Authentication data cleared for current tab', clearSharedStorage ? '(including shared storage)' : '');
};

/**
 * Force logout and redirect to auth page
 * @param clearAllTabs - Whether to clear authentication for all tabs/windows. Default: false for better multi-account support
 */
export const forceLogout = (clearAllTabs: boolean = false): void => {
  clearAllAuthData(clearAllTabs);
  window.location.href = '/auth';
};

/**
 * Check if user is authenticated
 * Prioritizes sessionStorage (tab-specific) over localStorage for better multi-account support
 */
export const isAuthenticated = (): boolean => {
  // Check sessionStorage first (tab-specific)
  let user = sessionStorage.getItem('user');
  
  // If not in sessionStorage, check localStorage (legacy/remember me)
  if (!user) {
    user = localStorage.getItem('user');
    // If found in localStorage and remember me is set, migrate to sessionStorage
    const rememberMe = localStorage.getItem('rememberMe') === 'true';
    if (user && rememberMe) {
      sessionStorage.setItem('user', user);
    }
  }
  
  return !!user;
};

/**
 * Get current user data - preferring sessionStorage over localStorage
 * Better supports multiple accounts by using tab-specific storage
 */
export const getCurrentUser = (): any | null => {
  try {
    // First check sessionStorage (tab-specific)
    let user = sessionStorage.getItem('user');
    
    // If not found in sessionStorage, fall back to localStorage (remember me / legacy)
    if (!user) {
      user = localStorage.getItem('user');
      
      // If found in localStorage and remember me is enabled, migrate to sessionStorage for this tab
      const rememberMe = localStorage.getItem('rememberMe') === 'true';
      if (user && rememberMe) {
        sessionStorage.setItem('user', user);
        // Keep in localStorage for other tabs if remember me is enabled
      }
    }
    
    return user ? JSON.parse(user) : null;
  } catch (error) {
    console.error('Error parsing user data:', error);
    // Clear corrupted data
    sessionStorage.removeItem('user');
    return null;
  }
};

/**
 * Set user data for the current tab only (helps with multi-account support)
 * @param userData - User data to store
 * @param rememberMe - Whether to persist across browser restarts
 */
export const setCurrentUserForTab = (userData: any, rememberMe: boolean = false): void => {
  try {
    const userDataString = JSON.stringify(userData);
    
    // Always set in sessionStorage for current tab
    sessionStorage.setItem('user', userDataString);
    sessionStorage.setItem('userRole', userData.role || '');
    sessionStorage.setItem('user_id', userData.user_id || '');
    
    // Only set in localStorage if remember me is enabled
    if (rememberMe) {
      localStorage.setItem('user', userDataString);
      localStorage.setItem('userRole', userData.role || '');
      localStorage.setItem('user_id', userData.user_id || '');
      localStorage.setItem('rememberMe', 'true');
    } else {
      // Clear remember me flag if not requested
      localStorage.removeItem('rememberMe');
    }
    
    console.log('✅ User data set for current tab', rememberMe ? '(with remember me)' : '');
  } catch (error) {
    console.error('Error storing user data:', error);
  }
};
