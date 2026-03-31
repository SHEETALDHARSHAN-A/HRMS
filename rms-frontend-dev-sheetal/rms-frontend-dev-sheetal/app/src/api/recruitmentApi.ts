// // src/api/recruitmentApi.ts
// import type { StandardResponse } from '../types/api';
// import axiosInstance from './axiosConfig'; 
// import type { AxiosError } from 'axios'; 

// // --- Data Structures (Updated SkillExplanation type from user's model) ---
// export interface RoundOverview {
//     job_id: string;
//     job_title: string;
//     round_id: string;
//     round_name: string;
//     round_order: number;
//     total_candidates: number;
//     shortlisted: number;
//     under_review: number;
//     rejected: number;
// }

// export interface ScoreBreakdown {
//     "Location fit": number;
//     "Potential fit": number;
//     "Role fit": number;
//     "Skill score": number;
// }

// export interface SkillExplanation {
//     evidence: string;
//     score: number; // Corrected: Mapped from backend's score_100
//     explanation: string;
// }

// export interface ExtractedResumeContent {
//     name: string;
//     email: string;
//     phone: string;
//     skills: string[];
//     summary: string;
//     location: string;
//     education: any[];
//     experience: any[];
//     certifications: string[];
// }

// export interface Candidate {
//     profile_id: string;
//     candidate_name: string;
//     experience_level: string;
//     candidate_email: string;
//     overall_score: number;
//     result: "shortlist" | "under_review" | "rejected";
//     round_name: string;
//     round_id: string;
//     round_status: "shortlisted" | "under_review" | "rejected";
//     reason: string | null;
//     score_breakdown: ScoreBreakdown;
//     skill_explanation: Record<string, SkillExplanation>;
//     extracted_resume_content: ExtractedResumeContent;
// }

// export type CandidateStatus = "shortlisted" | "under_review" | "rejected";

// type RecruitmentApiResult<T> = Promise<{ success: boolean; data?: T; error?: string }>;


// /**
//  * 3. Update candidate status (shortlist/reject/under_review).
//  * PATCH /v1/shortlist/{round_id}/candidates/{profile_id}/status
//  * @param roundId UUID of the current Interview Round
//  * @param profileId UUID of the candidate's Profile
//  * @param newStatus The target status: 'shortlisted', 'rejected', or 'under_review'.
//  * @param reason The reason text for the status change. // NOW REQUIRED BY UI
//  */
// export const patchCandidateStatus = async (
//     roundId: string, 
//     profileId: string, 
//     newStatus: CandidateStatus,
//     reason: string // Reason is now passed to API
// ): RecruitmentApiResult<Candidate> => {
//     try {
//         // Construct the payload including reason
//         const payload: { round_status: CandidateStatus; reason: string } = { 
//             round_status: newStatus,
//             reason: reason // Reason is always sent
//         };

//         const response = await axiosInstance.patch<StandardResponse<Candidate>>(
//             `/shortlist/${roundId}/candidates/${profileId}/status`, 
//             payload,
//         );
        
//         if (response.data.success && response.data.data) {
//             return { success: true, data: response.data.data };
//         }
//         return { success: false, error: response.data.message || 'Failed to update candidate status.' };
//     } catch (error) {
//         return { success: false, error: extractError(error) };
//     }
// };

// export interface JobWithRounds {
//     job_id: string;
//     job_title: string;
//     rounds: RoundOverview[];
//     total_applied: number; 
// }


// // Helper to handle Axios errors and return a standardized message
// const extractError = (error: unknown): string => {
//     const maybeAxios = error as AxiosError<any>;
//     const message = maybeAxios.response?.data?.message || maybeAxios.message;
//     return message || 'An unknown network error occurred.';
// };


// /** Fetches the overview of all jobs and their candidates per round. (GET /shortlist/overview) */
// export const getJobRoundOverview = async (): RecruitmentApiResult<{ job_round_overview: RoundOverview[] }> => {
//     type OverviewResponse = StandardResponse<{ job_round_overview: RoundOverview[] }>;
//     try {
//         const response = await axiosInstance.get<OverviewResponse>('/shortlist/overview');
        
//         if (response.data.success && response.data.data) {
//             return { success: true, data: response.data.data };
//         }
//         return { success: false, error: response.data.message || 'Failed to fetch job round overview.' };
//     } catch (error) {
//         return { success: false, error: extractError(error) };
//     }
// };

// /** Fetches the detailed list of candidates for a specific job and round. (GET /shortlist/{job_id}/rounds/{round_id}/candidates) */
// export const getCandidatesForRound = async (jobId: string, roundId: string): RecruitmentApiResult<Candidate[]> => {
//     type CandidateResponse = StandardResponse<{ candidates: Candidate[] }>;
//     try {
//         const response = await axiosInstance.get<CandidateResponse>(`/shortlist/${jobId}/rounds/${roundId}/candidates`);
        
//         if (response.data.success && response.data.data) {
            
//             // --- DATA TRANSFORMATION ---
//             // The API response uses a field like `score_100`, but the local interface uses `score`. 
//             // We must map the data to the expected local interface before returning it.
//             const candidates = (response.data.data.candidates || []).map(candidate => {
//                 const transformedSkills: Record<string, SkillExplanation> = {};
                
//                 // Map score_100 (or similar) to the simpler 'score' field
//                 for (const [skillName, expl] of Object.entries(candidate.skill_explanation)) {
//                     transformedSkills[skillName] = {
//                         evidence: expl.evidence,
//                         explanation: expl.explanation,
//                         // Assumes backend uses score_100 or a similar numeric field
//                         score: (expl as any).score_100 || (expl as any).score || 0,
//                     };
//                 }

//                 return {
//                     ...candidate,
//                     skill_explanation: transformedSkills
//                 };
//             });
            
//             return { success: true, data: candidates };
//         }
//         return { success: false, error: response.data.message || 'Failed to fetch candidates.' };
//     } catch (error) {
//         return { success: false, error: extractError(error) };
//     }
// };



// src/api/recruitmentApi.ts
import type { StandardResponse } from '../types/api';
import axiosInstance from './axiosConfig'; 
import type { AxiosError } from 'axios'; 

// --- Data Structures (Updated SkillExplanation type from user's model) ---
export interface RoundOverview {
    job_id: string;
    job_title: string;
    round_id: string;
    round_name: string;
    round_order: number;
    total_candidates: number;
    shortlisted: number;
    under_review: number;
    rejected: number;
}

export interface ScoreBreakdown {
    "Location fit": number;
    "Potential fit": number;
    "Role fit": number;
    "Skill score": number;
}

export interface SkillExplanation {
    evidence: string;
    score: number; // Corrected: Mapped from backend's score_100
    explanation: string;
}

export interface ExtractedResumeContent {
    name: string;
    email: string;
    phone: string;
    skills: string[];
    summary: string;
    location: string;
    education: any[];
    experience: any[];
    certifications: string[];
}

export interface Candidate {
    profile_id: string;
    candidate_name: string;
    experience_level: string;
    candidate_email: string;
    overall_score: number;
    result: "shortlist" | "under_review" | "rejected";
    round_name: string;
    round_id: string;
    round_status: CandidateStatus | "interview_scheduled";
    reason: string | null;
    score_breakdown: ScoreBreakdown;
    skill_explanation: Record<string, SkillExplanation>;
    extracted_resume_content: ExtractedResumeContent;
}

export type CandidateStatus = "shortlisted" | "under_review" | "rejected";

// --- NEW Data Structures for Scheduling ---
export type InterviewLevel = 'Easy' | 'Medium' | 'Hard';
export type InterviewType = 'Agent_interview' | 'In_person';

export interface ScheduledInterview {
    profile_id: string;
    job_id: string;
    round_id: string;
    candidate_name: string;
    candidate_email: string;
    job_title: string;
    round_name: string;
    scheduled_datetime: string;
    status: string;
    interview_token: string;
    interview_type: string;
    level_of_interview: string | null;
}

export interface ScheduleInterviewData {
    job_id: string;
    profile_id: string[];
    round_id: string;
    interview_date: string;
    interview_time: string;
    interviewer_id?: string;
    interview_type: InterviewType;
    level_of_interview: string;
    email_subject?: string;
    email_body?: string;
}

export interface RescheduleInterviewData {
    interview_token?: string;
    job_id?: string;
    profile_id?: string;
    round_id?: string;
    interview_date: string;
    interview_time: string;
    reason?: string;
    email_subject?: string;
    email_body?: string;
}

type RecruitmentApiResult<T> = Promise<{ success: boolean; data?: T; error?: string }>;


/**
 * 3. Update candidate status (shortlist/reject/under_review).
 * PATCH /v1/shortlist/{round_id}/candidates/{profile_id}/status
 * @param roundId UUID of the current Interview Round
 * @param profileId UUID of the candidate's Profile
 * @param newStatus The target status: 'shortlisted', 'rejected', or 'under_review'.
 * @param reason The reason text for the status change. // NOW REQUIRED BY UI
 */
export const patchCandidateStatus = async (
    roundId: string, 
    profileId: string, 
    newStatus: CandidateStatus,
    reason: string // Reason is always sent
): RecruitmentApiResult<Candidate> => {
    
    const backendStatus = newStatus === 'shortlisted' ? 'shortlist' : (newStatus === 'rejected' ? 'reject' : 'under_review');
    try {
        // Construct the payload including reason
        const payload: { new_result: string; reason: string } = {
            new_result: backendStatus,
            reason: reason // Reason is always sent
        };
        console.log(`[API HOOK] Attempting PATCH status for Profile ID: ${profileId} in Round ID: ${roundId}. New Status: ${newStatus}, Payload:`, payload);
        const response = await axiosInstance.patch<StandardResponse<Candidate>>(
            `/shortlist/rounds/${roundId}/candidates/${profileId}/status`, 
            payload,
        );
        
        if (response.data.success && response.data.data) {
            console.log(`[API HOOK] SUCCESS: Status updated successfully for ${profileId}.`);
            return { success: true, data: response.data.data };
        }
        // Logging the failure reason returned by the server
        const serverError = response.data.message || 'Failed to update candidate status.';
        console.warn(`[API HOOK] FAILURE: API rejected status update for ${profileId}. Message: ${serverError}`);
        return { success: false, error: serverError };
    } catch (error) {
        // ...
        return { success: false, error: extractError(error) };
    }
};

