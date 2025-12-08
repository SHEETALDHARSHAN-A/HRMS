import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { interviewApi } from "../../api/interviewApi";
import { InterviewRoom } from "../../components/interview/InterviewRoom";
import { useToast } from "../../context/ModalContext";
import Logo from "../../components/auth/Logo";
import Button from "../../components/common/Button";
import Input from "../../components/auth/Input";
import { Loader2, KeyRound, Mail, LogIn } from "lucide-react";
import OTPInput from "../../components/auth/OTPInput"; // Assuming you have this from AuthPage

type InterviewStep = "validate" | "otp" | "joining" | "in_progress";

interface LiveKitCredentials {
  url: string;
  token: string;
}

const InterviewLoginPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { showToast } = useToast();

  const [step, setStep] = useState<InterviewStep>("validate");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [liveKitCreds, setLiveKitCreds] = useState<LiveKitCredentials | null>(
    null
  );

  // Pre-fill token from URL query param if it exists
  useEffect(() => {
    const urlToken = searchParams.get("token");
    if (urlToken) {
      setToken(urlToken);
    }
  }, [searchParams]);

  const handleValidateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !token) {
      setErrorMessage("Please enter both email and interview token.");
      return;
    }
    
    setIsLoading(true);
    setErrorMessage("");

    try {
      await interviewApi.validateToken({ email, token });
      showToast("Verification code sent to your email.", "success");
      setStep("otp");
    } catch (error: any) {
      const detail = error.response?.data?.detail || "An unknown error occurred.";
      setErrorMessage(detail);
      showToast(detail, "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length < 6) {
      setErrorMessage("Please enter the 6-digit OTP.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");

    try {
      const response = await interviewApi.verifyOtp({ email, token, otp });
      setLiveKitCreds({
        url: response.livekit_url,
        token: response.livekit_token,
      });
      setStep("joining");
      // Give a moment for the "Joining" message before mounting LiveKit
      setTimeout(() => setStep("in_progress"), 1500);
    } catch (error: any)
    {
      const detail = error.response?.data?.detail || "Invalid or expired OTP.";
      setErrorMessage(detail);
      showToast(detail, "error");
    } finally {
      setIsLoading(false);
    }
  };

  // Render the LiveKit room if in progress
  if (step === "in_progress" && liveKitCreds) {
    return (
      <InterviewRoom
        serverUrl={liveKitCreds.url}
        token={liveKitCreds.token}
      />
    );
  }

  // Render the login/OTP forms
  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-gray-100 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <Logo size="medium" className="mx-auto mb-6" />

        {step === "validate" && (
          <form onSubmit={handleValidateSubmit}>
            <h2 className="mb-4 text-center text-2xl font-bold text-gray-800">
              Join Interview
            </h2>
            <p className="mb-6 text-center text-gray-600">
              Please enter your email and the interview token from your invitation.
            </p>

            <div className="mb-4 flex items-center">
              <div className="mr-3 text-gray-500">
                <Mail size={18} />
              </div>
              <Input
                id="email"
                type="email"
                placeholder="Your Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1"
              />
            </div>
            <div className="mb-6 flex items-center">
              <div className="mr-3 text-gray-500">
                <KeyRound size={18} />
              </div>
              <Input
                id="token"
                type="text"
                placeholder="Interview Token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="flex-1"
              />
            </div>

            {errorMessage && (
              <p className="mb-4 text-center text-sm text-red-600">
                {errorMessage}
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="animate-spin" />
              ) : (
                "Send Verification Code"
              )}
            </Button>
          </form>
        )}

        {step === "otp" && (
          <form onSubmit={handleOtpSubmit}>
            <h2 className="mb-4 text-center text-2xl font-bold text-gray-800">
              Check Your Email
            </h2>
            <p className="mb-6 text-center text-gray-600">
              We sent a 6-digit code to <strong>{email}</strong>. Please enter it
              below.
            </p>

            <OTPInput
              length={6}
              value={otp}
              onChange={(v: string) => {
                // Debug: log OTP updates to ensure parent state receives changes
                // eslint-disable-next-line no-console
                console.debug('InterviewLoginPage OTP change:', { previous: otp, next: v });
                setOtp(v);
              }}
              disabled={isLoading}
            />
            
            {errorMessage && (
              <p className="my-4 text-center text-sm text-red-600">
                {errorMessage}
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              className="mt-6 w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="animate-spin" />
              ) : (
                <><LogIn size={16} /> Join Interview</>
              )}
            </Button>

            <Button
              type="button"
              variant="ghost"
              className="mt-4 w-full"
              onClick={() => {
                setStep("validate");
                setErrorMessage("");
                setOtp("");
              }}
            >
              Use a different email or token?
            </Button>
          </form>
        )}

        {step === "joining" && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-16 w-16 animate-spin text-blue-600" />
            <h2 className="mt-6 text-2xl font-bold text-gray-800">
              Joining Session...
            </h2>
            <p className="mt-2 text-gray-600">
              Please wait while we connect you to the interview.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewLoginPage;