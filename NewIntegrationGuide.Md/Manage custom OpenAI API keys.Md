"""
app/services/openai_key_manager.py - Manage custom OpenAI API keys
"""

import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from cryptography.fernet import Fernet
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class OpenAIKeyManager:
    """
    Manages custom OpenAI API keys for users and assistants.
    Keys are encrypted at rest in MongoDB.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.users_collection = db["users"]
        self.assistants_collection = db["assistants"]
        
        # Get encryption key from environment
        encryption_key = os.getenv("API_KEY_ENCRYPTION_KEY")
        if not encryption_key:
            logger.warning(
                "API_KEY_ENCRYPTION_KEY not set. Generate with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
            # For development - generate temporary key
            encryption_key = Fernet.generate_key().decode()
        
        self.cipher = Fernet(encryption_key.encode())
        self.system_key = os.getenv("OPENAI_API_KEY")
    
    def _encrypt_key(self, api_key: str) -> str:
        """Encrypt an API key for storage"""
        encrypted = self.cipher.encrypt(api_key.encode())
        return encrypted.decode()
    
    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key from storage"""
        decrypted = self.cipher.decrypt(encrypted_key.encode())
        return decrypted.decode()
    
    # ========================================================================
    # User-Level Key Management
    # ========================================================================
    
    async def set_user_key(self, user_id: str, api_key: str) -> bool:
        """
        Set a custom OpenAI API key for a user.
        This key will be used for all their assistants by default.
        """
        if not api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        
        encrypted_key = self._encrypt_key(api_key)
        
        result = await self.users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "openai_api_key": encrypted_key,
                    "openai_key_type": "custom"
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Set custom OpenAI key for user {user_id}")
            return True
        
        return False
    
    async def get_user_key(self, user_id: str) -> Optional[str]:
        """
        Get OpenAI API key for a user.
        Returns custom key if set, otherwise system default.
        """
        user = await self.users_collection.find_one(
            {"_id": user_id},
            {"openai_api_key": 1}
        )
        
        if not user:
            return self.system_key
        
        encrypted_key = user.get("openai_api_key")
        if encrypted_key:
            try:
                return self._decrypt_key(encrypted_key)
            except Exception as e:
                logger.error(f"Failed to decrypt key for user {user_id}: {e}")
                return self.system_key
        
        return self.system_key
    
    async def remove_user_key(self, user_id: str) -> bool:
        """Remove user's custom OpenAI key"""
        result = await self.users_collection.update_one(
            {"_id": user_id},
            {
                "$unset": {"openai_api_key": ""},
                "$set": {"openai_key_type": "system"}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Removed custom key for user {user_id}")
            return True
        
        return False
    
    async def has_custom_user_key(self, user_id: str) -> bool:
        """Check if user has custom key"""
        user = await self.users_collection.find_one(
            {"_id": user_id},
            {"openai_api_key": 1}
        )
        return bool(user and user.get("openai_api_key"))
    
    # ========================================================================
    # Assistant-Level Key Management (Optional Override)
    # ========================================================================
    
    async def set_assistant_key(self, assistant_id: str, api_key: str) -> bool:
        """
        Set a custom key for a specific assistant.
        This overrides the user's key for this assistant only.
        """
        if not api_key.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        
        encrypted_key = self._encrypt_key(api_key)
        
        result = await self.assistants_collection.update_one(
            {"_id": assistant_id},
            {"$set": {"custom_openai_key": encrypted_key}}
        )
        
        return result.modified_count > 0
    
    async def get_assistant_key(self, assistant_id: str, user_id: str) -> str:
        """
        Get the appropriate OpenAI key for an assistant.
        Priority: Assistant custom key > User custom key > System default
        """
        # Check for assistant-specific key
        assistant = await self.assistants_collection.find_one(
            {"_id": assistant_id},
            {"custom_openai_key": 1}
        )
        
        if assistant and assistant.get("custom_openai_key"):
            try:
                return self._decrypt_key(assistant["custom_openai_key"])
            except Exception as e:
                logger.error(f"Failed to decrypt assistant key: {e}")
        
        # Fall back to user key
        return await self.get_user_key(user_id)
    
    async def remove_assistant_key(self, assistant_id: str) -> bool:
        """Remove assistant-specific custom key"""
        result = await self.assistants_collection.update_one(
            {"_id": assistant_id},
            {"$unset": {"custom_openai_key": ""}}
        )
        return result.modified_count > 0
    
    # ========================================================================
    # Key Validation
    # ========================================================================
    
    async def validate_key(self, api_key: str) -> dict:
        """
        Validate an OpenAI API key by making a test request.
        Returns dict with validation status and details.
        """
        try:
            client = OpenAI(api_key=api_key)
            
            # Make minimal test request
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            
            return {
                "valid": True,
                "message": "API key is valid",
                "model_access": "gpt-4o-mini",
                "test_tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # Determine error type
            if "invalid" in error_msg.lower() or "auth" in error_msg.lower():
                reason = "Invalid API key or authentication failed"
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                reason = "API key has exceeded quota or rate limit"
            elif "permission" in error_msg.lower():
                reason = "API key lacks required permissions"
            else:
                reason = f"Validation failed: {error_msg}"
            
            logger.warning(f"Key validation failed: {reason}")
            
            return {
                "valid": False,
                "message": reason,
                "error": error_msg
            }
    
    # ========================================================================
    # Key Status & Statistics
    # ========================================================================
    
    async def get_key_status(self, user_id: str) -> dict:
        """Get detailed status of user's OpenAI key configuration"""
        has_custom = await self.has_custom_user_key(user_id)
        
        # Count assistants using custom keys
        assistants_with_keys = await self.assistants_collection.count_documents({
            "userId": user_id,
            "custom_openai_key": {"$exists": True}
        })
        
        return {
            "has_custom_key": has_custom,
            "key_type": "custom" if has_custom else "system",
            "message": "Using custom API key" if has_custom else "Using system default API key",
            "assistants_using_custom_key": assistants_with_keys
        }
    
    async def get_key_for_request(
        self,
        user_id: str,
        assistant_id: Optional[str] = None
    ) -> tuple[str, bool]:
        """
        Get the appropriate key for a request.
        Returns (api_key, is_custom_key)
        """
        if assistant_id:
            key = await self.get_assistant_key(assistant_id, user_id)
        else:
            key = await self.get_user_key(user_id)
        
        is_custom = key != self.system_key
        return key, is_custom