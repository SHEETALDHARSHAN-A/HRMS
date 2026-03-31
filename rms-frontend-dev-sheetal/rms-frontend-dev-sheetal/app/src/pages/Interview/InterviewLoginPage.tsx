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
        interviewToken={token}
        candidateEmail={email}
      />
    );
  }

  // Render the login/OTP forms
  return (
    <div className="min-h-screen w-screen bg-slate-950 text-slate-100">
      <style>
        {`@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');`}
      </style>
      <div className="relative min-h-screen overflow-hidden">
        <div
          className="pointer-events-none absolute inset-0 opacity-90"
          style={{
            backgroundImage:
              "radial-gradient(circle at top left, rgba(14, 116, 144, 0.45), transparent 45%), radial-gradient(circle at 85% 10%, rgba(251, 191, 36, 0.35), transparent 40%), radial-gradient(circle at 20% 85%, rgba(34, 197, 94, 0.2), transparent 50%)",
          }}
        />
        <div
          className="relative mx-auto flex min-h-screen max-w-6xl flex-col gap-10 px-6 py-12 lg:flex-row lg:items-center"
          style={{ fontFamily: '"Space Grotesk", sans-serif' }}
        >
          <div className="flex-1 space-y-6">
            <p className="text-xs uppercase tracking-[0.32em] text-slate-400">Prayag RMS</p>
            <h1 className="text-4xl font-semibold text-white md:text-5xl">
              A focused, live interview experience
            </h1>
            <p className="max-w-xl text-base text-slate-200/90 md:text-lg">
              Enter the interview room with a clean, distraction-free setup. We verify your identity, then open a secure LiveKit session at the scheduled time.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                { title: "Private access", desc: "Token-based entry and OTP verification." },
                { title: "On-time join", desc: "Room unlocks 5 minutes before the slot." },
                { title: "Live assessment", desc: "Coding workspace launches in a new tab." },
                { title: "Secure audio", desc: "Built on LiveKit WebRTC streams." },
              ].map((item) => (
                <div
                  key={item.title}
                  className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur"
                >
                  <p className="text-sm font-semibold text-white">{item.title}</p>
                  <p className="mt-1 text-xs text-slate-300">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="w-full max-w-md">
            <div className="rounded-2xl bg-white/95 p-8 text-slate-900 shadow-2xl ring-1 ring-white/10 backdrop-blur">
              <div className="mb-6 flex items-center gap-3">
                <Logo size="medium" className="shrink-0" />
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Candidate access</p>
                  <h2 className="text-lg font-semibold text-slate-900">Join Interview</h2>
                </div>
              </div>

              {step === "validate" && (
                <form onSubmit={handleValidateSubmit}>
                  <p className="mb-6 text-sm text-slate-600">
                    Use the email and token from your invite. We will send a verification code before you enter.
                  </p>

                  <div className="mb-4">
                    <label htmlFor="email" className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-600">
                      <Mail size={14} /> Email address
                    </label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="name@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <div className="mb-6">
                    <label htmlFor="token" className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-600">
                      <KeyRound size={14} /> Interview token
                    </label>
                    <Input
                      id="token"
                      type="text"
                      placeholder="Enter the token"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      className="w-full"
                    />
                  </div>

                  {errorMessage && (
                    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
                      {errorMessage}
                    </div>
                  )}

                  <Button
                    type="submit"
                    variant="primary"
                    className="w-full"
                    disabled={isLoading}
                  >
                    {isLoading ? <Loader2 className="animate-spin" /> : "Send verification code"}
                  </Button>
                </form>
              )}

              {step === "otp" && (
                <form onSubmit={handleOtpSubmit}>
                  <p className="mb-6 text-sm text-slate-600">
                    Enter the 6-digit code sent to <strong>{email}</strong>.
                  </p>

                  <OTPInput
                    length={6}
                    value={otp}
                    onChange={(v: string) => {
                      console.debug('InterviewLoginPage OTP change:', { previous: otp, next: v });
                      setOtp(v);
                    }}
                    disabled={isLoading}
                  />

                  {errorMessage && (
                    <div className="my-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
                      {errorMessage}
                    </div>
                  )}

                  <Button
                    type="submit"
                    variant="primary"
                    className="mt-6 w-full"
                    disabled={isLoading}
                  >
                    {isLoading ? <Loader2 className="animate-spin" /> : (<><LogIn size={16} /> Join interview</>)}
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
                    Use a different email or token
                  </Button>
                </form>
              )}

              {step === "joining" && (
                <div className="flex flex-col items-center justify-center py-10">
                  <Loader2 className="h-14 w-14 animate-spin text-slate-700" />
                  <h2 className="mt-6 text-xl font-semibold text-slate-900">Joining session</h2>
                  <p className="mt-2 text-sm text-slate-600">We are preparing your interview room.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InterviewLoginPage;