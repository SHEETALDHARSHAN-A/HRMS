// rms-frontend-demo/app/src/utils/multiAccountManager.ts
// (This file now CONSUMES the tabId from axiosConfig.ts)

// 💡 IMPORT the single source of truth for tab management
import { 
  getTokenForCurrentTab, 
  setTokenForCurrentTab, 
  clearTokenForCurrentTab,
  getTabId // <-- Import the one true tabId function
} from '../api/axiosConfig';

interface TabSession {
  tabId: string;
  authToken: string;
  user: any;
  userRole: string;
  user_id: string;
  timestamp: number;
}

class MultiAccountManager {
  private static instance: MultiAccountManager;
  private currentTabId: string;
  private storageKey = 'multiAccountSessions';
  private isDebug = !!import.meta.env.DEV;
  
  constructor() {
    // 💡 FIX 1: Use the imported getTabId() from axiosConfig.
    // This ensures the manager and the API client are 100% in sync.
    this.currentTabId = getTabId(); 
    
    // 💡 FIX 2: The 'beforeunload' listener is permanently removed.
    // It was deleting the session during a redirect.
    
    // Clean up old sessions on startup
    this.cleanupOldSessions();
    
    // Make available globally for debugging (development mode only)
    if (import.meta.env.DEV) {
      (window as any).MultiAccountManager = MultiAccountManager;
    }
  }

  static getInstance(): MultiAccountManager {
    if (!MultiAccountManager.instance) {
      MultiAccountManager.instance = new MultiAccountManager();
    }
    return MultiAccountManager.instance;
  }

  // 💡 REMOVED: generateTabId() and tabIdKey - No longer needed, logic is in axiosConfig.ts

  private getAllSessions(): TabSession[] {
    const sessions = localStorage.getItem(this.storageKey);
    return sessions ? JSON.parse(sessions) : [];
  }

  private saveSessions(sessions: TabSession[]): void {
    localStorage.setItem(this.storageKey, JSON.stringify(sessions));
  }

  private cleanupOldSessions(): void {
    const sessions = this.getAllSessions();
    const now = Date.now();
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours
    
    const validSessions = sessions.filter(session => {
      return now - session.timestamp < maxAge;
    });
    
    this.saveSessions(validSessions);
  }

  private cleanupCurrentTab(): void {
    // This function is now only called by clearCurrentSession()
    const sessions = this.getAllSessions();
    const filteredSessions = sessions.filter(session => session.tabId !== this.currentTabId);
    this.saveSessions(filteredSessions);
  }

  // Store session data for current tab
  setCurrentSession(authToken: string, user: any, userRole: string, user_id: string): void {
    if (this.isDebug) {
      console.log('🔧 setCurrentSession called with:', {
        tabId: this.currentTabId,
        userRole,
        userId: user_id,
      });
    }
    
    if (!authToken) {
      console.error('❌ setCurrentSession called with empty token!');
      throw new Error('Cannot set session without auth token');
    }
    
    const sessions = this.getAllSessions();
    const currentSession: TabSession = {
      // 💡 FIX 3: No typo, and currentTabId is guaranteed correct.
      tabId: this.currentTabId,
      authToken,
      user,
      userRole,
      user_id,
      timestamp: Date.now()
    };

    // Remove any existing session for this tab
    const filteredSessions = sessions.filter(session => session.tabId !== this.currentTabId);
    filteredSessions.push(currentSession);
    
    try {
      this.saveSessions(filteredSessions);
      
      // Use the imported function to store the token
      setTokenForCurrentTab(authToken);
      
      // Verify save...
      const verifyToken = getTokenForCurrentTab();
      const verifySessions = this.getAllSessions();
      const verifySession = verifySessions.find(s => s.tabId === this.currentTabId);
      
      if (!(verifyToken && verifySession && verifySession.userRole === userRole)) {
        console.error('❌ Session storage verification FAILED');
        // Don't throw, but log the error
      }
      
    } catch (error) {
      console.error('❌ Error saving session:', error);
      throw error;
    }
  }

