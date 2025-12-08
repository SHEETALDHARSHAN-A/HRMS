// /rms-frontend-dev-gomathi/app/src/utils/validation.ts

import { z } from 'zod';

// Schema for one skill (matches SkillSchema)
const skillSchema = z.object({
  skill: z.string().min(1, "Skill name is required"),
  weightage: z.number().min(1, "Weight must be 1-10").max(10, "Weight must be 1-10"),
});

// Schema for one interview round (matches InterviewRoundSchema)
const interviewLevelSchema = z.object({
  level_name: z.string().min(1, "Level name is required"),
  description: z.string().optional(),
  round_order: z.number().min(1, "Round order must be at least 1"),
  shortlisting_threshold: z.number().min(0).max(100),
  rejected_threshold: z.number().min(0).max(100),
}).refine(data => data.shortlisting_threshold >= data.rejected_threshold, {
  message: "Shortlisting threshold must be >= rejecting threshold",
  path: ["shortlisting_threshold"],
});

// Schema for one description section (matches DescriptionSection)
const descriptionSectionSchema = z.object({
  title: z.string(),
  content: z.string().min(1, "Description content cannot be empty"),
});

// Main schema for the job post form (matches UpdateJdRequest + career fields)
export const jobPostSchema = z.object({
  job_id: z.string().uuid("Invalid Job ID format").optional(),
  job_title: z.string().min(3, "Job Title is required"),
  
  // --- FIX: Include BOTH fields ---
  job_description: z.string().min(1, "Job Description is required."),
  description_sections: z.array(descriptionSectionSchema)
    .min(1, "Job Description is required.")
    .refine(sections => sections.some(s => s.content.trim().length > 0), {
      message: "Job Description cannot be empty."
    }),
  // --- END FIX ---

  role_fit: z.number().min(0).max(100),
  potential_fit: z.number().min(0).max(100),
  location_fit: z.number().min(0).max(100),

  minimum_experience: z.number().min(0, "Min experience must be 0 or greater"),
  maximum_experience: z.number().min(0, "Max experience must be 0 or greater"),

  job_location: z.string().min(1, "Job Location is required"),
  work_from_home: z.boolean(),
  is_active: z.boolean(),
  work_mode: z.string().optional(),

  // --- FIX: Add career fields (matching the migration script) ---
  career_activation_mode: z.string(),
  career_activation_days: z.number(),
  career_shortlist_threshold: z.number(),
  // --- END FIX ---

  skills_required: z.array(skillSchema).min(1, "At least one skill is required"),
  
  interview_rounds: z.array(interviewLevelSchema).min(1, "At least one interview round is required"),
  
  // Per-round interview mode is used; job-level interview_type removed
  
  active_till: z.string().refine((val) => val && !isNaN(new Date(val).getTime()), {
    message: "Invalid expiration date",
  }),
  
  no_of_openings: z.number().min(1, "At least one opening is required"),

})
// Refinements at the object level
.refine(data => data.maximum_experience >= data.minimum_experience, {
  message: "Max experience must be >= min experience",
  path: ["maximum_experience"], 
})
.refine(data => (data.role_fit + data.potential_fit + data.location_fit) === 100, {
  message: "The sum of Role Fit, Potential Fit, and Location Fit must equal 100",
  path: ["score_total"], 
});