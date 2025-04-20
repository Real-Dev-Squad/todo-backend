from abc import ABC

from todo_project.db.config import DatabaseManager


class MongoRepository(ABC):
    collection = None
    collection_name = None
    database_manager = DatabaseManager()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "collection_name") or not isinstance(cls.collection_name, str):
            raise TypeError(f"Class {cls.__name__} must define a static `collection_name` field as a string.")

    @classmethod
    def get_collection(cls):
        if cls.collection is None:
            cls.collection = cls.database_manager.get_collection(cls.collection_name)
        return cls.collection

    @classmethod
    def get_client(cls):
        return cls.database_manager._get_database_client()
    
    @classmethod
    def get_database(cls):
        return cls.database_manager.get_database()
