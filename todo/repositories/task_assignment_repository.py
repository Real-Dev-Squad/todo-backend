from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.task_assignment import TaskAssignmentModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.common.pyobjectid import PyObjectId
from todo.constants.task import TaskStatus
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService


class TaskAssignmentRepository(MongoRepository):
    collection_name = TaskAssignmentModel.collection_name

    @classmethod
    def create(cls, task_assignment: TaskAssignmentModel) -> TaskAssignmentModel:
        collection = cls.get_collection()
        task_assignment.created_at = datetime.now(timezone.utc)
        task_assignment.updated_at = None

        task_assignment_dict = task_assignment.model_dump(mode="json", by_alias=True, exclude_none=True)
        insert_result = collection.insert_one(task_assignment_dict)
        task_assignment.id = insert_result.inserted_id

        dual_write_service = EnhancedDualWriteService()
        task_assignment_data = {
            "task_mongo_id": str(task_assignment.task_id),
            "assignee_id": str(task_assignment.assignee_id),
            "user_type": task_assignment.user_type,
            "team_id": str(task_assignment.team_id) if task_assignment.team_id else None,
            "is_active": task_assignment.is_active,
            "created_at": task_assignment.created_at,
            "updated_at": task_assignment.updated_at,
            "created_by": str(task_assignment.created_by),
            "updated_by": str(task_assignment.updated_by) if task_assignment.updated_by else None,
        }

        dual_write_success = dual_write_service.create_document(
            collection_name="task_assignments", data=task_assignment_data, mongo_id=str(task_assignment.id)
        )

        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync task assignment {task_assignment.id} to Postgres")

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
            current_assignment = cls.get_by_task_id(task_id)

            if not current_assignment:
                raise TaskNotFoundException(task_id)

            team_id = None

            if user_type == "team":
                team_id = assignee_id
            elif user_type == "user" and current_assignment.team_id is not None:
                team_id = current_assignment.team_id

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

            # Sync deactivation to PostgreSQL
            if current_assignment:
                dual_write_service = EnhancedDualWriteService()
                deactivation_data = {
                    "task_mongo_id": str(current_assignment.task_id),
                    "assignee_id": str(current_assignment.assignee_id),
                    "user_type": current_assignment.user_type,
                    "team_id": str(current_assignment.team_id) if current_assignment.team_id else None,
                    "is_active": False,
                    "created_at": current_assignment.created_at,
                    "updated_at": datetime.now(timezone.utc),
                    "created_by": str(current_assignment.created_by),
                    "updated_by": str(user_id),
                }

                dual_write_success = dual_write_service.update_document(
                    collection_name="task_assignments", data=deactivation_data, mongo_id=str(current_assignment.id)
                )

                if not dual_write_success:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync task assignment deactivation {current_assignment.id} to Postgres")

            new_assignment = TaskAssignmentModel(
                _id=PyObjectId(),
                task_id=PyObjectId(task_id),
                assignee_id=PyObjectId(assignee_id),
                user_type=user_type,
                created_by=PyObjectId(user_id),
                updated_by=None,
                team_id=PyObjectId(team_id),
            )

            return cls.create(new_assignment)
        except Exception:
            return None

    @classmethod
    def delete_assignment(cls, task_id: str, user_id: str) -> bool:
        collection = cls.get_collection()
        try:
            # Get current assignment first
            current_assignment = cls.get_by_task_id(task_id)
            if not current_assignment:
                return False

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

            if result.modified_count > 0:
                # Sync to PostgreSQL
                dual_write_service = EnhancedDualWriteService()
                assignment_data = {
                    "task_mongo_id": str(current_assignment.task_id),
                    "assignee_id": str(current_assignment.assignee_id),
                    "user_type": current_assignment.user_type,
                    "team_id": str(current_assignment.team_id) if current_assignment.team_id else None,
                    "is_active": False,
                    "created_at": current_assignment.created_at,
                    "updated_at": datetime.now(timezone.utc),
                    "created_by": str(current_assignment.created_by),
                    "updated_by": str(user_id),
                }

                dual_write_success = dual_write_service.update_document(
                    collection_name="task_assignments", data=assignment_data, mongo_id=str(current_assignment.id)
                )

                if not dual_write_success:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync task assignment deletion {current_assignment.id} to Postgres")

            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def update_executor(cls, task_id: str, executor_id: str, user_id: str) -> bool:
        collection = cls.get_collection()
        try:
            # Get current assignment first
            current_assignment = cls.get_by_task_id(task_id)
            if not current_assignment:
                return False

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

            if result.modified_count > 0:
                # Sync to PostgreSQL
                dual_write_service = EnhancedDualWriteService()
                assignment_data = {
                    "task_mongo_id": str(current_assignment.task_id),
                    "assignee_id": str(executor_id),
                    "user_type": "user",
                    "team_id": str(current_assignment.team_id) if current_assignment.team_id else None,
                    "is_active": current_assignment.is_active,
                    "created_at": current_assignment.created_at,
                    "updated_at": datetime.now(timezone.utc),
                    "created_by": str(current_assignment.created_by),
                    "updated_by": str(user_id),
                }

                dual_write_success = dual_write_service.update_document(
                    collection_name="task_assignments", data=assignment_data, mongo_id=str(current_assignment.id)
                )

                if not dual_write_success:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync task assignment update {current_assignment.id} to Postgres")

            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def deactivate_by_task_id(cls, task_id: str, user_id: str) -> bool:
        collection = cls.get_collection()
        try:
            # Get all active assignments for this task
            active_assignments = cls.get_by_task_id(task_id)
            if not active_assignments:
                return False

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

            if result.modified_count > 0:
                # Sync to PostgreSQL for each assignment
                dual_write_service = EnhancedDualWriteService()
                assignment_data = {
                    "task_mongo_id": str(active_assignments.task_id),
                    "assignee_id": str(active_assignments.assignee_id),
                    "user_type": active_assignments.user_type,
                    "team_id": str(active_assignments.team_id) if active_assignments.team_id else None,
                    "is_active": False,
                    "created_at": active_assignments.created_at,
                    "updated_at": datetime.now(timezone.utc),
                    "created_by": str(active_assignments.created_by),
                    "updated_by": str(user_id),
                }

                dual_write_success = dual_write_service.update_document(
                    collection_name="task_assignments", data=assignment_data, mongo_id=str(active_assignments.id)
                )

                if not dual_write_success:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to sync task assignment deactivation {active_assignments.id} to Postgres")

            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def reassign_tasks_from_user_to_team(cls, user_id: str, team_id: str, performed_by_user_id: str):
        """
        Reassign all tasks of user to team
        """
        collection = cls.get_collection()
        now = datetime.now(timezone.utc)
        pipeline = [
            {
                "$match": {
                    "team_id": {"$in": [team_id, ObjectId(team_id)]},
                    "assignee_id": {"$in": [user_id, ObjectId(user_id)]},
                    "user_type": "user",
                    "is_active": True,
                }
            },
            {
                "$addFields": {
                    "task_id_obj": {
                        "$convert": {"input": "$task_id", "to": "objectId", "onError": "$task_id", "onNull": None}
                    }
                }
            },
            {"$lookup": {"from": "tasks", "localField": "task_id_obj", "foreignField": "_id", "as": "task_info"}},
            {"$unwind": "$task_info"},
            {"$match": {"task_info.status": {"$ne": TaskStatus.DONE.value}}},
        ]
        user_task_assignments = list(collection.aggregate(pipeline))
        if not user_task_assignments:
            return 0

        # Deactivate current assignment (try using both ObjectId and string)
        collection.update_many(
            {"assignee_id": ObjectId(user_id), "team_id": ObjectId(team_id), "is_active": True},
            {"$set": {"is_active": False, "updated_by": ObjectId(performed_by_user_id), "updated_at": now}},
        )

        collection.update_many(
            {"assignee_id": user_id, "team_id": team_id, "is_active": True},
            {"$set": {"is_active": False, "updated_by": ObjectId(performed_by_user_id), "updated_at": now}},
        )

        new_assignments = []
        for task in user_task_assignments:
            new_assignments.append(
                TaskAssignmentModel(
                    _id=PyObjectId(),
                    task_id=task["task_id_obj"],
                    assignee_id=PyObjectId(team_id),
                    user_type="team",
                    created_by=PyObjectId(performed_by_user_id),
                    updated_by=None,
                    team_id=PyObjectId(team_id),
                ).model_dump(mode="json", by_alias=True, exclude_none=True)
            )
        if new_assignments:
            collection.insert_many(new_assignments)
        return len(new_assignments)
