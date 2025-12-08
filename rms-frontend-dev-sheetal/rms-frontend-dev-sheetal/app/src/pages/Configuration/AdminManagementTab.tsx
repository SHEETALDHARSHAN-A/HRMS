import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Loader2, Plus, Trash2, Edit, Mail, Check, X, CheckSquare, ChevronDown, RefreshCw, UserCog, AlertTriangle, Clock, CheckCircle, XCircle } from 'lucide-react';
import { 
    getAllAdmins, 
    inviteAdmin, 
    deleteAdminsBatch,
    updateAdmin, 
} from '../../api/adminApi';

import {
    getMyInvitations,
    getInvitationStats,
    type InvitationData,
    type InvitationStats
} from '../../api/invitationNotificationApi'; 

import type {
    Admin,
    AdminInviteData,
    AdminUpdateData
} from '../../api/adminApi'; 

import { useToast, useModal } from '../../context/ModalContext';
import Button from '../../components/common/Button';
import { ZodError, z } from 'zod';
import MultiAccountManager from '../../utils/multiAccountManager'; 

// --- Zod Schemas for Validation ---
const inviteSchema = z.object({
  email: z.string().email({ message: "Invalid email format." }),
  first_name: z.string().min(1, { message: "First name is required." }),
  last_name: z.string().optional(),
  phone_number: z.string().min(7, { message: "Phone number is required." }),
  role: z.enum(['SUPER_ADMIN', 'ADMIN', 'HR'], { message: "Valid role is required." }),
  expiration_days: z.number().int().min(1).max(365).optional(),
});

const updateSchema = z.object({
    first_name: z.string().min(1, { message: "First name is required." }).optional(),
    last_name: z.string().optional(),
    new_email: z.string().email({ message: "Invalid email format." }).optional().or(z.literal("")),
    phone_number: z.string().min(7, { message: "Phone number is required." }).optional(),
  role: z.enum(['SUPER_ADMIN','ADMIN','HR']).optional(),
  expiration_days: z.number().int().min(1).max(365).optional(),
}).refine(
  (data) => data.first_name || data.last_name || data.new_email || data.phone_number || data.role,
    { message: "At least one field (Name or Email) must be provided for update.", path: ['general'] }
);

interface InviteFormState {
  email: string;
  firstName: string;
  lastName: string;
  phoneNumber: string;
  role: 'SUPER_ADMIN' | 'ADMIN' | 'HR';
  expirationDays?: number;
}

interface EditFormState {
  first_name: string;
  last_name: string;
  new_email: string;
  phone_number: string;
  role?: 'SUPER_ADMIN' | 'ADMIN' | 'HR' | '';
  expirationDays?: number;
}

// (Legacy simple Modal removed — using ModernInviteModal / ModernEditModal for dialogs)

// Professional Edit Modal with clean design
interface ModernEditModalProps {
    isOpen: boolean;
    onClose: () => void;
    admin: Admin;
    children: React.ReactNode;
}

