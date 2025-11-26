# Assistant API Authentication & Integration Guide

## Auth Flow Summary

1. **Sign in**: POST `/auth/login` with email & password → returns `access_token` and `refresh_token`.
2. **Use token**: Include `access_token` in Authorization header for secured assistant API calls: `Authorization: Bearer <access_token>`.
3. **Refresh token**: When `access_token` expires, call POST `/auth/refresh` with `{ "refresh_token": "<refresh_token>" }` to get a new access token.
4. **(Optional) Validate token**: GET `/auth/me` can be used to validate token and fetch user profile.

---

## Authentication Endpoints

### Login Request / Response

**POST** `/auth/login`

Request:
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

Response (success - 200):
```json
{
  "status": true,
  "message": "Login successful",
  "access_token": "<jwt-access-token>",
  "refresh_token": "<jwt-refresh-token>",
  "token_type": "bearer",
  "login_id": "<user-id>"
}
```

**Notes:**
- Use `access_token` for resource calls.
- `token_type` is "bearer". Prefix with "Bearer " when setting Authorization header.
- Store `refresh_token` securely (preferably in httpOnly cookie or secure storage, NOT localStorage).
- `login_id` is the authenticated user's unique identifier.

### Using the Token

For all protected assistant endpoints, include the Authorization header:

```
Authorization: Bearer <access_token>
```

**Error responses:**
- **401 Unauthorized**: Token is invalid or expired — refresh token or prompt user to re-authenticate.
- **400 Bad Request**: Invalid input or not allowed (e.g., unconfirmed email).

### Refresh Token

**POST** `/auth/refresh`

Request:
```json
{
  "refresh_token": "<refresh-token>"
}
```

Response (success - 200):
```json
{
  "status": "success",
  "access_token": "<new-jwt-access-token>",
  "token_type": "bearer"
}
```

**Error responses:**
- **401 Unauthorized**: Invalid or expired refresh token — redirect user to login.

### Get Current User

**GET** `/auth/me`

Headers:
```
Authorization: Bearer <access_token>
```

Response (success - 200):
```json
{
  "status": "success",
  "user": {
    "id": "<user-id>",
    "email": "user@example.com",
    "is_confirmed": true,
    "created_at": "2025-11-25T10:00:00Z",
    "last_login": "2025-11-25T15:30:00Z"
  }
}
```

---

## Assistant API Endpoints

### 1. Create Assistant

**POST** `/create-assistant`

**Purpose:** Create a new assistant with metadata (JSON body).

Headers:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request body:
```json
{
  "astName": "My Assistant",
  "astInstruction": "You are a helpful assistant for customer support.",
  "gptModel": "gpt-4",
  "astTools": ["tool1", "tool2"]
}
```

Response (success - 200):
```json
{
  "status": true,
  "message": "Assistant created successfully",
  "data": {
    "astId": "<assistant-id>",
    "astName": "My Assistant",
    ...
  }
}
```

### 2. Create Assistant with Files

**POST** `/create-assistant-with-file`

**Purpose:** Create a new assistant and upload associated files (e.g., PDFs, documents) at creation time.

Headers:
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Form fields:
- `files` (multiple files): Files to attach to the assistant.
- `astName` (text): Assistant name.
- `astInstruction` (text): System instruction/behavior.
- `gptModel` (text): Model identifier (e.g., "gpt-4").
- `astTools` (text, JSON): Array of tool names as JSON string, e.g., `["tool1", "tool2"]`.

Response (success - 200):
```json
{
  "status": true,
  "message": "Assistant created successfully",
  "data": {
    "astId": "<assistant-id>",
    "astName": "My Assistant",
    ...
  }
}
```

### 3. Upload Assistant Files

**POST** `/upload-assistant-files/{ast_id}`

**Purpose:** Upload one or more files to an existing assistant.

Headers:
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

Path parameter:
- `ast_id` (string): ID of the target assistant.

Form field:
- `files` (multiple files): Files to upload.

Response (success - 200):
```json
{
  "status": true,
  "message": "Files uploaded successfully",
  "data": {
    "uploadedFiles": [...]
  }
}
```

### 4. Get All Assistants

**GET** `/get-assistant`

**Purpose:** Fetch all assistants belonging to the authenticated user.

Headers:
```
Authorization: Bearer <access_token>
```

Response (success - 200):
```json
{
  "status": true,
  "message": "Assistants fetched successfully",
  "data": [
    {
      "astId": "<assistant-id>",
      "astName": "My Assistant",
      "astInstruction": "...",
      "gptModel": "gpt-4",
      ...
    }
  ]
}
```

### 5. Get Assistant by ID

**GET** `/get-assistant/{ast_id}`

**Purpose:** Fetch a specific assistant by its ID.

Headers:
```
Authorization: Bearer <access_token>
```

Path parameter:
- `ast_id` (string): ID of the assistant.

Response (success - 200):
```json
{
  "status": true,
  "message": "Assistant fetched successfully",
  "data": {
    "astId": "<assistant-id>",
    "astName": "My Assistant",
    "astInstruction": "...",
    "gptModel": "gpt-4",
    ...
  }
}
```

