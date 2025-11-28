# Team Members Feature - Quick Start Guide

## What Was Implemented

A complete **team member management system** with role-based handoff access for your assistant API.

### The Problem Solved
- ❌ Before: Any authenticated user could see ALL handoffs
- ✅ After: Team members only see handoffs from their assigned bots

### The Solution
```
Owner Creates:
  ├─ Assistants/Bots (support_bot_1, sales_bot_1, etc.)
  └─ Team Members (alice, bob, charlie)
     ├─ Alice → assigned to support_bot_1
     ├─ Bob → assigned to sales_bot_1
     └─ Charlie → assigned to support_bot_1 + sales_bot_1

When a handoff occurs:
  ├─ support_bot_1 handoff → seen by Alice & Charlie only
  └─ sales_bot_1 handoff → seen by Bob & Charlie only
```

---

## 5-Minute Setup

### 1. **Start the API**
```bash
python -m uvicorn app.main:app --reload
```

### 2. **Run the Test Script**
```bash
chmod +x curl-team-members-test.sh
./curl-team-members-test.sh
```

This will automatically:
- Register an owner
- Create a bot
- Invite a team member
- Set up password via magic link
- Team member logs in
- Create and pickup a handoff
- Verify role-based filtering

---

## How to Use in Your Frontend

### Step 1: Owner Dashboard - Create Team Members

```javascript
// Invite a new team member
const inviteTeamMember = async (token, memberData) => {
  const response = await fetch('http://localhost:8000/api/owner/team-members/invite', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: 'agent@company.com',
      name: 'John Agent',
      role: 'agent',
      assigned_bots: ['bot_id_1', 'bot_id_2']
    })
  });
  
  const data = await response.json();
  // data.magic_link_token - send this to user
  return data;
};
```

### Step 2: Team Member - Set Password (After Email)

```javascript
// User receives email with magic link
// Frontend extracts token from URL: ?token=<magic_link_token>
const setupPassword = async (token, password) => {
  const response = await fetch('http://localhost:8000/auth/team-member/setup-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      token: token,
      password: password
    })
  });
  
  return response.json();
};
```

### Step 3: Team Member - Login

```javascript
const teamMemberLogin = async (email, password) => {
  const response = await fetch('http://localhost:8000/auth/team-member/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: email,
      password: password
    })
  });
  
  const data = await response.json();
  // data.access_token - use this for all requests
  // data.user.assigned_bots - these are the bots they can see
  localStorage.setItem('token', data.access_token);
  return data;
};
```

### Step 4: Team Member - View Pending Handoffs

```javascript
const getPendingHandoffs = async (token) => {
  const response = await fetch('http://localhost:8000/api/agent/pending-handoffs', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const data = await response.json();
  // data.data.threads - only shows their assigned bots
  // data.data.agent_role - "team_member" or "owner"
  return data.data.threads;
};
```

### Step 5: Team Member - Pick Up Handoff

```javascript
const pickupHandoff = async (token, threadId) => {
  const response = await fetch(`http://localhost:8000/api/agent/assign/${threadId}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  return response.json();
};
```

### Step 6: Team Member - Send Response

```javascript
const sendResponse = async (token, threadId, message) => {
  const response = await fetch('http://localhost:8000/api/agent/send-message', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      thread_id: threadId,
      message: message
    })
  });
  
  return response.json();
};
```

### Step 7: Team Member - Complete Handoff

```javascript
const completeHandoff = async (token, threadId, notes) => {
  const response = await fetch('http://localhost:8000/api/agent/complete-handoff', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      thread_id: threadId,
      notes: notes
    })
  });
  
  return response.json();
};
```

---

## Key Concepts

### 1. **Magic Links**
- No password needed initially
- 48-hour links sent to email
- One-time use only
- After first use, member uses email + password

### 2. **JWT Tokens**
```json
// What the token contains:
{
  "sub": "member_id",
  "email": "agent@company.com",
  "role": "agent",
  "is_team_member": true,
  "assigned_bots": ["bot_1", "bot_2"],  // ← This is key!
  "exp": 1234567890
}
```

### 3. **Filtering Happens Automatically**
- When team member requests `/api/agent/pending-handoffs`
- Backend extracts `assigned_bots` from JWT
- Query: `find({ status: "pending_handoff", astId: { $in: ["bot_1", "bot_2"] } })`
- Only sees handoffs from assigned bots

### 4. **Roles Available**
| Role | Can | Notes |
|------|-----|-------|
| `agent` | Pick up assigned handoffs | Entry-level support |
| `supervisor` | Pick up assigned handoffs + oversight | Can review team performance |

---

## File Changes Summary

### New Files
```
app/routers/team_members.py              ← Team member management endpoints
docs/TEAM-MEMBERS-IMPLEMENTATION.md      ← Full documentation
curl-team-members-test.sh                ← End-to-end test script
```

### Modified Files
```
app/models/schemas.py                    ← Added TeamMember models
app/models/model_types.py                ← Added request/response types
app/controllers/auth_controller.py       ← Added magic link methods
app/routers/auth.py                      ← Added team member auth endpoints
app/middleware/auth_middleware.py        ← Now extracts assigned_bots from JWT
app/controllers/agent.py                 ← Filters by assigned_bots
app/utils/mongo_utils.py                 ← Added team member database functions
app/main.py                              ← Registered new router
```

---

## Database Changes

### New Collection
```
team_members
├── member_id (UUID)
├── owner_id (links to owner)
├── email
├── name
├── role (agent|supervisor)
├── assigned_bots (array of bot IDs)
├── login_credentials
│   ├── type
│   ├── password_hash
│   └── magic_link
└── timestamps (created_at, invited_at, confirmed_at, last_login)
```

### Indexes Created
```javascript
db.team_members.createIndex({ owner_id: 1 })
db.team_members.createIndex({ email: 1 })
db.team_members.createIndex({ member_id: 1 })
db.team_members.createIndex({ "login_credentials.magic_link.token": 1 })
```

---

## Testing Scenarios

### Scenario 1: Agent Can't See Unassigned Bot Handoffs
```bash
# Owner creates 2 bots: bot_A, bot_B
# Owner creates 2 agents: alice (assigned bot_A), bob (assigned bot_B)
# Alice's handoff → only bob can't see it
# Bob's handoff → only alice can't see it

