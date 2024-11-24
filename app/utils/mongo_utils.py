from typing_extensions import Any
from app.schemas import CreateAssistantBaseSchema
from app.schemas import CreateAssistantThreadBaseSchema
from app.database import OurAssistant
from app.database import UsersCollection
from app.database import AssistantThreads
from app.database import UserProfiles
from datetime import datetime
from fastapi import HTTPException, status
import app.models.model_types as modelType

def find_user_by_email(email: str):
    """Find a user by email."""
    return UsersCollection.find_one({"email": email})

def insert_new_user(email: str, sub_id: str, is_confirmed: bool = False):
    """Insert a new user into the database."""
    user_data = {
        "email": email,
        "sub_id": sub_id,
        "is_confirmed": is_confirmed
    }
    return UsersCollection.insert_one(user_data)

def update_user_confirmation_status(email: str, is_confirmed: bool):
    """Update the confirmation status of a user."""
    return UsersCollection.update_one(
        {"email": email},
        {"$set": {"is_confirmed": is_confirmed}}
    )

def save_user_profile(userId,payload: modelType.UserProfile):
    new_profile = {
        "userID": userId,
        "UserName": payload.User_name,
        "UserMail": payload.User_email,
        "OpenAPIkey": payload.OpenAPI_key,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    } # type: ignore
    try:
        UserProfiles.insert_one(new_profile)
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during saving assistant thread in database.",
        )

def save_user_info(email: str, sub_id: str = None, is_confirmed: bool = False):
    try:
        # Define the update operation
        update_operation = {
            "email": email,
            "is_confirmed": is_confirmed
        }

        # Only update sub_id if it is provided
        if sub_id:
            update_operation["sub_id"] = sub_id

        # Use upsert=True to create the document if it doesn't exist
        UsersCollection.update_one(
            {"email": email},
            {"$set": update_operation},
            upsert=True
        )

    except Exception as e:
        print(f"Error saving user info: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while saving user info: {str(e)}")

def save_created_assistant(userId,assistant: modelType.Assistant, assistant_id ,api_token):
    print("2.1")
    new_assistant: CreateAssistantBaseSchema = {
        "userId": userId,
        "api_token": api_token,
        "astId": assistant_id,
        "astName": assistant.astName,
        "astInstruction": assistant.astInstruction,
        "gptModel": assistant.gptModel,
        "astFiles": [],
        "astTools": assistant.astTools,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    } # type: ignore
    try:
        print("2.2")
        OurAssistant.insert_one(new_assistant)
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during saving assistant in database.",
        )


def get_assistant_by_id(assistant_id):
    print("3.1")
    try:
        cur = OurAssistant.find(
            filter={"astId": assistant_id}, projection={"_id": 0}
        ).sort([("createdAt", -1)])
        print("3.2")
        result = []
        print("3.3")
        for doc in cur:
            result.append(doc)
        return result
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during fetching assistant.",
        )


def update_created_assistant(userId,assistant: modelType.UpdateAssistant):
    new_assistant: CreateAssistantBaseSchema = {
        "userId": userId,
        "astId": assistant.astId,
        "astName": assistant.astName,
        "astInstruction": assistant.astInstruction,
        "gptModel": assistant.gptModel,
        "astTools": assistant.astTools,
        "updatedAt": datetime.utcnow(),
    } # type: ignore
    try:
        OurAssistant.update_one({"astId": assistant.astId}, {"$set": new_assistant})
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during saving assistant in database.",
        )


def save_created_assistant_with_file(userId , assistant: modelType.Assistant, assistant_info ,api_token):
    new_assistant: CreateAssistantBaseSchema = {
        "userId": userId,
        "api_token": api_token,
        "astId": assistant_info["assistant"].id,
        "astName": assistant.astName,
        "astInstruction": assistant.astInstruction,
        "gptModel": assistant.gptModel,
        "astTools": assistant.astTools,
        "astFiles": assistant_info["files"],
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    } # type: ignore
    try:
        OurAssistant.insert_one(new_assistant)
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during saving assistant in database.",
        )


