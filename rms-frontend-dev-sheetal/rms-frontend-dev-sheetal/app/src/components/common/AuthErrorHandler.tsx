import React, { useEffect, useRef, useState } from 'react';
import MultiAccountManager from '../../utils/multiAccountManager';
import { clearTokenForCurrentTab } from '../../api/axiosConfig';
import LoginConfirmModal from './LoginConfirmModal';
import { EXCLUDED_PATHS } from '../../config/excludedRoutes';

/**
 * Global listener for 'auth-error' events emitted by the axios client.
 * Shows a confirmation modal asking the user to sign in again and performs
 * a local logout (clears current tab session, notifies other tabs, redirects).
 */
const AuthErrorHandler: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState<string>('');
  const shownRef = useRef(false);
  const pendingMsgRef = useRef<string | null>(null);

  useEffect(() => {
    const authErrorHandler = async (ev?: Event) => {
      console.debug('[AuthErrorHandler] received event', ev);
      const detail = (ev as any)?.detail || {};
      // If the event includes a request URL and it's in the excluded list, ignore it.
      try {
        const url = detail.url || '';
        if (url && EXCLUDED_PATHS.some((p) => {
          try { return url === p || url.startsWith(p) || url.includes(p); } catch { return false; }
        })) {
          console.debug('[AuthErrorHandler] Ignoring auth-error for excluded URL:', url);
          return;
        }
      } catch {
        // ignore errors while checking excluded list
      }
      const status = detail.status;

      // Only handle auth errors (401, 403)
      if (status !== 401 && status !== 403) return;

      // Avoid showing the modal multiple times in a short period
      if (shownRef.current) return;
      shownRef.current = true;

      const msg = detail.message || 'Your session is no longer valid. For your security, you need to sign in again.';

      // If the tab is hidden (user is on another tab or window), defer showing
      // the modal until they return (visibilitychange or focus). This avoids
      // interrupting other work and matches the desired behavior.
      if (typeof document !== 'undefined' && document.hidden) {
        // store pending message and set up listeners to show on return
        pendingMsgRef.current = msg;

        const showOnReturn = () => {
          // Only show once
          if (!pendingMsgRef.current) return;
          setMessage(pendingMsgRef.current);
          setIsOpen(true);
          pendingMsgRef.current = null;
          // cleanup
          try { window.removeEventListener('focus', showOnReturn); } catch {
            // no-op
          }
          try { document.removeEventListener('visibilitychange', visibilityHandler); } catch {
            // no-op
          }
        };

        const visibilityHandler = () => {
          if (document.visibilityState === 'visible') {
            showOnReturn();
          }
        };

        // Listen for either focus or visibilitychange
        window.addEventListener('focus', showOnReturn);
        document.addEventListener('visibilitychange', visibilityHandler);
      } else {
        // Tab is visible — show immediately
        setMessage(msg);
        setIsOpen(true);
      }
    };

  window.addEventListener('auth-error', authErrorHandler as EventListener);

    return () => {
      window.removeEventListener('auth-error', authErrorHandler as EventListener);
    };
  }, []);

  const handleConfirm = async () => {
    try {
      const manager = MultiAccountManager.getInstance();
      manager.clearCurrentSession();
      clearTokenForCurrentTab();
      try { localStorage.setItem('logout-event', Date.now().toString()); } catch {
        // no-op
      }
      window.location.href = '/auth';
    } catch (e) {
      console.error('Error during forced logout', e);
      window.location.href = '/auth';
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    // allow future auth-error modals to show
    setTimeout(() => { shownRef.current = false; }, 2000);
  };

  return (
    <>
      <LoginConfirmModal isOpen={isOpen} message={message} onClose={handleClose} onConfirm={handleConfirm} />
    </>
  );
};

export default AuthErrorHandler;
