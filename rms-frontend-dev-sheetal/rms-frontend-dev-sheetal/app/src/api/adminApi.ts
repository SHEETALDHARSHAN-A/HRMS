// ats-frontend-dev-sheetal/app/src/api/adminApi.ts
import axiosInstance from '../api/axiosConfig';
import type { StandardResponse } from '../types/api';

export interface Admin {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string; 
  phone_number?: string;
  created_at?: string;
}

export interface AdminInviteData {
  email: string;
  first_name: string;
  last_name?: string;
  phone_number?: string;
  role: 'SUPER_ADMIN' | 'ADMIN' | 'HR';
  expiration_days?: number;
}

export interface AdminUpdateData {
    first_name?: string;
    last_name?: string;
    new_email?: string; // Used to trigger email verification flow
    phone_number?: string;
  role?: 'SUPER_ADMIN' | 'ADMIN' | 'HR';
  expiration_days?: number;
}

// 1. Get List of all Admins (Role-based filtering: SUPER_ADMIN sees all, ADMIN sees ADMIN+HR, HR sees HR only)
export const getAllAdmins = async (): Promise<{ success: boolean, data?: Admin[], error?: string }> => {
  try {
    // Endpoint: GET /v1/admins/list-all
    const response = await axiosInstance.get<StandardResponse<{ admins: Admin[] }>>(`/admins/list-all`);
    
    if (response.data.success && response.data.data?.admins) {
        return { success: true, data: response.data.data.admins };
    }
    return { success: false, error: response.data.message || "Failed to fetch admin list." };
  } catch (err: any) {
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

// 2. Invite a new Admin
export const inviteAdmin = async (data: AdminInviteData): Promise<{ success: boolean, message?: string, error?: string }> => {
  try {
    // Endpoint: POST /v1/admins/invite
    const response = await axiosInstance.post<StandardResponse>(`/admins/invite`, data);
    return { success: true, message: response.data.message };
  } catch (err: any) {
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

// 3. Delete Admins in Batch
export const deleteAdminsBatch = async (userIds: string[]): Promise<{ 
    success: boolean, 
    data?: { deleted_count: number, deleted_ids: string[] }, 
    error?: string 
}> => {
  try {
    // Endpoint: DELETE /v1/admins/delete-batch
    const response = await axiosInstance.delete<StandardResponse>(`/admins/delete-batch`, { data: { user_ids: userIds } });

    if (response.data.success && response.data.data) {
        return { success: true, data: response.data.data as any };
    }
    return { success: false, error: response.data.message || "Batch deletion failed." };
  } catch (err: any) {
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

// 4. Update Admin Details (Triggers verification flow)
export const updateAdmin = async (adminId: string, data: AdminUpdateData): Promise<{ success: boolean, message?: string, error?: string }> => {
  try {
    // Endpoint: PUT /v1/admins/update/{admin_id}
    const response = await axiosInstance.put<StandardResponse>(`/admins/update/${adminId}`, data);
    return { success: true, message: response.data.message };
  } catch (err: any) {
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

// 5. Complete Initial Admin Setup
export const completeAdminSetup = async (token: string): Promise<{ success: boolean, message?: string, error?: string, data?: any }> => {
  try {
    // Endpoint: POST /v1/admins/complete-admin-setup?token={token}
    const response = await axiosInstance.post<StandardResponse>(`/admins/complete-admin-setup?token=${token}`, {});
    
    // 💡 RETURN DATA FIELD FOR USER DETAILS
    return { success: true, message: response.data.message, data: response.data.data };
  } catch (err: any) {
    return { success: false, error: err.response?.data?.message || err.message };
  }
};
// 6. Complete Name Update Verification 
export const verifyAdminNameUpdate = async (token: string, userId: string): Promise<{ success: boolean, message?: string, error?: string }> => {
  try {
    // Endpoint: POST /v1/admins/verify-name-update?user_id={user_id}&token={token}
    const params = new URLSearchParams({ 
        user_id: userId,
        token: token,
    });
    
    // The endpoint uses URL queries, so pass an empty object {} as the body
    const response = await axiosInstance.post<StandardResponse>(`/admins/verify-name-update?${params.toString()}`, {});
    
    return { success: true, message: response.data.message };
  } catch (err: any) {
    return { success: false, error: err.response?.data?.message || err.message };
  }
};

export interface EmailUpdateVerifyData {
  token: string;
  user_id: string;
  new_email: string;
}

// Verify email update after clicking link
export const verifyEmailUpdate = async (data: { 
  token: string; 
  user_id: string; 
  new_email: string; 
}) => {
  try {
    const response = await axiosInstance.get(
      `/admins/complete-email-update-status`,
      { 
        params: {
          token: data.token,
          user_id: data.user_id,
          new_email: data.new_email
        }
      }
    );
    return { success: true, data: response.data };
  } catch (error: any) {
    return {
      success: false,
      error: error.response?.data?.message || 'Failed to verify email update'
    };
  }
};

/**
 * Searches for users by a query string (name, email, user_type, or ID).
 * Assumes a backend endpoint like GET /api/v1/admin/search?q=...
 */
export const searchUsers = async (query: string): Promise<StandardResponse<Admin[]>> => {
  if (!query) return { success: true, status_code: 200, message: "OK", data: [] };
  try {
    const response = await axiosInstance.get('/admins/search', {
      params: { q: query }
    });

    const resp = response.data as any;
    const admins = resp?.data?.admins ?? [];
    return { success: resp.success, status_code: resp.status_code ?? 200, message: resp.message ?? '', data: admins } as StandardResponse<Admin[]>;
  } catch (error: any) {
    return error.response?.data || { success: false, status_code: 500, message: 'Failed to search users' };
  }
};

/**
 * Gets a single user's details by their ID.
 * Assumes a backend endpoint like GET /api/v1/admin/get/<adminId>
 */
export const getAdminById = async (adminId: string): Promise<StandardResponse<Admin>> => {
  try {
    const response = await axiosInstance.get(`/admins/get/${adminId}`);
    return response.data;
  } catch (error: any) {
    return error.response?.data || { success: false, status_code: 500, message: 'Failed to get user details' };
  }
};

// (No additional re-exports here) Keep individual named exports as defined above.