// rms-frontend-dev-sheetal/app/src/App.tsx
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import JobRecruitmentPage from "./pages/JobRecruitment";

import { useEffect } from "react";
import JobPostsPage from "./pages/JobPosts";
import { UserProvider } from "./context/UserContext";
import { ThemeProvider } from "./context/ThemeContext";
import { NotificationProvider } from "./context/NotificationContext";
import { ToastProvider } from "./context/ToastContext";
import DashboardPage from "./pages/Dashboard";
import AuthPage from "./pages/AuthPage";
import { ModalProvider } from "./context/ModalContext"; 
import CareerPage from "./pages/Career/CareerPage";
import JobApplicationPage from "./pages/Career/JobApplicationPage"; 
import ConfigurationPage from "./pages/Configuration/ConfigurationPage"; 
import AdminSetupCompletionPage from "./pages/Auth/AdminSetupCompletionPage";
import AdminNameCompletionPage from "./pages/Auth/AdminNameCompletionPage";
// import VerificationProcessing from "./components/VerificationProcessing";

import ProtectedRoute from "./components/router/ProtectedRoute";
import type { UserRole } from "./components/router/ProtectedRoute";
import { getCurrentUser } from "./utils/authUtils";
import AuthErrorHandler from './components/common/AuthErrorHandler';
import LogoutListener from './components/common/LogoutListener';

import ControlHubPage from "./pages/ControlHub";
import EmailVerificationHandler from './pages/Auth/EmailVerificationHandler';
import EmailUpdateSuccessPage from './pages/Auth/EmailUpdateSuccessPage';
import MultiAccountManager from './utils/multiAccountManager';
import InterviewLoginPage from "./pages/Interview/InterviewLoginPage";
import InterviewThankYou from "./pages/Interview/InterviewThankYou";
import InterviewCodingPage from "./pages/Interview/InterviewCodingPage";
import AgentHubPage from './pages/AgentHub/AgentHubPage';
import installFetchAuthInterceptor from './utils/fetchAuthInterceptor';
/**
 * Redirects authenticated users using multi-account system.
 * - Admins go to /dashboard.
 * - All others (including candidates, though they shouldn't be auth'd) go to /career-page.
 */
const RoleBasedRedirect = () => {
  const accountManager = MultiAccountManager.getInstance();
  const currentSession = accountManager.getCurrentSession();
  const authenticated = !!(currentSession && currentSession.authToken);
  
  if (!authenticated) {
    // If not authenticated, default to public career page
    return <Navigate to="/career-page" replace />;
  }
  
  // Get role from current session (tab-specific)
  let userRole = currentSession.userRole;
  
  // Fallback to legacy authUtils for backward compatibility
  if (!userRole) {
    const user = getCurrentUser();
    if (user?.role) {
      if (typeof user.role === 'string') {
        userRole = user.role;
      } else if (Array.isArray(user.role) && user.role.length > 0) {
        userRole = user.role[0];
      }
    }
  }
  
  // 💡 MODIFICATION: All admin roles (including HR) should be auth'd. Send them to dashboard.
  if (userRole === 'ADMIN' || userRole === 'SUPER_ADMIN' || userRole === 'HR') {
    return <Navigate to="/dashboard" replace />;
  }
  
  // Default for any other case (e.g., old candidate session) is career page
  return <Navigate to="/career-page" replace />;
};

function App() {
  // Ensure global fetch calls will trigger the same auth-error event
  // that axios responses use for 401/403, allowing the AuthErrorHandler
  // modal to appear for non-axios network requests as well.
  installFetchAuthInterceptor();
  useEffect(() => {
    // Validate current tab's session on mount
    const accountManager = MultiAccountManager.getInstance();
    const currentSession = accountManager.getCurrentSession();
    
    if (!currentSession) {
      console.warn('⚠️ No session detected for this tab');
    }
    // NOTE: storage events are handled by the LogoutListener which shows
    // a modal before redirecting so the user sees the "session terminated" UI.
  }, []);
  
  const adminAndSuperAdmin: UserRole[] = ['ADMIN', 'SUPER_ADMIN', 'HR'];

  return (
    <ThemeProvider>
      <Router>
        <UserProvider>
          <NotificationProvider>
            <ToastProvider>
              <ModalProvider>
            {/* Global auth-error handler: shows a forced-logout modal when a 401 occurs */}
            <AuthErrorHandler />
            {/* Listen for cross-tab logout events and show a "session terminated" modal */}
            <LogoutListener />
            <Routes>
            {/* --- PUBLIC ROUTES --- */}
            <Route path="/career-page" element={<CareerPage />} /> 
            {/* 💡 MODIFIED: /apply/:jobId is now a public route */}
            <Route path="/apply/:jobId" element={<JobApplicationPage />} /> 
            {/* /interview/join is now a public route */}
            <Route path="/interview/join" element={<InterviewLoginPage />} />
            <Route path="/interview/thank-you" element={<InterviewThankYou />} />
            <Route path="/interview/coding" element={<InterviewCodingPage />} />

            {/* Admin Setup/Verification Routes (Publicly Accessible via email link) */}
            <Route path="/auth/complete-admin-setup" element={<AdminSetupCompletionPage />} />
            <Route path="/auth/complete-name-update" element={<AdminNameCompletionPage />} />
            <Route path="/auth/verify-email-update" element={<EmailVerificationHandler />} />
            <Route path="/auth/email-update-success" element={<EmailUpdateSuccessPage />} />
            
            {/* Verification Processing Page - Shows loading then confirmation for email verification links */}
            <Route path="/verification/processing" element={<AdminSetupCompletionPage />} />
            
            {/* 💡 MODIFIED: /auth route - Always show AuthPage, let it handle internal logic */}
            <Route
              path="/auth"
              element={<AuthPage />}
            />

            {/* --- ADMIN & SUPER_ADMIN PROTECTED ROUTES --- */}
            <Route element={<ProtectedRoute allowedRoles={adminAndSuperAdmin} unauthorizedRedirectPath="/career-page" />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/jobs/my-jobs" element={<JobPostsPage />} />
                <Route path="/jobs/all-jobs" element={<JobPostsPage />} />
                <Route path="/jobs/:jobId" element={<JobPostsPage />} /> {/* Route for direct link/form */}
                <Route path="/control-hub" element={<ControlHubPage />} />
                <Route path="/job-recruitment" element={<JobRecruitmentPage />} />
                <Route path="/settings" element={<ConfigurationPage />} />
                <Route path="/interview-agent" element={<AgentHubPage />} />
            </Route>
            
            {/* --- ROOT & FALLBACKS --- */}
            <Route
              path="/"
              element={<RoleBasedRedirect />} // Will send admins to /dashboard, public to /career-page
            />
            <Route
              path="*"
              element={<RoleBasedRedirect />} // Send any other route to the same logic
            />
              
            </Routes>

            
              </ModalProvider>
            </ToastProvider>
          </NotificationProvider>
        </UserProvider>
      </Router>
    </ThemeProvider>
  );
}

export default App;