### 6. Update Assistant

**PUT** `/update-assistant`

**Purpose:** Update assistant metadata (name, instruction, model, tools).

Headers:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request body (must include `astId`):
```json
{
  "astId": "<assistant-id>",
  "astName": "Updated Assistant Name",
  "astInstruction": "Updated instruction...",
  "gptModel": "gpt-4-turbo",
  "astTools": ["tool1", "tool2", "tool3"]
}
```

Response (success - 200):
```json
{
  "status": true,
  "message": "Assistant updated successfully",
  "data": {
    "astId": "<assistant-id>",
    "astName": "Updated Assistant Name",
    ...
  }
}
```

---

## TypeScript Integration Guide

### 1. TypeScript Interfaces

```typescript
// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  status: boolean;
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  login_id: string;
}

export interface RefreshResponse {
  status: string;
  access_token: string;
  token_type: "bearer";
}

// Assistant types
export interface Assistant {
  astName: string;
  astInstruction: string;
  gptModel: string;
  astTools: string[];
}

export interface UpdateAssistant extends Assistant {
  astId: string;
}

export interface AssistantResponse {
  status: boolean;
  message: string;
  data: any;
}

export interface UserProfile {
  id: string;
  email: string;
  is_confirmed: boolean;
  created_at: string;
  last_login: string;
}
```

### 2. Helper: Authorization Header

```typescript
function authHeader(token: string): Record<string, string> {
  return { "Authorization": `Bearer ${token}` };
}
```

### 3. Login (Fetch)

```typescript
async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (!res.ok) {
    throw new Error(`Login failed: ${res.statusText}`);
  }
  
  return res.json();
}
```

### 4. Create Assistant (JSON Body)

```typescript
async function createAssistant(
  accessToken: string,
  assistant: Assistant
): Promise<AssistantResponse> {
  const res = await fetch('/create-assistant', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(accessToken),
    },
    body: JSON.stringify(assistant),
  });
  
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Failed to create assistant');
  }
  
  return res.json();
}
```

### 5. Create Assistant with Files (Axios)

```typescript
import axios from 'axios';

async function createAssistantWithFiles(
  accessToken: string,
  assistant: Assistant,
  files: File[]
): Promise<AssistantResponse> {
  const form = new FormData();
  
  // Attach files (multiple)
  files.forEach((f) => form.append('files', f));
  
  // Attach assistant fields individually as text fields
  form.append('astName', assistant.astName);
  form.append('astInstruction', assistant.astInstruction);
  form.append('gptModel', assistant.gptModel);
  
  // For array, send as JSON string
  form.append('astTools', JSON.stringify(assistant.astTools));

  const res = await axios.post('/create-assistant-with-file', form, {
    headers: {
      'Content-Type': 'multipart/form-data',
      Authorization: `Bearer ${accessToken}`,
    },
  });
  
  return res.data;
}
```

**Note:** If the backend expects form fields named exactly like the Pydantic model properties (`astName`, `astInstruction`, etc.), sending them as separate form fields works well. For arrays, JSON-stringify them unless the backend explicitly parses multiple keys.

### 6. Upload Files to Existing Assistant (Axios)

```typescript
async function uploadAssistantFiles(
  accessToken: string,
  astId: string,
  files: File[]
): Promise<AssistantResponse> {
  const form = new FormData();
  files.forEach(f => form.append('files', f));

  const res = await axios.post(
    `/upload-assistant-files/${encodeURIComponent(astId)}`,
    form,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );
  
  return res.data;
}
```

### 7. Get All Assistants (Fetch)

```typescript
async function getAssistants(accessToken: string): Promise<AssistantResponse> {
  const res = await fetch('/get-assistant', {
    method: 'GET',
    headers: {
      ...authHeader(accessToken),
      'Content-Type': 'application/json'
    },
  });
  
  if (!res.ok) throw new Error('Failed to fetch assistants');
  return res.json();
}
```

### 8. Get Assistant by ID (Fetch)

```typescript
async function getAssistantById(
  accessToken: string,
  id: string
): Promise<AssistantResponse> {
  const res = await fetch(`/get-assistant/${encodeURIComponent(id)}`, {
    headers: authHeader(accessToken)
  });
  
  if (!res.ok) throw new Error('Failed to fetch assistant');
  return res.json();
}
```

### 9. Update Assistant (Fetch)

```typescript
async function updateAssistant(
  accessToken: string,
  update: UpdateAssistant
): Promise<AssistantResponse> {
  const res = await fetch('/update-assistant', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...authHeader(accessToken),
    },
    body: JSON.stringify(update),
  });
  
  if (!res.ok) throw new Error('Failed to update assistant');
  return res.json();
}
```

### 10. Refresh Access Token (Fetch)

```typescript
async function refreshAccessToken(refreshToken: string): Promise<RefreshResponse> {
  const res = await fetch('/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  
  if (!res.ok) {
    throw new Error('Refresh token failed');
  }
  
  return res.json();
}
```

### 11. Error Handling Patterns

