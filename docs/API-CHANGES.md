# API & Router Response Format Changes

**Date**: 28 November 2025  
**Feature**: Team Members & Handoff Management Integration

---

## Summary

✅ **ONLY 1 EXISTING API response format was modified**  
✅ **The change is BACKWARD COMPATIBLE**  
✅ **New fields are optional with defaults**

---

## Modified Endpoint: GET /api/agent/pending-handoffs

### Old Response Format (Before)
```json
{
  "status": true,
  "data": {
    "pending_count": 2,
    "threads": [
      {
        "thread_id": "thread_123",
        "user_id": "user_456",
        "assistant_id": "bot_id_1",
        "status": "pending_handoff",
        "handoff_reason": "User asked for help",
        "requested_at": "2025-11-28T14:30:00.000Z",
        "recent_messages": [...]
      }
    ]
  }
}
```

### New Response Format (After)
```json
{
  "status": true,
  "data": {
    "pending_count": 2,
    "agent_role": "team_member",        // ← NEW FIELD ADDED
    "threads": [
      {
        "thread_id": "thread_123",
        "user_id": "user_456",
        "assistant_id": "bot_id_1",
        "status": "pending_handoff",
        "handoff_reason": "User asked for help",
        "requested_at": "2025-11-28T14:30:00.000Z",
        "recent_messages": [...]
      }
    ]
  }
}
```

### What Changed?

| Field | Old | New | Type | Required? |
|-------|-----|-----|------|-----------|
| `status` | ✓ | ✓ | boolean | Yes |
| `data.pending_count` | ✓ | ✓ | number | Yes |
| `data.threads` | ✓ | ✓ | array | Yes |
| `data.agent_role` | ✗ | ✅ **NEW** | string | No* |

**`agent_role` value**:
- `"owner"` - If user is owner (full access)
- `"team_member"` - If user is team member (scoped access)

---

## Code Change Reference

### File: app/controllers/agent.py
**Location**: Line 60-65

**Before**:
```python
return {
    "status": True,
    "data": {
        "pending_count": len(enriched_threads),
        "threads": enriched_threads
    }
}
```

**After**:
```python
return {
    "status": True,
    "data": {
        "pending_count": len(enriched_threads),
        "threads": enriched_threads,
        "agent_role": "team_member" if is_team_member else "owner"  # ← NEW
    }
}
```

---

## Changes to `get_current_user()` Dependency

### File: app/middleware/auth_middleware.py

### Old User Object Structure (Before)
```json
{
  "sub": "user_id",
  "email": "user@company.com"
}
```

### New User Object Structure (After)
```json
{
  "sub": "user_id",
  "email": "user@company.com",
  "role": "owner",                    // ← NEW
  "is_team_member": false,            // ← NEW
  "assigned_bots": []                 // ← NEW
}
```

### Code Change

**Before**:
```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = auth_controller.verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(...)
    return {"sub": payload["sub"], "email": payload["email"]}
```

**After**:
```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    payload = auth_controller.verify_token(token, token_type="access")
    if not payload:
        raise HTTPException(...)
    return {
        "sub": payload["sub"],
        "email": payload["email"],
        "role": payload.get("role", "owner"),                   # ← NEW
        "is_team_member": payload.get("is_team_member", False), # ← NEW
        "assigned_bots": payload.get("assigned_bots", [])       # ← NEW
    }
```

---

## Impact Analysis

### ✅ What Still Works (Backward Compatible)

All these existing calls continue to work **without any changes**:

```python
# All existing code still works:
agent_user = get_current_user(...)
agent_user["sub"]        # ✓ Still works
agent_user["email"]      # ✓ Still works

# New fields available but optional:
agent_user["role"]           # ✓ New, always has default
agent_user["is_team_member"] # ✓ New, always has default
agent_user["assigned_bots"]  # ✓ New, always has default
```

### ✅ Existing Routes Unchanged

