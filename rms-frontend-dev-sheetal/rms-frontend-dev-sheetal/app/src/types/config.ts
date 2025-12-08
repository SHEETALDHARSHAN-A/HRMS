// src/types/config.ts

import type { StandardResponse } from './api'; // Assuming you have a standard API response wrapper

// --- 1. GET /config/email/template/{key} (Load the raw template) ---
export interface EmailTemplateResponseData {
  template_key: string;
  subject_template: string; // The raw string with {{PLACEHOLDERS}}
  body_template_html: string; // The raw HTML with {{PLACEHOLDERS}}
}
export type GetEmailTemplateResponse = StandardResponse<EmailTemplateResponseData>;


// --- 2. POST /config/email/preview (Request to render a preview) ---
export interface EmailTemplatePreviewRequest {
  template_subject: string;
  template_body: string;
  // This dictionary must contain sample values for ALL placeholders (e.g., ROOM_CODE, JOIN_URL)
  sample_context: Record<string, string | number>; 
}

// --- 3. POST /config/email/preview (Response containing rendered HTML) ---
export interface EmailTemplatePreviewResponseData {
  rendered_subject: string;
  rendered_html_body: string; // The final HTML, ready to display in an iframe
}
export type PostEmailPreviewResponse = StandardResponse<EmailTemplatePreviewResponseData>;


// --- 4. POST /config/email/template (Save/Update the template) ---
export interface EmailTemplateUpdateRequest {
  template_key: string;
  subject_template: string; // Raw, edited template with {{PLACEHOLDERS}}
  body_template_html: string; // Raw, edited template with {{PLACEHOLDERS}}
}
export type PostEmailUpdateResponse = StandardResponse<null>;