/**
 * 4. Schedules interviews for a list of candidates.
 * POST /v1/scheduling/schedule-interview
 */
export const scheduleInterview = async (data: ScheduleInterviewData): RecruitmentApiResult<any> => {
    try {
        // Endpoint: POST /v1/scheduling/schedule-interview
        const response = await axiosInstance.post<StandardResponse<any>>('/scheduling/schedule-interview', data);
        
        if (response.data.success) {
            return { success: true, data: response.data.data };
        }
        return { success: false, error: response.data.message || 'Failed to schedule interviews.' };
    } catch (error) {
        return { success: false, error: extractError(error) };
    }
};

/**
 * 5. Fetch scheduled interviews for a round.
 * GET /v1/scheduling/scheduled-interviews
 */
export const getScheduledInterviews = async (
    jobId: string,
    roundId: string
): RecruitmentApiResult<ScheduledInterview[]> => {
    try {
        const response = await axiosInstance.get<StandardResponse<{ interviews: ScheduledInterview[] }>>(
            '/scheduling/scheduled-interviews',
            { params: { job_id: jobId, round_id: roundId } }
        );

        if (response.data.success && response.data.data) {
            return { success: true, data: response.data.data.interviews || [] };
        }
        return { success: false, error: response.data.message || 'Failed to load scheduled interviews.' };
    } catch (error) {
        return { success: false, error: extractError(error) };
    }
};

/**
 * 6. Reschedule a scheduled interview.
 * POST /v1/scheduling/reschedule-interview
 */
export const rescheduleInterview = async (data: RescheduleInterviewData): RecruitmentApiResult<any> => {
    try {
        const response = await axiosInstance.post<StandardResponse<any>>('/scheduling/reschedule-interview', data);

        if (response.data.success) {
            return { success: true, data: response.data.data };
        }
        return { success: false, error: response.data.message || 'Failed to reschedule interview.' };
    } catch (error) {
        return { success: false, error: extractError(error) };
    }
};


export interface JobWithRounds {
    job_id: string;
    job_title: string;
    rounds: RoundOverview[];
    total_applied: number; 
}


// Helper to handle Axios errors and return a standardized message
const extractError = (error: unknown): string => {
    const maybeAxios = error as AxiosError<any>;
    const message = maybeAxios.response?.data?.message || maybeAxios.message;
    return message || 'An unknown network error occurred.';
};


/** Fetches the overview of all jobs and their candidates per round. (GET /shortlist/overview) */
export const getJobRoundOverview = async (): RecruitmentApiResult<{ job_round_overview: RoundOverview[] }> => {
    type OverviewResponse = StandardResponse<{ job_round_overview: RoundOverview[] }>;
    try {
        const response = await axiosInstance.get<OverviewResponse>('/shortlist/overview');
        
        if (response.data.success && response.data.data) {
            return { success: true, data: response.data.data };
        }
        return { success: false, error: response.data.message || 'Failed to fetch job round overview.' };
    } catch (error) {
        return { success: false, error: extractError(error) };
    }
};

/** Fetches the detailed list of candidates for a specific job and round. (GET /shortlist/{job_id}/rounds/{round_id}/candidates) */
export const getCandidatesForRound = async (jobId: string, roundId: string): RecruitmentApiResult<Candidate[]> => {
    type CandidateResponse = StandardResponse<{ candidates: Candidate[] }>;
    try {
        const response = await axiosInstance.get<CandidateResponse>(`/shortlist/${jobId}/rounds/${roundId}/candidates`);
        
        if (response.data.success && response.data.data) {
            
            // --- DATA TRANSFORMATION ---
            // The API response uses a field like `score_100`, but the local interface uses `score`. 
            // We must map the data to the expected local interface before returning it.
            const candidates = (response.data.data.candidates || []).map(candidate => {
                const transformedSkills: Record<string, SkillExplanation> = {};
                
                // Map score_100 (or similar) to the simpler 'score' field
                for (const [skillName, expl] of Object.entries(candidate.skill_explanation)) {
                    transformedSkills[skillName] = {
                        evidence: expl.evidence,
                        explanation: expl.explanation,
                        // Assumes backend uses score_100 or a similar numeric field
                        score: (expl as any).score_100 || (expl as any).score || 0,
                    };
                }

                return {
                    ...candidate,
                    skill_explanation: transformedSkills
                };
            });
            
            return { success: true, data: candidates };
        }
        return { success: false, error: response.data.message || 'Failed to fetch candidates.' };
    } catch (error) {
        return { success: false, error: extractError(error) };
    }
};