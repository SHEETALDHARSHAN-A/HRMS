import React, { useState, useEffect } from 'react';
import MultiAccountManager from '../../utils/multiAccountManager';
import { useUser } from '../../context/UserContext';

interface SessionInfo {
  tabId: string;
  hasToken: boolean;
  userRole: string;
  userName: string;
  userId: string;
  timestamp: string;
}

const MultiAccountDebug: React.FC = () => {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [currentTabId, setCurrentTabId] = useState<string>('');
  const { user } = useUser();

  const refreshSessionInfo = () => {
    const accountManager = MultiAccountManager.getInstance();
    const allSessions = accountManager.getPublicSessions();
    const currentSession = accountManager.getCurrentSession();

    const sessionInfos: SessionInfo[] = allSessions.map(session => ({
      tabId: session.tabId,
      hasToken: Boolean(session.authToken),
      userRole: session.userRole || 'No role',
      userName: session.user?.name || session.user?.email || 'No name',
      userId: session.user_id || 'No ID',
      timestamp: new Date(session.timestamp).toLocaleTimeString()
    }));

    setSessions(sessionInfos);
    setCurrentTabId(currentSession?.tabId || '');
  };

  useEffect(() => {
    refreshSessionInfo();
    
    // Refresh every 2 seconds to show real-time updates
    const interval = setInterval(refreshSessionInfo, 2000);
    
    return () => clearInterval(interval);
  }, [user]);

  const handleSwitchAccount = (tabId: string) => {
    const accountManager = MultiAccountManager.getInstance();
    accountManager.switchToAccount(tabId);
    window.location.reload(); // Force refresh to load new account
  };

  const handleClearAccount = (tabId: string) => {
    const accountManager = MultiAccountManager.getInstance();
    if (tabId === currentTabId) {
      accountManager.clearCurrentSession();
    } else {
      accountManager.clearSessionById(tabId);
    }
    refreshSessionInfo();
  };

  if (import.meta.env.PROD) {
    return null; // Don't show in production
  }

  return (
    <div style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      background: 'rgba(0,0,0,0.8)',
      color: 'white',
      padding: '10px',
      borderRadius: '8px',
      fontSize: '12px',
      maxWidth: '400px',
      zIndex: 9999,
      fontFamily: 'monospace'
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '10px' }}>
        Multi-Account Debug Info
      </div>
      
      <div style={{ marginBottom: '10px' }}>
        <strong>Current Tab:</strong> {currentTabId}
      </div>

      <div style={{ marginBottom: '10px' }}>
        <strong>Active Sessions ({sessions.length}):</strong>
      </div>

      {sessions.map((session) => (
        <div
          key={session.tabId}
          style={{
            background: session.tabId === currentTabId ? 'rgba(0,255,0,0.2)' : 'rgba(255,255,255,0.1)',
            padding: '8px',
            margin: '4px 0',
            borderRadius: '4px',
            border: session.tabId === currentTabId ? '1px solid green' : '1px solid transparent'
          }}
        >
          <div><strong>Tab:</strong> {session.tabId.slice(-8)}... {session.tabId === currentTabId && '(Current)'}</div>
          <div><strong>User:</strong> {session.userName}</div>
          <div><strong>Role:</strong> {session.userRole}</div>
          <div><strong>Token:</strong> {session.hasToken ? '✅' : '❌'}</div>
          <div><strong>Time:</strong> {session.timestamp}</div>
          
          <div style={{ marginTop: '4px' }}>
            {session.tabId !== currentTabId && (
              <button
                onClick={() => handleSwitchAccount(session.tabId)}
                style={{
                  background: 'blue',
                  color: 'white',
                  border: 'none',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontSize: '10px',
                  marginRight: '4px',
                  cursor: 'pointer'
                }}
              >
                Switch
              </button>
            )}
            <button
              onClick={() => handleClearAccount(session.tabId)}
              style={{
                background: 'red',
                color: 'white',
                border: 'none',
                padding: '2px 6px',
                borderRadius: '3px',
                fontSize: '10px',
                cursor: 'pointer'
              }}
            >
              Clear
            </button>
          </div>
        </div>
      ))}

      <div style={{ marginTop: '10px', fontSize: '10px', opacity: 0.7 }}>
        Auto-refreshing every 2s
      </div>
    </div>
  );
};

export default MultiAccountDebug;