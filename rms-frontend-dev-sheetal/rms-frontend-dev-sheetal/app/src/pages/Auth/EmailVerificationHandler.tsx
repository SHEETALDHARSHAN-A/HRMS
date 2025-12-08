// RMS-F/app/src/pages/Auth/EmailVerificationHandler.tsx
import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { verifyEmailUpdate } from '../../api/adminApi';
import { Loader2 } from 'lucide-react';

const EmailVerificationHandler: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const handleVerification = async () => {
      try {
        const token = searchParams.get('token');
        const userId = searchParams.get('user_id');
        const newEmail = searchParams.get('new_email');

        if (!token || !userId || !newEmail) {
          // Invalid parameters, redirect to error page
          navigate('/auth/email-update-success?status=error&message=Invalid verification link');
          return;
        }

        // Call backend verification endpoint
        const result = await verifyEmailUpdate({
          token,
          user_id: userId,
          new_email: decodeURIComponent(newEmail)
        });

        // Redirect to success/error page based on result
        if (result.success) {
          navigate('/auth/email-update-success?status=success');
        } else {
          navigate(`/auth/email-update-success?status=error&message=${encodeURIComponent(result.error || 'Verification failed')}`);
        }
      } catch (error) {
        console.error('Email verification failed:', error);
        navigate('/auth/email-update-success?status=error&message=An unexpected error occurred');
      }
    };

    handleVerification();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary-500" />
        <h2 className="mt-4 text-xl font-semibold text-gray-900">Verifying Email Update</h2>
        <p className="mt-2 text-gray-600">Please wait...</p>
      </div>
    </div>
  );
};

export default EmailVerificationHandler;