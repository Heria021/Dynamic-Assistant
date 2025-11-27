from fastapi import APIRouter, Depends

import app.models.model_types as model_type
from app.controllers.threads import ThreadController
from app.database.db import get_database
from app.middleware.auth_middleware import get_current_user

router = APIRouter()


def get_thread_controller(db=Depends(get_database)):
    return ThreadController(db)


@router.post("/create-thread")
async def create_thread(
    thread: model_type.AssistantThread,
    user: dict = Depends(get_current_user),
    controller: ThreadController = Depends(get_thread_controller),
):
    return await controller.create_thread(thread, user)

@router.get("/get-thread/{assistant_id}")
async def get_all_thread(
    assistant_id: str,
    user: dict = Depends(get_current_user),
    controller: ThreadController = Depends(get_thread_controller),
):
    return await controller.get_threads_by_assistant(assistant_id, user)

@router.get("/get-thread-history/{thread_id}")
async def get_thread_history_by_id(
    thread_id: str,
    user: dict = Depends(get_current_user),
    controller: ThreadController = Depends(get_thread_controller),
):
    return await controller.get_thread_history(thread_id, user)

