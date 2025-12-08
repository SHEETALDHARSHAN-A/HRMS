# app/authentication/protected_routes_config.py

EXCLUDED_ROUTES = [
    "/docs",
    "/openapi.json",
    "/v1/auth/send-otp",
    "/v1/auth/resend-otp",
    "/v1/auth/verify-otp",
    "/v1/auth/check-cookie",
    "/v1/auth/check-email-status",
    "/v1/auth/debug-list-emails",
    # Also accept fully-prefixed paths in case root_path handling differs
    "/api/v1/auth/send-otp",
    "/api/v1/auth/resend-otp",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/check-cookie",
    "/api/v1/auth/check-email-status",
    "/api/v1/auth/debug-list-emails",
    # Public interview endpoints for candidates
    "/v1/interview/validate-token",
    "/v1/interview/verify-otp",
    "/v1/admins/complete-setup",
    "/v1/admins/complete-admin-setup",
    "/v1/admins/verify-name-update",
    "/v1/admins/confirm-phone-update",
    "/v1/admins/complete-email-update-status",
    "/v1/admins/approve-email-update",
    "/v1/admins/verify-email-update",
    # Public job listings (career page) - allow unauthenticated access
    "/v1/job-post/active", # Main active route
    # Public job details for application page - allow unauthenticated access
    "/v1/job-post/public/job/", # Wildcard for /job-post/public/job/{job_id}
    # Public search endpoints - allow unauthenticated access
    "/v1/job-post/public/search-suggestions",
    "/v1/job-post/public/search",
    # Career application endpoints - allow unauthenticated access
    "/v1/career/apply/send-otp",
    "/v1/career/apply/verify-and-submit",
    # Resume upload endpoint for career applications - allow unauthenticated access
    "/v1/resume/upload-resumes/", # Wildcard for /v1/resume/upload-resumes/{job_id}


    "/api/v1/interview/validate-token",
    "/api/v1/interview/verify-otp",
    "/api/v1/admins/complete-setup",
    "/api/v1/admins/complete-admin-setup",
    "/api/v1/admins/verify-name-update",
    "/api/v1/admins/confirm-phone-update",
    "/api/v1/admins/complete-email-update-status",
    "/api/v1/admins/approve-email-update",
    "/api/v1/admins/verify-email-update",
    "/api/v1/job-post/active",
    "/api/v1/job-post/public/job/",
    "/api/v1/job-post/public/search-suggestions",
    "/api/v1/job-post/public/search",
    "/api/v1/career/apply/send-otp",
    "/api/v1/career/apply/verify-and-submit",
    "/api/v1/resume/upload-resumes/",
] 

ROLE_PROTECTED_ENDPOINTS = {
  
    # Role-based permissions for inviting users
    "/v1/admins/invite": ["SUPER_ADMIN", "ADMIN", "HR"],        
    "/v1/admins/delete/{admin_id}": ["SUPER_ADMIN"], 
    "/v1/admins/delete-batch": ["SUPER_ADMIN", "ADMIN"], 
    "/v1/admins/get/{admin_id}": ["SUPER_ADMIN", "ADMIN", "HR"], 
    "/v1/admins/list-all":  ["SUPER_ADMIN", "ADMIN", "HR"],

    "/api/v1/admins/invite": ["SUPER_ADMIN", "ADMIN", "HR"],        
    "/v1/admins/delete/{admin_id}": ["SUPER_ADMIN"], 
    "/api/v1/admins/delete-batch": ["SUPER_ADMIN", "ADMIN"], 
    "/api/v1/admins/get/{admin_id}": ["SUPER_ADMIN", "ADMIN", "HR"], 
    "/api/v1/admins/list-all":  ["SUPER_ADMIN", "ADMIN", "HR"],
    # ----------------------------------------
    # II. GENERAL USER MANAGEMENT (Admin/Super Admin Access)
    # ----------------------------------------
    "/v1/profile/update": ["ADMIN", "CANDIDATE"],
    "/v1/profile/verify-email-update": ["ADMIN", "CANDIDATE"],
    "/v1/admins/verify-email-update": ["ADMIN","SUPER_ADMIN"],
    "/v1/admins/update/{admin_id}": ["ADMIN", "SUPER_ADMIN"],

    "/api/v1/profile/update": ["ADMIN", "CANDIDATE"],
    "/api/v1/profile/verify-email-update": ["ADMIN", "CANDIDATE"],
    "/api/v1/admins/verify-email-update": ["ADMIN","SUPER_ADMIN"],
    "/api/v1/admins/update/{admin_id}": ["ADMIN", "SUPER_ADMIN"],
    # ----------------------------------------
    # III. CANDIDATE (STUDENT) / INTERVIEW ROUTES
    # ----------------------------------------
    "/v1/interview/start-sessions": ["CANDIDATE"],
    "/v1/interview/end-sessions": ["CANDIDATE"],
    "/v1/interview/schedule-session": ["ADMIN", "SUPER_ADMIN"],
    "/v1/interview/abort-session": ["ADMIN", "SUPER_ADMIN"], 
    "/v1/students/sessions": ["CANDIDATE", "ADMIN", "SUPER_ADMIN"],
    "/v1/students/update/{user_id}": ["CANDIDATE", "ADMIN", "SUPER_ADMIN"],
    
    "/api/v1/interview/start-sessions": ["CANDIDATE"],
    "/api/v1/interview/end-sessions": ["CANDIDATE"],
    "/api/v1/interview/schedule-session": ["ADMIN", "SUPER_ADMIN"],
    "/api/v1/interview/abort-session": ["ADMIN", "SUPER_ADMIN"], 
    "/api/v1/students/sessions": ["CANDIDATE", "ADMIN", "SUPER_ADMIN"],
    "/api/v1/students/update/{user_id}": ["CANDIDATE", "ADMIN", "SUPER_ADMIN"],
    # ----------------------------------------
    # IV. ADMIN/SUPER ADMIN DASHBOARD & REGISTRATION
    # ----------------------------------------
    "/v1/dashboard/overview": ["ADMIN", "SUPER_ADMIN"],
    "/v1/registration/students/upload": ["ADMIN", "SUPER_ADMIN"],
    "/v1/registration/admin/upload": ["SUPER_ADMIN"],
    "/api/v1/dashboard/overview": ["ADMIN", "SUPER_ADMIN"],
    "/api/v1/registration/students/upload": ["ADMIN", "SUPER_ADMIN"],
    "/api/v1/registration/admin/upload": ["SUPER_ADMIN"],
    
    # ----------------------------------------
    # V. INVITATIONS & NOTIFICATIONS (Admin Access)
    # ----------------------------------------
    "/v1/invitations/my-invitations": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/invitations/stats": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/notifications/": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/notifications/unread-count": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/notifications/{notification_id}/mark-read": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/v1/notifications/mark-all-read": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/api/v1/invitations/my-invitations": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/api/v1/invitations/stats": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/api/v1/notifications/": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/api/v1/notifications/unread-count": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/api/v1/notifications/{notification_id}/mark-read": ["SUPER_ADMIN", "ADMIN", "HR"],
    "/api/v1/notifications/mark-all-read": ["SUPER_ADMIN", "ADMIN", "HR"],
}
