import logging
import os
from typing import Optional, Tuple

from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorDatabase
from openai import OpenAI

from app.utils.db_helpers import get_user_collection, normalize_object_id

logger = logging.getLogger(__name__)


class OpenAIKeyManager:
    """Manage encrypted storage and retrieval of custom OpenAI API keys."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.users_collection = get_user_collection(db)
        self.assistants_collection = db["assistants"]

        encryption_key = os.getenv("API_KEY_ENCRYPTION_KEY")
        if not encryption_key:
            logger.warning(
                "API_KEY_ENCRYPTION_KEY not set; generating ephemeral key for runtime only."
            )
            encryption_key = Fernet.generate_key().decode()

        self.cipher = Fernet(encryption_key.encode())
        self.system_key = os.getenv("OPENAI_API_KEY")

    def _encrypt_key(self, api_key: str) -> str:
        return self.cipher.encrypt(api_key.encode()).decode()

    def _decrypt_key(self, encrypted_key: str) -> str:
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    async def set_user_key(self, user_id: str, api_key: str) -> bool:
        if not api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")

        encrypted_key = self._encrypt_key(api_key)
        result = await self.users_collection.update_one(
            {"_id": normalize_object_id(user_id)},
            {
                "$set": {
                    "openai_api_key": encrypted_key,
                    "openai_key_type": "custom",
                }
            },
        )
        if result.modified_count:
            logger.info("Set custom OpenAI key for user %s", user_id)
            return True
        return False

    async def get_user_key(self, user_id: str) -> Optional[str]:
        user = await self.users_collection.find_one(
            {"_id": normalize_object_id(user_id)}, {"openai_api_key": 1}
        )
        if not user:
            return self.system_key

        encrypted_key = user.get("openai_api_key")
        if not encrypted_key:
            return self.system_key

        try:
            return self._decrypt_key(encrypted_key)
        except Exception as exc:
            logger.error("Failed to decrypt key for user %s: %s", user_id, exc)
            return self.system_key

    async def remove_user_key(self, user_id: str) -> bool:
        result = await self.users_collection.update_one(
            {"_id": normalize_object_id(user_id)},
            {
                "$unset": {"openai_api_key": ""},
                "$set": {"openai_key_type": "system"},
            },
        )
        if result.modified_count:
            logger.info("Removed custom key for user %s", user_id)
            return True
        return False

    async def has_custom_user_key(self, user_id: str) -> bool:
        user = await self.users_collection.find_one(
            {"_id": normalize_object_id(user_id)}, {"openai_api_key": 1}
        )
        return bool(user and user.get("openai_api_key"))

    async def set_assistant_key(self, assistant_id: str, api_key: str) -> bool:
        if not api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        encrypted_key = self._encrypt_key(api_key)
        result = await self.assistants_collection.update_one(
            {"_id": assistant_id},
            {"$set": {"custom_openai_key": encrypted_key}},
        )
        return bool(result.modified_count)

    async def get_assistant_key(self, assistant_id: str, user_id: str) -> str:
        assistant = await self.assistants_collection.find_one(
            {"_id": assistant_id}, {"custom_openai_key": 1}
        )
        if assistant and assistant.get("custom_openai_key"):
            try:
                return self._decrypt_key(assistant["custom_openai_key"])
            except Exception as exc:
                logger.error("Failed to decrypt assistant key %s: %s", assistant_id, exc)
        return await self.get_user_key(user_id)

    async def remove_assistant_key(self, assistant_id: str) -> bool:
        result = await self.assistants_collection.update_one(
            {"_id": assistant_id},
            {"$unset": {"custom_openai_key": ""}},
        )
        return bool(result.modified_count)

    async def validate_key(self, api_key: str) -> dict:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return {
                "valid": True,
                "message": "API key is valid",
                "model_access": "gpt-4o-mini",
                "test_tokens_used": response.usage.total_tokens,
            }
        except Exception as exc:
            error_msg = str(exc)
            if "invalid" in error_msg.lower() or "auth" in error_msg.lower():
                reason = "Invalid API key or authentication failed"
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                reason = "API key has exceeded quota or rate limit"
            elif "permission" in error_msg.lower():
                reason = "API key lacks required permissions"
            else:
                reason = f"Validation failed: {error_msg}"
            logger.warning("Key validation failed: %s", reason)
            return {"valid": False, "message": reason, "error": error_msg}

    async def get_key_status(self, user_id: str) -> dict:
        has_custom = await self.has_custom_user_key(user_id)
        assistants_with_keys = await self.assistants_collection.count_documents(
            {"userId": user_id, "custom_openai_key": {"$exists": True}}
        )
        return {
            "has_custom_key": has_custom,
            "key_type": "custom" if has_custom else "system",
            "message": "Using custom API key"
            if has_custom
            else "Using system default API key",
            "assistants_using_custom_key": assistants_with_keys,
        }

    async def get_key_for_request(
        self, user_id: str, assistant_id: Optional[str] = None
    ) -> Tuple[str, bool]:
        if assistant_id:
            key = await self.get_assistant_key(assistant_id, user_id)
        else:
            key = await self.get_user_key(user_id)
        is_custom = key != self.system_key
        return key, is_custom

