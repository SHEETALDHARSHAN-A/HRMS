# app/api/v1/authentication_routes.py

import json
import logging
import redis.asyncio as redis

from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import APIRouter, Depends, Query, Response, Request, status

from app.config.app_config import AppConfig
from app.db.connection_manager import get_db
from app.db.redis_manager import get_redis_client
from fastapi.responses import JSONResponse, RedirectResponse
from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_utils import create_access_token, create_refresh_token

from app.schemas.standard_response import StandardResponse
from app.schemas.authentication_request import  VerifyOTPRequest, SendOTPRequest ,AdminInviteRequest, DeleteAdminsBatchRequest, UpdateEmailVerifyTokenRequest,AdminUpdateRequest
from app.controllers.authentication_controller import (
    handle_verify_otp_controller,
    handle_send_otp_controller,
    handle_resend_otp_controller,
    handle_check_cookie_controller,
    handle_logout_controller,
    handle_invite_admin_controller,
    handle_complete_admin_setup_controller,
    handle_delete_admins_batch_controller,
    handle_get_all_admins_controller,
    handle_get_admin_by_id_controller,
    handle_update_admin_controller,
    handle_verify_admin_name_update_controller,
    handle_verify_admin_phone_update_controller,
    handle_verify_admin_email_update_controller,
    handle_check_email_status_controller,
    handle_debug_list_emails_controller,
    handle_complete_email_update_controller,
    handle_approve_email_update_controller
    ,
    handle_search_admins_controller
)

settings = AppConfig()

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
admin_router = APIRouter(prefix="/admins", tags=["Admin Management"])

@auth_router.post("/send-otp", response_model=StandardResponse, summary="Send OTP for Sign-in")
async def send_otp_endpoint(
    user_data: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
):
    return await handle_send_otp_controller(user_data, db, cache)

@auth_router.post("/resend-otp", response_model=StandardResponse, summary="Resend OTP for Sign-in/Sign-up")
async def resend_otp_endpoint(
    user_data: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
):
    return await handle_resend_otp_controller(user_data, db, cache)

@auth_router.get("/check-email-status", response_model=StandardResponse, summary="Check if email exists in DB")
async def check_email_status_endpoint(
    email: str = Query(..., description="Email address to check for existence"),
    db: AsyncSession = Depends(get_db)
):
    """
    Checks if an email is registered in the database. 
    Returns 200 OK (success: true) if available, 409 CONFLICT (success: false) if user exists.
    """
    return await handle_check_email_status_controller(email, db)

@auth_router.get("/debug-list-emails", response_model=StandardResponse, summary="DEBUG: List all emails in database")
async def debug_list_emails_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """DEBUG endpoint to list all emails in the database for troubleshooting."""
    return await handle_debug_list_emails_controller(db)

@auth_router.post("/verify-otp", response_model=StandardResponse, summary="Verify OTP and Issue Tokens")
async def verify_otp_endpoint(
    user_data: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
):
    return await handle_verify_otp_controller(user_data, response, db, cache)

@auth_router.get("/check-cookie", response_model=StandardResponse, summary="Check Cookie Authentication")
async def check_cookie_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    return await handle_check_cookie_controller(request, db)

@auth_router.get("/logout", response_model=StandardResponse, summary="Logout")
async def logout_endpoint(response: Response, request: Request, cache: redis.Redis = Depends(get_redis_client)):
    return await handle_logout_controller(response, request, cache)

@admin_router.post("/invite", response_model=StandardResponse, summary="Send Admin Invitation Link")
async def invite_admin_endpoint(
    user_data: AdminInviteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
) -> JSONResponse:
    return await handle_invite_admin_controller(user_data, db, cache, request)

#--------------- Admin Management Endpoints (SUPER_ADMIN) ----------------#

@admin_router.post("/complete-admin-setup", response_model=StandardResponse, summary="Complete Admin Setup via Link")
async def complete_admin_setup_endpoint(
    response: Response, # 💡 FIX: Moved Response to before parameters with defaults
    token: str = Query(..., description="Secure token from the invitation link"),
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
) -> JSONResponse:
    return await handle_complete_admin_setup_controller(token, db, cache, response)

@admin_router.get("/list-all", response_model=StandardResponse, summary="SUPER_ADMIN: Get list of all Admins")
async def get_all_admins_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    return await handle_get_all_admins_controller(db, request)

