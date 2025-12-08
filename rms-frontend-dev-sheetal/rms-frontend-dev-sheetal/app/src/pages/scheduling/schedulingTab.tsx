// src/pages/Scheduling/SchedulingTab.tsx (Conceptual Component)

import React, { useState, useEffect, useCallback } from 'react';
import { getTemplate, previewTemplate, updateTemplate } from '../../api/configApi';
import { useToast } from '../../context/ToastContext';
import type { EmailTemplatePreviewRequest } from '../../types/config';



// ----------------------------------------------------
// Mock Data (In a real app, this comes from job/candidate data)
// ----------------------------------------------------
const TEMPLATE_KEY = 'interview_invite';
const SAMPLE_CONTEXT = {
  CANDIDATE_NAME: 'Jane Doe',
  JOIN_URL: 'https://demo.meet/room-test',
  ROOM_CODE: 'ABC12345',
  INTERVIEW_TIME: '15 Nov 2025 at 10:00 AM IST',
  JOB_TITLE: 'Senior Dev',
};

// ----------------------------------------------------
// Component State and Logic
// ----------------------------------------------------

interface TemplateState {
  subject: string;
  bodyHtml: string;
}

interface RenderedState {
  subject: string;
  bodyHtml: string;
}

const SchedulingTab: React.FC = () => {
  const { showToast } = useToast();
  const [template, setTemplate] = useState<TemplateState>({ subject: '', bodyHtml: '' });
  const [previewContent, setPreviewContent] = useState<RenderedState | null>(null);
  const [isTemplateLoading, setIsTemplateLoading] = useState(true);

  // --- 1. FETCH TEMPLATE ON LOAD (GET Endpoint) ---
  useEffect(() => {
    const fetchInitialTemplate = async () => {
      try {
        const data = await getTemplate(TEMPLATE_KEY);
        // The data fetched here is the RAW template with placeholders
        setTemplate({
          subject: data.subject_template,
          bodyHtml: data.body_template_html,
        });
      } catch (error) {
        showToast({ message: 'error', type: 'Failed to load email template configuration.' });
        
      } finally {
        setIsTemplateLoading(false);
      }
    };
    fetchInitialTemplate();
  }, []);

  // --- 2. PREVIEW LOGIC (POST /preview Endpoint) ---
  const handlePreview = useCallback(async () => {
    if (!template.subject || !template.bodyHtml) return;

    const previewRequest: EmailTemplatePreviewRequest = {
      template_subject: template.subject, // Current content from the input box
      template_body: template.bodyHtml,   // Current content from the input box
      sample_context: SAMPLE_CONTEXT,     // Mock data for replacement
    };

    try {
      const data = await previewTemplate(previewRequest);
      // The data returned is fully rendered HTML/Subject
      setPreviewContent({
        subject: data.rendered_subject,
        bodyHtml: data.rendered_html_body,
      });
    } catch (error) {
      showToast('error', 'Failed to generate email preview.');
    }
  }, [template, showToast]);


  // --- 3. FINAL SEND/UPDATE LOGIC (POST /template Endpoint) ---
  const handleFinalSchedule = async (schedulingDetails: any) => {
    // A. First, save the user's current edited template
    try {
      await updateTemplate({
        template_key: TEMPLATE_KEY,
        subject_template: template.subject, // Raw template content is saved
        body_template_html: template.bodyHtml, // Raw template content is saved
      });
      showToast('success', 'Email template saved successfully.');
    } catch (error) {
      // It's critical to continue scheduling even if saving the template fails
      showToast('warning', 'Failed to save template, sending email anyway...');
    }

    // B. Call the main scheduling API (assuming it accepts the custom content)
    try {
        const finalPayload = {
            ...schedulingDetails,
            // Pass the template content so the scheduling service knows which version to use
            custom_subject: template.subject, 
            custom_body: template.bodyHtml,
        };
        // await schedulingApi.scheduleInterview(finalPayload);
        showToast('success', 'Interviews scheduled and emails sent!');
    } catch (error) {
        showToast('error', 'Failed to schedule interviews.');
    }
  };

  if (isTemplateLoading) return <p>Loading email configuration...</p>;

  return (
    <div>
      <h2>Email Invitation Configuration</h2>
      <p>
        **Available Placeholders:** `{{CANDIDATE_NAME}}`, `{{JOIN_URL}}`, `{{ROOM_CODE}}`, etc.
      </p>

      {/* Subject Input */}
      <label>Email Subject:</label>
      <input
        type="text"
        value={template.subject}
        onChange={(e) => setTemplate({ ...template, subject: e.target.value })}
      />

      {/* Body Input (Use a rich text editor in a real app) */}
      <label>Email Body (HTML/Text):</label>
      <textarea
        value={template.bodyHtml}
        onChange={(e) => setTemplate({ ...template, bodyHtml: e.target.value })}
        rows={10}
      />

      {/* Action Buttons */}
      <button onClick={handlePreview}>Preview Email</button>
      <button onClick={() => handleFinalSchedule(/* Pass all scheduling data here */)}>
        Schedule and Send
      </button>

      {/* Preview Modal/Area */}
      {previewContent && (
        <div style={{ border: '1px solid #ccc', padding: '15px', marginTop: '20px' }}>
          <h3>{previewContent.subject}</h3>
          {/* CRITICAL: Use dangerouslySetInnerHTML for rendered HTML */}
          <div dangerouslySetInnerHTML={{ __html: previewContent.bodyHtml }} />
        </div>
      )}
    </div>
  );
};

export default SchedulingTab;