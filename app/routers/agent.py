from fastapi import APIRouter, Depends
from app.controllers.agent import AgentController
from app.routers.auth import get_current_user  
from pydantic import BaseModel
from app.database.db import get_database

router = APIRouter(prefix="/api/agent", tags=["Agent"])


# Add the controller dependency here
async def get_agent_controller():
    # get_database from app.database.db is async and returns an AsyncIOMotorDatabase
    db = await get_database()
    return AgentController(db)

class SendMessageRequest(BaseModel):
    thread_id: str
    message: str


class CompleteHandoffRequest(BaseModel):
    thread_id: str
    notes: str = ""


@router.get("/pending-handoffs")
async def get_pending_handoffs(
    agent_user: dict = Depends(get_current_user),
    controller: AgentController = Depends(get_agent_controller)
):
    """Get all threads waiting for human agent."""
    return await controller.get_pending_handoffs(agent_user)


@router.post("/assign/{thread_id}")
async def assign_thread(
    thread_id: str,
    agent_user: dict = Depends(get_current_user),
    controller: AgentController = Depends(get_agent_controller)
):
    """Assign thread to current agent."""
    return await controller.assign_thread_to_agent(thread_id, agent_user)


@router.post("/send-message")
async def send_message(
    request: SendMessageRequest,
    agent_user: dict = Depends(get_current_user),
    controller: AgentController = Depends(get_agent_controller)
):
    """Send message as human agent."""
    return await controller.send_human_message(
        thread_id=request.thread_id,
        message=request.message,
        agent_user=agent_user
    )


@router.post("/complete-handoff")
async def complete_handoff(
    request: CompleteHandoffRequest,
    agent_user: dict = Depends(get_current_user),
    controller: AgentController = Depends(get_agent_controller)
):
    """Complete handoff and return thread to AI."""
    return await controller.complete_handoff(
        thread_id=request.thread_id,
        agent_user=agent_user,
        notes=request.notes
    )


@router.get("/my-threads")
async def get_my_threads(
    agent_user: dict = Depends(get_current_user),
    controller: AgentController = Depends(get_agent_controller)
):
    """Get threads currently assigned to me."""
    return await controller.get_my_active_threads(agent_user)