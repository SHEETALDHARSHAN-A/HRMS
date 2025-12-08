// src/api/configApi.ts

import axiosInstance from './axiosConfig';

import type {
  EmailTemplateResponseData,
  EmailTemplatePreviewRequest,
  EmailTemplatePreviewResponseData,
  EmailTemplateUpdateRequest,
} from '../types/config';

const API_BASE_URL = '/config/email';

// --- API Service for Configuration ---

// 1. GET: Fetch the current (saved or default) template on load
export async function getTemplate(templateKey: string): Promise<EmailTemplateResponseData> {
  const response = await axiosInstance.get(`${API_BASE_URL}/template/${templateKey}`);
  // Assuming successful API response structure is handled by a standard wrapper
  // and the actual data is at response.data.data
  return response.data.data;
}

// 2. POST: Render the template for preview
export async function previewTemplate(
  data: EmailTemplatePreviewRequest
): Promise<EmailTemplatePreviewResponseData | null> {
  try {
    const response = await axiosInstance.post(`${API_BASE_URL}/preview`, data);
    // This will return the data object on success
    return response.data.data;
  } catch (error) {
    // If the backend returned a structured error message, forward it so the UI
    // can display a helpful message. Axios error may include response.data.message
    try {
      const resp = (error as any).response;
      if (resp && resp.data && resp.data.message) {
        return { __error: resp.data.message } as any;
      }
    } catch (e) {
      // ignore
    }
    console.error('Error in previewTemplate API call:', error);
    return null;
  }
}

// 3. POST: Save the client's edited template as the new default
export async function updateTemplate(
  data: EmailTemplateUpdateRequest
): Promise<void> {
  await axiosInstance.post(`${API_BASE_URL}/template`, data);
}

// 4. POST: Reset a template to the server-side default
export async function resetTemplate(templateKey: string): Promise<void> {
  await axiosInstance.post(`${API_BASE_URL}/template/${templateKey}/reset`);
}