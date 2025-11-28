# Team Members & Handoff Management - Complete API Reference

## Base URL
```
http://localhost:8000
```

---

## 🔒 Authentication Endpoints

### 1. Team Member Setup Password (Magic Link)
**Endpoint**: `POST /auth/team-member/setup-password`

**Description**: Team member sets password using magic link token received via email

**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "token": "secure_token_from_email",
  "password": "SecurePassword123"
}
```

**Response Success (200)**:
```json
{
  "status": "success",
  "message": "Password set successfully. You can now log in."
}
```

**Response Error (400)**:
```json
{
  "detail": "Invalid or expired magic link token"
}
```

**Error Codes**:
- `400`: Invalid token, token expired, or token already used
- `500`: Internal server error

---

### 2. Team Member Login
**Endpoint**: `POST /auth/team-member/login`

**Description**: Team member logs in with email and password

**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "email": "agent@company.com",
  "password": "SecurePassword123"
}
```

**Response Success (200)**:
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "member_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "agent@company.com",
    "name": "John Agent",
    "role": "agent",
    "assigned_bots": ["bot_id_1", "bot_id_2"]
  }
}
```

**Response Error (400)**:
```json
{
  "detail": "Invalid email or password"
}
```

**Response Error (403)**:
```json
{
  "detail": "Account has been deactivated"
}
```

---

### 3. Team Member Magic Link Login
**Endpoint**: `POST /auth/team-member/magic-link-login`

**Description**: Team member logs in using magic link token (passwordless)

**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "token": "magic_link_token_from_email"
}
```

**Response Success (200)**:
```json
{
  "status": "success",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "member_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "agent@company.com",
    "name": "John Agent",
    "role": "agent",
    "assigned_bots": ["bot_id_1", "bot_id_2"]
  }
}
```

**Response Error (400)**:
```json
{
  "detail": "Invalid or expired magic link token"
}
```

**Notes**: After successful login, the magic link token is marked as used and cannot be used again.

---

## 👥 Team Member Management Endpoints

### 4. Invite Team Member
**Endpoint**: `POST /api/owner/team-members/invite`

**Description**: Owner invites a new team member and assigns bots

**Headers**:
```
Authorization: Bearer <owner_access_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "email": "alice@company.com",
  "name": "Alice Support",
  "role": "agent",
  "assigned_bots": ["bot_id_1", "bot_id_2"]
}
```

**Response Success (200)**:
```json
{
  "member_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@company.com",
  "name": "Alice Support",
  "invite_sent": true,
  "magic_link_token": "secure_token_for_testing_only",
  "message": "Team member invited successfully. Check email for setup link."
}
```

**Response Error (400)**:
```json
{
  "detail": "Team member with this email already exists"
}
```

**Response Error (403)**:
```json
{
  "detail": "Only owners can invite team members"
}
```

**Notes**:
- Email is sent with magic link (if email service configured)
- Magic links expire in 48 hours
- Role can be: `"agent"` or `"supervisor"`
- `assigned_bots` is required array (can be empty)

---

### 5. List Team Members
**Endpoint**: `GET /api/owner/team-members`

**Description**: List all team members for the owner

**Headers**:
```
Authorization: Bearer <owner_access_token>
```

**Response Success (200)**:
```json
[
  {
    "member_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alice@company.com",
    "name": "Alice Support",
    "role": "agent",
    "assigned_bots": ["bot_id_1", "bot_id_2"],
    "is_active": true,
    "created_at": "2025-11-28T10:30:00.000Z",
    "confirmed_at": "2025-11-28T11:00:00.000Z"
  },
  {
    "member_id": "660e8400-e29b-41d4-a716-446655440001",
    "email": "bob@company.com",
    "name": "Bob Support",
    "role": "supervisor",
    "assigned_bots": ["bot_id_1", "bot_id_2", "bot_id_3"],
    "is_active": true,
    "created_at": "2025-11-27T09:15:00.000Z",
    "confirmed_at": "2025-11-27T10:00:00.000Z"
  }
]
```

**Response Error (403)**:
```json
{
  "detail": "Only owners can list team members"
}
```

---

### 6. Get Team Member Details
**Endpoint**: `GET /api/owner/team-members/{member_id}`

**Description**: Get specific team member details

**Headers**:
```
Authorization: Bearer <owner_access_token>
```

**URL Parameters**:
- `member_id` (required): UUID of team member

**Response Success (200)**:
```json
{
  "member_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@company.com",
  "name": "Alice Support",
  "role": "agent",
  "assigned_bots": ["bot_id_1", "bot_id_2"],
  "is_active": true,
  "created_at": "2025-11-28T10:30:00.000Z",
  "confirmed_at": "2025-11-28T11:00:00.000Z"
}
```

**Response Error (404)**:
```json
{
  "detail": "Team member not found"
}
```

---

### 7. Update Team Member
**Endpoint**: `PATCH /api/owner/team-members/{member_id}`

**Description**: Update team member role, assigned bots, or activation status

**Headers**:
```
Authorization: Bearer <owner_access_token>
Content-Type: application/json
```

**URL Parameters**:
- `member_id` (required): UUID of team member

**Request Body** (all fields optional):
```json
{
  "name": "Alice Support Senior",
  "role": "supervisor",
  "assigned_bots": ["bot_id_1", "bot_id_2", "bot_id_3"],
  "is_active": true
}
```

**Response Success (200)**:
```json
{
  "member_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@company.com",
  "name": "Alice Support Senior",
  "role": "supervisor",
  "assigned_bots": ["bot_id_1", "bot_id_2", "bot_id_3"],
  "is_active": true,
  "created_at": "2025-11-28T10:30:00.000Z",
  "confirmed_at": "2025-11-28T11:00:00.000Z"
}
```

**Notes**:
- Only provided fields are updated
- Cannot update email via this endpoint
- Changes take effect immediately
- If bots changed, member only sees new bots on next login

---

### 8. Delete Team Member (Deactivate)
**Endpoint**: `DELETE /api/owner/team-members/{member_id}`

**Description**: Deactivate a team member (soft delete)

**Headers**:
```
Authorization: Bearer <owner_access_token>
```

**URL Parameters**:
- `member_id` (required): UUID of team member

**Response Success (200)**:
```json
{
  "status": true,
  "message": "Team member deleted successfully"
}
```

**Response Error (404)**:
```json
{
  "detail": "Team member not found"
}
```

**Notes**:
- Member cannot log in after deactivation
- Data is not deleted, just marked inactive
- Can be reactivated by setting `is_active: true`

---

### 9. Resend Team Member Invitation
**Endpoint**: `POST /api/owner/team-members/{member_id}/resend-invite`

**Description**: Resend invitation email with new magic link token

**Headers**:
```
Authorization: Bearer <owner_access_token>
```

**URL Parameters**:
- `member_id` (required): UUID of team member

**Response Success (200)**:
```json
{
  "status": true,
  "message": "Invitation resent successfully",
  "token": "new_secure_magic_link_token"
}
```

**Response Error (404)**:
```json
{
  "detail": "Team member not found"
}
```

**Notes**:
- Generates new magic link token
- Old token is invalidated
- Email is resent with new link

---

## 🎯 Handoff Management Endpoints

### 10. Get Pending Handoffs (Role-Based Filtered)
**Endpoint**: `GET /api/agent/pending-handoffs`

**Description**: Get all pending handoffs (filtered by assigned bots for team members)

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response Success (200)** - As Team Member:
```json
{
  "status": true,
  "data": {
    "pending_count": 2,
    "agent_role": "team_member",
    "threads": [
      {
        "thread_id": "thread_123",
        "user_id": "user_456",
        "assistant_id": "bot_id_1",
        "status": "pending_handoff",
        "handoff_reason": "User asked for human help",
        "requested_at": "2025-11-28T14:30:00.000Z",
        "recent_messages": [
          {
            "role": "user",
            "content": "I need to speak with an agent",
            "timestamp": "2025-11-28T14:30:00.000Z"
          },
          {
            "role": "assistant",
            "content": "I'm connecting you with a human agent...",
            "timestamp": "2025-11-28T14:30:05.000Z"
          }
        ]
      }
    ]
  }
}
```

**Response Success (200)** - As Owner:
```json
{
  "status": true,
  "data": {
    "pending_count": 5,
    "agent_role": "owner",
    "threads": [
      {
        "thread_id": "thread_123",
        "user_id": "user_456",
        "assistant_id": "bot_id_1",
        "status": "pending_handoff",
        ...
      },
      ...
    ]
  }
}
```

**Notes**:
- Team members only see handoffs from assigned bots
- Owners see all handoffs
- Filtered at database level for security
- Results sorted by oldest first

---

### 11. Assign Thread to Agent
**Endpoint**: `POST /api/agent/assign/{thread_id}`

**Description**: Agent picks up a handoff

**Headers**:
```
Authorization: Bearer <access_token>
```

**URL Parameters**:
- `thread_id` (required): ID of the thread

**Response Success (200)**:
```json
{
  "status": true,
  "message": "Thread assigned to agent alice@company.com",
  "data": {
    "thread_id": "thread_123",
    "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
    "assigned_at": "2025-11-28T14:35:00.000Z"
  }
}
```

**Response Error (403)**:
```json
{
  "detail": "Thread not found, already assigned, or not assigned to your bots"
}
```

**Response Error (404)**:
```json
{
  "detail": "Thread not found"
}
```

**Notes**:
- Team members can only assign threads from assigned bots
- Thread status changes to "with_human"
- Only one agent can have thread at a time

---

### 12. Send Agent Message
**Endpoint**: `POST /api/agent/send-message`

