from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pymongo import ReturnDocument
import logging

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.repositories.task_assignment_repository import TaskAssignmentRepository
from todo.constants.messages import ApiErrors, RepositoryErrors
from todo.constants.task import SORT_FIELD_PRIORITY, SORT_FIELD_ASSIGNEE, SORT_ORDER_DESC, TaskStatus


class TaskRepository(MongoRepository):
    collection_name = TaskModel.collection_name

    @classmethod
    def _build_status_filter(cls, status_filter: str = None) -> dict:
        now = datetime.now(timezone.utc)

        if status_filter == TaskStatus.DEFERRED.value:
            return {
                "$and": [
                    {"deferredDetails": {"$ne": None}},
                    {"deferredDetails.deferredTill": {"$gt": now}},
                ]
            }

        elif status_filter == TaskStatus.DONE.value:
            return {
                "$or": [
                    {"deferredDetails": None},
                    {"deferredDetails.deferredTill": {"$lte": now}},
                ]
            }

        else:
            return {
                "$and": [
                    {"status": {"$ne": TaskStatus.DONE.value}},
                    {
                        "$or": [
                            {"deferredDetails": None},
                            {"deferredDetails.deferredTill": {"$lte": now}},
                        ]
                    },
                ]
            }

    @classmethod
    def list(
        cls,
        page: int,
        limit: int,
        sort_by: str,
        order: str,
        user_id: str = None,
        team_id: str = None,
        status_filter: str = None,
    ) -> List[TaskModel]:
        tasks_collection = cls.get_collection()
        logger = logging.getLogger(__name__)

        base_filter = cls._build_status_filter(status_filter)

        if team_id:
            logger.debug(f"TaskRepository.list: team_id={team_id}")
            team_assignments = TaskAssignmentRepository.get_by_assignee_id(team_id, "team")
            team_task_ids = [assignment.task_id for assignment in team_assignments]
            logger.debug(f"TaskRepository.list: team_task_ids={team_task_ids}")
            query_filter = {"$and": [base_filter, {"_id": {"$in": team_task_ids}}]}
            logger.debug(f"TaskRepository.list: query_filter={query_filter}")
        elif user_id:
            assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
            query_filter = {"$and": [base_filter, {"_id": {"$in": assigned_task_ids}}]}
        else:
            query_filter = base_filter

        if sort_by == SORT_FIELD_PRIORITY:
            sort_direction = 1 if order == SORT_ORDER_DESC else -1
            sort_criteria = [(sort_by, sort_direction)]
        elif sort_by == SORT_FIELD_ASSIGNEE:
            # Assignee sorting is no longer supported since assignee is in separate collection
            sort_direction = -1 if order == SORT_ORDER_DESC else 1
            sort_criteria = [("createdAt", sort_direction)]
        else:
            sort_direction = -1 if order == SORT_ORDER_DESC else 1
            sort_criteria = [(sort_by, sort_direction)]

        tasks_cursor = tasks_collection.find(query_filter).sort(sort_criteria).skip((page - 1) * limit).limit(limit)
        return [TaskModel(**task) for task in tasks_cursor]

    @classmethod
    def _get_assigned_task_ids_for_user(cls, user_id: str) -> List[ObjectId]:
        """Get task IDs where user is assigned (either directly or as team member)."""
        direct_assignments = TaskAssignmentRepository.get_by_assignee_id(user_id, "user")
        direct_task_ids = [assignment.task_id for assignment in direct_assignments]

        # Get teams where user is a member
        from todo.repositories.team_repository import UserTeamDetailsRepository, TeamRepository

        user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)
        team_ids = [str(team.team_id) for team in user_teams]

        # Get tasks assigned to those teams (only if user is POC)
        team_task_ids = []
        if team_ids:
            # Get teams where user is POC
            poc_teams = TeamRepository.get_collection().find(
                {"_id": {"$in": [ObjectId(team_id) for team_id in team_ids]}, "is_deleted": False, "poc_id": user_id}
            )
            poc_team_ids = [str(team["_id"]) for team in poc_teams]

            # Get team assignments for POC teams
            if poc_team_ids:
                team_assignments = TaskAssignmentRepository.get_collection().find(
                    {"assignee_id": {"$in": poc_team_ids}, "user_type": "team", "is_active": True}
                )
                team_task_ids = [ObjectId(assignment["task_id"]) for assignment in team_assignments]

        return direct_task_ids + team_task_ids

    @classmethod
    def count(cls, user_id: str = None, team_id: str = None, status_filter: str = None) -> int:
        tasks_collection = cls.get_collection()

        base_filter = cls._build_status_filter(status_filter)

        if team_id:
            team_assignments = TaskAssignmentRepository.get_by_assignee_id(team_id, "team")
            team_task_ids = [assignment.task_id for assignment in team_assignments]
            query_filter = {"$and": [base_filter, {"_id": {"$in": team_task_ids}}]}
        elif user_id:
            assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
            query_filter = {
                "$and": [base_filter, {"$or": [{"createdBy": user_id}, {"_id": {"$in": assigned_task_ids}}]}]
            }
        else:
            query_filter = base_filter
        return tasks_collection.count_documents(query_filter)

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

        # Check if user is the creator
        if user_id != task.get("createdBy"):
            # Check if user is assigned to this task
            assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
            if task_id not in assigned_task_ids:
                raise PermissionError(ApiErrors.UNAUTHORIZED_TITLE)

        # Deactivate assignee relationship for this task
        TaskAssignmentRepository.deactivate_by_task_id(str(task_id), user_id)

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
    def get_tasks_for_user(cls, user_id: str, page: int, limit: int, status_filter: str = None) -> List[TaskModel]:
        tasks_collection = cls.get_collection()
        assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)

        base_filter = cls._build_status_filter(status_filter)

        query = {"$and": [base_filter, {"_id": {"$in": assigned_task_ids}}]}
        tasks_cursor = tasks_collection.find(query).skip((page - 1) * limit).limit(limit)
        return [TaskModel(**task) for task in tasks_cursor]

    @classmethod
    def get_by_ids(cls, task_ids: List[str]) -> List[TaskModel]:
        """
        Get multiple tasks by their IDs in a single database query.
        Returns only the tasks that exist.
        """
        if not task_ids:
            return []
        tasks_collection = cls.get_collection()
        object_ids = [ObjectId(task_id) for task_id in task_ids]
        cursor = tasks_collection.find({"_id": {"$in": object_ids}})
        return [TaskModel(**doc) for doc in cursor]
