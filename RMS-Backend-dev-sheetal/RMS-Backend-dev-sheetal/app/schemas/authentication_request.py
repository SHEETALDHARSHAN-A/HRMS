# app/schemas/authentication_request.py

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator

class SendOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(SendOTPRequest):
    otp: str
    
class VerifySignUpOTPRequest(VerifyOTPRequest):
    first_name: str
    last_name: Optional[str] = None

class AdminInviteRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: Optional[str] = None
    phone_number: Optional[str] = Field(None, description="Contact phone number for the invited admin.")
    role: str = Field(..., description="Role for the invited admin: SUPER_ADMIN, ADMIN, or HR")
    expiration_days: Optional[int] = Field(None, description="Optional number of days the invite link should remain valid.")
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['SUPER_ADMIN', 'ADMIN', 'HR']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of {allowed_roles}')
        return v

class DeleteAdminByEmailRequest(BaseModel):
    email: EmailStr

class DeleteAdminsBatchRequest(BaseModel):
    user_ids: List[str]

class AdminUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, description="New first name of the admin.")
    last_name: Optional[str] = Field(None, description="New last name of the admin.")
    new_email: Optional[EmailStr] = Field(None, description="New email for the admin. Triggers verification.")
    phone_number: Optional[str] = Field(None, description="Updated phone number for the admin.")
    expiration_days: Optional[int] = Field(None, description="Optional number of days confirmation links should remain valid when triggering updates.")
    role: Optional[str] = Field(None, description="Optional role update: SUPER_ADMIN, ADMIN, or HR")

    @validator('role')
    def validate_role(cls, v):
        if v is None:
            return v
        allowed_roles = ['SUPER_ADMIN', 'ADMIN', 'HR']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of {allowed_roles}')
        return v

class UpdateEmailVerifyRequest(BaseModel):
    user_id: str
    token: str 
    new_email: EmailStr

class UpdateEmailVerifyTokenRequest(BaseModel):
    user_id: str
    token: str
    new_email: EmailStr
