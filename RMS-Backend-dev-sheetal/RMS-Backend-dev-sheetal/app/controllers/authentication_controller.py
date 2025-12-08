# app/controllers/authentication_controller.py

import asyncio
import logging
import redis.asyncio as redis

from datetime import datetime, timezone 
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError, ExpiredSignatureError 
from fastapi import HTTPException, Response, status, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.schemas.authentication_request import ( 
    VerifyOTPRequest, 
    SendOTPRequest, 
    AdminInviteRequest, 
    DeleteAdminsBatchRequest, 
    AdminUpdateRequest, 
    UpdateEmailVerifyTokenRequest
)

from app.config.app_config import AppConfig
from app.db.repository.user_repository import get_user_by_id
from app.utils.standard_response_utils import ResponseBuilder
from app.utils.authentication_utils import add_jti_to_blocklist

from app.services.admin_service.update_admin_service import UpdateAdminService
from app.services.admin_service.invite_admin_service import InviteAdminService 
from app.services.authentication_service.send_otp_service import SendOtpService
from app.services.admin_service.get_all_admins_service import GetAllAdminsService
from app.services.admin_service.get_admin_by_id_service import GetAdminByIdService
from app.services.authentication_service.resend_otp_service import ResendOtpService 
from app.services.authentication_service.verify_otp_service import VerifyOtpService
from app.services.admin_service.delete_admins_batch_service import DeleteAdminsBatchService 
from app.services.admin_service.complete_admin_setup_service import CompleteAdminSetupService 
from app.services.authentication_service.check_email_service import CheckUserExistenceService

logger = logging.getLogger(__name__)
settings = AppConfig()

