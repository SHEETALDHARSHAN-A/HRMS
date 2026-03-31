// NotificationContext.tsx - Context for managing notifications

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { 
  getNotifications, 
  getUnreadNotificationCount, 
  markNotificationAsRead, 
  markAllNotificationsAsRead,
  deleteNotification as apiDeleteNotification,
  type NotificationData 
} from '../api/invitationNotificationApi';
import MultiAccountManager from '../utils/multiAccountManager';

interface NotificationContextType {
  notifications: NotificationData[];
  unreadCount: number;
  isLoading: boolean;
  refreshNotifications: () => Promise<void>;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  deleteNotification: (notificationId: string) => Promise<boolean>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const isDebug = !!import.meta.env.DEV;
  const [notifications, setNotifications] = useState<NotificationData[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const refreshNotifications = useCallback(async () => {
    // Check if current tab has an authenticated session
    const accountManager = MultiAccountManager.getInstance();
    const currentSession = accountManager.getCurrentSession();
    
    if (!currentSession || !currentSession.authToken) {
      if (isDebug) {
        console.log('⏭️ Skipping notification refresh: No authenticated session in current tab');
      }
      return;
    }

    setIsLoading(true);
    try {
      if (isDebug) {
        console.log('🔔 Fetching notifications for tab:', currentSession.tabId);
      }
      
      // Fetch both notifications and unread count
      const [notificationsResult, countResult] = await Promise.all([
        getNotifications(false, 20), // Get last 20 notifications
        getUnreadNotificationCount()
      ]);

      if (notificationsResult.success && notificationsResult.data) {
        setNotifications(notificationsResult.data);
      }

      if (countResult.success && typeof countResult.data === 'number') {
        setUnreadCount(countResult.data);
      }
    } catch (error) {
      console.error('Error refreshing notifications for tab:', currentSession.tabId, error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      const result = await markNotificationAsRead(notificationId);
      if (result.success) {
        // Update local state
        setNotifications(prev => 
          prev.map(notif => 
            notif.notification_id === notificationId 
              ? { ...notif, is_read: true, read_at: new Date().toISOString() }
              : notif
          )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    try {
      const result = await markAllNotificationsAsRead();
      if (result.success) {
        // Update local state
        const now = new Date().toISOString();
        setNotifications(prev => 
          prev.map(notif => ({ ...notif, is_read: true, read_at: now }))
        );
        setUnreadCount(0);
      }
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  }, []);

  const deleteNotification = useCallback(async (notificationId: string) => {
    try {
      const result = await apiDeleteNotification(notificationId);
      if (result.success) {
        setNotifications(prev => prev.filter(n => n.notification_id !== notificationId));
        setUnreadCount(prev => Math.max(0, prev - (prev > 0 && prev ? 1 : 0)));
        return true;
      }
      console.error('Failed to delete notification:', result.error || result.message);
      return false;
    } catch (err) {
      console.error('Error deleting notification:', err);
      return false;
    }
  }, []);

  // Initial load and periodic refresh - now with multi-account support
  useEffect(() => {
    const accountManager = MultiAccountManager.getInstance();
    const currentSession = accountManager.getCurrentSession();
    
    // Only set up polling if we have an authenticated session
    if (currentSession && currentSession.authToken) {
      if (isDebug) {
        console.log('🔔 Setting up notification polling for tab:', currentSession.tabId);
      }
      
      // Initial load
      refreshNotifications();
      
      // Set up polling for new notifications every 30 seconds
      const interval = setInterval(() => {
        // Re-check authentication before each poll
        const session = accountManager.getCurrentSession();
        if (session && session.authToken) {
          refreshNotifications();
        } else {
          if (isDebug) {
            console.log('⏭️ Skipping notification poll: Session expired for tab');
          }
        }
      }, 30000);
      
      return () => {
        if (isDebug) {
          console.log('🔔 Cleaning up notification polling for tab:', currentSession.tabId);
        }
        clearInterval(interval);
      };
    } else {
      if (isDebug) {
        console.log('⏭️ Skipping notification setup: No authenticated session');
      }
    }
  }, [refreshNotifications, isDebug]);

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    isLoading,
    refreshNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};