from app.config import settings

# Re-export synchronous and (legacy) database helpers from app.database.db
from .db import get_sync_database

# Provide a module-level synchronous database connection for code that
# expects `from app.database import get_database` (backwards compatibility).
# Internally use the get_sync_database() implementation defined in db.py.
db = get_sync_database()

OurAssistant = db.Assistant
AssistantThreads = db.AssistantThreads
UsersCollection = db.users_collection
UserProfiles = db.UserProfiles

__all__ = ['OurAssistant', 'AssistantThreads', 'UsersCollection', 'UserProfiles', 'get_database', 'get_sync_database']

def get_database():
    """Synchronous helper (legacy API) returning a pymongo database instance.

    Kept for backward compatibility with existing imports of
    `from app.database import get_database`.
    """
    return db
