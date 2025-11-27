"""
app/routers/settings_router.py - New router for user settings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.auth_middleware import get_current_user
from app.database.db import get_database
from app.services.openai_key_manager import OpenAIKeyManager
from app.models.schemas import (
    OpenAIKeyUpdate,
    OpenAIKeyStatus
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["User Settings"])


# ============================================================================
# OpenAI Key Management
# ============================================================================

@router.post("/openai-key")
async def set_openai_key(
    key_update: OpenAIKeyUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Set a custom OpenAI API key for the authenticated user.
    This key will be used for all their assistants and messages.
    
    Benefits:
    - No rate limits (except OpenAI's own)
    - Full cost control
    - Use your own OpenAI credits
    - Better privacy
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    key_manager = OpenAIKeyManager(db)
    
    try:
        # Set the key
        success = await key_manager.set_user_key(user_id, key_update.api_key)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update API key"
            )
        
        logger.info(f"User {user_id} set custom OpenAI key")
        
        return {
            "status": True,
            "message": "OpenAI API key updated successfully. All your messages will now use your custom key.",
            "data": {
                "key_type": "custom",
                "active": True
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting OpenAI key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while setting the API key"
        )


@router.delete("/openai-key")
async def remove_openai_key(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Remove your custom OpenAI API key.
    You will fall back to the system default key with rate limits.
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    key_manager = OpenAIKeyManager(db)
    
    success = await key_manager.remove_user_key(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom API key found to remove"
        )
    
    logger.info(f"User {user_id} removed custom OpenAI key")
    
    return {
        "status": True,
        "message": "Custom API key removed. You are now using the system default key.",
        "data": {
            "key_type": "system",
            "rate_limits_apply": True
        }
    }


@router.get("/openai-key/status", response_model=OpenAIKeyStatus)
async def get_openai_key_status(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Check if you have a custom OpenAI key set.
    Does not return the actual key for security.
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    key_manager = OpenAIKeyManager(db)
    
    status_info = await key_manager.get_key_status(user_id)
    
    return OpenAIKeyStatus(**status_info)


@router.post("/validate-openai-key")
async def validate_openai_key(
    key_update: OpenAIKeyUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Validate an OpenAI API key without saving it.
    Useful for testing keys before committing.
    
    This makes a real API call to OpenAI to verify the key works.
    """
    key_manager = OpenAIKeyManager(db)
    
    validation_result = await key_manager.validate_key(key_update.api_key)
    
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_result["message"]
        )
    
    return {
        "status": True,
        "message": "API key is valid and working",
        "data": validation_result
    }


# ============================================================================
# Assistant-Level Key Management (Advanced)
# ============================================================================

@router.post("/assistant/{assistant_id}/openai-key")
async def set_assistant_openai_key(
    assistant_id: str,
    key_update: OpenAIKeyUpdate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Set a custom OpenAI key for a specific assistant.
    This overrides your user-level key for this assistant only.
    
    Use case: Different projects/clients with different OpenAI accounts.
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    # Verify user owns this assistant
    assistant = await db["assistants"].find_one({
        "_id": assistant_id,
        "userId": user_id
    })
    
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found or you don't have permission"
        )
    
    key_manager = OpenAIKeyManager(db)
    
    try:
        success = await key_manager.set_assistant_key(assistant_id, key_update.api_key)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update assistant API key"
            )
        
        logger.info(f"Set custom key for assistant {assistant_id}")
        
        return {
            "status": True,
            "message": f"Custom API key set for assistant '{assistant.get('astName')}'",
            "data": {
                "assistant_id": assistant_id,
                "has_custom_key": True
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/assistant/{assistant_id}/openai-key")
async def remove_assistant_openai_key(
    assistant_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Remove custom key from assistant.
    It will fall back to your user-level key or system default.
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    # Verify ownership
    assistant = await db["assistants"].find_one({
        "_id": assistant_id,
        "userId": user_id
    })
    
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found"
        )
    
    key_manager = OpenAIKeyManager(db)
    success = await key_manager.remove_assistant_key(assistant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom key found for this assistant"
        )
    
    return {
        "status": True,
        "message": "Custom key removed from assistant",
        "data": {
            "assistant_id": assistant_id,
            "using": "user_key_or_system_default"
        }
    }