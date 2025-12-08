// src/utils/emailDefaultTemplates.ts

/**
 * This file contains the default email templates, mirrored from the backend's
 * `app/utils/email_utils.py`.
 *
 * They are used as a fallback in the Email Configuration tab if no custom
 * template has been saved in the database yet.
 *
 * Placeholders use the `{{PLACEHOLDER}}` format, matching Jinja2.
 */

// --- Template: ADMIN_INVITE ---
const ADMIN_INVITE_SUBJECT = "You're Invited to Join the RMS Platform";
const ADMIN_INVITE_BODY = `
<div style="font-family: Arial, sans-serif; line-height: 1.6;">
  <h2 style="color: #333;">Welcome to the Team!</h2>
  <p>Hello {{ADMIN_NAME}},</p>
  <p>You have been invited by <strong>{{INVITED_BY_NAME}}</strong> to join the Recruitment Management System (RMS) as an administrator.</p>
  <p>Please click the link below to set up your account and get started:</p>
  <p style="margin: 25px 0;">
    <a href="{{INVITE_LINK}}" style="background-color: #007bff; color: #ffffff; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Set Up Your Account</a>
  </p>
  <p>This invitation link is valid for 24 hours.</p>
  <p>If you have any questions, please contact your administrator.</p>
  <br>
  <p>Best regards,<br>The RMS Team</p>
</div>
`;

// --- Template: ADMIN_ROLE_UPDATE ---
const ADMIN_ROLE_UPDATE_SUBJECT = "Your Admin Role Has Been Updated";
const ADMIN_ROLE_UPDATE_BODY = `
<div style="font-family: Arial, sans-serif; line-height: 1.6;">
  <h2 style="color: #333;">Account Update Notification</h2>
  <p>Hello {{ADMIN_NAME}},</p>
  <p>This is to inform you that your role on the Recruitment Management System (RMS) has been updated by <strong>{{UPDATED_BY_NAME}}</strong>.</p>
  <p>Your new role is: <strong>{{NEW_ROLE}}</strong>.</p>
  <p>Your permissions and access may have changed. Please log in to review the changes.</p>
  <p>If you believe this was in error, please contact your Super Admin.</p>
  <br>
  <p>Best regards,<br>The RMS Team</p>
</div>
`;

// --- Template: ADMIN_DELETE ---
const ADMIN_DELETE_SUBJECT = "Your Admin Account Has Been Deactivated";
const ADMIN_DELETE_BODY = `
<div style="font-family: Arial, sans-serif; line-height: 1.6;">
  <h2 style="color: #333;">Account Deactivation Notification</h2>
  <p>Hello {{ADMIN_NAME}},</p>
  <p>This is to inform you that your administrator account on the Recruitment Management System (RMS) has been deactivated by <strong>{{DELETED_BY_NAME}}</strong>.</p>
  <p>You will no longer be able to access the platform.</p>
  <p>If you believe this was in error, please contact your Super Admin.</p>
  <br>
  <p>Best regards,<br>The RMS Team</p>
</div>
`;

// --- Template: CANDIDATE_INTERVIEW_SCHEDULED ---
const CANDIDATE_INTERVIEW_SUBJECT = "Interview Invitation for {{JOB_TITLE}}";
const CANDIDATE_INTERVIEW_BODY = `
<div style="font-family: Arial, sans-serif; line-height: 1.6;">
  <p>Dear {{CANDIDATE_NAME}},</p>
  <p>Congratulations! You have been shortlisted for the <strong>{{ROUND_NAME}}</strong> round for the <strong>{{JOB_TITLE}}</strong> position.</p>
  
  <h3 style="color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px;">Interview Details</h3>
  <ul style="list-style-type: none; padding-left: 0;">
    <li><strong>Date:</strong> {{DATE}}</li>
    <li><strong>Time:</strong> {{TIME}}</li>
    <li><strong>Type:</strong> {{INTERVIEW_TYPE}}</li>
  </ul>
  
  <p>The interview link below will become active near the scheduled time. Please use the Room ID to join the session.</p>
  
  <p style="margin: 25px 0;">
    <a href="{{INTERVIEW_LINK}}" style="background-color: #007bff; color: #ffffff; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Join Interview Session</a>
  </p>
  
  <p><strong>Room ID:</strong> <span style="font-size: 1.1em; font-weight: bold; color: #333;">{{INTERVIEW_TOKEN}}</span></p>
  
  <p>The next round after this will be: <strong>{{NEXT_ROUND_NAME}}</strong>.</p>
  <p>We look forward to speaking with you.</p>
  <br>
  <p>Best regards,<br>The RMS Team</p>
</div>
`;

