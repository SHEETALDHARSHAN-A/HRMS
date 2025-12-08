// src/types/career.ts
export interface Job {
    job_id: string;
    job_title: string;
    job_description: string;
    min_experience: number;
    max_experience: number;
    job_location: string;
    work_from_home: boolean;
    posted_date: string;
    skills_required: string[];
  }
  
  export interface ApplicationFormData {
    firstName: string;
    lastName: string;
    email: string;
    phoneNumber: string;
    linkedinUrl: string;
    resume: File | null;
  }
  
  export interface ApplicationFormErrors {
    firstName?: string;
    lastName?: string;
    email?: string;
    phoneNumber?: string;
    resume?: string;
    submit?: string;
  }
  