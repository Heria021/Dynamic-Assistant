from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import mongo_client
from app.config import settings

_async_client = None
_async_db = None
_sync_client = None
_sync_db = None

async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI async dependency that returns the motor async database."""
    global _async_client, _async_db
    if _async_client is None:
        _async_client = AsyncIOMotorClient(settings.DATABASE_URL)
        _async_db = _async_client[settings.MONGO_INITDB_DATABASE]
        print('Async MongoDB Connected Successfully...')
    return _async_db

def get_sync_database():
    """For backwards compatibility with synchronous code."""
    global _sync_client, _sync_db
    if _sync_client is None:
        _sync_client = mongo_client.MongoClient(settings.DATABASE_URL)
        _sync_db = _sync_client[settings.MONGO_INITDB_DATABASE]
        print('Sync MongoDB Connected Successfully...')
    return _sync_db

