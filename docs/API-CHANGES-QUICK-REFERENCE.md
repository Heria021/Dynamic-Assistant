# Quick Reference: Response Format Changes

## TL;DR - 30 Second Summary

✅ **ONLY 1 endpoint response changed** - `/api/agent/pending-handoffs`  
✅ **Change is BACKWARD COMPATIBLE** - old code still works  
✅ **New field added** - `agent_role` (tells if user is owner or team_member)  
✅ **User object enhanced** - 3 new optional fields in `get_current_user()`

---

## The One Change You Need to Know

### GET /api/agent/pending-handoffs

**OLD** response:
```json
{
  "status": true,
  "data": {
    "pending_count": 2,
    "threads": [...]
  }
}
```

**NEW** response:
```json
{
  "status": true,
  "data": {
    "pending_count": 2,
    "agent_role": "team_member",  // ← NEW FIELD
    "threads": [...]
  }
}
```

**Values for `agent_role`**:
- `"owner"` = Owner (sees all handoffs)
- `"team_member"` = Agent/Team Member (sees only assigned bot handoffs)

---

## User Object Changes (Middleware)

### OLD (before):
```python
agent_user = {
    "sub": "user_id",
    "email": "user@company.com"
}
```

### NEW (after):
```python
agent_user = {
    "sub": "user_id",
    "email": "user@company.com",
    "role": "owner|agent|supervisor",  # ← NEW
    "is_team_member": false|true,       # ← NEW
    "assigned_bots": ["bot_1", ...]     # ← NEW
}
```

---

## JWT Token Changes

### Owner Token Structure:
```json
{
  "sub": "owner_id",
  "email": "owner@company.com",
  "type": "access",
  "role": "owner",           // ← NEW
  "is_team_member": false,   // ← NEW
  "exp": timestamp
}
```

### Team Member Token Structure:
```json
{
  "sub": "member_id",
  "email": "agent@company.com",
  "type": "access",
  "role": "agent",           // ← NEW
  "is_team_member": true,    // ← NEW
  "assigned_bots": ["bot_1", "bot_2"],  // ← NEW (IMPORTANT!)
  "exp": timestamp
}
```

---

## Code Examples

### Check if User is Team Member:
```python
# In any router using get_current_user dependency
def my_endpoint(current_user: dict = Depends(get_current_user)):
    if current_user["is_team_member"]:
        print("This is a team member")
    else:
        print("This is an owner")
```

### Get User's Role:
```python
role = current_user.get("role")  # "owner", "agent", or "supervisor"
```

### Get Assigned Bots:
```python
assigned_bots = current_user.get("assigned_bots", [])  # List of bot IDs
print(f"User can access: {assigned_bots}")
```

### Use agent_role in Frontend:
```javascript
const response = await fetch('/api/agent/pending-handoffs', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data = await response.json();

console.log(data.data.agent_role);  // "owner" or "team_member"
```

---

## What Stayed the Same

✅ All other endpoints unchanged  
✅ Response format for `/api/agent/assign/{id}` - Same  
✅ Response format for `/api/agent/send-message` - Same  
✅ Response format for `/api/agent/complete-handoff` - Same  
✅ Response format for `/api/assistant/*` - Same  
✅ Response format for `/api/threads/*` - Same  
✅ Response format for `/api/chats/*` - Same  
✅ Response format for `/auth/login` - Same  
✅ Response format for `/auth/sign-up` - Same  

---

## Filtering Logic Added

### In `/api/agent/pending-handoffs`:

**Before**: Show all pending handoffs to anyone authenticated
```
Anyone → See ALL handoffs
```

**After**: Show only relevant handoffs
```
Owner → See ALL handoffs (no filter)
Team Member → See ONLY assigned bot handoffs (filtered)
```

---

## Real World Examples

### Scenario 1: Owner Logs In
```
✓ Token has: is_team_member = false
✓ Response includes: agent_role = "owner"
✓ Can see: ALL pending handoffs (5 from bot_A, 3 from bot_B, 2 from bot_C)
```

