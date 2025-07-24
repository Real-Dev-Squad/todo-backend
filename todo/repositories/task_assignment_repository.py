from datetime import datetime, timezone
from typing import Optional, List
import uuid
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from todo.utils.retry_utils import retry
from django.db import transaction

from todo.models.task_assignment import TaskAssignmentModel
from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.postgres.task_assignment import TaskAssignment as PostgresTaskAssignment


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
            insert_result = task_assignments_collection.insert_one(doc)
            return insert_result.inserted_id

        def write_postgres():
            with transaction.atomic():
                if task_assignment_model.user_type == "user":
                    assignee_user_id = task_assignment_model.assignee_id
                    assignee_team_id = None
                elif task_assignment_model.user_type == "team":
                    assignee_team_id = task_assignment_model.assignee_id
                    assignee_user_id = None
                PostgresTaskAssignment.objects.create(
                    id=new_assignment_id,
                    task_id=task_assignment_model.task_id,
                    assignee_user_id=assignee_user_id,
                    assignee_team_id=assignee_team_id,
                    user_type=task_assignment_model.user_type,
                    is_active=True,
                    created_at=now,
                    created_by_id=task_assignment_model.created_by,
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

    @classmethod
    def update_assignment_parallel(
        cls, task_id: str, assignee_id: str, user_type: str, user_id: str
    ) -> Optional[TaskAssignmentModel]:
        """
        Update the assignment for a task using parallel execution on both databases.
        """
        task_assignments_collection = cls.get_collection()
        new_assignment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Create new assignment model
        new_assignment = TaskAssignmentModel(
            _id=None,
            task_id=task_id,
            assignee_id=assignee_id,
            user_type=user_type,
            created_by=user_id,
            updated_by=None,
        )

        new_assignment_dict = new_assignment.model_dump(by_alias=True)
        new_assignment_dict["_id"] = new_assignment_id
        new_assignment_dict["created_at"] = now

        def write_mongo():
            task_assignments_collection.update_many(
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": user_id,
                        "updated_at": now,
                    }
                },
            )

            insert_result = task_assignments_collection.insert_one(new_assignment_dict)
            return insert_result.inserted_id

        def write_postgres():
            with transaction.atomic():
                updated_count = PostgresTaskAssignment.objects.filter(task_id=task_id, is_active=True).update(
                    is_active=False, updated_by_id=user_id, updated_at=now
                )
                print(f"[DEBUG] Deactivated {updated_count} rows for task_id={task_id}")

                if user_type == "user":
                    assignee_user_id = assignee_id
                    assignee_team_id = None
                elif user_type == "team":
                    assignee_team_id = assignee_id
                    assignee_user_id = None
                else:
                    raise ValueError(f"Invalid user_type: {user_type}")

                PostgresTaskAssignment.objects.create(
                    id=new_assignment_id,
                    task_id=task_id,
                    assignee_user_id=assignee_user_id,
                    assignee_team_id=assignee_team_id,
                    user_type=user_type,
                    is_active=True,
                    created_at=now,
                    created_by_id=user_id,
                )
                return "postgres_success"

        exceptions = []
        mongo_id = None
        postgres_done = False

        try:
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
                        print(f"[ERROR] Update assignment write failed: {exc}")

            # Compensation logic
            if exceptions:
                if mongo_id and not postgres_done:
                    # Rollback MongoDB changes
                    task_assignments_collection.delete_one({"_id": new_assignment_id})
                    # Reactivate previous assignments (best effort)
                    task_assignments_collection.update_many(
                        {"task_id": task_id, "updated_at": now, "is_active": False},
                        {"$set": {"is_active": True, "$unset": {"updated_by": "", "updated_at": ""}}},
                    )
                    print(f"[COMPENSATION] Rolled back Mongo for task assignment update {new_assignment_id}")

                if postgres_done and not mongo_id:
                    # Rollback PostgreSQL changes
                    with transaction.atomic():
                        PostgresTaskAssignment.objects.filter(id=new_assignment_id).delete()
                        # Reactivate previous assignments (best effort)
                        PostgresTaskAssignment.objects.filter(task_id=task_id, updated_at=now, is_active=False).update(
                            is_active=True, updated_by_id=None, updated_at=None
                        )
                    print(f"[COMPENSATION] Rolled back Postgres for task assignment update {new_assignment_id}")

                raise Exception(f"TaskAssignment update failed: {exceptions}")

            new_assignment.id = mongo_id
            return new_assignment

        except Exception as e:
            print(f"[ERROR] TaskAssignment update failed: {e}")
            return None

    @classmethod
    def delete_assignment_parallel(cls, task_id: str, user_id: str) -> bool:
        """
        Soft delete a task assignment by setting is_active to False using parallel execution.
        """
        task_assignments_collection = cls.get_collection()
        now = datetime.now(timezone.utc)

        def write_mongo():
            result = task_assignments_collection.update_many(
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": user_id,
                        "updated_at": now,
                    }
                },
            )
            return result.modified_count

        def write_postgres():
            with transaction.atomic():
                assignments_to_update = list(
                    PostgresTaskAssignment.objects.filter(task_id=task_id, is_active=True).values_list("id", flat=True)
                )

                # Soft delete assignments
                updated_count = PostgresTaskAssignment.objects.filter(task_id=task_id, is_active=True).update(
                    is_active=False, updated_by_id=user_id, updated_at=now
                )

                return {"updated_count": updated_count, "assignment_ids": assignments_to_update}

        exceptions = []
        mongo_modified_count = 0
        postgres_result = None

        try:
            with ThreadPoolExecutor() as executor:
                future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
                future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
                wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

                for future in (future_mongo, future_postgres):
                    try:
                        res = future.result()
                        if isinstance(res, dict) and "updated_count" in res:
                            postgres_result = res
                        else:
                            mongo_modified_count = res
                    except Exception as exc:
                        exceptions.append(exc)
                        print(f"[ERROR] Delete assignment write failed: {exc}")

            # Check if both operations were successful
            postgres_modified_count = postgres_result["updated_count"] if postgres_result else 0

            # Compensation logic
            if exceptions:
                if mongo_modified_count > 0 and postgres_result is None:
                    # Rollback MongoDB changes - reactivate the assignments
                    task_assignments_collection.update_many(
                        {"task_id": task_id, "is_active": False, "updated_at": now, "updated_by": user_id},
                        {"$set": {"is_active": True}, "$unset": {"updated_by": "", "updated_at": ""}},
                    )
                    print(f"[COMPENSATION] Rolled back Mongo soft delete for task {task_id}")

                if postgres_result and mongo_modified_count == 0:
                    # Rollback PostgreSQL changes - reactivate the assignments
                    with transaction.atomic():
                        PostgresTaskAssignment.objects.filter(id__in=postgres_result["assignment_ids"]).update(
                            is_active=True, updated_by_id=None, updated_at=None
                        )
                    print(f"[COMPENSATION] Rolled back Postgres soft delete for task {task_id}")

                raise Exception(f"TaskAssignment delete failed: {exceptions}")

            # Success if both databases were updated (or both had no records to update)
            success = (mongo_modified_count > 0 and postgres_modified_count > 0) or (
                mongo_modified_count == 0 and postgres_modified_count == 0
            )

            if success:
                print(f"[SUCCESS] Soft deleted {mongo_modified_count} assignment(s) for task {task_id}")

            return success

        except Exception as e:
            print(f"[ERROR] TaskAssignment delete failed: {e}")
            return False

    @classmethod
    def update_executor_parallel(cls, task_id: str, executor_id: str, user_id: str) -> bool:
        """
        Update the executor_id for the active assignment of the given task_id using parallel execution.
        """
        task_assignments_collection = cls.get_collection()
        now = datetime.now(timezone.utc)

        def write_mongo():
            result = task_assignments_collection.update_one(
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "assignee_id": executor_id,
                        "user_type": "user",
                        "updated_by": user_id,
                        "updated_at": now,
                    }
                },
            )
            return {"modified_count": result.modified_count, "matched_count": result.matched_count}

        def write_postgres():
            with transaction.atomic():
                try:
                    current_assignment = PostgresTaskAssignment.objects.get(task_id=task_id, is_active=True)
                    old_assignee_user_id = current_assignment.assignee_user_id
                    old_assignee_team_id = current_assignment.assignee_team_id
                    old_user_type = current_assignment.user_type

                    updated_count = PostgresTaskAssignment.objects.filter(task_id=task_id, is_active=True).update(
                        assignee_user_id=executor_id,
                        assignee_team_id=None,
                        user_type="user",
                        updated_by_id=user_id,
                        updated_at=now,
                    )

                    return {
                        "updated_count": updated_count,
                        "old_assignee_user_id": old_assignee_user_id,
                        "old_assignee_team_id": old_assignee_team_id,
                        "old_user_type": old_user_type,
                        "assignment_id": current_assignment.id,
                    }
                except PostgresTaskAssignment.DoesNotExist:
                    return {"updated_count": 0}

        exceptions = []
        mongo_result = None
        postgres_result = None

        try:
            with ThreadPoolExecutor() as executor:
                future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
                future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
                wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

                for future in (future_mongo, future_postgres):
                    try:
                        res = future.result()
                        if "updated_count" in res and "assignment_id" in res:
                            postgres_result = res
                        else:
                            mongo_result = res
                    except Exception as exc:
                        exceptions.append(exc)
                        print(f"[ERROR] Update executor write failed: {exc}")

            # Compensation logic
            if exceptions:
                if mongo_result and mongo_result["modified_count"] > 0 and postgres_result is None:
                    print(f"[COMPENSATION] MongoDB updated but Postgres failed for task {task_id}")

                if postgres_result and postgres_result["updated_count"] > 0 and mongo_result is None:
                    with transaction.atomic():
                        PostgresTaskAssignment.objects.filter(id=postgres_result["assignment_id"]).update(
                            assignee_user_id=postgres_result["old_assignee_user_id"],
                            assignee_team_id=postgres_result["old_assignee_team_id"],
                            user_type=postgres_result["old_user_type"],
                            updated_by_id=None,
                            updated_at=None,
                        )
                    print(f"[COMPENSATION] Rolled back Postgres executor update for task {task_id}")

                raise Exception(f"TaskAssignment executor update failed: {exceptions}")

            # Success if both databases were updated consistently
            mongo_modified = mongo_result["modified_count"] if mongo_result else 0
            postgres_modified = postgres_result["updated_count"] if postgres_result else 0

            success = (mongo_modified > 0 and postgres_modified > 0) or (mongo_modified == 0 and postgres_modified == 0)

            if success and mongo_modified > 0:
                print(f"[SUCCESS] Updated executor to {executor_id} for task {task_id}")

            return success

        except Exception as e:
            print(f"[ERROR] TaskAssignment executor update failed: {e}")
            return False

    @classmethod
    def deactivate_by_task_id_parallel(cls, task_id: str, user_id: str) -> bool:
        """
        Deactivate all assignments for a specific task by setting is_active to False using parallel execution.
        """
        task_assignments_collection = cls.get_collection()
        now = datetime.now(timezone.utc)

        def write_mongo():
            result = task_assignments_collection.update_many(
                {"task_id": task_id, "is_active": True},
                {
                    "$set": {
                        "is_active": False,
                        "updated_by": user_id,
                        "updated_at": now,
                    }
                },
            )
            return result.modified_count

        def write_postgres():
            with transaction.atomic():
                # Get assignments that will be updated for potential rollback
                assignments_to_update = list(
                    PostgresTaskAssignment.objects.filter(task_id=task_id, is_active=True).values_list("id", flat=True)
                )

                # Deactivate all assignments for the task
                updated_count = PostgresTaskAssignment.objects.filter(task_id=task_id, is_active=True).update(
                    is_active=False, updated_by_id=user_id, updated_at=now
                )

                return {"updated_count": updated_count, "assignment_ids": assignments_to_update}

        exceptions = []
        mongo_modified_count = 0
        postgres_result = None

        try:
            with ThreadPoolExecutor() as executor:
                future_mongo = executor.submit(lambda: retry(write_mongo, max_attempts=3))
                future_postgres = executor.submit(lambda: retry(write_postgres, max_attempts=3))
                wait([future_mongo, future_postgres], return_when=ALL_COMPLETED)

                for future in (future_mongo, future_postgres):
                    try:
                        res = future.result()
                        if isinstance(res, dict) and "updated_count" in res:
                            postgres_result = res
                        else:
                            mongo_modified_count = res
                    except Exception as exc:
                        exceptions.append(exc)
                        print(f"[ERROR] Deactivate by task_id write failed: {exc}")

            # Check if both operations were successful
            postgres_modified_count = postgres_result["updated_count"] if postgres_result else 0

            # Compensation logic
            if exceptions:
                if mongo_modified_count > 0 and postgres_result is None:
                    # Rollback MongoDB changes - reactivate the assignments
                    task_assignments_collection.update_many(
                        {"task_id": task_id, "is_active": False, "updated_at": now, "updated_by": user_id},
                        {"$set": {"is_active": True}, "$unset": {"updated_by": "", "updated_at": ""}},
                    )
                    print(f"[COMPENSATION] Rolled back Mongo deactivation for task {task_id}")

                if postgres_result and mongo_modified_count == 0:
                    # Rollback PostgreSQL changes - reactivate the assignments
                    with transaction.atomic():
                        PostgresTaskAssignment.objects.filter(id__in=postgres_result["assignment_ids"]).update(
                            is_active=True, updated_by_id=None, updated_at=None
                        )
                    print(f"[COMPENSATION] Rolled back Postgres deactivation for task {task_id}")

                raise Exception(f"TaskAssignment deactivation failed: {exceptions}")

            # Success if both databases were updated consistently
            success = (mongo_modified_count > 0 and postgres_modified_count > 0) or (
                mongo_modified_count == 0 and postgres_modified_count == 0
            )

            if success and mongo_modified_count > 0:
                print(f"[SUCCESS] Deactivated {mongo_modified_count} assignment(s) for task {task_id}")

            return success

        except Exception as e:
            print(f"[ERROR] TaskAssignment deactivation failed: {e}")
            return False