These routes have **NO response format changes**:

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/agent/assign/{thread_id}` | POST | ✓ Unchanged |
| `/api/agent/send-message` | POST | ✓ Unchanged |
| `/api/agent/complete-handoff` | POST | ✓ Unchanged |
| `/api/agent/my-threads` | GET | ✓ Unchanged |
| All `/api/assistant/*` | * | ✓ Unchanged |
| All `/api/threads/*` | * | ✓ Unchanged |
| All `/api/chats/*` | * | ✓ Unchanged |
| All `/api/enduser/*` | * | ✓ Unchanged |
| All `/auth/login` | POST | ✓ Unchanged |
| All `/auth/sign-up` | POST | ✓ Unchanged |

### ⚠️ What Changed (Minimal)

Only **1 endpoint** has response format changes:

| Endpoint | Method | Change | Breaking? |
|----------|--------|--------|-----------|
| `/api/agent/pending-handoffs` | GET | Added `agent_role` field | ❌ NO |

---

## Frontend Integration Guide

### If You Have Existing Frontend

**Option 1: Do Nothing** (Recommended if `agent_role` not needed)
```javascript
// Your existing code still works perfectly
const response = await fetch('/api/agent/pending-handoffs', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = response.json();
const count = data.data.pending_count;  // ✓ Still works
const threads = data.data.threads;      // ✓ Still works
```

**Option 2: Use New Field** (If you want to know user role)
```javascript
// Use new agent_role to display different UI
const response = await fetch('/api/agent/pending-handoffs', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = response.json();

if (data.data.agent_role === "team_member") {
  console.log("Only seeing assigned bot handoffs");
} else if (data.data.agent_role === "owner") {
  console.log("Seeing all handoffs");
}
```

---

## JWT Token Structure Changes

### Old JWT (Before)
```json
{
  "sub": "owner_id",
  "email": "owner@company.com",
  "type": "access",
  "exp": 1733041200
}
```

### New JWT (After) - For Owners
```json
{
  "sub": "owner_id",
  "email": "owner@company.com",
  "type": "access",
  "role": "owner",              // ← NEW
  "is_team_member": false,      // ← NEW
  "exp": 1733041200
}
```

### New JWT (After) - For Team Members
```json
{
  "sub": "member_id",
  "email": "agent@company.com",
  "type": "access",
  "role": "agent",              // ← NEW
  "is_team_member": true,       // ← NEW
  "assigned_bots": [            // ← NEW (KEY ADDITION)
    "bot_id_1",
    "bot_id_2"
  ],
  "exp": 1733041200
}
```

---

## Filtering Logic Changes

### Database Query in `get_pending_handoffs()`

**Before**: No role-based filtering
```python
# All users see all handoffs
query = {"status": "pending_handoff"}
threads = await collection.find(query).to_list(100)
```

**After**: Role-based filtering
```python
# Query built based on user role
query = {"status": "pending_handoff"}

if is_team_member and assigned_bots:
    # Team members only see assigned bots
    query["astId"] = {"$in": assigned_bots}  # ← FILTERING ADDED

threads = await collection.find(query).to_list(100)
```

---

## Response Examples by User Type

### Example 1: Owner Viewing Handoffs
```json
{
  "status": true,
  "data": {
    "pending_count": 5,
    "agent_role": "owner",      // ← Owner sees ALL handoffs
    "threads": [
      { "thread_id": "t1", "assistant_id": "bot_A" },
      { "thread_id": "t2", "assistant_id": "bot_B" },
      { "thread_id": "t3", "assistant_id": "bot_C" },
      { "thread_id": "t4", "assistant_id": "bot_A" },
      { "thread_id": "t5", "assistant_id": "bot_B" }
    ]
  }
}
```

### Example 2: Team Member (Assigned to bot_A only)
```json
{
  "status": true,
  "data": {
    "pending_count": 2,         // ← Only from assigned bots
    "agent_role": "team_member",
    "threads": [
      { "thread_id": "t1", "assistant_id": "bot_A" },
      { "thread_id": "t4", "assistant_id": "bot_A" }
    ]
  }
}
```

### Example 3: Team Member (Assigned to bot_A + bot_B)
```json
{
  "status": true,
  "data": {
    "pending_count": 4,         // ← From both assigned bots
    "agent_role": "team_member",
    "threads": [
      { "thread_id": "t1", "assistant_id": "bot_A" },
      { "thread_id": "t2", "assistant_id": "bot_B" },
      { "thread_id": "t4", "assistant_id": "bot_A" },
      { "thread_id": "t5", "assistant_id": "bot_B" }
    ]
  }
}
```

---

## Dependency Injection Changes

### Controllers Using `get_current_user()`

All controllers that use `get_current_user()` dependency now receive enhanced user object:

**Example - Agent Router**:
```python
@router.get("/pending-handoffs")
async def get_pending_handoffs(
    agent_user: dict = Depends(get_current_user),  # ← Gets enhanced dict
    controller: AgentController = Depends(get_agent_controller)
):
    # agent_user now has: sub, email, role, is_team_member, assigned_bots
    return await controller.get_pending_handoffs(agent_user)
```

**What's Available**:
```python
{
    "sub": agent_user["sub"],                      # Existing
    "email": agent_user["email"],                  # Existing
    "role": agent_user["role"],                    # NEW - "owner" or "agent"
    "is_team_member": agent_user["is_team_member"], # NEW - bool
    "assigned_bots": agent_user["assigned_bots"]  # NEW - list
}
```

---

## Testing the Changes

### Test 1: Verify Old Code Still Works
```python
# Old usage still works
user = get_current_user(...)
assert user["sub"]     # ✓ Pass
assert user["email"]   # ✓ Pass
```

### Test 2: New Fields Have Defaults
```python
# New fields have defaults
user = get_current_user(...)
assert user["role"] == "owner"           # ✓ Default for owners
assert user["is_team_member"] == False   # ✓ Default for owners
assert user["assigned_bots"] == []       # ✓ Default for owners
```

### Test 3: Team Member Gets Proper Values
```python
# Team member token creates proper values
token = create_team_member_access_token(
    member_id="member_1",
    email="agent@company.com",
    role="agent",
    assigned_bots=["bot_1", "bot_2"]
)
user = get_current_user(...)  # Using above token
assert user["role"] == "agent"                    # ✓ "agent"
assert user["is_team_member"] == True             # ✓ True
assert "bot_1" in user["assigned_bots"]           # ✓ Contains assigned bots
```

---

## Summary Table: What Changed

| Component | Old | New | Impact | Breaking? |
|-----------|-----|-----|--------|-----------|
| **JWT Payload** | minimal | role, is_team_member, assigned_bots | Filtering possible | ❌ No |
| **get_current_user() return** | 2 fields | 5 fields | More info available | ❌ No |
| **GET /api/agent/pending-handoffs response** | No role field | agent_role added | Can distinguish user type | ❌ No |
| **Database queries in get_pending_handoffs** | No filtering | Bot filtering added | Scoped results | ❌ No |

---

## Migration Checklist

- ✅ Existing code still works (backward compatible)
- ✅ No mandatory changes needed for frontend
- ✅ Optional: Use new `agent_role` field if desired
- ✅ Optional: Use new user fields for enhanced logic
- ✅ Database queries automatically filtered
- ✅ No authentication changes needed

---

## What If You Ignore These Changes?

**Everything Still Works** ✓

```javascript
// Your existing frontend code will continue to work exactly as before
fetch('/api/agent/pending-handoffs', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => {
  console.log(data.data.pending_count);  // ✓ Works
  console.log(data.data.threads);        // ✓ Works
  // data.data.agent_role is available but optional to use
});
```

---

## Advanced: Using New Fields

### Display Different UI Based on Role
```javascript
const response = await fetch('/api/agent/pending-handoffs', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data } = await response.json();

if (data.agent_role === "owner") {
  renderOwnerDashboard(data.threads);     // Show all
} else if (data.agent_role === "team_member") {
  renderAgentDashboard(data.threads);     // Show assigned only
}
```

### Log User Role for Analytics
```javascript
const response = await fetch('/api/agent/pending-handoffs', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data } = await response.json();

analytics.log({
  event: "view_handoffs",
  user_role: data.agent_role,           // ← New info available
  pending_count: data.pending_count
});
```

---

## Questions & Answers

**Q: Do I need to update my code?**
A: No, but you can optionally use the new `agent_role` field.

**Q: Will my existing API calls break?**
A: No, all existing fields remain unchanged.

**Q: What about my database?**
A: No changes needed. New filtering happens in application logic.

**Q: Can I use new fields immediately?**
A: Yes, they're available for all users (with defaults for owners).

**Q: How do I know the difference between owner and team member?**
A: Check `data.agent_role` in response or `is_team_member` in user object.

---

## Conclusion

✅ **Changes are minimal and backward compatible**  
✅ **Only 1 endpoint response modified (with new optional field)**  
✅ **User object enhanced with 3 new optional fields**  
✅ **Database filtering automatically applied**  
✅ **No breaking changes to any API**  
✅ **Frontend can continue as-is or use new features**