  // Get session data for current tab
  getCurrentSession(): TabSession | null {
    // Get token from the single source of truth
    const sessionToken = getTokenForCurrentTab();
    
    // Get user data from multi-account storage
    const sessions = this.getAllSessions();
    
    // Find the session for *this* tab
    const storedSession = sessions.find(session => session.tabId === this.currentTabId);
    
    if (this.isDebug) {
      console.log('🔍 getCurrentSession Debug:', {
        tabId: this.currentTabId,
        hasToken: !!sessionToken,
        hasStoredSession: !!storedSession,
        storedUserRole: storedSession?.userRole || 'none'
      });
    }

    // Success: We have a token and matching session data
    if (sessionToken && storedSession) {
      return {
        tabId: this.currentTabId,
        authToken: sessionToken,
        user: storedSession.user,
        userRole: storedSession.userRole,
        user_id: storedSession.user_id,
        timestamp: storedSession.timestamp
      };
    }
    
    // Fallback: We have a token, but no session data.
    // This happens if session storage was cleared. Return a minimal session.
    if (sessionToken && !storedSession) {
      if (this.isDebug) {
        console.warn('⚠️ Token found but session data missing for tab. Rebuilding minimal session.', this.currentTabId);
      }

      let recoveredRole = '';
      let recoveredUserId = '';
      let recoveredUser: any = {};

      try {
        const payload = JSON.parse(atob(sessionToken.split('.')[1] || ''));
        recoveredRole = payload?.role || payload?.user_role || '';
        recoveredUserId = payload?.user_id || payload?.sub || '';
        recoveredUser = {
          email: payload?.email || '',
          first_name: payload?.fn || payload?.first_name || '',
          last_name: payload?.ln || payload?.last_name || '',
          role: recoveredRole,
          user_id: recoveredUserId,
        };
      } catch (error) {
        console.warn('⚠️ Failed to recover user details from token payload:', error);
      }

      const rebuiltSession: TabSession = {
        tabId: this.currentTabId,
        authToken: sessionToken,
        user: recoveredUser,
        userRole: recoveredRole,
        user_id: recoveredUserId,
        timestamp: Date.now(),
      };

      const refreshedSessions = sessions.filter(session => session.tabId !== this.currentTabId);
      refreshedSessions.push(rebuiltSession);
      this.saveSessions(refreshedSessions);

      return rebuiltSession;
    }

    // No token and no valid session
    if (this.isDebug) {
      console.log('🔍 No valid session found for tab:', this.currentTabId);
    }
    return null;
  }

  // Clear current tab session
  clearCurrentSession(): void {
    // Use the imported function
    clearTokenForCurrentTab();
    
    // Remove from multi-account sessions (localStorage)
    this.cleanupCurrentTab();
  }

  // ... (rest of the functions remain the same) ...

  getAllActiveAccounts(): { email: string; role: string; tabId: string }[] {
    const sessions = this.getAllSessions();
    return sessions.map(session => ({
      email: session.user?.email || 'Unknown',
      role: session.userRole,
      tabId: session.tabId
    }));
  }

  switchToAccount(targetTabId: string): void {
    const sessions = this.getAllSessions();
    const targetSession = sessions.find(session => session.tabId === targetTabId);
    
    if (targetSession) {
      const newTab = window.open(window.location.href, '_blank');
      if (newTab) {
        newTab.focus();
      }
    }
  }

  isTokenValid(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp > Date.now() / 1000;
    } catch {
      return false;
    }
  }

  getCurrentTabId(): string {
    return this.currentTabId;
  }

  getPublicSessions(): TabSession[] {
    return Object.values(this.getAllSessions());
  }

  clearSessionById(tabId: string): void {
    const sessions = this.getAllSessions();
    const filteredSessions = sessions.filter(session => session.tabId !== tabId);
    this.saveSessions(filteredSessions);
  }
}

export default MultiAccountManager;