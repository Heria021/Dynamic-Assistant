from fastapi import UploadFile
from pydantic import BaseModel
from pydantic import BaseModel, EmailStr, constr
from typing import *

class InitiatePasswordResetRequest(BaseModel):
    email: str


class ConfirmPasswordResetRequest(BaseModel):
    email: str
    confirmation_code: str
    new_password: constr(min_length=8)


class ConfirmUserRequest(BaseModel):
    email: str
    confirmation_code: str


class SignUpRequest(BaseModel):
    email: str
    password: constr(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class ResendVerificationRequest(BaseModel):
    email: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class Assistant(BaseModel):
    astName: str
    astInstruction: str
    gptModel: str
    astTools: list[str]


class UpdateAssistant(BaseModel):
    astId: str
    astName: str
    astInstruction: str
    gptModel: str
    astTools: list[str]


class AssistantWithFile(BaseModel):
    astName: str
    astInstruction: str
    gptModel: str
    astTools: list[str]
    file: UploadFile


class AssistantThread(BaseModel):
    astId: str
    threadTitle: str


class AssistantChat(BaseModel):
    astId: str
    threadId: str
    message: str


class AssistantFile(BaseModel):
    fileId: str
    fileName: str
    fileSize: str
    fileType: str

class UserProfile(BaseModel):
    User_name : str
    User_email : str
    OpenAPI_key : Optional[str] = None

class Channel(BaseModel):
    astName: str
    apiToken: str


# ============================================================================
# TEAM MEMBER REQUEST/RESPONSE MODELS
# ============================================================================

class SetPasswordRequest(BaseModel):
    email: Optional[str] = None
    token: str
    password: constr(min_length=8)


class TeamMemberLoginRequest(BaseModel):
    email: str
    password: str


class MagicLinkLoginRequest(BaseModel):
    token: str