/**
 * A Map containing the default fallback templates.
 */
export const DEFAULT_EMAIL_TEMPLATES = new Map<string, { subject: string, body: string }>([
    ['ADMIN_INVITE', { subject: ADMIN_INVITE_SUBJECT, body: ADMIN_INVITE_BODY.trim() }],
    ['ADMIN_ROLE_UPDATE', { subject: ADMIN_ROLE_UPDATE_SUBJECT, body: ADMIN_ROLE_UPDATE_BODY.trim() }],
    ['ADMIN_DELETE', { subject: ADMIN_DELETE_SUBJECT, body: ADMIN_DELETE_BODY.trim() }],
    ['CANDIDATE_INTERVIEW_SCHEDULED', { subject: CANDIDATE_INTERVIEW_SUBJECT, body: CANDIDATE_INTERVIEW_BODY.trim() }],
  // OTP and verification flows
  ['OTP', { subject: 'Your One-Time Password (OTP) for RMS', body: `Your OTP is: {{OTP_CODE}}` }],
  ['OTP_VERIFICATION', { subject: 'Your One-Time Password (OTP) for RMS', body: `Your OTP is: {{OTP_CODE}}` }],
  ['EMAIL_UPDATE_VERIFICATION', { subject: 'Action Required: Confirm Your New Email Address', body: `Please confirm: {{VERIFICATION_LINK}}` }],
  ['EMAIL_CHANGE_TRANSFER_NOTIFICATION', { subject: 'Security Notice: Admin Email Transfer Initiated', body: `An admin email transfer has been initiated for {{OLD_EMAIL}} -> {{NEW_EMAIL}}` }],
  ['NAME_UPDATE_VERIFICATION', { subject: 'Action Required: Confirm Name Change', body: `Confirm name change to {{NEW_NAME}}: {{VERIFICATION_LINK}}` }],
  ['NAME_UPDATE_SUCCESS', { subject: 'Your Profile Name Has Been Updated', body: `Your profile name is now {{NEW_NAME}}` }],
  ['PHONE_UPDATE_VERIFICATION', { subject: 'Action Required: Confirm Phone Number Change', body: `Confirm phone update: {{VERIFICATION_LINK}}` }],
  ['OTP_FOR_EMAIL_UPDATE', { subject: 'OTP to Confirm Admin Email Change', body: `Your OTP is: {{OTP_CODE}}` }],
]);

/**
 * A Map containing the placeholders for each template.
 * These MUST match the keys in email_utils.py (e.g., {{ADMIN_NAME}} -> ADMIN_NAME)
 */
