import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.database.db import get_database
from app.middleware.auth_middleware import get_current_user
from app.models.schemas import ResetUserUsage, UpdateUserLimits
from app.services.rate_limiter import RateLimiter
from app.utils.db_helpers import get_user_collection, normalize_object_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def is_admin(current_user: dict) -> bool:
    logger.warning("Admin check not implemented - allowing all users")
    return True


@router.put("/user/{user_id}/limits")
async def update_user_limits(
    user_id: str,
    limits: UpdateUserLimits,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    users_collection = get_user_collection(db)
    user = await users_collection.find_one({"_id": normalize_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rate_limiter = RateLimiter(db)
    success = await rate_limiter.update_limits(
        user_id=user_id,
        daily_messages=limits.daily_messages,
        weekly_messages=limits.weekly_messages,
        monthly_tokens=limits.monthly_tokens,
        max_assistants=limits.max_assistants,
        max_threads_per_assistant=limits.max_threads_per_assistant,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update limits",
        )

    logger.info(
        "Admin %s updated limits for user %s", current_user.get("email"), user_id
    )

    return {
        "status": True,
        "message": f"Rate limits updated for user {user.get('email')}",
        "data": {"user_id": user_id, "updated_limits": limits.model_dump(exclude_none=True)},
    }


@router.get("/user/{user_id}/limits")
async def get_user_limits(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    users_collection = get_user_collection(db)
    user = await users_collection.find_one({"_id": normalize_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": True,
        "data": {"user_id": user_id, "email": user.get("email"), "limits": user.get("limits", {})},
    }


@router.get("/user/{user_id}/usage")
async def get_user_usage(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    rate_limiter = RateLimiter(db)
    stats = await rate_limiter.get_usage_stats(user_id)
    if not stats:
        raise HTTPException(status_code=404, detail="User not found")

    users_collection = get_user_collection(db)
    user = await users_collection.find_one({"_id": normalize_object_id(user_id)})

    return {
        "status": True,
        "data": {**stats, "email": user.get("email") if user else None},
    }


@router.post("/user/{user_id}/reset-usage")
async def reset_user_usage(
    user_id: str,
    reset: ResetUserUsage,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    if not is_admin(current_user):
        raise HTTPException(
            status=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    users_collection = get_user_collection(db)
    user = await users_collection.find_one({"_id": normalize_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if reset.reset_all:
        updates = {
            "usage.messages_today": 0,
            "usage.messages_this_week": 0,
            "usage.tokens_this_month": 0,
        }
    else:
        if reset.reset_daily:
            updates["usage.messages_today"] = 0
        if reset.reset_weekly:
            updates["usage.messages_this_week"] = 0
        if reset.reset_monthly:
            updates["usage.tokens_this_month"] = 0

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No reset options specified",
        )

    users_collection = get_user_collection(db)
    await users_collection.update_one({"_id": normalize_object_id(user_id)}, {"$set": updates})
    logger.info("Admin %s reset usage for user %s", current_user.get("email"), user_id)

    return {
        "status": True,
        "message": f"Usage reset for user {user.get('email')}",
        "data": {"user_id": user_id, "reset_fields": list(updates.keys())},
    }


@router.get("/stats/overview")
async def get_system_overview(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    users_collection = get_user_collection(db)
    total_users = await users_collection.count_documents({})
    users_with_custom_keys = await users_collection.count_documents(
        {"openai_api_key": {"$exists": True}}
    )

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_messages_today": {"$sum": "$usage.messages_today"},
                "total_messages_week": {"$sum": "$usage.messages_this_week"},
                "total_tokens_month": {"$sum": "$usage.tokens_this_month"},
            }
        }
    ]
    usage_result = await users_collection.aggregate(pipeline).to_list(length=1)
    usage = usage_result[0] if usage_result else {}

    total_assistants = await db["assistants"].count_documents({})
    total_threads = await db["threads"].count_documents({})

    return {
        "status": True,
        "data": {
            "users": {
                "total": total_users,
                "with_custom_keys": users_with_custom_keys,
                "percentage_custom_keys": round(
                    users_with_custom_keys / total_users * 100, 2
                )
                if total_users
                else 0,
            },
            "usage": {
                "messages_today": usage.get("total_messages_today", 0),
                "messages_this_week": usage.get("total_messages_week", 0),
                "tokens_this_month": usage.get("total_tokens_month", 0),
            },
            "resources": {
                "total_assistants": total_assistants,
                "total_threads": total_threads,
            },
        },
    }


@router.get("/stats/top-users")
async def get_top_users(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    users_collection = get_user_collection(db)
    cursor = (
        users_collection.find({}).sort("usage.tokens_this_month", -1).limit(limit)
    )
    users = await cursor.to_list(length=limit)

    top_users = []
    for user in users:
        usage = user.get("usage", {})
        top_users.append(
            {
                "user_id": user.get("_id"),
                "email": user.get("email"),
                "messages_today": usage.get("messages_today", 0),
                "messages_this_week": usage.get("messages_this_week", 0),
                "tokens_this_month": usage.get("tokens_this_month", 0),
                "assistants_created": usage.get("assistants_created", 0),
                "has_custom_key": bool(user.get("openai_api_key")),
            }
        )

    return {"status": True, "data": {"top_users": top_users}}

