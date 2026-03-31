// rms-frontend-demo/app/src/api/axiosConfig.ts
// (The final fix: withCredentials is set to false)

import axios from "axios";
import { AUTH_CONFIG } from '../constants/auth';
import { EXCLUDED_PATHS } from '../config/excludedRoutes';

// -----------------------------------------------------------------
// TAB-SPECIFIC TOKEN & ID MANAGEMENT (SINGLE SOURCE OF TRUTH)
// -----------------------------------------------------------------
const tabTokenMap = new Map<string, string>();
const TAB_ID_KEY = 'currentTabId'; // The key for sessionStorage
const TOKEN_STORAGE_PREFIX = 'token_'; // The prefix for localStorage

/**
 * Gets the unique, persistent ID for the current browser tab.
 * If one doesn't exist in sessionStorage, it creates one.
 * This is the SINGLE source of truth for the tabId.
 */
function getTabId(): string {
  let tabId = sessionStorage.getItem(TAB_ID_KEY);
  if (!tabId) {
    tabId = `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    sessionStorage.setItem(TAB_ID_KEY, tabId);
  }
  return tabId;
}

/**
 * Gets the auth token for the *current* tab.
 * It checks in-memory cache first, then tab-specific localStorage.
 */
function getTokenForCurrentTab(): string | null {
  const tabId = getTabId();
  
  // 1. First check in-memory cache (fast)
  let token = tabTokenMap.get(tabId);
  if (token) {
    return token ?? null;
  }
  
  // 2. If not in memory, check localStorage (persistent across page reloads)
  const storageKey = `${TOKEN_STORAGE_PREFIX}${tabId}`;
  token = localStorage.getItem(storageKey) ?? undefined;
  
  if (token) {
    // Restore to in-memory cache
    tabTokenMap.set(tabId, token);
  }
  
  return token ?? null;
}

/**
 * Sets the auth token for the *current* tab.
 * Stores it in both the in-memory cache and tab-specific localStorage.
 */
function setTokenForCurrentTab(token: string): void {
  const tabId = getTabId();
  const storageKey = `${TOKEN_STORAGE_PREFIX}${tabId}`;
  
  tabTokenMap.set(tabId, token);
  localStorage.setItem(storageKey, token);
}

/**
 * Clears the auth token for the *current* tab from all storage.
 */
function clearTokenForCurrentTab(): void {
  const tabId = getTabId();
  tabTokenMap.delete(tabId);
  localStorage.removeItem(`${TOKEN_STORAGE_PREFIX}${tabId}`);
}

/**
 * Returns true when the provided JWT is missing or expired.
 * Treats parse failures as expired for safety.
 */
function isJwtExpired(token: string | null): boolean {
  if (!token) return true;
  try {
    const parts = token.split('.');
    if (parts.length < 2) return true;
    const payload = JSON.parse(atob(parts[1]));
    // `exp` is seconds since epoch in most JWTs
    const expMs = (payload?.exp || 0) * 1000;
    return expMs <= Date.now();
  } catch {
    return true;
  }
}

// -----------------------------------------------------------------
// AXIOS INSTANCE CREATION
// -----------------------------------------------------------------

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"; 
const axiosInstance = axios.create({
  baseURL: `${BACKEND_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },

  // 💡💡💡 THE FIX 💡💡💡
  // Set to false. We are using Bearer tokens, not cookies.
  // This stops the browser from sending a shared cookie
  // and forces the backend to read our tab-specific 'Authorization' header.
  withCredentials: false, 

  timeout: 30000, // 30 seconds timeout
});

console.log('[api] axios baseURL =', axiosInstance.defaults.baseURL);

// -----------------------------------------------------------------
// AXIOS INTERCEPTORS
// -----------------------------------------------------------------

