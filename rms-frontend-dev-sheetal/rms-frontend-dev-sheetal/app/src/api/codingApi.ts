import type { AxiosError } from "axios";

import axiosInstance from "./axiosConfig";
import type { ApiResult } from "./jobApi";


export interface CodingQuestion {
  challengeType?: "coding" | "mcq";
  source: "ai" | "provided";
  title: string;
  problem?: string;
  difficulty: string;
  languages?: string[];
  constraints?: string[];
  hints?: string[];
  testCaseMode?: string;
  testCases?: Array<Record<string, any>>;
  starterCode?: Record<string, string>;
  questions?: Array<Record<string, any>>;
  passingScore?: number;
  instructions?: string;
  questionMode?: string;
  roundListId?: string;
  jobId?: string;
}

export interface McqAnswerItem {
  questionId: string;
  selectedOptionId: string;
}

export interface CodingSubmitPayload {
  token: string;
  email: string;
  challengeType?: "coding" | "mcq";
  language?: string;
  code?: string;
  mcqAnswers?: McqAnswerItem[];
  question?: Record<string, any>;
}

export interface CodingSubmissionResult {
  submissionId: string;
  challengeType?: "coding" | "mcq";
  score: number | null;
  feedback: string | null;
  breakdown?: Record<string, any>;
  testCaseResults?: Array<Record<string, any>>;
  passed?: boolean;
  maxScore?: number;
  evaluationSource?: string;
  language: string;
  status: string;
  question?: Record<string, any>;
  createdAt?: string;
}


const extractApiErrorMessage = (err: unknown): string => {
  if (!err) return "An unknown error occurred";
  const maybeAxios = err as AxiosError<any>;
  if (maybeAxios.response) {
    const data = maybeAxios.response.data;
    if (typeof data === "string") return data;
    if (data?.message) return String(data.message);
    if (data?.detail) return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    try {
      return JSON.stringify(data);
    } catch {
      return `Request failed with status ${maybeAxios.response.status}`;
    }
  }
  return maybeAxios.message || String(err);
};


export const getCodingQuestion = async (token: string, email: string): Promise<ApiResult<CodingQuestion>> => {
  try {
    const resp = await axiosInstance.get("/coding/question", { params: { token, email } });
    const payload = resp.data?.data ?? resp.data;
    return { success: true, data: payload, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};


export const submitCodingSolution = async (
  payload: CodingSubmitPayload
): Promise<ApiResult<CodingSubmissionResult>> => {
  try {
    const resp = await axiosInstance.post("/coding/submit", payload);
    const data = resp.data?.data ?? resp.data;
    return { success: true, data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};


export const getCodingSubmission = async (
  submissionId: string,
  token: string,
  email: string
): Promise<ApiResult<CodingSubmissionResult>> => {
  try {
    const resp = await axiosInstance.get(`/coding/submission/${submissionId}`, {
      params: { token, email },
    });
    const data = resp.data?.data ?? resp.data;
    return { success: true, data, status: resp.status };
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};
