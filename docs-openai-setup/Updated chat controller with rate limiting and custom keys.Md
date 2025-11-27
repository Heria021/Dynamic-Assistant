"""
app/controllers/chats.py - Updated chat controller with rate limiting and custom keys
"""

from fastapi import UploadFile, HTTPException, status
from app.helpers.openai_helper import OpenAIHelper
from app.services.openai_key_manager import OpenAIKeyManager
from app.services.rate_limiter import RateLimiter
from typing import List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ChatController:
    def __init__(self, db):
        self.db = db
        self.users_collection = db["users"]
        self.assistants_collection = db["assistants"]
        self.threads_collection = db["threads"]
        self.chats_collection = db["chats"]
    
    async def create_chat(
        self,
        astId: str,
        threadId: str,
        message: str,
        current_user: dict,
        image: Optional[List[UploadFile]] = None
    ):
        """
        Create a new chat message with rate limiting and custom OpenAI key support.
        """
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # ====================================================================
        # STEP 1: Rate Limiting Check
        # ====================================================================
        rate_limiter = RateLimiter(self.db)
        
        # Check message limits
        can_send, reason = await rate_limiter.check_message_limit(user_id)
        if not can_send:
            logger.warning(f"User {user_id} hit rate limit: {reason}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": reason,
                    "suggestions": [
                        "Wait for your daily/weekly limit to reset",
                        "Upgrade to a higher tier plan",
                        "Add your own OpenAI API key for unlimited messages"
                    ]
                }
            )
        
        # Check token limit
        can_use_tokens, token_reason = await rate_limiter.check_token_limit(user_id)
        if not can_use_tokens:
            logger.warning(f"User {user_id} exceeded token limit: {token_reason}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "TOKEN_LIMIT_EXCEEDED",
                    "message": token_reason,
                    "suggestions": [
                        "Add your own OpenAI API key to bypass token limits",
                        "Wait for monthly reset",
                        "Use a more efficient model (gpt-4o-mini)"
                    ]
                }
            )
        
        # ====================================================================
        # STEP 2: Get Assistant and OpenAI Key
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
        
        # Get appropriate OpenAI key
        key_manager = OpenAIKeyManager(self.db)
        openai_key, is_custom_key = await key_manager.get_key_for_request(
            user_id=user_id,
            assistant_id=astId
        )
        
        if not openai_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No OpenAI API key available"
            )
        
        logger.info(
            f"User {user_id} sending message to assistant {astId} "
            f"using {'custom' if is_custom_key else 'system'} key"
        )
        
        # ====================================================================
        # STEP 3: Verify Thread
        # ====================================================================
        thread = await self.threads_collection.find_one({
            "threadId": threadId,
            "userId": user_id,
            "astId": astId
        })
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or doesn't belong to this assistant"
            )
        
        # ====================================================================
        # STEP 4: Process Images (if any)
        # ====================================================================
        image_data_list = []
        if image:
            try:
                import base64
                for img_file in image:
                    contents = await img_file.read()
                    base64_image = base64.b64encode(contents).decode('utf-8')
                    image_data_list.append({
                        "filename": img_file.filename,
                        "data": base64_image,
                        "content_type": img_file.content_type
                    })
            except Exception as e:
                logger.error(f"Error processing images: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to process images: {str(e)}"
                )
        
        # ====================================================================
        # STEP 5: Send Message to OpenAI
        # ====================================================================
        try:
            # Initialize OpenAI helper with custom key
            openai_helper = OpenAIHelper(api_key=openai_key)
            
            # Add message to thread and run assistant
            response = await openai_helper.create_message_and_run(
                thread_id=threadId,
                assistant_id=assistant["astId"],
                message=message,
                images=image_data_list
            )
            
            assistant_response = response.get("response", "")
            tokens_used = response.get("tokens_used", 0)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get response from assistant: {str(e)}"
            )
        
        # ====================================================================
        # STEP 6: Increment Rate Limit Counters
        # ====================================================================
        await rate_limiter.increment_message_count(user_id)
        
        # ====================================================================
        # STEP 7: Track Token Usage
        # ====================================================================
        if tokens_used > 0:
            await rate_limiter.track_token_usage(
                user_id=user_id,
                tokens_used=tokens_used,
                assistant_id=astId,
                thread_id=threadId,
                model=assistant.get("gptModel", "gpt-4o-mini")
            )
            
            # Update usage history with custom key flag
            await self.db["usage_history"].update_one(
                {
                    "userId": user_id,
                    "assistantId": astId,
                    "threadId": threadId,
                    "timestamp": {"$gte": datetime.utcnow()}
                },
                {
                    "$set": {
                        "metadata.used_custom_key": is_custom_key,
                        "assistantName": assistant.get("astName")
                    }
                },
                upsert=False
            )
        
        # ====================================================================
        # STEP 8: Save Chat to Database
        # ====================================================================
        chat_document = {
            "userId": user_id,
            "astId": astId,
            "threadId": threadId,
            "userMessage": message,
            "assistantResponse": assistant_response,
            "images": image_data_list if image_data_list else None,
            "tokens_used": tokens_used,
            "used_custom_key": is_custom_key,
            "createdAt": datetime.utcnow()
        }
        
        result = await self.chats_collection.insert_one(chat_document)
        
        # ====================================================================
        # STEP 9: Return Response
        # ====================================================================
        return {
            "status": True,
            "message": "Chat created successfully",
            "data": {
                "chat_id": str(result.inserted_id),
                "user_message": message,
                "assistant_response": assistant_response,
                "tokens_used": tokens_used,
                "used_custom_key": is_custom_key,
                "images_count": len(image_data_list) if image_data_list else 0,
                "timestamp": datetime.utcnow()
            }
        }
    
    async def get_chat_history(
        self,
        threadId: str,
        current_user: dict,
        limit: int = 50
    ):
        """Get chat history for a thread"""
        user_id = current_user.get("sub") or current_user.get("user_id")
        
        # Verify thread ownership
        thread = await self.threads_collection.find_one({
            "threadId": threadId,
            "userId": user_id
        })
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )
        
        # Get chats
        cursor = self.chats_collection.find({
            "threadId": threadId,
            "userId": user_id
        }).sort("createdAt", -1).limit(limit)
        
        chats = await cursor.to_list(length=limit)
        
        # Reverse to get chronological order
        chats.reverse()
        
        return {
            "status": True,
            "data": {
                "thread_id": threadId,
                "total_messages": len(chats),
                "messages": chats
            }
        }