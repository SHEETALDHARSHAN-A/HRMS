import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import {
  AlertCircle,
  CheckCircle2,
  CircleDot,
  Code2,
  XCircle,
  ListChecks,
  Loader2,
  Play,
  Send,
  TerminalSquare,
} from "lucide-react";

import {
  getLatestCodingSubmission,
  getCodingQuestion,
  runCodingSolution,
  submitCodingSolution,
  type CodingQuestion,
  type CodingRunResult,
  type CodingSubmissionResult,
  type McqAnswerItem,
} from "../../api/codingApi";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Label } from "../../components/ui/label";
import { Progress } from "../../components/ui/progress";
import { RadioGroup, RadioGroupItem } from "../../components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { hasInterviewAccess, saveInterviewAccess } from "../../utils/interviewAccessAuth";


type ChallengeType = "coding" | "mcq";


const editorShell =
  "overflow-hidden rounded-xl border border-slate-800/90 bg-[#0b1020] shadow-[0_30px_70px_-50px_rgba(15,23,42,0.9)]";


const fallbackCodeByLanguage: Record<string, string> = {
  python: "def solve(input_data):\n    # Write your solution here\n    return None\n",
  javascript: "function solve(inputData) {\n  // Write your solution here\n  return null;\n}\n",
  typescript: "function solve(inputData: unknown): unknown {\n  // Write your solution here\n  return null;\n}\n",
  java: "class Solution {\n    public static Object solve(Object inputData) {\n        // Write your solution here\n        return null;\n    }\n}\n",
  cpp: "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n",
  go: "package main\n\nfunc solve(inputData any) any {\n    // Write your solution here\n    return nil\n}\n",
};


const monacoLanguageMap: Record<string, string> = {
  cpp: "cpp",
  csharp: "csharp",
  javascript: "javascript",
  typescript: "typescript",
  python: "python",
  java: "java",
  go: "go",
  rust: "rust",
  php: "php",
  ruby: "ruby",
  sql: "sql",
  bash: "shell",
};


const toMonacoLanguage = (language: string): string => {
  return monacoLanguageMap[language] || "plaintext";
};


const normalizeMcqQuestions = (raw: any): any[] => {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((q: any, index: number) => {
      const question = String(q?.question || q?.prompt || "").trim();
      if (!question) return null;

      const rawOptions = Array.isArray(q?.options) ? q.options : [];
      const options = rawOptions
        .map((opt: any, optionIndex: number) => {
          if (typeof opt === "string") {
            return {
              id: `q${index + 1}_opt${optionIndex + 1}`,
              text: opt,
            };
          }
          if (opt && typeof opt === "object") {
            const text = String(opt.text || opt.label || "").trim();
            if (!text) return null;
            return {
              id: String(opt.id || `q${index + 1}_opt${optionIndex + 1}`),
              text,
            };
          }
          return null;
        })
        .filter(Boolean);

      if (options.length < 2) return null;

      return {
        id: String(q?.id || `q_${index + 1}`),
        question,
        options,
      };
    })
    .filter(Boolean);
};


const normalizeCodingExamples = (rawExamples: any, rawTestCases: any[]): Array<{ input: string; output: string; explanation: string }> => {
  const normalizedFromPayload = Array.isArray(rawExamples)
    ? rawExamples
        .map((item: any) => {
          const input = String(item?.input || item?.sampleInput || item?.stdin || "").trim();
          const output = String(item?.output || item?.expectedOutput || item?.sampleOutput || "").trim();
          const explanation = String(item?.explanation || item?.note || "").trim();
          if (!input && !output && !explanation) return null;
          return {
            input,
            output,
            explanation,
          };
        })
        .filter(Boolean)
    : [];

  if (normalizedFromPayload.length > 0) {
    return normalizedFromPayload as Array<{ input: string; output: string; explanation: string }>;
  }

  if (!Array.isArray(rawTestCases)) return [];

  return rawTestCases
    .filter((item: any) => !item?.isHidden)
    .slice(0, 2)
    .map((item: any) => {
      const input = String(item?.input || "").trim();
      const output = String(item?.expectedOutput || "").trim();
      if (!input && !output) return null;
      return {
        input,
        output,
        explanation: "Sample derived from visible test case.",
      };
    })
    .filter(Boolean) as Array<{ input: string; output: string; explanation: string }>;
};


const InterviewCodingPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";
  const email = searchParams.get("email") || "";

  const [isLoadingQuestion, setIsLoadingQuestion] = useState(true);
  const [isLoadingLatest, setIsLoadingLatest] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");

  const [question, setQuestion] = useState<CodingQuestion | null>(null);
  const [challengeType, setChallengeType] = useState<ChallengeType>("coding");
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(fallbackCodeByLanguage.python);
  const [hasCustomCode, setHasCustomCode] = useState(false);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, string>>({});
  const [runResult, setRunResult] = useState<CodingRunResult | null>(null);
  const [evaluation, setEvaluation] = useState<CodingSubmissionResult | null>(null);
  const [lastSubmission, setLastSubmission] = useState<CodingSubmissionResult | null>(null);
  const [activeTab, setActiveTab] = useState<"problem" | "constraints" | "hints" | "testcases">("problem");
  const [activePanel, setActivePanel] = useState<"editor" | "output">("editor");
  const [fontSize, setFontSize] = useState(14);
  const [copied, setCopied] = useState(false);

  const mcqQuestions = useMemo(() => normalizeMcqQuestions(question?.questions), [question?.questions]);

  const mcqAllAnswered = useMemo(() => {
    if (mcqQuestions.length === 0) return false;
    return mcqQuestions.every((q) => Boolean(mcqAnswers[q.id]));
  }, [mcqQuestions, mcqAnswers]);

  const canSubmit = useMemo(() => {
    if (!token || !email || isSubmitting || isRunning || !question) return false;
    if (challengeType === "mcq") return mcqAllAnswered;
    return code.trim().length > 0;
  }, [token, email, isSubmitting, isRunning, question, challengeType, mcqAllAnswered, code]);

  const canRun = useMemo(() => {
    if (!token || !email || isSubmitting || isRunning || !question) return false;
    if (challengeType === "mcq") return mcqAllAnswered;
    return code.trim().length > 0;
  }, [token, email, isSubmitting, isRunning, question, challengeType, mcqAllAnswered, code]);

  useEffect(() => {
    const loadQuestion = async () => {
      if (!token || !email) {
        setError("Missing interview token or email. Open this page from the interview room.");
        setQuestion(null);
        setIsLoadingQuestion(false);
        return;
      }

      if (!hasInterviewAccess(token, email)) {
        setError("Authorization required. Please join from interview login and complete OTP verification first.");
        setQuestion(null);
        setIsLoadingQuestion(false);
        return;
      }

      saveInterviewAccess(token, email, "coding-workspace");

      setIsLoadingQuestion(true);
      setError("");
      setQuestion(null);
      setRunResult(null);
      setEvaluation(null);
      setLastSubmission(null);

      const result = await getCodingQuestion(token, email);
      if (!result.success) {
        setError(result.error);
        setQuestion(null);
        setIsLoadingQuestion(false);
        return;
      }

      const payload = result.data;
      const type = (payload.challengeType || "coding") as ChallengeType;
      setQuestion(payload);
      setChallengeType(type === "mcq" ? "mcq" : "coding");
      setActiveTab("problem");
      setActivePanel("editor");

      const firstLanguage = payload?.languages?.[0] || "python";
      setLanguage(firstLanguage);

      const starter = resolveStarterCode(firstLanguage, payload);
      setCode(starter);
      setHasCustomCode(false);
      setCopied(false);
      setMcqAnswers({});

      setIsLoadingLatest(true);
      const latestSubmissionResult = await getLatestCodingSubmission(token, email);
      if (latestSubmissionResult.success) {
        setLastSubmission(latestSubmissionResult.data);
      } else {
        setLastSubmission(null);
      }
      setIsLoadingLatest(false);
      setIsLoadingQuestion(false);
    };

    void loadQuestion();
  }, [token, email]);

  const goToInterviewJoin = () => {
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (email) params.set("email", email);
    navigate(`/interview/join${params.toString() ? `?${params.toString()}` : ""}`);
  };

  const resolveStarterCode = (lang: string, source?: CodingQuestion | null) => {
    const payload = source ?? question;
    return payload?.starterCode?.[lang] || fallbackCodeByLanguage[lang] || fallbackCodeByLanguage.python;
  };

  const onChangeLanguage = (nextLanguage: string) => {
    setLanguage(nextLanguage);
    setRunResult(null);
    if (!hasCustomCode) {
      setCode(resolveStarterCode(nextLanguage));
    }
  };

  const onResetCode = () => {
    setCode(resolveStarterCode(language));
    setHasCustomCode(false);
    setRunResult(null);
  };

  const onCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const onChooseMcqOption = (questionId: string, optionId: string) => {
    setMcqAnswers((prev) => ({
      ...prev,
      [questionId]: optionId,
    }));
  };

  const onSubmit = async () => {
    if (!canSubmit || !question) return;

    setIsSubmitting(true);
    setError("");
    setRunResult(null);
    setActivePanel("output");

    const mcqAnswersPayload: McqAnswerItem[] = Object.entries(mcqAnswers).map(([questionId, selectedOptionId]) => ({
      questionId,
      selectedOptionId,
    }));

    const result = await submitCodingSolution({
      token,
      email,
      challengeType,
      language: challengeType === "coding" ? language : undefined,
      code: challengeType === "coding" ? code : undefined,
      mcqAnswers: challengeType === "mcq" ? mcqAnswersPayload : undefined,
      question,
    });

    if (!result.success) {
      setError(result.error);
      setIsSubmitting(false);
      return;
    }

    setEvaluation(result.data);
    setLastSubmission(result.data);
    setIsSubmitting(false);
  };

  const onRun = async () => {
    if (!canRun || !question) return;

    setIsRunning(true);
    setError("");
    setRunResult(null);
    setActivePanel("output");

    const mcqAnswersPayload: McqAnswerItem[] = Object.entries(mcqAnswers).map(([questionId, selectedOptionId]) => ({
      questionId,
      selectedOptionId,
    }));

    const result = await runCodingSolution({
      token,
      email,
      challengeType,
      language: challengeType === "coding" ? language : undefined,
      code: challengeType === "coding" ? code : undefined,
      mcqAnswers: challengeType === "mcq" ? mcqAnswersPayload : undefined,
      question,
    });

    if (!result.success) {
      setError(result.error);
      setIsRunning(false);
      return;
    }

    setRunResult(result.data);
    setIsRunning(false);
  };

  const testCases = Array.isArray(question?.testCases) ? question?.testCases : [];
  const mcqAnsweredCount = Object.keys(mcqAnswers).length;
  const mcqProgress = mcqQuestions.length > 0 ? Math.round((mcqAnsweredCount / mcqQuestions.length) * 100) : 0;
  const constraints = Array.isArray(question?.constraints) ? question.constraints : [];
  const hints = Array.isArray(question?.hints) ? question.hints : [];
  const inputFormat = typeof question?.inputFormat === "string" ? question.inputFormat.trim() : "";
  const outputFormat = typeof question?.outputFormat === "string" ? question.outputFormat.trim() : "";
  const detailedPrompt = typeof question?.detailedPrompt === "string" ? question.detailedPrompt.trim() : "";
  const problemExamples = useMemo(
    () => normalizeCodingExamples(question?.examples, testCases),
    [question?.examples, testCases]
  );
  const languages = question?.languages && question.languages.length > 0 ? question.languages : ["python", "javascript"];
  const difficultyLabel = question?.difficulty || "medium";
  const difficultyValue = difficultyLabel.toLowerCase();
  const difficultyStyles =
    difficultyValue === "easy"
      ? "bg-emerald-100 text-emerald-700"
      : difficultyValue === "hard"
      ? "bg-rose-100 text-rose-700"
      : "bg-amber-100 text-amber-700";
  const tabs = [
    { id: "problem", label: "Problem", enabled: true },
    { id: "constraints", label: "Constraints", enabled: constraints.length > 0 },
    { id: "hints", label: "Hints", enabled: hints.length > 0 },
    {
      id: "testcases",
      label: `Tests${testCases.length > 0 ? ` (${testCases.length})` : ""}`,
      enabled: testCases.length > 0,
    },
  ] as const;

  return (
    <div className="coding-shell relative min-h-screen overflow-hidden">
      <style>
        {`@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        .coding-shell { font-family: "Outfit", sans-serif; }
        .coding-shell .code-font { font-family: "JetBrains Mono", monospace; }
        `}
      </style>
      <div
        className="pointer-events-none absolute inset-0 opacity-90"
        style={{
          backgroundImage:
            "radial-gradient(circle at 10% 20%, rgba(251, 146, 60, 0.25), transparent 45%), radial-gradient(circle at 90% 15%, rgba(20, 184, 166, 0.2), transparent 40%), radial-gradient(circle at 20% 85%, rgba(59, 130, 246, 0.16), transparent 50%)",
        }}
      />
      <div className="relative z-10 mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-10">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-orange-100 p-3 text-orange-700">
              <Code2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Live assessment</p>
              <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">Interview Coding Workspace</h1>
              <p className="mt-2 max-w-xl text-sm text-slate-600">
                {challengeType === "mcq"
                  ? "Complete every multiple-choice question to finish the evaluation. Your progress is tracked live."
                   : "Solve the challenge in the editor, run test cases for output preview, then submit the final answer."}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="rounded-full border border-slate-200 bg-white/80 text-slate-600" variant="secondary">
              {challengeType === "mcq" ? "MCQ" : "CODING"}
            </Badge>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${difficultyStyles}`}>
              {difficultyLabel}
            </span>
          </div>
        </header>

        {isLoadingQuestion ? (
          <div className="mt-8 rounded-[28px] border border-slate-200/70 bg-white/90 p-10 text-center shadow-[0_30px_80px_-60px_rgba(15,23,42,0.35)]">
            <div className="flex items-center justify-center gap-3 text-slate-700">
              <Loader2 className="h-6 w-6 animate-spin" />
              Loading assessment question...
            </div>
          </div>
        ) : !question ? (
          <div className="mt-8 rounded-[28px] border border-rose-200/80 bg-rose-50/90 p-8 shadow-[0_30px_80px_-60px_rgba(15,23,42,0.35)]">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-rose-100 p-2 text-rose-600">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-rose-900">Assessment is not accessible right now</h2>
                <p className="mt-2 text-sm text-rose-800">{error || "The assessment window may not have started yet, or it may have expired."}</p>
                <p className="mt-2 text-xs text-rose-700/90">
                  Re-open this page from the interview room, or contact the recruiter if the schedule looks incorrect.
                </p>
                <button
                  type="button"
                  onClick={goToInterviewJoin}
                  className="mt-4 inline-flex items-center rounded-full border border-rose-300 bg-white px-4 py-2 text-xs font-semibold text-rose-700 transition hover:bg-rose-100"
                >
                  Go to interview login
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
            <section className="rounded-[28px] border border-slate-200/70 bg-white/90 p-6 shadow-[0_30px_80px_-60px_rgba(15,23,42,0.35)] backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Challenge</p>
                  <h2 className="mt-2 text-2xl font-semibold text-slate-900">{question?.title || "Assessment"}</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Source: <span className="font-medium capitalize text-slate-700">{question?.source || "ai"}</span>
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200/70 bg-white/80 px-3 py-2 text-xs font-semibold text-slate-600">
                  {challengeType === "mcq" ? "Objective scoring" : "Live coding"}
                </div>
              </div>

              {challengeType === "coding" ? (
                <>
                  <div className="mt-6 flex flex-wrap gap-2">
                    {tabs.map((tab) => {
                      const isActive = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          disabled={!tab.enabled}
                          onClick={() => tab.enabled && setActiveTab(tab.id)}
                          className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                            isActive
                              ? "bg-slate-900 text-white"
                              : "border border-slate-200 text-slate-600 hover:border-slate-300"
                          } ${tab.enabled ? "opacity-100" : "cursor-not-allowed opacity-40"}`}
                        >
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>

                  <div className="mt-4 text-sm leading-6 text-slate-700">
                    {activeTab === "problem" && (
                      <div className="space-y-4">
                        <p className="whitespace-pre-wrap">{question?.problem || "No coding question available."}</p>

                        {(inputFormat || outputFormat) && (
                          <div className="grid gap-3 md:grid-cols-2">
                            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Input format</p>
                              <p className="mt-2 text-xs text-slate-700 whitespace-pre-wrap">{inputFormat || "Input format not specified."}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Output format</p>
                              <p className="mt-2 text-xs text-slate-700 whitespace-pre-wrap">{outputFormat || "Output format not specified."}</p>
                            </div>
                          </div>
                        )}

                        {problemExamples.length > 0 && (
                          <div className="space-y-3">
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sample input and output</p>
                            {problemExamples.map((sample, index) => (
                              <div key={`${sample.input}-${sample.output}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                                <p className="text-xs font-semibold text-slate-600">Example {index + 1}</p>
                                <p className="mt-2 text-xs text-slate-700 whitespace-pre-wrap">
                                  <span className="font-semibold">Input:</span> {sample.input || "N/A"}
                                </p>
                                <p className="mt-1 text-xs text-slate-700 whitespace-pre-wrap">
                                  <span className="font-semibold">Output:</span> {sample.output || "N/A"}
                                </p>
                                {sample.explanation && (
                                  <p className="mt-1 text-xs text-slate-700 whitespace-pre-wrap">
                                    <span className="font-semibold">Explanation:</span> {sample.explanation}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {constraints.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Constraints</p>
                            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                              {constraints.map((item: string, idx: number) => (
                                <li key={`${item}-${idx}`}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {hints.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Hints</p>
                            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                              {hints.map((item: string, idx: number) => (
                                <li key={`${item}-${idx}`}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {detailedPrompt && (
                          <details className="rounded-2xl border border-slate-200 bg-white p-3">
                            <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Full specification text</summary>
                            <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-700">{detailedPrompt}</pre>
                          </details>
                        )}
                      </div>
                    )}
                    {activeTab === "constraints" && (
                      <ul className="list-disc space-y-2 pl-5">
                        {constraints.map((item: string, idx: number) => (
                          <li key={`${item}-${idx}`}>{item}</li>
                        ))}
                      </ul>
                    )}
                    {activeTab === "hints" && (
                      <ul className="list-disc space-y-2 pl-5">
                        {hints.map((item: string, idx: number) => (
                          <li key={`${item}-${idx}`}>{item}</li>
                        ))}
                      </ul>
                    )}
                    {activeTab === "testcases" && (
                      <div className="space-y-3">
                        {testCases.map((testCase: any, index: number) => (
                          <div key={String(testCase?.id || index)} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                            <p className="text-xs font-semibold text-slate-500">
                              Case {index + 1} {testCase?.isHidden ? "(hidden)" : "(visible)"}
                            </p>
                            <p className="mt-2 text-xs text-slate-600">Input: {String(testCase?.input || "")}</p>
                            {testCase?.expectedOutput && (
                              <p className="text-xs text-slate-600">Expected: {String(testCase.expectedOutput)}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <p className="mt-4 text-sm text-slate-700">{question?.instructions || "Choose one option for each question."}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    Passing score: <span className="font-semibold">{question?.passingScore ?? 60}%</span>
                  </p>
                  <div className="mt-4 space-y-4">
                    {mcqQuestions.map((q, index) => (
                      <div key={q.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                        <p className="text-sm font-semibold text-slate-900">
                          {index + 1}. {q.question}
                        </p>
                        <RadioGroup
                          className="mt-3 space-y-2"
                          value={mcqAnswers[q.id] || ""}
                          onValueChange={(value) => onChooseMcqOption(q.id, value)}
                        >
                          {q.options.map((opt: any) => {
                            const inputId = `option-${q.id}-${opt.id}`;
                            return (
                              <div
                                key={opt.id}
                                className="flex items-start gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm transition hover:border-slate-300 hover:bg-slate-50"
                              >
                                <RadioGroupItem id={inputId} value={opt.id} className="mt-0.5" />
                                <Label htmlFor={inputId} className="cursor-pointer text-sm font-normal text-slate-700">
                                  {opt.text}
                                </Label>
                              </div>
                            );
                          })}
                        </RadioGroup>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </section>

            <section className="space-y-4">
              {challengeType === "coding" ? (
                <div className="rounded-[28px] border border-slate-800/80 bg-slate-950/95 p-4 text-slate-100 shadow-[0_30px_80px_-60px_rgba(15,23,42,0.7)]">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-slate-400">
                      <TerminalSquare className="h-4 w-4 text-orange-400" />
                      Workspace
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="flex items-center gap-1 rounded-full border border-slate-700/80 bg-slate-900/60 p-1">
                        <button
                          type="button"
                          onClick={() => setActivePanel("editor")}
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold transition ${
                            activePanel === "editor" ? "bg-white text-slate-900" : "text-slate-300"
                          }`}
                        >
                          Code
                        </button>
                        <button
                          type="button"
                          onClick={() => setActivePanel("output")}
                          className={`rounded-full px-3 py-1 text-[11px] font-semibold transition ${
                            activePanel === "output" ? "bg-white text-slate-900" : "text-slate-300"
                          }`}
                        >
                          Output
                        </button>
                      </div>

                      <div className="flex items-center gap-2">
                        <Label htmlFor="language-select" className="text-[11px] font-semibold text-slate-300">
                          Language
                        </Label>
                        <Select value={language} onValueChange={onChangeLanguage}>
                          <SelectTrigger id="language-select" className="w-[160px] border-slate-700/80 bg-slate-900 text-slate-100">
                            <SelectValue placeholder="Select language" />
                          </SelectTrigger>
                          <SelectContent>
                            {languages.map((lang: string) => (
                              <SelectItem key={lang} value={lang}>
                                {lang}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex items-center gap-2">
                        <Label htmlFor="font-select" className="text-[11px] font-semibold text-slate-300">
                          Font
                        </Label>
                        <Select value={String(fontSize)} onValueChange={(value) => setFontSize(Number(value))}>
                          <SelectTrigger id="font-select" className="w-[90px] border-slate-700/80 bg-slate-900 text-slate-100">
                            <SelectValue placeholder="Size" />
                          </SelectTrigger>
                          <SelectContent>
                            {[12, 13, 14, 15, 16, 18].map((size) => (
                              <SelectItem key={size} value={String(size)}>
                                {size}px
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          onClick={onCopyCode}
                          variant="outline"
                          className="h-8 rounded-full border-slate-700/80 bg-transparent px-3 text-[11px] text-slate-200 hover:bg-slate-800"
                        >
                          {copied ? "Copied" : "Copy"}
                        </Button>
                        <Button
                          type="button"
                          onClick={onResetCode}
                          variant="outline"
                          className="h-8 rounded-full border-slate-700/80 bg-transparent px-3 text-[11px] text-slate-200 hover:bg-slate-800"
                        >
                          Reset
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3">
                    {activePanel === "editor" ? (
                      <div className={editorShell}>
                        <Editor
                          height="460px"
                          language={toMonacoLanguage(language)}
                          value={code}
                          onChange={(value) => {
                            setCode(value || "");
                            setHasCustomCode(true);
                          }}
                          options={{
                            minimap: { enabled: false },
                            fontSize,
                            fontFamily: "JetBrains Mono",
                            automaticLayout: true,
                            scrollBeyondLastLine: false,
                            wordWrap: "on",
                            cursorStyle: "line",
                            cursorWidth: 2,
                            cursorBlinking: "smooth",
                            cursorSmoothCaretAnimation: "on",
                            smoothScrolling: true,
                            lineHeight: 20,
                            lineNumbersMinChars: 3,
                            tabSize: 2,
                            insertSpaces: true,
                            padding: { top: 10, bottom: 10 },
                            renderLineHighlight: "line",
                          }}
                          theme="vs-dark"
                        />
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-slate-800/90 bg-slate-950/70 p-4 text-sm text-slate-200">
                        {(isSubmitting || isRunning) && (
                          <div className="flex items-center gap-2 text-slate-300">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            {isRunning ? "Running test cases..." : "Running final evaluation..."}
                          </div>
                        )}
                        {!isSubmitting && !isRunning && error && (
                          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-100">
                            <div className="flex items-center gap-2 font-semibold">
                              <AlertCircle className="h-4 w-4" />
                              Could not complete assessment
                            </div>
                            <p className="mt-2 text-rose-100/80">{error}</p>
                          </div>
                        )}
                        {!isSubmitting && !isRunning && !error && runResult && (
                          <div className="space-y-3 rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-3">
                            <div className="flex items-center justify-between">
                              <p className="text-xs uppercase tracking-[0.25em] text-cyan-200">Run preview</p>
                              <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-semibold text-cyan-200">
                                Score {runResult.score ?? "N/A"}/100
                              </span>
                            </div>
                            <p className="text-xs text-cyan-100/90">{runResult.summary || runResult.feedback || "Run completed."}</p>
                            <p className="text-[11px] text-cyan-100/80">
                              Source: {runResult.evaluationSource || "unknown"}
                              {String(runResult.evaluationSource || "").startsWith("runtime")
                                ? " (actual runtime execution)"
                                : " (estimated/non-runtime evaluation)"}
                            </p>
                            {Array.isArray(runResult.testCaseResults) && runResult.testCaseResults.length > 0 && (
                              <div className="space-y-2">
                                {runResult.testCaseResults.slice(0, 6).map((item: any, index: number) => {
                                  const passed = Boolean(item?.passed || item?.isCorrect);
                                  const inputText = String(item?.input ?? "").trim();
                                  const expectedText = String(item?.expectedOutput ?? item?.expected ?? "").trim();
                                  const actualText = String(item?.actualOutput ?? item?.output ?? "").trim();
                                  const notesText = String(item?.notes ?? "").trim();
                                  return (
                                    <div
                                      key={String(item?.id || index)}
                                      className={`rounded-lg border px-2 py-2 text-[11px] ${
                                        passed ? "border-emerald-500/40 bg-emerald-500/10" : "border-rose-500/40 bg-rose-500/10"
                                      }`}
                                    >
                                      <div className="flex items-center gap-2">
                                        {passed ? (
                                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-300" />
                                        ) : (
                                          <XCircle className="h-3.5 w-3.5 text-rose-300" />
                                        )}
                                        <span className="text-slate-100">Case {index + 1}: {passed ? "Pass" : "Fail"}</span>
                                      </div>
                                      {(inputText || expectedText || actualText || notesText) && (
                                        <div className="mt-2 space-y-1 text-[10px] text-slate-200/90">
                                          {inputText && (
                                            <p className="whitespace-pre-wrap">
                                              <span className="font-semibold text-slate-100">Input:</span> {inputText}
                                            </p>
                                          )}
                                          {expectedText && (
                                            <p className="whitespace-pre-wrap">
                                              <span className="font-semibold text-slate-100">Expected:</span> {expectedText}
                                            </p>
                                          )}
                                          {actualText && (
                                            <p className="whitespace-pre-wrap">
                                              <span className="font-semibold text-slate-100">Actual:</span> {actualText}
                                            </p>
                                          )}
                                          {notesText && (
                                            <p className="whitespace-pre-wrap text-slate-300">
                                              <span className="font-semibold text-slate-200">Notes:</span> {notesText}
                                            </p>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        )}
                        {!isSubmitting && !isRunning && !error && !runResult && !evaluation && !isLoadingLatest && !lastSubmission && (
                          <div className="text-xs text-slate-400">Run your code to preview outputs, then submit to save the final evaluation.</div>
                        )}
                        {!isSubmitting && !isRunning && evaluation && (
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Result</p>
                                <p className="mt-2 text-sm font-semibold text-white">Score {evaluation.score ?? "N/A"}/100</p>
                              </div>
                              <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-semibold text-white">
                                {evaluation.passed ? "Passed" : "Review"}
                              </span>
                            </div>
                            <p className="text-xs text-slate-300">{evaluation.feedback || "No feedback returned."}</p>
                          </div>
                        )}
                        {!isSubmitting && !isRunning && !evaluation && isLoadingLatest && (
                          <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Loading latest saved submission...
                          </div>
                        )}
                        {!isSubmitting && !isRunning && !evaluation && lastSubmission && (
                          <div className="mt-3 rounded-xl border border-slate-700 bg-slate-900/60 p-3 text-xs text-slate-200">
                            <p className="uppercase tracking-[0.25em] text-slate-400">Latest saved submission</p>
                            <p className="mt-2">Score {lastSubmission.score ?? "N/A"}/100</p>
                            <p className="mt-1 text-slate-300">{lastSubmission.feedback || "Saved evaluation available."}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                    <span>Autosave is enabled. Submit when you are ready.</span>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        onClick={onRun}
                        disabled={!canRun}
                        variant="outline"
                        className="inline-flex items-center gap-2 rounded-full border-cyan-400/50 bg-cyan-500/10 text-cyan-100 hover:bg-cyan-500/20"
                      >
                        {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                        {isRunning ? "Running..." : "Run"}
                      </Button>
                      <Button
                        type="button"
                        onClick={onSubmit}
                        disabled={!canSubmit}
                        className="inline-flex items-center gap-2 rounded-full bg-orange-400 text-slate-900 hover:bg-orange-300"
                      >
                        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        {isSubmitting ? "Evaluating..." : "Submit"}
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-[28px] border border-slate-200/70 bg-white/90 p-5 shadow-[0_25px_60px_-45px_rgba(15,23,42,0.35)]">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <ListChecks className="h-4 w-4 text-orange-500" />
                    MCQ progress
                  </div>
                  <p className="mt-2 text-sm text-slate-600">
                    {mcqAnsweredCount} / {mcqQuestions.length} answered
                  </p>
                  <Progress className="mt-3" value={mcqProgress} />
                  <div className="mt-4 flex justify-end">
                    <Button
                      type="button"
                      onClick={onSubmit}
                      disabled={!canSubmit}
                      className="inline-flex items-center gap-2 rounded-full bg-orange-500 text-white hover:bg-orange-400"
                    >
                      {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                      {isSubmitting ? "Evaluating..." : "Submit"}
                    </Button>
                  </div>
                </div>
              )}

              {challengeType === "mcq" && error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertCircle className="h-4 w-4" />
                    Could not complete assessment
                  </div>
                  <p className="mt-2 text-rose-700/90">{error}</p>
                </div>
              )}

              {challengeType === "mcq" && evaluation && (
                <div className="rounded-[28px] border border-slate-200/70 bg-white/95 p-5 shadow-[0_25px_60px_-45px_rgba(15,23,42,0.35)]">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Evaluation</p>
                      <h3 className="mt-2 text-lg font-semibold text-slate-900">Result summary</h3>
                    </div>
                    <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white">
                      {evaluation.passed ? "Passed" : "Review"}
                    </span>
                  </div>
                  <div className="mt-4 text-sm text-slate-700">
                    <p>
                      Score: <span className="font-semibold">{evaluation.score ?? "N/A"}</span>/100
                    </p>
                    <p className="mt-1">Status: {evaluation.passed ? "Passed" : "Needs improvement"}</p>
                    <p className="mt-3 leading-6">{evaluation.feedback || "No feedback returned."}</p>
                  </div>

                  {Array.isArray(evaluation.testCaseResults) && evaluation.testCaseResults.length > 0 && (
                    <div className="mt-4 space-y-2">
                      <h4 className="text-sm font-semibold text-slate-900">Detailed results</h4>
                      {evaluation.testCaseResults.map((item: any, index: number) => {
                        const passed = Boolean(item?.passed || item?.isCorrect);
                        return (
                          <div
                            key={String(item?.id || item?.questionId || index)}
                            className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm ${
                              passed ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"
                            }`}
                          >
                            {passed ? (
                              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                            ) : (
                              <CircleDot className="h-4 w-4 text-rose-600" />
                            )}
                            <span className="text-slate-700">
                              {item?.questionId ? `Question ${index + 1}` : `Case ${index + 1}`}: {passed ? "Pass" : "Fail"}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {evaluation.breakdown && (
                    <pre className="code-font mt-4 overflow-auto rounded-2xl bg-slate-900 p-3 text-xs text-slate-100">
{JSON.stringify(evaluation.breakdown, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewCodingPage;
