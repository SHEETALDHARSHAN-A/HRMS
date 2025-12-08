# app/utils/standard_response_utils.py

from fastapi import status
from typing import Any, List, Optional

class ResponseBuilder:
    @staticmethod
    def success(
        message: str,
        data: Any = None,
        status_code: int = status.HTTP_200_OK
    ):
        return {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
        }

    @staticmethod
    def created(message: str, data: Any = None):
        return ResponseBuilder.success(
            message=message,
            data=data,
            status_code=status.HTTP_201_CREATED
        )
 
    @staticmethod
    def error(
        message: str,
        errors: Optional[List[str]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        # Make errors optional for convenience; if not provided, include the
        # main message as the sole error entry.
        if errors is None:
            errors = [message]
        return {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": None,
            "errors": errors or []
        }
 
    @staticmethod
    def not_found(message: str = "Resource not found"):
        return ResponseBuilder.error(
            message=message,
            errors=[message],
            status_code=status.HTTP_404_NOT_FOUND
        )
 
    @staticmethod
    def conflict(message: str = "Resource already exists"):
        return ResponseBuilder.error(
            message=message,
            errors=[message],
            status_code=status.HTTP_409_CONFLICT
        )
 
    @staticmethod
    def server_error(message: str = "Internal server error"):
        return ResponseBuilder.error(
            message=message,
            errors=[message],
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Lightweight response container used by services/tests that expect an
# object named `StandardResponse` to be importable from this module.
class StandardResponse:
    def __init__(self, *, success: bool, status_code: int = status.HTTP_200_OK, message: str = "", data: Any = None, errors: Optional[List[str]] = None):
        self.success = success
        self.status_code = status_code
        self.message = message
        self.data = data
        self.errors = errors or ([] if not success else None)

    def to_dict(self):
        return {
            "success": self.success,
            "status_code": self.status_code,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
        }