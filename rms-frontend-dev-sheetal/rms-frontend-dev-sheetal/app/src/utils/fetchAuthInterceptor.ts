import { EXCLUDED_PATHS } from '../config/excludedRoutes';

export function installFetchAuthInterceptor(): void {
  if (typeof window === 'undefined' || !(window as any).fetch) return;
  if ((window as any).__fetchAuthInterceptorInstalled) return;

  const originalFetch = (window as any).fetch.bind(window);

  (window as any).fetch = async (input: RequestInfo, init?: RequestInit) => {
    const resp = await originalFetch(input, init);
    try {
      // Derive a request URL string to decide whether this is a public/career endpoint
      let requestUrl = '';
      try {
        if (typeof input === 'string') requestUrl = input as string;
        else if ((input as Request).url) requestUrl = (input as Request).url;
      } catch {
        requestUrl = '';
      }

      // Use centralized exclusion list to skip dispatch for public/career endpoints
      const isExcluded = EXCLUDED_PATHS.some((s) => {
        try { return requestUrl === s || requestUrl.startsWith(s) || requestUrl.includes(s); } catch { return false; }
      });

      if (!isExcluded && resp && (resp.status === 401 || resp.status === 403)) {
        window.dispatchEvent(new CustomEvent('auth-error', {
          detail: {
            status: resp.status,
            message: resp.status === 401 ? 'Your session has expired. Please sign in again.' : 'Access denied. Please sign in again.',
          }
        }));
        try {
          localStorage.setItem('logout-event', Date.now().toString());
        } catch {
          // ignore storage failures
        }
      }
    } catch {
      // best-effort: swallow dispatch/notification errors only
    }
    return resp;
  };

  (window as any).__fetchAuthInterceptorInstalled = true;
}

export default installFetchAuthInterceptor;
