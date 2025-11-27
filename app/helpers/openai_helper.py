import asyncio
import io
import time
from typing import List, Optional

import app.models.model_types as modelType
from fastapi import UploadFile
from openai import OpenAI


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
        tools: List[str],
        file_ids: Optional[List[str]] = None,
    ):
        tool_payload = [{"type": tool} for tool in tools]
        payload = {
            "name": name,
            "instructions": instructions,
            "model": model,
            "tools": tool_payload,
        }

        if file_ids:
            payload["file_ids"] = file_ids

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
        run = self.client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        while run.status in {"queued", "in_progress"}:
            time.sleep(0.5)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
        return run

    async def create_message_and_run(
        self,
        thread_id: str,
        assistant_id: str,
        message: str,
        images: Optional[List[dict]] = None,
    ) -> dict:
        content = [{"type": "text", "text": message}]
        if images:
            for image in images:
                content.append(
                    {
                        "type": "input_image",
                        "image": {
                            "data": image.get("data"),
                            "media_type": image.get("content_type", "image/png"),
                        },
                    }
                )

        self.client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=assistant_id
        )
        run = self._wait_for_run(thread_id, run.id)

        messages = self.client.beta.threads.messages.list(
            thread_id=thread_id, order="desc", limit=1
        )
        latest_message = messages.data[0] if messages.data else None
        assistant_response = (
            latest_message.content[0].text.value if latest_message else ""
        )

        tokens_used = getattr(getattr(run, "usage", None), "total_tokens", 0) or 0

        return {
            "response": assistant_response,
            "tokens_used": tokens_used,
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
