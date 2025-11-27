from fastapi import APIRouter, Depends, HTTPException, status

from app.database.db import get_database
from app.middleware.auth_middleware import get_current_user
from app.models.schemas import OpenAIKeyStatus, OpenAIKeyUpdate
from app.services.openai_key_manager import OpenAIKeyManager

router = APIRouter(prefix="/api/settings", tags=["User Settings"])


@router.post("/openai-key")
async def set_openai_key(
    key_update: OpenAIKeyUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = current_user.get("sub") or current_user.get("user_id")
    key_manager = OpenAIKeyManager(db)

    try:
        success = await key_manager.set_user_key(user_id, key_update.api_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key",
        )

    return {
        "status": True,
        "message": "OpenAI API key updated successfully. All your messages will now use your custom key.",
        "data": {"key_type": "custom", "active": True},
    }


@router.delete("/openai-key")
async def remove_openai_key(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = current_user.get("sub") or current_user.get("user_id")
    key_manager = OpenAIKeyManager(db)

    success = await key_manager.remove_user_key(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom API key found to remove",
        )

    return {
        "status": True,
        "message": "Custom API key removed. You are now using the system default key.",
        "data": {"key_type": "system", "rate_limits_apply": True},
    }


@router.get("/openai-key/status", response_model=OpenAIKeyStatus)
async def get_openai_key_status(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = current_user.get("sub") or current_user.get("user_id")
    key_manager = OpenAIKeyManager(db)
    status_info = await key_manager.get_key_status(user_id)
    return OpenAIKeyStatus(**status_info)


@router.post("/validate-openai-key")
async def validate_openai_key(
    key_update: OpenAIKeyUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    key_manager = OpenAIKeyManager(db)
    validation_result = await key_manager.validate_key(key_update.api_key)

    if not validation_result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_result["message"],
        )

    return {
        "status": True,
        "message": "API key is valid and working",
        "data": validation_result,
    }


@router.post("/assistant/{assistant_id}/openai-key")
async def set_assistant_openai_key(
    assistant_id: str,
    key_update: OpenAIKeyUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = current_user.get("sub") or current_user.get("user_id")
    assistant = await db["assistants"].find_one(
        {"_id": assistant_id, "userId": user_id}
    )

    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found or you don't have permission",
        )

    key_manager = OpenAIKeyManager(db)
    try:
        success = await key_manager.set_assistant_key(assistant_id, key_update.api_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update assistant API key",
        )

    return {
        "status": True,
        "message": f"Custom API key set for assistant '{assistant.get('astName')}'",
        "data": {"assistant_id": assistant_id, "has_custom_key": True},
    }


@router.delete("/assistant/{assistant_id}/openai-key")
async def remove_assistant_openai_key(
    assistant_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = current_user.get("sub") or current_user.get("user_id")
    assistant = await db["assistants"].find_one(
        {"_id": assistant_id, "userId": user_id}
    )

    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant not found",
        )

    key_manager = OpenAIKeyManager(db)
    success = await key_manager.remove_assistant_key(assistant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No custom key found for this assistant",
        )

    return {
        "status": True,
        "message": "Custom key removed from assistant",
        "data": {
            "assistant_id": assistant_id,
            "using": "user_key_or_system_default",
        },
    }

