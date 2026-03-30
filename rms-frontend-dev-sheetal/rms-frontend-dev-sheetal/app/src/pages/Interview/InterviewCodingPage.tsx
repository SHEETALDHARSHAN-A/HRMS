import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Editor from "@monaco-editor/react";
import {
  AlertCircle,
  CheckCircle2,
  CircleDot,
  Code2,
  ListChecks,
  Loader2,
  Send,
  Sparkles,
  TerminalSquare,
} from "lucide-react";

import {
  getCodingQuestion,
  submitCodingSolution,
  type CodingQuestion,
  type CodingSubmissionResult,
  type McqAnswerItem,
} from "../../api/codingApi";
import { Alert, AlertDescription, AlertTitle } from "../../components/ui/alert";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Label } from "../../components/ui/label";
import { Progress } from "../../components/ui/progress";
import { RadioGroup, RadioGroupItem } from "../../components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";


type ChallengeType = "coding" | "mcq";


const editorShell =
  "rounded-xl border border-gray-300 bg-white shadow-sm focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500";


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


const InterviewCodingPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const email = searchParams.get("email") || "";

  const [isLoadingQuestion, setIsLoadingQuestion] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [question, setQuestion] = useState<CodingQuestion | null>(null);
  const [challengeType, setChallengeType] = useState<ChallengeType>("coding");
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(fallbackCodeByLanguage.python);
  const [hasCustomCode, setHasCustomCode] = useState(false);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, string>>({});
  const [evaluation, setEvaluation] = useState<CodingSubmissionResult | null>(null);

  const mcqQuestions = useMemo(() => normalizeMcqQuestions(question?.questions), [question?.questions]);

  const mcqAllAnswered = useMemo(() => {
    if (mcqQuestions.length === 0) return false;
    return mcqQuestions.every((q) => Boolean(mcqAnswers[q.id]));
  }, [mcqQuestions, mcqAnswers]);

  const canSubmit = useMemo(() => {
    if (!token || !email || isSubmitting) return false;
    if (challengeType === "mcq") return mcqAllAnswered;
    return code.trim().length > 0;
  }, [token, email, isSubmitting, challengeType, mcqAllAnswered, code]);

  useEffect(() => {
    const loadQuestion = async () => {
      if (!token || !email) {
        setError("Missing interview token or email. Open this page from the interview room.");
        setIsLoadingQuestion(false);
        return;
      }

      setIsLoadingQuestion(true);
      setError("");
      setEvaluation(null);

      const result = await getCodingQuestion(token, email);
      if (!result.success) {
        setError(result.error);
        setIsLoadingQuestion(false);
        return;
      }

      const payload = result.data;
      const type = (payload.challengeType || "coding") as ChallengeType;
      setQuestion(payload);
      setChallengeType(type === "mcq" ? "mcq" : "coding");

      const firstLanguage = payload?.languages?.[0] || "python";
      setLanguage(firstLanguage);

      const starter = payload?.starterCode?.[firstLanguage] || fallbackCodeByLanguage[firstLanguage] || fallbackCodeByLanguage.python;
      setCode(starter);
      setHasCustomCode(false);
      setMcqAnswers({});
      setIsLoadingQuestion(false);
    };

    void loadQuestion();
  }, [token, email]);

  const onChangeLanguage = (nextLanguage: string) => {
    setLanguage(nextLanguage);
    if (!hasCustomCode) {
      const starter =
        question?.starterCode?.[nextLanguage] ||
        fallbackCodeByLanguage[nextLanguage] ||
        fallbackCodeByLanguage.python;
      setCode(starter);
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
    setIsSubmitting(false);
  };

  const testCases = Array.isArray(question?.testCases) ? question?.testCases : [];
  const mcqAnsweredCount = Object.keys(mcqAnswers).length;
  const mcqProgress = mcqQuestions.length > 0 ? Math.round((mcqAnsweredCount / mcqQuestions.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-100 px-4 py-6 sm:px-6 lg:px-10">
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <div className="relative overflow-hidden rounded-xl">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.22),_transparent_62%),radial-gradient(ellipse_at_bottom_left,_rgba(16,185,129,0.14),_transparent_52%)]" />
          <Card className="relative border-slate-200/80 bg-white/95 shadow-[0_20px_50px_-36px_rgba(37,99,235,0.35)]">
            <CardHeader className="p-6">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-blue-100 p-2 text-blue-600">
                  <Code2 className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-2xl font-semibold text-gray-900">Assessment Workspace</CardTitle>
                  <CardDescription className="text-sm text-gray-600">
                    {challengeType === "mcq"
                      ? "Complete the MCQ challenge and submit for objective scoring."
                      : "Solve the coding challenge and submit for AI plus test-case evaluation."}
                  </CardDescription>
                </div>
                <Badge className="ml-auto" variant="secondary">
                  {challengeType === "mcq" ? "MCQ" : "CODING"}
                </Badge>
              </div>
            </CardHeader>
          </Card>
        </div>

        {isLoadingQuestion ? (
          <Card>
            <CardContent className="p-10">
              <div className="flex items-center justify-center gap-3 text-gray-700">
                <Loader2 className="h-6 w-6 animate-spin" />
                Loading assessment question...
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <Card className="lg:col-span-2">
              <CardHeader className="p-6 pb-3">
                <div className="flex items-center gap-2 text-sm font-medium text-blue-600">
                  <Sparkles className="h-4 w-4" />
                  Challenge
                </div>
                <CardTitle className="mt-2 text-xl font-semibold text-gray-900">{question?.title || "Assessment"}</CardTitle>
                <CardDescription className="mt-1 text-sm text-gray-500">
                  Difficulty: <span className="font-medium capitalize text-gray-700">{question?.difficulty || "medium"}</span>
                </CardDescription>
              </CardHeader>

              <CardContent className="p-6 pt-2">
                {challengeType === "coding" ? (
                  <>
                    <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-700">
                      {question?.problem || "No coding question available."}
                    </div>

                    {Array.isArray(question?.constraints) && question.constraints.length > 0 && (
                      <div className="mt-5">
                        <h3 className="text-sm font-semibold text-gray-900">Constraints</h3>
                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
                          {question.constraints.map((item: string, idx: number) => (
                            <li key={`${item}-${idx}`}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {Array.isArray(question?.hints) && question.hints.length > 0 && (
                      <div className="mt-5">
                        <h3 className="text-sm font-semibold text-gray-900">Hints</h3>
                        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
                          {question.hints.map((item: string, idx: number) => (
                            <li key={`${item}-${idx}`}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {testCases.length > 0 && (
                      <div className="mt-5">
                        <h3 className="text-sm font-semibold text-gray-900">Configured Test Cases</h3>
                        <div className="mt-2 space-y-2">
                          {testCases.map((testCase: any, index: number) => (
                            <div key={String(testCase?.id || index)} className="rounded-lg border border-gray-200 bg-gray-50 p-2 text-xs">
                              <p className="font-semibold text-gray-700">
                                Case {index + 1} {testCase?.isHidden ? "(hidden)" : "(visible)"}
                              </p>
                              <p className="mt-1 text-gray-600">Input: {String(testCase?.input || "")}</p>
                              {testCase?.expectedOutput && <p className="text-gray-600">Expected: {String(testCase.expectedOutput)}</p>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <p className="mt-2 text-sm text-gray-700">{question?.instructions || "Choose one option for each question."}</p>
                    <p className="mt-2 text-xs text-gray-500">
                      Passing score: <span className="font-semibold">{question?.passingScore ?? 60}%</span>
                    </p>
                    <div className="mt-4 space-y-4">
                      {mcqQuestions.map((q, index) => (
                        <div key={q.id} className="rounded-xl border border-gray-200 p-3">
                          <p className="text-sm font-semibold text-gray-900">
                            {index + 1}. {q.question}
                          </p>
                          <RadioGroup
                            className="mt-2 space-y-2"
                            value={mcqAnswers[q.id] || ""}
                            onValueChange={(value) => onChooseMcqOption(q.id, value)}
                          >
                            {q.options.map((opt: any) => {
                              const inputId = `option-${q.id}-${opt.id}`;
                              return (
                                <div
                                  key={opt.id}
                                  className="flex items-start gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50"
                                >
                                  <RadioGroupItem id={inputId} value={opt.id} className="mt-0.5" />
                                  <Label htmlFor={inputId} className="cursor-pointer text-sm font-normal text-gray-700">
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
              </CardContent>
            </Card>

            <section className="lg:col-span-3 space-y-4">
              {challengeType === "coding" ? (
                <Card>
                  <CardContent className="p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                        <TerminalSquare className="h-4 w-4 text-blue-600" />
                        Internal Code Editor
                      </div>

                      <div className="flex items-center gap-2">
                        <Label htmlFor="language-select" className="text-sm text-gray-600">
                          Language
                        </Label>
                        <Select value={language} onValueChange={onChangeLanguage}>
                          <SelectTrigger id="language-select" className="w-[180px]">
                            <SelectValue placeholder="Select language" />
                          </SelectTrigger>
                          <SelectContent>
                            {(question?.languages || ["python", "javascript"]).map((lang: string) => (
                              <SelectItem key={lang} value={lang}>
                                {lang}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className={`mt-3 ${editorShell}`}>
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
                          fontSize: 14,
                          automaticLayout: true,
                          scrollBeyondLastLine: false,
                          wordWrap: "on",
                        }}
                        theme="vs-light"
                      />
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
                      <ListChecks className="h-4 w-4 text-blue-600" />
                      MCQ Progress
                    </div>
                    <p className="mt-2 text-sm text-gray-600">
                      {mcqAnsweredCount} / {mcqQuestions.length} answered
                    </p>
                    <Progress className="mt-3" value={mcqProgress} />
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardContent className="p-4">
                  <div className="flex justify-end">
                    <Button type="button" onClick={onSubmit} disabled={!canSubmit} className="inline-flex items-center gap-2">
                      {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                      {isSubmitting ? "Evaluating..." : "Submit Assessment"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Could not complete assessment</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {evaluation && (
                <Card>
                  <CardHeader className="p-5 pb-2">
                    <CardTitle className="text-lg font-semibold text-gray-900">Evaluation Result</CardTitle>
                  </CardHeader>
                  <CardContent className="p-5 pt-0">
                    <p className="mt-2 text-sm text-gray-700">
                      Score: <span className="font-semibold">{evaluation.score ?? "N/A"}</span>/100
                    </p>
                    <p className="mt-1 text-sm text-gray-700">
                      Status: {evaluation.passed ? "Passed" : "Needs improvement"}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-gray-700">{evaluation.feedback || "No feedback returned."}</p>

                    {Array.isArray(evaluation.testCaseResults) && evaluation.testCaseResults.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <h4 className="text-sm font-semibold text-gray-900">Detailed Results</h4>
                        {evaluation.testCaseResults.map((item: any, index: number) => {
                          const passed = Boolean(item?.passed || item?.isCorrect);
                          return (
                            <div
                              key={String(item?.id || item?.questionId || index)}
                              className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
                                passed ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50"
                              }`}
                            >
                              {passed ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                              ) : (
                                <CircleDot className="h-4 w-4 text-rose-600" />
                              )}
                              <span className="text-gray-700">
                                {item?.questionId ? `Question ${index + 1}` : `Case ${index + 1}`}: {passed ? "Pass" : "Fail"}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {evaluation.breakdown && (
                      <pre className="mt-4 overflow-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100">
{JSON.stringify(evaluation.breakdown, null, 2)}
                      </pre>
                    )}
                  </CardContent>
                </Card>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewCodingPage;
