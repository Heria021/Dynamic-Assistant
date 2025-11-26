# 🚀 Minor Assistant API - Complete Application Documentation

**Version:** 1.0  
**Status:** ✅ Production Ready  
**Last Updated:** November 26, 2025  
**Framework:** FastAPI (Python)  
**Database:** MongoDB

---

## 📋 Table of Contents

1. [Purpose of the Application](#purpose-of-the-application)
2. [Core Features](#core-features)
3. [System Architecture](#system-architecture)
4. [API Endpoints & Features](#api-endpoints--features)
5. [Feature Implementation Pipeline](#feature-implementation-pipeline)
6. [Task Workflow & Operations](#task-workflow--operations)
7. [Epics Overview](#epics-overview)
8. [Technical Stack](#technical-stack)
9. [Setup & Deployment](#setup--deployment)

---

## 🎯 Purpose of the Application

### Mission
The **Minor Assistant API** is a sophisticated backend service that bridges OpenAI's Assistant API with a multi-user platform, enabling organizations to:

- **Create and manage AI assistants** with custom instructions and capabilities
- **Facilitate multi-threaded conversations** with persistent state management
- **Enable secure API integration** through third-party channels
- **Provide end-user chat interfaces** without exposing admin credentials
- **Store and manage conversation history** with vector search capabilities
- **Support file uploads** for context-aware AI responses
- **Handle user authentication** with JWT-based security

### Key Use Cases

1. **Internal Team Collaboration**: Create assistants for internal processes
2. **Customer Support Automation**: Deploy assistants for customer interactions
3. **Knowledge Management**: Build AI systems that reference uploaded documents
4. **Multi-channel Integration**: Connect assistants to various platforms (channels)
5. **Enterprise Solutions**: Support multiple users with role-based access

---

## ✨ Core Features

### 1. **Authentication & User Management**
- Email-based sign-up and login
- JWT token-based authorization
- Email verification workflow
- Password reset functionality
- Token refresh mechanism
- Secure credential management

### 2. **Assistant Management**
- Create custom AI assistants with specific instructions
- Define assistant capabilities (tools/models)
- Update assistant configurations
- List all assistants for a user
- Support for multiple GPT models (gpt-4o-mini, gpt-4o, etc.)
- File attachment support for knowledge base

### 3. **Conversation Threading**
- Create isolated conversation threads
- Manage multiple conversations per assistant
- Retrieve thread history
- Thread-level message organization
- Persistent conversation state

### 4. **Chat Messaging**
- Send messages to assistants
- Support for text and image inputs
- Receive AI-generated responses
- Chat history tracking
- Message content processing

### 5. **Channel Integration**
- API token-based third-party access
- Channel-specific assistant configuration
- Integration verification
- Webhook-ready architecture

### 6. **End-User API**
- Public API for end-users (without authentication)
- Thread token generation
- Simplified chat creation
- Direct assistant access via API tokens
- No authentication required for end-users

### 7. **File Management**
- Upload files to assistants
- PDF and document support
- Vector database integration
- File search and retrieval
- Content vectorization for semantic search

---

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATIONS                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Web App  │  │  Mobile  │  │ 3rd Party│  │  Direct  │        │
│  │          │  │  Client  │  │ Channel  │  │  Clients │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API ROUTERS (6 Main Routes)                 │  │
│  │  ┌────────────┬──────────┬─────────┬────────┬────────┐   │  │
│  │  │  Auth     │ Assistant│ Threads │ Chats  │ Channel│   │  │
│  │  └────────────┴──────────┴─────────┴────────┴────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              CONTROLLERS (Business Logic)                │  │
│  │  ├─ auth_controller.py                                   │  │
│  │  ├─ assistant.py                                         │  │
│  │  ├─ threads.py                                           │  │
│  │  ├─ chats.py                                             │  │
│  │  ├─ channels.py                                          │  │
│  │  └─ cognito.py                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    UTILITIES & SERVICES                  │  │
│  │  ├─ openai_helper.py (OpenAI API Integration)           │  │
│  │  ├─ mongo_utils.py (Database Operations)                │  │
│  │  ├─ vector_utils.py (Vector Database)                   │  │
│  │  ├─ ocr_pdf_utils.py (Document Processing)              │  │
│  │  └─ email_service.py (Email Notifications)              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DATA & EXTERNAL SERVICES                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   MongoDB    │  │  OpenAI API  │  │  Gmail API   │          │
│  │   Database   │  │  (Assistants)│  │  (Email)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Architecture

```
User Request
    │
    ▼
┌─────────────────────┐
│ JWT Authentication  │
│ Token Verification  │
└─────────────────────┘
    │
    ├─ Invalid → 401 Unauthorized
    │
    └─ Valid
        ▼
   ┌────────────────────┐
   │ Route Handler      │
   │ (Router)           │
   └────────────────────┘
        │
        ▼
   ┌────────────────────┐
   │ Controller Logic   │
   │ Business Rules     │
   └────────────────────┘
        │
        ├─────────────────────┬──────────────────────┐
        ▼                     ▼                      ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │ Database Ops │   │ OpenAI Calls │   │ Email Sends  │
   │ (MongoDB)    │   │ (AI Response)│   │ (Alerts)     │
   └──────────────┘   └──────────────┘   └──────────────┘
        │                     │                      │
        └─────────────────────┴──────────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │ Response Formatting     │
            │ Status + Data + Message │
            └─────────────────────────┘
                        │
                        ▼
                  Client Application
```

---

## 🔌 API Endpoints & Features

### 1️⃣ **Authentication Endpoints** (`/auth`)

#### Feature: User Registration & Email Verification

**Endpoints:**
```
POST   /auth/sign-up                    - Create new user account
POST   /auth/confirm-sign-up            - Verify email with code
POST   /auth/resend-verification        - Resend verification email
```

**Workflow:**
```
1. User submits email + password
   ↓
2. System hashes password & generates verification code
   ↓
3. Email sent to user with verification code
   ↓
4. User confirms with email + verification code
   ↓
5. Account activated, user can login
```

---

#### Feature: Authentication & Token Management

**Endpoints:**
```
POST   /auth/login                      - User login & token generation
POST   /auth/refresh                    - Refresh access token
GET    /auth/me                         - Get current user profile
```

**Workflow:**
```
1. User login with email + password
   ↓
2. Password verified against hash
   ↓
3. JWT access & refresh tokens generated
   ↓
4. Tokens returned to client
   ↓
5. Client uses access token for authenticated requests
```

**Token Structure:**
```
- Access Token: Short-lived (15-30 min) for API requests
- Refresh Token: Long-lived for obtaining new access tokens
- Contains: user_id (sub), email, token_type, exp
```

---

#### Feature: Password Management

**Endpoints:**
```
POST   /auth/initiate-password-reset    - Start password reset
POST   /auth/confirm-password-reset     - Complete password reset
```

**Workflow:**
```
1. User initiates password reset with email
   ↓
2. System sends verification code to email
   ↓
3. User provides email + code + new password
   ↓
4. Password hashed and updated in database
   ↓
5. User can login with new password
```

---

### 2️⃣ **Assistant Management Endpoints** (`/api/assistant`)

#### Feature: Create & Manage AI Assistants

**Endpoints:**
```
POST   /api/assistant/create-assistant              - Create new assistant
POST   /api/assistant/create-assistant-with-file    - Create with files
GET    /api/assistant/get-assistant                 - List all assistants
GET    /api/assistant/get-assistant/{id}            - Get specific assistant
PUT    /api/assistant/update-assistant              - Update assistant config
POST   /api/assistant/upload-assistant-files/{id}   - Upload files to assistant
```

**Feature Details:**

**Create Assistant Workflow:**
```
1. Authenticated user submits:
   - astName: Display name
   - astInstruction: System prompt/instructions
   - gptModel: Model selection (gpt-4o-mini, gpt-4o, etc.)
   - astTools: List of capabilities [file_search, code_interpreter, etc.]
   ↓
2. System generates unique API token for assistant
   ↓
3. Assistant created in OpenAI
   ↓
4. Metadata stored in MongoDB:
   {
     _id: ObjectId,
     userId: user_id,
     astName: string,
     astInstruction: string,
     gptModel: string,
     astTools: [strings],
     astId: openai_assistant_id,
     apiToken: unique_token,
     createdAt: timestamp
   }
   ↓
5. Assistant ready for conversation threads
```

**Update Assistant Workflow:**
```
1. User provides:
   - astId: Assistant ID to update
   - New configuration (name, instruction, model, tools)
   ↓
2. Validation: Verify user owns this assistant
   ↓
3. Update in OpenAI
   ↓
4. Sync MongoDB records
   ↓
5. Confirmation returned
```

**File Upload Workflow:**
```
1. User uploads files to specific assistant
   ↓
2. Files processed and uploaded to OpenAI
   ↓
3. Files indexed for vector search
   ↓
4. File IDs stored in MongoDB
   ↓
5. Assistant can reference files in responses
```

---

### 3️⃣ **Thread Management Endpoints** (`/api/threads`)

#### Feature: Conversation Threading

**Endpoints:**
```
POST   /api/threads/create-thread              - Create new conversation
GET    /api/threads/get-thread/{assistant_id}  - List threads for assistant
GET    /api/threads/get-thread-history/{id}    - Get thread conversation
```

**Workflow:**

**Create Thread:**
```
1. Authenticated user provides:
   - astId: Assistant ID
   - threadTitle: Thread name/topic
   ↓
2. System creates conversation thread in OpenAI
   ↓
3. Thread stored in MongoDB:
   {
     threadId: openai_thread_id,
     userId: user_id,
     astId: assistant_id,
     threadTitle: string,
     createdAt: timestamp,
     updatedAt: timestamp
   }
   ↓
4. Thread ID returned for chat operations
```

**Get Thread History:**
```
1. User requests history for specific thread
   ↓
2. System fetches messages from OpenAI
   ↓
3. Messages formatted with:
   - Message content
   - Sender role (user/assistant)
   - Timestamp
   - Attachments if any
   ↓
4. Full conversation returned to user
```

---

### 4️⃣ **Chat Messaging Endpoints** (`/api/chats`)

#### Feature: Send & Receive Messages

**Endpoint:**
```
POST   /api/chats/create-chat  - Send message to assistant
```

**Workflow:**

```
1. Authenticated user submits:
   - astId: Assistant ID
   - threadId: Thread ID
   - message: Text message
   - image: Optional image attachments
   ↓
2. Image Processing (if images provided):
   a) Receive image files
   b) Convert to base64
   c) Embed in message content
   d) Create image reference in message
   ↓
3. Content Processing:
   a) Parse message text
   b) Extract any file references
   c) Format for OpenAI API
   d) Add metadata (userId, timestamp)
   ↓
4. Send to OpenAI:
   a) Submit message to thread
   b) Run assistant on thread
   c) Wait for response generation
   ↓
5. Store in MongoDB:
   {
     userId: user_id,
     astId: assistant_id,
     threadId: thread_id,
     userMessage: original_message,
     assistantResponse: ai_response,
     images: image_metadata,
     createdAt: timestamp
   }
   ↓
6. Vector Embedding:
   a) Extract text content
   b) Generate embeddings
   c) Store in vector database
   d) Enable semantic search
   ↓
7. Return to user:
   - Original message
   - Assistant response
   - Message metadata
   - Timestamp
```

**Message Content Processing:**

```
Input: User message + images

Step 1: Parse Message
├─ Extract text
├─ Identify mentions
└─ Extract references

Step 2: Process Images
├─ Receive upload files
├─ Validate format (jpg, png, webp, gif)
├─ Convert to base64
├─ Create image objects
└─ Add to message content

Step 3: Format for OpenAI
├─ Create content array
├─ Add text content
├─ Add image content
├─ Include metadata
└─ Validate format

Step 4: Send & Execute
├─ Submit to OpenAI thread
├─ Run assistant
├─ Monitor execution
└─ Retrieve response
```

---

### 5️⃣ **Channel Integration Endpoints** (`/api/channel`)

#### Feature: Third-Party API Integration

**Endpoints:**
```
POST   /api/channel/channels-ast-info           - Get assistant info
POST   /api/channel/channels-api-integration    - Verify API token
```

**Workflow:**

**Get Assistant Info:**
```
1. System provides:
   - Assistant metadata
   - Configuration details
   - Available tools
   - Model information
   ↓
2. Used for channel integration setup
```

**API Integration & Verification:**
```
1. Third-party sends:
   - astName: Assistant name
   - apiToken: API token
   ↓
2. System validates:
   a) Check if assistant exists
   b) Verify API token matches
   c) Confirm integration permissions
   ↓
3. Response:
   - Verification status
   - Integration details
   - Access level
   ↓
4. Channel can now use assistant
   without authentication
```

---

### 6️⃣ **End-User API Endpoints** (`/api/enduser`)

#### Feature: Public API for External Users

**Endpoint:**
```
POST   /api/enduser/end-user-chat  - Send chat without authentication
```

**Workflow:**

```
1. End-user (no authentication) submits:
   - astName: Assistant name (public)
   - apiToken: API token (from channel)
   - threadtoken: Existing thread (optional)
   - message: Chat message
   - image: Images (optional)
   ↓
2. Token Verification:
   a) Look up assistant by name
   b) Verify API token
   c) Check permissions
   d) Validate token not revoked
   ↓
3. Auto-Create or Reuse Thread:
   If threadtoken not provided:
   a) Get userId from assistant owner
   b) Create new thread
   c) Return threadtoken for future use
   Else:
   a) Validate threadtoken
   b) Retrieve existing thread
   ↓
4. Create Chat:
   a) Process message and images
   b) Send to assistant
   c) Get response
   ↓
5. Return Response:
   - Chat response
   - Thread data
   - Next threadtoken (for continuation)
   ↓
6. Benefits:
   - No authentication required
   - Public API access
   - Channel integration ready
   - Secure via API tokens
```

---

## 🔄 Feature Implementation Pipeline

### General Pipeline for All Features

```
┌────────────────────────────────────┐
│  CLIENT REQUEST RECEIVED           │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│  1. REQUEST VALIDATION             │
│  ├─ Check required fields          │
│  ├─ Validate data types            │
│  ├─ Verify format                  │
│  └─ Sanitize inputs                │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│  2. AUTHENTICATION (if required)   │
│  ├─ Extract JWT token              │
│  ├─ Verify token signature         │
│  ├─ Check token expiration         │
│  └─ Extract user identity          │
└────────────┬───────────────────────┘
             │
         ┌───┴────────────────┐
         │                    │
    ✓ Valid            ✗ Invalid
         │                    │
         ▼                    ▼
    Continue         Return 401 Unauthorized
         │
         ▼
┌────────────────────────────────────┐
│  3. AUTHORIZATION                  │
│  ├─ Check user permissions         │
│  ├─ Verify resource ownership      │
│  ├─ Validate access level          │
│  └─ Check role-based access        │
└────────────┬───────────────────────┘
             │
         ┌───┴────────────────┐
         │                    │
    ✓ Allowed       ✗ Denied
         │                    │
         ▼                    ▼
    Continue         Return 403 Forbidden
         │
         ▼
┌────────────────────────────────────┐
│  4. BUSINESS LOGIC EXECUTION       │
│  ├─ Apply business rules           │
│  ├─ Perform calculations           │
│  ├─ Execute workflows              │
│  └─ Validate business constraints  │
└────────────┬───────────────────────┘
             │
         ┌───┴────────────────┐
         │                    │
    ✓ Valid            ✗ Invalid
         │                    │
         ▼                    ▼
    Continue      Return 400 Bad Request
         │
         ▼
┌────────────────────────────────────┐
│  5. DATABASE/EXTERNAL OPERATIONS   │
│  ├─ Query MongoDB                  │
│  ├─ Call OpenAI API                │
│  ├─ Send emails                    │
│  └─ Process files                  │
└────────────┬───────────────────────┘
             │
         ┌───┴────────────────┐
         │                    │
    ✓ Success            ✗ Error
         │                    │
         ▼                    ▼
    Continue      Return 500 Server Error
         │
         ▼
┌────────────────────────────────────┐
│  6. RESPONSE FORMATTING            │
│  ├─ Format response data           │
│  ├─ Add metadata                   │
│  ├─ Include status codes           │
│  └─ Add timestamps                 │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│  RETURN TO CLIENT                  │
│  {                                 │
│    "status": boolean,              │
│    "message": string,              │
│    "data": object,                 │
│    "timestamp": iso-string         │
│  }                                 │
└────────────────────────────────────┘
```

### Feature-Specific Implementations

#### Assistant Creation Pipeline
```
Input: Assistant Config
    ↓
[Validate Configuration]
    - Check name not empty
    - Verify gptModel is valid
    - Confirm astTools exist
    ↓
[Generate API Token]
    - Create random token
    - Store token hash
    ↓
[Create in OpenAI]
    - Call OpenAI API
    - Provide name, instructions, tools
    - Get OpenAI assistant_id back
    ↓
[Store in MongoDB]
    - Save assistant metadata
    - Link to user
    - Store creation timestamp
    ↓
[Return Response]
    - Send success status
    - Include assistant ID
    - Include API token
```

#### Chat Message Pipeline
```
Input: Message + Images
    ↓
[Validate Message]
    - Check message not empty
    - Verify assistant exists
    - Confirm thread exists
    ↓
[Process Images]
    If images provided:
    - Receive files
    - Convert to base64
    - Create image objects
    ↓
[Send to OpenAI]
    - Add message to thread
    - Execute assistant run
    - Poll for completion
    - Extract response
    ↓
[Generate Embeddings]
    - Extract text
    - Call embedding model
    - Store vectors
    ↓
[Store in MongoDB]
    - Save message pair
    - Link to thread
    - Store embeddings
    - Store metadata
    ↓
[Return Response]
    - User message
    - Assistant response
    - Message ID
    - Timestamp
```

---

## 📊 Task Workflow & Operations

### 1. User Onboarding Workflow

```
New User
    ↓
┌─────────────────────────────────────┐
│ SIGN UP TASK                        │
├─────────────────────────────────────┤
│ 1. Receive email + password         │
│ 2. Validate email format            │
│ 3. Check email not already used     │
│ 4. Hash password (bcrypt)           │
│ 5. Generate verification code       │
│ 6. Create user record in MongoDB    │
│ 7. Send verification email          │
│ 8. Return success message           │
└─────────────────────────────────────┘
    ↓
User Receives Email
    ↓
┌─────────────────────────────────────┐
│ EMAIL CONFIRMATION TASK             │
├─────────────────────────────────────┤
│ 1. User clicks link or enters code  │
│ 2. System validates code            │
│ 3. Mark user as confirmed           │
│ 4. User account activated           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ LOGIN TASK                          │
├─────────────────────────────────────┤
│ 1. Receive email + password         │
│ 2. Find user by email               │
│ 3. Verify password hash             │
│ 4. Generate access token (15 min)   │
│ 5. Generate refresh token (7 days)  │
│ 6. Return tokens to client          │
│ 7. Client uses access token for API │
└─────────────────────────────────────┘
    ↓
User Authenticated & Ready
```

### 2. Assistant Creation & Setup Workflow

```
Authenticated User
    ↓
┌─────────────────────────────────────┐
│ CREATE ASSISTANT TASK               │
├─────────────────────────────────────┤
│ 1. Define assistant name            │
│ 2. Write system instructions        │
│ 3. Select GPT model                 │
│ 4. Choose tools/capabilities        │
└─────────────────────────────────────┘
    ↓
    ├─────────────────────────────────────────────────┐
    │ (Optional) Upload Files                         │
    ├─────────────────────────────────────────────────┤
    │ 1. Select files to attach                       │
    │ 2. Upload to system                             │
    │ 3. Process documents (PDF, text, etc.)         │
    │ 4. Generate embeddings                          │
    │ 5. Store in vector database                     │
    └─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ SYSTEM PROCESSING                   │
├─────────────────────────────────────┤
│ 1. Generate unique API token        │
│ 2. Call OpenAI to create assistant  │
│ 3. Store metadata in MongoDB:       │
│    - astId (from OpenAI)            │
│    - apiToken                       │
│    - User association               │
│    - Configuration details          │
│ 4. Return assistant to user         │
└─────────────────────────────────────┘
    ↓
Assistant Ready for Use
```

### 3. Conversation Management Workflow

```
User with Assistant
    ↓
┌─────────────────────────────────────┐
│ CREATE THREAD TASK                  │
├─────────────────────────────────────┤
│ 1. Choose assistant                 │
│ 2. Give thread a name/topic         │
│ 3. System creates OpenAI thread     │
│ 4. Store thread in MongoDB          │
│ 5. Return thread ID                 │
└─────────────────────────────────────┘
    ↓
Thread Created - Ready for Chat
    ↓
    ├─────────────────────────────────────────┐
    │ SEND MESSAGE TASK (Repeatable)          │
    ├─────────────────────────────────────────┤
    │ 1. User types message                   │
    │ 2. (Optional) Attach images            │
    │ 3. Submit to assistant                  │
    │ 4. System adds to thread                │
    │ 5. Run assistant on thread              │
    │ 6. Get AI response                      │
    │ 7. Store both messages                  │
    │ 8. Generate embeddings                  │
    │ 9. Return response to user              │
    │ 10. Continue loop...                    │
    └─────────────────────────────────────────┘
    ↓
    Conversation History Grows
    ↓
┌─────────────────────────────────────┐
│ RETRIEVE HISTORY TASK               │
├─────────────────────────────────────┤
│ 1. Request full thread history      │
│ 2. Fetch all messages from OpenAI   │
│ 3. Format with metadata             │
│ 4. Return complete conversation     │
└─────────────────────────────────────┘
```

### 4. Channel Integration Workflow

```
Third-Party Channel/Partner
    ↓
┌──────────────────────────────────────┐
│ REQUEST INTEGRATION                  │
├──────────────────────────────────────┤
│ 1. Admin creates assistant in system │
│ 2. System generates API token        │
│ 3. Token shared with partner         │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ PARTNER SETUP                        │
├──────────────────────────────────────┤
│ 1. Partner receives:                 │
│    - Assistant name                  │
│    - API token                       │
│    - Base URL                        │
│ 2. Partner stores credentials        │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ PARTNER API CALL (No Auth Required)  │
├──────────────────────────────────────┤
│ 1. Partner sends:                    │
│    - astName                         │
│    - apiToken                        │
│    - threadtoken (if existing)       │
│    - message                         │
│ 2. System verifies token             │
│ 3. Routes to assistant               │
│ 4. Creates/reuses thread             │
│ 5. Sends message                     │
│ 6. Returns response                  │
│ 7. Partner integrates response       │
└──────────────────────────────────────┘
    ↓
Seamless Integration
```

### 5. End-User Interaction Workflow

```
End-User (No Account)
    ↓
    │ Channel/Partner provides:
    │ - Assistant name
    │ - API token
    │
    ▼
┌──────────────────────────────────────┐
│ FIRST MESSAGE (NEW THREAD)           │
├──────────────────────────────────────┤
│ 1. Send message + images (optional)  │
│ 2. System verifies API token         │
│ 3. Auto-creates thread               │
│ 4. Sends message to assistant        │
│ 5. Returns:                          │
│    - Response                        │
│    - New threadtoken (for continuation)
│    - Conversation state              │
└──────────────────────────────────────┘
    ↓
End-User Receives threadtoken
    ↓
┌──────────────────────────────────────┐
│ SUBSEQUENT MESSAGES (SAME THREAD)    │
├──────────────────────────────────────┤
│ 1. Send message with threadtoken     │
│ 2. System finds existing thread      │
│ 3. Adds message to thread            │
│ 4. Gets response                     │
│ 5. Returns updated conversation      │
└──────────────────────────────────────┘
    ↓
Continuous Conversation Flow
```

---

## 🎯 Epics Overview

### Epic 1: User Identity & Authentication ⚡
**Purpose:** Secure user management and token-based access control

**Features Included:**
- User sign-up with email verification
- Email-based login
- JWT token generation and refresh
- Password reset workflow
- User profile management

**User Stories:**
1. "As a new user, I want to create an account with email and password"
2. "As a user, I want to receive a verification email to confirm my account"
3. "As a user, I want to login with my credentials and receive tokens"
4. "As a user, I want to refresh my token when it expires"
5. "As a user, I want to reset my password if forgotten"

**APIs Used:** `/auth/sign-up`, `/auth/confirm-sign-up`, `/auth/login`, `/auth/refresh`, `/auth/me`

**Database Collections:** `users`, `verification_codes`, `tokens`

---

### Epic 2: Assistant Management & Configuration 🤖
**Purpose:** Enable users to create, configure, and manage AI assistants

**Features Included:**
- Create assistants with custom instructions
- Select AI models (gpt-4o-mini, gpt-4o, etc.)
- Configure tools/capabilities
- Update assistant configurations
- Upload files to assistants
- List and retrieve assistant details

**User Stories:**
1. "As an admin, I want to create a custom AI assistant with specific instructions"
2. "As an admin, I want to configure which tools my assistant can use"
3. "As an admin, I want to upload knowledge base files to my assistant"
4. "As an admin, I want to view all my assistants"
5. "As an admin, I want to update my assistant's configuration"

**APIs Used:** `/api/assistant/create-assistant`, `/api/assistant/update-assistant`, `/api/assistant/get-assistant`, `/api/assistant/upload-assistant-files/{id}`

**Database Collections:** `assistants`, `assistant_files`

**External Services:** OpenAI API (Assistant creation/management)

---

### Epic 3: Conversation Threading & Management 💬
**Purpose:** Organize conversations into isolated, persistent threads

**Features Included:**
- Create conversation threads
- List threads per assistant
- Retrieve thread history
- Manage thread metadata

**User Stories:**
1. "As a user, I want to create a new conversation thread for a topic"
2. "As a user, I want to see all conversations for a specific assistant"
3. "As a user, I want to view the complete history of a conversation"
4. "As a user, I want to organize conversations by topic/thread"

**APIs Used:** `/api/threads/create-thread`, `/api/threads/get-thread/{assistant_id}`, `/api/threads/get-thread-history/{thread_id}`

**Database Collections:** `threads`, `thread_metadata`

**External Services:** OpenAI Threads API

---

### Epic 4: Chat Messaging & AI Responses 💭
**Purpose:** Enable real-time messaging with AI assistants and conversation history

**Features Included:**
- Send text messages to assistants
- Support image attachments
- Receive AI-generated responses
- Store message history
- Generate embeddings for semantic search
- Process multi-modal content

**User Stories:**
1. "As a user, I want to send a message to an assistant and get a response"
2. "As a user, I want to include images with my message"
3. "As a user, I want to see my full conversation history"
4. "As a user, I want to search conversations by semantic meaning"
5. "As a user, I want real-time message processing"

**APIs Used:** `/api/chats/create-chat`

**Database Collections:** `messages`, `embeddings`

**External Services:** OpenAI Assistants API, Vector DB

---

### Epic 5: Channel Integration & Third-Party Access 🔗
**Purpose:** Enable secure third-party integrations via API tokens

**Features Included:**
- Assistant info retrieval for integration
- API token-based verification
- Channel configuration management
- Integration health checks

**User Stories:**
1. "As an integrator, I want to integrate an assistant into my platform"
2. "As an integrator, I want to verify my API token with the system"
3. "As an integrator, I want to retrieve assistant information"
4. "As an admin, I want to manage which channels can access which assistants"

**APIs Used:** `/api/channel/channels-ast-info`, `/api/channel/channels-api-integration`

**Database Collections:** `channels`, `api_tokens`, `channel_permissions`

---

### Epic 6: End-User Public API 🌍
**Purpose:** Provide public API access for end-users without authentication

**Features Included:**
- Token-based public API access
- Thread token generation
- Auto-thread creation
- Stateless session management
- Chat creation for end-users

**User Stories:**
1. "As an end-user, I want to chat with an assistant without creating an account"
2. "As an end-user, I want to continue my conversation in a new session using a token"
3. "As an end-user, I want to send messages with attachments"
4. "As a platform, I want to offer assistant access without authentication"

**APIs Used:** `/api/enduser/end-user-chat`

**Database Collections:** `end_user_threads`, `end_user_sessions`

---

### Epic 7: File Management & Knowledge Base 📁
**Purpose:** Support document uploads for knowledge base and semantic search

**Features Included:**
- File upload to assistants
- Document processing (PDF, text, etc.)
- Vector embedding generation
- Semantic search capability
- File metadata management

**User Stories:**
1. "As an admin, I want to upload documents to build a knowledge base"
2. "As an admin, I want to enable semantic search on uploaded documents"
3. "As an admin, I want to manage which files are attached to which assistants"
4. "As a system, I want to extract and embed text from documents"

**Utilities Used:** `ocr_pdf_utils.py`, `vector_utils.py`

**Database Collections:** `files`, `vector_embeddings`

---

### Epic 8: Email & Notifications 📧
**Purpose:** Send transactional emails for verification and password reset

**Features Included:**
- Verification email sending
- Password reset email sending
- Email templating
- Gmail API integration

**User Stories:**
1. "As a user, I want to receive a verification email when signing up"
2. "As a user, I want to receive password reset link in email"
3. "As a system, I want reliable email delivery"

**Services Used:** `email_service.py`, Gmail API

**Configuration:** `GMAIL_CREDENTIALS_FILE`, `GMAIL_TOKEN_FILE`

---

### Epic 9: Security & Token Management 🔐
**Purpose:** Ensure secure authentication, authorization, and token management

**Features Included:**
- JWT token generation and verification
- Password hashing (bcrypt)
- API token generation
- Token refresh mechanism
- Authorization checks

**User Stories:**
1. "As a system, I want to securely hash passwords"
2. "As a system, I want to generate secure JWT tokens"
3. "As a system, I want to verify tokens and prevent unauthorized access"
4. "As a system, I want API tokens for third-party integrations"

**Components Used:** `auth_controller.py`, HTTPBearer security

---

### Epic 10: Database & Persistence 💾
**Purpose:** Reliable data persistence with MongoDB

**Features Included:**
- User record storage
- Assistant metadata storage
- Thread and message history
- File metadata storage
- Vector embeddings storage
- Audit logging

**Database Collections:**
```
├── users
├── assistants
├── threads
├── messages
├── embeddings
├── files
├── api_tokens
├── channels
├── end_user_sessions
└── audit_logs
```

**Utilities Used:** `mongo_utils.py`

---

## 🛠️ Technical Stack

### Backend Framework
- **FastAPI**: Async Python web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Authentication & Security
- **PyJWT**: JWT token generation/verification
- **bcrypt**: Password hashing
- **HTTPBearer**: Bearer token security

### Database
- **MongoDB**: NoSQL document database
- **Motor**: Async MongoDB driver

### AI & LLM
- **OpenAI API**: GPT models and Assistants
- **OpenAI Embeddings**: Vector embeddings for semantic search
- **Assistant API**: Multi-turn conversations

### File Processing
- **PyPDF2**: PDF file parsing
- **Pillow**: Image processing
- **python-magic**: File type detection

### Email
- **Gmail API**: Email sending
- **google-auth-oauthlib**: Google OAuth

### Utilities
- **python-dotenv**: Environment variable management
- **aiofiles**: Async file operations
- **requests**: HTTP client

---

## 🚀 Setup & Deployment

### Prerequisites
```bash
- Python 3.10+
- MongoDB instance
- OpenAI API key
- Gmail API credentials
- .env file with configuration
```

### Environment Variables (.env)
```
DATABASE_URL=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_INITDB_DATABASE=assistant_db
OPENAI_API_KEY=sk-xxxxx
CLIENT_ORIGIN=http://localhost:3000
EMAIL_FROM=your-email@gmail.com
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.pickle
APP_NAME=Minor Assistant API
ENVIRONMENT=development
```

### Installation
```bash
# Clone repository
git clone <repo-url>

# Install dependencies
pip install -r requirements.txt

# Start API server
python start.py

# Or manually
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### API Access
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health

---

## 📈 Performance & Scalability

### Current Implementation
- ✅ Async/await for non-blocking operations
- ✅ Database indexing for fast queries
- ✅ Token-based rate limiting ready
- ✅ Horizontal scaling via stateless design

### Optimization Opportunities
- 🔄 Redis caching for frequently accessed data
- 🔄 Message queue for async processing
- 🔄 CDN for file delivery
- 🔄 Load balancer for multiple instances

---

## 🎓 Learning Resources

### API Documentation
- Read: `CURL-TESTING-GUIDE.md`
- Reference: `QUICK-REFERENCE.md`
- Examples: `curl-commands-examples.sh`

### Integration Guide
- Frontend: `docs/assistant-api-auth.md`
- Test Suite: `curl-api-tests.sh`

### Testing
- Run tests: `bash curl-api-tests.sh`
- Manual testing: `bash test-with-curl.sh`

---

## 📞 Support & Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| API not responding | Verify API is running: `python start.py` |
| 401 Unauthorized | Re-login and get new token |
| 403 Forbidden | Verify user owns the resource |
| 500 Server Error | Check logs and OpenAI API status |
| File upload fails | Verify file format and size limits |
| Token expired | Use refresh token to get new access token |

---

## 📝 Summary

The **Minor Assistant API** is a comprehensive, production-ready backend system that:

✅ **Manages Users**: Secure authentication and profiles  
✅ **Creates Assistants**: Custom AI assistants with capabilities  
✅ **Organizes Conversations**: Threading for multi-topic management  
✅ **Enables Chat**: Real-time messaging with AI responses  
✅ **Integrates Channels**: Third-party platform support  
✅ **Serves End-Users**: Public API without authentication  
✅ **Processes Files**: Knowledge base and document search  
✅ **Sends Emails**: Verification and notifications  
✅ **Ensures Security**: JWT tokens and encrypted credentials  
✅ **Persists Data**: MongoDB for reliable storage  

**Status:** ✅ **Ready for Production**

---

**Last Updated:** November 26, 2025  
**API Version:** 1.0  
**Framework:** FastAPI  
**Database:** MongoDB  
**Auth:** JWT Bearer Token
