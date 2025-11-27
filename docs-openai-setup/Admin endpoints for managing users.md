"""
app/routers/admin_router.py - Admin endpoints for managing users
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.auth_middleware import get_current_user
from app.database.db import get_database
from app.services.rate_limiter import RateLimiter
from app.models.schemas import UpdateUserLimits, ResetUserUsage
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# TODO: Add proper admin role check middleware
def is_admin(current_user: dict) -> bool:
    """
    Check if user is admin.
    TODO: Implement proper role-based access control.
    For now, you can check email or add 'is_admin' field to user model.
    """
    # Example implementation:
    # return current_user.get("email") in ["admin@example.com"]
    # OR
    # return current_user.get("role") == "admin"
    
    # For now, allowing all authenticated users for testing
    # IMPORTANT: Implement proper admin check in production!
    logger.warning("Admin check not implemented - allowing all users")
    return True


# ============================================================================
# User Limit Management
# ============================================================================

@router.put("/user/{user_id}/limits")
async def update_user_limits(
    user_id: str,
    limits: UpdateUserLimits,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Update rate limits for a specific user.
    
    Admin only endpoint.
    
    Use cases:
    - Upgrade user to premium tier
    - Give extra quota for special projects
    - Reduce limits for abuse prevention
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Verify user exists
    user = await db["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    rate_limiter = RateLimiter(db)
    
    success = await rate_limiter.update_limits(
        user_id=user_id,
        daily_messages=limits.daily_messages,
        weekly_messages=limits.weekly_messages,
        monthly_tokens=limits.monthly_tokens,
        max_assistants=limits.max_assistants,
        max_threads_per_assistant=limits.max_threads_per_assistant
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update limits"
        )
    
    logger.info(f"Admin {current_user.get('email')} updated limits for user {user_id}")
    
    return {
        "status": True,
        "message": f"Rate limits updated for user {user.get('email')}",
        "data": {
            "user_id": user_id,
            "updated_limits": limits.dict(exclude_none=True)
        }
    }


@router.get("/user/{user_id}/limits")
async def get_user_limits(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get current limits for a user.
    Admin only.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    user = await db["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    limits = user.get("limits", {})
    
    return {
        "status": True,
        "data": {
            "user_id": user_id,
            "email": user.get("email"),
            "limits": limits
        }
    }


# ============================================================================
# User Usage Management
# ============================================================================

@router.get("/user/{user_id}/usage")
async def get_user_usage(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get usage statistics for any user.
    Admin only.
    
    Useful for:
    - Customer support
    - Monitoring heavy users
    - Investigating abuse
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    rate_limiter = RateLimiter(db)
    stats = await rate_limiter.get_usage_stats(user_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user email
    user = await db["users"].find_one({"_id": user_id})
    
    return {
        "status": True,
        "data": {
            **stats,
            "email": user.get("email") if user else None
        }
    }


@router.post("/user/{user_id}/reset-usage")
async def reset_user_usage(
    user_id: str,
    reset: ResetUserUsage,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Reset usage counters for a user.
    Admin only.
    
    Use cases:
    - Give user extra quota mid-period
    - Fix accounting errors
    - Reset after refund
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    user = await db["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updates = {}
    
    if reset.reset_all:
        updates = {
            "usage.messages_today": 0,
            "usage.messages_this_week": 0,
            "usage.tokens_this_month": 0
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
            detail="No reset options specified"
        )
    
    await db["users"].update_one(
        {"_id": user_id},
        {"$set": updates}
    )
    
    logger.info(f"Admin {current_user.get('email')} reset usage for user {user_id}")
    
    return {
        "status": True,
        "message": f"Usage reset for user {user.get('email')}",
        "data": {
            "user_id": user_id,
            "reset_fields": list(updates.keys())
        }
    }


# ============================================================================
# System-Wide Statistics
# ============================================================================

@router.get("/stats/overview")
async def get_system_overview(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get system-wide statistics.
    Admin only.
    
    Shows:
    - Total users
    - Total messages today
    - Total tokens this month
    - Users with custom keys
    - Cost estimates
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Count users
    total_users = await db["users"].count_documents({})
    
    # Count users with custom keys
    users_with_custom_keys = await db["users"].count_documents({
        "openai_api_key": {"$exists": True}
    })
    
    # Aggregate usage
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_messages_today": {"$sum": "$usage.messages_today"},
                "total_messages_week": {"$sum": "$usage.messages_this_week"},
                "total_tokens_month": {"$sum": "$usage.tokens_this_month"}
            }
        }
    ]
    
    usage_result = await db["users"].aggregate(pipeline).to_list(length=1)
    usage = usage_result[0] if usage_result else {}
    
    # Count assistants and threads
    total_assistants = await db["assistants"].count_documents({})
    total_threads = await db["threads"].count_documents({})
    
    return {
        "status": True,
        "data": {
            "users": {
                "total": total_users,
                "with_custom_keys": users_with_custom_keys,
                "percentage_custom_keys": round(users_with_custom_keys / total_users * 100, 2) if total_users > 0 else 0
            },
            "usage": {
                "messages_today": usage.get("total_messages_today", 0),
                "messages_this_week": usage.get("total_messages_week", 0),
                "tokens_this_month": usage.get("total_tokens_month", 0)
            },
            "resources": {
                "total_assistants": total_assistants,
                "total_threads": total_threads
            }
        }
    }


@router.get("/stats/top-users")
async def get_top_users(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get top users by usage.
    Admin only.
    
    Shows who's using the platform the most.
    """
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Get users sorted by tokens this month
    cursor = db["users"].find({}).sort("usage.tokens_this_month", -1).limit(limit)
    users = await cursor.to_list(length=limit)
    
    top_users = []
    for user in users:
        usage = user.get("usage", {})
        top_users.append({
            "user_id": user.get("_id"),
            "email": user.get("email"),
            "messages_today": usage.get("messages_today", 0),
            "messages_this_week": usage.get("messages_this_week", 0),
            "tokens_this_month": usage.get("tokens_this_month", 0),
            "assistants_created": usage.get("assistants_created", 0),
            "has_custom_key": bool(user.get("openai_api_key"))
        })
    
    return {
        "status": True,
        "data": {
            "top_users": top_users
        }
    }