import uuid
from app.utils.mongo_utils import save_created_thread
from app.utils.mongo_utils import fetch_threads_by_assistant_id
from app.utils.open_ai_utils import create_thread
from app.utils.open_ai_utils import create_thread_title
from app.utils.open_ai_utils import get_all_thread_history
import app.utils.open_ai_utils as ai_utils
import app.models.model_types as model_type


# async def create_new_thread(userId,thread: model_type.AssistantThread):
#         created_thread = await create_thread()
#         thread_title = await create_thread_title(thread.threadTitle)
#         thread.threadTitle = thread_title
#         save_created_thread(userId,thread, created_thread.id)
#         return {"thread": created_thread}

async def create_new_thread(userId,thread: model_type.AssistantThread):
        print("C.2.1")
        user_token = await generate_user_token(userId)
        print("C.2.2")
        created_thread = await create_thread()
        print("C.2.3")
        thread_title = await create_thread_title(thread.threadTitle)
        print("C.2.4")
        thread.threadTitle = thread_title
        print("C.2.5")
        save_created_thread(user_token,userId,thread, created_thread.id)
        print("C.2.6")
        return {"thread": created_thread}

async def get_all_threads(userId,assistant_id: str):
        result = fetch_threads_by_assistant_id(userId,assistant_id)
        return result


async def get_thread_history_by_id(thread_id: str):
        result = await get_all_thread_history(thread_id)
        return result

async def generate_user_token(user_id):
    # Combine user_id with current timestamp
    api_token = ai_utils.generate_api_token(user_id)
    return api_token