const ModernEditModal: React.FC<ModernEditModalProps> = ({ isOpen, onClose, admin, children }) => {
  // internal visibility to animate in/out
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    if (isOpen) {
      // start enter animation on next tick
      const t = setTimeout(() => setVisible(true), 10);
      return () => clearTimeout(t);
    }
    setVisible(false);
  }, [isOpen]);

  if (!isOpen) return null;

  const initials = `${admin.first_name[0]}${admin.last_name?.[0] || ''}`.toUpperCase();
  
  // use shared getAvatarColor helper (defined below)

  const closeWithAnimation = () => {
    // trigger exit animation
    setVisible(false);
    // wait for animation to complete then call onClose
    setTimeout(() => onClose(), 220);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-start justify-center bg-black/40 backdrop-blur-sm transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
      style={{ paddingTop: '2rem', paddingBottom: '6rem', overflowY: 'auto' }}
      aria-modal="true"
      role="dialog"
      onClick={closeWithAnimation}
    >
      <div
        className={`relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 my-4 transform transition-all duration-200 ${visible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-3 scale-95'}`}
        style={{ maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Section */}
        <div className="relative bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100">
          {/* Close Button */}
          <button
            onClick={closeWithAnimation}
            className="absolute top-4 right-4 z-10 p-2 rounded-lg bg-white/80 backdrop-blur-sm text-gray-500 hover:text-gray-700 hover:bg-white transition-all duration-200 shadow-sm"
            aria-label="Close"
          >
            <X size={20} />
          </button>

          {/* Header Content */}
          <div className="flex items-center gap-6 p-8">
            {/* Avatar */}
            <div className={`flex-shrink-0 w-20 h-20 rounded-full ${getAvatarColor(admin.first_name)} flex items-center justify-center text-white text-2xl font-bold shadow-lg ring-4 ring-white`}>
              {initials}
            </div>
            
            {/* Admin Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-bold text-gray-900">
                  {admin.first_name} {admin.last_name}
                </h2>
                <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${getRoleBadgeClasses(admin.role)}`}>
                  {formatRoleName(admin.role) || 'ADMIN'}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Mail size={14} className="text-gray-400" />
                <span className="truncate">{admin.email}</span>
              </div>
              {admin.created_at && (
                <p className="text-xs text-gray-500 mt-1">
                    Admin since {new Date(admin.created_at).toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                  })}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Form Content */}
        <div className="p-8">
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Edit Administrator Details</h3>
            <p className="text-sm text-gray-500">Update the administrator's profile information below.</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
};

// Small helper to render avatar initials with gradient
const Avatar: React.FC<{ name: string, size?: 'sm' | 'md' }> = ({ name, size = 'md' }) => {
    const initials = name.split(' ').map(n => n[0]?.toUpperCase()).slice(0,2).join('');
    const colors = ['from-indigo-400 to-indigo-500','from-teal-400 to-teal-500','from-pink-400 to-pink-500','from-amber-400 to-amber-500'];
    const color = colors[name.length % colors.length];
    
    const sizeClasses = size === 'md' ? 'w-12 h-12 text-lg' : 'w-8 h-8 text-sm';

    return (
      <div 
        className={`${sizeClasses} rounded-full bg-gradient-to-br ${color} flex items-center justify-center text-white font-semibold shadow-inner flex-shrink-0`}
        title={name.trim() || 'Admin'}
      >
        {initials || 'A'}
      </div>
    );
};

// Helper to get role badge styling
const getRoleBadgeClasses = (role: string) => {
  switch (role) {
    case 'SUPER_ADMIN':
      return 'bg-red-50 text-red-700 border-red-200';
    case 'ADMIN':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'HR':
      return 'bg-green-50 text-green-700 border-green-200';
    default:
      return 'bg-gray-50 text-gray-700 border-gray-200';
  }
};

// Helper to format role display name
const formatRoleName = (role: string) => {
  switch (role) {
    case 'SUPER_ADMIN':
      return 'Super Admin';
    case 'ADMIN':
      return 'Admin';
    case 'HR':
      return 'HR';
    default:
      return role;
  }
};


const AdminManagementTab: React.FC = () => {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [invitations, setInvitations] = useState<InvitationData[]>([]);
  const [invitationStats, setInvitationStats] = useState<InvitationStats | null>(null);
  const [activeTab, setActiveTab] = useState<'admins' | 'invitations'>('admins');
  const [isLoading, setIsLoading] = useState(true);
  const [isInviting, setIsInviting] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<Admin | null>(null);
  const [selectedAdmins, setSelectedAdmins] = useState<Record<string, boolean>>({}); // Changed to object for performance/consistency
  
  // Get current user's role from multi-account manager (tab-specific)
  const [currentUserRole, setCurrentUserRole] = useState<string>('');
  const [currentUserId, setCurrentUserId] = useState<string>('');
  
  useEffect(() => {
    const accountManager = MultiAccountManager.getInstance();
    const currentSession = accountManager.getCurrentSession();
    
    if (currentSession) {
      console.log('📋 AdminManagementTab MOUNTED - Tab:', currentSession.tabId, 'Role:', currentSession.userRole, 'UserID:', currentSession.user_id);
      
      const role = currentSession.userRole;
      const userId = currentSession.user_id;
      
      // Verify with JWT token for additional validation
      if (currentSession.authToken) {
        try {
          const payload = JSON.parse(atob(currentSession.authToken.split('.')[1]));
          const tokenRole = payload.role;
          const tokenUserId = payload.user_id || payload.sub;
          
          // Log any mismatches for debugging (but use session values)
          if (tokenRole && tokenRole !== role) {
            console.warn('� Role mismatch - Session:', role, 'Token:', tokenRole);
          }
          
          if (tokenUserId && tokenUserId !== userId) {
            console.warn('� User ID mismatch - Session:', userId, 'Token:', tokenUserId);
          }
        } catch (e) {
          console.warn('📋 Failed to decode token for validation:', e);
        }
      }
      
      setCurrentUserRole(role || '');
      setCurrentUserId(userId || '');
    } else {
      console.log('� AdminManagementTab - No session found for current tab');
      setCurrentUserRole('');
      setCurrentUserId('');
    }
  }, []);
  
  // RBAC Permission Helpers
  const canEditAdmin = useCallback((adminRole: string) => {
    if (currentUserRole === 'SUPER_ADMIN') return true;
    if (currentUserRole === 'ADMIN' && (adminRole === 'ADMIN' || adminRole === 'HR')) return true;
    if (currentUserRole === 'HR' && adminRole === 'HR') return true;
    return false;
  }, [currentUserRole]);

  const canDeleteAdmin = useCallback((adminRole: string, adminId: string) => {
    // Prevent self-deletion
    if (adminId === currentUserId) return false;
    
    if (currentUserRole === 'SUPER_ADMIN') return true;
    if (currentUserRole === 'ADMIN' && (adminRole === 'ADMIN' || adminRole === 'HR')) return true;
    if (currentUserRole === 'HR' && adminRole === 'HR') return true;
    return false;
  }, [currentUserRole, currentUserId]);
  
  // Bulk selection state
  const [topSelectMenuOpen, setTopSelectMenuOpen] = useState(false);
  const selectedCount = useMemo(() => Object.values(selectedAdmins).filter(Boolean).length, [selectedAdmins]);

  // Forms State
  const [inviteForm, setInviteForm] = useState<InviteFormState>({ email: '', firstName: '', lastName: '', phoneNumber: '', role: 'HR', expirationDays: 7 });

  const [editForm, setEditForm] = useState<EditFormState>({ first_name: '', last_name: '', new_email: '', phone_number: '', expirationDays: 7 });
  const [inviteErrors, setInviteErrors] = useState<Record<string, string>>({});
  const [editErrors, setEditErrors] = useState<Record<string, string>>({});

  const { showToast } = useToast();
  const { showConfirm, setModalProcessing } = useModal();
  
  // --- Data Fetching ---
  const fetchAdmins = useCallback(async () => {
    setIsLoading(true);
    setSelectedAdmins({}); // Clear selection on refresh
    try {
      const result = await getAllAdmins();
      
      if (result.success && Array.isArray(result.data)) {
        // Backend already filters based on role permissions, display all returned admins
        console.log('📋 Fetched admins:', result.data.map(a => ({ id: a.user_id, name: a.first_name, role: a.role })));
        
        const roleCount = result.data.reduce((acc: Record<string, number>, admin) => {
          acc[admin.role] = (acc[admin.role] || 0) + 1;
          return acc;
        }, {});
        
        console.log('📋 Admin role distribution:', roleCount);
        setAdmins(result.data as Admin[]);
      } else {
        console.error("API Call Failed: getAllAdmins:", result.error);
        setAdmins([]);
        showToast(result.error || "Failed to load admin list. Check server logs.", 'error'); 
      }
    } catch (e) {
        console.error("Network/Unexpected Error fetching Admins:", e);
        setAdmins([]);
        showToast("Network error or unexpected response when fetching admins.", 'error');
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  const fetchInvitations = useCallback(async () => {
    // Guard: don't call invitation endpoints when there is no auth session available.
    // This avoids repeated 401 requests while the user is unauthenticated.
    const accountManager = MultiAccountManager.getInstance();
    const currentSession = accountManager.getCurrentSession();
    
    if (!currentSession || !currentSession.authToken) {
      // Not authenticated in this tab — skip fetching invitations to avoid 401 spam.
      console.warn('[invites] Skipping invitation fetch for tab: no auth session');
      setInvitations([]);
      setInvitationStats(null);
      return;
    }

    // Additional check: validate token structure and expiry
    try {
      const payload = JSON.parse(atob(currentSession.authToken.split('.')[1]));
      // Check for user ID in either 'user_id' or 'sub' field (JWT standard)
      if (!payload.user_id && !payload.sub) {
        console.warn('[invites] Skipping invitation fetch: token missing user identifier (user_id or sub)');
        setInvitations([]);
        setInvitationStats(null);
        return;
      }
      if (payload.exp && Date.now() / 1000 > payload.exp) {
        console.warn('[invites] Skipping invitation fetch: token expired for tab:', currentSession.tabId);
        setInvitations([]);
        setInvitationStats(null);
        return;
      }
    } catch (e) {
      console.warn('[invites] Skipping invitation fetch: invalid token format for tab:', currentSession.tabId, e);
      setInvitations([]);
      setInvitationStats(null);
      return;
    }

    try {
      const [invitationResult, statsResult] = await Promise.all([
        getMyInvitations(),
        getInvitationStats()
      ]);
      
      if (invitationResult.success && invitationResult.data) {
        setInvitations(invitationResult.data);
      }
      
      if (statsResult.success && statsResult.data) {
        setInvitationStats(statsResult.data);
      }
    } catch (error) {
      console.error('Error fetching invitations:', error);
    }
  }, []);

  useEffect(() => {
    fetchAdmins();
    fetchInvitations();
  }, [fetchAdmins, fetchInvitations]);
  
  // Re-fetch data when user ID changes (important for user-specific data)
  useEffect(() => {
    if (currentUserId) {
      fetchInvitations();
    }
  }, [currentUserId, fetchInvitations]);

  // REMOVED: Multi-account session change listeners that were causing cross-tab interference
  // Each tab now maintains its own state independently through sessionStorage
  // No need to listen for global storage events or sessionUpdate events
  
  // Auto-refresh invitations when on invitations tab
  useEffect(() => {
    if (activeTab !== 'invitations') return;
    
    const interval = setInterval(() => {
      fetchInvitations();
    }, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, [activeTab, fetchInvitations]);

  // --- Invitation Display Helpers ---
  // Compute display status (treat pending invites whose expires_at is in the past as EXPIRED)
  const getInvitationDisplayStatus = (inv: InvitationData) => {
    try {
      const now = Date.now();
      const exp = inv.expires_at ? new Date(inv.expires_at).getTime() : null;
  if (inv.status === 'PENDING' && exp && exp < now) return 'EXPIRED';
    } catch (e) {
      // fall through
    }
    return inv.status;
  };

  // Derive local invitation stats from the fetched invitations so UI reflects computed expiry state
  const computedInvitationStats = React.useMemo(() => {
    const counts = { pending: 0, accepted: 0, expired: 0 } as { pending: number; accepted: number; expired: number };
    invitations.forEach(inv => {
      const s = getInvitationDisplayStatus(inv);
      if (s === 'ACCEPTED') counts.accepted += 1;
      else if (s === 'EXPIRED') counts.expired += 1;
      else counts.pending += 1;
    });
    return counts;
  }, [invitations]);
  
  // Close select menu automatically when nothing is selected
  useEffect(() => {
    if (selectedCount === 0) {
      setTopSelectMenuOpen(false);
    }
  }, [selectedCount]);


  // --- Invitation Logic ---
  const handleInviteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteErrors({});
    
    const data: AdminInviteData = {
        email: inviteForm.email.trim(),
        first_name: inviteForm.firstName.trim(),
        last_name: inviteForm.lastName.trim() || undefined,
        phone_number: inviteForm.phoneNumber.trim(),
        role: inviteForm.role,
    expiration_days: inviteForm.expirationDays ?? 7,
    };

    try {
        inviteSchema.parse(data);
    } catch (error) {
        if (error instanceof ZodError) {
            const fieldErrors: Record<string,string> = {};
            error.issues.forEach(issue => {
                const key = issue.path[0] as string;
                if (key === 'email') fieldErrors.email = issue.message;
                if (key === 'first_name') fieldErrors.firstName = issue.message;
        if (key === 'phone_number') fieldErrors.phoneNumber = issue.message;
            });
            setInviteErrors(fieldErrors);
        }
        return;
    }

    setIsInviting(true);
    const result = await inviteAdmin(data);
    setIsInviting(false);
    
    if (result.success) {
      showToast(result.message || 'Invitation sent!', 'success');
      setInviteModalOpen(false);
      setInviteForm({ email: '', firstName: '', lastName: '', phoneNumber: '', role: 'HR' });
      fetchAdmins(); 
      fetchInvitations(); // Also refresh invitations
    } else {
      // show toast for global error, field errors under the email field
      showToast(result.error || 'Failed to send invitation.', 'error');
      setInviteErrors({ general: result.error || 'Failed to send invitation.' });
    }
  };

  // --- Selection & Deletion Logic ---
  const toggleSelectAdmin = (userId: string, checked: boolean) => {
    setSelectedAdmins(s => ({ ...s, [userId]: checked }));
  };

  const clearSelection = () => setSelectedAdmins({});

  const selectAll = () => {
    // Only select admins the user has permission to delete
    const all = admins
      .filter(a => canDeleteAdmin(a.role, a.user_id))
      .reduce((acc, a) => ({ ...acc, [a.user_id]: true }), {} as Record<string, boolean>);
    setSelectedAdmins(all);
  };

  const invertSelection = () => {
    // Only invert selection for admins the user has permission to delete
    const inverted = admins
      .filter(a => canDeleteAdmin(a.role, a.user_id))
      .reduce((acc, a) => ({ ...acc, [a.user_id]: !selectedAdmins[a.user_id] }), {} as Record<string, boolean>);
    setSelectedAdmins(inverted);
  };
  
  const handleBulkDelete = async () => {
    const ids = Object.keys(selectedAdmins).filter(id => selectedAdmins[id]);
    if (ids.length === 0) {
        showToast('No admins selected for deletion', 'info');
        return;
    }
    
    const confirmed = await showConfirm({
        title: "Confirm Batch Deletion",
        message: `Are you sure you want to permanently delete ${ids.length} selected admin account(s)? This action revokes their access and cannot be undone.`,
        confirmText: "Delete",
        isDestructive: true,
    });
    
    if (!confirmed) return;
    
    setModalProcessing(true);
    setIsBulkDeleting(true);
    
    // Optimistic UI update: Remove from list immediately
    setAdmins(prev => prev.filter(admin => !ids.includes(admin.user_id)));
    
    try {
        const result = await deleteAdminsBatch(ids);
        
        if (result.success) {
            showToast(`Successfully deleted ${result.data?.deleted_count || ids.length} admin(s).`, 'success');
            setSelectedAdmins({});
        } else {
            showToast(result.error || 'Batch deletion failed. Reverting list.', 'error');
            fetchAdmins(); // Re-fetch on failure
        }
    } catch (e: any) {
        showToast(e.message || 'Network error during deletion. Reverting list.', 'error');
        fetchAdmins(); // Re-fetch on network error
    } finally {
        setModalProcessing(false);
        setIsBulkDeleting(false);
    }
  };

  // --- Single Admin Delete Logic ---
  const [deletingAdminId, setDeletingAdminId] = useState<string | null>(null);

  const handleDeleteSingle = async (adminId: string) => {
    const confirmed = await showConfirm({
      title: 'Confirm Deletion',
      message: 'Are you sure you want to permanently delete this admin? This action cannot be undone.',
      confirmText: 'Delete',
      isDestructive: true,
    });

    if (!confirmed) return;

    setModalProcessing(true);
    setDeletingAdminId(adminId);

    // optimistic removal
    const prev = admins;
    setAdmins(a => a.filter(x => x.user_id !== adminId));

    try {
      const result = await deleteAdminsBatch([adminId]);
      if (result.success) {
        showToast('Admin deleted.', 'success');
        // clear selection if this id was selected
        setSelectedAdmins(s => {
          const copy = { ...s };
          delete copy[adminId];
          return copy;
        });
      } else {
        showToast(result.error || 'Failed to delete admin. Reverting.', 'error');
        setAdmins(prev);
      }
    } catch (e: any) {
      showToast(e.message || 'Network error during deletion. Reverting.', 'error');
      setAdmins(prev);
    } finally {
      setDeletingAdminId(null);
      setModalProcessing(false);
    }
  };

  // --- Edit Logic ---
  const openEditModal = (admin: Admin) => {
    setEditingAdmin(admin);
    setEditForm({
      first_name: admin.first_name,
      last_name: admin.last_name || '',
      new_email: admin.email,
      phone_number: admin.phone_number || '',
      role: ['SUPER_ADMIN', 'ADMIN', 'HR'].includes(admin.role) ? (admin.role as 'SUPER_ADMIN' | 'ADMIN' | 'HR') : '',
      expirationDays: 7,
    });
    setEditModalOpen(true);
    setEditErrors({});
  };
  
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAdmin) return;
    
    setEditErrors({});
    
  const updates: AdminUpdateData = {};
  const currentLastName = editingAdmin.last_name || '';
  const currentPhone = editingAdmin.phone_number || '';
     
    // Collect changes
    if (editForm.first_name.trim() !== editingAdmin.first_name) updates.first_name = editForm.first_name.trim();
      if (editForm.last_name.trim() !== currentLastName) updates.last_name = editForm.last_name.trim();
      if (editForm.new_email.trim() && editForm.new_email.trim() !== editingAdmin.email) updates.new_email = editForm.new_email.trim();
    if (editForm.phone_number.trim() !== currentPhone) updates.phone_number = editForm.phone_number.trim();
    if (editForm.role !== undefined && editForm.role !== '' && editForm.role !== editingAdmin.role) updates.role = editForm.role;
    // Include expiration_days to control how long confirmation links (email/phone/name) should remain valid
    if (typeof editForm.expirationDays === 'number' && !isNaN(editForm.expirationDays)) {
      updates.expiration_days = editForm.expirationDays;
    }
    
    if (Object.keys(updates).length === 0) {
        setEditErrors({ general: "No changes detected." });
        return;
    }
    
  try {
    // Use a temporary object for validation, as optional fields are not present if no change
  const validationData: AdminUpdateData = { ...updates } as any;
    // include expiration_days in validation if provided
    if (updates.expiration_days) (validationData as any).expiration_days = updates.expiration_days;
    updateSchema.parse(validationData as any);
    } catch (error) {
        if (error instanceof ZodError) {
            const fieldErrors: Record<string,string> = {};
            error.issues.forEach(issue => {
                const key = issue.path[0] as string;
                if (key === 'first_name') fieldErrors.first_name = issue.message;
                if (key === 'new_email') fieldErrors.new_email = issue.message;
        if (key === 'phone_number') fieldErrors.phone_number = issue.message;
            });
            setEditErrors(fieldErrors);
        } else if (error && (error as any).path?.[0] === 'general') {
            setEditErrors({ general: (error as any).message });
        }
        return;
    }
    
    setIsUpdating(true);
    setModalProcessing(true);
    
    try {
        const result = await updateAdmin(editingAdmin.user_id, updates);

        if (result.success) {
            showToast(result.message || 'Admin updated.', 'success');
            setEditModalOpen(false);
            fetchAdmins();
        } else {
            setEditErrors({ general: result.error || 'Failed to update admin.' });
        }
    } catch (e: any) {
        setEditErrors({ general: e.message || 'Network error during update.' });
    } finally {
        setIsUpdating(false);
        setModalProcessing(false);
    }
  };

  const isInviteFormValid = Boolean(inviteForm.email.trim() && inviteForm.firstName.trim() && inviteForm.phoneNumber.trim());
  const isEditFormValid = Boolean(
    editForm.first_name.trim() ||
    editForm.last_name.trim() ||
    editForm.new_email.trim() ||
    editForm.phone_number.trim() ||
    (editingAdmin && editForm.role !== undefined && editForm.role !== '' && editForm.role !== editingAdmin.role)
  );
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 size={32} className="animate-spin text-[var(--color-primary-500)]" />
        <p className="ml-3 text-lg font-medium text-gray-600">Loading admin accounts...</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('admins')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'admins'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Admin Accounts ({admins.length})
        </button>
        <button
          onClick={() => setActiveTab('invitations')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'invitations'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Invitations
          {invitationStats && (
            <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
              {invitationStats.pending} pending, {invitationStats.accepted} accepted
            </span>
          )}
        </button>
      </div>
      
      {/* Content based on active tab */}
      {activeTab === 'admins' ? (
        <>
      {/* List Header/Action Button - Using style from JobPostsList.tsx */}
      <div className="flex justify-between items-center mb-6 border-b pb-4 border-gray-100">
        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <UserCog size={20} className="text-gray-600" />
            Admin Accounts ({admins.length})
        </h2>
        
        <div className="flex gap-3 items-center">
            {/* Bulk actions toolbar */}
            <div className="flex items-center gap-2 h-10 px-3 bg-white/90 border border-gray-100 rounded-md shadow-sm">
                <div className="relative">
                <button
                    title="Select options"
                    onClick={() => setTopSelectMenuOpen(v => !v)}
                    className="inline-flex items-center gap-1.5 px-2 py-1.5 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600 transition-colors"
                >
                    <CheckSquare size={14} />
                    <ChevronDown size={14} className={`transition-transform duration-200 ${topSelectMenuOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Select menu */}
                {topSelectMenuOpen && (
                    <div className="absolute right-0 top-10 bg-white rounded-md shadow-lg border border-gray-100 p-1 text-sm z-30 min-w-[120px]">
                    <button
                        className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700"
                        onClick={() => { selectAll(); setTopSelectMenuOpen(false); }}
                    >
                        <CheckSquare size={12} className="text-gray-400" />
                        Select All
                    </button>
                    <button
                        className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700"
                        onClick={() => { clearSelection(); setTopSelectMenuOpen(false); }}
                    >
                        <X size={12} className="text-gray-400" />
                        Clear
                    </button>
                    <button
                        className="flex w-full items-center gap-2 text-left px-2 py-1.5 rounded hover:bg-gray-50 text-gray-700"
                        onClick={() => { invertSelection(); setTopSelectMenuOpen(false); }}
                    >
                        <RefreshCw size={12} className="text-gray-400" />
                        Invert
                    </button>
                    </div>
                )}
                </div>

                <div className={`inline-flex items-center justify-center h-6 min-w-[24px] px-2 rounded text-xs font-medium ${
                selectedCount ? 'bg-red-50 text-red-600' : 'bg-gray-50 text-gray-500'
                }`}>
                {selectedCount}
                </div>

                <div className="h-4 w-px bg-gray-200" />

                <button
                onClick={handleBulkDelete}
                disabled={selectedCount === 0 || isBulkDeleting}
                aria-busy={isBulkDeleting}
                title={selectedCount === 0 ? 'Select admins to enable delete' : 'Delete selected admins'}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                    selectedCount === 0
                    ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                    : 'bg-red-50 text-red-600 hover:bg-red-100 active:bg-red-200'}`}
                >
                {isBulkDeleting ? (
                    <>
                    <Loader2 size={12} className="animate-spin" />
                    <span>Deleting...</span>
                    </>
                ) : (
                    <>
                    <Trash2 size={12} />
                    <span>Delete</span>
                    </>
                )}
                </button>
            </div>

            <Button
                onClick={fetchAdmins}
                variant="outline"
                className="rounded-lg px-3 h-10 text-sm flex items-center justify-center"
                disabled={isLoading}
            >
                <RefreshCw size={16} />
            </Button>
            
            <Button 
                variant="primary" 
                onClick={() => setInviteModalOpen(true)}
                className="py-2 px-4 text-sm flex items-center gap-2"
            >
                <Plus size={16} /> Invite
            </Button>
        </div>
      </div>


      {/* Admin List Section - new horizontal card design */}
      <div className="w-full flex flex-col gap-3">
        {admins.length === 0 && (
            <div className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50">
                <p className="text-lg font-medium text-gray-500 mb-2">No admin accounts found</p>
                <p className="text-sm text-gray-400">Invite the first administrator to get started.</p>
            </div>
        )}
        {admins.map(admin => (
          <div 
            key={admin.user_id} 
            className={`relative flex items-stretch w-full p-0 rounded-lg shadow-sm transition-all duration-200 
              ${selectedAdmins[admin.user_id] ? 'bg-red-50 border-l-4 border-red-400' : 'bg-white border border-gray-100'} hover:shadow-md overflow-hidden`}
          >
            
            {/* 1. Checkbox Area (Outside Left - Non-Clickable for Modal) - Only show if user can delete */}
            {canDeleteAdmin(admin.role, admin.user_id) && (
              <div
                className={`flex-shrink-0 flex items-center justify-center p-4 transition-colors ${selectedAdmins[admin.user_id] ? 'bg-red-100/50' : 'bg-gray-50'} border-r border-gray-100`}
                onClick={(e) => e.stopPropagation()}
              >
                <label className="inline-flex items-center cursor-pointer" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Select admin ${admin.first_name}`}
                    className="sr-only peer"
                    checked={!!selectedAdmins[admin.user_id]}
                    onChange={(e) => toggleSelectAdmin(admin.user_id, e.target.checked)}
                    onClick={(e) => e.stopPropagation()}
                  />

                  <div className={`relative flex items-center justify-center w-6 h-6 border-2 rounded transition-all duration-200
                    ${selectedAdmins[admin.user_id]
                        ? 'bg-red-50 border-red-500'
                        : 'bg-white border-gray-300 hover:border-red-400'
                      }`}
                  >
                    <Check
                      className={`w-5 h-5 transition-all duration-200
                        ${selectedAdmins[admin.user_id]
                          ? 'text-red-500 opacity-100 scale-100'
                          : 'opacity-0 scale-75'
                        }`}
                      strokeWidth={3}
                      aria-hidden="true"
                    />
                  </div>
                </label>
              </div>
            )}

            {/* 2. Main Card Content */}
            <div className="flex items-center gap-4 flex-1 p-3 sm:p-4">
              
              {/* Avatar/Basic Info */}
              <div className="flex items-center gap-4 flex-1 min-w-0">
                  <Avatar name={`${admin.first_name} ${admin.last_name || ''}`} size="md" />
                  
                  <div className="min-w-0 flex-1">
                      <div className="text-lg font-bold text-gray-900 truncate">
                        {admin.first_name} {admin.last_name}
                      </div>
                      <div className="text-sm text-gray-500 truncate mt-0.5">
                        <Mail size={14} className="inline-block mr-1 text-gray-400" /> 
                        {admin.email}
                      </div>
                  </div>
              </div>
              
              {/* Role and Actions */}
              <div className="flex flex-col items-end gap-2 ml-4 flex-shrink-0">
                <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${getRoleBadgeClasses(admin.role)}`}>
                  {formatRoleName(admin.role) || 'ADMIN'}
                </span>                  <div className="flex items-center gap-1">
                    {/* Date Info */}
                    <div className="text-xs text-gray-400 mr-2">
                        Admin Since: {admin.created_at ? new Date(admin.created_at).toLocaleDateString() : '—'}
                    </div>

                    {/* Edit Button - show only if user has permission */}
                    {canEditAdmin(admin.role) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); openEditModal(admin); }}
                        className="inline-flex items-center gap-2 p-2 rounded-md text-gray-600 hover:text-green-600 hover:bg-green-50 transition-all duration-150"
                        title={`Edit ${admin.first_name}`}
                        aria-label={`Edit ${admin.first_name}`}
                      >
                        <Edit size={16} />
                        <span className="sr-only">Edit</span>
                      </button>
                    )}

                    {/* Delete Button (single admin) - show only if user has permission */}
                    {canDeleteAdmin(admin.role, admin.user_id) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteSingle(admin.user_id); }}
                        className="p-2 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50 transition-all duration-150"
                        title={`Delete ${admin.first_name}`}
                        aria-label={`Delete ${admin.first_name}`}
                        disabled={isBulkDeleting || deletingAdminId === admin.user_id}
                      >
                        {deletingAdminId === admin.user_id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Trash2 size={16} />
                        )}
                      </button>
                    )}
                  </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Invite Modal - Modern Design (matches Edit modal) */}
      {inviteModalOpen && (
        <ModernInviteModal
          isOpen={inviteModalOpen}
          onClose={() => setInviteModalOpen(false)}
          name={`${inviteForm.firstName} ${inviteForm.lastName}`}
          email={inviteForm.email}
          role={inviteForm.role}
        >
          <form onSubmit={handleInviteSubmit} className="space-y-4">
            <p className="text-sm text-gray-600">An invitation link will be sent to the provided email address for account creation.</p>
            {currentUserRole === 'HR' && (
              <div className="mt-2 text-sm text-blue-800 bg-blue-50 border border-blue-100 p-2 rounded-md flex items-start gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mt-0.5 flex-shrink-0 text-blue-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
                </svg>
                <div>
                  <span className="font-medium">Note:</span>
                  <div>You can invite HR users only.</div>
                </div>
              </div>
            )}
            {inviteErrors.general && <div className="text-sm text-red-600 bg-red-50 p-2 rounded">{inviteErrors.general}</div>}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700">First name*</label>
                <input
                  value={inviteForm.firstName}
                  onChange={(e) => setInviteForm({ ...inviteForm, firstName: e.target.value })}
                  className="w-full mt-1 p-2 border border-gray-300 focus:border-blue-500 focus:ring-blue-500 rounded-md transition-colors"
                  disabled={isInviting}
                />
                {inviteErrors.firstName && <p className="text-xs text-red-500 mt-1">{inviteErrors.firstName}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Last name</label>
                <input
                  value={inviteForm.lastName}
                  onChange={(e) => setInviteForm({ ...inviteForm, lastName: e.target.value })}
                  className="w-full mt-1 p-2 border border-gray-300 focus:border-blue-500 focus:ring-blue-500 rounded-md transition-colors"
                  disabled={isInviting}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Email address*</label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                className="w-full mt-1 p-2 border border-gray-300 focus:border-blue-500 focus:ring-blue-500 rounded-md transition-colors"
                disabled={isInviting}
              />
              {inviteErrors.email && <p className="text-xs text-red-500 mt-1">{inviteErrors.email}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Phone number*</label>
              <input
                value={inviteForm.phoneNumber}
                onChange={(e) => setInviteForm({ ...inviteForm, phoneNumber: e.target.value })}
                className="w-full mt-1 p-2 border border-gray-300 focus:border-blue-500 focus:ring-blue-500 rounded-md transition-colors"
                disabled={isInviting}
                placeholder="Enter phone number"
              />
              {inviteErrors.phoneNumber && <p className="text-xs text-red-500 mt-1">{inviteErrors.phoneNumber}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Role*</label>
              <select
                value={inviteForm.role}
                onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value as 'SUPER_ADMIN' | 'ADMIN' | 'HR' })}
                className="w-full mt-1 p-2 border border-gray-300 focus:border-blue-500 focus:ring-blue-500 rounded-md transition-colors"
                disabled={isInviting}
              >
                {currentUserRole === 'SUPER_ADMIN' && <option value="SUPER_ADMIN">Super Admin</option>}
                {(currentUserRole === 'SUPER_ADMIN' || currentUserRole === 'ADMIN') && <option value="ADMIN">Admin</option>}
                <option value="HR">HR</option>
              </select>
              {inviteErrors.role && <p className="text-xs text-red-500 mt-1">{inviteErrors.role}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Expiration (days)</label>
              <input
                type="number"
                min={1}
                max={365}
                value={inviteForm.expirationDays}
                onChange={(e) => setInviteForm({ ...inviteForm, expirationDays: Number(e.target.value) })}
                className="w-full mt-1 p-2 border border-gray-300 focus:border-blue-500 focus:ring-blue-500 rounded-md transition-colors"
                disabled={isInviting}
                placeholder="7"
              />
              <p className="text-xs text-gray-400 mt-1">How many days the invite link will remain valid (default: 7)</p>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={() => setInviteModalOpen(false)} disabled={isInviting}>Cancel</Button>
              <Button type="submit" variant="primary" disabled={!isInviteFormValid || isInviting} className="flex items-center gap-2">
                {isInviting ? <Loader2 size={16} className="animate-spin" /> : <Mail size={16} />} 
                {isInviting ? 'Sending...' : 'Send Invitation'}
              </Button>
            </div>
          </form>
        </ModernInviteModal>
      )}

      {/* Professional Edit Modal */}
      {editModalOpen && editingAdmin && (
        <ModernEditModal isOpen={editModalOpen} onClose={() => setEditModalOpen(false)} admin={editingAdmin}>
          <form onSubmit={handleEditSubmit} className="space-y-6">
            {editErrors.general && (
              <div className="flex items-start gap-3 text-sm text-red-700 bg-red-50 p-4 rounded-lg border border-red-200">
                <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
                <span>{editErrors.general}</span>
              </div>
            )}
            
            {/* Name Fields */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    First name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={editForm.first_name}
                    onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                    className={`w-full px-4 py-2.5 border rounded-lg transition-all duration-200 ${
                      editErrors.first_name 
                        ? 'border-red-300 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200' 
                        : 'border-gray-300 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                    } disabled:bg-gray-50 disabled:text-gray-500`}
                    disabled={isUpdating}
                    placeholder="Enter first name"
                  />
                  {editErrors.first_name && (
                    <p className="text-xs text-red-600 mt-1.5 flex items-center gap-1">
                      <X size={12} />
                      {editErrors.first_name}
                    </p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Last name
                  </label>
                  <input
                    type="text"
                    value={editForm.last_name}
                    onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all duration-200 disabled:bg-gray-50 disabled:text-gray-500"
                    disabled={isUpdating}
                    placeholder="Enter last name (optional)"
                  />
                </div>
              </div>
            </div>

            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email address
              </label>
              <input
                type="email"
                value={editForm.new_email}
                onChange={(e) => setEditForm({ ...editForm, new_email: e.target.value })}
                className={`w-full px-4 py-2.5 border rounded-lg transition-all duration-200 ${
                  editErrors.new_email 
                    ? 'border-red-300 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200' 
                    : 'border-gray-300 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                } disabled:bg-gray-50 disabled:text-gray-500`}
                disabled={isUpdating}
                placeholder="Enter new email address"
              />
              {editErrors.new_email ? (
                <p className="text-xs text-red-600 mt-1.5 flex items-center gap-1">
                  <X size={12} />
                  {editErrors.new_email}
                </p>
              ) : (
                <p className="text-xs text-gray-500 mt-1.5 flex items-center gap-1">
                  <Mail size={12} />
                  Leave unchanged to keep current email
                </p>
              )}
            </div>

            {/* Phone Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Phone number
              </label>
              <input
                type="text"
                value={editForm.phone_number}
                onChange={(e) => setEditForm({ ...editForm, phone_number: e.target.value })}
                className={`w-full px-4 py-2.5 border rounded-lg transition-all duration-200 ${
                  editErrors.phone_number
                    ? 'border-red-300 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-200'
                    : 'border-gray-300 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200'
                } disabled:bg-gray-50 disabled:text-gray-500`}
                disabled={isUpdating}
                placeholder="Enter phone number"
              />
              {editErrors.phone_number && (
                <p className="text-xs text-red-600 mt-1.5 flex items-center gap-1">
                  <X size={12} />
                  {editErrors.phone_number}
                </p>
              )}
            </div>

              {/* Role Selector (permission-aware) */}
              {currentUserRole !== 'HR' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                  <select
                    value={editForm.role}
                    onChange={(e) => setEditForm({ ...editForm, role: e.target.value as any })}
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                    disabled={isUpdating}
                  >
                    {currentUserRole === 'SUPER_ADMIN' && (
                      <>
                        <option value="SUPER_ADMIN">Super Admin</option>
                        <option value="ADMIN">Admin</option>
                        <option value="HR">HR</option>
                      </>
                    )}
                    {currentUserRole === 'ADMIN' && (
                      <>
                        <option value="ADMIN">Admin</option>
                        <option value="HR">HR</option>
                      </>
                    )}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">Changing role is restricted by your permissions.</p>
                </div>
              )}

              {/* Confirmation Link Expiry (days) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Confirmation link expiry (days)</label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={editForm.expirationDays}
                  onChange={(e) => setEditForm({ ...editForm, expirationDays: Number(e.target.value) })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                  disabled={isUpdating}
                  placeholder="7"
                />
                <p className="text-xs text-gray-500 mt-1">Number of days the confirmation link (email/phone/name) should remain valid. Default: 7</p>
              </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-6 border-t border-gray-200">
              <Button 
                type="button" 
                variant="secondary" 
                onClick={() => setEditModalOpen(false)} 
                disabled={isUpdating}
                className="px-6 py-2.5 text-sm font-medium"
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                variant="primary" 
                disabled={!isEditFormValid || isUpdating} 
                className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium shadow-md hover:shadow-lg"
              >
                {isUpdating ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>Saving Changes...</span>
                  </>
                ) : (
                  <>
                    <Check size={16} />
                    <span>Save Changes</span>
                  </>
                )}
              </Button>
            </div>
          </form>
        </ModernEditModal>
      )}
        </>
      ) : (
        /* Invitations Tab */
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <Mail size={20} className="text-gray-600" />
              Sent Invitations
            </h2>
            
            <div className="flex items-center gap-4">
              {(invitationStats || invitations.length > 0) && (
                <div className="flex gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Clock size={16} className="text-orange-500" />
                    <span>{(invitations.length > 0 ? computedInvitationStats.pending : (invitationStats?.pending ?? 0))} Pending</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle size={16} className="text-green-500" />
                    <span>{(invitations.length > 0 ? computedInvitationStats.accepted : (invitationStats?.accepted ?? 0))} Accepted</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <XCircle size={16} className="text-red-500" />
                    <span>{(invitations.length > 0 ? computedInvitationStats.expired : (invitationStats?.expired ?? 0))} Expired</span>
                  </div>
                </div>
              )}
              
              <Button
                onClick={fetchInvitations}
                variant="outline"
                className="rounded-lg px-3 h-10 text-sm flex items-center justify-center"
                disabled={isLoading}
              >
                <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
              </Button>
            </div>
          </div>

          {/* Invitations List */}
          <div className="space-y-3">
              {invitations.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <Mail size={48} className="mx-auto text-gray-300 mb-4" />
                <p className="text-lg font-medium">No invitations sent yet</p>
                <p className="text-sm">Start by inviting team members from the Admin Accounts tab</p>
              </div>
              ) : (
              invitations.map((invitation) => {
                const displayStatus = getInvitationDisplayStatus(invitation);
                return (
                <div
                  key={invitation.invitation_id}
                  className={`p-4 rounded-lg border ${
                    displayStatus === 'ACCEPTED' 
                      ? 'bg-green-50 border-green-200' 
                      : displayStatus === 'EXPIRED'
                      ? 'bg-red-50 border-red-200'
                      : 'bg-orange-50 border-orange-200'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-medium text-gray-900">
                          {invitation.invited_first_name} {invitation.invited_last_name}
                        </h3>
                        <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                          displayStatus === 'ACCEPTED'
                            ? 'bg-green-100 text-green-800'
                            : displayStatus === 'EXPIRED'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-orange-100 text-orange-800'
                        }`}>
                          {displayStatus}
                        </span>
                        <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                          {invitation.invited_role}
                        </span>
                      </div>
                      
                      <p className="text-sm text-gray-600 mb-2">{invitation.invited_email}</p>
                      
                      <div className="flex gap-4 text-xs text-gray-500">
                        <span>Sent: {new Date(invitation.created_at).toLocaleDateString()}</span>
                        {invitation.accepted_at && (
                          <span>Accepted: {new Date(invitation.accepted_at).toLocaleDateString()}</span>
                        )}
                        {(displayStatus === 'PENDING' || displayStatus === 'EXPIRED') && (
                          <span>Expires: {new Date(invitation.expires_at).toLocaleDateString()}</span>
                        )}
                      </div>
                      
                    </div>
                    
                    <div className="ml-4">
                      {displayStatus === 'ACCEPTED' ? (
                        <CheckCircle size={20} className="text-green-500" />
                      ) : displayStatus === 'EXPIRED' ? (
                        <XCircle size={20} className="text-red-500" />
                      ) : (
                        <Clock size={20} className="text-orange-500" />
                      )}
                    </div>
                  </div>
                </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Shared avatar color helper for both invite and edit modals
const getAvatarColor = (name: string) => {
  const colors = [
    'bg-blue-500',
    'bg-indigo-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-teal-500',
    'bg-green-500'
  ];
  const index = (name || '').length % colors.length;
  return colors[index];
};

// Modern Invite Modal (shares visuals/animation with ModernEditModal)
interface ModernInviteModalProps {
  isOpen: boolean;
  onClose: () => void;
  name: string;
  email: string;
  role: string;
  children: React.ReactNode;
}

const ModernInviteModal: React.FC<ModernInviteModalProps> = ({ isOpen, onClose, name, email, role, children }) => {
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    if (isOpen) {
      const t = setTimeout(() => setVisible(true), 10);
      return () => clearTimeout(t);
    }
    setVisible(false);
  }, [isOpen]);

  if (!isOpen) return null;

  const initials = (name || '').split(' ').map(n => n[0]?.toUpperCase()).slice(0,2).join('') || 'A';

  const closeWithAnimation = () => {
    setVisible(false);
    setTimeout(() => onClose(), 220);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-start justify-center bg-black/40 backdrop-blur-sm transition-opacity duration-200 ${visible ? 'opacity-100' : 'opacity-0'}`}
      style={{ paddingTop: '2rem', paddingBottom: '6rem', overflowY: 'auto' }}
      aria-modal="true"
      role="dialog"
      onClick={closeWithAnimation}
    >
      <div
        className={`relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 my-4 transform transition-all duration-200 ${visible ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-3 scale-95'}`}
        style={{ maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Decorative header with accent and close button */}
        <div className="relative overflow-hidden rounded-t-2xl" style={{ background: 'linear-gradient(90deg,#eef2ff 0%,#eef6ff 100%)' }}>
          <button
            onClick={closeWithAnimation}
            className="absolute top-4 right-4 z-20 p-2 rounded-lg bg-white/80 backdrop-blur-sm text-gray-500 hover:text-gray-700 hover:bg-white transition-all duration-200 shadow-sm"
            aria-label="Close"
          >
            <X size={20} />
          </button>

          <div className="absolute -left-20 -top-10 opacity-30 transform rotate-12 w-56 h-56 bg-gradient-to-br from-indigo-200 to-blue-200 rounded-full blur-2xl pointer-events-none" />

          <div className="flex items-center gap-6 p-8 relative z-10">
            <div className={`flex-shrink-0 w-20 h-20 rounded-full ${getAvatarColor(name)} flex items-center justify-center text-white text-2xl font-bold shadow-md ring-4 ring-white`}>
              {initials}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-2xl font-extrabold text-gray-900 leading-tight">Invite New Administrator</h2>
                <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${getRoleBadgeClasses(role)}`}>
                  {formatRoleName(role)}
                </span>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <Mail size={14} className="text-gray-400" />
                <span className="truncate">{email || 'Email not specified'}</span>
                <span className="ml-2 text-xs text-gray-400">•</span>
                <span className="text-xs text-gray-400">Expires in 7 days</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 sm:p-8">
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">Invite Administrator</h3>
            <p className="text-sm text-gray-500">Fill out the details to send an invitation link to the user.</p>
          </div>

          <div className="space-y-4">{children}</div>
        </div>

        {/* Sticky action/footer area to keep primary actions always visible */}
        <div className="w-full border-t border-gray-100 p-4 bg-white/70 backdrop-blur-sm sticky bottom-0">
          <div className="max-w-2xl mx-4 flex items-center justify-end gap-3">
            <button className="px-4 py-2 rounded-md text-sm font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 transition" onClick={closeWithAnimation}>Cancel</button>
            {/* Note: the real submit button lives inside the child form; we render a subtle hint button for UX */}
            <button className="px-4 py-2 rounded-md text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition shadow" onClick={() => {
              // Try to submit any form inside the modal if present
              const form = document.querySelector('#invite-form') as HTMLFormElement | null;
              if (form) form.requestSubmit();
            }}>
              Send Invite
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminManagementTab;