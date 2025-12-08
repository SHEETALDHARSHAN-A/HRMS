import React, { useEffect, useRef } from 'react';
import { useModal } from '../../context/ModalContext';
import MultiAccountManager from '../../utils/multiAccountManager';
import { clearTokenForCurrentTab } from '../../api/axiosConfig';

const LogoutListener: React.FC = () => {
  const { showConfirm } = useModal();
  const lastSeenRef = useRef<string | null>(null);
  const showingRef = useRef(false);

  const showLogoutModal = async (message?: string) => {
    if (showingRef.current) return;
    showingRef.current = true;

    try {
      const confirmed = await showConfirm({
        title: 'Session terminated',
        message: message || 'Your session has been terminated. Please sign in again.',
        confirmText: 'Sign in',
        cancelText: 'Cancel',
        isDestructive: false,
      });

      if (confirmed) {
        try {
          const manager = MultiAccountManager.getInstance();
          manager.clearCurrentSession();
          clearTokenForCurrentTab();
          try { localStorage.setItem('logout-event', Date.now().toString()); } catch (e) {}
          window.location.href = '/auth';
        } catch (err) {
          console.error('LogoutListener: error during logout', err);
          window.location.href = '/auth';
        }
      } else {
        // allow future events to show again
        setTimeout(() => { showingRef.current = false; }, 1500);
      }
    } catch (err) {
      console.error('LogoutListener showConfirm failed', err);
      showingRef.current = false;
    }
  };

  useEffect(() => {
    // On mount, record the current logout-event value
    try {
      lastSeenRef.current = localStorage.getItem('logout-event');
    } catch (e) {
      lastSeenRef.current = null;
    }

    // If there's an existing logout-event stamp, show the modal
    try {
      const stamp = localStorage.getItem('logout-event');
      if (stamp && stamp !== lastSeenRef.current) {
        // The tab was opened after a logout — force the modal
        showLogoutModal();
        lastSeenRef.current = stamp;
      }
    } catch (e) {
      // ignore
    }

    const onStorage = (e: StorageEvent) => {
      if (e.key === 'logout-event') {
        const msg = (e.newValue && typeof e.newValue === 'string') ? undefined : undefined;
        showLogoutModal(msg);
        lastSeenRef.current = e.newValue;
      }
    };

    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  return null;
};

export default LogoutListener;
