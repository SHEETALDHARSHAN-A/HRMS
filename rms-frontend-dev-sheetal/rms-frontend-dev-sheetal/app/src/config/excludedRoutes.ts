// Central list of frontend-excluded public routes.
// Keep this in sync with backend `protected_routes_config.EXCLUDED_ROUTES`.

export const EXCLUDED_PATHS: string[] = [
  // Auth/public helpers
  '/auth',
  '/auth/',
  '/auth/complete-admin-setup',
  '/auth/complete-name-update',
  '/auth/verify-otp',
  '/auth/verify-email-update',
  '/auth/email-update-success',

  // Interview public endpoints
  '/interview/join',
  '/interview/thank-you',
  '/interview/coding',
  '/interview/validate-token',
  '/interview/verify-otp',
  '/coding/question',
  '/coding/run',
  '/coding/submit',
  '/coding/submission/latest',
  '/coding/submission/',

  // Public job/career endpoints
  '/job-post/active',
  '/job-post/public/job/',
  '/job-post/public/search-suggestions',
  '/job-post/public/search',
  '/career/apply/send-otp',
  '/career/apply/verify-and-submit',
  '/resume/upload-resumes/',
  '/v1/auth/check-email-status',

  // Full /api/v1 prefixed variants
  '/api/v1/auth/verify-otp',
  '/api/v1/auth/check-email-status',
  '/api/v1/coding/question',
  '/api/v1/coding/run',
  '/api/v1/coding/submit',
  '/api/v1/coding/submission/latest',
  '/api/v1/coding/submission/',
  '/api/v1/interview/validate-token',
  '/api/v1/interview/verify-otp',
  '/api/v1/job-post/active',
  '/api/v1/job-post/public/job/',
  '/api/v1/job-post/public/search-suggestions',
  '/api/v1/job-post/public/search',
  '/api/v1/career/apply/send-otp',
  '/api/v1/career/apply/verify-and-submit',
  '/api/v1/resume/upload-resumes/',
];

export default EXCLUDED_PATHS;
