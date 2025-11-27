from datetime import datetime

from fastapi import HTTPException, status

import app.models.model_types as model_type
from app.helpers.openai_helper import OpenAIHelper
from app.services.openai_key_manager import OpenAIKeyManager
from app.services.rate_limiter import RateLimiter
from app.utils.db_helpers import get_user_collection, normalize_object_id


class ThreadController:
    def __init__(self, db):
        self.db = db
        self.assistants_collection = db["assistants"]
        self.threads_collection = db["threads"]
        self.users_collection = get_user_collection(db)

    async def create_thread(
        self,
        thread: model_type.AssistantThread,
        current_user: dict,
    ):
        user_id = current_user.get("sub") or current_user.get("user_id")
        assistant = await self.assistants_collection.find_one(
            {"astId": thread.astId, "userId": user_id}
        )

        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found or you don't have permission",
            )

        ast_id = assistant.get("astId") or assistant.get("_id")

        rate_limiter = RateLimiter(self.db)
        can_create, reason = await rate_limiter.check_thread_limit(
            user_id=user_id, assistant_id=ast_id
        )
        if not can_create:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "THREAD_LIMIT_EXCEEDED",
                    "message": reason,
                    "assistant_id": ast_id,
                    "assistant_name": assistant.get("astName"),
                },
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=ast_id
        )
        openai_helper = OpenAIHelper(api_key=openai_key)

        try:
            thread_data = await openai_helper.create_thread()
            thread_id = thread_data.id
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create thread: {exc}",
            ) from exc

        thread_document = {
            "threadId": thread_id,
            "userId": user_id,
            "astId": ast_id,
            "threadTitle": thread.threadTitle,
            "message_count": 0,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

        result = await self.threads_collection.insert_one(thread_document)
        thread_document["_id"] = str(result.inserted_id)

        await rate_limiter.increment_thread_count(user_id)
        await self.assistants_collection.update_one(
            {"astId": ast_id},
            {
                "$inc": {"usage_stats.total_threads": 1},
                "$set": {"updatedAt": datetime.utcnow()},
            },
        )

        await self.db["usage_history"].insert_one(
            {
                "userId": user_id,
                "assistantId": ast_id,
                "threadId": thread_id,
                "action": "thread_created",
                "tokens_used": 0,
                "timestamp": datetime.utcnow(),
                "metadata": {
                    "thread_title": thread.threadTitle,
                    "assistant_name": assistant.get("astName"),
                },
            }
        )

        return {"status": True, "message": "Thread created successfully", "data": thread_document}

    async def get_threads_by_assistant(self, assistant_id: str, current_user: dict):
        user_id = current_user.get("sub") or current_user.get("user_id")

        assistant = await self.assistants_collection.find_one(
            {"astId": assistant_id, "userId": user_id}
        )
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assistant not found"
            )

        cursor = (
            self.threads_collection.find(
                {"astId": assistant_id, "userId": user_id}
            ).sort("updatedAt", -1)
        )
        threads = await cursor.to_list(length=1000)
        for thread in threads:
            thread["_id"] = str(thread["_id"])

        return {
            "status": True,
            "data": {
                "assistant_id": assistant_id,
                "assistant_name": assistant.get("astName"),
                "total_threads": len(threads),
                "threads": threads,
            },
        }

    async def get_thread_history(self, thread_id: str, current_user: dict):
        user_id = current_user.get("sub") or current_user.get("user_id")
        thread = await self.threads_collection.find_one(
            {"threadId": thread_id, "userId": user_id}
        )

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=thread.get("astId")
        )

        openai_helper = OpenAIHelper(api_key=openai_key)

        try:
            messages = await openai_helper.get_thread_messages(thread_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve messages: {exc}",
            ) from exc

        return {
            "status": True,
            "data": {
                "thread_id": thread_id,
                "thread_title": thread.get("threadTitle"),
                "messages": messages,
                "message_count": len(messages),
            },
        }

    async def delete_thread(self, thread_id: str, current_user: dict):
        user_id = current_user.get("sub") or current_user.get("user_id")
        thread = await self.threads_collection.find_one(
            {"threadId": thread_id, "userId": user_id}
        )

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, _ = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=thread.get("astId")
        )
        openai_helper = OpenAIHelper(api_key=openai_key)

        try:
            await openai_helper.delete_thread(thread_id)
        except Exception:
            pass

        await self.threads_collection.delete_one({"threadId": thread_id})
        await self.users_collection.update_one(
            {"_id": normalize_object_id(user_id)},
            {"$inc": {"usage.threads_created": -1}},
        )
        await self.assistants_collection.update_one(
            {"astId": thread.get("astId")},
            {"$inc": {"usage_stats.total_threads": -1}},
        )

        return {"status": True, "message": "Thread deleted successfully"}
