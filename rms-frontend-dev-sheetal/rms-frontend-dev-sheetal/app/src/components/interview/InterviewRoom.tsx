import {
  LiveKitRoom,
  VideoConference,
  ControlBar,
  RoomAudioRenderer,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { AlertCircle, Code2, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ErrorBoundary from "../common/ErrorBoundary";
import { getCodingQuestion, type CodingQuestion } from "../../api/codingApi";
import { saveInterviewAccess } from "../../utils/interviewAccessAuth";

interface InterviewRoomProps {
  token: string;
  serverUrl: string;
  interviewToken?: string;
  candidateEmail?: string;
}

export const InterviewRoom: React.FC<InterviewRoomProps> = ({
  token,
  serverUrl,
  interviewToken,
  candidateEmail,
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [question, setQuestion] = useState<CodingQuestion | null>(null);
  const [questionStatus, setQuestionStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [questionError, setQuestionError] = useState("");
  const navigate = useNavigate();

  const openCodingWorkspace = () => {
    if (!interviewToken || !candidateEmail) return;
    const target = `/interview/coding?token=${encodeURIComponent(interviewToken)}&email=${encodeURIComponent(candidateEmail)}`;
    window.open(target, "_blank", "noopener,noreferrer");
  };

  useEffect(() => {
    if (!interviewToken || !candidateEmail) return;
    saveInterviewAccess(interviewToken, candidateEmail, "interview-room");
  }, [interviewToken, candidateEmail]);

  useEffect(() => {
    if (!interviewToken || !candidateEmail) return;
    let isActive = true;

    const loadQuestion = async () => {
      setQuestionStatus("loading");
      setQuestionError("");
      const result = await getCodingQuestion(interviewToken, candidateEmail);
      if (!isActive) return;
      if (!result.success) {
        setQuestionStatus("error");
        setQuestionError(result.error || "Unable to load the live question.");
        return;
      }
      setQuestion(result.data);
      setQuestionStatus("ready");
    };

    void loadQuestion();

    return () => {
      isActive = false;
    };
  }, [interviewToken, candidateEmail]);

  return (
    <div className="interview-shell relative min-h-screen w-screen bg-slate-950 text-slate-100">
      <style>
        {`@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
        .interview-shell { font-family: "Space Grotesk", sans-serif; }
        .interview-shell .lk-video-conference { height: 100%; border-radius: 20px; overflow: hidden; background: #0b1220; }
        .interview-shell .lk-video-conference .lk-control-bar { display: none !important; }
        .interview-shell .custom-controls { position: absolute; left: 0; right: 0; bottom: 16px; z-index: 40; display: flex; justify-content: center; pointer-events: none; padding: 0 16px; }
        .interview-shell .custom-controls .lk-control-bar { display: flex !important; gap: 10px; margin: 0; padding: 0; width: auto; max-width: none; background: transparent; border: 0; box-shadow: none; pointer-events: auto; }
        .interview-shell .custom-controls .lk-button { border-radius: 999px; width: 46px; height: 46px; border: 1px solid rgba(148, 163, 184, 0.35); background: rgba(2, 6, 23, 0.72); backdrop-filter: blur(8px); }
        .interview-shell .custom-controls .lk-button:hover { background: rgba(15, 23, 42, 0.9); }
        .interview-shell .custom-controls .lk-disconnect-button { background: rgba(220, 38, 38, 0.9); border-color: rgba(254, 202, 202, 0.5); }
        .interview-shell .custom-controls .lk-disconnect-button:hover { background: rgba(185, 28, 28, 0.95); }
        `}
      </style>
      <div
        className="pointer-events-none absolute inset-0 opacity-80"
        style={{
          backgroundImage:
            "radial-gradient(circle at 10% 10%, rgba(34, 197, 94, 0.2), transparent 45%), radial-gradient(circle at 90% 10%, rgba(14, 116, 144, 0.4), transparent 40%)",
        }}
      />

      <header className="relative z-10 flex flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Live interview</p>
          <h1 className="text-lg font-semibold text-white">Interview Room</h1>
          <div className="mt-2 flex items-center gap-2 text-xs text-slate-300">
            <span className={`h-2.5 w-2.5 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            {isConnected ? 'Connected' : 'Connecting'}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {interviewToken && candidateEmail && (
            <button
              type="button"
              onClick={openCodingWorkspace}
              className="inline-flex items-center gap-2 rounded-full border border-emerald-200/40 bg-emerald-200/10 px-4 py-2 text-xs font-semibold text-emerald-100 backdrop-blur hover:bg-emerald-200/20"
            >
              <Code2 className="h-4 w-4" />
              Open assessment
            </button>
          )}
        </div>
      </header>

      <div className="relative z-10 flex h-[calc(100vh-96px)] flex-col px-6 pb-6">
        <div className="grid flex-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-3xl border border-white/10 bg-slate-900/60 p-4 shadow-2xl backdrop-blur">
            <ErrorBoundary>
              <LiveKitRoom
                video={true}
                audio={true}
                token={token}
                serverUrl={serverUrl}
                connectOptions={{ autoSubscribe: true }}
                data-lk-theme="default"
                className="relative h-full"
                onConnected={() => setIsConnected(true)}
                onDisconnected={() => {
                  // When disconnected (for example via the Leave control), navigate
                  // to a friendly thank-you screen.
                  try {
                    navigate('/interview/thank-you')
                  } catch (err) {
                    console.warn('Navigation to thank-you failed', err)
                  }
                }}
              >
                {/* The VideoConference component handles all participant tiles */}
                <VideoConference />

                {/* Custom Controls */}
                <div className="custom-controls">
                  <ControlBar
                    controls={{
                      microphone: true,
                      camera: true,
                      screenShare: true,
                      leave: true,
                      chat: false, // Disable chat to avoid ChatToggle/layout-context errors
                    }}
                  />
                </div>

                {/* Handles all remote audio tracks */}
                <RoomAudioRenderer />

                {/* Loading overlay */}
                {!isConnected && (
                  <div className="absolute inset-0 z-50 flex flex-col items-center justify-center rounded-3xl bg-slate-950/90 text-white">
                    <Loader2 className="mb-4 h-12 w-12 animate-spin" />
                    <p className="text-lg font-semibold">Connecting to interview room...</p>
                    <p className="mt-1 text-xs text-slate-300">Please keep this tab open.</p>
                  </div>
                )}
              </LiveKitRoom>
            </ErrorBoundary>
          </div>

          {(interviewToken && candidateEmail) && (
            <aside className="rounded-3xl border border-white/10 bg-slate-900/70 p-4 shadow-2xl backdrop-blur">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.28em] text-slate-400">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  Live prompt
                </div>
                {question?.challengeType && (
                  <span className="rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[10px] font-semibold text-slate-100">
                    {question.challengeType === "mcq" ? "MCQ" : "CODING"}
                  </span>
                )}
              </div>

              {questionStatus === "loading" && (
                <div className="mt-4 flex items-center gap-2 text-sm text-slate-300">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading question...
                </div>
              )}

              {questionStatus === "error" && (
                <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-100">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertCircle className="h-4 w-4" />
                    Unable to load question
                  </div>
                  <p className="mt-2 text-rose-100/80">{questionError}</p>
                </div>
              )}

              {questionStatus === "ready" && question && (
                <div className="mt-4 space-y-3 text-sm text-slate-200">
                  <div>
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Question</p>
                    <h2 className="mt-2 text-base font-semibold text-white">{question.title || "Assessment"}</h2>
                    <p className="mt-1 text-xs text-slate-400">Difficulty: {question.difficulty || "medium"}</p>
                  </div>

                  <div className="max-h-44 overflow-y-auto rounded-2xl border border-white/10 bg-slate-950/60 p-3 text-xs leading-5 text-slate-200/90">
                    {question.problem || question.instructions || "No question description available."}
                  </div>

                  {Array.isArray(question.constraints) && question.constraints.length > 0 && (
                    <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3 text-xs">
                      <p className="font-semibold text-slate-300">Constraints</p>
                      <ul className="mt-2 list-disc space-y-1 pl-4 text-slate-300/90">
                        {question.constraints.slice(0, 3).map((item: string, idx: number) => (
                          <li key={`${item}-${idx}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {Array.isArray(question.hints) && question.hints.length > 0 && (
                    <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-3 text-xs">
                      <p className="font-semibold text-slate-300">Hints</p>
                      <ul className="mt-2 list-disc space-y-1 pl-4 text-slate-300/90">
                        {question.hints.slice(0, 2).map((item: string, idx: number) => (
                          <li key={`${item}-${idx}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={openCodingWorkspace}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-emerald-200/40 bg-emerald-200/10 px-4 py-2 text-xs font-semibold text-emerald-100 hover:bg-emerald-200/20"
                  >
                    <Code2 className="h-4 w-4" />
                    Open full workspace
                  </button>
                </div>
              )}
            </aside>
          )}
        </div>
      </div>
    </div>
  );
};