### Scenario 2: Team Member (assigned to bot_A)
```
✓ Token has: is_team_member = true, assigned_bots = ["bot_A"]
✓ Response includes: agent_role = "team_member"
✓ Can see: ONLY bot_A handoffs (5 from bot_A)
✓ Cannot see: bot_B, bot_C handoffs (returns empty or 403)
```

### Scenario 3: Supervisor (assigned to bot_A + bot_B)
```
✓ Token has: is_team_member = true, assigned_bots = ["bot_A", "bot_B"]
✓ Response includes: agent_role = "team_member"
✓ Can see: bot_A + bot_B handoffs (5 from bot_A, 3 from bot_B)
✓ Cannot see: bot_C handoffs
```

---

## FAQ

**Q: Will my old code break?**  
A: No, fields are additive (only added, not removed).

**Q: Do I have to use the new fields?**  
A: No, they're optional. Ignore them if you don't need them.

**Q: What if my frontend doesn't expect `agent_role`?**  
A: It won't cause an error. Just ignore the extra field.

**Q: Can team members see other agents' handoffs?**  
A: No, they only see their assigned bots' handoffs.

**Q: What's the difference between `role` and `agent_role`?**  
A: `role` is in user object (set), `agent_role` is in response (tells you the role).

---

## Files Changed

| File | What Changed |
|------|--------------|
| `app/controllers/auth_controller.py` | Updated `create_access_token()` to add role and assigned_bots |
| `app/middleware/auth_middleware.py` | Updated `get_current_user()` to extract role info |
| `app/controllers/agent.py` | Added role-based filtering in `get_pending_handoffs()` |
| All other endpoints | **NO CHANGES** |

---

## Testing Your Changes

### Test 1: Old Code Still Works
```bash
curl http://localhost:8000/api/agent/pending-handoffs \
  -H "Authorization: Bearer <token>"

# Old fields still present:
# ✓ status
# ✓ data.pending_count
# ✓ data.threads
```

### Test 2: New Field Present
```bash
curl http://localhost:8000/api/agent/pending-handoffs \
  -H "Authorization: Bearer <token>"

# New field added:
# ✓ data.agent_role  (equals "owner" or "team_member")
```

### Test 3: Filtering Works
```bash
# As owner - see all handoffs
curl http://localhost:8000/api/agent/pending-handoffs \
  -H "Authorization: Bearer <owner_token>"
# Returns: ALL pending handoffs

# As team member - see only assigned
curl http://localhost:8000/api/agent/pending-handoffs \
  -H "Authorization: Bearer <agent_token>"
# Returns: ONLY assigned bot handoffs
```

---

## Implementation Details

### Where Filtering Happens:

**Database Level** (MongoDB Query):
```python
query = {"status": "pending_handoff"}
if is_team_member:
    query["astId"] = {"$in": assigned_bots}
threads = await db.threads.find(query)
```

**JWT Level** (Token Claims):
```json
{
  "assigned_bots": ["bot_1", "bot_2"],
  "is_team_member": true
}
```

**Application Level** (Additional checks):
```python
if is_team_member and assigned_bots:
    # Verify bot access before allowing pickup
    if requested_bot not in assigned_bots:
        raise HTTPException(403, "Not assigned to this bot")
```

---

## Migration Path (If Needed)

### If you have existing code:
```javascript
// Before - still works
const count = response.data.data.pending_count;

// After - optionally use new info
const count = response.data.data.pending_count;
const role = response.data.data.agent_role;  // Can now check role
```

### No breaking changes required ✓

---

## Key Takeaway

🎯 **One response field added** (`agent_role`)  
🎯 **Three user object fields added** (`role`, `is_team_member`, `assigned_bots`)  
🎯 **All backward compatible**  
🎯 **Automatic filtering for team members**  
🎯 **Existing code continues to work**  

**Bottom line**: You don't need to change anything, but you can use the new fields if you want to.