async def handle_send_otp_controller(user_data: SendOTPRequest, db: AsyncSession, cache: redis.Redis) -> JSONResponse:
    try:
        service = SendOtpService(db, cache)
        result = await service.send_otp(user_data)
        
        if isinstance(result, dict) and result.get("success") is not None and result.get("status_code"):
            return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
            
        return JSONResponse(content=ResponseBuilder.success(result["message"], {"expires_in": result["expires_in"]}), status_code=status.HTTP_200_OK)
    
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_send_otp_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_resend_otp_controller(user_data: SendOTPRequest, db: AsyncSession, cache: redis.Redis) -> JSONResponse:
    """Controller for POST /auth/resend-otp (Resend Flow)."""
    try:
        # Pass DB into the ResendOtpService so it can use saved templates when sending OTPs.
        # Some tests monkeypatch a fake ResendOtpService with a different
        # constructor signature (e.g. only accepting cache). Attempt the
        # intended (cache, db) instantiation first and gracefully fall back
        # to the single-arg form for compatibility with test fakes.
        try:
            service = ResendOtpService(cache, db)
        except TypeError:
            service = ResendOtpService(cache)
        result = await service.resend_otp(user_data)
        
        if isinstance(result, dict) and result.get("success") is not None and result.get("status_code"):
            return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
            
        return JSONResponse(content=ResponseBuilder.success(result["message"], {"expires_in": result["expires_in"]}), status_code=status.HTTP_200_OK)
    
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_resend_otp_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_verify_otp_controller(user_data: VerifyOTPRequest, response: Response, db: AsyncSession, cache: redis.Redis) -> JSONResponse:
    """Controller for POST /auth/verify-otp (Handles both Sign-in and Sign-up)."""
    try:
        service = VerifyOtpService(db, cache)
        result = await service.verify_otp(user_data, response)
        # Note: VerifyOtpService is expected to return a JSONResponse object directly
        return result
        
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_verify_otp_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
async def handle_check_email_status_controller(email: str, db: AsyncSession) -> JSONResponse:
    """Controller for GET /auth/check-email-status (Email existence check)."""
    try:
        logger.info(f"check_email_status_controller: received email={email}")
        service = CheckUserExistenceService(db)
        result = await service.check_email_status(email)
        
        logger.info(f"check_email_status_controller: service result={result}")
        # The service returns a dict containing status_code, use it for JSONResponse.
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
    
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_check_email_status_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_debug_list_emails_controller(db: AsyncSession) -> JSONResponse:
    """DEBUG Controller for GET /auth/debug-list-emails (List all emails in DB)."""
    try:
        from sqlalchemy.future import select
        from app.db.models.user_model import User
        
        result = await db.execute(select(User.email, User.role, User.user_id).limit(20))
        emails = [{"email": row[0], "role": row[1], "user_id": str(row[2])} for row in result.fetchall()]
        
        return JSONResponse(content={
            "success": True,
            "message": f"Found {len(emails)} users",
            "data": {"users": emails}
        }, status_code=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in debug list emails: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Debug error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- ADMIN INVITE HANDLERS ---

async def handle_invite_admin_controller(user_data: AdminInviteRequest, db: AsyncSession, cache: redis.Redis, request: Request):
    """Controller for POST /v1/admins/invite (Role-Based Protected)."""
    try:
        # Get the caller's role from JWT
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=status.HTTP_401_UNAUTHORIZED),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        caller_role = user_payload.get("role")
        invited_role = user_data.role
        
        # Validate permissions:
        # SUPER_ADMIN can invite anyone (SUPER_ADMIN, ADMIN, HR)
        # ADMIN can invite ADMIN or HR
        # HR can invite HR only
        if caller_role == "SUPER_ADMIN":
            # Super admin can invite anyone
            pass
        elif caller_role == "ADMIN":
            if invited_role not in ["ADMIN", "HR"]:
                return JSONResponse(
                    content=ResponseBuilder.error("ADMIN can only invite ADMIN or HR roles", [], status_code=status.HTTP_403_FORBIDDEN),
                    status_code=status.HTTP_403_FORBIDDEN
                )
        elif caller_role == "HR":
            if invited_role != "HR":
                return JSONResponse(
                    content=ResponseBuilder.error("HR can only invite HR roles", [], status_code=status.HTTP_403_FORBIDDEN),
                    status_code=status.HTTP_403_FORBIDDEN
                )
        else:
            return JSONResponse(
                content=ResponseBuilder.error("Insufficient permissions to invite users", [], status_code=status.HTTP_403_FORBIDDEN),
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        # Get the caller's user ID for tracking who sent the invitation (check both 'user_id' and standard 'sub' field)
        caller_user_id = user_payload.get("user_id") or user_payload.get("sub")
        
        service = InviteAdminService(db, cache)
        result = await service.generate_admin_invite(user_data, caller_user_id)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
        
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_invite_admin_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_complete_admin_setup_controller(token: str, db: AsyncSession, cache: redis.Redis, response: Response):
    """Controller for POST /v1/admins/complete-setup (Public Link Endpoint)."""
    try:
        service = CompleteAdminSetupService(db, cache)
        # Pass the response object to the service
        result = await service.complete_admin_setup(token, response)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_201_CREATED))
        
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_complete_admin_setup_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
# --- ADMIN MANAGEMENT HANDLERS (SUPER_ADMIN ACTIONS) ---

