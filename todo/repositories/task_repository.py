from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pymongo import ReturnDocument

from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.messages import RepositoryErrors


class TaskRepository(MongoRepository):
    collection_name = TaskModel.collection_name
    _exclude_deleted = {'$ne': True}


    def _add_soft_delete_filter(cls, filter_dict: dict = None) -> dict:
        """Add soft delete filter to query if not already present"""
        if filter_dict is None:
            filter_dict = {}
        
        # Only add the filter if isDeleted is not already specified
        if 'isDeleted' not in filter_dict:
            filter_dict['isDeleted'] = {'$ne': True}
        
        return filter_dict

    @classmethod
    def list(cls, page: int, limit: int) -> List[TaskModel]:
        tasks_collection = cls.get_collection()
        tasks_cursor = tasks_collection.find(cls._exclude_deleted).skip((page - 1) * limit).limit(limit)
        return [TaskModel(**task) for task in tasks_cursor]

    @classmethod
    def count(cls) -> int:
        tasks_collection = cls.get_collection()
        return tasks_collection.count_documents(cls._exclude_deleted)

    @classmethod
    def get_all(cls) -> List[TaskModel]:
        """
        Get all tasks from the repository

        Returns:
            List[TaskModel]: List of all task models
        """
        tasks_collection = cls.get_collection()
        tasks_cursor = tasks_collection.find(cls._exclude_deleted)
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
        """
        Gets a specific task by its ID.
        """

        tasks_collection = cls.get_collection()   
        task_data = tasks_collection.find_one({**cls._exclude_deleted, "_id": ObjectId(task_id)})

        if task_data:
            return TaskModel(**task_data)
        return None

    @classmethod
    def delete_by_id(cls, task_id: str) -> TaskModel | None:
        """
        Deletes a specific task by its ID.
        """
        tasks_collection = cls.get_collection()

        try:
            obj_id = ObjectId(task_id)
        except Exception:
            return None

        deleted_task_data = tasks_collection.find_one_and_update(
            {"_id": obj_id, **cls._exclude_deleted},
            {
                "$set": {
                    "isDeleted": True,
                    "updatedAt": datetime.now(timezone.utc),
                    "updatedBy": "system",
                }  # TODO: modify to use actual user after auth implementation,
            },
            return_document=ReturnDocument.AFTER,
        )

        if deleted_task_data:
            return TaskModel(**deleted_task_data)
        return None

    @classmethod
    def update(cls, task_id: str, update_data: dict) -> TaskModel | None:
        """
        Updates a specific task by its ID with the given data.
        """
        if not isinstance(update_data, dict):
            raise ValueError("update_data must be a dictionary.")

        try:
            obj_id = ObjectId(task_id)
        except Exception:
            return None

        update_data_with_timestamp = {**update_data, "updatedAt": datetime.now(timezone.utc)}
        update_data_with_timestamp.pop("_id", None)
        update_data_with_timestamp.pop("id", None)

        tasks_collection = cls.get_collection()

        updated_task_doc = tasks_collection.find_one_and_update(
            {"_id": obj_id, **cls._exclude_deleted}, {"$set": update_data_with_timestamp}, return_document=ReturnDocument.AFTER
        )

        if updated_task_doc:
            return TaskModel(**updated_task_doc)
        return None
