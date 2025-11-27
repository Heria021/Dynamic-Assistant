from datetime import datetime, timedelta
from typing import Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.utils.db_helpers import get_user_collection

import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handles rate limiting and usage tracking for users."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.users_collection = get_user_collection(db)

    def _get_object_id(self, user_id: str):
        """Convert user_id string to MongoDB ObjectId if needed."""
        try:
            return ObjectId(user_id)
        except:
            return user_id

    async def _ensure_usage_fields(self, user_id: str) -> bool:
        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user:
            return False

        updates = {}
        if "limits" not in user:
            updates["limits"] = {
                "daily_messages": 100,
                "weekly_messages": 500,
                "monthly_tokens": 1_000_000,
                "max_assistants": 500,
                "max_threads_per_assistant": 50,
            }
        if "usage" not in user:
            updates["usage"] = {
                "messages_today": 0,
                "messages_this_week": 0,
                "tokens_this_month": 0,
                "assistants_created": 0,
                "threads_created": 0,
                "last_reset_daily": datetime.utcnow(),
                "last_reset_weekly": datetime.utcnow(),
                "last_reset_monthly": datetime.utcnow(),
            }

        if updates:
            await self.users_collection.update_one(
                {"_id": self._get_object_id(user_id)}, {"$set": updates}, upsert=False
            )
        return True

    async def _reset_counters_if_needed(self, user_id: str):
        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user or "usage" not in user:
            return

        usage = user["usage"]
        now = datetime.utcnow()
        updates = {}

        last_daily = usage.get("last_reset_daily")
        if not last_daily or last_daily.date() < now.date():
            updates["usage.messages_today"] = 0
            updates["usage.last_reset_daily"] = now

        last_weekly = usage.get("last_reset_weekly")
        week_start = now - timedelta(days=now.weekday())
        if not last_weekly or last_weekly.date() < week_start.date():
            updates["usage.messages_this_week"] = 0
            updates["usage.last_reset_weekly"] = now

        last_monthly = usage.get("last_reset_monthly")
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not last_monthly or last_monthly < month_start:
            updates["usage.tokens_this_month"] = 0
            updates["usage.last_reset_monthly"] = now

        if updates:
            await self.users_collection.update_one(
                {"_id": self._get_object_id(user_id)}, {"$set": updates}, upsert=False
            )

    async def check_message_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        await self._ensure_usage_fields(user_id)
        await self._reset_counters_if_needed(user_id)

        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user:
            return False, "User not found"

        limits = user.get("limits", {})
        usage = user.get("usage", {})

        daily_limit = limits.get("daily_messages", 100)
        if usage.get("messages_today", 0) >= daily_limit:
            return False, f"Daily message limit reached ({daily_limit} messages per day)"

        weekly_limit = limits.get("weekly_messages", 500)
        if usage.get("messages_this_week", 0) >= weekly_limit:
            return (
                False,
                f"Weekly message limit reached ({weekly_limit} messages per week)",
            )

        return True, None

    async def increment_message_count(self, user_id: str) -> bool:
        result = await self.users_collection.update_one(
            {"_id": self._get_object_id(user_id)},
            {"$inc": {"usage.messages_today": 1, "usage.messages_this_week": 1}},
        )
        return bool(result.modified_count)

    async def check_token_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        await self._ensure_usage_fields(user_id)
        await self._reset_counters_if_needed(user_id)
        
        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user:
            return False, "User not found"

        limits = user.get("limits", {})
        usage = user.get("usage", {})

        monthly_limit = limits.get("monthly_tokens", 1_000_000)
        if usage.get("tokens_this_month", 0) >= monthly_limit:
            return False, f"Monthly token limit reached ({monthly_limit:,} tokens)"

        return True, None

    async def track_token_usage(
        self,
        user_id: str,
        tokens_used: int,
        assistant_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        model: str = "gpt-4o-mini",
        used_custom_key: bool = False,
    ) -> bool:
        result = await self.users_collection.update_one(
            {"_id": self._get_object_id(user_id)}, {"$inc": {"usage.tokens_this_month": tokens_used}}
        )
        await self.db["usage_history"].insert_one(
            {
                "userId": user_id,
                "assistantId": assistant_id,
                "threadId": thread_id,
                "action": "message_sent",
                "tokens_used": tokens_used,
                "model_used": model,
                "cost_estimate": self._calculate_cost(tokens_used, model),
                "timestamp": datetime.utcnow(),
                "metadata": {"used_custom_key": used_custom_key},
            }
        )
        return bool(result.modified_count)

    async def check_assistant_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        await self._ensure_usage_fields(user_id)
        await self._reset_counters_if_needed(user_id)
        
        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user:
            return False, "User not found"

        limits = user.get("limits", {})
        usage = user.get("usage", {})
        max_assistants = limits.get("max_assistants", 5)
        if usage.get("assistants_created", 0) >= max_assistants:
            return False, f"Maximum assistant limit reached ({max_assistants} assistants)"

        return True, None

    async def increment_assistant_count(self, user_id: str) -> bool:
        result = await self.users_collection.update_one(
            {"_id": self._get_object_id(user_id)}, {"$inc": {"usage.assistants_created": 1}}
        )
        return bool(result.modified_count)

    async def check_thread_limit(
        self, user_id: str, assistant_id: str
    ) -> Tuple[bool, Optional[str]]:
        await self._ensure_usage_fields(user_id)
        await self._reset_counters_if_needed(user_id)
        
        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user:
            return False, "User not found"

        limits = user.get("limits", {})
        max_threads = limits.get("max_threads_per_assistant", 50)
        thread_count = await self.db["threads"].count_documents(
            {"userId": user_id, "astId": assistant_id}
        )
        if thread_count >= max_threads:
            return False, f"Maximum threads per assistant reached ({max_threads} threads)"

        return True, None

    async def increment_thread_count(self, user_id: str) -> bool:
        result = await self.users_collection.update_one(
            {"_id": self._get_object_id(user_id)}, {"$inc": {"usage.threads_created": 1}}
        )
        return bool(result.modified_count)

    async def get_usage_stats(self, user_id: str) -> Optional[dict]:
        await self._ensure_usage_fields(user_id)
        await self._reset_counters_if_needed(user_id)

        user = await self.users_collection.find_one({"_id": self._get_object_id(user_id)})
        if not user:
            return None

        limits = user.get("limits", {})
        usage = user.get("usage", {})

        daily_remaining = max(
            0, limits.get("daily_messages", 100) - usage.get("messages_today", 0)
        )
        weekly_remaining = max(
            0, limits.get("weekly_messages", 500) - usage.get("messages_this_week", 0)
        )
        tokens_remaining = max(
            0,
            limits.get("monthly_tokens", 1_000_000)
            - usage.get("tokens_this_month", 0),
        )
        assistants_remaining = max(
            0, limits.get("max_assistants", 5) - usage.get("assistants_created", 0)
        )

        return {
            "user_id": user_id,
            "messages_today": usage.get("messages_today", 0),
            "messages_this_week": usage.get("messages_this_week", 0),
            "tokens_this_month": usage.get("tokens_this_month", 0),
            "assistants_created": usage.get("assistants_created", 0),
            "threads_created": usage.get("threads_created", 0),
            "daily_messages_limit": limits.get("daily_messages", 100),
            "weekly_messages_limit": limits.get("weekly_messages", 500),
            "monthly_tokens_limit": limits.get("monthly_tokens", 1_000_000),
            "max_assistants": limits.get("max_assistants", 5),
            "max_threads_per_assistant": limits.get("max_threads_per_assistant", 50),
            "daily_remaining": daily_remaining,
            "weekly_remaining": weekly_remaining,
            "tokens_remaining": tokens_remaining,
            "assistants_remaining": assistants_remaining,
            "can_send_message": daily_remaining > 0 and weekly_remaining > 0,
            "can_create_assistant": assistants_remaining > 0,
            "can_create_thread": True,
        }

    async def update_limits(
        self,
        user_id: str,
        daily_messages: Optional[int] = None,
        weekly_messages: Optional[int] = None,
        monthly_tokens: Optional[int] = None,
        max_assistants: Optional[int] = None,
        max_threads_per_assistant: Optional[int] = None,
    ) -> bool:
        updates = {}
        if daily_messages is not None:
            updates["limits.daily_messages"] = daily_messages
        if weekly_messages is not None:
            updates["limits.weekly_messages"] = weekly_messages
        if monthly_tokens is not None:
            updates["limits.monthly_tokens"] = monthly_tokens
        if max_assistants is not None:
            updates["limits.max_assistants"] = max_assistants
        if max_threads_per_assistant is not None:
            updates["limits.max_threads_per_assistant"] = max_threads_per_assistant

        if not updates:
            return False

        result = await self.users_collection.update_one(
            {"_id": self._get_object_id(user_id)}, {"$set": updates}
        )
        return bool(result.matched_count)

    def _calculate_cost(self, tokens: int, model: str) -> float:
        pricing = {
            "gpt-4o": 0.0025 / 1000,
            "gpt-4o-mini": 0.000375 / 1000,
            "gpt-4": 0.03 / 1000,
            "gpt-3.5-turbo": 0.0005 / 1000,
        }
        cost_per_token = pricing.get(model, 0.001 / 1000)
        return tokens * cost_per_token

