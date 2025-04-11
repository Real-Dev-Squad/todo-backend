from pymongo import DESCENDING
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
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

    
    @classmethod
    def create(cls, task: TaskModel) -> TaskModel:
        """
        Creates a new task in the repository with a unique displayId, inside a transaction.
        Retries if displayId conflicts occur.

        Args:
            task (TaskModel): Task to create

        Returns:
            TaskModel: Created task with displayId
        """
        tasks_collection = cls.get_collection()
        client = cls.get_client()

        with client.start_session() as session:
            for _ in range(3):
                try:
                    with session.start_transaction():
                        last_task = tasks_collection.find_one(sort=[("displayId", DESCENDING)], session=session)

                        if last_task and "displayId" in last_task:
                            last_number = int(last_task["displayId"].split("-")[-1])
                            task.displayId = f"TASK-{last_number + 1:06d}"
                        else:
                            task.displayId = "TASK-0001"

                        task.createdAt = datetime.now(timezone.utc)
                        task.updatedAt = None

                        task_dict = task.model_dump(mode="json", by_alias=True, exclude_none=True)
                        insert_result = tasks_collection.insert_one(task_dict, session=session)

                        task.id = insert_result.inserted_id
                        return task
                    
                except DuplicateKeyError:
                    continue
                
        raise ValueError("Failed to create task with a unique displayId after 3 attempts.")
