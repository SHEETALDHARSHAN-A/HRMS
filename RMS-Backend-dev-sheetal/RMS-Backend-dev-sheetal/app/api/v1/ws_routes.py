# app/api/v1/ws_routes.py

import json
import asyncio

from fastapi import status
from jose import jwt, JWTError
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.redis_manager import RedisManager

ws_router = APIRouter(prefix="/ws", tags=["WebSocket"])


def _extract_token_from_websocket(websocket: WebSocket) -> str | None:
    """Try multiple locations for the token: query param, cookies, Authorization header."""
    # 1) Query param
    token = websocket.query_params.get("token")
    if token:
        return token

    # 2) Cookies (browser will send cookies automatically on WS upgrade)
    try:
        cookie_token = websocket.cookies.get("access_token") or websocket.cookies.get("authToken")
        if cookie_token:
            return cookie_token
    except Exception:
        # Some ASGI servers may not expose cookies; ignore if not present
        pass

    # 3) Authorization header
    auth_header = websocket.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()

    return None


@ws_router.websocket("/task-status/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: str):
    # Attempt to extract token from multiple locations (query/cookie/header)
    token = _extract_token_from_websocket(websocket)

    if not token:
        # Deny connection if no token found
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Validate JWT
    try:
        secret_key = websocket.app.state.jwt_secret_key
        algorithm = websocket.app.state.jwt_algorithm
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # At this point token is valid; accept the websocket
    await websocket.accept()

    # Brief welcome message (includes authenticated subject)
    try:
        await websocket.send_json({"message": "WebSocket connected", "task_id": task_id, "user": payload.get("sub")})
    except Exception:
        # Ignore send errors for welcome message
        pass

    # Subscribe to Redis status channel and forward messages for this task
    redis_client = None
    try:
        redis_client = RedisManager.get_client()
    except Exception as e:
        await websocket.send_json({"error": f"Redis unavailable: {e}"})
        await websocket.close()
        return

    pubsub = redis_client.pubsub()
    STATUS_CHANNEL = "ATS_JOB_STATUS"

    await pubsub.subscribe(STATUS_CHANNEL)

    try:
        # Listen for messages and forward those that match our task_id
        while True:
            # Use non-blocking get_message with a small timeout to allow WebSocket disconnect checks
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            # Check for new messages
            if message and message.get("type") == "message":
                raw = message.get("data")
                try:
                    # raw may already be a decoded string depending on redis client config
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    payload_msg = json.loads(raw)
                except Exception:
                    # If payload is not JSON, skip
                    continue

                # Some producers send `task` or `task_id` fields
                msg_task = payload_msg.get("task") or payload_msg.get("task_id") or payload_msg.get("taskId")
                if msg_task and str(msg_task) == str(task_id):
                    # Forward to client
                    try:
                        await websocket.send_json(payload_msg)
                    except Exception:
                        # If client disconnected, break and cleanup
                        break

            # Also check if client closed the connection
            try:
                # Non-blocking receive_text to detect closure; will raise if closed
                await asyncio.sleep(0)
            except Exception:
                break

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await pubsub.unsubscribe(STATUS_CHANNEL)
            await pubsub.close()
        except Exception:
            pass
