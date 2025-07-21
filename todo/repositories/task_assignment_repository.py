from datetime import datetime, timezone
from typing import Optional, List
import uuid
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from todo.utils.retry_utils import retry
from django.db import transaction

from todo.models.task_assignment import TaskAssignmentModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.postgres.task_assignment import TaskAssignment as PostgresTaskAssignment
from todo.models.postgres.task import Task as PostgresTask


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
            task_assignment_data = collection.find_one({"task_id": task_id, "is_active": True})
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
                {"assignee_id": assignee_id, "user_type": user_type, "is_active": True}
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
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": user_id,
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
                        "updated_by": user_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )

            new_assignment = TaskAssignmentModel(
                _id=None,
                task_id=task_id,
                assignee_id=assignee_id,
                user_type=user_type,
                created_by=user_id,
                updated_by=None,
            )

            return cls.create_parallel(new_assignment)
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
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
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
                            "is_active": False,
                            "updated_by": user_id,
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
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": user_id,
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
                            "updated_by": user_id,
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
            return result.modified_count > 0
        except Exception:
            return False

    @classmethod
    def create_parallel(cls, task_assignment_model):
        task_assignments_collection = cls.get_collection()
        new_assignment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        doc = task_assignment_model.model_dump(by_alias=True)
        doc["_id"] = new_assignment_id

        def write_mongo():
            client = cls.get_client()
            with client.start_session() as session:
                with session.start_transaction():
                    insert_result = task_assignments_collection.insert_one(doc, session=session)
                    return insert_result.inserted_id

        def write_postgres():
            print(task_assignment_model)
            task_instance = PostgresTask.objects.get(id=task_assignment_model.task_id)
            # TODO: Use this later if we want to store it as a foreign key
            # user_instance = PostgresUser.objects.get(id=task_assignment_model.assignee_id)
            with transaction.atomic():
                PostgresTaskAssignment.objects.create(
                    id=new_assignment_id,
                    task=task_instance,
                    assignee_id=task_assignment_model.assignee_id,
                    user_type=task_assignment_model.user_type,
                    is_active=True,
                    created_at=now,
                    created_by=task_assignment_model.created_by,
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

        # Compensation logic
        if exceptions:
            if mongo_id and not postgres_done:
                task_assignments_collection.delete_one({"_id": new_assignment_id})
                print(f"[COMPENSATION] Rolled back Mongo for task assignment {new_assignment_id}")
            if postgres_done and not mongo_id:
                with transaction.atomic():
                    PostgresTaskAssignment.objects.filter(id=new_assignment_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for task assignment {new_assignment_id}")
            raise Exception(f"TaskAssignment creation failed: {exceptions}")

        task_assignment_model.id = mongo_id
        return task_assignment_model
