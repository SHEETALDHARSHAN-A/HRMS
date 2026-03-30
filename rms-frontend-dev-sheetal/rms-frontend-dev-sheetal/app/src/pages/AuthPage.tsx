// // rms-frontend-dev-sheetal/app/src/pages/AuthPage.tsx
// import AuthLeftPanel from '../components/auth/AuthLeftPanel';
// import AuthRightPanel from '../components/auth/AuthRightPanel';
// import { AuthProvider } from '../context/AuthContext';
// import { useSearchParams, useNavigate } from 'react-router-dom';
// import { useToast } from '../context/ModalContext';
// import { useEffect } from 'react';
// import { clearAllAuthData } from '../utils/authUtils';
// import { CheckCircle, AlertTriangle, LogIn } from 'lucide-react';
// import Logo from '../components/auth/Logo';
// import Button from '../components/common/Button';

// // --- Dedicated Status Component (Responsive Adjustments) ---
// // This component handles the redirect from email verification links
// // Accept both email update success and transfer-approval statuses.
// const VerificationStatus: React.FC<{ status: 'email_updated' | 'email_transfer_approved' | 'error', email?: string, message?: string }> = ({
//   status,
//   email,
//   message,
// }) => {
//     const navigate = useNavigate();
//     const { showToast } = useToast();

//     useEffect(() => {
//         // This page is a terminal step after verification, so we clear all auth data
//         // to force the admin to log in again (especially after an email change).
//         clearAllAuthData();

//     if (status === 'email_updated' && email) {
//       showToast(`Email updated successfully to ${email}. Please sign in with your new email.`, 'success');
//     } else if (status === 'email_transfer_approved') {
//       // The admin approved the transfer from their current email; inform them and prompt login.
//       const msg = email ? `Approval recorded. A verification email has been sent to ${email}.` : 'Approval recorded. A verification email has been sent to the new address.';
//       showToast(msg, 'success');
//     } else if (status === 'error' && message) {
//       showToast(`Verification failed: ${message}`, 'error');
//     }

//         // Clean the URL query parameters
//         window.history.replaceState({}, document.title, window.location.pathname);
//     }, [status, email, message, showToast]);

//   const isSuccess = status === 'email_updated' || status === 'email_transfer_approved';
//   const displayMessage = isSuccess
//     ? (status === 'email_updated'
//       ? `Your email address has been successfully updated${email ? ` to ${email}` : ''}. You must log in with the new email now.`
//       : (email ? `Approval recorded. A verification email has been sent to ${email}. Please sign in once you've verified.` : `Approval recorded. A verification email has been sent to the new address.`)
//       )
//     : message || "An unexpected error occurred during verification. Please contact support.";

//     return (
//         <div className="flex-1 p-4 sm:p-8 md:p-12 flex flex-col justify-center items-center relative z-10 bg-transparent w-full">
//             <div className="bg-white p-6 sm:p-8 md:p-10 rounded-xl shadow-2xl w-full max-w-md flex flex-col items-center text-center">
//                 <Logo size="medium" className="mb-6 sm:mb-8" />

//                 {isSuccess ? (
//                     <>
//                         <CheckCircle size={40} className="text-green-500 mb-4 sm:mb-6 sm:w-12 sm:h-12" />
//                         <h1 className="text-lg sm:text-xl font-bold text-green-700 mb-2">Verification Complete!</h1>
//                     </>
//                 ) : (
//                     <>
//                         <AlertTriangle className="text-red-500 mb-4 sm:mb-6 w-10 h-10 sm:w-12 sm:h-12" />
//                         <h1 className="text-lg sm:text-xl font-bold text-red-700 mb-2">Update Failed</h1>
//                     </>
//                 )}

//                 <p className="text-gray-700 text-sm mb-6">{displayMessage}</p>

//                 <Button
//                     onClick={() => navigate('/auth')}
//                     variant="primary"
//                     className="w-full sm:w-40 py-2.5 sm:py-2 text-sm sm:text-base"
//                 >
//                     <LogIn size={16} /> Go to Login
//                 </Button>
//             </div>
//         </div>
//     );
// };

// // --- Main Auth Page Content Logic ---
// const AuthPageContent = () => {
//   const [searchParams] = useSearchParams();

//   const status = searchParams.get('status');
//   const email = searchParams.get('new_email');
//   const encodedMessage = searchParams.get('message');

//   // Check if we are on a verification redirect URL
//   const showStatusPage = status === 'email_updated' || status === 'error' || status === 'email_transfer_approved' || status === 'email_transfer_error';

//   if (showStatusPage) {
//       const message = encodedMessage ? decodeURIComponent(encodedMessage) : undefined;
//       // Re-use the VerificationStatus component for all redirect statuses
//       return (
//         <VerificationStatus
//             status={status as 'email_updated' | 'error'} // Cast to known statuses
//             email={email || undefined}
//             message={message}
//         />
//       );
//   }

//   // --- MODIFICATION ---
//   // Default to the Admin Login page
//   // We no longer need the AuthProvider here, as the RightPanel will
//   // directly render the SignInForm. We wrap the forms themselves
//   // in the AuthProvider instead.
//   return (
//     <>
//         <AuthLeftPanel />
//         {/* AuthRightPanel will now internally use AuthProvider */}
//         <AuthRightPanel />
//     </>
//   );
// };

