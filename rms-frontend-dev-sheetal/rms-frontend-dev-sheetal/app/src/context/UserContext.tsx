import React, { createContext, useContext, useState, useEffect } from 'react';
import type { User } from '../types/auth'; // Use the new User type
import useLogout from '../hooks/useLogout';
import MultiAccountManager from '../utils/multiAccountManager'; 

// Define the shape of the context state
interface UserContextType {
  user: User | null;
  logout: () => Promise<void>; // Expose logout
  updateUser: (userData: User | null) => void; // Add method to update user
}

// Create the context. We keep the default undefined so we can detect missing provider,
// but provide a harmless fallback for consumers when needed.
const UserContext = createContext<UserContextType | undefined>(undefined);

// A safe default returned when the context is missing at runtime.
const SAFE_USER_CONTEXT: UserContextType = {
  user: null,
  logout: async () => {},
  updateUser: () => {},
};

// Helper function to read user from multi-account manager
const getInitialUser = (): User | null => {
  try {
    const accountManager = MultiAccountManager.getInstance();
    const currentSession = accountManager.getCurrentSession();
    
    if (currentSession && currentSession.user) {
      return currentSession.user as User;
    }
    
    return null;
  } catch (error) {
    console.error("Failed to get user data from multi-account manager:", error);
    return null;
  }
};

// Create the provider component
export const UserProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Initialize state from localStorage
  const [user, setUser] = useState<User | null>(getInitialUser());
  const { logout: callLogout } = useLogout(); // Get the powerful logout hook

  // Custom context logout function
  const logout = async () => {
      await callLogout(); // The hook handles clearing storage and redirecting
      setUser(null);
  };

  // Custom context update function
  const updateUser = (userData: User | null) => {
    setUser(userData);
  };
  
  // Update state when multi-account sessions change
  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
        // Handle logout event broadcast from other tabs
        if (event.key === 'logout-event') {
          const accountManager = MultiAccountManager.getInstance();
          const currentSession = accountManager.getCurrentSession();
          // Only logout if this tab doesn't have its own active session
          if (!currentSession) {
            setUser(null);
          }
        }
        
        // REMOVED: Do not listen to multiAccountSessions changes from other tabs
        // Each tab manages its own session independently via sessionStorage
    };

    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  // Removed setUser from value as state is controlled by login/logout flow

  return (
    <UserContext.Provider value={{ user, logout, updateUser }}>
      {children}
    </UserContext.Provider>
  );
};

// Custom hook to easily use the user context
export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    // Instead of throwing (which crashes the whole app), log a helpful warning and
    // return a safe default. This avoids runtime crashes while we trace mounting order
    // issues (e.g., during HMR or an accidental render outside the provider).
    // NOTE: This masks the root cause; prefer fixing the provider mount order.
    // Keep the error message to help developers find the issue in logs.
     
    console.warn('useUser called outside of UserProvider — returning safe default. Ensure components are wrapped by <UserProvider>.');
    return SAFE_USER_CONTEXT;
  }
  return context;
};

// Additional hook to update user context after login
export const useUserUpdate = () => {
  const context = useContext(UserContext);
  if (!context) return () => {};
  
  return context.updateUser;
};