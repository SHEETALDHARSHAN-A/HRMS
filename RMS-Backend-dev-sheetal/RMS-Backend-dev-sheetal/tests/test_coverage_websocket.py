import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from app.api.v1 import ws_routes as ws_mod
from app.api.v1.ws_routes import websocket_task_status, _extract_token_from_websocket

def test_extract_token_priorities():
    # 1. Query param
    ws1 = MagicMock()
    ws1.query_params = {"token": "q_token"}
    assert _extract_token_from_websocket(ws1) == "q_token"
    
    # 2. Cookie
    ws2 = MagicMock()
    ws2.query_params = {}
    ws2.cookies = {"access_token": "c_token"}
    assert _extract_token_from_websocket(ws2) == "c_token"
    
    # 3. Header
    ws3 = MagicMock()
    ws3.query_params = {}
    ws3.cookies = {}
    ws3.headers = {"authorization": "Bearer h_token"}
    assert _extract_token_from_websocket(ws3) == "h_token"

@pytest.mark.asyncio
async def test_websocket_task_status_flow(monkeypatch):
    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.query_params = {"token": "valid.token"}
    # Mock app state for key
    mock_ws.app.state.jwt_secret_key = "secret"
    mock_ws.app.state.jwt_algorithm = "HS256"
    
    # Mock jwt decode on the actual module to avoid import-path resolution issues
    monkeypatch.setattr(ws_mod.jwt, "decode", lambda t, k, algorithms: {"sub": "u1"})
    
    # Mock Redis
    mock_redis = MagicMock()
    mock_pubsub = AsyncMock()
    mock_redis.pubsub.return_value = mock_pubsub
    monkeypatch.setattr(ws_mod.RedisManager, "get_client", lambda: mock_redis)
    
    # Mock pubsub message sequence: 
    # 1. message for this task
    # 2. message for another task (should be ignored)
    # 3. WebSocketDisconnect (simulated via side_effect on sleep)
    
    msg1 = {"type": "message", "data": json.dumps({"task_id": "t1", "status": "done"})}
    msg2 = {"type": "message", "data": json.dumps({"task_id": "other", "status": "processing"})}
    
    mock_pubsub.get_message.side_effect = [msg1, msg2, None]
    
    # Force disconnect loop
    with patch("asyncio.sleep", side_effect=[None, None, WebSocketDisconnect()]):
        await websocket_task_status(mock_ws, "t1")
    
    # Verify accept
    mock_ws.accept.assert_awaited()
    # Verify send_json called for msg1
    calls = mock_ws.send_json.await_args_list
    # Call 0 is welcome msg, Call 1 should be msg1
    assert len(calls) >= 2
    assert calls[1][0][0] == {"task_id": "t1", "status": "done"}