// ats-frontend-dev-sheetal/app/src/pages/Auth/AdminSetupCompletionPage.tsx

import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate, Link, useLocation } from 'react-router-dom';
import { Loader2, CheckCircle, AlertTriangle, LogIn } from 'lucide-react';
import { useToast } from '../../context/ModalContext';
import { completeAdminSetup } from '../../api/adminApi';
import Button from '../../components/common/Button';
import { getCurrentUser } from '../../utils/authUtils'; 
import type { User } from '../../types/auth'; 

const AdminSetupCompletionPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { showToast } = useToast();

    const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
    const [message, setMessage] = useState('Verifying invitation link and setting up account...');
    const [token, setToken] = useState<string | null>(null);
    const [userEmail, setUserEmail] = useState<string | null>(null); 
    const REDIRECT_DELAY_MS = 3000; 
    const location = useLocation();

    const type = searchParams.get('type');
    const statusParam = searchParams.get('status');
    const messageParam = searchParams.get('message');
    const redirectTo = searchParams.get('redirect_to');

    /**
     * Stores user profile data into session storage to manually trigger the authenticated state 
     * in the client's UserContext, since cookies were already set by the backend.
     */
    const saveUserToStorage = (userData: User) => {
        const userRole = userData.role; 
        
        sessionStorage.setItem('user', JSON.stringify(userData));
        sessionStorage.setItem('userRole', userRole || 'ADMIN');
        sessionStorage.setItem('user_id', userData.user_id || '');
        
        // Clear old auth flow data
        sessionStorage.removeItem('authEmail');
        sessionStorage.removeItem('authStep');
        
        // Note: No sessionUpdate event - this page redirects to login, not dashboard
    }

    /**
     * Checks if the user is logged in (via newly set cookies/storage) and redirects if so.
     * @param delay - Time in ms to wait before redirecting.
     * @returns boolean - True if redirection was triggered.
     */
    const checkAndRedirect = useCallback((delay: number): boolean => {
        const existingUser = getCurrentUser();
        if (existingUser) {
            // Extract user role (handle both string and array formats)
            let userRole: string | undefined;
            if (typeof existingUser.role === 'string') {
                userRole = existingUser.role;
            } else if (Array.isArray(existingUser.role) && existingUser.role.length > 0) {
                userRole = existingUser.role[0];
            }
            
            // All admin roles (including HR) should go to dashboard
            if (userRole === 'SUPER_ADMIN' || userRole === 'ADMIN' || userRole === 'HR') {
                setStatus('success');
                setUserEmail(existingUser.email);
                setMessage('Account verified and logged in. Redirecting to dashboard...');
                
                setTimeout(() => {
                    navigate('/dashboard');
                }, delay); 
                return true;
            }
        }
        return false;
    }, [navigate]);

    // Initial check on mount/token change
    useEffect(() => {
        const urlToken = searchParams.get('token');
        // 💡 FIX: Only check for the presence of 'token'. The initial admin invite does NOT use 'user_id'.
        if (urlToken) {
            setToken(urlToken);
        } else {
            setStatus('error');
            // 💡 FIX: Updated message to reflect only token is missing
            setMessage('Error: Invitation token is missing from the URL.');
        }
        
        // Immediate check to handle browser navigations/reloads
        checkAndRedirect(0); 
    }, [searchParams, checkAndRedirect]);


    const handleSetup = useCallback(async (setupToken: string) => {
        setStatus('loading');
        
        // If we hit this, the initial check failed, proceed with API call
        const result = await completeAdminSetup(setupToken);

        if (result.success && result.data) { 
            
            const responseData = result.data as any;
            
            // Check if this is the new response format (account created but not auto-logged in)
            if (responseData.account_created && responseData.redirect_to_signin) {
                setStatus('success');
                setUserEmail(responseData.email); 
                setMessage(`Account created successfully! Please sign in with your email: ${responseData.email}`);
                showToast('Admin account created successfully. Please sign in to continue.', 'success');
                
                // Redirect to sign-in page instead of dashboard
                setTimeout(() => {
                    navigate('/auth', { state: { email: responseData.email } }); 
                }, REDIRECT_DELAY_MS);
            } else {
                // Legacy format - decide behavior based on where this page was opened from.
                // If this is the admin invite completion route, prefer redirecting to sign-in
                // so the user can log in (backend may not auto-login on invite flows).
                const userData: User = result.data as User;
                const isInviteFlow = location.pathname.includes('complete-admin-setup');

                if (isInviteFlow) {
                    // Do NOT auto-login; prompt user to sign in instead.
                    setStatus('success');
                    setUserEmail(userData.email);
                    setMessage(`Account created successfully! Please sign in with your email: ${userData.email}`);
                    showToast('Admin account created successfully. Please sign in to continue.', 'success');

                    setTimeout(() => {
                        navigate('/auth', { state: { email: userData.email } });
                    }, REDIRECT_DELAY_MS);
                } else {
                    // Fallback: legacy behavior - save user and navigate to dashboard
                    saveUserToStorage(userData); // Save to trigger UserContext update
                    setStatus('success');
                    setUserEmail(userData.email);
                    setMessage(`Account setup complete! You are now logged in as ${userData.email}. Redirecting to dashboard...`);
                    showToast('Admin account created and logged in successfully.', 'success');

                    setTimeout(() => {
                        navigate('/dashboard');
                    }, REDIRECT_DELAY_MS);
                }
            }
                 
        } else {
            // 💡 CRITICAL: Fallback check to recover session immediately after a failed API response
            const recoveredUser = getCurrentUser();
            
            if (recoveredUser) {
                // Extract user role (handle both string and array formats)
                let userRole: string | undefined;
                if (typeof recoveredUser.role === 'string') {
                    userRole = recoveredUser.role;
                } else if (Array.isArray(recoveredUser.role) && recoveredUser.role.length > 0) {
                    userRole = recoveredUser.role[0];
                }
                
                // All admin roles (including HR) should go to dashboard
                if (userRole === 'SUPER_ADMIN' || userRole === 'ADMIN' || userRole === 'HR') {
                     // Account created, cookies set, session recovered.
                     setStatus('success');
                     setUserEmail(recoveredUser.email);
                     setMessage('Setup recovered! Account created and logged in successfully. Redirecting...');
                     showToast('Setup successful (recovered from API failure).', 'success');
                     
                     setTimeout(() => {
                         navigate('/dashboard');
                     }, 500); 
                     return;
                }
            }
            
            // Final definitive error
            setStatus('error');
            setMessage(result.error || 'Setup failed. The invitation link may be invalid or expired.');
            showToast(result.error || 'Admin setup failed.', 'error');
        }
    }, [showToast, navigate]);

    useEffect(() => {
        // Only run setup if we have a token and we are not already redirecting/successful from initial check
        if (token && status === 'loading' && !getCurrentUser()) { 
            handleSetup(token);
        }
    }, [token, handleSetup, status]);

    const renderContent = () => {
        switch (status) {
            case 'loading':
                return (
                    <>
                        <Loader2 size={48} className="animate-spin text-[var(--color-primary-500)] mb-6" />
                        <h1 className="text-xl font-bold text-gray-800 mb-2">Processing Setup...</h1>
                        <p className="text-gray-600 text-center">{message}</p>
                    </>
                );
            case 'success':
                return (
                    <>
                        <CheckCircle size={48} className="text-green-500 mb-6" />
                        <h1 className="text-xl font-bold text-green-700 mb-2">Account Setup Complete!</h1>
                        <p className="text-gray-700 text-center mb-6">
                            {message.includes('sign in') ? (
                                <>
                                    Account created successfully! 
                                    <strong className="block text-lg font-bold mt-1 text-gray-900">{userEmail || 'N/A'}</strong>
                                    <span className="text-sm text-blue-600 mt-2 block">Please sign in to continue</span>
                                </>
                            ) : (
                                <>
                                    You are now logged in. Your email address: 
                                    <strong className="block text-lg font-bold mt-1 text-gray-900">{userEmail || 'N/A'}</strong>
                                </>
                            )}
                        </p>
                        <p className="text-sm text-gray-500 mb-6">
                            {message.includes('sign in') ? 
                                `Redirecting to Sign In page in ${REDIRECT_DELAY_MS / 1000} seconds...` :
                                `Redirecting to Dashboard in ${REDIRECT_DELAY_MS / 1000} seconds...`
                            }
                        </p>
                        
                        <div className="hidden">
                            <Link to="/dashboard">
                                <Button variant="primary" className="px-8 bg-[var(--color-primary-500)]">
                                    <LogIn size={16} /> Go to Dashboard
                                </Button>
                            </Link>
                        </div>
                    </>
                );
            case 'error':
                return (
                    <>
                        <AlertTriangle size={48} className="text-red-500 mb-6" />
                        <h1 className="text-xl font-bold text-red-700 mb-2">Setup Failed</h1>
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

    const [verificationStage, setVerificationStage] = useState<'processing' | 'confirmation'>('processing');

    // show a short processing state before confirmation
    useEffect(() => {
        if (!statusParam) return;
        setVerificationStage('processing');
        const t = setTimeout(() => setVerificationStage('confirmation'), 2000);
        return () => clearTimeout(t);
    }, [statusParam]);

    // Auto-redirect when the verification/status params are present
    useEffect(() => {
        if (!statusParam) return;

        const redirectTimer = setTimeout(() => {
            if (redirectTo === 'auth') {
                navigate('/auth');
            } else if (redirectTo === 'login') {
                navigate('/auth/login');
            } else {
                navigate('/auth');
            }
        }, 5000);

        return () => clearTimeout(redirectTimer);
    }, [statusParam, redirectTo, navigate]);

    const renderVerificationContent = () => {
        if (!statusParam) return null;

        if (verificationStage === 'processing') {
            return (
                <>
                    <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-[var(--color-primary-50)] flex items-center justify-center">
                        <Loader2 size={36} className="animate-spin text-[var(--color-primary-500)]" />
                    </div>
                    <h1 className="text-xl font-bold text-gray-800 mb-2">Processing...</h1>
                    <p className="text-gray-600 text-center mb-6">Please wait while we confirm your action.</p>
                </>
            );
        }

        // confirmation stage
        const success = statusParam === 'success';
        return (
            <>
                <div className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center" style={{ backgroundColor: success ? '#ECFDF5' : '#FEF2F2' }}>
                    {success ? (
                        <CheckCircle size={36} className="text-green-600" />
                    ) : (
                        <AlertTriangle size={36} className="text-red-600" />
                    )}
                </div>

                <h1 className={`text-xl font-bold ${success ? 'text-green-700' : 'text-red-700'} mb-2`}>
                    {success ? 'Verification Successful' : 'Verification Failed'}
                </h1>

                <p className="text-gray-700 text-center mb-6">
                    {success
                        ? `Your ${type || 'update'} has been successfully verified and updated.`
                        : messageParam || `There was an error processing your ${type || 'update'}.`}
                </p>

                <div className="mb-4 flex justify-center">
                    <Button
                        variant="primary"
                        className="px-8 bg-[var(--color-primary-500)] mx-auto"
                        onClick={() => {
                            if (redirectTo === 'auth') {
                                navigate('/auth');
                            } else if (redirectTo === 'login') {
                                navigate('/auth/login');
                            } else {
                                navigate('/auth');
                            }
                        }}
                    >
                        Go to Auth Page Now
                    </Button>
                </div>
            </>
        );
    };

    if (statusParam) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <div className="bg-white p-10 rounded-xl shadow-2xl w-full max-w-md flex flex-col items-center">
                    <img src="/logo.svg" alt="PRAYAG.AI" className="h-14 w-auto mb-8" />
                    <div className="w-full text-center">
                        {renderVerificationContent()}
                        <div className="text-sm text-gray-500 mt-2">Redirecting to authentication page in a few seconds...</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="bg-white p-10 rounded-xl shadow-2xl w-full max-w-md flex flex-col items-center">
                <img src="/logo.svg" alt="PRAYAG.AI" className="h-14 w-auto mb-8" />
                {renderContent()}
            </div>
        </div>
    );
};

export default AdminSetupCompletionPage;