@admin_router.delete("/delete-batch", response_model=StandardResponse, summary="SUPER_ADMIN: Delete Admins by list of User IDs")
async def delete_admins_batch_endpoint(
    user_data: DeleteAdminsBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    return await handle_delete_admins_batch_controller(user_data, db, request)

@admin_router.get("/get/{admin_id}", response_model=StandardResponse, summary="SUPER_ADMIN: Get Admin details by User ID")
async def get_admin_by_id_endpoint(admin_id: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    return await handle_get_admin_by_id_controller(admin_id, db)


@admin_router.get("/search", response_model=StandardResponse, summary="Search Admins by name, email or ID")
async def search_admins_endpoint(
    q: str = Query(..., description="Search query (name, email, or ID)"),
    db: AsyncSession = Depends(get_db),
):
    """Search endpoint used by frontend: GET /v1/admins/search?q=..."""
    return await handle_search_admins_controller(q, db)

@admin_router.put("/update/{admin_id}", response_model=StandardResponse, summary="SUPER_ADMIN: Update Admin details (Triggers verification for name/email change)")
async def update_admin_endpoint(
    admin_id: str, 
    user_data: AdminUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
) -> JSONResponse:
    return await handle_update_admin_controller(admin_id, user_data, db, cache, request)

@admin_router.get("/approve-email-update", include_in_schema=False)
async def approve_email_update_endpoint(
    token: str = Query(..., description="Approval token sent to the current admin email."),
    user_id: str = Query(..., description="User ID of the admin."),
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
):
    return await handle_approve_email_update_controller(token, user_id, db, cache)

@admin_router.get("/verify-email-update", response_model=StandardResponse, summary="ADMIN: Complete email update process using verification token link")
async def verify_email_update_endpoint(
    user_id: str = Query(..., description="User ID of the admin."),
    token: str = Query(..., description="Secure token from the verification link."),
    new_email: str = Query(..., description="The new email being verified."),
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
) -> JSONResponse:
    request_data = UpdateEmailVerifyTokenRequest(user_id=user_id, token=token, new_email=new_email)
    return await handle_verify_admin_email_update_controller(request_data, db, cache)

@admin_router.post("/verify-email-update", response_model=StandardResponse, summary="API endpoint to verify email update")
async def verify_email_update_endpoint(
    user_data: UpdateEmailVerifyTokenRequest,
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client)
) -> JSONResponse:
    """API endpoint for email verification (for programmatic access)"""
    try:
        result = await handle_verify_admin_email_update_controller(user_data, db, cache)
        return result
    except Exception as e:
        return JSONResponse(
            content=ResponseBuilder.error(str(e), [str(e)], status_code=500),
            status_code=500
        )

@admin_router.get("/verify-name-update", include_in_schema=True, summary="Verify admin name update (public link)")
async def verify_name_update_endpoint_name(
    user_id: str = Query(..., description="UUID of the admin user"),
    token: str = Query(..., description="Verification token"),
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client),
):
    """
    Public endpoint that finalizes name updates initiated via email confirmation.
    """
    try:
        return await handle_verify_admin_name_update_controller(token=token, user_id=user_id, db=db, cache=cache)
    except Exception as e:
        logger.exception("Error in verify_name_update_endpoint_name: %s", e)
        return JSONResponse(content=ResponseBuilder.server_error(f"An unexpected error occurred: {e}"), status_code=500)


@admin_router.get("/confirm-phone-update", include_in_schema=True)
async def confirm_phone_update_endpoint(
    token: str = Query(..., description="Verification token for phone update"),
    user_id: str = Query(..., description="User ID of the admin"),
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client),
):
    """Public endpoint that finalizes phone number updates via link and redirects to frontend."""
    try:
        return await handle_verify_admin_phone_update_controller(token=token, user_id=user_id, db=db, cache=cache)
    except Exception as e:
        logger.exception("Error in confirm_phone_update_endpoint: %s", e)
        # Redirect with a generic error
        from fastapi.responses import RedirectResponse
        import urllib.parse

        message = urllib.parse.quote("Unexpected error during phone confirmation.")
        redirect_url = f"{settings.frontend_url}/auth?status=phone_update_error&message={message}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

@admin_router.get("/complete-email-update-status", include_in_schema=True)
async def complete_email_update_status_endpoint(
    request: Request,
    token: str = Query(...),
    user_id: str = Query(...),
    new_email: str = Query(...),
    redirect_to: str = Query(None),
    db: AsyncSession = Depends(get_db),
    cache: redis.Redis = Depends(get_redis_client),
    response: Response = None,
):
    """Complete email update verification.
    This is a public endpoint that handles email verification without requiring authentication.
    """
    try:
        # Delegate to the controller designed for public GET verification which returns RedirectResponses
        return await handle_complete_email_update_controller(token, user_id, new_email, db, cache)
    except Exception as e:
        # Fallback: redirect to provided frontend URL with an encoded error message
        if redirect_to:
            error_url = f"{redirect_to}?error={quote_plus(str(e))}"
            return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
        return ResponseBuilder.server_error(str(e))