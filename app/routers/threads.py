from fastapi import APIRouter,Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import app.controllers.threads as controller
import app.models.model_types as model_type
import app.models.response_model as response_model
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


@router.post("/create-thread")
async def create_thread(thread: model_type.AssistantThread,
    user: dict = Depends(get_current_user_jwt)):
    try:
        userId = user.get('login_id')
        created_thread = await controller.create_new_thread(userId,thread)
        response = {
            "status": True,
            "message": "Thread created successfully",
            "data": created_thread
        }
        return response
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred while creating the thread.{e}",
            "data": None
        }

@router.get("/get-thread/{assistant_id}")
async def get_all_thread(assistant_id: str,
    user: dict = Depends(get_current_user_jwt)):
    try:
        userId = user.get('login_id')
        thread_history = await controller.get_all_threads(userId,assistant_id)
        response = {
            "status": True,
            "message": "Thread fetched successfully",
            "data": thread_history
        }
        return response
    except Exception as e:
        return {
            "status": False,
            "message": "An error occurred while fetching the threads.",
            "data": None
        }

@router.get("/get-thread-history/{thread_id}")
async def get_thread_history_by_id(thread_id: str,
    user: dict = Depends(get_current_user_jwt)):
    try:
        thread_history = await controller.get_thread_history_by_id(thread_id)
        response = {
            "status": True,
            "message": "Thread history fetched successfully",
            "data": thread_history
        }   
        return response
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred while fetching the thread history.{e}",
            "data": None
        }

