// // rms-frontend-dev-sheetal/app/src/components/auth/AuthRightPanel.tsx
// import React from 'react';
// import Logo from './Logo';
// import SignInForm from './SignInForm';
// // import SignUpForm from './SignUpForm'; // No longer needed
// import OTPVerificationForm from './OTPVerificationForm';
// import { useAuthContext } from '../../context/AuthContext';
// import { AUTH_CONFIG } from '../../constants/auth';

// /**
//  * Renders the correct form based on the AuthContext state.
//  * This component now only handles Sign-In and OTP steps.
//  */
// const AuthFormRenderer: React.FC = () => {
//   const { currentStep } = useAuthContext();

//   // The Sign-Up step is removed from this flow
//   if (currentStep === AUTH_CONFIG.AUTH_STEPS.VERIFY_OTP) {
//     return <OTPVerificationForm />;
//   }
  
//   // Default to SignInForm
//   return <SignInForm />;
// };

// /**
//  * The right-hand panel for the Admin Authentication page.
//  * It now wraps the form renderer in the AuthProvider.
//  */
// const AuthRightPanel: React.FC = () => {
//   return (
//     <div className="flex-1 p-4 sm:p-8 md:p-12 flex flex-col justify-center items-center relative z-10 bg-transparent w-full">
//       <div
//         className="flex flex-col justify-center items-center p-0 w-full max-w-md sm:max-w-lg md:max-w-[453px]"
//         style={{
//           gap: '30px sm:40px md:50px',
//         }}
//       >
//         <div className="flex flex-col items-start w-full space-y-4 sm:space-y-6 md:space-y-[30px] self-stretch">
//           <div className="flex flex-col items-start space-y-3 sm:space-y-4 md:space-y-5 w-full">
//             <div className="flex items-center relative w-full max-w-[447px]">
//               <Logo size="large" className="w-40 sm:w-48 md:w-[198.53px]" />
//             </div>
//             <h1
//               className="w-full text-[#016BAE] text-xl sm:text-2xl md:text-[28px]"
//               style={{
//                 fontFamily: 'Raleway',
//                 fontWeight: 600,
//                 lineHeight: '1.2',
//               }}
//             >
//               Prayag <span className="text-[#FF4C00]">Recruitment Management</span>
//             </h1>
//           </div>
//         </div>
        
//         {/* Render the appropriate form (Sign In or OTP) */}
//         <div className="w-full mt-4 sm:mt-5">
//           <AuthFormRenderer />
//         </div>
//       </div>
//     </div>
//   );
// };

// export default React.memo(AuthRightPanel);


// src/components/auth/AuthRightPanel.tsx

import React from 'react'; // 💡 Required for the class-based Error Boundary
import Logo from './Logo';
import SignInForm from './SignInForm';
import OTPVerificationForm from './OTPVerificationForm';
import { useAuthContext } from '../../context/AuthContext';
import { AUTH_CONFIG } from '../../constants/auth';

// --- NEW: Class-based Error Boundary Component ---
interface ErrorBoundaryProps {
    children: React.ReactNode;
}
interface ErrorBoundaryState {
    hasError: boolean;
}

class ErrorFallbackWrapper extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false };
    }

    // Must be static to be a valid error boundary method
    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        console.error("Auth Component Boundary Caught Error:", error);
        // Update state to render fallback UI
        return { hasError: true };
    }

    // Optional: Log error details to an error tracking service
    componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
        console.error("Uncaught error details:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            // Fallback UI to show when an error is caught
            return (
                <div className="text-center p-8 rounded-xl border-2 border-red-400 bg-red-50 shadow-inner">
                    <h2 className="text-xl font-bold text-red-700 mb-2">Authentication System Unavailable</h2>
                    <p className="text-red-600 text-sm">
                        A critical error occurred while loading the sign-in form. This usually means the component structure is incorrect (e.g., missing a context provider). Please refresh your browser.
                    </p>
                </div>
            );
        }
        return this.props.children;
    }
}
// --- END Error Boundary Component ---

/**
 * Renders the correct form based on the AuthContext state.
 */
const AuthFormRenderer: React.FC = () => {
  const { currentStep } = useAuthContext(); // <-- Original failure point

  // The Sign-Up step is removed from this flow
  if (currentStep === AUTH_CONFIG.AUTH_STEPS.VERIFY_OTP) {
    return <OTPVerificationForm />;
  }
  
  // Default to SignInForm
  return <SignInForm />;
};

/**
 * The right-hand panel for the Admin Authentication page.
 * The inner forms are wrapped in the Error Boundary.
 */
const AuthRightPanel: React.FC = () => {
  return (
    <div className="flex-1 p-4 sm:p-8 md:p-12 flex flex-col justify-center items-center relative z-10 bg-transparent w-full">
      <div
        className="flex flex-col justify-center items-center p-0 w-full max-w-md sm:max-w-lg md:max-w-[453px]"
        style={{
          gap: '30px sm:40px md:50px',
        }}
      >
        <div className="flex flex-col items-start w-full space-y-4 sm:space-y-6 md:space-y-[30px] self-stretch">
          <div className="flex flex-col items-start space-y-3 sm:space-y-4 md:space-y-5 w-full">
            <div className="flex items-center relative w-full max-w-[447px]">
              <Logo size="large" className="w-40 sm:w-48 md:w-[198.53px]" />
            </div>
            <h1
              className="w-full text-[#016BAE] text-xl sm:text-2xl md:text-[28px]"
              style={{
                fontFamily: 'Raleway',
                fontWeight: 600,
                lineHeight: '1.2',
              }}
            >
              Prayag <span className="text-[#FF4C00]">Recruitment Management</span>
            </h1>
          </div>
        </div>
        
        {/* Render the appropriate form (Sign In or OTP) wrapped in the Error Boundary */}
        <div className="w-full mt-4 sm:mt-5">
          <ErrorFallbackWrapper>
            <AuthFormRenderer />
          </ErrorFallbackWrapper>
        </div>
      </div>
    </div>
  );
};

export default React.memo(AuthRightPanel);