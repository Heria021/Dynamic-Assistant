import asyncio
import io
import json
import re
import time
from typing import List, Optional, Dict, Any

import app.models.model_types as modelType
from fastapi import UploadFile
from openai import OpenAI
try:
    from langchain_community.embeddings import OpenAIEmbeddings
    from langchain_community.vectorstores import Milvus
except ImportError:
    # Fallback for older langchain versions
    from langchain.embeddings.openai import OpenAIEmbeddings
    from langchain.vectorstores import Milvus
from app.utils.utils import replace_hyphens_with_underscores


class OpenAIHelper:
    """Helper wrapper around the OpenAI Assistants/Threads API."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    async def upload_file(self, file: UploadFile) -> str:
        contents = await file.read()
        file_like = io.BytesIO(contents)
        file_like.name = file.filename

        created_file = self.client.files.create(file=file_like, purpose="assistants")
        return created_file.id

    async def create_assistant(
        self,
        name: str,
        instructions: str,
        model: str,
        tools: List[Any],
        file_ids: Optional[List[str]] = None,
        vector_store_id: Optional[str] = None,  # NEW: For OpenAI file search
    ):
        # Tools already normalized by controller — use as-is
        tool_payload = tools.copy()
        
        # Add file_search tool if vector store is provided
        if vector_store_id:
            tool_payload.append({"type": "file_search"})
            print(f"[RAG-DEBUG] Added file_search tool to assistant")
        
        payload = {
            "name": name,
            "instructions": instructions,
            "model": model,
            "tools": tool_payload,
        }

        # Configure tool_resources for file_search if vector store provided
        if vector_store_id:
            payload["tool_resources"] = {
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
            print(f"[RAG-DEBUG] Configured tool_resources with vector_store_id: {vector_store_id}")

        return self.client.beta.assistants.create(**payload)

    async def update_assistant(self, assistant_id: str, **updates):
        return self.client.beta.assistants.update(
            assistant_id=assistant_id, **updates
        )

    async def delete_assistant(self, assistant_id: str):
        return self.client.beta.assistants.delete(assistant_id=assistant_id)

    async def create_thread(self):
        return self.client.beta.threads.create()

    async def delete_thread(self, thread_id: str):
        return self.client.beta.threads.delete(thread_id=thread_id)

    async def get_thread_messages(self, thread_id: str):
        messages = self.client.beta.threads.messages.list(
            thread_id=thread_id, order="asc"
        )
        return messages.data

    def _wait_for_run(self, thread_id: str, run_id: str):
        """Original polling method - keep for backward compatibility"""
        run = self.client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        while run.status in {"queued", "in_progress"}:
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
        return run

    # === NEW: RAG RETRIEVAL METHOD ===
    async def retrieve_context(
        self,
        query: str,
        collection_name: str,
        top_k: int = 3
    ) -> str:
        """
        Retrieve relevant context from Milvus vector store.
        Returns concatenated text chunks.
        """
        try:
            print(f"[RAG-DEBUG] ===== RAG RETRIEVAL START =====")
            print(f"[RAG-DEBUG] Collection name: {collection_name}")
            print(f"[RAG-DEBUG] Query: {query}")
            print(f"[RAG-DEBUG] Top K: {top_k}")
            
            sanitized_query = re.sub(r'\n', ' ', query.strip())
            print(f"[RAG-DEBUG] Sanitized query: {sanitized_query}")
            
            print(f"[RAG-DEBUG] Initializing OpenAI embeddings...")
            embeddings = OpenAIEmbeddings(openai_api_key=self.client.api_key)
            print(f"[RAG-DEBUG] Embeddings initialized")
            
            print(f"[RAG-DEBUG] Connecting to Milvus at 127.0.0.1:19530...")
            print(f"[RAG-DEBUG] Collection name for Milvus: {collection_name}")
            vector_store = Milvus(
                embedding_function=embeddings,
                collection_name=collection_name,
                connection_args={"host": "127.0.0.1", "port": "19530"}
            )
            print(f"[RAG-DEBUG] Milvus connection established")
            
            print(f"[RAG-DEBUG] Performing similarity search...")
            # Retrieve top_k similar documents
            docs = vector_store.similarity_search(sanitized_query, k=top_k)
            print(f"[RAG-DEBUG] Similarity search completed")
            
            if not docs:
                print(f"[RAG-DEBUG] ⚠️  No documents found in collection: {collection_name}")
                print(f"[RAG-DEBUG] This could mean:")
                print(f"[RAG-DEBUG]   1. Collection doesn't exist in Milvus")
                print(f"[RAG-DEBUG]   2. Collection is empty")
                print(f"[RAG-DEBUG]   3. Collection name mismatch")
                return ""
            
            print(f"[RAG-DEBUG] ✓ Retrieved {len(docs)} document(s) from collection: {collection_name}")
            for i, doc in enumerate(docs):
                print(f"[RAG-DEBUG]   Doc {i+1}: {len(doc.page_content)} chars - {doc.page_content[:100]}...")
            
            # Concatenate retrieved chunks
            context = "\n\n".join([doc.page_content for doc in docs])
            print(f"[RAG-DEBUG] Total context length: {len(context)} chars")
            print(f"[RAG-DEBUG] ===== RAG RETRIEVAL SUCCESS =====")
            return context
            
        except Exception as e:
            print(f"[RAG-DEBUG] ✗ ERROR: Retrieval failed for collection {collection_name}")
            print(f"[RAG-DEBUG] Error type: {type(e).__name__}")
            print(f"[RAG-DEBUG] Error message: {str(e)}")
            import traceback
            print(f"[RAG-DEBUG] Full traceback:")
            traceback.print_exc()
            print(f"[RAG-DEBUG] ===== RAG RETRIEVAL FAILED =====")
            return ""

    # === NEW: FUNCTION CALL HANDLER ===
    async def _wait_and_handle_functions(self, thread_id: str, run_id: str):
        """
        Enhanced polling that handles function calls.
        OpenAI will pause run with 'requires_action' status when function is needed.
        """
        run = self.client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        
        while run.status in {"queued", "in_progress", "requires_action"}:
            if run.status == "requires_action":
                # Handle function calls
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments
                    
                    # Execute function (you'll implement these)
                    output = await self._execute_function(function_name, function_args)
                    
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": output
                    })
                
                # Submit outputs back to OpenAI
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )
            
            await asyncio.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
        
        return run

    async def _execute_function(self, function_name: str, function_args: str) -> str:
        """
        Stub function executor.
        Returns JSON confirmation that will be sent back to OpenAI.
        Actual execution happens in your backend after response.
        """
        try:
            args = json.loads(function_args)
        except json.JSONDecodeError:
            args = {}
        
        # Just return confirmation - actual execution happens later
        if function_name == "handoff_to_human":
            return json.dumps({"status": "queued", "reason": args.get("reason", "")})
        elif function_name == "send_link":
            return json.dumps({"status": "link_prepared", "url": args.get("url", ""), "description": args.get("description", "")})
        elif function_name == "send_email":
            return json.dumps({"status": "email_queued", "to": args.get("to", ""), "subject": args.get("subject", ""), "body": args.get("body", "")})
        
        return json.dumps({"status": "unknown_function"})

    def _extract_actions_from_run(self, run) -> List[Dict[str, Any]]:
        """
        Extract actions from completed function calls.
        Must fetch run steps explicitly from OpenAI API.
        """
        actions = []
        seen_actions = set()
        
        print(f"[FUNC-DEBUG] Extracting actions from run: {run.id}")
        
        # === METHOD 1: required_action (waiting for function output) ===
        if hasattr(run, 'required_action') and run.required_action:
            print(f"[FUNC-DEBUG] Run has required_action (functions called)")
            submit_tool_outputs = getattr(run.required_action, 'submit_tool_outputs', None)
            if submit_tool_outputs:
                tool_calls = getattr(submit_tool_outputs, 'tool_calls', [])
                print(f"[FUNC-DEBUG] Found {len(tool_calls)} tool call(s) in required_action")
                
                for tool_call in tool_calls:
                    if hasattr(tool_call, 'function'):
                        function_name = getattr(tool_call.function, 'name', '')
                        try:
                            function_args_str = getattr(tool_call.function, 'arguments', '{}')
                            function_args = json.loads(function_args_str)
                        except (json.JSONDecodeError, AttributeError, TypeError) as e:
                            print(f"[FUNC-DEBUG] Failed to parse args: {e}")
                            function_args = {}
                        
                        action_key = (function_name, json.dumps(function_args, sort_keys=True))
                        if action_key not in seen_actions:
                            seen_actions.add(action_key)
                            actions.append({
                                "type": function_name,
                                "data": function_args
                            })
                            print(f"[FUNC-DEBUG] ✓ Extracted action: {function_name}")
        
        # === METHOD 2: Fetch steps from API (completed function calls) ===
        try:
            print(f"[FUNC-DEBUG] Fetching run steps from API...")
            run_steps = self.client.beta.threads.runs.steps.list(
                thread_id=run.thread_id,
                run_id=run.id
            )
            print(f"[FUNC-DEBUG] Retrieved {len(run_steps.data)} step(s)")
            
            for step in run_steps.data:
                print(f"[FUNC-DEBUG] Step {step.id}: type={step.type}, status={step.status}")
                
                step_details = getattr(step, 'step_details', None)
                if not step_details:
                    continue

                tool_calls = getattr(step_details, 'tool_calls', [])
                print(f"[FUNC-DEBUG] Step has {len(tool_calls)} tool call(s)")

                for tool_call in tool_calls:
                    tool_type = getattr(tool_call, 'type', '')
                    print(f"[FUNC-DEBUG] Tool call type: {tool_type}")

                    if tool_type == 'function':
                        function_obj = getattr(tool_call, 'function', None)
                        if function_obj:
                            function_name = getattr(function_obj, 'name', '')
                            try:
                                function_args_str = getattr(function_obj, 'arguments', '{}')
                                function_args = json.loads(function_args_str)
                            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                                print(f"[FUNC-DEBUG] Failed to parse function args: {e}")
                                function_args = {}

                            action_key = (function_name, json.dumps(function_args, sort_keys=True))
                            if action_key not in seen_actions:
                                seen_actions.add(action_key)
                                actions.append({
                                    "type": function_name,
                                    "data": function_args
                                })
                                print(f"[FUNC-DEBUG] ✓ Extracted completed action: {function_name}")

                    elif tool_type == 'file_search':
                        print(f"[FUNC-DEBUG] File search tool used (RAG)")

                    elif tool_type == 'code_interpreter':
                        print(f"[FUNC-DEBUG] Code interpreter tool used")
        
        except Exception as e:
            print(f"[FUNC-DEBUG] ✗ Error fetching run steps: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()

        print(f"[FUNC-DEBUG] Total actions extracted: {len(actions)}")
        return actions

    async def create_message_and_run(
        self,
        thread_id: str,
        assistant_id: str,
        message: str,
        images: Optional[List[dict]] = None,
        collection_name: Optional[str] = None,  # NEW: for RAG
        tools: Optional[List[dict]] = None,  # NEW: for function calling
    ) -> dict:
        """
        Enhanced version with:
        1. RAG context injection
        2. Function calling support
        3. Action extraction
        """
        
        # === STEP 1: OPENAI NATIVE FILE SEARCH ===
        # OpenAI automatically uses file_search tool when assistant has files
        # No manual RAG retrieval needed - OpenAI handles it internally!
        print(f"[RAG-DEBUG] Using OpenAI native file_search (automatic RAG)")
        print(f"[RAG-DEBUG] Message: {message[:100]}...")
        
        # Use original message - OpenAI will automatically retrieve relevant context
        augmented_message = message

        # === STEP 2: CREATE MESSAGE WITH CONTENT ===
        content = [{"type": "text", "text": augmented_message}]
        
        if images:
            for image in images:
                content.append({
                    "type": "input_image",
                    "image": {
                        "data": image.get("data"),
                        "media_type": image.get("content_type", "image/png"),
                    },
                })

        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )

        # === STEP 3: TOOLS ARE ALREADY ON ASSISTANT ===
        # Function tools are added at assistant creation time
        # No need to update them here - OpenAI will use them automatically
        print(f"[FUNC] Using function tools already configured on assistant")

        # === STEP 4: CREATE RUN ===
        run = self.client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # === DEBUG: Log run details ===
        print(f"[FUNC-DEBUG] ===== RUN CREATED =====")
        print(f"[FUNC-DEBUG] Run ID: {run.id}")
        print(f"[FUNC-DEBUG] Run status: {run.status}")
        print(f"[FUNC-DEBUG] Thread ID: {thread_id}")
        print(f"[FUNC-DEBUG] Assistant ID: {assistant_id}")

        # Check assistant to see what tools it has
        try:
            assistant_obj = self.client.beta.assistants.retrieve(assistant_id)
            print(f"[FUNC-DEBUG] Assistant tools:")
            for tool in assistant_obj.tools:
                if hasattr(tool, 'type'):
                    if tool.type == 'function':
                        func_name = getattr(tool.function, 'name', 'unknown')
                        print(f"[FUNC-DEBUG]   - function: {func_name}")
                    else:
                        print(f"[FUNC-DEBUG]   - {tool.type}")
        except Exception as e:
            print(f"[FUNC-DEBUG] Could not retrieve assistant details: {e}")

        print(f"[FUNC-DEBUG] ===== STARTING RUN POLLING =====")
        
        # === STEP 5: WAIT FOR COMPLETION & HANDLE FUNCTION CALLS ===
        run = await self._wait_and_handle_functions(thread_id, run.id)

        # === STEP 6: GET RESPONSE ===
        messages = self.client.beta.threads.messages.list(
            thread_id=thread_id, order="desc", limit=1
        )
        latest_message = messages.data[0] if messages.data else None
        assistant_response = (
            latest_message.content[0].text.value if latest_message else ""
        )

        tokens_used = getattr(getattr(run, "usage", None), "total_tokens", 0) or 0

        # === STEP 7: EXTRACT ACTIONS FROM FUNCTION CALLS ===
        actions = self._extract_actions_from_run(run)

        # === STEP 5: DETECT RAG USAGE ===
        # Check if response contains OpenAI citations (indicates file_search was used)
        # Citations look like: 【4:0†source】 or 【8:0†source】
        used_rag = False
        if assistant_response:
            import re
            citation_pattern = r'【\d+:\d+†source】'
            if re.search(citation_pattern, assistant_response):
                used_rag = True
                print(f"[RAG-DEBUG] ✓ RAG was used - citations found in response")
            else:
                print(f"[RAG-DEBUG] No citations found - RAG may not have been used")

        return {
            "response": assistant_response,
            "tokens_used": tokens_used,
            "actions": actions,  # NEW
            "used_rag": used_rag,  # NEW: Detects OpenAI file_search usage
            "run": run.model_dump() if hasattr(run, "model_dump") else None,
        }

def wait_on_run(run, thread_id):
        client = OpenAI()
        while run.status == "queued" or run.status == "in_progress":
                run = client.beta.threads.runs.retrieve(
                        thread_id=thread_id,
                        run_id=run.id,
                )
                time.sleep(0.5)
        return run


def submit_message(chat : modelType.AssistantChat, user_message):
        client = OpenAI()
        client.beta.threads.messages.create(
                thread_id= chat.threadId,
                role="user",
                content=user_message,

        )
        return client.beta.threads.runs.create(
                thread_id=chat.threadId,
                assistant_id=chat.astId,
        )

def create_run(chat : modelType.AssistantChat, user_message):
        run = submit_message(chat, user_message)
        return run



async def get_response(thread_id: str):
        client = OpenAI()
        return client.beta.threads.messages.list(thread_id=thread_id, order="asc")


def pretty_print(messages):
        print("# Messages")
        for m in messages:
                print(f"{m.role}: {m.content[0].text.value}")
        print()


def prettify_all_response(response):
        assistant_response = []
        for m in response:
                response = {
                        "id": m.id,
                        "role": m.role,
                        "message": m.content[0].text.value,
                        "thread_id": m.thread_id,
                        "created_at": m.created_at
                }
                assistant_response.append(response)

        return assistant_response


def prettify_single_response(response):
        all_messages = []

        for m in response:
                all_messages.append(m)

        last_response = all_messages[len(all_messages) - 1]

        assistant_response = [
                {
                        "id": last_response.id,
                        "role": last_response.role,
                        "message": last_response.content[0].text.value,
                        "thread_id": last_response.thread_id,
                        "created_at": last_response.created_at
                }
        ]

        return assistant_response


import io
from fastapi import UploadFile
from openai import OpenAI

async def create_file(file: UploadFile, vector_storeId):
    print('1.4.1')
    client = OpenAI()
    
    # Read the file contents
    contents = await file.read()
    
    # Create a BytesIO object and set its name attribute to include the filename with extension
    file_like = io.BytesIO(contents)
    file_like.name = file.filename  # Add this to ensure the file has its original name
    
    print('1.4.2')
    created_file = client.files.create(file=file_like, purpose="assistants")
    
    print('1.4.3')
    fileId = created_file.id
    
    # Associate the file with the vector store
    vector_store_file = client.beta.vector_stores.files.create(
        vector_store_id=vector_storeId,
        file_id=fileId
    )
    
    print('1.4.4')
    
    # Create a file object with metadata
    file_object = {
        "fileId": created_file.id,
        "fileName": file.filename,
        "fileSize": file.size,
        "fileType": file.content_type,
    }
    
    print('1.4.5')
    return file_object



async def create_files(files: [UploadFile],vector_storeId):
        print('1.4.1')
        async_files = [create_file(file,vector_storeId) for file in files]
        files = await asyncio.gather(*async_files)
        return files
