import type { User } from './auth';

// Matches ats-dev-sheetal/app/schemas/standard\_response.py
export interface StandardResponse<T = any> {
  success: boolean;
  status_code: number;
  message: string;
  data?: T;
  errors?: string[];
}


// Re-export User for convenience
export type { User };