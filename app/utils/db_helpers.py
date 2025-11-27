import os
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId


USER_COLLECTION_NAME = os.getenv("USERS_COLLECTION_NAME", "users_collection")


def get_user_collection(db: Any):
    """
    Return the Mongo collection that stores user documents.
    The default legacy collection name is `users_collection`, but this helper
    allows overriding via the USERS_COLLECTION_NAME env var.
    """
    return db[USER_COLLECTION_NAME]


def normalize_object_id(value: Any):
    """
    Convert a string representation of an ObjectId into an actual ObjectId so
    queries continue to work regardless of whether callers pass str or ObjectId.
    """
    if isinstance(value, ObjectId):
        return value

    if isinstance(value, str):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return value

    return value

