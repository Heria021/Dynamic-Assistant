from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.controllers.chats import ChatController
from app.database.db import get_database
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


def get_chat_controller(db=Depends(get_database)):
    return ChatController(db)


@router.post("/create-chat")
async def create_chat(
    astId: str = Form(...),
    threadId: str = Form(...),
    message: str = Form(...),
    image: List[UploadFile] | None = File(None),
    user: dict = Depends(get_current_user),
    controller: ChatController = Depends(get_chat_controller),
):
    return await controller.create_chat(astId, threadId, message, user, image)


@router.get("/history/{thread_id}")
async def get_chat_history(
    thread_id: str,
    limit: int = 50,
    user: dict = Depends(get_current_user),
    controller: ChatController = Depends(get_chat_controller),
):
    return await controller.get_chat_history(thread_id, user, limit)
