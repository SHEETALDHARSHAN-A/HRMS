"""Compatibility shim for tests that import from `app.controllers`.

This module delegates to the real implementation in
`app.api.v1.agent_config_routes` but adapts its behavior slightly for
tests that expect route functions to raise HTTPException directly when
validation fails.
"""
from typing import Any
from fastapi import HTTPException

from app.api.v1.agent_config_routes import update_agent_config_route as _update_agent_config_route


async def update_agent_config_route(job_id: str, request: Any, config_update: Any, db: Any = None):
	"""Delegate to the real route and re-raise HTTP-like error dicts as HTTPException.

	Some tests expect the route to raise an HTTPException for invalid
	input. The original implementation returns a ResponseBuilder dict
	when catching HTTPException; this wrapper converts that dict back
	into an actual HTTPException so older tests behave as expected.
	"""
	result = await _update_agent_config_route(job_id, request, config_update, db)

	# If the underlying implementation returned an error dict, raise
	# HTTPException to match previous expectations in tests.
	if isinstance(result, dict) and result.get("success") is False:
		status_code = result.get("status_code", 400)
		detail = result.get("message", "Bad request")
		raise HTTPException(status_code=status_code, detail=detail)

	return result


__all__ = ["update_agent_config_route"]
