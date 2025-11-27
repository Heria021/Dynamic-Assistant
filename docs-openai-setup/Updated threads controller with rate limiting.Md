"""
app/controllers/threads.py - Updated threads controller with rate limiting
"""

from fastapi import HTTPException, status
from app.helpers.openai_helper import OpenAIHelper
from app.services.rate_limiter import RateLimiter
from app.services.openai_key_manager import OpenAIKeyManager
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ThreadController:
    def __init__(self, db):
        self.db = db
        self.assistants_collection = db["assistants"]
        self.threads_collection = db["threads"]
    
    async def create_thread(
        self,
        astId: str,
        threadTitle: str,
        current_user: dict
    ):
        """
        Create a new conversation thread with rate limit check.
        """
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # ====================================================================
        # STEP 1: Verify Assistant Exists
        # ====================================================================
        assistant = await self.assistants_collection.find_one({
            "_id": astId,
            "userId": user_id
        })
        
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found or you don't have permission"
            )
        
        # ====================================================================
        # STEP 2: Check Thread Limit for This Assistant
        # ====================================================================
        rate_limiter = RateLimiter(self.db)
        
        can_create, reason = await rate_limiter.check_thread_limit(
            user_id=user_id,
            assistant_id=astId
        )
        
        if not can_create:
            logger.warning(f"User {user_id} hit thread limit for assistant {astId}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "THREAD_LIMIT_EXCEEDED",
                    "message": reason,
                    "assistant_id": astId,
                    "assistant_name": assistant.get("astName"),
                    "suggestions": [
                        "Delete unused threads for this assistant",
                        "Upgrade to higher tier for more threads per assistant"
                    ]
                }
            )
        
        # ====================================================================
        # STEP 3: Get OpenAI Key
        # ====================================================================
        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id,
            assistant_id=astId
        )
        
        if not openai_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No OpenAI API key available"
            )
        
        # ====================================================================
        # STEP 4: Create Thread in OpenAI
        # ====================================================================
        try:
            openai_helper = OpenAIHelper(api_key=openai_key)
            thread_data = await openai_helper.create_thread()
            thread_id = thread_data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to create thread in OpenAI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create thread: {str(e)}"
            )
        
        # ====================================================================
        # STEP 5: Save to Database
        # ====================================================================
        thread_document = {
            "threadId": thread_id,
            "userId": user_id,
            "astId": astId,
            "threadTitle": threadTitle,
            "message_count": 0,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = await self.threads_collection.insert_one(thread_document)
        thread_document["_id"] = str(result.inserted_id)
        
        # ====================================================================
        # STEP 6: Increment Thread Counter
        # ====================================================================
        await rate_limiter.increment_thread_count(user_id)
        
        # Update assistant's thread count
        await self.assistants_collection.update_one(
            {"_id": astId},
            {
                "$inc": {"usage_stats.total_threads": 1},
                "$set": {"updatedAt": datetime.utcnow()}
            }
        )
        
        # Log to usage history
        await self.db["usage_history"].insert_one({
            "userId": user_id,
            "assistantId": astId,
            "threadId": thread_id,
            "action": "thread_created",
            "tokens_used": 0,
            "timestamp": datetime.utcnow(),
            "metadata": {
                "thread_title": threadTitle,
                "assistant_name": assistant.get("astName")
            }
        })
        
        logger.info(f"User {user_id} created thread for assistant {astId}")
        
        return {
            "status": True,
            "message": "Thread created successfully",
            "data": thread_document
        }
    
    async def get_threads_by_assistant(
        self,
        assistant_id: str,
        current_user: dict
    ):
        """Get all threads for a specific assistant"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Verify assistant ownership
        assistant = await self.assistants_collection.find_one({
            "_id": assistant_id,
            "userId": user_id
        })
        
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found"
            )
        
        # Get threads
        cursor = self.threads_collection.find({
            "astId": assistant_id,
            "userId": user_id
        }).sort("updatedAt", -1)
        
        threads = await cursor.to_list(length=1000)
        
        # Convert ObjectId to string
        for thread in threads:
            thread["_id"] = str(thread["_id"])
        
        return {
            "status": True,
            "data": {
                "assistant_id": assistant_id,
                "assistant_name": assistant.get("astName"),
                "total_threads": len(threads),
                "threads": threads
            }
        }
    
    async def get_thread_history(
        self,
        thread_id: str,
        current_user: dict
    ):
        """Get message history for a thread"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Verify thread ownership
        thread = await self.threads_collection.find_one({
            "threadId": thread_id,
            "userId": user_id
        })
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        
        # Get OpenAI key
        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id,
            assistant_id=thread.get("astId")
        )
        
        # Get messages from OpenAI
        try:
            openai_helper = OpenAIHelper(api_key=openai_key)
            messages = await openai_helper.get_thread_messages(thread_id)
            
        except Exception as e:
            logger.error(f"Failed to get thread messages: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve messages: {str(e)}"
            )
        
        return {
            "status": True,
            "data": {
                "thread_id": thread_id,
                "thread_title": thread.get("threadTitle"),
                "messages": messages,
                "message_count": len(messages)
            }
        }
    
    async def delete_thread(
        self,
        thread_id: str,
        current_user: dict
    ):
        """Delete a thread"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Verify ownership
        thread = await self.threads_collection.find_one({
            "threadId": thread_id,
            "userId": user_id
        })
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        
        # Delete from OpenAI
        try:
            key_manager = OpenAIKeyManager(self.db)
            openai_key, _ = await key_manager.get_key_for_request(
                user_id=user_id,
                assistant_id=thread.get("astId")
            )
            
            openai_helper = OpenAIHelper(api_key=openai_key)
            await openai_helper.delete_thread(thread_id)
            
        except Exception as e:
            logger.warning(f"Failed to delete thread from OpenAI: {e}")
            # Continue with database deletion
        
        # Delete from database
        await self.threads_collection.delete_one({"threadId": thread_id})
        
        # Decrement counters
        await self.db["users"].update_one(
            {"_id": user_id},
            {"$inc": {"usage.threads_created": -1}}
        )
        
        await self.assistants_collection.update_one(
            {"_id": thread.get("astId")},
            {"$inc": {"usage_stats.total_threads": -1}}
        )
        
        logger.info(f"User {user_id} deleted thread {thread_id}")
        
        return {
            "status": True,
            "message": "Thread deleted successfully"
        }