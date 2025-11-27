"""
app/controllers/assistant.py - Updated assistant controller with rate limiting
"""

from fastapi import HTTPException, status, UploadFile
from app.helpers.openai_helper import OpenAIHelper
from app.services.rate_limiter import RateLimiter
from app.services.openai_key_manager import OpenAIKeyManager
from typing import List, Optional
import logging
from datetime import datetime
import secrets

logger = logging.getLogger(__name__)


class AssistantController:
    def __init__(self, db):
        self.db = db
        self.assistants_collection = db["assistants"]
    
    async def create_assistant(
        self,
        astName: str,
        astInstruction: str,
        gptModel: str,
        astTools: List[str],
        current_user: dict,
        files: Optional[List[UploadFile]] = None
    ):
        """
        Create a new assistant with rate limit check.
        """
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # ====================================================================
        # STEP 1: Check Assistant Creation Limit
        # ====================================================================
        rate_limiter = RateLimiter(self.db)
        
        can_create, reason = await rate_limiter.check_assistant_limit(user_id)
        if not can_create:
            logger.warning(f"User {user_id} hit assistant limit: {reason}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "ASSISTANT_LIMIT_EXCEEDED",
                    "message": reason,
                    "suggestions": [
                        "Delete unused assistants",
                        "Upgrade to a higher tier plan for more assistants"
                    ]
                }
            )
        
        # ====================================================================
        # STEP 2: Get OpenAI Key
        # ====================================================================
        key_manager = OpenAIKeyManager(self.db)
        openai_key = await key_manager.get_user_key(user_id)
        
        if not openai_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No OpenAI API key available"
            )
        
        # ====================================================================
        # STEP 3: Create Assistant in OpenAI
        # ====================================================================
        try:
            openai_helper = OpenAIHelper(api_key=openai_key)
            
            # Process files if provided
            file_ids = []
            if files:
                for file in files:
                    file_id = await openai_helper.upload_file(file)
                    file_ids.append(file_id)
            
            # Create assistant
            assistant_data = await openai_helper.create_assistant(
                name=astName,
                instructions=astInstruction,
                model=gptModel,
                tools=astTools,
                file_ids=file_ids
            )
            
            assistant_id = assistant_data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to create assistant in OpenAI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create assistant: {str(e)}"
            )
        
        # ====================================================================
        # STEP 4: Generate API Token
        # ====================================================================
        api_token = secrets.token_urlsafe(32)
        
        # ====================================================================
        # STEP 5: Save to Database
        # ====================================================================
        assistant_document = {
            "userId": user_id,
            "astName": astName,
            "astInstruction": astInstruction,
            "gptModel": gptModel,
            "astTools": astTools,
            "astId": assistant_id,
            "apiToken": api_token,
            "file_ids": file_ids if file_ids else [],
            "usage_stats": {
                "total_messages": 0,
                "total_tokens": 0,
                "total_threads": 0,
                "last_used": None
            },
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = await self.assistants_collection.insert_one(assistant_document)
        assistant_document["_id"] = str(result.inserted_id)
        
        # ====================================================================
        # STEP 6: Increment Assistant Counter
        # ====================================================================
        await rate_limiter.increment_assistant_count(user_id)
        
        # Log to usage history
        await self.db["usage_history"].insert_one({
            "userId": user_id,
            "assistantId": str(result.inserted_id),
            "action": "assistant_created",
            "tokens_used": 0,
            "model_used": gptModel,
            "cost_estimate": 0.0,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "assistant_name": astName,
                "tools": astTools
            }
        })
        
        logger.info(f"User {user_id} created assistant {astName}")
        
        return {
            "status": True,
            "message": "Assistant created successfully",
            "data": assistant_document
        }
    
    async def get_assistants(self, current_user: dict):
        """Get all assistants for a user"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        cursor = self.assistants_collection.find({
            "userId": user_id
        }).sort("createdAt", -1)
        
        assistants = await cursor.to_list(length=1000)
        
        # Convert ObjectId to string
        for assistant in assistants:
            assistant["_id"] = str(assistant["_id"])
        
        return {
            "status": True,
            "data": assistants
        }
    
    async def get_assistant_by_id(
        self,
        assistant_id: str,
        current_user: dict
    ):
        """Get a specific assistant"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        assistant = await self.assistants_collection.find_one({
            "_id": assistant_id,
            "userId": user_id
        })
        
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found"
            )
        
        assistant["_id"] = str(assistant["_id"])
        
        return {
            "status": True,
            "data": assistant
        }
    
    async def update_assistant(
        self,
        assistant_id: str,
        astName: Optional[str] = None,
        astInstruction: Optional[str] = None,
        gptModel: Optional[str] = None,
        astTools: Optional[List[str]] = None,
        current_user: dict = None
    ):
        """Update an assistant"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Verify ownership
        assistant = await self.assistants_collection.find_one({
            "_id": assistant_id,
            "userId": user_id
        })
        
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found"
            )
        
        # Get OpenAI key
        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id,
            assistant_id=assistant_id
        )
        
        # Update in OpenAI
        try:
            openai_helper = OpenAIHelper(api_key=openai_key)
            
            update_data = {}
            if astName:
                update_data["name"] = astName
            if astInstruction:
                update_data["instructions"] = astInstruction
            if gptModel:
                update_data["model"] = gptModel
            if astTools:
                update_data["tools"] = astTools
            
            await openai_helper.update_assistant(
                assistant_id=assistant["astId"],
                **update_data
            )
            
        except Exception as e:
            logger.error(f"Failed to update assistant in OpenAI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update assistant: {str(e)}"
            )
        
        # Update in database
        db_updates = {}
        if astName:
            db_updates["astName"] = astName
        if astInstruction:
            db_updates["astInstruction"] = astInstruction
        if gptModel:
            db_updates["gptModel"] = gptModel
        if astTools:
            db_updates["astTools"] = astTools
        
        db_updates["updatedAt"] = datetime.utcnow()
        
        await self.assistants_collection.update_one(
            {"_id": assistant_id},
            {"$set": db_updates}
        )
        
        logger.info(f"User {user_id} updated assistant {assistant_id}")
        
        return {
            "status": True,
            "message": "Assistant updated successfully",
            "data": {
                "assistant_id": assistant_id,
                "updates": db_updates
            }
        }
    
    async def delete_assistant(
        self,
        assistant_id: str,
        current_user: dict
    ):
        """Delete an assistant"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Verify ownership
        assistant = await self.assistants_collection.find_one({
            "_id": assistant_id,
            "userId": user_id
        })
        
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found"
            )
        
        # Delete from OpenAI
        try:
            key_manager = OpenAIKeyManager(self.db)
            openai_key, _ = await key_manager.get_key_for_request(
                user_id=user_id,
                assistant_id=assistant_id
            )
            
            openai_helper = OpenAIHelper(api_key=openai_key)
            await openai_helper.delete_assistant(assistant["astId"])
            
        except Exception as e:
            logger.warning(f"Failed to delete assistant from OpenAI: {e}")
            # Continue with database deletion even if OpenAI deletion fails
        
        # Delete from database
        await self.assistants_collection.delete_one({"_id": assistant_id})
        
        # Decrement counter
        await self.db["users"].update_one(
            {"_id": user_id},
            {"$inc": {"usage.assistants_created": -1}}
        )
        
        logger.info(f"User {user_id} deleted assistant {assistant_id}")
        
        return {
            "status": True,
            "message": "Assistant deleted successfully"
        }