```typescript
// Retry pattern with token refresh
async function apiCallWithRetry<T>(
  apiCall: () => Promise<T>,
  refreshToken: string,
  onTokenRefresh: (newToken: string) => void
): Promise<T> {
  try {
    return await apiCall();
  } catch (error: any) {
    if (error?.response?.status === 401) {
      // Token expired, attempt refresh
      try {
        const refreshed = await refreshAccessToken(refreshToken);
        onTokenRefresh(refreshed.access_token);
        // Retry original call
        return await apiCall();
      } catch (refreshError) {
        // Refresh failed, redirect to login
        console.error('Refresh failed, redirecting to login');
        throw new Error('Session expired, please log in again');
      }
    }
    throw error;
  }
}
```

### 12. Axios Interceptor Pattern (Optional)

```typescript
import axios from 'axios';

let accessToken = '';
let refreshToken = '';

// Response interceptor for auto-refresh
axios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshed = await refreshAccessToken(refreshToken);
        accessToken = refreshed.access_token;
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return axios(originalRequest);
      } catch (refreshError) {
        // Redirect to login on refresh failure
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);
```

---

## End-to-End Example (Minimal TypeScript + Axios)

```typescript
import axios from 'axios';

class AssistantClient {
  private accessToken: string = '';
  private refreshToken: string = '';

  async login(email: string, password: string): Promise<void> {
    const response = await login(email, password);
    this.accessToken = response.access_token;
    this.refreshToken = response.refresh_token;
  }

  async createAssistant(assistant: Assistant): Promise<AssistantResponse> {
    return createAssistant(this.accessToken, assistant);
  }

  async createAssistantWithFiles(
    assistant: Assistant,
    files: File[]
  ): Promise<AssistantResponse> {
    return createAssistantWithFiles(this.accessToken, assistant, files);
  }

  async uploadFiles(astId: string, files: File[]): Promise<AssistantResponse> {
    return uploadAssistantFiles(this.accessToken, astId, files);
  }

  async getAssistants(): Promise<AssistantResponse> {
    return getAssistants(this.accessToken);
  }

  async getAssistant(id: string): Promise<AssistantResponse> {
    return getAssistantById(this.accessToken, id);
  }

  async updateAssistant(update: UpdateAssistant): Promise<AssistantResponse> {
    return updateAssistant(this.accessToken, update);
  }

  async refreshToken(): Promise<void> {
    const response = await refreshAccessToken(this.refreshToken);
    this.accessToken = response.access_token;
  }
}

// Usage example:
async function main() {
  const client = new AssistantClient();
  
  // 1. Login
  await client.login('user@example.com', 'password123');
  
  // 2. Create assistant
  const createResponse = await client.createAssistant({
    astName: 'My Support Bot',
    astInstruction: 'Help users with their inquiries.',
    gptModel: 'gpt-4',
    astTools: ['search', 'email']
  });
  
  const astId = createResponse.data.astId;
  
  // 3. Fetch all assistants
  const allAssistants = await client.getAssistants();
  console.log('My assistants:', allAssistants.data);
  
  // 4. Update assistant
  await client.updateAssistant({
    astId,
    astName: 'Updated Support Bot',
    astInstruction: 'Updated instruction...',
    gptModel: 'gpt-4-turbo',
    astTools: ['search', 'email', 'calendar']
  });
}

main().catch(console.error);
```

---

## Security Best Practices

1. **Token Storage:**
   - Store `access_token` in memory or session storage for immediate access.
   - Store `refresh_token` in a **httpOnly cookie** (not accessible to JavaScript) for enhanced security in browser environments.
   - On Node.js/backend, use secure session storage or environment variables.

2. **Token Refresh:**
   - Implement automatic refresh before token expiry (e.g., refresh when 1 minute remains).
   - On 401 responses, attempt refresh once; if it fails, redirect user to login.

3. **HTTPS:**
   - Always use HTTPS in production to prevent token interception.

4. **CORS:**
   - Configure CORS properly to only allow requests from trusted domains.

5. **Error Messages:**
   - Avoid exposing sensitive information in error messages to end users.
   - Log detailed errors server-side for debugging.

---

## Common HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Use the returned data. |
| 400 | Bad Request | Check request format and required fields. |
| 401 | Unauthorized | Token is invalid/expired; refresh or re-login. |
| 403 | Forbidden | User doesn't have permission. |
| 404 | Not Found | Resource (e.g., assistant) doesn't exist. |
| 500 | Server Error | Server-side issue; retry later or contact support. |

---

## Additional Resources

- **Authentication Flow**: See "Auth Flow Summary" at the top of this document.
- **Token Refresh**: Use the `/auth/refresh` endpoint to obtain a new access token before expiry.
- **User Info**: Call `/auth/me` with a valid access token to get current user details.

---

## Questions or Issues?

If you encounter any issues or have questions about the API:

1. Check HTTP status codes and error messages in responses.
2. Ensure the Authorization header is formatted correctly: `Bearer <token>`.
3. Verify that tokens are not expired before making requests.
4. Contact the backend team with detailed error logs if the issue persists.

---

**Last Updated:** November 25, 2025