async def handle_get_all_admins_controller(db: AsyncSession, request: Request):
    """Controller for GET /v1/admins/list-all (Role-Based Protected)."""
    try:
        # Get the caller's role from JWT
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=status.HTTP_401_UNAUTHORIZED),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        caller_role = user_payload.get("role")
        
        # DEBUG: Log what we're receiving
        print(f"[DEBUG] JWT Middleware user_payload: {user_payload}")
        print(f"[DEBUG] Extracted caller_role: {caller_role}")
        print(f"[DEBUG] user_payload keys: {list(user_payload.keys()) if user_payload else 'None'}")
        
        service = GetAllAdminsService(db)
        result = await service.get_all_admins(caller_role=caller_role)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
        
    except Exception as e:
        logger.error(f"Error in handle_get_all_admins_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_delete_admins_batch_controller(user_data: DeleteAdminsBatchRequest, db: AsyncSession, request: Request):
    """Controller for DELETE /v1/admins/delete-batch (Role-Based Protected)."""
    try:
        # Get the caller's role from JWT
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=status.HTTP_401_UNAUTHORIZED),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        caller_role = user_payload.get("role")
        caller_id = user_payload.get("sub")
        
        service = DeleteAdminsBatchService(db)
        result = await service.delete_admins(user_data, caller_role=caller_role, caller_id=caller_id)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
        
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    
    except Exception as e:
        logger.error(f"Error in handle_delete_admins_batch_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_get_admin_by_id_controller(admin_id: str, db: AsyncSession):
    """Controller for GET /v1/admins/get/{admin_id} (Super Admin Protected)."""
    try:
        service = GetAdminByIdService(db)
        result = await service.get_admin_details(admin_id)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error in handle_get_admin_by_id_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def handle_search_admins_controller(query: str, db: AsyncSession):
    """Controller to handle admin search queries (GET /v1/admins/search?q=...)."""
    try:
        from app.db.repository.user_repository import search_admins

        results = await search_admins(db, query)
        # Return results under a data key for compatibility with frontend expectations
        return JSONResponse(content=ResponseBuilder.success("Search results", {"admins": results}), status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Error in handle_search_admins_controller: %s", e)
        return JSONResponse(content=ResponseBuilder.server_error(str(e)), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_update_admin_controller(admin_id: str, user_data: AdminUpdateRequest, db: AsyncSession, cache: redis.Redis, request: Request):
    """Controller for PUT /v1/admins/update/{admin_id} (Role-Based Protected)."""
    try:
        # Get the caller's role from JWT
        user_payload = getattr(request.state, 'user', None)
        if not user_payload:
            return JSONResponse(
                content=ResponseBuilder.error("Authentication required", [], status_code=status.HTTP_401_UNAUTHORIZED),
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        caller_role = user_payload.get("role")
        caller_id = user_payload.get("sub")
        
        service = UpdateAdminService(db, cache)
        result = await service.update_admin_details(admin_id, user_data, caller_role=caller_role, caller_id=caller_id)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error in handle_update_admin_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_verify_admin_name_update_controller(token: str, user_id: str, db: AsyncSession, cache: redis.Redis):
    """Handles the completion of the name update via a verification link."""
    try:
        service = UpdateAdminService(db, cache)
        result = await service.verify_name_update(token, user_id)
        # If verification succeeded, redirect to processing page that will show confirmation and redirect to auth
        if isinstance(result, dict) and result.get("success"):
            redirect_url = f"{settings.frontend_url}/verification/processing?type=name_update&status=success&redirect_to=auth"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        # Otherwise redirect to processing page with error status
        import urllib.parse
        msg = urllib.parse.quote(result.get("message", "Unable to confirm name change."))
        redirect_url = f"{settings.frontend_url}/verification/processing?type=name_update&status=error&message={msg}&redirect_to=auth"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except HTTPException as e:
        import urllib.parse
        encoded_message = urllib.parse.quote(str(e.detail))
        redirect_url = f"{settings.frontend_url}/verification/processing?type=name_update&status=error&message={encoded_message}&redirect_to=auth"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error in handle_verify_admin_name_update_controller: {e}")
        import urllib.parse
        encoded_message = urllib.parse.quote("Unexpected error while processing name confirmation.")
        redirect_url = f"{settings.frontend_url}/verification/processing?type=name_update&status=error&message={encoded_message}&redirect_to=auth"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


async def handle_verify_admin_phone_update_controller(token: str, user_id: str, db: AsyncSession, cache: redis.Redis):
    """Handles the completion of a phone number update via a verification link and redirects to frontend."""
    from fastapi.responses import RedirectResponse
    import urllib.parse

    try:
        service = UpdateAdminService(db, cache)
        result = await service.verify_phone_update(token, user_id)

        # On success, redirect to processing page that will show confirmation and redirect to auth
        if result.get("success"):
            redirect_url = f"{settings.frontend_url}/verification/processing?type=phone_update&status=success&redirect_to=auth"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        # Otherwise, redirect to processing page with error status
        message = urllib.parse.quote(result.get("message", "Unable to confirm phone update."))
        redirect_url = f"{settings.frontend_url}/verification/processing?type=phone_update&status=error&message={message}&redirect_to=auth"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except HTTPException as e:
        encoded_message = urllib.parse.quote(str(e.detail))
        redirect_url = f"{settings.frontend_url}/verification/processing?type=phone_update&status=error&message={encoded_message}&redirect_to=auth"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error in handle_verify_admin_phone_update_controller: {e}")
        encoded_message = urllib.parse.quote("Unexpected error while processing phone confirmation.")
        redirect_url = f"{settings.frontend_url}/verification/processing?type=phone_update&status=error&message={encoded_message}&redirect_to=auth"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

async def handle_verify_admin_email_update_controller(user_data: UpdateEmailVerifyTokenRequest, db: AsyncSession, cache: redis.Redis):
    """Controller for POST /v1/admins/verify-email-update (Super Admin Token Confirmation)."""
    # NOTE:  The public frontend route for email verification typically only receives the token.
    # The logic here assumes a simplified flow where the frontend URL passes back user_id, new_email, and token.
    try:
        service = UpdateAdminService(db, cache)
        result = await service.verify_email_update(user_data)
        return JSONResponse(content=result, status_code=result.get("status_code", status.HTTP_200_OK))
    except HTTPException as e:
        return JSONResponse(content=ResponseBuilder.error(e.detail, [e.detail], status_code=e.status_code), status_code=e.status_code)
    except Exception as e:
        logger.error(f"Error in handle_verify_admin_email_update_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Internal server error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

async def handle_approve_email_update_controller(token: str, user_id: str, db: AsyncSession, cache: redis.Redis):
    """Controller for GET /v1/admins/approve-email-update (Existing email approval step)."""
    from fastapi.responses import RedirectResponse
    import urllib.parse

    redirect_base = settings.frontend_url

    try:
        service = UpdateAdminService(db, cache)
        result = await service.approve_email_update(token, user_id)

        if result.get("success"):
            new_email = result.get("data", {}).get("new_email", "")
            redirect_url = f"{redirect_base}/auth?status=email_transfer_approved"
            if new_email:
                redirect_url += f"&new_email={urllib.parse.quote(new_email)}"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

        message = result.get("message", "Unable to process approval.")
        encoded_message = urllib.parse.quote(message)
        redirect_url = f"{redirect_base}/auth?status=email_transfer_error&message={encoded_message}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except HTTPException as e:
        encoded_message = urllib.parse.quote(str(e.detail))
        redirect_url = f"{redirect_base}/auth?status=email_transfer_error&message={encoded_message}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error in handle_approve_email_update_controller: {e}")
        encoded_message = urllib.parse.quote("Unexpected error while processing approval.")
        redirect_url = f"{redirect_base}/auth?status=email_transfer_error&message={encoded_message}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

async def handle_complete_email_update_controller(token: str, user_id: str, new_email: str, db: AsyncSession, cache: redis.Redis):
    """
    Controller to handle the final verification GET request from the email link.
    ...
    """
    from fastapi.responses import RedirectResponse
    import urllib.parse 
    
    # CRITICAL FIX: Create the Pydantic model needed by the service
    request_data = UpdateEmailVerifyTokenRequest(user_id=user_id, token=token, new_email=new_email)
    
    # Use the correct variable name for the frontend URL (settings.frontend_url)
    FRONTEND_REDIRECT_URL = settings.frontend_url # <-- FIXED VARIABLE NAME
    
    try:
        service = UpdateAdminService(db, cache)
        
        # This call now runs the DB update and revocation
        verification_result = await service.verify_email_update(request_data) 
        
        # Success: Redirect to the frontend login with a success/status message
        if verification_result.get("success"):
            # Use query params to inform the frontend of success and the new email
            status_url = f"{FRONTEND_REDIRECT_URL}/auth?status=email_updated&new_email={urllib.parse.quote(new_email)}"
            return RedirectResponse(url=status_url, status_code=status.HTTP_302_FOUND)
        
    except HTTPException as e:
        logger.error(f"HTTPException during email update for user {user_id}: {e.detail}")
        # Failure: Redirect to the frontend login with an error message
        error_message = f"Verification failed: {e.detail}"
        # Use URL encoding for the error message
        encoded_message = urllib.parse.quote(error_message)
        
        error_url = f"{FRONTEND_REDIRECT_URL}/auth?status=error&message={encoded_message}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    
    except Exception as e:
        logger.error(f"FATAL Exception during email update for user {user_id}: {e}")
        # Catch-all: Redirect to frontend with a generic error
        error_message = "Unexpected verification error (Check backend logs for details)."
        encoded_message = urllib.parse.quote(error_message)
        
        error_url = f"{FRONTEND_REDIRECT_URL}/auth?status=error&message={encoded_message}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)
    
    return JSONResponse(content=ResponseBuilder.server_error("Unknown verification error"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- TOKEN/COOKIE HANDLERS ---
    
async def handle_check_cookie_controller(request: Request, db: AsyncSession) -> JSONResponse:

    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    SECRET_KEY = settings.secret_key
    ALGORITHM = settings.algorithm

    def decode_token(token):
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    payload = None
    
    try:
        if access_token:
            payload = decode_token(access_token)
        elif refresh_token:
            payload = decode_token(refresh_token)
        else:
            return JSONResponse(content=ResponseBuilder.error(
                "No valid tokens found in cookies.", 
                ["Authentication token missing."], 
                status_code=status.HTTP_401_UNAUTHORIZED
            ), status_code=status.HTTP_401_UNAUTHORIZED)

    except ExpiredSignatureError:
        return JSONResponse(content=ResponseBuilder.error(
            "Session expired. Please log in again.", 
            ["Token expired."], 
            status_code=status.HTTP_401_UNAUTHORIZED
        ), status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        return JSONResponse(content=ResponseBuilder.error(
            "Invalid token signature.", 
            ["Token is invalid."], 
            status_code=status.HTTP_403_FORBIDDEN
        ), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        logger.error(f"Token processing error in handle_check_cookie_controller: {e}")
        return JSONResponse(content=ResponseBuilder.server_error(f"Token processing error: {e}"), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    user_id = payload.get("sub")
    user_role = payload.get("role")  # Get role from JWT token

    token_first = payload.get("fn")
    token_last = payload.get("ln")

    first_name = token_first
    last_name = token_last

    user = None
    if not first_name or not last_name:
        try:
            if user_id:
                user = await get_user_by_id(db, user_id)
                if user:
                    first_name = user.first_name
                    last_name = user.last_name
        except Exception as e:
            logger.warning(f"Failed to fetch user details from DB in handle_check_cookie: {e}")
            user = None

    user_data = {
        "is_authenticate": True,
        "first_name": first_name if first_name else "Authenticated",
        "last_name": last_name if last_name else "User",
        "user_id": user_id,
        "role": user_role  # Return role instead of user_type
    }

    return JSONResponse(content=ResponseBuilder.success(
        "Token is valid.",
        user_data,
        status_code=status.HTTP_200_OK
    ), status_code=status.HTTP_200_OK)

async def handle_logout_controller(response: Response, request: Request, cache: redis.Redis) -> JSONResponse:
    """
    Controller for /auth/logout. Invalidates both access and refresh tokens
    by blocking their JTI and deletes cookies.
    """
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    SECRET_KEY = settings.secret_key
    ALGORITHM = settings.algorithm
    
    # Function to decode, extract JTI, calculate lifespan, and block the JTI
    def revoke_token_by_jti(token):
        """Calculates token lifespan and adds the JTI to the Redis blocklist."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            exp_timestamp = payload.get("exp")
            
            if jti and exp_timestamp:
                # Calculate remaining time in seconds until expiry
                time_until_expiry = int(exp_timestamp - datetime.timestamp(datetime.now(timezone.utc)))
                
                if time_until_expiry > 0:
                    # Use the JTI-based blocklist function
                    return add_jti_to_blocklist(jti, cache, time_until_expiry)
        except (JWTError, ExpiredSignatureError):
            # If the token is already expired or invalid, we ignore it.
            pass 
            
    tasks = []
    if access_token:
        tasks.append(revoke_token_by_jti(access_token))
    if refresh_token:
        tasks.append(revoke_token_by_jti(refresh_token))
    
    # Execute revocation tasks concurrently
    if tasks:
        # Await the coroutines created by revoke_token_by_jti
        # Filter out Nones as revoke_token_by_jti returns None on failure/expiry
        await asyncio.gather(*[t for t in tasks if t is not None]) 

    # Delete cookies regardless of token revocation success
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    
    return JSONResponse(content=ResponseBuilder.success("Successfully logged out"), status_code=status.HTTP_200_OK)
