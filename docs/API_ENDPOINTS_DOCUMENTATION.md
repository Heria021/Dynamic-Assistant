# API Endpoints Documentation

This document contains all API endpoints with cURL examples and TypeScript response interfaces.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Assistant Management](#assistant-management)
3. [Thread Management](#thread-management)
4. [Chat & Interactions](#chat--interactions)
5. [Agent Dashboard](#agent-dashboard)
6. [Channels Integration](#channels-integration)
7. [End-User API](#end-user-api)
8. [Usage & Analytics](#usage--analytics)
9. [Admin Panel](#admin-panel)
10. [Settings](#settings)
11. [Health](#health)

---

## Authentication

### Login

**Endpoint:** `POST /auth/login`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

**Response (TypeScript):**
```typescript
export interface AuthLoginResponse {
  status: boolean;
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  login_id: string;
}
```

---

### Refresh Token

**Endpoint:** `POST /auth/refresh`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/auth/refresh" \
  -H "Authorization: Bearer $REFRESH_TOKEN" \
  -H "Content-Type: application/json"
```

**Response (TypeScript):**
```typescript
export interface AuthRefreshResponse {
  status: string;
  access_token: string;
  token_type: "bearer";
}
```

---

### Get Current User

**Endpoint:** `GET /auth/me`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface UserProfile {
  id: string;
  email: string;
  is_confirmed: boolean;
  created_at: string;
  last_login: string;
}

export interface AuthMeResponse {
  status: "success" | "error";
  user?: UserProfile;
  message?: string;
}
```

---

## Assistant Management

### Create Assistant

**Endpoint:** `POST /api/assistant/create-assistant`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/assistant/create-assistant" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "astName": "My Support Bot",
    "astInstruction": "You are a helpful customer support assistant",
    "gptModel": "gpt-4",
    "astTools": ["retrieval", "code_interpreter"]
  }'
```

**Response (TypeScript):**
```typescript
export interface AssistantData {
  _id?: string;
  astId: string;
  userId: string;
  astName: string;
  astInstruction: string;
  gptModel: string;
  astTools: string[];
  file_ids?: string[];
  vector_store_id?: string;
  api_token?: string;
  apiToken?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface AssistantCreateResponse {
  status: boolean;
  message: string;
  data: AssistantData;
}
```

---

### Create Assistant with Files

**Endpoint:** `POST /api/assistant/create-assistant-with-file`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/assistant/create-assistant-with-file" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "astName=My Support Bot" \
  -F "astInstruction=You are a helpful customer support assistant" \
  -F "gptModel=gpt-4" \
  -F "astTools=retrieval" \
  -F "file=@/path/to/document.pdf"
```

**Response (TypeScript):**
```typescript
export interface FileData {
  fileId: string;
  fileName: string;
  uploadedAt?: string;
}

export interface AssistantCreateWithFileResponse {
  status: boolean;
  message: string;
  data: AssistantData;
  files?: FileData[];
}
```

---

### Get All Assistants

**Endpoint:** `GET /api/assistant/get-assistant`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/assistant/get-assistant" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface AssistantListResponse {
  status: boolean;
  message: string;
  data: AssistantData[];
}
```

---

### Get Assistant by ID

**Endpoint:** `GET /api/assistant/get-assistant/{ast_id}`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/assistant/get-assistant/asst_12345" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface AssistantGetByIdResponse {
  status: boolean;
  message: string;
  data: AssistantData;
}
```

---

### Update Assistant

**Endpoint:** `PUT /api/assistant/update-assistant`

**cURL:**
```bash
curl -X PUT "http://127.0.0.1:8000/api/assistant/update-assistant" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "astId": "asst_12345",
    "astName": "Updated Bot Name",
    "astInstruction": "Updated instructions",
    "gptModel": "gpt-4-turbo"
  }'
```

**Response (TypeScript):**
```typescript
export interface AssistantUpdateResponse {
  status: boolean;
  message: string;
  data: AssistantData;
}
```

---

### Delete Assistant

**Endpoint:** `DELETE /api/assistant/delete-assistant/{ast_id}`

**cURL:**
```bash
curl -X DELETE "http://127.0.0.1:8000/api/assistant/delete-assistant/asst_12345" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface AssistantDeleteResponse {
  status: boolean;
  message: string;
}
```

---

### Upload Assistant Files

**Endpoint:** `POST /api/assistant/upload-assistant-files/{ast_id}`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/assistant/upload-assistant-files/asst_12345" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/path/to/document.pdf"
```

**Response (TypeScript):**
```typescript
export interface AssistantUploadFilesResponse {
  status: boolean;
  message: string;
  data: {
    files: FileData[];
  };
}
```

---

## Thread Management

### Create Thread

**Endpoint:** `POST /api/threads/create-thread`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/threads/create-thread" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "astId": "asst_12345",
    "threadTitle": "Support Request"
  }'
```

**Response (TypeScript):**
```typescript
export interface HandoffData {
  requested_at: string;
  reason: string;
  assigned_to?: string | null;
  assigned_at?: string | null;
  completed_at?: string | null;
  notes: string;
}

export interface ThreadDocument {
  _id?: string;
  threadId: string;
  userId: string;
  astId: string;
  threadTitle?: string;
  message_count?: number;
  status?: string;
  handoff?: HandoffData | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface ThreadCreateResponse {
  status: boolean;
  message: string;
  data: ThreadDocument;
}
```

---

### Get Threads by Assistant

**Endpoint:** `GET /api/threads/get-thread/{assistant_id}`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/threads/get-thread/asst_12345" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface ThreadsByAssistantData {
  assistant_id: string;
  assistant_name?: string;
  total_threads: number;
  threads: ThreadDocument[];
}

export interface ThreadsByAssistantResponse {
  status: boolean;
  message: string;
  data: ThreadsByAssistantData;
}
```

---

### Get Thread History

**Endpoint:** `GET /api/threads/get-thread-history/{thread_id}`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/threads/get-thread-history/thread_abc123" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface MessageDocument {
  id: string;
  role: "user" | "assistant";
  message: string;
  thread_id: string;
  created_at: number;
  images?: Array<{ filename: string; data?: string; content_type?: string }> | null;
  from_human?: boolean;
}

export interface ThreadHistoryData {
  thread_id: string;
  thread_title?: string;
  messages: MessageDocument[];
  message_count: number;
}

export interface ThreadHistoryResponse {
  status: boolean;
  message: string;
  data: ThreadHistoryData;
}
```

---

## Chat & Interactions

### Create Chat (Send Message)

**Endpoint:** `POST /api/chats/create-chat`

**Note:** This handles RAG and Function Calling automatically.

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/chats/create-chat" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "astId=asst_12345" \
  -F "threadId=thread_abc123" \
  -F "message=I need to speak to a human agent"
```

**Response (TypeScript):**
```typescript
export interface ChatAction {
  type: "handoff_to_human" | "send_link" | "send_email" | string;
  data: Record<string, any>;
}

export interface ChatCreateData {
  chat_id: string;
  user_message: string;
  assistant_response: string;
  tokens_used: number;
  used_custom_key: boolean;
  used_rag: boolean;
  images_count: number;
  timestamp: string;
}

export interface ChatCreateResponse {
  status: boolean;
  message: string;
  data: ChatCreateData;
  actions?: ChatAction[] | null;
}
```

---

### Get Chat History

**Endpoint:** `GET /api/chats/history/{thread_id}`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/chats/history/thread_abc123" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface ChatHistoryData {
  thread_id: string;
  total_messages: number;
  messages: MessageDocument[];
}

export interface ChatHistoryResponse {
  status: boolean;
  message: string;
  data: ChatHistoryData;
}
```

---

## Agent Dashboard

### Get Pending Handoffs

**Endpoint:** `GET /api/agent/pending-handoffs`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/agent/pending-handoffs" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface PendingHandoffsThreadPreview {
  thread_id: string;
  user_id: string;
  assistant_id: string;
  status: string;
  handoff_reason?: string | null;
  requested_at?: string | null;
  recent_messages: Array<{
    role: "user" | "assistant";
    content: string;
    timestamp?: string | null;
  }>;
}

export interface PendingHandoffsData {
  pending_count: number;
  threads: PendingHandoffsThreadPreview[];
}

export interface AgentPendingHandoffsResponse {
  status: boolean;
  message: string;
  data: PendingHandoffsData;
}
```

---

### Assign Thread to Agent

**Endpoint:** `POST /api/agent/assign/{thread_id}`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/agent/assign/thread_abc123" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "user_agent_123"
  }'
```

**Response (TypeScript):**
```typescript
export interface AssignThreadData {
  thread_id: string;
  assigned_to: string;
  assigned_at: string;
}

export interface AgentAssignThreadResponse {
  status: boolean;
  message: string;
  data: AssignThreadData;
}
```

---

### Agent Send Message

**Endpoint:** `POST /api/agent/send-message`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/agent/send-message" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_abc123",
    "message": "I can help you with that"
  }'
```

**Response (TypeScript):**
```typescript
export interface AgentSendMessageData {
  chat_id: string;
  message: string;
  timestamp: string;
}

export interface AgentSendMessageResponse {
  status: boolean;
  message: string;
  data: AgentSendMessageData;
}
```

---

### Complete Handoff

**Endpoint:** `POST /api/agent/complete-handoff`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/agent/complete-handoff" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_abc123"
  }'
```

**Response (TypeScript):**
```typescript
export interface CompleteHandoffData {
  thread_id: string;
  completed_at: string;
}

export interface AgentCompleteHandoffResponse {
  status: boolean;
  message: string;
  data: CompleteHandoffData;
}
```

---

### Get Agent's Assigned Threads

**Endpoint:** `GET /api/agent/my-threads`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/agent/my-threads" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface MyThreadsData {
  active_count: number;
  threads: ThreadDocument[];
}

export interface AgentMyThreadsResponse {
  status: boolean;
  message: string;
  data: MyThreadsData;
}
```

---

## Channels Integration

### Get Channels Assistant Info

**Endpoint:** `POST /api/channel/channels-ast-info`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/channel/channels-ast-info" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_ids": ["channel_1", "channel_2"]
  }'
```

**Response (TypeScript):**
```typescript
export interface ChannelAssistantInfo {
  astId: string;
  astName: string;
  api_token?: string;
  apiToken?: string;
  gptModel?: string;
  file_ids?: string[];
}

export interface ChannelsAstInfoResponse {
  status: boolean;
  message: string;
  data: ChannelAssistantInfo[];
}
```

---

### Channels API Integration

**Endpoint:** `POST /api/channel/channels-api-integration`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/channel/channels-api-integration" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel_id": "channel_1",
    "astId": "asst_12345"
  }'
```

**Response (TypeScript):**
```typescript
export interface ChannelsApiIntegrationResponse {
  status: boolean;
  message: string;
  data: {
    channel_id?: string;
    created_at?: string;
  };
}
```

---

## End-User API

### End-User Chat

**Endpoint:** `POST /api/enduser/end-user-chat`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/enduser/end-user-chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have a question",
    "threadtoken": "thread_token_xyz"
  }'
```

**Response (TypeScript):**
```typescript
export interface EndUserChatData {
  message: string;
  threadtoken: string;
  thread_id?: string;
  chat_id?: string;
  timestamp?: string;
  used_rag?: boolean;
}

export interface EndUserChatResponse {
  status: boolean;
  message: string;
  data: EndUserChatData;
  actions?: ChatAction[] | null;
}
```

---

## Usage & Analytics

### Get Usage History

**Endpoint:** `GET /usage/history`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/usage/history?limit=100&offset=0" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface UsageHistoryItem {
  timestamp: string;
  action: string;
  assistantId?: string;
  threadId?: string;
  tokens_used: number;
  model_used: string;
  cost_estimate: number;
}

export interface UsageHistoryResponse {
  status: boolean;
  message: string;
  data: {
    user_id: string;
    total_records: number;
    items: UsageHistoryItem[];
  };
}
```

---

### Get Cost Breakdown

**Endpoint:** `GET /usage/cost-breakdown`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/usage/cost-breakdown?period=monthly" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface CostBreakdownItem {
  assistant_id: string;
  assistant_name: string;
  messages: number;
  tokens: number;
  cost: number;
}

export interface UsageCostBreakdownResponse {
  status: boolean;
  message: string;
  data: {
    period: string;
    total_cost: number;
    breakdown: CostBreakdownItem[];
  };
}
```

---

### Export Usage Data

**Endpoint:** `GET /usage/export`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/usage/export?format=json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface UsageExportData {
  user_id: string;
  exported_at: string;
  total_records: number;
  items: UsageHistoryItem[];
}

export interface UsageExportResponse {
  status: boolean;
  message: string;
  data: UsageExportData;
}
```

---

## Admin Panel

### Get Admin Statistics

**Endpoint:** `GET /admin/stats`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/admin/stats" \
  -H "Authorization: Bearer $ADMIN_ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface AdminStatsData {
  total_users: number;
  total_assistants: number;
  total_threads: number;
  total_messages: number;
  active_users_today: number;
}

export interface AdminStatsResponse {
  status: boolean;
  message: string;
  data: AdminStatsData;
}
```

---

## Settings

### Get Settings

**Endpoint:** `GET /settings`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/settings" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Response (TypeScript):**
```typescript
export interface SettingsData {
  setting_key: string;
  setting_value: any;
  updated_at?: string;
}

export interface SettingsGetResponse {
  status: boolean;
  message: string;
  data: SettingsData[];
}
```

---

### Update Settings

**Endpoint:** `POST /settings`

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/settings" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "setting_key": "theme",
    "setting_value": "dark"
  }'
```

**Response (TypeScript):**
```typescript
export interface SettingsSetResponse {
  status: boolean;
  message: string;
  data: SettingsData;
}
```

---

## Health

### Health Check

**Endpoint:** `GET /health`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/health"
```

**Response (TypeScript):**
```typescript
export interface HealthResponse {
  status: string;
  message?: string;
}
```

---

## Common Types

```typescript
/**
 * Common types used across multiple endpoints
 */

export interface Action {
  type: string;
  data: Record<string, any>;
}

export interface ApiResponse<T = any> {
  status: boolean;
  message?: string;
  data?: T;
  actions?: Action[] | null;
}

export interface ChatAction {
  type: "handoff_to_human" | "send_link" | "send_email" | string;
  data: Record<string, any>;
}

export interface MessageDocument {
  id: string;
  role: "user" | "assistant";
  message: string;
  thread_id: string;
  created_at: number;
  images?: Array<{ filename: string; data?: string; content_type?: string }> | null;
  from_human?: boolean;
}
```

---

## Usage Notes

- All endpoints require `Authorization: Bearer $ACCESS_TOKEN` header (except `/health` and `/api/enduser/end-user-chat`)
- Replace placeholders like `asst_12345`, `thread_abc123`, etc. with actual IDs
- Environment variables: `$ACCESS_TOKEN`, `$REFRESH_TOKEN`, `$ADMIN_ACCESS_TOKEN`
- POST requests use `Content-Type: application/json` unless otherwise specified
- File upload endpoints use multipart form data (`-F` flag in cURL)
- All responses follow the standard `{status, message, data}` format
- Some endpoints include optional `actions` array for function calling/automation