def update_assistant_files(ast_id: str, assistant_files):
    try:
        files = assistant_files["files"]
        OurAssistant.update_one(
            {"astId": ast_id}, {"$push": {"astFiles": {"$each": files}}}
        )
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during saving assistant in database.",
        )


def save_created_thread(user_token,userId,payload: modelType.AssistantThread, threadId: str):
    new_assistant: CreateAssistantThreadBaseSchema = {
        "userId": userId,
        "threadToken": user_token,
        "astId": payload.astId,
        "threadId": threadId,
        "threadTitle": payload.threadTitle,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    } # type: ignore
    try:
        AssistantThreads.insert_one(new_assistant)
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during saving assistant thread in database.",
        )


def fetch_all_assistants(user_id: str):
    try:

        cur = OurAssistant.find(
            filter={"userId": user_id}, 
            projection={
                "_id": 0, 
                "astId": 1, 
                "astName": 1, 
                "astInstruction": 1, 
                "gptModel": 1, 
                "astTools": 1, 
                "astTopP": 1,
                "funcDesc": 1, 
                "createdAt": 1, 
                "updatedAt": 1
            }
        ).sort([("createdAt", -1)])

        # Convert cursor to list
        result = [doc for doc in cur]

        return result
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during fetching assistants.{e}",
        )


def fetch_threads_by_assistant_id(userId,assistant_id: str):
    try:
        cur = AssistantThreads.find(
            filter={"userId": userId,"astId": assistant_id}, projection={"_id": 0}
        ).sort([("createdAt", -1)])
        result = []
        for doc in cur:
            result.append(doc)
        print(f"Find assistants", result)
        return result
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during fetching assistant.",
        )

async def get_astId_by_apiToken(api_token: str):
    try:
        doc = OurAssistant.find(
            filter={"api_token": api_token},
            projection={"_id": 0, "astId": 1}
        )    
        result = None
        for document in doc:
            result = document.get("astId")
        
        if not result:
            print(f"No assistant found for api token {api_token}")
            return ""
        return result
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Something went wrong during fetching vector store."
        )
    

async def get_astId_by_astName(astName: str):
    try:
        doc = OurAssistant.find(
            filter={"astName": astName},
            projection={"_id": 0, "astId": 1}
        )    
        result = None
        for document in doc:
            result = document.get("astId")
        
        if not result:
            print(f"No assistant found for ast name {astName}")
            return ""
        return result
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Something went wrong during fetching vector store."
        )
    

async def get_userid_by_assistant_id(assistant_id):
    try:
        doc = OurAssistant.find_one(
            filter={"astId": assistant_id},
            projection={"_id": 0, "userId": 1},
            sort=[("createdAt", -1)])
        
        print("Document found: ",doc["userId"])  # Debugging line

        return doc["userId"]

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Something went wrong during fetching assistant."
        )
    
async def fetch_threadID_by_threadToken(threadToken: str):
    try:
        doc = AssistantThreads.find(
            filter={"threadToken": threadToken},
            projection={"_id": 0, "threadId": 1}
        ).sort([("createdAt", -1)]).limit(1)
        
        result = None
        for document in doc:
            result = document.get("threadId")
        
        if not result:
            print(f"No threadId found for threadToken {threadToken}")
            return None
        return result
    except Exception as e:
        return f"Error fetching  threadID: {e}"
    
async def fetch_data_by_thread_id(thread_id):
    print("THREAD_ID:",thread_id)
    try:
        cur = AssistantThreads.find(
            filter={"threadId": thread_id}, projection={"_id": 0,"threadToken": 1,"threadTitle":1}
        ).sort([("createdAt", -1)])
        result = []
        print("CUR :",cur)
        for doc in cur:
            print("DOC:",doc)
            result.append(doc)
        print(f"Find thread data", result)
        return result
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Something went wrong during fetching assistant.",
        )


def fetch_channel_info_by_ast_id(userid: str):
    try:
        cur = OurAssistant.find(
            filter={"astId": userid}, projection={"_id": 0, "astName": 1, "api_token": 1}
        ).sort([("createdAt", -1)])
        result = []
        for doc in cur:
            result.append(doc)
        return result
    except Exception as e:
        print(f"Error {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Something went wrong during fetching assistant.",
        )
