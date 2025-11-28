# Team Members & Handoff Management - Implementation Guide

## Overview

This implementation provides a **hybrid role-based access control (RBAC) + team management system** for handling handoffs in your assistant API. 

### Architecture

```
Owner (Main User)
├── Creates & Manages Bots (Assistants)
├── Creates & Manages Team Members
│   ├── Team Member 1 (Role: Agent)
│   │   ├── Credentials: Magic Link + Password
│   │   ├── Assigned Bots: [bot_1, bot_2]
│   │   └── Permissions: View/pickup only assigned bot handoffs
│   │
│   └── Team Member 2 (Role: Supervisor)
│       ├── Credentials: Magic Link + Password
│       ├── Assigned Bots: [bot_1, bot_2, bot_3]
│       └── Permissions: View/pickup all assigned bot handoffs
│
└── Handoff Flow
    ├── User requests handoff → Status: pending_handoff
    ├── Only assigned members see it in their interface
    ├── Member picks it up → Status: with_human
    ├── Member handles and responds
    └── Member completes → Status: active (back to AI)
```

## Key Features Implemented

### 1. **Team Member Management**
- Create team members with unique credentials
- Assign members to specific bots
- Different roles: `agent`, `supervisor`
- Activate/deactivate members

### 2. **Magic Link Authentication**
- Passwordless setup via magic links
- 48-hour expiration on links
- One-time use tokens
- Email-based invitation flow

### 3. **Role-Based Access Control**
- JWT tokens include `role` and `assigned_bots`
- Agents only see handoffs from assigned bots
- Supervisors can oversee team activity
- Owners have full visibility

### 4. **Secure Scoping**
- Team members cannot see/pick up handoffs from unassigned bots
- HTTP 403 Forbidden returned for unauthorized access
- All queries filtered at database level

## API Endpoints

### Owner Team Member Management
`POST /api/owner/team-members/invite`
```json
{
  "email": "agent@company.com",
  "name": "John Doe",
  "role": "agent",
  "assigned_bots": ["bot_id_1", "bot_id_2"]
}
```

`GET /api/owner/team-members`
- List all team members

`GET /api/owner/team-members/{member_id}`
- Get specific member details

`PATCH /api/owner/team-members/{member_id}`
```json
{
  "assigned_bots": ["bot_id_1", "bot_id_2"],
  "role": "supervisor"
}
```

`DELETE /api/owner/team-members/{member_id}`
- Deactivate member (soft delete)

`POST /api/owner/team-members/{member_id}/resend-invite`
- Resend invitation with new magic link

### Team Member Authentication
`POST /auth/team-member/setup-password`
```json
{
  "token": "<magic_link_token>",
  "password": "SecurePassword123"
}
```

`POST /auth/team-member/login`
```json
{
  "email": "agent@company.com",
  "password": "SecurePassword123"
}
```

`POST /auth/team-member/magic-link-login`
```json
{
  "token": "<magic_link_token>"
}
```
Returns: Access token with `assigned_bots` scope

### Team Member Handoff Management (Already Existing)
`GET /api/agent/pending-handoffs` 
- Only shows handoffs from assigned bots
- Returns with agent role info

`POST /api/agent/assign/{thread_id}`
- Pick up a handoff
- Validates bot assignment

`POST /api/agent/send-message`
- Send response to user

`POST /api/agent/complete-handoff`
- Return thread to AI

## Database Schema

### TeamMember Collection
```python
{
  "member_id": "uuid",
  "owner_id": "uuid",
  "email": "agent@company.com",
  "name": "John Doe",
  "role": "agent|supervisor",
  "assigned_bots": ["bot_id_1", "bot_id_2"],
  "login_credentials": {
    "type": "password|magic_link",
    "password_hash": "bcrypt_hash",
    "magic_link": {
      "token": "secure_token",
      "created_at": "ISO timestamp",
      "expires_at": "ISO timestamp",
      "used_at": "ISO timestamp or null",
      "is_used": false
    }
  },
  "is_active": true,
  "created_at": "ISO timestamp",
  "invited_at": "ISO timestamp",
  "confirmed_at": "ISO timestamp or null",
  "last_login": "ISO timestamp or null",
  "metadata": {}
}
```

## JWT Token Structure

### Owner Token
```json
{
  "sub": "owner_id",
  "email": "owner@company.com",
  "type": "access",
  "role": "owner",
  "is_team_member": false,
  "exp": 1234567890
}
```

### Team Member Token
```json
{
  "sub": "member_id",
  "email": "agent@company.com",
  "type": "access",
  "role": "agent",
  "is_team_member": true,
  "assigned_bots": ["bot_id_1", "bot_id_2"],
  "exp": 1234567890
}
```

## Authentication Flow

### New Team Member Onboarding

```
1. Owner calls: POST /api/owner/team-members/invite
   ├─ System generates: member_id, magic_link_token
   ├─ Stores in DB with 48h expiry
   └─ Sends email with setup link

2. Team Member receives email with link:
   └─ https://frontend.com/setup-password?token=<magic_link_token>

3. Team Member sets password:
   ├─ POST /auth/team-member/setup-password
   ├─ Token validated and marked as "used"
   ├─ Password hashed and stored
   └─ confirmed_at timestamp set

4. Team Member logs in:
   ├─ POST /auth/team-member/login (email + password)
   ├─ Token verified
   └─ Access token returned with assigned_bots scope

5. Team Member makes requests:
   ├─ Authorization: Bearer <access_token>
   ├─ Middleware extracts assigned_bots from JWT
   └─ Queries automatically filtered by assigned bots
```

