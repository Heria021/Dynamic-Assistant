from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import app.controllers.channels as controller
import app.models.model_types as model_type
from app.controllers.auth_controller import AuthController
from app.config import settings

# Use JWT-based dependency (same as assistant router)
security = HTTPBearer()
auth_controller = AuthController(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)

def get_current_user_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = auth_controller.verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return {"login_id": payload["sub"], "email": payload.get("email")}

router = APIRouter()

@router.post("/channels-ast-info")
async def get_ast_info(
    ast_ID:str,
    user: dict = Depends(get_current_user_jwt)
):
    data = await controller.ast_info(ast_ID)
    try:
        message = "Data fetched successfully"
        return {
            "status": True,
            "message": message,
            "data": data
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }
    
@router.post("/channels-api-integration")
async def api_integration(
    channel: model_type.Channel = Depends(),
    user: dict = Depends(get_current_user_jwt)
):
    data = await controller.api_integration(channel)
    try:
        message = "Data fetched successfully"
        return {
            "status": True,
            "message": message,
            "data": data
        }

    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }