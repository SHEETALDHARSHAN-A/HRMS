import type { AxiosError } from "axios";

import axiosInstance from "./axiosConfig";
import type { ApiResult } from "./jobApi";


export interface CodingQuestion {
  challengeType?: "coding" | "mcq";
  source: "ai" | "provided";
  title: string;
  problem?: string;
  detailedPrompt?: string;
  inputFormat?: string;
  outputFormat?: string;
  examples?: Array<Record<string, any>>;
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

export interface CodingRunResult {
  challengeType?: "coding" | "mcq";
  score: number | null;
  summary?: string;
  feedback?: string | null;
  breakdown?: Record<string, any>;
  testCaseResults?: Array<Record<string, any>>;
  evaluationSource?: string;
  passed?: boolean;
  maxScore?: number;
  language?: string;
  strengths?: string[];
  improvements?: string[];
  question?: Record<string, any>;
  securityValidation?: Record<string, any>;
  saved?: boolean;
}

interface StandardApiEnvelope<T> {
  success?: boolean;
  status_code?: number;
  message?: string;
  data?: T;
  errors?: string[];
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

const getEnvelopeErrorMessage = (payload: StandardApiEnvelope<unknown>): string => {
  if (typeof payload?.message === "string" && payload.message.trim()) {
    return payload.message;
  }
  if (Array.isArray(payload?.errors) && payload.errors.length > 0) {
    return String(payload.errors[0]);
  }
  return "Request failed";
};

const unwrapStandardResponse = <T>(raw: any, httpStatus: number): ApiResult<T> => {
  if (raw && typeof raw === "object" && ("success" in raw || "status_code" in raw || "errors" in raw)) {
    const payload = raw as StandardApiEnvelope<T>;
    const status = Number(payload.status_code) || httpStatus;

    if (payload.success === false) {
      return {
        success: false,
        error: getEnvelopeErrorMessage(payload),
        status,
      };
    }

    return {
      success: true,
      data: payload.data as T,
      status,
    };
  }

  return {
    success: true,
    data: (raw?.data ?? raw) as T,
    status: httpStatus,
  };
};


export const getCodingQuestion = async (token: string, email: string): Promise<ApiResult<CodingQuestion>> => {
  try {
    const resp = await axiosInstance.get("/coding/question", { params: { token, email } });
    return unwrapStandardResponse<CodingQuestion>(resp.data, resp.status);
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
    return unwrapStandardResponse<CodingSubmissionResult>(resp.data, resp.status);
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};


export const runCodingSolution = async (
  payload: CodingSubmitPayload
): Promise<ApiResult<CodingRunResult>> => {
  try {
    const resp = await axiosInstance.post("/coding/run", payload);
    return unwrapStandardResponse<CodingRunResult>(resp.data, resp.status);
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
    return unwrapStandardResponse<CodingSubmissionResult>(resp.data, resp.status);
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};


export const getLatestCodingSubmission = async (
  token: string,
  email: string
): Promise<ApiResult<CodingSubmissionResult>> => {
  try {
    const resp = await axiosInstance.get("/coding/submission/latest", {
      params: { token, email },
    });
    return unwrapStandardResponse<CodingSubmissionResult>(resp.data, resp.status);
  } catch (err: unknown) {
    const maybe = err as AxiosError;
    return { success: false, error: extractApiErrorMessage(err), status: maybe?.response?.status };
  }
};