## Security Features

### 1. **Password Security**
- Passwords hashed with bcrypt
- Minimum 8 characters enforced
- Never stored in plaintext

### 2. **Magic Link Security**
- Tokens are 32+ character random strings (secrets.token_urlsafe)
- One-time use only
- 48-hour expiration
- Tokens not exposed in responses after use

### 3. **JWT Scoping**
- Team members get limited scope via JWT
- `assigned_bots` array in token
- Cannot modify token to access other bots

### 4. **Database-Level Filtering**
- All agent queries include bot filter
- `query["astId"] = {"$in": assigned_bots}`
- Even if token is tampered, DB enforces limits

### 5. **Permission Checks**
- Only owners can invite/manage members
- HTTP 403 returned for unauthorized access
- Team members cannot access owner endpoints

## Implementation Checklist

✅ Models updated with TeamMember schemas
✅ AuthController supports magic links
✅ JWT includes role and assigned_bots
✅ Auth middleware extracts and validates scoping
✅ Database utilities for team member CRUD
✅ Team member management router created
✅ Team member auth endpoints added
✅ Agent handoff filtering by assigned_bots
✅ Main app registers new router
✅ Test script created

## Running Tests

```bash
# Make the test script executable
chmod +x curl-team-members-test.sh

# Run the complete end-to-end test
./curl-team-members-test.sh
```

The test script verifies:
1. Owner registration and login
2. Bot creation
3. Team member invitation with bot assignment
4. Password setup via magic link
5. Team member login
6. Handoff creation
7. Role-based filtering (agent only sees assigned bots)
8. Team member picks up handoff
9. Team member sends response
10. Owner views team members

## Usage Examples

### Create a Team Member (Owner)
```bash
curl -X POST http://localhost:8000/api/owner/team-members/invite \
  -H "Authorization: Bearer <owner_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@company.com",
    "name": "Alice Support",
    "role": "agent",
    "assigned_bots": ["bot_123", "bot_456"]
  }'
```

### Team Member Sets Password
```bash
curl -X POST http://localhost:8000/auth/team-member/setup-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<magic_link_token_from_email>",
    "password": "SecurePass123"
  }'
```

### Team Member Logs In
```bash
curl -X POST http://localhost:8000/auth/team-member/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@company.com",
    "password": "SecurePass123"
  }'
# Response includes access token with assigned_bots
```

### Team Member Views Handoffs (Auto-filtered)
```bash
curl http://localhost:8000/api/agent/pending-handoffs \
  -H "Authorization: Bearer <team_member_token>"
# Only returns handoffs from assigned bots due to JWT scope
```

### Update Team Member Assignments
```bash
curl -X PATCH http://localhost:8000/api/owner/team-members/member_123 \
  -H "Authorization: Bearer <owner_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_bots": ["bot_789", "bot_101112"],
    "role": "supervisor"
  }'
```

## Next Steps / Future Enhancements

### Phase 2 (Optional)
- [ ] Round-robin assignment of handoffs to team members
- [ ] Team-based handoff routing (automatic distribution)
- [ ] Handoff SLA tracking (response time requirements)
- [ ] Escalation rules (escalate to supervisor if agent can't handle)

### Phase 3 (Optional)
- [ ] Supervisor dashboards with team activity
- [ ] Handoff analytics and metrics
- [ ] Audit logs for compliance
- [ ] Team performance metrics

### Phase 4 (Optional)
- [ ] AI-powered handoff routing (sentiment analysis)
- [ ] Knowledge base for team members
- [ ] Chat history search
- [ ] Canned responses library

## Troubleshooting

### Magic link not working
- Check expiry: `expires_at` should be > current time
- Verify token hasn't been used: `is_used` should be false
- Ensure frontend is passing correct token format

### Team member can't see handoffs
- Verify bot_id is in `assigned_bots` array
- Check JWT token includes `assigned_bots` claim
- Ensure handoff has correct `astId` matching assigned bot

### Password reset issues
- Ensure password is minimum 8 characters
- Check bcrypt library is installed: `pip install bcrypt`
- Verify MongoDB connection is working

### Token validation failing
- Check JWT_SECRET_KEY environment variable is set
- Verify token hasn't expired
- Ensure Authorization header format: `Bearer <token>`

## Database Migrations

If running on existing database:

```python
# Create indexes for performance
db.team_members.create_index([("owner_id", 1)])
db.team_members.create_index([("email", 1)])
db.team_members.create_index([("member_id", 1)])
db.team_members.create_index([("login_credentials.magic_link.token", 1)])

# Add owner_id to existing assistants (if needed)
db.assistants.update_many(
  { owner_id: { $exists: false } },
  { $set: { owner_id: "<default_owner_id>" } }
)
```

## Environment Variables

Ensure these are set in `.env`:
```
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
DATABASE_URL=mongodb://user:pass@host:port
MONGO_INITDB_DATABASE=database_name
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.pickle
FRONTEND_URL=http://localhost:3000
CLIENT_ORIGIN=http://localhost:3000
```

## Summary

This implementation provides:

✅ **Single Owner** with full control  
✅ **Multiple Team Members** with role-based access  
✅ **Magic Links** for passwordless invitations  
✅ **Automatic Scoping** via JWT tokens  
✅ **Database-Level Security** with filtered queries  
✅ **Easy to Use** APIs for onboarding  
✅ **Production Ready** with error handling  
✅ **Fully Tested** end-to-end workflow  

The system scales from simple (single owner, few agents) to complex (multiple supervisors, specialized teams) without architectural changes.
