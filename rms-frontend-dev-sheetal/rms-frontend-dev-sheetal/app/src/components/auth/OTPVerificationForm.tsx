import React, { useState, useEffect, useCallback } from 'react';
import { useAuthContext } from '../../context/AuthContext';
import { AUTH_CONFIG } from '../../constants/auth';
import OTPInput from './OTPInput'; 
import { Edit, Loader2 } from 'lucide-react'; 

// ------------------------------------------
// 🚀 CUSTOM HOOK: Countdown Logic (Remains the same)
// ------------------------------------------
const useCountdownTimer = (initialDuration: number, resendCooldownDuration: number, onExpire?: () => void) => {
  const [secondsLeft, setSecondsLeft] = useState(initialDuration);
  const [isExpired, setIsExpired] = useState(false);

  const [resendCooldown, setResendCooldown] = useState(resendCooldownDuration); // Sync with RESEND_COOLDOWN_SECONDS initially
  const [resendTimeIsUp, setResendTimeIsUp] = useState(false);

  const reset = useCallback(() => {
    setSecondsLeft(initialDuration);
    setResendCooldown(resendCooldownDuration); // Reset resend cooldown to match RESEND_COOLDOWN_SECONDS
    setIsExpired(false);
    setResendTimeIsUp(false); // Lock resend until OTP expires again
  }, [initialDuration, resendCooldownDuration]);

  useEffect(() => {
    if (secondsLeft <= 0) {
      setIsExpired(true);
      setResendTimeIsUp(true); // Allow resend when OTP expires
      if (onExpire) onExpire();
      return;
    }

    const timer = setInterval(() => {
      setSecondsLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [secondsLeft, onExpire]);

  useEffect(() => {
    if (resendCooldown > 0) {
      const cooldownTimer = setInterval(() => {
        setResendCooldown((prev) => {
          if (prev - 1 <= 0) {
            clearInterval(cooldownTimer);
            setResendTimeIsUp(true); // Resend becomes available
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(cooldownTimer);
    }
  }, [resendCooldown]);

  const formatTime = (s: number) => {
    const minutes = Math.floor(s / 60);
    const seconds = s % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const startResendCooldown = (duration: number) => {
    setResendCooldown(duration);
    setResendTimeIsUp(false);
  };

  return {
    secondsLeft,
    isExpired,
    resendCooldown,
    resendTimeIsUp,
    reset,
    formatTime,
    startResendCooldown,
  };
};

// ------------------------------------------
// 🖥️ OTP VERIFICATION FORM COMPONENT
// ------------------------------------------
const OTPVerificationForm: React.FC = () => {
  const {
    loading,
    error,
    userEmail,
    verifyOTP,
    resendOTP,
    goBackToForm,
  } = useAuthContext();

  const [otp, setOtp] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState<string | null>(null);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [verificationAttempts, setVerificationAttempts] = useState(0);
  const [otpInputKey, setOtpInputKey] = useState(0);

  const MAX_ATTEMPTS = 3;

  const {
    isExpired,
    secondsLeft,
    resendCooldown,
    resendTimeIsUp,
    reset: resetOTPExpiry,
    startResendCooldown,
    formatTime,
  } = useCountdownTimer(AUTH_CONFIG.OTP_EXPIRY_SECONDS, AUTH_CONFIG.RESEND_COOLDOWN_SECONDS);

  useEffect(() => {
    if (resendSuccess) {
      const timer = setTimeout(() => setResendSuccess(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [resendSuccess]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length === 6 && !isExpired && !loading) {
      setResendSuccess(null);
      setOtpError(null);

      try {
        console.log('Attempting OTP verification...');
        const result = await verifyOTP(otp);

        if (result && result.success) {
          console.log('✅ OTP verification successful in form component');
          // Success - the redirect will be handled by useAuth hook
        } else if (result && !result.success) {
          setVerificationAttempts((prev) => prev + 1);
          setOtpError(result.message || 'Invalid verification code. Please try again.');
          console.error('OTP verification failed:', result.message);
        }
      } catch (err) {
        setVerificationAttempts((prev) => prev + 1);
        console.error('OTP verification error:', err);

        // Use generic error handling if API doesn't provide structured error
        setOtpError('Verification failed. Please try again or request a new code.');
      }
    }
  };

  const handleResend = async () => {
    if (loading || resendLoading || !resendTimeIsUp) return;

    setResendLoading(true);

    try {
      setOtp('');
      setOtpInputKey((prev) => prev + 1);

      const result = await resendOTP();

      if (result.success) {
        setOtp('');
        setOtpInputKey((prev) => prev + 1);

        resetOTPExpiry();
        startResendCooldown(AUTH_CONFIG.RESEND_COOLDOWN_SECONDS);

        setResendSuccess(result.message || 'New OTP successfully sent!');
        setOtpError(null); // Clear any previous error
        setVerificationAttempts(0); // Reset attempts
      } else {
        setOtpError(result.message || 'Failed to resend OTP.');
      }
    } catch (error) {
      console.error("Resend OTP failed:", error);
      setOtpError('Error resending OTP. Please check network.');
    } finally {
      setResendLoading(false);
    }
  };

  const handleOTPChange = (value: string) => {
    if (otpError) setOtpError(null);
    setOtp(value);
  };

  const isVerificationLoading = loading && !resendLoading; 

  const isSubmitDisabled = isVerificationLoading || otp.length !== 6 || isExpired;
  
  const isResendDisabled = loading || resendLoading || !resendTimeIsUp; 

  const resendLinkText = () => {
    if (resendLoading) return <><Loader2 size={16} className="animate-spin mr-1" /> Sending...</>;
    
    if (!resendTimeIsUp) {
      return `Resend in ${formatTime(resendCooldown)}`;
    }
    
    return 'Resend Code';
  }

  return (
    <div className="w-full max-w-md sm:max-w-[453px] px-4 sm:px-0 mx-auto space-y-5">
      <h2 className="text-lg sm:text-xl md:text-2xl font-semibold text-gray-700 mb-2" style={{ fontFamily: 'Poppins' }}>
        {AUTH_CONFIG.CONTENT.verifyTitle}
      </h2>
      
      <div className="text-sm sm:text-base text-gray-600 mb-6" style={{ fontFamily: 'Poppins' }}>
        <div>{AUTH_CONFIG.CONTENT.otpInstruction}</div>
        <div className="flex items-center space-x-2 mt-1">
          <strong className="text-gray-900 font-semibold">{userEmail}</strong>
          <button 
             type="button" 
             onClick={goBackToForm} 
             className="
               text-[var(--color-accent-orange)] hover:text-red-600 transition-colors disabled:opacity-50
               bg-transparent p-0 border-0 shadow-none appearance-none ml-1
               cursor-pointer inline-flex items-center text-sm
             "
             disabled={loading}
             aria-label="Change email address"
          >
             <Edit size={16} className="mr-0.5" /> Edit
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="flex justify-center">
          <OTPInput
            key={otpInputKey}
            length={6}
            value={otp}
            onChange={handleOTPChange}
            disabled={loading || isExpired} 
          />
        </div>
        
        {/* Resend Text Link & Countdown Timer */}
        <div className="flex flex-col sm:flex-row sm:justify-between items-start sm:items-center text-sm gap-2">
          <button 
            type="button" 
            onClick={handleResend}
            disabled={isResendDisabled}
            className="
               flex items-center bg-transparent p-0 border-0 shadow-none appearance-none 
               text-[var(--color-accent-orange)] hover:text-red-600 transition-colors disabled:opacity-50 
               font-semibold cursor-pointer focus:outline-none text-sm
            "
          >
              {resendLinkText()}
          </button>

          <p className={isExpired ? 'text-red-600 font-bold' : 'text-gray-600 font-medium'}>
              {isExpired ? 'OTP Expired' : `Expires in: ${formatTime(secondsLeft)}`}
          </p>
        </div>
        

        {/* Error/Message */}
        {(error || otpError) && (
            <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg border border-red-200" role="alert">
                {otpError || error}
                {verificationAttempts >= MAX_ATTEMPTS && (
                    <div className="mt-2 font-medium">
                        Having trouble? <button 
                            type="button"
                            onClick={handleResend}
                            disabled={isResendDisabled}
                            className="text-[var(--color-accent-orange)] underline hover:text-red-600 disabled:opacity-50"
                        >
                            Request a new code
                        </button>
                    </div>
                )}
            </div>
        )}

        {/* Resend Success Toast */}
        {resendSuccess && (
            <div className="text-green-600 text-sm bg-green-50 p-3 rounded-lg border border-green-200 shadow-lg" role="status">
                {resendSuccess}
            </div>
        )}

        {/* Continue Button with Loading Spinner */}
    <button 
      type="submit" 
      disabled={isSubmitDisabled} 
      className={`
        w-full h-12 sm:h-14 rounded-xl text-white font-semibold text-lg tracking-wider 
        shadow-lg hover:bg-[var(--color-primary-600)] transition-colors duration-200
        disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center
      `}
      style={{
        fontFamily: 'Poppins',
        backgroundColor: 'var(--color-primary-500)',
        boxShadow: '0px 4px 19px rgba(1,107,174,0.3)',
      }}
    >
            {isVerificationLoading ? (
                <div className="flex items-center justify-center space-x-2">
                    <Loader2 size={20} className="animate-spin" />
                    <span>Verifying your code...</span>
                </div>
            ) : AUTH_CONFIG.CONTENT.continueButton}
        </button>
      </form>
    </div>
  );
};

export default OTPVerificationForm;