from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pymongo import ReturnDocument, ASCENDING, DESCENDING

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.messages import ApiErrors, RepositoryErrors


class TaskRepository(MongoRepository):
    collection_name = TaskModel.collection_name

    @classmethod
    def list(cls, page: int, limit: int, sort_by: str = "createdAt", order: str = "desc") -> List[TaskModel]:
        """
        Get a paginated list of tasks with sorting applied at the database level.

        Args:
            page (int): Page number (1-based)
            limit (int): Number of items per page
            sort_by (str): Field to sort by (priority, dueAt, createdAt, assignee)
            order (str): Sort order (asc or desc)

        Returns:
            List[TaskModel]: List of task models for the specified page
        """
        tasks_collection = cls.get_collection()

        if sort_by == "assignee":
            pipeline = [
                {"$lookup": {"from": "users", "localField": "assignee", "foreignField": "_id", "as": "assignee_info"}},
                {"$addFields": {"assignee_name": {"$ifNull": [{"$arrayElemAt": ["$assignee_info.name", 0]}, ""]}}},
                {"$sort": {"assignee_name": ASCENDING if order == "asc" else DESCENDING}},
                {"$skip": (page - 1) * limit},
                {"$limit": limit},
            ]

            tasks_cursor = tasks_collection.aggregate(pipeline)
            return [TaskModel(**task) for task in tasks_cursor]

        elif sort_by == "priority":
            sort_direction = ASCENDING if order == "desc" else DESCENDING
        else:
            sort_direction = ASCENDING if order == "asc" else DESCENDING

        tasks_cursor = tasks_collection.find().sort(sort_by, sort_direction).skip((page - 1) * limit).limit(limit)

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

    @classmethod
    def delete_by_id(cls, task_id: ObjectId, user_id: str) -> TaskModel | None:
        tasks_collection = cls.get_collection()

        task = tasks_collection.find_one({"_id": task_id, "isDeleted": False})
        if not task:
            raise TaskNotFoundException(task_id)

        assignee_id = task.get("assignee")

        if assignee_id:
            if assignee_id != user_id:
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)
        else:
            if user_id != task.get("createdBy"):
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)

        deleted_task_data = tasks_collection.find_one_and_update(
            {"_id": task_id},
            {
                "$set": {
                    "isDeleted": True,
                    "updatedAt": datetime.now(timezone.utc),
                    "updatedBy": user_id,
                }
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
            {"_id": obj_id}, {"$set": update_data_with_timestamp}, return_document=ReturnDocument.AFTER
        )

        if updated_task_doc:
            return TaskModel(**updated_task_doc)
        return None
