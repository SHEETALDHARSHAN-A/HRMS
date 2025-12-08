// rms-frontend-demo/app/src/components/router/ProtectedRoute.tsx
// (Updated with improved debugging)

import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useUser } from '../../context/UserContext';
import MultiAccountManager from '../../utils/multiAccountManager';

// Define explicit roles for clear type safety and constants
export type UserRole = 'CANDIDATE' | 'ADMIN' | 'SUPER_ADMIN' | 'HR';

interface ProtectedRouteProps {
  // Roles allowed to access this specific route
  allowedRoles?: UserRole[]; 
  // The default landing page for authenticated but unauthorized users
  unauthorizedRedirectPath?: string; 
}

/**
 * A protected route component that handles both authentication and authorization.
 * It reads session data from MultiAccountManager, which is the source of truth
 * for the current tab's session.
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  allowedRoles,
  unauthorizedRedirectPath = '/career-page', // Default to candidate page
}) => {
  // Fallback context, but MultiAccountManager is the primary source
  const { user: userFromContext } = useUser();
  
  // 1. Get the current session from the singleton manager
  const accountManager = MultiAccountManager.getInstance();
  const currentSession = accountManager.getCurrentSession();
  
  // 2. Check Authentication
  // We are authenticated if the session exists and has either user data or a token.
  // This supports both cookie-based (user data only) and token-based (token + user data) flows.
  const hasStoredUser = !!(currentSession && currentSession.user && Object.keys(currentSession.user).length > 0);
  const hasToken = !!(currentSession && currentSession.authToken);
  const isAuthenticated = !!(currentSession && (hasToken || hasStoredUser));

  // 3. Check for Authentication
  if (!isAuthenticated) {
    // If no session at all, redirect to login.
    return <Navigate to="/auth" replace />;
  }

  // 4. Extract User Role
  // We must find a valid role to proceed.
  let userRole: UserRole | undefined;
  
  if (currentSession.userRole) {
    // Priority 1: Role stored at the top level of the session (from 3rd arg)
    userRole = currentSession.userRole as UserRole;
  } else if (currentSession.user?.role) {
    // Priority 2: Role stored inside the session's user object (from 2nd arg)
    const sessionUserRole = currentSession.user.role;
    if (typeof sessionUserRole === 'string') {
      userRole = sessionUserRole as UserRole;
    } else if (Array.isArray(sessionUserRole) && sessionUserRole.length > 0) {
      userRole = sessionUserRole[0] as UserRole;
    }
  } else if (userFromContext?.role) {
    // Priority 3: Fallback to the UserContext (might be stale)
    const contextRole = (userFromContext as any).role || (userFromContext as any).user_role;
    if (typeof contextRole === 'string') {
      userRole = contextRole as UserRole;
    } else if (Array.isArray(contextRole) && contextRole.length > 0) {
      userRole = contextRole[0] as UserRole;
    }
  }
  
  // 5. Handle Authenticated Users WITH NO ROLE
  // This is the check that was causing your redirect loop.
  if (!userRole) {
    // We are authenticated but have no role. This is a critical state error.
    // The useAuth hook likely failed to save the role on login.
    
    // 💡 IMPROVED LOGGING:
    console.error(
      'ProtectedRoute Error: Authenticated user has no valid role. This is the cause of the redirect loop.'
    );
    console.warn('Failing session data (from MultiAccountManager):', JSON.stringify(currentSession));
    console.warn('Failing context data (from UserContext):', JSON.stringify(userFromContext));
    console.warn('Redirecting to /auth to force re-authentication.');

    // Clear the broken session to prevent an infinite loop
    accountManager.clearCurrentSession();
    return <Navigate to="/auth" replace />;
  }

  // 6. Check Authorization
  if (allowedRoles && allowedRoles.length > 0) {
    // SUPER_ADMIN gets universal access
    const isSuperAdmin = userRole === 'SUPER_ADMIN';

    // Check if the user's role is in the allowed list
    const isAuthorized = isSuperAdmin || allowedRoles.includes(userRole);

    if (!isAuthorized) {
      // User is authenticated but not authorized for this *specific* page.
      // Redirect them to their default landing page.
      console.warn(
        `Authorization Failed: User with role '${userRole}' tried to access a route limited to '${allowedRoles.join(', ')}'.`,
        `Redirecting to '${unauthorizedRedirectPath}'.`
      );
      return <Navigate to={unauthorizedRedirectPath} replace />;
    }
  }
  
  // 7. Success
  // User is authenticated and authorized. Render the requested component.
  return <Outlet />;
};

export default ProtectedRoute;