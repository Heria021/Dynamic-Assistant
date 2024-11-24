import json
import secrets
from fastapi import UploadFile
from openai import OpenAI
import app.models.model_types as model_type
import app.helpers.openai_helper as ai_helper
from fastapi import HTTPException, status
import hashlib
import time

async def create_thread_title(content: str) -> str:
    template_string = f"""
                content = {content}
                task = Give me a short title using the content which we have mentioned earlier under 8-10 words 
                without any special character or double quotes. And don't write or tell me what you're really doing, The Final response should contain only the Title and Nothing else.
        """
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": template_string},
        ],
    )

    return response.choices[0].message.content

def generate_api_token(user_id) :
    # Combine user_id with current timestamp
    raw_token = f"{user_id}-{time.time()}-{secrets.token_urlsafe(16)}"
    
    # Hash the combined string using SHA-256
    hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
    
    return hashed_token

async def create_assistant(payload: model_type.Assistant):
    assistant_tools = []
    print("1.1")
    for aiTool in payload.astTools:
        for ai_tool in aiTool.split(','):
            tool = {"type": ai_tool}
            assistant_tools.append(tool)
    print("1.2")
    client = OpenAI()
    assistant = client.beta.assistants.create(
        name=payload.astName,
        instructions=payload.astInstruction,
        model=payload.gptModel,
        tools=assistant_tools,
    )
    print("1.3")
    return assistant


async def update_assistant(payload: model_type.UpdateAssistant):
    assistant_tools = []

    for aiTool in payload.astTools:
        tool = {"type": aiTool}
        assistant_tools.append(tool)

    client = OpenAI()
    assistant = client.beta.assistants.update(
        assistant_id=payload.astId,
        name=payload.astName,
        instructions=payload.astInstruction,
        model=payload.gptModel,
        tools=assistant_tools,
    )
    return assistant


async def create_assistant_with_file(
    payload: model_type.Assistant, files: list[UploadFile]
):
    assistant_tools = []
    print("1.1")
    try:
        for aiTool in payload.astTools:
            for ai_tool in aiTool.split(','):
                tool = {"type": ai_tool}
                assistant_tools.append(tool)
        print("1.2")

        client = OpenAI()
        vector_store = client.beta.vector_stores.create(
        name = payload.astName
    )
        print("1.3")
        vector_store_id = vector_store.id
        print("1.4")
        files_list = await ai_helper.create_files(files,vector_store_id)
        print("1.5")
        file_ids: list = []
        for element in files_list:
            file_id = element["fileId"]
            file_ids.append(file_id)
        print("1.6")
        tool_resources_set = {
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        print("1.7")
        assistant = client.beta.assistants.create(
            name=payload.astName,
            instructions=payload.astInstruction,
            model=payload.gptModel,
            tools=assistant_tools,
            tool_resources=tool_resources_set,
        )
        print("1.8")
        response = {"files": files_list, "assistant": assistant}
        return response

    except Exception as e:
        return f"There was an error creating the Assistant{e}"


async def get_assistant_by_id(ast_id: str):
    try:
        client = OpenAI()
        assistant = client.beta.assistants.retrieve(assistant_id=ast_id)

        response = {"assistant": assistant}
        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{e.args}",
        )


async def upload_assistant_files(ast_id: str, files: list[UploadFile]):
    assistant = await get_assistant_by_id(ast_id)
    old_file_ids = assistant["assistant"].file_ids

    try:
        client = OpenAI()

        files_list = await ai_helper.create_files(files)

        for element in files_list:
            file_id = element["fileId"]
            old_file_ids.append(file_id)

        assistant = client.beta.assistants.update(
            assistant_id=ast_id,
            file_ids=old_file_ids,
        )

        response = {"files": files_list}
        return response

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{e.args}",
        )


async def create_thread():
    client = OpenAI()
    thread = client.beta.threads.create()
    return thread


async def get_all_thread_history(thread_id: str):
    messages = await ai_helper.get_response(thread_id)
    prettified_response = ai_helper.prettify_all_response(messages)
    return prettified_response


async def create_assistant_chat(chat: model_type.AssistantChat, message):
    run = ai_helper.create_run(chat,message)
    run = ai_helper.wait_on_run(run, chat.threadId)
    response = await ai_helper.get_response(chat.threadId)
    prettified_response = ai_helper.prettify_single_response(response)
    return prettified_response

async def upload_image_to_openai(image: UploadFile,client):
    try:
        client = OpenAI()

        # Read the file's content as bytes
        file_content = await image.read()

        # Upload the file content to OpenAI
        response = client.files.create(
            file=(image.filename, file_content),
            purpose='vision'
        )

        file_id = response.id
        return file_id
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image to OpenAI: {e}")