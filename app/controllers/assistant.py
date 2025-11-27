import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

import app.models.model_types as model_type
import app.utils.open_ai_utils as ai_utils
from app.helpers.openai_helper import OpenAIHelper
from app.services.openai_key_manager import OpenAIKeyManager
from app.services.rate_limiter import RateLimiter
from app.utils.db_helpers import get_user_collection, normalize_object_id


class AssistantController:
    def __init__(self, db):
        self.db = db
        self.assistants_collection = db["assistants"]
        self.users_collection = get_user_collection(db)

    async def create_assistant(
        self,
        assistant: model_type.Assistant,
        current_user: dict,
        files: Optional[List[UploadFile]] = None,
    ):
        user_id = current_user.get("sub") or current_user.get("user_id")

        rate_limiter = RateLimiter(self.db)
        can_create, reason = await rate_limiter.check_assistant_limit(user_id)
        if not can_create:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "ASSISTANT_LIMIT_EXCEEDED",
                    "message": reason,
                    "suggestions": [
                        "Delete unused assistants",
                        "Upgrade to a higher tier plan for more assistants",
                    ],
                },
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key = await key_manager.get_user_key(user_id)
        if not openai_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No OpenAI API key available",
            )

        openai_helper = OpenAIHelper(api_key=openai_key)

        file_ids: List[str] = []
        if files:
            for file in files:
                file_id = await openai_helper.upload_file(file)
                file_ids.append(file_id)

        try:
            assistant_data = await openai_helper.create_assistant(
                name=assistant.astName,
                instructions=assistant.astInstruction,
                model=assistant.gptModel,
                tools=assistant.astTools,
                file_ids=file_ids,
            )
            assistant_id = assistant_data.id
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create assistant: {exc}",
            ) from exc

        api_token = secrets.token_urlsafe(32)

        assistant_document = {
            "userId": user_id,
            "astName": assistant.astName,
            "astInstruction": assistant.astInstruction,
            "gptModel": assistant.gptModel,
            "astTools": assistant.astTools,
            "astId": assistant_id,
            "apiToken": api_token,
            "file_ids": file_ids,
            "usage_stats": {
                "total_messages": 0,
                "total_tokens": 0,
                "total_threads": 0,
                "last_used": None,
            },
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

        result = await self.assistants_collection.insert_one(assistant_document)
        assistant_document["_id"] = str(result.inserted_id)

        await rate_limiter.increment_assistant_count(user_id)

        await self.db["usage_history"].insert_one(
            {
                "userId": user_id,
                "assistantId": str(result.inserted_id),
                "action": "assistant_created",
                "tokens_used": 0,
                "model_used": assistant.gptModel,
                "cost_estimate": 0.0,
                "timestamp": datetime.utcnow(),
                "metadata": {
                    "assistant_name": assistant.astName,
                    "tools": assistant.astTools,
                },
            }
        )

        return {
            "status": True,
            "message": "Assistant created successfully",
            "data": assistant_document,
        }

    async def get_assistants(self, current_user: dict):
        user_id = current_user.get("sub") or current_user.get("user_id")
        cursor = (
            self.assistants_collection.find({"userId": user_id})
            .sort("createdAt", -1)
        )
        assistants = await cursor.to_list(length=1000)
        for assistant in assistants:
            assistant["_id"] = str(assistant["_id"])
        return {"status": True, "data": assistants}

    async def get_assistant_by_id(self, assistant_id: str, current_user: dict):
        user_id = current_user.get("sub") or current_user.get("user_id")
        assistant = await self.assistants_collection.find_one(
            {"astId": assistant_id, "userId": user_id}
        )

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found",
            )

        assistant["_id"] = str(assistant["_id"])
        return {"status": True, "data": assistant}

    async def update_assistant(
        self,
        assistant_payload: model_type.UpdateAssistant,
        current_user: dict,
    ):
        user_id = current_user.get("sub") or current_user.get("user_id")
        assistant = await self.assistants_collection.find_one(
            {"astId": assistant_payload.astId, "userId": user_id}
        )

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found",
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=assistant_payload.astId
        )

        openai_helper = OpenAIHelper(api_key=openai_key)

        update_data = {}
        if assistant_payload.astName:
            update_data["name"] = assistant_payload.astName
        if assistant_payload.astInstruction:
            update_data["instructions"] = assistant_payload.astInstruction
        if assistant_payload.gptModel:
            update_data["model"] = assistant_payload.gptModel
        if assistant_payload.astTools:
            update_data["tools"] = [{"type": tool} for tool in assistant_payload.astTools]

        try:
            await openai_helper.update_assistant(
                assistant_id=assistant["astId"],
                **update_data,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update assistant: {exc}",
            ) from exc

        db_updates = {}
        if assistant_payload.astName:
            db_updates["astName"] = assistant_payload.astName
        if assistant_payload.astInstruction:
            db_updates["astInstruction"] = assistant_payload.astInstruction
        if assistant_payload.gptModel:
            db_updates["gptModel"] = assistant_payload.gptModel
        if assistant_payload.astTools:
            db_updates["astTools"] = assistant_payload.astTools

        db_updates["updatedAt"] = datetime.utcnow()

        await self.assistants_collection.update_one(
            {"astId": assistant_payload.astId},
            {"$set": db_updates},
        )

        return {
            "status": True,
            "message": "Assistant updated successfully",
            "data": {"assistant_id": assistant_payload.astId, "updates": db_updates},
        }

    async def delete_assistant(self, assistant_id: str, current_user: dict):
        user_id = current_user.get("sub") or current_user.get("user_id")
        assistant = await self.assistants_collection.find_one(
            {"astId": assistant_id, "userId": user_id}
        )

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found",
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=assistant_id
        )
        openai_helper = OpenAIHelper(api_key=openai_key)

        try:
            await openai_helper.delete_assistant(assistant["astId"])
        except Exception:
            # Continue even if deletion fails remotely.
            pass

        await self.assistants_collection.delete_one({"astId": assistant_id})
        await self.users_collection.update_one(
            {"_id": normalize_object_id(user_id)},
            {"$inc": {"usage.assistants_created": -1}},
        )

        return {"status": True, "message": "Assistant deleted successfully"}

    async def upload_assistant_files(
        self,
        assistant_id: str,
        files: List[UploadFile],
        current_user: dict,
    ):
        user_id = current_user.get("sub") or current_user.get("user_id")
        assistant = await self.assistants_collection.find_one(
            {"astId": assistant_id, "userId": user_id}
        )

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found",
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=assistant_id
        )
        openai_helper = OpenAIHelper(api_key=openai_key)

        new_file_ids: List[str] = []
        for file in files:
            file_id = await openai_helper.upload_file(file)
            new_file_ids.append(file_id)

        updated_file_ids = assistant.get("file_ids", []) + new_file_ids

        await openai_helper.update_assistant(
            assistant_id=assistant["astId"], file_ids=updated_file_ids
        )

        await self.assistants_collection.update_one(
            {"astId": assistant_id},
            {
                "$set": {
                    "file_ids": updated_file_ids,
                    "updatedAt": datetime.utcnow(),
                }
            },
        )

        return {
            "status": True,
            "message": "Files uploaded successfully",
            "data": {"file_ids": updated_file_ids},
        }


async def generate_api_token(user_id):
    return ai_utils.generate_api_token(user_id)
