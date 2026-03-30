import React from 'react';
import { AlertCircle } from 'lucide-react';
import OTPVerificationForm from './OTPVerificationForm';
import { useAuthContext } from '../../context/AuthContext';
import { AUTH_CONFIG } from '../../constants/auth';
import { LoginForm } from '@/components/login-form';
import { cn } from '@/lib/utils';

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

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    console.error('Auth Component Boundary Caught Error:', error);
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('Uncaught auth panel error details:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-left">
          <div className="mb-2 flex items-center gap-2 text-red-700">
            <AlertCircle className="h-4 w-4" />
            <h2 className="text-sm font-semibold">Authentication unavailable</h2>
          </div>
          <p className="text-sm text-red-600">
            A critical error occurred while loading the sign-in flow. Please refresh this page and try again.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}

const AuthFormRenderer: React.FC = () => {
  const { currentStep } = useAuthContext();

  if (currentStep === AUTH_CONFIG.AUTH_STEPS.VERIFY_OTP) {
    return <OTPVerificationForm />;
  }

  return <LoginForm />;
};

const AuthRightPanel: React.FC = () => {
  const { currentStep } = useAuthContext();
  const isOtpStep = currentStep === AUTH_CONFIG.AUTH_STEPS.VERIFY_OTP;

  return (
    <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-8 sm:px-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(1,107,174,0.14),transparent_55%),radial-gradient(circle_at_bottom_left,rgba(255,76,0,0.12),transparent_50%)]" />

      <div className={cn('relative z-10 w-full', isOtpStep ? 'max-w-xl' : 'max-w-md')}>
        <ErrorFallbackWrapper>
          <AuthFormRenderer />
        </ErrorFallbackWrapper>
      </div>
    </div>
  );
};

export default React.memo(AuthRightPanel);
