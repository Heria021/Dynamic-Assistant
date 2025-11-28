from datetime import datetime
from typing import Optional
from fastapi import HTTPException, status


class AgentController:
    """Controller for human agents to manage handoffs."""
    
    def __init__(self, db):
        self.db = db
        self.threads_collection = db["threads"]
        self.chats_collection = db["chats"]
        self.users_collection = db["users"]  # Assuming you have users
    
    async def get_pending_handoffs(self, agent_user: dict):
        """
        Get all threads waiting for human agent pickup.
        For team members, only show handoffs from assigned bots.
        """
        agent_id = agent_user.get("sub") or agent_user.get("user_id")
        is_team_member = agent_user.get("is_team_member", False)
        assigned_bots = agent_user.get("assigned_bots", [])
        
        # Build query
        query = {"status": "pending_handoff"}
        
        # If team member, filter by assigned bots
        if is_team_member and assigned_bots:
            query["astId"] = {"$in": assigned_bots}
        
        # Find threads pending handoff
        cursor = self.threads_collection.find(query).sort("handoff.requested_at", 1)  # Oldest first
        
        pending_threads = await cursor.to_list(length=100)
        
        # Enrich with user info and last messages
        enriched_threads = []
        for thread in pending_threads:
            # Get last few messages
            last_messages = await self.chats_collection.find(
                {"threadId": thread["threadId"]}
            ).sort("createdAt", -1).limit(5).to_list(length=5)
            
            last_messages.reverse()  # Chronological order
            
            enriched_threads.append({
                "thread_id": thread["threadId"],
                "user_id": thread["userId"],
                "assistant_id": thread["astId"],
                "status": thread["status"],
                "handoff_reason": thread.get("handoff", {}).get("reason"),
                "requested_at": thread.get("handoff", {}).get("requested_at"),
                "recent_messages": [
                    {
                        "role": "user" if msg.get("userMessage") else "assistant",
                        "content": msg.get("userMessage") or msg.get("assistantResponse"),
                        "timestamp": msg.get("createdAt")
                    }
                    for msg in last_messages
                ]
            })
        
        return {
            "status": True,
            "data": {
                "pending_count": len(enriched_threads),
                "threads": enriched_threads,
                "agent_role": "team_member" if is_team_member else "owner"
            }
        }
    
    async def assign_thread_to_agent(
        self,
        thread_id: str,
        agent_user: dict
    ):
        """
        Human agent picks up a thread.
        Team members can only pick up threads from assigned bots.
        """
        agent_id = agent_user.get("sub") or agent_user.get("user_id")
        agent_email = agent_user.get("email", "unknown")
        is_team_member = agent_user.get("is_team_member", False)
        assigned_bots = agent_user.get("assigned_bots", [])
        
        # Check if thread is available
        query = {
            "threadId": thread_id,
            "status": "pending_handoff"
        }
        
        # For team members, verify the bot is assigned to them
        if is_team_member and assigned_bots:
            query["astId"] = {"$in": assigned_bots}
        
        thread = await self.threads_collection.find_one(query)
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN if is_team_member else status.HTTP_404_NOT_FOUND,
                detail="Thread not found, already assigned, or not assigned to your bots"
            )
        
        # Assign to agent
        update_result = await self.threads_collection.update_one(
            {"threadId": thread_id},
            {
                "$set": {
                    "status": "with_human",
                    "handoff.assigned_to": agent_id,
                    "handoff.assigned_to_email": agent_email,
                    "handoff.assigned_at": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        if update_result.modified_count > 0:
            return {
                "status": True,
                "message": f"Thread assigned to agent {agent_email}",
                "data": {
                    "thread_id": thread_id,
                    "assigned_to": agent_id,
                    "assigned_at": datetime.utcnow()
                }
            }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign thread"
        )
    
    async def send_human_message(
        self,
        thread_id: str,
        message: str,
        agent_user: dict
    ):
        """
        Human agent sends message to user.
        """
        agent_id = agent_user.get("sub") or agent_user.get("user_id")
        
        # Verify thread is assigned to this agent
        thread = await self.threads_collection.find_one({
            "threadId": thread_id,
            "status": "with_human",
            "handoff.assigned_to": agent_id
        })
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread not assigned to you or not in handoff mode"
            )
        
        # Save message to chats
        chat_document = {
            "userId": thread["userId"],
            "astId": thread["astId"],
            "threadId": thread_id,
            "userMessage": None,  # No user message
            "assistantResponse": message,
            "from_human": True,  # Mark as human response
            "human_agent_id": agent_id,
            "images": None,
            "tokens_used": 0,
            "used_custom_key": False,
            "actions": [],
            "used_rag": False,
            "createdAt": datetime.utcnow(),
        }
        
        result = await self.chats_collection.insert_one(chat_document)
        
        # Update thread last message
        await self.threads_collection.update_one(
            {"threadId": thread_id},
            {
                "$set": {
                    "last_message_from": "human",
                    "updatedAt": datetime.utcnow()
                },
                "$inc": {"message_count": 1}
            }
        )
        
        return {
            "status": True,
            "message": "Message sent to user",
            "data": {
                "chat_id": str(result.inserted_id),
                "message": message,
                "timestamp": datetime.utcnow()
            }
        }
    
    async def complete_handoff(
        self,
        thread_id: str,
        agent_user: dict,
        notes: Optional[str] = None
    ):
        """
        Agent completes handoff and returns thread to AI.
        """
        agent_id = agent_user.get("sub") or agent_user.get("user_id")
        
        # Verify thread is assigned to this agent
        thread = await self.threads_collection.find_one({
            "threadId": thread_id,
            "handoff.assigned_to": agent_id
        })
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thread not assigned to you"
            )
        
        # Mark handoff complete
        update_result = await self.threads_collection.update_one(
            {"threadId": thread_id},
            {
                "$set": {
                    "status": "active",  # Back to AI
                    "last_message_from": "human",
                    "handoff.completed_at": datetime.utcnow(),
                    "handoff.notes": notes or "",
                    "updatedAt": datetime.utcnow()
                }
            }
        )
        
        if update_result.modified_count > 0:
            return {
                "status": True,
                "message": "Handoff completed - thread returned to AI",
                "data": {
                    "thread_id": thread_id,
                    "completed_at": datetime.utcnow()
                }
            }
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete handoff"
        )
    
    async def get_my_active_threads(self, agent_user: dict):
        """
        Get threads currently assigned to this agent.
        """
        agent_id = agent_user.get("sub") or agent_user.get("user_id")
        
        cursor = self.threads_collection.find({
            "status": "with_human",
            "handoff.assigned_to": agent_id
        }).sort("updatedAt", -1)
        
        active_threads = await cursor.to_list(length=100)
        # Ensure ObjectId and other non-JSON-serializable fields are converted
        sanitized_threads = []
        for thread in active_threads:
            # Convert top-level Mongo ObjectId to string if present
            if thread is None:
                continue
            if "_id" in thread:
                try:
                    thread["_id"] = str(thread["_id"])
                except Exception:
                    pass
            sanitized_threads.append(thread)

        return {
            "status": True,
            "data": {
                "active_count": len(sanitized_threads),
                "threads": sanitized_threads
            }
        }
