from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class Action(BaseModel):
    type: str  # "handoff_to_human", "send_link", "send_email"
    data: Dict[str, Any]  # Flexible data based on action type


class ApiResponse(BaseModel):
        status: bool = False
        message: str = ""
        data: dict | list = None
        actions: Optional[List[Action]] = None  # NEW: Optional actions array
