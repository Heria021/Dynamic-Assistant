from fastapi import APIRouter,UploadFile,Depends,Form,File, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import app.controllers.chats as controller
import app.models.model_types as model_type
from app.controllers.auth_controller import AuthController
from app.config import settings
from typing import *

router = APIRouter()

# JWT-based dependency (same as assistant router)
security = HTTPBearer()
auth_controller = AuthController(settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)

def get_current_user_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = auth_controller.verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return {"login_id": payload["sub"], "email": payload.get("email")}


@router.post("/create-chat")
async def create_chat(
    astId: str = Form(...),
    threadId: str = Form(...),
    message: str = Form(...),
    user: dict = Depends(get_current_user_jwt),
    image: List[UploadFile] = File(None),
):
    userId = user.get('login_id')
    # Create an instance of AssistantChat
    chat_instance = model_type.AssistantChat(
        userId=userId,
        astId=astId,
        threadId=threadId,
        message=message
    )
    content = await controller.process_chat_content([chat_instance], image)
    created_response = await controller.create_new_chat([chat_instance], content)
    response = {
        "status": True,
        "message": "Chat created successfully",
        "data": created_response
    }

    return response
