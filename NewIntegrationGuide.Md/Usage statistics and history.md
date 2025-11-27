"""
app/routers/usage_router.py - Usage statistics and history
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.middleware.auth_middleware import get_current_user
from app.database.db import get_database
from app.services.rate_limiter import RateLimiter
from app.models.schemas import UsageStats
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/usage", tags=["Usage & Statistics"])


# ============================================================================
# Current Usage Statistics
# ============================================================================

@router.get("/stats", response_model=UsageStats)
async def get_usage_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get your current usage statistics.
    
    Shows:
    - Messages sent today/this week
    - Tokens used this month
    - Remaining limits
    - Whether you can send messages/create assistants
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    rate_limiter = RateLimiter(db)
    
    stats = await rate_limiter.get_usage_stats(user_id)
    
    if not stats:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    return UsageStats(**stats)


# ============================================================================
# Usage History
# ============================================================================

@router.get("/history")
async def get_usage_history(
    period: str = Query("month", regex="^(today|week|month|all)$"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get detailed usage history.
    
    Query params:
    - period: today, week, month, or all
    
    Returns list of all actions with token usage and costs.
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # all
        start_date = datetime(2020, 1, 1)
    
    # Query usage history
    cursor = db["usage_history"].find({
        "userId": user_id,
        "timestamp": {"$gte": start_date}
    }).sort("timestamp", -1)
    
    items = await cursor.to_list(length=1000)
    
    # Calculate totals
    total_messages = sum(1 for item in items if item.get("action") == "message_sent")
    total_tokens = sum(item.get("tokens_used", 0) for item in items)
    total_cost = sum(item.get("cost_estimate", 0.0) for item in items)
    
    # Format items
    formatted_items = []
    for item in items:
        formatted_items.append({
            "timestamp": item.get("timestamp"),
            "action": item.get("action"),
            "assistant_id": item.get("assistantId"),
            "assistant_name": item.get("assistantName"),
            "thread_id": item.get("threadId"),
            "tokens_used": item.get("tokens_used", 0),
            "model_used": item.get("model_used"),
            "cost_estimate": item.get("cost_estimate", 0.0),
            "used_custom_key": item.get("metadata", {}).get("used_custom_key", False)
        })
    
    return {
        "status": True,
        "data": {
            "user_id": user_id,
            "period": period,
            "start_date": start_date,
            "end_date": now,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "total_cost_estimate": round(total_cost, 4),
            "items": formatted_items
        }
    }


# ============================================================================
# Per-Assistant Usage
# ============================================================================

@router.get("/assistant/{assistant_id}/stats")
async def get_assistant_usage_stats(
    assistant_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get usage statistics for a specific assistant.
    
    Shows:
    - Total messages sent to this assistant
    - Total tokens used
    - Estimated costs
    - Most active days
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    # Verify ownership
    assistant = await db["assistants"].find_one({
        "_id": assistant_id,
        "userId": user_id
    })
    
    if not assistant:
        raise HTTPException(
            status_code=404,
            detail="Assistant not found or you don't have permission"
        )
    
    # Get usage stats from history
    cursor = db["usage_history"].find({
        "userId": user_id,
        "assistantId": assistant_id
    })
    
    items = await cursor.to_list(length=10000)
    
    if not items:
        return {
            "status": True,
            "data": {
                "assistant_id": assistant_id,
                "assistant_name": assistant.get("astName"),
                "total_messages": 0,
                "total_tokens": 0,
                "total_threads": 0,
                "cost_estimate": 0.0,
                "last_used": None
            }
        }
    
    # Calculate stats
    total_messages = len([i for i in items if i.get("action") == "message_sent"])
    total_tokens = sum(i.get("tokens_used", 0) for i in items)
    cost_estimate = sum(i.get("cost_estimate", 0.0) for i in items)
    last_used = max([i.get("timestamp") for i in items])
    
    # Count unique threads
    thread_count = await db["threads"].count_documents({
        "userId": user_id,
        "astId": assistant_id
    })
    
    return {
        "status": True,
        "data": {
            "assistant_id": assistant_id,
            "assistant_name": assistant.get("astName"),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "total_threads": thread_count,
            "cost_estimate": round(cost_estimate, 4),
            "last_used": last_used,
            "model": assistant.get("gptModel")
        }
    }


# ============================================================================
# Cost Breakdown
# ============================================================================

@router.get("/cost-breakdown")
async def get_cost_breakdown(
    period: str = Query("month", regex="^(week|month|all)$"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Get detailed cost breakdown by assistant, model, and date.
    
    Useful for understanding where your OpenAI costs are going.
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    # Calculate date range
    now = datetime.utcnow()
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now.replace(day=1)
    else:  # all
        start_date = datetime(2020, 1, 1)
    
    # Aggregate by assistant
    pipeline = [
        {
            "$match": {
                "userId": user_id,
                "timestamp": {"$gte": start_date}
            }
        },
        {
            "$group": {
                "_id": "$assistantId",
                "total_messages": {"$sum": 1},
                "total_tokens": {"$sum": "$tokens_used"},
                "total_cost": {"$sum": "$cost_estimate"}
            }
        },
        {"$sort": {"total_cost": -1}}
    ]
    
    results = await db["usage_history"].aggregate(pipeline).to_list(length=100)
    
    # Get assistant names
    breakdown = []
    for result in results:
        assistant_id = result["_id"]
        if assistant_id:
            assistant = await db["assistants"].find_one({"_id": assistant_id})
            assistant_name = assistant.get("astName") if assistant else "Unknown"
        else:
            assistant_name = "System"
        
        breakdown.append({
            "assistant_id": assistant_id,
            "assistant_name": assistant_name,
            "messages": result["total_messages"],
            "tokens": result["total_tokens"],
            "cost": round(result["total_cost"], 4)
        })
    
    total_cost = sum(item["cost"] for item in breakdown)
    
    return {
        "status": True,
        "data": {
            "period": period,
            "total_cost": round(total_cost, 4),
            "breakdown": breakdown
        }
    }


# ============================================================================
# Export Usage Data
# ============================================================================

@router.get("/export")
async def export_usage_data(
    format: str = Query("json", regex="^(json|csv)$"),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Export all your usage data.
    
    Formats:
    - json: Structured JSON data
    - csv: CSV format for Excel/Sheets
    """
    user_id = current_user.get("sub") or current_user.get("user_id")
    
    # Get all usage history
    cursor = db["usage_history"].find({
        "userId": user_id
    }).sort("timestamp", -1)
    
    items = await cursor.to_list(length=100000)
    
    if format == "csv":
        # Convert to CSV format
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "timestamp", "action", "assistant_id", "thread_id",
            "tokens_used", "model", "cost_estimate"
        ])
        writer.writeheader()
        
        for item in items:
            writer.writerow({
                "timestamp": item.get("timestamp"),
                "action": item.get("action"),
                "assistant_id": item.get("assistantId", ""),
                "thread_id": item.get("threadId", ""),
                "tokens_used": item.get("tokens_used", 0),
                "model": item.get("model_used", ""),
                "cost_estimate": item.get("cost_estimate", 0.0)
            })
        
        from fastapi.responses import StreamingResponse
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=usage_export.csv"}
        )
    
    else:  # json
        return {
            "status": True,
            "data": {
                "user_id": user_id,
                "exported_at": datetime.utcnow(),
                "total_records": len(items),
                "items": items
            }
        }