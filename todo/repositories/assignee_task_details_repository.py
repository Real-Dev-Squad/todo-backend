from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId

from todo.models.assignee_task_details import AssigneeTaskDetailsModel
from todo.repositories.common.mongo_repository import MongoRepository


class AssigneeTaskDetailsRepository(MongoRepository):
    collection_name = AssigneeTaskDetailsModel.collection_name

    @classmethod
    def create(cls, assignee_task: AssigneeTaskDetailsModel) -> AssigneeTaskDetailsModel:
        """
        Creates a new assignee-task relationship.
        """
        collection = cls.get_collection()
        assignee_task.created_at = datetime.now(timezone.utc)
        assignee_task.updated_at = None

        assignee_task_dict = assignee_task.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(assignee_task_dict)
        assignee_task.id = insert_result.inserted_id
        return assignee_task

    @classmethod
    def get_by_task_id(cls, task_id: str) -> Optional[AssigneeTaskDetailsModel]:
        """
        Get the assignee relationship for a specific task.
        """
        collection = cls.get_collection()
        try:
            assignee_task_data = collection.find_one({"task_id": task_id, "is_active": True})
            if assignee_task_data:
                return AssigneeTaskDetailsModel(**assignee_task_data)
            return None
        except Exception:
            return None

    @classmethod
    def get_by_assignee_id(cls, assignee_id: str, relation_type: str) -> list[AssigneeTaskDetailsModel]:
        """
        Get all task relationships for a specific assignee (team or user).
        """
        collection = cls.get_collection()
        try:
          
            from bson import ObjectId
            results = list(collection.find({
                "assignee_id": ObjectId(assignee_id),
                "relation_type": relation_type,
                "is_active": True
            }))
            if not results:
                
                results = list(collection.find({
                    "assignee_id": assignee_id,
                    "relation_type": relation_type,
                    "is_active": True
                }))
            return [AssigneeTaskDetailsModel(**data) for data in results]
        except Exception:
            return []

    @classmethod
    def update_assignee(
        cls, task_id: str, assignee_id: str, relation_type: str, user_id: str
    ) -> Optional[AssigneeTaskDetailsModel]:
        """
        Update the assignee for a task.
        """
        collection = cls.get_collection()
        try:
            # Deactivate current assignee if exists
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

            # Create new assignee relationship
            new_assignee = AssigneeTaskDetailsModel(
                assignee_id=ObjectId(assignee_id),
                task_id=ObjectId(task_id),
                relation_type=relation_type,
                created_by=ObjectId(user_id),
                updated_by=None,
            )

            return cls.create(new_assignee)
        except Exception:
            return None

    @classmethod
    def deactivate_by_task_id(cls, task_id: str, user_id: str) -> bool:
        """
        Deactivate the assignee relationship for a specific task.
        """
        collection = cls.get_collection()
        try:
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
            return result.modified_count > 0
        except Exception:
            return False
