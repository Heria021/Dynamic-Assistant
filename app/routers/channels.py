from fastapi import APIRouter, Depends
import app.controllers.channels as controller
from app.controllers.cognito import get_current_user
import app.models.model_types as model_type

router = APIRouter()

@router.post("/channels-ast-info")
async def get_ast_info(
    ast_ID:str,
    user: dict = Depends(get_current_user)
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
    user: dict = Depends(get_current_user)
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