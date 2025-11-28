from fastapi import APIRouter, Depends, File, Form, UploadFile
from typing import List, Optional

import app.models.model_types as model_type
from app.controllers.assistant import AssistantController
from app.database.db import get_database
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


def get_assistant_controller(db=Depends(get_database)):
    return AssistantController(db)

@router.post("/create-assistant")
async def create_assistant(
    assistant: model_type.Assistant,
    user: dict = Depends(get_current_user),
    controller: AssistantController = Depends(get_assistant_controller),
):
    return await controller.create_assistant(assistant, user)

@router.post("/create-assistant-with-file")
async def create_assistant_with_file(
    files: List[UploadFile] = File(...),
    astName: str = Form(...),
    astInstruction: str = Form(...),
    gptModel: str = Form(...),
    astTools: str = Form(...),  # JSON string or comma-separated
    user: dict = Depends(get_current_user),
    controller: AssistantController = Depends(get_assistant_controller),
):
    # Parse astTools - can be JSON string or comma-separated
    import json
    try:
        tools_list = json.loads(astTools)
    except:
        # If not JSON, treat as comma-separated
        tools_list = [tool.strip() for tool in astTools.split(",") if tool.strip()]
    
    # Create Assistant model from form data
    assistant = model_type.Assistant(
        astName=astName,
        astInstruction=astInstruction,
        gptModel=gptModel,
        astTools=tools_list
    )
    
    return await controller.create_assistant(assistant, user, files)

@router.post("/upload-assistant-files/{ast_id}")
async def upload_assistant_files(
    ast_id: str,
    files: list[UploadFile],
    user: dict = Depends(get_current_user),
    controller: AssistantController = Depends(get_assistant_controller),
):
    return await controller.upload_assistant_files(ast_id, files, user)

@router.get("/get-assistant")
async def get_all_assistant(
    user: dict = Depends(get_current_user),
    controller: AssistantController = Depends(get_assistant_controller),
):
    return await controller.get_assistants(user)

@router.get("/get-assistant/{ast_id}")
async def get_all_assistant_by_id(
    ast_id: str,
    user: dict = Depends(get_current_user),
    controller: AssistantController = Depends(get_assistant_controller),
):
    return await controller.get_assistant_by_id(ast_id, user)

@router.put("/update-assistant")
async def update_assistant_with_file(
    assistant: model_type.UpdateAssistant,
    user: dict = Depends(get_current_user),
    controller: AssistantController = Depends(get_assistant_controller),
):
    return await controller.update_assistant(assistant, user)
