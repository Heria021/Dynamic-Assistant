from fastapi import Depends
from app.database import get_database
from app.controllers.agent import AgentController

def get_agent_controller():
    db = get_database()
    return AgentController(db)