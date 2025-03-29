from typing import List
from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository


class TaskRepository(MongoRepository):
    collection_name = TaskModel.collection_name

    @classmethod
    def list(cls, page: int, limit: int) -> List[TaskModel]:
        tasks_collection = cls.get_collection()
        tasks_cursor = tasks_collection.find().skip((page - 1) * limit).limit(limit)
        return [TaskModel(**task) for task in tasks_cursor]

    @classmethod
    def count(cls) -> int:
        tasks_collection = cls.get_collection()
        return tasks_collection.count_documents({})

    @classmethod
    def get_all(cls) -> List[TaskModel]:
        """
        Get all tasks from the repository

        Returns:
            List[TaskModel]: List of all task models
        """
        tasks_collection = cls.get_collection()
        tasks_cursor = tasks_collection.find()
        return [TaskModel(**task) for task in tasks_cursor]
