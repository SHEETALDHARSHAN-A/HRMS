import React, { useState, useEffect, useCallback } from 'react';
import { AlertCircle, Edit3, Loader2, Mail, RotateCcw, ShieldCheck } from 'lucide-react';
import { useAuthContext } from '../../context/AuthContext';
import { AUTH_CONFIG } from '../../constants/auth';
import OTPInput from './OTPInput';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const useCountdownTimer = (
  initialDuration: number,
  resendCooldownDuration: number,
  onExpire?: () => void
) => {
  const [secondsLeft, setSecondsLeft] = useState(initialDuration);
  const [isExpired, setIsExpired] = useState(false);

  const [resendCooldown, setResendCooldown] = useState(resendCooldownDuration);
  const [resendTimeIsUp, setResendTimeIsUp] = useState(false);

  const reset = useCallback(() => {
    setSecondsLeft(initialDuration);
    setResendCooldown(resendCooldownDuration);
    setIsExpired(false);
    setResendTimeIsUp(false);
  }, [initialDuration, resendCooldownDuration]);

  useEffect(() => {
    if (secondsLeft <= 0) {
      setIsExpired(true);
      setResendTimeIsUp(true);
      if (onExpire) {
        onExpire();
      }
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
            setResendTimeIsUp(true);
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

const OTPVerificationForm: React.FC = () => {
  const { loading, error, userEmail, verifyOTP, resendOTP, goBackToForm } = useAuthContext();

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
        const result = await verifyOTP(otp);

        if (result && !result.success) {
          setVerificationAttempts((prev) => prev + 1);
          setOtpError(result.message || 'Invalid verification code. Please try again.');
        }
      } catch {
        setVerificationAttempts((prev) => prev + 1);
        setOtpError('Verification failed. Please try again or request a new code.');
      }
    }
  };

  const handleResend = async () => {
    if (loading || resendLoading || !resendTimeIsUp) {
      return;
    }

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

        setResendSuccess(result.message || 'New OTP sent successfully.');
        setOtpError(null);
        setVerificationAttempts(0);
      } else {
        setOtpError(result.message || 'Failed to resend OTP.');
      }
    } catch {
      setOtpError('Error resending OTP. Please check your network.');
    } finally {
      setResendLoading(false);
    }
  };

  const handleOTPChange = (value: string) => {
    if (otpError) {
      setOtpError(null);
    }
    setOtp(value);
  };

  const isVerificationLoading = loading && !resendLoading;
  const isSubmitDisabled = isVerificationLoading || otp.length !== 6 || isExpired;
  const isResendDisabled = loading || resendLoading || !resendTimeIsUp;

  const resendLinkText = () => {
    if (resendLoading) {
      return (
        <>
          <Loader2 size={14} className="mr-1 animate-spin" />
          Sending...
        </>
      );
    }

    if (!resendTimeIsUp) {
      return `Resend in ${formatTime(resendCooldown)}`;
    }

    return (
      <>
        <RotateCcw size={14} className="mr-1" />
        Resend code
      </>
    );
  };

  return (
    <div className="mx-auto w-full max-w-md space-y-6">
      <div className="space-y-2">
        <Badge variant="outline" className="border-[var(--color-primary-500)]/30 text-[var(--color-primary-500)]">
          <ShieldCheck className="mr-1 h-3.5 w-3.5" />
          OTP Verification
        </Badge>
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">{AUTH_CONFIG.CONTENT.verifyTitle}</h2>
        <p className="text-sm text-muted-foreground">{AUTH_CONFIG.CONTENT.otpInstruction}</p>

        <div className="flex items-center justify-between gap-2 rounded-lg border bg-muted/30 px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <Mail className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm font-medium text-foreground">{userEmail || 'No email selected'}</span>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={goBackToForm} disabled={loading} className="h-8 text-xs">
            <Edit3 className="mr-1 h-3.5 w-3.5" />
            Change
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-3">
          <div className="flex justify-center">
            <OTPInput
              key={otpInputKey}
              length={6}
              value={otp}
              onChange={handleOTPChange}
              disabled={loading || isExpired}
            />
          </div>

          <div className="flex items-center justify-between gap-2">
            <Button
              type="button"
              variant="link"
              onClick={handleResend}
              disabled={isResendDisabled}
              className="h-auto p-0 text-[var(--color-primary-500)] hover:text-[var(--color-primary-600)]"
            >
              {resendLinkText()}
            </Button>
            <Badge variant={isExpired ? 'destructive' : 'secondary'} className="font-medium">
              {isExpired ? 'OTP expired' : `Expires in ${formatTime(secondsLeft)}`}
            </Badge>
          </div>
        </div>

        {(error || otpError) && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Verification failed</AlertTitle>
            <AlertDescription>
              {otpError || error}
              {verificationAttempts >= MAX_ATTEMPTS && (
                <span className="ml-1">
                  Need a new code?
                  <Button
                    type="button"
                    variant="link"
                    onClick={handleResend}
                    disabled={isResendDisabled}
                    className="ml-1 h-auto p-0 align-baseline"
                  >
                    Request now
                  </Button>
                </span>
              )}
            </AlertDescription>
          </Alert>
        )}

        {resendSuccess && (
          <Alert className="border-emerald-200 text-emerald-700 [&_svg]:text-emerald-600">
            <ShieldCheck className="h-4 w-4" />
            <AlertTitle>Code sent</AlertTitle>
            <AlertDescription>{resendSuccess}</AlertDescription>
          </Alert>
        )}

        <Button
          type="submit"
          disabled={isSubmitDisabled}
          className="h-11 w-full bg-[var(--color-primary-500)] text-white hover:bg-[var(--color-primary-600)]"
        >
          {isVerificationLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              Verifying code...
            </span>
          ) : (
            AUTH_CONFIG.CONTENT.continueButton
          )}
        </Button>
      </form>
    </div>
  );
};

export default OTPVerificationForm;