axiosInstance.interceptors.request.use(
  (config) => {
    // Get token from our tab-safe function
    const token = getTokenForCurrentTab();
    const requestUrl = (config && config.url) ? String(config.url) : '';
    const isExcluded = EXCLUDED_PATHS.some((p) => {
      try { return requestUrl === p || requestUrl.startsWith(p) || requestUrl.includes(p); } catch { return false; }
    });

    if (!isExcluded && token && isJwtExpired(token)) {
      try {
        window.dispatchEvent(new CustomEvent('auth-error', {
          detail: {
            status: 401,
            message: 'Your session has expired. Please sign in again.',
          }
        }));
      } catch {
        // no-op
      }
      try {
        localStorage.setItem('logout-event', Date.now().toString());
      } catch {
        // no-op
      }
      try { clearTokenForCurrentTab(); } catch {
        // no-op
      }
      return Promise.reject(new Error('Auth token expired'));
    }

    if (token) {
      // This header will now be the ONLY source of auth
      config.headers.Authorization = `Bearer ${token}`;
      
      if (import.meta.env.DEV) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          console.log('🔍 JWT Token Debug (Header):', {
            endpoint: config.url,
            tabId: getTabId(),
            subValue: payload.sub,
            role: payload.role,
          });
        } catch {
          // ignore
        }
      }
    } else if (!isExcluded) {
      console.warn('⚠️ No auth token found for tab:', getTabId());
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ... (your response interceptor remains unchanged) ...
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
        console.error("API Error: 🚨 NETWORK CONNECTION FAILED 🚨", {
            message: error.message,
            code: error.code
        });
        
        if (error.code === 'ERR_NETWORK') {
            error.message = 'Cannot connect to the server. Please check your network connection.';
        } else if (error.code === 'ECONNABORTED') {
            error.message = 'Request timed out. Please try again.';
        } else {
            error.message = AUTH_CONFIG.ERROR_MESSAGES.NETWORK_ERROR;
        }
        window.dispatchEvent(new CustomEvent('network-error', { 
            detail: { message: error.message } 
        }));
    } 
    else if (error.response.status === 401 || error.response.status === 403) {
        const requestUrl = (error.config && error.config.url) ? String(error.config.url) : (error.response?.config?.url ? String(error.response.config.url) : '');
        const isExcluded = EXCLUDED_PATHS.some((p) => {
          try { return requestUrl === p || requestUrl.startsWith(p) || requestUrl.includes(p); } catch { return false; }
        });

        if (isExcluded) {
          return Promise.reject(error);
        }

        console.warn(`API Error: ${error.response.status} ${error.response.status === 401 ? 'Unauthorized' : 'Forbidden'}. Session may be invalid.`);
        try {
          // Include the request URL so listeners can decide to ignore protected/public routes
          window.dispatchEvent(new CustomEvent('auth-error', {
            detail: {
              status: error.response.status,
              message: error.response.status === 401 
                ? 'Your session may have expired. Please sign in again.'
                : 'You do not have permission to access this resource. Please sign in again.',
              url: requestUrl,
            },
          }));
          // Also write a cross-tab logout-event so other tabs and the
          // LogoutListener (which listens to storage) will show the modal
          // even if the auth-error event misses a listener.
          try {
            localStorage.setItem('logout-event', Date.now().toString());
          } catch {
            // ignore storage failures
          }
        } catch (eventError) {
          console.error('Failed to dispatch auth-error event', eventError);
        }
    }
    else {
          const status = error.response.status;
          const respData = error.response.data;
          let backendMessage = 'No message provided.';
          if (respData) {
            if (typeof respData === 'string') backendMessage = respData;
            else if (respData.message) backendMessage = respData.message;
            else if (respData.error) backendMessage = respData.error;
            else if (respData.detail) backendMessage = typeof respData.detail === 'string' ? respData.detail : JSON.stringify(respData.detail);
            else backendMessage = JSON.stringify(respData);
          }
          console.error(`API Error ${status}: ${backendMessage}`, { responseData: respData });
          error.message = backendMessage;
          try {
            window.dispatchEvent(new CustomEvent('api-error', { detail: { status, body: respData, message: backendMessage } }));
          } catch {
            // no-op
          }
    }
    return Promise.reject(error);
  }
);


export default axiosInstance;

// Export the *single source of truth* functions
export { getTokenForCurrentTab, setTokenForCurrentTab, clearTokenForCurrentTab, getTabId };