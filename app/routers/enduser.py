from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from typing import List, Optional
import secrets

from app.controllers.chats import ChatController
from app.controllers.threads import ThreadController
from app.models.model_types import AssistantThread
import app.utils.mongo_utils as mongo
from app.controllers.cognito import get_api_token
from app.database.db import get_database

router = APIRouter()


@router.post("/end-user-chat")
async def create_chat(
    astName: str = Form(...),
    apiToken: str = Form(...),
    threadtoken: Optional[str] = Form(None),
    message: str = Form(...),
    image: Optional[List[UploadFile]] = File(None),
    db=Depends(get_database),
):
    """
    Public endpoint for end-users to chat with assistants using apiToken authentication.
    No JWT token required - uses apiToken instead.
    """
    try:
        # Step 1: Get assistant ID from name using async db
        assistant_doc = await db["assistants"].find_one(
            {"astName": astName},
            projection={"_id": 0, "astId": 1, "userId": 1, "api_token": 1, "apiToken": 1},
            sort=[("createdAt", -1)]
        )
        if not assistant_doc:
            return {
                "status": False,
                "message": "Assistant not found with the given name",
                "data": None
            }
        
        astID = assistant_doc.get("astId")
        userId = assistant_doc.get("userId")
        
        if not astID:
            return {
                "status": False,
                "message": "Assistant ID not found",
                "data": None
            }
        
        # Step 2: Verify API token (check both field names)
        stored_token = assistant_doc.get("apiToken") or assistant_doc.get("api_token")
        if stored_token != apiToken:
            return {
                "status": False,
                "message": "Invalid API Token",
                "data": None
            }
        
        # Step 3: Verify we have userId
        if not userId:
            return {
                "status": False,
                "message": "Failed to get user ID for assistant",
                "data": None
            }
        
        # Step 4: Create user dict for controllers (they expect this format)
        current_user = {"sub": userId, "user_id": userId}
        
        # Step 5: Initialize controllers
        thread_controller = ThreadController(db)
        chat_controller = ChatController(db)
        
        # Step 6: Handle thread creation or retrieval
        thread_token = None
        if threadtoken is None:
            # Create new thread
            try:
                thread = AssistantThread(
                    astId=astID,
                    threadTitle=message[:100]  # Limit title length
                )
                thread_result = await thread_controller.create_thread(thread, current_user)
                
                # Extract thread ID from response
                if thread_result.get("status") and thread_result.get("data"):
                    threadID = thread_result["data"].get("threadId")
                    if not threadID:
                        return {
                            "status": False,
                            "message": "Failed to extract thread ID from creation response",
                            "data": None
                        }
                    
                    # Generate threadToken for end-user API (secure token for public access)
                    thread_token = secrets.token_urlsafe(32)
                    
                    # Update thread document with threadToken
                    await db["threads"].update_one(
                        {"threadId": threadID},
                        {"$set": {"threadToken": thread_token}}
                    )
                else:
                    return {
                        "status": False,
                        "message": "Failed to create thread",
                        "data": thread_result
                    }
            except HTTPException as e:
                return {
                    "status": False,
                    "message": f"Error creating thread: {e.detail}",
                    "data": None
                }
            except Exception as e:
                return {
                    "status": False,
                    "message": f"An error occurred while creating the thread: {str(e)}",
                    "data": None
                }
        else:
            # Use existing thread - get threadID from threadToken using async db
            thread_doc = await db["threads"].find_one(
                {"threadToken": threadtoken},
                projection={"_id": 0, "threadId": 1}
            )
            if not thread_doc:
                return {
                    "status": False,
                    "message": "Invalid thread token",
                    "data": None
                }
            threadID = thread_doc.get("threadId")
            if not threadID:
                return {
                    "status": False,
                    "message": "Thread ID not found for token",
                    "data": None
                }
            thread_token = threadtoken  # Return the same token
        
        # Step 7: Create chat message
        try:
            chat_result = await chat_controller.create_chat(
                astId=astID,
                threadId=threadID,
                message=message,
                current_user=current_user,
                image=image
            )
            
            response = {
                "status": True,
                "message": "Chat created successfully",
                "data": chat_result.get("data", {}),
                "threadtoken": thread_token
            }
            
            return response
            
        except HTTPException as e:
            return {
                "status": False,
                "message": f"Error creating chat: {e.detail}",
                "data": None
            }
        except Exception as e:
            return {
                "status": False,
                "message": f"An error occurred while creating the chat: {str(e)}",
                "data": None
            }
            
    except Exception as e:
        return {
            "status": False,
            "message": f"Unexpected error: {str(e)}",
            "data": None
        }

