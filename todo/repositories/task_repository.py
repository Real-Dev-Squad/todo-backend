from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pymongo import ReturnDocument

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.constants.messages import ApiErrors, RepositoryErrors
from todo.constants.task import SORT_FIELD_PRIORITY, SORT_FIELD_ASSIGNEE, SORT_ORDER_DESC


class TaskRepository(MongoRepository):
    collection_name = TaskModel.collection_name

    @classmethod
    def list(cls, page: int, limit: int, sort_by: str, order: str) -> List[TaskModel]:
        tasks_collection = cls.get_collection()

        if sort_by == SORT_FIELD_PRIORITY:
            sort_direction = 1 if order == SORT_ORDER_DESC else -1
            sort_criteria = [(sort_by, sort_direction)]
        elif sort_by == SORT_FIELD_ASSIGNEE:
            return cls._list_sorted_by_assignee(page, limit, order)
        else:
            sort_direction = -1 if order == SORT_ORDER_DESC else 1
            sort_criteria = [(sort_by, sort_direction)]

        tasks_cursor = tasks_collection.find().sort(sort_criteria).skip((page - 1) * limit).limit(limit)
        return [TaskModel(**task) for task in tasks_cursor]

    @classmethod
    def _list_sorted_by_assignee(cls, page: int, limit: int, order: str) -> List[TaskModel]:
        """Handle assignee sorting using aggregation pipeline to sort by user names"""
        tasks_collection = cls.get_collection()

        sort_direction = -1 if order == SORT_ORDER_DESC else 1

        pipeline = [
            {
                "$addFields": {
                    "assignee_oid": {
                        "$cond": {
                            "if": {"$ne": ["$assignee", None]},
                            "then": {"$toObjectId": "$assignee"},
                            "else": None,
                        }
                    }
                }
            },
            {"$lookup": {"from": "users", "localField": "assignee_oid", "foreignField": "_id", "as": "assignee_user"}},
            {"$addFields": {"assignee_name": {"$ifNull": [{"$arrayElemAt": ["$assignee_user.name", 0]}, ""]}}},
            {"$sort": {"assignee_name": sort_direction}},
            {"$skip": (page - 1) * limit},
            {"$limit": limit},
            {"$project": {"assignee_user": 0, "assignee_name": 0, "assignee_oid": 0}},
        ]

        result = list(tasks_collection.aggregate(pipeline))
        return [TaskModel(**task) for task in result]

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

    @classmethod
    def get_tasks_for_user(cls, user_id: str, page: int, limit: int) -> List[TaskModel]:
        tasks_collection = cls.get_collection()
        query = {"$or": [{"createdBy": user_id}, {"assignee": user_id}]}
        tasks_cursor = tasks_collection.find(query).skip((page - 1) * limit).limit(limit)
        return [TaskModel(**task) for task in tasks_cursor]
