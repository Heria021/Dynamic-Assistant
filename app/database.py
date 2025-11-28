from pymongo import MongoClient
from app.config import settings

# Sync Mongo Client
client = MongoClient(settings.DATABASE_URL)
print("MongoDB Connected Successfully...")

# Return actual database object (not module)
db = client[settings.MONGO_INITDB_DATABASE]

# Collections
OurAssistant = db["Assistant"]
AssistantThreads = db["AssistantThreads"]
UsersCollection = db["users_collection"]
UserProfiles = db["UserProfiles"]

def get_database():
    """Return the actual MongoDB database instance."""
    return db
