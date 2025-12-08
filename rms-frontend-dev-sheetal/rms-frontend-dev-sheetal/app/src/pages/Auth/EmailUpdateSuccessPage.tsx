import React from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle } from 'lucide-react';

const EmailUpdateSuccessPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const status = searchParams.get('status');
  const message = searchParams.get('message');

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-8 bg-white rounded-xl shadow-lg">
        {status === 'success' ? (
          <div className="text-center">
            <CheckCircle className="h-12 w-12 mx-auto text-green-500" />
            <h2 className="mt-4 text-xl font-semibold text-gray-900">Email Updated Successfully!</h2>
            <p className="mt-2 text-gray-600">You can now sign in with your new email address.</p>
            <button
              onClick={() => navigate('/auth/signin')}
              className="mt-6 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
            >
              Go to Login
            </button>
          </div>
        ) : (
          <div className="text-center">
            <XCircle className="h-12 w-12 mx-auto text-red-500" />
            <h2 className="mt-4 text-xl font-semibold text-gray-900">Verification Failed</h2>
            <p className="mt-2 text-gray-600">{message || 'An error occurred during verification.'}</p>
            <button
              onClick={() => navigate('/auth/signin')}
              className="mt-6 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
            >
              Go to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailUpdateSuccessPage;