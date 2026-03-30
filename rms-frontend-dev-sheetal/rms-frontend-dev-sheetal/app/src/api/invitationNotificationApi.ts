// Frontend API functions for invitations and notifications

import axiosInstance from './axiosConfig';
import type { StandardResponse } from '../types/api';

// Invitation Types
export interface InvitationData {
  invitation_id: string;
  invited_email: string;
  invited_first_name: string;
  invited_last_name?: string;
  invited_role: string;
  status: 'PENDING' | 'ACCEPTED' | 'EXPIRED' | 'REVOKED';
  created_at: string;
  expires_at: string;
  accepted_at?: string;
  accepted_user?: {
    user_id: string;
    first_name: string;
    last_name: string;
    email: string;
  };
}

export interface InvitationStats {
  pending: number;
  accepted: number;
  expired: number;
}

// Notification Types
export interface NotificationData {
  notification_id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  read_at?: string;
  related_invitation_id?: string;
  related_user?: {
    user_id: string;
    first_name: string;
    last_name: string;
    email: string;
    role: string;
  };
}

// Invitation API Functions
export const getMyInvitations = async (status?: string): Promise<{ success: boolean, data?: InvitationData[], error?: string }> => {
  try {
    const params = status ? { status } : {};
    const response = await axiosInstance.get<StandardResponse<{ invitations: InvitationData[] }>>('/invitations/my-invitations', { params });
    
    if (response.data.success && response.data.data?.invitations) {
      return { success: true, data: response.data.data.invitations };
    }
    return { success: false, error: response.data.message || "Failed to fetch invitations." };
  } catch (err: any) {
    // If this is an auth error, dispatch a global event so auth UI can react
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try {
        window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } }));
      } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

export const getInvitationStats = async (): Promise<{ success: boolean, data?: InvitationStats, error?: string }> => {
  try {
    const response = await axiosInstance.get<StandardResponse<{ stats: InvitationStats }>>('/invitations/stats');
    
    if (response.data.success && response.data.data?.stats) {
      return { success: true, data: response.data.data.stats };
    }
    return { success: false, error: response.data.message || "Failed to fetch invitation stats." };
  } catch (err: any) {
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try { window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } })); } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

// Notification API Functions
export const getNotifications = async (unreadOnly: boolean = false, limit: number = 50): Promise<{ success: boolean, data?: NotificationData[], error?: string }> => {
  try {
    const params = { unread_only: unreadOnly, limit };
    const response = await axiosInstance.get<StandardResponse<{ notifications: NotificationData[] }>>('/notifications/', { params });
    
    if (response.data.success && response.data.data?.notifications) {
      return { success: true, data: response.data.data.notifications };
    }
    return { success: false, error: response.data.message || "Failed to fetch notifications." };
  } catch (err: any) {
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try { window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } })); } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

export const getUnreadNotificationCount = async (): Promise<{ success: boolean, data?: number, error?: string }> => {
  try {
    const response = await axiosInstance.get<StandardResponse<{ unread_count: number }>>('/notifications/unread-count');
    
    if (response.data.success && typeof response.data.data?.unread_count === 'number') {
      return { success: true, data: response.data.data.unread_count };
    }
    return { success: false, error: response.data.message || "Failed to fetch unread count." };
  } catch (err: any) {
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try { window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } })); } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

export const markNotificationAsRead = async (notificationId: string): Promise<{ success: boolean, message?: string, error?: string }> => {
  try {
    const response = await axiosInstance.put<StandardResponse>(`/notifications/${notificationId}/mark-read`);
    return { success: response.data.success, message: response.data.message };
  } catch (err: any) {
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try { window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } })); } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

export const markAllNotificationsAsRead = async (): Promise<{ success: boolean, message?: string, error?: string }> => {
  try {
    const response = await axiosInstance.put<StandardResponse>('/notifications/mark-all-read');
    return { success: response.data.success, message: response.data.message };
  } catch (err: any) {
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try { window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } })); } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

export const deleteNotification = async (notificationId: string): Promise<{ success: boolean, message?: string, error?: string }> => {
  try {
    const response = await axiosInstance.delete<StandardResponse>(`/notifications/${notificationId}`);
    return { success: response.data.success, message: response.data.message };
  } catch (err: any) {
    if (err?.response && (err.response.status === 401 || err.response.status === 403)) {
      try { window.dispatchEvent(new CustomEvent('auth-error', { detail: { status: err.response.status, message: err.response.data?.message } })); } catch {
        // no-op
      }
    }
    return { success: false, error: err.response?.data?.message || err.message };
  }
};