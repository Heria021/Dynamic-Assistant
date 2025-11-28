from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.controllers.auth_controller import AuthController

security = HTTPBearer()
auth_controller = AuthController(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = auth_controller.verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {
        "sub": payload["sub"],
        "email": payload["email"],
        "role": payload.get("role", "owner"),
        "is_team_member": payload.get("is_team_member", False),
        "assigned_bots": payload.get("assigned_bots", [])
    }