**Description**: Agent sends response to user in a handoff

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "thread_id": "thread_123",
  "message": "Hi! I'm here to help. What seems to be the issue?"
}
```

**Response Success (200)**:
```json
{
  "status": true,
  "message": "Message sent to user",
  "data": {
    "chat_id": "chat_456",
    "message": "Hi! I'm here to help. What seems to be the issue?",
    "timestamp": "2025-11-28T14:40:00.000Z"
  }
}
```

**Response Error (403)**:
```json
{
  "detail": "Thread not assigned to you or not in handoff mode"
}
```

---

### 13. Complete Handoff
**Endpoint**: `POST /api/agent/complete-handoff`

**Description**: Agent completes handoff and returns thread to AI

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body**:
```json
{
  "thread_id": "thread_123",
  "notes": "User issue resolved. They needed billing assistance."
}
```

**Response Success (200)**:
```json
{
  "status": true,
  "message": "Handoff completed - thread returned to AI",
  "data": {
    "thread_id": "thread_123",
    "completed_at": "2025-11-28T14:50:00.000Z"
  }
}
```

**Response Error (403)**:
```json
{
  "detail": "Thread not assigned to you"
}
```

**Notes**:
- Thread status changes back to "active"
- AI can resume conversation
- Notes are stored for record-keeping
- Optional notes field

---

### 14. Get Agent Active Threads
**Endpoint**: `GET /api/agent/my-threads`

**Description**: Get all threads currently assigned to the agent

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response Success (200)**:
```json
{
  "status": true,
  "data": {
    "active_count": 3,
    "threads": [
      {
        "threadId": "thread_123",
        "userId": "user_456",
        "astId": "bot_id_1",
        "status": "with_human",
        "handoff": {
          "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
          "assigned_at": "2025-11-28T14:35:00.000Z"
        },
        "updatedAt": "2025-11-28T14:40:00.000Z"
      }
    ]
  }
}
```

---

## Error Codes Reference

| Code | Meaning | Common Cause |
|------|---------|-------------|
| 400 | Bad Request | Invalid input, expired token, invalid email format |
| 401 | Unauthorized | Missing/invalid token, token expired |
| 403 | Forbidden | User lacks permission (not owner, not assigned to bot) |
| 404 | Not Found | Team member/thread/bot doesn't exist |
| 409 | Conflict | Email already exists, duplicate operation |
| 500 | Internal Server Error | Server-side error, check logs |

---

## JWT Token Claims

### Owner Token
```json
{
  "sub": "owner_id_uuid",
  "email": "owner@company.com",
  "type": "access",
  "role": "owner",
  "is_team_member": false,
  "exp": 1733041200,
  "iat": 1732955800
}
```

### Team Member Token
```json
{
  "sub": "member_id_uuid",
  "email": "agent@company.com",
  "type": "access",
  "role": "agent",
  "is_team_member": true,
  "assigned_bots": ["bot_id_1", "bot_id_2"],
  "exp": 1733041200,
  "iat": 1732955800
}
```

---

## Request/Response Patterns

### Pagination (if implemented in future)
```
Query Parameters:
  ?page=1&limit=20

Response:
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

### Filtering Examples
```
GET /api/owner/team-members?role=agent
GET /api/owner/team-members?is_active=true
```

---

## Rate Limiting (if implemented)

Headers in response:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1733041200
```

---

## CORS & Security Headers

All endpoints support CORS if configured.

**Required Headers**:
```
Authorization: Bearer <token>
Content-Type: application/json (for POST/PATCH)
Origin: <client_origin>
```

---

## Webhook Events (Future Enhancement)

Possible events to implement:
```
handoff.created
handoff.assigned
handoff.completed
team_member.invited
team_member.confirmed
team_member.deactivated
```

---

## Rate Limiting Recommendations

- Authentication endpoints: 5 requests/minute per IP
- Handoff endpoints: 100 requests/minute per user
- Management endpoints: 50 requests/minute per user
- General endpoints: 1000 requests/hour per user

---

## Example cURL Commands

### Invite Team Member
```bash
curl -X POST http://localhost:8000/api/owner/team-members/invite \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@company.com",
    "name": "Alice Support",
    "role": "agent",
    "assigned_bots": ["bot_123"]
  }'
```

### Team Member Login
```bash
curl -X POST http://localhost:8000/auth/team-member/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@company.com",
    "password": "SecurePassword123"
  }'
```

### View Pending Handoffs
```bash
curl http://localhost:8000/api/agent/pending-handoffs \
  -H "Authorization: Bearer $TEAM_MEMBER_TOKEN"
```

### Pickup Handoff
```bash
curl -X POST http://localhost:8000/api/agent/assign/thread_123 \
  -H "Authorization: Bearer $TEAM_MEMBER_TOKEN"
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-28 | Initial release with team members, magic links, and role-based filtering |

---

## Support & Feedback

For issues or questions:
1. Check `docs/TEAM-MEMBERS-IMPLEMENTATION.md` for detailed explanations
2. Review `curl-team-members-test.sh` for working examples
3. Check API logs for error details
4. Verify MongoDB is running and indexes are created
