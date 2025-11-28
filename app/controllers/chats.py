import base64
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from app.helpers.openai_helper import OpenAIHelper
from app.services.openai_key_manager import OpenAIKeyManager
from app.services.rate_limiter import RateLimiter


class ChatController:
    def __init__(self, db):
        self.db = db
        self.assistants_collection = db["assistants"]
        self.threads_collection = db["threads"]
        self.chats_collection = db["chats"]

    async def create_chat(
        self,
        astId: str,
        threadId: str,
        message: str,
        current_user: dict,
        image: Optional[List[UploadFile]] = None,
    ):
        user_id = current_user.get("sub") or current_user.get("user_id")

        rate_limiter = RateLimiter(self.db)
        can_send, reason = await rate_limiter.check_message_limit(user_id)
        if not can_send:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": reason,
                    "suggestions": [
                        "Wait for your daily/weekly limit to reset",
                        "Upgrade to a higher tier plan",
                        "Add your own OpenAI API key for unlimited messages",
                    ],
                },
            )

        can_use_tokens, token_reason = await rate_limiter.check_token_limit(user_id)
        if not can_use_tokens:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "TOKEN_LIMIT_EXCEEDED",
                    "message": token_reason,
                    "suggestions": [
                        "Add your own OpenAI API key to bypass token limits",
                        "Wait for monthly reset",
                        "Use a more efficient model (gpt-4o-mini)",
                    ],
                },
            )

        assistant = await self.assistants_collection.find_one(
            {"astId": astId, "userId": user_id}
        )
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found or you don't have permission",
            )

        thread = await self.threads_collection.find_one(
            {"threadId": threadId, "userId": user_id, "astId": astId}
        )
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or doesn't belong to this assistant",
            )

        key_manager = OpenAIKeyManager(self.db)
        openai_key, is_custom_key = await key_manager.get_key_for_request(
            user_id=user_id, assistant_id=astId
        )

        image_data_list = []
        if image:
            for img_file in image:
                contents = await img_file.read()
                base64_image = base64.b64encode(contents).decode("utf-8")
                image_data_list.append(
                    {
                        "filename": img_file.filename,
                        "data": base64_image,
                        "content_type": img_file.content_type,
                    }
                )

        # === OPENAI NATIVE FILE SEARCH ===
        # OpenAI automatically uses file_search tool when files are attached
        # No need for manual RAG retrieval - OpenAI handles it!
        has_files = bool(assistant.get("file_ids"))
        if has_files:
            print(f"[RAG-DEBUG] Assistant has {len(assistant.get('file_ids', []))} file(s) - OpenAI file_search enabled")
        else:
            print(f"[RAG-DEBUG] Assistant has no files - file_search disabled")

        # === CALL OPENAI WITH RAG + FUNCTIONS ===
        # Note: Function tools are already on the assistant (added at creation time)
        # No need to pass them here - OpenAI will use them automatically
        openai_helper = OpenAIHelper(api_key=openai_key)
        try:
            response = await openai_helper.create_message_and_run(
                thread_id=threadId,
                assistant_id=assistant["astId"],
                message=message,
                images=image_data_list,
                # Function tools are already on the assistant - no need to pass them
                # Note: OpenAI file_search is automatic when assistant has files
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get response from assistant: {exc}",
            ) from exc

        # === EXTRACT RESPONSE DATA ===
        assistant_response = response.get("response", "")
        tokens_used = response.get("tokens_used", 0)
        actions = response.get("actions", [])  # NEW
        used_rag = response.get("used_rag", False)  # NEW
        
        print(f"[RAG-DEBUG] Response extracted - used_rag: {used_rag}, actions: {len(actions) if actions else 0}")
        if actions:
            print(f"[RAG-DEBUG] Actions found: {actions}")

        await rate_limiter.increment_message_count(user_id)

        if tokens_used > 0:
            await rate_limiter.track_token_usage(
                user_id=user_id,
                tokens_used=tokens_used,
                assistant_id=astId,
                thread_id=threadId,
                model=assistant.get("gptModel", "gpt-4o-mini"),
                used_custom_key=is_custom_key,
            )

        chat_document = {
            "userId": user_id,
            "astId": astId,
            "threadId": threadId,
            "userMessage": message,
            "assistantResponse": assistant_response,
            "images": image_data_list if image_data_list else None,
            "tokens_used": tokens_used,
            "used_custom_key": is_custom_key,
            "actions": actions,  # NEW
            "used_rag": used_rag,  # NEW
            "createdAt": datetime.utcnow(),
        }

        result = await self.chats_collection.insert_one(chat_document)

        # === NEW: PROCESS ACTIONS ===
        if actions:
            await self._process_actions(
                actions=actions,
                thread_id=threadId,
                user_id=user_id,
                assistant_id=astId
            )

        # === RETURN RESPONSE WITH ACTIONS ===
        return {
            "status": True,
            "message": "Chat created successfully",
            "data": {
                "chat_id": str(result.inserted_id),
                "user_message": message,
                "assistant_response": assistant_response,
                "tokens_used": tokens_used,
                "used_custom_key": is_custom_key,
                "used_rag": used_rag,  # NEW
                "images_count": len(image_data_list) if image_data_list else 0,
                "timestamp": datetime.utcnow(),
            },
            "actions": actions if actions else None,  # NEW: Root-level actions
        }

    async def get_chat_history(
        self,
        threadId: str,
        current_user: dict,
        limit: int = 50,
    ):
        user_id = current_user.get("sub") or current_user.get("user_id")
        thread = await self.threads_collection.find_one(
            {"threadId": threadId, "userId": user_id}
        )

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found",
            )

        cursor = (
            self.chats_collection.find(
                {"threadId": threadId, "userId": user_id}
            )
            .sort("createdAt", -1)
            .limit(limit)
        )
        chats = await cursor.to_list(length=limit)
        chats.reverse()

        # Convert ObjectId to string for JSON serialization
        for chat in chats:
            if "_id" in chat:
                chat["_id"] = str(chat["_id"])
            if "chat_id" in chat:
                chat["chat_id"] = str(chat["chat_id"])

        return {
            "status": True,
            "data": {
                "thread_id": threadId,
                "total_messages": len(chats),
                "messages": chats,
            },
        }

    # === NEW METHOD: Process Actions ===
    async def _process_actions(
        self,
        actions: List[dict],
        thread_id: str,
        user_id: str,
        assistant_id: str
    ):
        """
        Process actions returned by OpenAI function calls.
        """
        for action in actions:
            action_type = action.get("type")
            action_data = action.get("data", {})

            print(f"[ACTION] Processing action: {action_type}")

            if action_type == "handoff_to_human":
                await self._handle_handoff_to_human(
                    thread_id=thread_id,
                    user_id=user_id,
                    assistant_id=assistant_id,
                    reason=action_data.get("reason", "User requested human assistance")
                )

            elif action_type == "send_link":
                print(f"[ACTION] Link to send: {action_data.get('url')}")

            elif action_type == "send_email":
                print(f"[ACTION] Email to send: {action_data.get('subject')}")

    async def _handle_handoff_to_human(
        self,
        thread_id: str,
        user_id: str,
        assistant_id: str,
        reason: str
    ):
        """
        Mark thread as needing human assistance.
        """
        print(f"[HANDOFF] Initiating handoff for thread: {thread_id}")
        print(f"[HANDOFF] Reason: {reason}")

        update_result = await self.threads_collection.update_one(
            {"threadId": thread_id, "userId": user_id},
            {
                "$set": {
                    "status": "pending_handoff",
                    "last_message_from": "ai",
                    "handoff": {
                        "requested_at": datetime.utcnow(),
                        "reason": reason,
                        "assigned_to": None,
                        "assigned_at": None,
                        "completed_at": None,
                        "notes": ""
                    },
                    "updatedAt": datetime.utcnow()
                }
            }
        )

        if update_result.modified_count > 0:
            print(f"[HANDOFF] ✓ Thread {thread_id} marked for human handoff")
        else:
            print(f"[HANDOFF] ✗ Failed to update thread status")