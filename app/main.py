from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()
from app.config import settings
from app.routers import assistant
from app.routers import threads
from app.routers import chats
from app.routers import auth,enduser,channels
app = FastAPI()

origins = [settings.CLIENT_ORIGIN]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, tags=["Authentication"], prefix="/api/auth")
app.include_router(assistant.router, tags=["Assistant"], prefix="/api/assistant")
app.include_router(threads.router, tags=["Threads"], prefix="/api/threads")
app.include_router(chats.router, tags=["Chats"], prefix="/api/chats")
app.include_router(enduser.router, tags = ["Enduser API"],prefix="/api/enduser")
app.include_router(channels.router, tags=["Channel"], prefix="/api/channel")

@app.get("/health")
async def root():
    return {"message": "API is working fine."}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="127.0.0.1", port=8000, log_level="info", reload=True
    )

# App run command
# uvicorn app.main:app --reload

# Swagger URL for this API's
# http://127.0.0.1:8000/docs#/
