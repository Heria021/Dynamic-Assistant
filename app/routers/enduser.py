from fastapi import APIRouter,Depends,File, UploadFile,Form
import app.controllers.chats as Chat
import app.controllers.threads as Thread
import app.models.model_types as model_type
import app.utils.mongo_utils as mongo
from app.controllers.cognito import get_api_token
import re
from typing import *


router = APIRouter()

@router.post("/end-user-chat")
async def create_chat(
    astName: str = Form(...),
    apiToken:str = Form(...),
    threadtoken: Optional[str] = Form(None),  # Default threadId to None
    message: str = Form(...),
    image: List[UploadFile] = File(None),
):
    print("A")
    astID = await mongo.get_astId_by_astName(astName)
    print("B")
    verification = await get_api_token(astID,apiToken)
    print("C")
    if verification == 'Success':
        thread = model_type.AssistantThread(
            astId=astID,
            threadTitle=message
        )
        print("C.1")
        if threadtoken == None:
            try:
                userId = await mongo.get_userid_by_assistant_id(astID)
                print("C.2")
                created_thread = await Thread.create_new_thread(userId,thread)
                print("C.3")
                response = {
                    "status": True,
                    "message": "Thread created successfully",
                    "data": created_thread
                }
                thread_data = response.get("data", {}).get("thread", None)
                match = re.search(r"id='(.*?)'", str(thread_data))
                thread_id = match.group(1)
                threadID = thread_id

            except Exception as e:
                return {
                    "status": False,
                    "message": f"An error occurred while creating the thread.{e}",
                    "data": None
                }
            print("D")
        else:
            threadID = await mongo.fetch_threadID_by_threadToken(threadtoken)
        print("1.5",threadID)
        thread_data = await mongo.fetch_data_by_thread_id(threadID)
        print("2")
        # Create an instance of AssistantChat
        chat_instance = model_type.AssistantChat(
            userId=verification,
            astId=astID,
            threadId=threadID,
            message=message
        )
        print("5")
        content = await Chat.process_chat_content([chat_instance], image)
        print("6")
        created_response = await Chat.create_new_chat([chat_instance], content)
        print("7")
        response = {
            "status": True,
            "message": "Chat created successfully",
            "data": created_response,
            "thread_data": thread_data
        }

        return response
    else :
        return("Invalid API Token or Assistant Id")

