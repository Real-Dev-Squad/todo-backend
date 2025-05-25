from datetime import datetime, timezone
from typing import List
from bson import ObjectId

from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.messages import RepositoryErrors


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
        Creates a new task in the repository with a unique displayId, using atomic counter operations.

        Args:
            task (TaskModel): Task to create

        Returns:
            TaskModel: Created task with displayId
        """
        tasks_collection = cls.get_collection()
        client = cls.get_client()

        with client.start_session() as session:
            try:
                with session.start_transaction():
                    # Atomically increment and get the next counter value
                    db = cls.get_database()
                    counter_result = db.counters.find_one_and_update(
                        {"_id": "taskDisplayId"}, {"$inc": {"seq": 1}}, return_document=True, session=session
                    )

                    if not counter_result:
                        db.counters.insert_one({"_id": "taskDisplayId", "seq": 1}, session=session)
                        next_number = 1
                    else:
                        next_number = counter_result["seq"]

                    task.displayId = f"#{next_number}"
                    task.createdAt = datetime.now(timezone.utc)
                    task.updatedAt = None

                    task_dict = task.model_dump(mode="json", by_alias=True, exclude_none=True)
                    insert_result = tasks_collection.insert_one(task_dict, session=session)

                    task.id = insert_result.inserted_id
                    return task

            except Exception as e:
                raise ValueError(RepositoryErrors.TASK_CREATION_FAILED.format(str(e)))

    @classmethod
    def get_by_id(cls, task_id: str) -> TaskModel | None:
        tasks_collection = cls.get_collection()
        task_data = tasks_collection.find_one({"_id": ObjectId(task_id)})
        if task_data:
            return TaskModel(**task_data)
        return None
