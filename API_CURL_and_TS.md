# API curl examples + TypeScript I/O types

This single reference file contains ready-to-run curl examples and TypeScript interfaces (input/output shapes) for the *Agent*, *Chat*, and *Thread* endpoints (including the updated `actions` output). Give this file to a backend operator to test and integrate the APIs.

Notes:
- Replace placeholders: BASE_URL, <YOUR_BEARER_TOKEN>, ASSISTANT_ID, THREAD_ID, AGENT_THREAD_ID, etc.
- All endpoints require Authorization using a bearer token unless otherwise noted.
- Dates/timestamps are ISO strings in responses.

## Common

Base URL (example):

- BASE_URL=https://api.example.com
- Authorization header: `Authorization: Bearer <YOUR_BEARER_TOKEN>`

Common TypeScript helpers:

```ts
// Generic API envelope used across endpoints
export interface ApiResponse<T = any> {
  status: boolean;
  message?: string;
  data?: T;
  // some endpoints (chat create) return top-level actions
  actions?: Action[] | null;
}

export interface Action {
  type: string; // e.g. 'handoff_to_human', 'send_link', 'send_email'
  data?: Record<string, any>; // action-specific payload
}
```

---

## Agent endpoints (prefix: /api/agent)

1) GET /api/agent/pending-handoffs

Description: List threads waiting for a human agent.

Curl:

```bash
curl -X GET "$BASE_URL/api/agent/pending-handoffs" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"
```

Response TypeScript:

```ts
export interface PendingHandoffsThreadPreview {
  thread_id: string;
  user_id: string;
  assistant_id: string;
  status: string; // e.g. 'pending_handoff'
  handoff_reason?: string | null;
  requested_at?: string | null; // ISO timestamp
  recent_messages: Array<{ role: 'user'|'assistant'; content: string; timestamp?: string | null }>;
}

export interface PendingHandoffsResponseData {
  pending_count: number;
  threads: PendingHandoffsThreadPreview[];
}

export type PendingHandoffsResponse = ApiResponse<PendingHandoffsResponseData>;
```

---

2) POST /api/agent/assign/{thread_id}

Description: Agent picks up and claims a pending thread.

Curl:

```bash
curl -X POST "$BASE_URL/api/agent/assign/$THREAD_ID" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"
```

Response TypeScript:

```ts
export interface AssignThreadData {
  thread_id: string;
  assigned_to: string; // agent id
  assigned_at: string; // ISO timestamp
}

export type AssignThreadResponse = ApiResponse<AssignThreadData>;
```

---

3) POST /api/agent/send-message

Description: Agent sends a message into the thread as a human.

Request body (JSON):
- thread_id: string
- message: string

Curl:

```bash
curl -X POST "$BASE_URL/api/agent/send-message" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"'$THREAD_ID'","message":"Hello from agent"}'
```

Request TypeScript:

```ts
export interface AgentSendMessageRequest {
  thread_id: string;
  message: string;
}
```

Response TypeScript:

```ts
export interface AgentSendMessageData {
  chat_id: string; // inserted chat document id
  message: string;
  timestamp: string;
}

export type AgentSendMessageResponse = ApiResponse<AgentSendMessageData>;
```

---

4) POST /api/agent/complete-handoff

Description: Agent completes handoff and returns thread to AI.

Request body (JSON):
- thread_id: string
- notes?: string

Curl:

```bash
curl -X POST "$BASE_URL/api/agent/complete-handoff" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"'$THREAD_ID'","notes":"Agent notes on resolution"}'
```

Request TypeScript:

```ts
export interface CompleteHandoffRequest {
  thread_id: string;
  notes?: string;
}
```

Response TypeScript:

```ts
export interface CompleteHandoffData {
  thread_id: string;
  completed_at: string;
}

export type CompleteHandoffResponse = ApiResponse<CompleteHandoffData>;
```

---

5) GET /api/agent/my-threads

Description: List threads currently assigned to the calling agent.

Curl:

```bash
curl -X GET "$BASE_URL/api/agent/my-threads" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"
```

Response TypeScript (threads are full thread documents from DB):

```ts
export type ThreadDocument = {
  _id?: string;
  threadId: string;
  userId: string;
  astId: string;
  threadTitle?: string;
  message_count?: number;
  status?: string;
  handoff?: any;
  createdAt?: string;
  updatedAt?: string;
};

export interface MyThreadsData {
  active_count: number;
  threads: ThreadDocument[];
}

export type MyThreadsResponse = ApiResponse<MyThreadsData>;
```

---

## Chat endpoints

1) POST /create-chat

Description: Send a message to an existing thread. This endpoint accepts form-data and optional file uploads.

Form fields:
- astId (string) — assistant id
- threadId (string) — thread id
- message (string)
- image (file) — optional, repeatable for multiple files

Curl (single image):

```bash
curl -X POST "$BASE_URL/create-chat" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>" \
  -F "astId=$ASSISTANT_ID" \
  -F "threadId=$THREAD_ID" \
  -F "message=Hello" \
  -F "image=@/path/to/file.jpg"
```

