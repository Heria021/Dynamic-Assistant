from fastapi import APIRouter, UploadFile, Depends, File
import app.controllers.assistant as controller
import app.models.model_types as model_type
from app.controllers.cognito import get_current_user
router = APIRouter()

@router.post("/create-assistant")
async def create_assistant(assistant: model_type.Assistant,
                           user: dict = Depends(get_current_user)):
    try:
        userId = user.get('login_id')
        api_token = await controller.generate_api_token(userId)
        response = await controller.create_new_assistant(userId,assistant,api_token)
        return {
            "status": True,
            "message": "Assistant created successfully",
            "data": response
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }

@router.post("/create-assistant-with-file")
async def create_assistant_with_file(
    files: list[UploadFile],
    assistant: model_type.Assistant = Depends(),
    user: dict = Depends(get_current_user)
):
    try: 
        userId = user.get('login_id')
        api_token = await controller.generate_api_token(userId)
        new_assistant = await controller.create_new_assistant_with_file(userId,assistant,api_token ,files)
        return {
            "status": True,
            "message": "Assistant created successfully",
            "data": new_assistant,
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }

@router.post("/upload-assistant-files/{ast_id}")
async def upload_assistant_files(
    ast_id: str,
    files: list[UploadFile],
    user: dict = Depends(get_current_user)
):
    try:
        uploaded_files = await controller.upload_assistant_files(ast_id, files)
        return {
            "status": True,
            "message": "Files uploaded successfully",
            "data": uploaded_files
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }

@router.get("/get-assistant")
async def get_all_assistant(user: dict = Depends(get_current_user)):
    try:
        userId = user.get('login_id')
        chat_files = await controller.get_all_assistants(userId)
        return {
            "status": True,
            "message": "Assistants fetched successfully",
            "data": chat_files
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }

@router.get("/get-assistant/{ast_id}")
async def get_all_assistant_by_id(ast_id: str,
                                  user: dict = Depends(get_current_user)):
    try:
        userId = user.get('login_id')
        assistant = await controller.get_assistant_by_id(userId,ast_id)
        return {
            "status": True,
            "message": "Assistant fetched successfully",
            "data": assistant
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }

@router.put("/update-assistant")
async def update_assistant_with_file(
    assistant: model_type.UpdateAssistant,
    user: dict = Depends(get_current_user)
):
    try:
        userId = user.get('login_id')
        updated_assistant = await controller.update_assistant(userId,assistant)
        return {
            "status": True,
            "message": "Assistant updated successfully",
            "data": updated_assistant
        }
    except Exception as e:
        return {
            "status": False,
            "message": f"An error occurred: {e}",
            "data": None
        }