export const TEMPLATE_PLACEHOLDERS = new Map<string, { key: string, description: string }[]>([
    ['ADMIN_INVITE', [
        { key: 'ADMIN_NAME', description: 'The invited admin\'s full name' },
        { key: 'INVITE_LINK', description: 'The unique account setup link' },
        { key: 'INVITED_BY_NAME', description: 'The name of the admin who sent the invite' }
    ]],
    ['ADMIN_ROLE_UPDATE', [
        { key: 'ADMIN_NAME', description: 'The admin\'s full name' },
        { key: 'NEW_ROLE', description: 'The new role assigned (e.g., "HR")' },
        { key: 'UPDATED_BY_NAME', description: 'The name of the admin who made the change' }
    ]],
    ['ADMIN_DELETE', [
        { key: 'ADMIN_NAME', description: 'The deactivated admin\'s full name' },
        { key: 'DELETED_BY_NAME', description: 'The name of the admin who deactivated the account' }
    ]],
    ['CANDIDATE_INTERVIEW_SCHEDULED', [
        { key: 'CANDIDATE_NAME', description: 'The candidate\'s full name' },
        { key: 'JOB_TITLE', description: 'The title of the job (e.g., "Software Engineer")' },
        { key: 'ROUND_NAME', description: 'The name of the interview round (e.g., "Technical Round")' },
        { key: 'DATE', description: 'The date of the interview (e.g., "November 12, 2025")' },
        { key: 'TIME', description: 'The time of the interview (e.g., "3:00 PM IST")' },
        { key: 'INTERVIEW_TYPE', description: 'The type of interview (e.g., "Agent Interview")' },
        { key: 'INTERVIEW_LINK', description: 'The URL link for the candidate to join' },
        { key: 'INTERVIEW_TOKEN', description: 'The unique Room ID for the interview' },
        { key: 'NEXT_ROUND_NAME', description: 'The name of the following round (e.g., "HR Round")' }
    ]],
  ['OTP', [
    { key: 'OTP_CODE', description: 'The one-time password code' },
    { key: 'OTP_EXPIRE_MINUTES', description: 'Minutes before OTP expires' }
  ]],
  ['EMAIL_UPDATE_VERIFICATION', [
    { key: 'ADMIN_NAME', description: 'Name of the admin' },
    { key: 'VERIFICATION_LINK', description: 'Verification link to confirm email' },
    { key: 'EXPIRES_TEXT', description: 'Expiry display for the link' }
  ]],
  ['EMAIL_CHANGE_TRANSFER_NOTIFICATION', [
    { key: 'ADMIN_NAME', description: 'Name of the admin' },
    { key: 'OLD_EMAIL', description: 'Original admin email' },
    { key: 'NEW_EMAIL', description: 'New email being transferred to' }
  ]],
  ['NAME_UPDATE_VERIFICATION', [
    { key: 'OLD_NAME', description: 'Old display name' },
    { key: 'NEW_NAME', description: 'Proposed new display name' },
    { key: 'VERIFICATION_LINK', description: 'Verification link' }
  ]],
  ['NAME_UPDATE_SUCCESS', [
    { key: 'FIRST_NAME', description: 'Recipient first name' },
    { key: 'NEW_NAME', description: 'New full name' }
  ]],
  ['PHONE_UPDATE_VERIFICATION', [
    { key: 'ADMIN_NAME', description: 'Name of the admin' },
    { key: 'NEW_PHONE', description: 'The new phone number' },
    { key: 'VERIFICATION_LINK', description: 'Verification link' }
  ]],
  ['OTP_FOR_EMAIL_UPDATE', [
    { key: 'OTP_CODE', description: 'The one-time password code' },
    { key: 'OTP_EXPIRE_MINUTES', description: 'Minutes before OTP expires' }
  ]],
]);

/**
 * List of all configurable templates to display as cards.
 */
export const CONFIGURABLE_TEMPLATES = [
    {
        key: 'ADMIN_INVITE',
        name: 'Admin Invitation',
        description: 'Email sent when a new admin is invited to the platform.',
    },
    {
        key: 'ADMIN_ROLE_UPDATE',
        name: 'Admin Role Change',
        description: 'Email notifying an admin that their role has been updated.',
    },
    {
        key: 'ADMIN_DELETE',
        name: 'Admin Account Deletion',
        description: 'Email notifying an admin that their account has been deactivated.',
    },
    {
        key: 'CANDIDATE_INTERVIEW_SCHEDULED',
        name: 'Candidate Interview',
        description: 'Main invitation sent to candidates for an interview.',
    }
  ,
  {
    key: 'OTP',
    name: 'OTP Verification',
    description: 'One-time password (OTP) emails for verification flows.',
  },
  {
    key: 'EMAIL_UPDATE_VERIFICATION',
    name: 'Email Update Verification',
    description: 'Verification link sent to confirm a change of email address.',
  },
  {
    key: 'EMAIL_CHANGE_TRANSFER_NOTIFICATION',
    name: 'Email Transfer Notification',
    description: 'Security notice when an admin email transfer is initiated.',
  },
  {
    key: 'NAME_UPDATE_VERIFICATION',
    name: 'Name Update Verification',
    description: 'Verification email for name changes.',
  },
  {
    key: 'NAME_UPDATE_SUCCESS',
    name: 'Name Update Success',
    description: 'Notification after a successful name update.',
  },
  {
    key: 'PHONE_UPDATE_VERIFICATION',
    name: 'Phone Update Verification',
    description: 'Verification email for phone number updates.',
  },
  {
    key: 'OTP_FOR_EMAIL_UPDATE',
    name: 'OTP for Email Update',
    description: 'OTP sent specifically to confirm admin email changes.',
  }
    // ... Add more templates here as they are created
];