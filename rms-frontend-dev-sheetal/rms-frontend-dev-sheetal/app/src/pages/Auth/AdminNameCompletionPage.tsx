// ats-frontend-dev-sheetal/app/src/pages/Auth/AdminNameCompletionPage.tsx

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Loader2, CheckCircle, AlertTriangle, LogIn } from 'lucide-react';
import { useToast } from '../../context/ModalContext';
import Button from '../../components/common/Button';
import { verifyAdminNameUpdate } from '../../api/adminApi'; 
import Logo from '../../components/auth/Logo'; 

const AdminNameCompletionPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { showToast } = useToast();

    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState('Verifying name update and updating profile...');
    
    const REDIRECT_DELAY_MS = 3000; 
    
    const handleSetup = useCallback(async () => {
        const token = searchParams.get('token');
        const userId = searchParams.get('user_id');

        if (!token || !userId) {
            setStatus('error');
            setMessage('Error: Verification token or User ID is missing from the URL.');
            return;
        }

        setStatus('loading');
        
        try {
            const result = await verifyAdminNameUpdate(token, userId);

            if (result.success) { 
                setStatus('success');
                setMessage(`Profile name successfully updated! Redirecting to dashboard...`);
                showToast(result.message || 'Profile name updated successfully.', 'success');
                
                // Clear user context to force reloading the user details (with new name) on redirect
                localStorage.removeItem('user');
                sessionStorage.removeItem('user');
                
                setTimeout(() => {
                    navigate('/dashboard'); 
                }, REDIRECT_DELAY_MS);
                     
            } else {
                setStatus('error');
                setMessage(result.error || 'Name update failed. The link may be invalid or expired.');
                showToast(result.error || 'Name update failed.', 'error');
            }
        } catch (err) {
              console.error("Admin name completion failed:", err);
              setStatus('error');
              setMessage('Network error or unexpected response during setup.');
              showToast('Network error during name update verification.', 'error');
        }
    }, [showToast, navigate, searchParams]);

    useEffect(() => {
        handleSetup();
    }, [handleSetup]);

    const renderContent = () => {
        switch (status) {
            case 'loading':
                return (
                    <>
                        <Loader2 size={48} className="animate-spin text-[var(--color-primary-500)] mb-6" />
                        <h1 className="text-xl font-bold text-gray-800 mb-2">Processing Name Update...</h1>
                        <p className="text-gray-600 text-center">{message}</p>
                    </>
                );
            case 'success':
                return (
                    <>
                        <CheckCircle size={48} className="text-green-500 mb-6" />
                        <h1 className="text-xl font-bold text-green-700 mb-2">Name Update Complete!</h1>
                        <p className="text-gray-700 text-center mb-6">
                            Your profile name has been successfully updated.
                        </p>
                        <p className="text-sm text-gray-500 mb-6">
                            Redirecting to Dashboard in {REDIRECT_DELAY_MS / 1000} seconds...
                        </p>
                        <Link to="/dashboard">
                            <Button variant="primary" className="px-8 bg-[var(--color-primary-500)]">
                                <LogIn size={16} /> Go to Dashboard
                            </Button>
                        </Link>
                    </>
                );
            case 'error':
                return (
                    <>
                        <AlertTriangle size={48} className="text-red-500 mb-6" />
                        <h1 className="text-xl font-bold text-red-700 mb-2">Update Failed</h1>
                        <p className="text-gray-700 text-center mb-6">{message}</p>
                        <Link to="/auth">
                             <Button variant="secondary" className="px-8">
                                Go to Login
                            </Button>
                        </Link>
                    </>
                );
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="bg-white p-10 rounded-xl shadow-2xl w-full max-w-md flex flex-col items-center">
                <Logo size="medium" className="mb-8" />
                {renderContent()}
            </div>
        </div>
    );
};

export default AdminNameCompletionPage;