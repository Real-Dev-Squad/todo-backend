from datetime import datetime, timezone
from typing import List
from bson import ObjectId
from pymongo import ReturnDocument
import logging
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from todo.utils.retry_utils import retry
from django.db import transaction

from todo.exceptions.task_exceptions import TaskNotFoundException
from todo.models.task import TaskModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.repositories.task_assignment_repository import TaskAssignmentRepository
from todo.constants.messages import ApiErrors, RepositoryErrors
from todo.constants.task import SORT_FIELD_PRIORITY, SORT_FIELD_ASSIGNEE, SORT_ORDER_DESC
from todo.models.postgres.task import Task as PostgresTask
import uuid


class TaskRepository(MongoRepository):
    collection_name = TaskModel.collection_name

    @classmethod
    def list(
        cls, page: int, limit: int, sort_by: str, order: str, user_id: str = None, team_id: str = None
    ) -> List[TaskModel]:
        tasks_collection = cls.get_collection()
        logger = logging.getLogger(__name__)

        if team_id:
            logger.debug(f"TaskRepository.list: team_id={team_id}")
            team_assignments = TaskAssignmentRepository.get_by_assignee_id(team_id, "team")
            team_task_ids = [assignment.task_id for assignment in team_assignments]
            logger.debug(f"TaskRepository.list: team_task_ids={team_task_ids}")
            query_filter = {"_id": {"$in": team_task_ids}}
            logger.debug(f"TaskRepository.list: query_filter={query_filter}")
        elif user_id:
            assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
            query_filter = {"_id": {"$in": assigned_task_ids}}
        else:
            query_filter = {}

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
        from todo.repositories.team_repository import UserTeamDetailsRepository

        user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)
        team_ids = [str(team.team_id) for team in user_teams]

        # Get tasks assigned to those teams
        team_task_ids = []
        for team_id in team_ids:
            team_assignments = TaskAssignmentRepository.get_by_assignee_id(team_id, "team")
            team_task_ids.extend([assignment.task_id for assignment in team_assignments])

        return direct_task_ids + team_task_ids

    @classmethod
    def count(cls, user_id: str = None, team_id: str = None) -> int:
        tasks_collection = cls.get_collection()
        if team_id:
            team_assignments = TaskAssignmentRepository.get_by_assignee_id(team_id, "team")
            team_task_ids = [assignment.task_id for assignment in team_assignments]
            query_filter = {"_id": {"$in": team_task_ids}}
        elif user_id:
            assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
            query_filter = {"$or": [{"createdBy": user_id}, {"_id": {"$in": assigned_task_ids}}]}
        else:
            query_filter = {}
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
        task_data = tasks_collection.find_one({"_id": task_id})
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
            obj_id = task_id
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
        assigned_task_ids = cls._get_assigned_task_ids_for_user(user_id)
        query = {"_id": {"$in": assigned_task_ids}}
        tasks_cursor = tasks_collection.find(query).skip((page - 1) * limit).limit(limit)
        print(tasks_cursor)
        return [TaskModel(**task) for task in tasks_cursor]

    @classmethod
    def create_parallel(cls, task: TaskModel) -> TaskModel:
        tasks_collection = cls.get_collection()
        new_task_id = str(uuid.uuid4())
        task.createdAt = datetime.now(timezone.utc)
        task.updatedAt = None
        task_dict = task.model_dump(mode="json", by_alias=True, exclude_none=True)
        task_dict["_id"] = new_task_id

        def write_mongo():
            client = cls.get_client()
            with client.start_session() as session:
                with session.start_transaction():
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
                    task_dict["displayId"] = task.displayId
                    insert_result = tasks_collection.insert_one(task_dict, session=session)
                    return insert_result.inserted_id

        def write_postgres():
            with transaction.atomic():
                deferred_at = task.deferredDetails.deferredAt if task.deferredDetails else None
                deferred_till = task.deferredDetails.deferredTill if task.deferredDetails else None
                deferred_by = task.deferredDetails.deferredBy if task.deferredDetails else None
                PostgresTask.objects.create(
                    id=new_task_id,
                    title=task.title,
                    description=task.description,
                    priority=task.priority,
                    status=task.status,
                    is_acknowledged=task.isAcknowledged,
                    labels=task.labels,
                    is_deleted=task.isDeleted,
                    deferred_at=deferred_at,
                    deferred_till=deferred_till,
                    deferred_by=deferred_by,
                    started_at=task.startedAt,
                    due_at=task.dueAt,
                    created_at=task.createdAt,
                    created_by=task.createdBy,
                )
                return "postgres_success"

        exceptions = []
        mongo_id = None
        postgres_done = False

        with ThreadPoolExecutor() as executor:
            future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
            future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
            wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

            for future in (future_mongo, future_postgres):
                try:
                    res = future.result()
                    if isinstance(res, str) and res == "postgres_success":
                        postgres_done = True
                    else:
                        mongo_id = res
                except Exception as exc:
                    exceptions.append(exc)
                    print(f"[ERROR] Write failed: {exc}")

        if exceptions:
            if mongo_id and not postgres_done:
                tasks_collection.delete_one({"_id": new_task_id})
                print(f"[COMPENSATION] Rolled back Mongo for task {new_task_id}")
            if postgres_done and not mongo_id:
                with transaction.atomic():
                    PostgresTask.objects.filter(id=new_task_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for task {new_task_id}")
            raise Exception(f"Task creation failed: {exceptions}")

        task.id = mongo_id
        return task
