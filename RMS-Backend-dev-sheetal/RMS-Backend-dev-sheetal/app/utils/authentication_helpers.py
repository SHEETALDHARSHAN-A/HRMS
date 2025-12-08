# app/utils/authentication_helpers.py

from fastapi import HTTPException, status
from email_validator import validate_email, EmailNotValidError

def is_valid_email(email: str) -> bool:
    try:
        # Skip deliverability checks to avoid DNS/network dependency during tests
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False
        
def validate_input_email(email: str):
    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )