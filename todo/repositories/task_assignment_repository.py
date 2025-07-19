from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId

from todo.models.task_assignment import TaskAssignmentModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.common.pyobjectid import PyObjectId


class TaskAssignmentRepository(MongoRepository):
    collection_name = TaskAssignmentModel.collection_name

    @classmethod
    def create(cls, task_assignment: TaskAssignmentModel) -> TaskAssignmentModel:
        """
        Creates a new task assignment.
        """
        collection = cls.get_collection()
        task_assignment.created_at = datetime.now(timezone.utc)
        task_assignment.updated_at = None

        task_assignment_dict = task_assignment.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(task_assignment_dict)
        task_assignment.id = insert_result.inserted_id
        return task_assignment

    @classmethod
    def get_by_task_id(cls, task_id: str) -> Optional[TaskAssignmentModel]:
        """
        Get the task assignment for a specific task.
        """
        collection = cls.get_collection()
        try:
            # Try with ObjectId first
            task_assignment_data = collection.find_one({"task_id": ObjectId(task_id), "is_active": True})
            if not task_assignment_data:
                # Try with string if ObjectId doesn't work
                task_assignment_data = collection.find_one({"task_id": task_id, "is_active": True})

            if task_assignment_data:
                return TaskAssignmentModel(**task_assignment_data)
            return None
        except Exception:
            return None

    @classmethod
    def get_by_assignee_id(cls, assignee_id: str, user_type: str) -> List[TaskAssignmentModel]:
        """
        Get all task assignments for a specific assignee (team or user).
        """
        collection = cls.get_collection()
        try:
            # Try with ObjectId first
            task_assignments_data = collection.find(
                {"assignee_id": ObjectId(assignee_id), "user_type": user_type, "is_active": True}
            )
            if not list(task_assignments_data):
                # Try with string if ObjectId doesn't work
                task_assignments_data = collection.find(
                    {"assignee_id": assignee_id, "user_type": user_type, "is_active": True}
                )
            return [TaskAssignmentModel(**data) for data in task_assignments_data]
        except Exception:
            return []

    @classmethod
    def update_assignment(
        cls, task_id: str, assignee_id: str, user_type: str, user_id: str
    ) -> Optional[TaskAssignmentModel]:
        """
        Update the assignment for a task.
        """
        collection = cls.get_collection()
        try:
            # Deactivate current assignment if exists (try both ObjectId and string)
            collection.update_many(
                {"task_id": ObjectId(task_id), "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": ObjectId(user_id),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            # Also try with string
            collection.update_many(
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": ObjectId(user_id),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

            new_assignment = TaskAssignmentModel(
                _id=PyObjectId(),
                task_id=PyObjectId(task_id),
                assignee_id=PyObjectId(assignee_id),
                user_type=user_type,
                created_by=PyObjectId(user_id),
                updated_by=None,
            )

            return cls.create(new_assignment)
        except Exception:
            return None

    @classmethod
    def delete_assignment(cls, task_id: str, user_id: str) -> bool:
        """
        Soft delete a task assignment by setting is_active to False.
        """
        collection = cls.get_collection()
        try:
            # Try with ObjectId first
            result = collection.update_one(
                {"task_id": ObjectId(task_id), "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": ObjectId(user_id),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            if result.modified_count == 0:
                # Try with string if ObjectId doesn't work
                result = collection.update_one(
                    {"task_id": task_id, "is_active": True},
                    {
                        "$set": {
                            "is_active": False,
                            "updated_by": ObjectId(user_id),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def update_executor(cls, task_id: str, executor_id: str, user_id: str) -> bool:
        """
        Update the executor_id for the active assignment of the given task_id.
        """
        collection = cls.get_collection()
        try:
            result = collection.update_one(
                {"task_id": ObjectId(task_id), "is_active": True},
                {
                    "$set": {
                        "assignee_id": executor_id,
                        "user_type": "user",
                        "updated_by": user_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            if result.modified_count == 0:
                # Try with string if ObjectId doesn't work
                result = collection.update_one(
                    {"task_id": task_id, "is_active": True},
                    {
                        "$set": {
                            "assignee_id": executor_id,
                            "user_type": "user",
                            "updated_by": user_id,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def deactivate_by_task_id(cls, task_id: str, user_id: str) -> bool:
        """
        Deactivate all assignments for a specific task by setting is_active to False.
        """
        collection = cls.get_collection()
        try:
            # Try with ObjectId first
            result = collection.update_many(
                {"task_id": ObjectId(task_id), "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": ObjectId(user_id),
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            if result.modified_count == 0:
                # Try with string if ObjectId doesn't work
                result = collection.update_many(
                    {"task_id": task_id, "is_active": True},
                    {
                        "$set": {
                            "is_active": False,
                            "updated_by": ObjectId(user_id),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            return result.modified_count > 0
        except Exception:
            return False