Curl (no files):

```bash
curl -X POST "$BASE_URL/create-chat" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>" \
  -F "astId=$ASSISTANT_ID" \
  -F "threadId=$THREAD_ID" \
  -F "message=Hello"
```

Response notes:
- The controller returns a top-level `actions` array when the assistant invoked functions that produced actions.
- `data` contains chat metadata (chat_id, assistant_response, tokens_used, used_rag, etc.).

Request TypeScript:

```ts
// For form-data use FormData in frontend; this interface is for server-side typing
export interface CreateChatForm {
  astId: string;
  threadId: string;
  message: string;
  // images are sent as File[] in FormData
}
```

Response TypeScript:

```ts
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

export interface ChatMessageDocument {
  _id?: string;
  userId?: string;
  astId?: string;
  threadId?: string;
  userMessage?: string | null;
  assistantResponse?: string | null;
  from_human?: boolean;
  human_agent_id?: string | null;
  images?: Array<{ filename: string; data?: string; content_type?: string }> | null;
  tokens_used?: number;
  used_custom_key?: boolean;
  actions?: Action[] | null;
  used_rag?: boolean;
  createdAt?: string;
}

export type CreateChatResponse = ApiResponse<ChatCreateData> & { actions?: Action[] | null };
```

Important: `actions` has this shape (example):

```ts
export type HandoffAction = {
  type: 'handoff_to_human';
  data: { reason?: string };
};
export type SendLinkAction = {
  type: 'send_link';
  data: { url: string; text?: string };
};
export type SendEmailAction = {
  type: 'send_email';
  data: { to: string; subject?: string; body?: string };
};

export type ActionUnion = HandoffAction | SendLinkAction | SendEmailAction | { type: string; data?: any };
```

---

2) GET /history/{thread_id}

Description: Get chat history for a thread (paginated by limit param).

Curl:

```bash
curl -X GET "$BASE_URL/history/$THREAD_ID?limit=50" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"
```

Response TypeScript:

```ts
export interface ChatHistoryData {
  thread_id: string;
  total_messages: number;
  messages: ChatMessageDocument[]; // as defined above
}

export type ChatHistoryResponse = ApiResponse<ChatHistoryData>;
```

---

## Thread endpoints

1) POST /create-thread

Description: Create a new thread for an assistant. Request body is JSON matching AssistantThread shape.

Request body (JSON):
- astId: string
- threadTitle: string

Curl:

```bash
curl -X POST "$BASE_URL/create-thread" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"astId":"'$ASSISTANT_ID'","threadTitle":"Support about billing"}'
```

Request TypeScript:

```ts
export interface AssistantThreadRequest {
  astId: string;
  threadTitle: string;
}
```

Response TypeScript (on success returns created thread document):

```ts
export interface ThreadCreateData {
  _id?: string;
  threadId: string; // provider thread id
  userId: string;
  astId: string;
  threadTitle?: string;
  message_count?: number;
  createdAt?: string;
  updatedAt?: string;
}

export type CreateThreadResponse = ApiResponse<ThreadCreateData>;
```

---

2) GET /get-thread/{assistant_id}

Description: List threads for an assistant owned by the user.

Curl:

```bash
curl -X GET "$BASE_URL/get-thread/$ASSISTANT_ID" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"
```

Response TypeScript:

```ts
export interface ThreadsByAssistantData {
  assistant_id: string;
  assistant_name?: string;
  total_threads: number;
  threads: ThreadDocument[]; // ThreadDocument defined earlier
}

export type ThreadsByAssistantResponse = ApiResponse<ThreadsByAssistantData>;
```

---

3) GET /get-thread-history/{thread_id}

Description: Retrieve message history for a thread. This delegates to OpenAI and returns the messages plus metadata.

Curl:

```bash
curl -X GET "$BASE_URL/get-thread-history/$THREAD_ID" \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"
```

Response TypeScript:

```ts
export interface GetThreadHistoryData {
  thread_id: string;
  thread_title?: string;
  messages: Array<{ role?: string; content?: string; /* as returned by openai_helper */ }>;
  message_count: number;
}

export type GetThreadHistoryResponse = ApiResponse<GetThreadHistoryData>;
```

---

## Quick examples

Create chat (JS fetch):

```ts
const fd = new FormData();
fd.append('astId', ASSISTANT_ID);
fd.append('threadId', THREAD_ID);
fd.append('message', 'Hello');
// fd.append('image', fileInput.files[0]);

fetch(`${BASE_URL}/create-chat`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${TOKEN}` },
  body: fd
});
```

Create thread (JS fetch):

```ts
fetch(`${BASE_URL}/create-thread`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ astId: ASSISTANT_ID, threadTitle: 'Billing question' })
});
```

---

If you want, I can also produce a small Postman collection or a shell script with all curl commands parameterized (but you asked for a single file only).