// /**
//  * Main Auth Page Wrapper.
//  * This page is now exclusively for Admin Sign-In.
//  * Candidate Sign-Up is removed.
//  */
// const AuthPage = () => {
//   return (
//     // AuthProvider is now wrapped around the content that needs it
//     <AuthProvider>
//       <div
//         className="min-h-screen w-screen flex items-center justify-center bg-white"
//       >
//         <div
//           className="flex w-screen h-screen overflow-hidden relative"
//           style={{
//             backgroundColor: 'white',
//           }}
//         >
//           <AuthPageContent />
//         </div>
//       </div>
//     </AuthProvider>
//   );
// };

// export default AuthPage;

// rms-frontend-dev-sheetal/app/src/pages/AuthPage.tsx

import AuthLeftPanel from '../components/auth/AuthLeftPanel';
import AuthRightPanel from '../components/auth/AuthRightPanel';
import { AuthProvider } from '../context/AuthContext';
import { useAuthContext } from '../context/AuthContext';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { useToast } from '../context/ModalContext';
import { useEffect } from 'react';
import { clearAllAuthData } from '../utils/authUtils';
import { CheckCircle, AlertTriangle, LogIn } from 'lucide-react';
import Logo from '../components/auth/Logo';
import Button from '../components/common/Button';

// --- Dedicated Status Component (Responsive Adjustments) ---
// (VerificationStatus remains unchanged - removed for brevity)
const VerificationStatus: React.FC<{ status: 'email_updated' | 'email_transfer_approved' | 'error', email?: string, message?: string }> = ({
  status,
  email,
  message,
}) => {
    const navigate = useNavigate();
    const { showToast } = useToast();

    useEffect(() => {
        clearAllAuthData();

    if (status === 'email_updated' && email) {
      showToast(`Email updated successfully to ${email}. Please sign in with your new email.`, 'success');
    } else if (status === 'email_transfer_approved') {
      const msg = email ? `Approval recorded. A verification email has been sent to ${email}.` : 'Approval recorded. A verification email has been sent to the new address.';
      showToast(msg, 'success');
    } else if (status === 'error' && message) {
      showToast(`Verification failed: ${message}`, 'error');
    }

        window.history.replaceState({}, document.title, window.location.pathname);
    }, [status, email, message, showToast]);

  const isSuccess = status === 'email_updated' || status === 'email_transfer_approved';
  const displayMessage = isSuccess
    ? (status === 'email_updated'
      ? `Your email address has been successfully updated${email ? ` to ${email}` : ''}. You must log in with the new email now.`
      : (email ? `Approval recorded. A verification email has been sent to ${email}. Please sign in once you've verified.` : `Approval recorded. A verification email has been sent to the new address.`)
      )
    : message || "An unexpected error occurred during verification. Please contact support.";

    return (
        <div className="flex-1 p-4 sm:p-8 md:p-12 flex flex-col justify-center items-center relative z-10 bg-transparent w-full">
            <div className="bg-white p-6 sm:p-8 md:p-10 rounded-xl shadow-2xl w-full max-w-md flex flex-col items-center text-center">
                <Logo size="medium" className="mb-6 sm:mb-8" />

                {isSuccess ? (
                    <>
                        <CheckCircle size={40} className="text-green-500 mb-4 sm:mb-6 sm:w-12 sm:h-12" />
                        <h1 className="text-lg sm:text-xl font-bold text-green-700 mb-2">Verification Complete!</h1>
                    </>
                ) : (
                    <>
                        <AlertTriangle className="text-red-500 mb-4 sm:mb-6 w-10 h-10 sm:w-12 sm:h-12" />
                        <h1 className="text-lg sm:text-xl font-bold text-red-700 mb-2">Update Failed</h1>
                    </>
                )}

                <p className="text-gray-700 text-sm mb-6">{displayMessage}</p>

                <Button
                    onClick={() => navigate('/auth')}
                    variant="primary"
                    className="w-full sm:w-40 py-2.5 sm:py-2 text-sm sm:text-base"
                >
                    <LogIn size={16} /> Go to Login
                </Button>
            </div>
        </div>
    );
};


// --- Main Auth Page Content Logic ---
const AuthPageContent = () => {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { switchToSignIn } = useAuthContext();

  const status = searchParams.get('status');
  const email = searchParams.get('new_email');
  const encodedMessage = searchParams.get('message');

  // Removed conflicting authentication redirect logic - this is now handled by RoleBasedRedirect in App.tsx

  // Check if we are on a verification redirect URL
  const showStatusPage = status === 'email_updated' || status === 'error' || status === 'email_transfer_approved' || status === 'email_transfer_error';

  useEffect(() => {
    if (!showStatusPage) {
      sessionStorage.removeItem('authStep');
      switchToSignIn?.();
    }
  }, [location.key, showStatusPage, switchToSignIn]);

  if (showStatusPage) {
      const message = encodedMessage ? decodeURIComponent(encodedMessage) : undefined;
      return (
        <VerificationStatus
            status={status as 'email_updated' | 'error'}
            email={email || undefined}
            message={message}
        />
      );
  }

  // Simple return without double wrapping AuthProvider
  return (
    <>
        <AuthLeftPanel />
        <AuthRightPanel /> 
    </>
  );
};
/**
 * Main Auth Page Wrapper.
 * This component wraps everything in AuthProvider for proper context.
 */
const AuthPage = () => {
  return (
    <AuthProvider>
      <div
        className="min-h-screen w-screen flex items-center justify-center bg-white"
      >
        <div
          className="flex w-screen h-screen overflow-hidden relative"
          style={{
            backgroundColor: 'white',
          }}
        >
          <AuthPageContent />
        </div>
      </div>
    </AuthProvider>
  );
};export default AuthPage;