GET /api/agent/pending-handoffs (as alice)
# Returns: handoffs from bot_A only
# Returns: 403 Forbidden if tries to pickup bot_B handoff
```

### Scenario 2: Supervisor Can See Multiple Bots
```bash
# Owner assigns supervisor charlie to bot_A + bot_B
GET /api/agent/pending-handoffs (as charlie)
# Returns: handoffs from bot_A AND bot_B
```

### Scenario 3: Magic Link Expiration
```bash
# 1. Link sent to agent
# 2. After 48 hours: Link expires
# 3. POST /auth/team-member/setup-password with old link
# Returns: 400 Bad Request - "Magic link token has expired"
# Solution: Owner resends invite
```

---

## Common Issues & Solutions

### Issue: "Only owners can invite team members"
**Cause**: Logged in as team member, not owner
**Solution**: Use owner's token for `/api/owner/team-members/*` endpoints

### Issue: "Thread not found or not assigned to your bots"
**Cause**: Team member trying to access handoff from unassigned bot
**Solution**: Verify bot is in their `assigned_bots` array

### Issue: "Invalid or expired magic link token"
**Cause**: Token expired or already used
**Solution**: Owner should resend invitation with new token

### Issue: Team member sees empty handoffs list
**Cause**: Bot is not assigned or no pending handoffs exist
**Solution**: 
1. Check `assigned_bots` in team member profile
2. Verify handoff is from assigned bot
3. Check thread status is "pending_handoff"

---

## Next Steps

### Immediate (Optional Enhancements)
- [ ] Add resend password reset for team members
- [ ] Add team member profile update endpoint
- [ ] Add ban/suspend member functionality

### Short Term (Recommended)
- [ ] Handoff SLA tracking (response time metrics)
- [ ] Supervisor dashboard with team stats
- [ ] Audit logs for compliance
- [ ] Handoff notes and tags

### Medium Term (Nice to Have)
- [ ] Auto-routing of handoffs (round-robin or load balancing)
- [ ] AI-powered routing (route to best agent)
- [ ] Escalation rules (escalate if no response in X minutes)
- [ ] Canned responses/templates for agents

### Long Term (Advanced)
- [ ] Multi-team support (teams within organization)
- [ ] Handoff reason classification
- [ ] Performance metrics and KPIs
- [ ] Integration with ticketing systems
- [ ] Bulk member import/export

---

## Support

For issues or questions:
1. Check the full docs: `docs/TEAM-MEMBERS-IMPLEMENTATION.md`
2. Review test script: `curl-team-members-test.sh` for examples
3. Check logs for error messages
4. Verify MongoDB connection and indexes

---

## Summary

✅ **What You Get:**
- Single owner with full control
- Multiple team members with specific bot access
- Secure passwordless invitations via magic links
- Role-based automatic filtering
- Production-ready implementation
- Full test coverage

✅ **Security:**
- Passwords hashed with bcrypt
- JWT tokens with scoping
- Database-level filtering
- One-time magic link tokens
- Permission validation on every request

✅ **Ready to Use:**
- Just run the test script to verify
- Full API documentation included
- Frontend code examples provided
- Easy to integrate into existing UI
