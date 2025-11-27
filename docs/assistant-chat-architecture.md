## Assistant Chat Architecture

This document explains how assistants, threads, chats, and OpenAI integrations work inside this project. It covers what you asked for: where the OpenAI calls happen, how system prompts are defined, how files are attached, and the current state of RAG-style retrieval.

---

### Data Flow Overview
- **Assistants**: User-scoped definitions that bundle a name, instruction (system prompt), tools, and optional files.
- **Threads**: OpenAI thread IDs tied to a specific assistant and user. Every chat message belongs to one.
- **Chats**: Individual interactions (user message + assistant response) stored in Mongo after OpenAI returns.
- **Rate limiting / usage**: Guardrails provided by `RateLimiter` and `OpenAIKeyManager` around every send.
- **OpenAI helper**: `app/helpers/openai_helper.py` encapsulates all live API calls.

---

### Assistant Creation (System Prompt, Tools, Files)
**Entry point:** `POST /create-assistant` → `AssistantController.create_assistant` (`app/controllers/assistant.py`).

Workflow:
1. Enforce per-user assistant quotas via `RateLimiter`.
2. Fetch an OpenAI key (either the user’s own or the shared pool) through `OpenAIKeyManager`.
3. Upload each optional file with `OpenAIHelper.upload_file`, storing the returned file IDs.
4. Create the assistant at OpenAI:
   - `name = astName`
   - `instructions = astInstruction` ← this is the *system prompt* used for every future run.
   - `model = gptModel`
   - `tools = astTools` (converted into `{"type": tool}` payloads)
   - `file_ids = uploaded file IDs`
5. Persist the assistant document in Mongo (`assistants` collection) together with usage stats and an API token for SDK clients.

> **System prompt**: whatever the user entered in `astInstruction`. There’s no hidden prompt injection elsewhere; Assistant updates simply replace this field on OpenAI and in Mongo.

---

### Thread Creation
**Entry point:** `POST /create-thread` → `ThreadController.create_thread` (`app/controllers/threads.py`).

Steps:
1. Validate the assistant belongs to the current user.
2. Check per-user/per-assistant thread limits via `RateLimiter`.
3. Obtain an OpenAI key via `OpenAIKeyManager`.
4. Call `OpenAIHelper.create_thread()` (wraps `client.beta.threads.create()`).
5. Store the resulting `threadId` along with the assistant ID, user ID, title, and timestamps in Mongo (`threads` collection).

Threads are required because OpenAI Assistants run statefully per thread. Every chat call references both `astId` and `threadId`.

---

### Chat Creation + Response Formatting
**Entry point:** `POST /create-chat` → `ChatController.create_chat` (`app/controllers/chats.py`).

Pipeline:
1. Rate limits
   - `RateLimiter.check_message_limit` (per-day/week messages)
   - `RateLimiter.check_token_limit` (token-allocation guard)
2. Ownership checks: confirm both assistant and thread belong to the user.
3. Pick API key: `OpenAIKeyManager.get_key_for_request` returns `(key, used_custom_key)` so that heavy users can plug in their own credentials.
4. Files/images: any uploaded images are base64-encoded and turned into `input_image` blocks for OpenAI Vision-able models.
5. Send to OpenAI: `OpenAIHelper.create_message_and_run` writes the user message to the thread, starts a run, polls for completion, grabs the latest assistant reply, and reports total tokens.
6. Persistence: store `userMessage`, `assistantResponse`, images, token usage, key provenance, and timestamps in the `chats` collection.
7. Response shape (FastAPI):
   ```json
   {
     "status": true,
     "message": "Chat created successfully",
     "data": {
       "chat_id": "...",
       "user_message": "...",
       "assistant_response": "...",
       "tokens_used": 123,
       "used_custom_key": false,
       "images_count": 0,
       "timestamp": "UTC ISO"
     }
   }
   ```
8. Token accounting: if OpenAI returned `tokens_used`, the limiter records it via `track_token_usage`.

History retrieval (`GET /history/{thread_id}`) simply reads stored chat documents and returns them chronologically.

---

### Where OpenAI Calls Happen
All live calls are centralized in `app/helpers/openai_helper.py`:
- `create_assistant`, `update_assistant`, `delete_assistant`
- `create_thread`, `delete_thread`, `get_thread_messages`
- `create_message_and_run` (message send + run polling)
- `upload_file` plus the helper coroutine pair `create_file` / `create_files` used by legacy tooling

The controllers never call the OpenAI SDK directly. They import `OpenAIHelper` and pass the correct key.

---

### File Attachments & RAG Story
#### Current Production Path
- During assistant creation, each uploaded file is pushed to OpenAI (`purpose="assistants"`), and the resulting `file_ids` are tied to the assistant.
- OpenAI’s Assistants API automatically leverages these files when answering, so chats benefit from the uploaded knowledge without extra code.

#### Vector Store / Advanced RAG (Experimental)
- `app/utils/open_ai_utils.py:create_assistant_with_file` demonstrates how to create an OpenAI vector store, upload files into it via `OpenAIHelper.create_files`, and wire it through `tool_resources={"file_search": {"vector_store_ids": [...]}}`. This isn’t called from the FastAPI controller today but can be adopted if you need explicit file-search tooling.
- `app/utils/vector_utils.py` contains an alternative Milvus + LangChain ingest pipeline (`ingest_file_to_vector_db`, `make_chain`, etc.). Nothing references it right now, so it’s scaffolding for a custom RAG workflow if you want to move outside the OpenAI-native approach.

If you plan to expose RAG explicitly, decide whether to:
1. Stick with OpenAI’s native file search (already partially wired, needs controller integration), or
2. Use the Milvus/LangChain pipeline and call it before chats to fetch context snippets.

---

### System Prompt Updates
- `AssistantController.update_assistant` patches the assistant both in Mongo and on OpenAI. Any change to `astInstruction` immediately becomes the new system prompt for future runs; past chats remain unaffected because instructions are stored per assistant, not per thread.

---

### Reference Index
| Responsibility | File(s) |
| --- | --- |
| Assistant CRUD | `app/controllers/assistant.py`, `app/models/model_types.py` |
| Thread CRUD | `app/controllers/threads.py` |
| Chat creation/history | `app/controllers/chats.py`, `app/routers/chats.py` |
| OpenAI helper | `app/helpers/openai_helper.py` |
| Rate limiting / keys | `app/services/rate_limiter.py`, `app/services/openai_key_manager.py` |
| API response schema | `app/models/response_model.py` |
| Legacy/OpenAI utility helpers | `app/utils/open_ai_utils.py` |
| Vector store experiments | `app/utils/vector_utils.py` |

---

### What to Customize Next
- **RAG depth**: Decide whether to integrate the vector-store path into the main controller or stick with OpenAI’s native file search.
- **System prompts**: Provide admin tooling or presets for `astInstruction` if you need standardized prompts.
- **Telemetry**: Hook `usage_history` and `tokens_used` stats into dashboards for visibility.
- **Testing**: Use `curl-new-endpoints-tests.sh` (already in repo) as a blueprint for automated chat endpoint checks.

With this map, new contributors can trace any user request from HTTP to OpenAI and back, understand how instructions/files influence outputs, and extend the RAG story confidently.

