# app/authentication/jwt_middleware.py

from fastapi.responses import JSONResponse
from starlette.routing import compile_path
from jose import jwt, JWTError, ExpiredSignatureError
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.redis_manager import RedisManager 
from app.utils.authentication_utils import is_jti_revoked 
from app.authentication.protected_routes_config import EXCLUDED_ROUTES, ROLE_PROTECTED_ENDPOINTS

class JWTMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle JWT validation, token blocklist check (via JTI),
    and role-based access control for protected endpoints.
    """
    def __init__(self, app, excluded_routes=EXCLUDED_ROUTES, role_protected_endpoints=ROLE_PROTECTED_ENDPOINTS):
        super().__init__(app)
        self.excluded_routes = excluded_routes
        self.role_protected_endpoints = role_protected_endpoints

    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method
        root_path = request.scope.get("root_path", "")
        normalized_path = path

        if root_path and path.startswith(root_path):
            normalized_path = path[len(root_path):] or "/"

        # Check for excluded routes (exact match or pattern match)
        if method == "OPTIONS":
            return await call_next(request)
        
        # Check exact matches first
        if normalized_path in self.excluded_routes:
            return await call_next(request)
        
        for excluded_route in self.excluded_routes:
            if excluded_route.endswith('/') and normalized_path.startswith(excluded_route):
                return await call_next(request)
        

        try:
            token = request.cookies.get("access_token")
            is_refresh_token_used = False

            if not token:
                token = request.cookies.get("refresh_token")
                if token:
                    is_refresh_token_used = True

            if not token:
                auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
                if auth_header and auth_header.lower().startswith("bearer "):
                    token = auth_header.split(" ", 1)[1].strip()
                    # authorization header is not a refresh token
                    is_refresh_token_used = False

            # --- Temporary Access Check (e.g., during email update) ---
            user_id_param = request.query_params.get("user_id")
            if user_id_param:
                try:
                    redis_client = RedisManager.get_client()
                except ConnectionError:
                    redis_client = None
                temp_access_key = f"temp_access:{user_id_param}"
                if redis_client:
                    has_temp_access = await redis_client.get(temp_access_key)
                else:
                    has_temp_access = False
                if has_temp_access:
                    return await call_next(request)

            if not token:
                return JSONResponse(
                    {"detail": "Authentication token missing."},
                    status_code=403
                )
            
            # --- Token Decoding and JTI Check ---
            try:
                redis_client = RedisManager.get_client()
            except ConnectionError:
                return JSONResponse(
                    {"detail": "Server misconfiguration: Redis pool not initialized."},
                    status_code=500
                )
            secret_key = getattr(request.app.state, "jwt_secret_key", None)
            algorithm = getattr(request.app.state, "jwt_algorithm", None)

            if not secret_key or not algorithm:
                return JSONResponse(
                    {"detail": "Server misconfiguration: JWT settings missing."},
                    status_code=500
                )

            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[algorithm],
            )
            
            jti = payload.get("jti")
            if not jti:
                return JSONResponse(
                    {"detail": "Authentication failed: Token is missing required ID (JTI)."},
                    status_code=403
                )

            # Check for revocation using the JTI from the token
            try:
                revoked = await is_jti_revoked(jti, redis_client)
            except Exception as e:
                # Defensive: log and treat as not revoked to avoid 5xx errors
                print(f"Warning: JTI revocation check failed: {e}")
                revoked = False

            if revoked:
                return JSONResponse(
                    {"detail": "Token revoked. Please log in again."},
                    status_code=401
                )

            # Set user info on app state (used by dependency injection)

            request.state.user = payload

            # --- Role-Based Access Control ---
            for protected_path, allowed_roles in self.role_protected_endpoints.items():
                path_regex, _, _ = compile_path(protected_path)
                
                if path_regex.match(normalized_path):
                    user_role = payload.get("role")
                    
                    if not user_role or user_role not in allowed_roles:
                        return JSONResponse(
                            {"detail": "Access Denied."},
                            status_code=403
                        )
                    break 

            return await call_next(request)

        except ExpiredSignatureError:
            return JSONResponse({"detail": "Token expired."}, status_code=401)
        except JWTError:
            return JSONResponse({"detail": "Unauthorized: Invalid or expired token."}, status_code=401)
        except Exception as exc:
            import traceback
            print(f"Unexpected error in JWT middleware: {exc}")
            print(f"Traceback: {traceback.format_exc()}")
            return JSONResponse({"detail": f"Server error: {str(exc)}"}, status_code=500)