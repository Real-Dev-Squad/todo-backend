from datetime import datetime, timezone
from typing import List, Tuple
from typing import Optional
import uuid
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from todo.utils.retry_utils import retry
from django.db import transaction

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.watchlist import WatchlistModel
from todo.dto.watchlist_dto import WatchlistDTO
from todo.models.postgres.watchlist import Watchlist as PostgresWatchlist
from todo.models.postgres.task import Task as PostgresTask
from todo.models.postgres.user import User as PostgresUser


class WatchlistRepository(MongoRepository):
    collection_name = WatchlistModel.collection_name

    @classmethod
    def get_by_user_and_task(cls, user_id: str, task_id: str) -> Optional[WatchlistModel]:
        doc = cls.get_collection().find_one({"userId": user_id, "taskId": task_id})
        if doc:
            if "updatedBy" in doc and doc["updatedBy"]:
                doc["updatedBy"] = str(doc["updatedBy"])
            return WatchlistModel(**doc)
        return None

    @classmethod
    def create(cls, watchlist_model: WatchlistModel) -> WatchlistModel:
        doc = watchlist_model.model_dump(by_alias=True)
        doc.pop("_id", None)
        insert_result = cls.get_collection().insert_one(doc)
        watchlist_model.id = str(insert_result.inserted_id)
        return watchlist_model

    @classmethod
    def get_watchlisted_tasks(cls, page, limit, user_id) -> Tuple[int, List[WatchlistDTO]]:
        """
        Get paginated list of watchlisted tasks with assignee details.
        The assignee represents who the task belongs to (who is responsible for completing the task).
        """
        watchlist_collection = cls.get_collection()

        query = {"userId": user_id, "isActive": True}

        zero_indexed_page = page - 1
        skip = zero_indexed_page * limit

        pipeline = [
            {"$match": query},
            {
                "$facet": {
                    "data": [
                        {
                            "$lookup": {
                                "from": "tasks",
                                "let": {"taskIdStr": "$taskId"},
                                "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", "$$taskIdStr"]}}}],
                                "as": "task",
                            }
                        },
                        {"$unwind": "$task"},
                        {
                            "$lookup": {
                                "from": "task_details",
                                "let": {"taskIdStr": "$taskId"},
                                "pipeline": [
                                    {
                                        "$match": {
                                            "$expr": {
                                                "$and": [
                                                    {"$eq": ["$task_id", "$$taskIdStr"]},
                                                    {"$eq": ["$is_active", True]},
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "as": "assignment",
                            }
                        },
                        {
                            "$lookup": {
                                "from": "users",
                                "let": {"assigneeId": {"$arrayElemAt": ["$assignment.assignee_id", 0]}},
                                "pipeline": [
                                    {
                                        "$match": {
                                            "$expr": {
                                                "$and": [
                                                    {"$eq": ["$_id", "$$assigneeId"]},
                                                    {"$eq": [{"$arrayElemAt": ["$assignment.user_type", 0]}, "user"]},
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "as": "assignee_user",
                            }
                        },
                        {
                            "$lookup": {
                                "from": "teams",
                                "let": {"assigneeId": {"$arrayElemAt": ["$assignment.assignee_id", 0]}},
                                "pipeline": [
                                    {
                                        "$match": {
                                            "$expr": {
                                                "$and": [
                                                    {"$eq": ["$_id", "$$assigneeId"]},
                                                    {"$eq": [{"$arrayElemAt": ["$assignment.user_type", 0]}, "team"]},
                                                ]
                                            }
                                        }
                                    }
                                ],
                                "as": "assignee_team",
                            }
                        },
                        {
                            "$replaceRoot": {
                                "newRoot": {
                                    "$mergeObjects": [
                                        "$task",
                                        {
                                            "watchlistId": {"$toString": "$_id"},
                                            "taskId": {"$toString": "$task._id"},
                                            "assignee": {
                                                "$cond": {
                                                    "if": {"$gt": [{"$size": "$assignee_user"}, 0]},
                                                    "then": {
                                                        "assignee_id": {
                                                            "$toString": {"$arrayElemAt": ["$assignee_user._id", 0]}
                                                        },
                                                        "assignee_name": {"$arrayElemAt": ["$assignee_user.name", 0]},
                                                        "user_type": "user",
                                                    },
                                                    "else": {
                                                        "$cond": {
                                                            "if": {"$gt": [{"$size": "$assignee_team"}, 0]},
                                                            "then": {
                                                                "assignee_id": {
                                                                    "$toString": {
                                                                        "$arrayElemAt": ["$assignee_team._id", 0]
                                                                    }
                                                                },
                                                                "assignee_name": {
                                                                    "$arrayElemAt": ["$assignee_team.name", 0]
                                                                },
                                                                "user_type": "team",
                                                            },
                                                            "else": None,
                                                        }
                                                    },
                                                }
                                            },
                                        },
                                    ]
                                }
                            }
                        },
                        {"$skip": skip},
                        {"$limit": limit},
                    ],
                    "total": [{"$count": "value"}],
                }
            },
            {"$addFields": {"total": {"$ifNull": [{"$arrayElemAt": ["$total.value", 0]}, 0]}}},
        ]

        aggregation_result = watchlist_collection.aggregate(pipeline)
        result = next(aggregation_result, {"total": 0, "data": []})
        count = result.get("total", 0)

        tasks = list(result.get("data", []))

        # If assignee is null, try to fetch it separately
        for task in tasks:
            if not task.get("assignee"):
                task["assignee"] = cls._get_assignee_for_task(task.get("taskId"))
            if "watchlistId" in task:
                task["id"] = task["watchlistId"]
                task["displayId"] = task["watchlistId"]

        tasks = [WatchlistDTO(**doc) for doc in tasks]

        return count, tasks

    @classmethod
    def _get_assignee_for_task(cls, task_id: str):
        """
        Fallback method to get assignee details for a task.
        """
        if not task_id:
            return None

        try:
            from todo.repositories.task_assignment_repository import TaskAssignmentRepository
            from todo.repositories.user_repository import UserRepository
            from todo.repositories.team_repository import TeamRepository

            # Get task assignment
            assignment = TaskAssignmentRepository.get_by_task_id(task_id)
            if not assignment:
                return None

            assignee_id = str(assignment.assignee_id)
            user_type = assignment.user_type

            if user_type == "user":
                # Get user details
                user = UserRepository.get_by_id(assignee_id)
                if user:
                    return {"assignee_id": assignee_id, "assignee_name": user.name, "user_type": "user"}
            elif user_type == "team":
                # Get team details
                team = TeamRepository.get_by_id(assignee_id)
                if team:
                    return {"assignee_id": assignee_id, "assignee_name": team.name, "user_type": "team"}

        except Exception:
            # If any error occurs, return None
            return None

        return None

    @classmethod
    def update(cls, taskId: str, isActive: bool, userId: str) -> dict:
        """
        Update the watchlist status of a task.
        """
        watchlist_collection = cls.get_collection()
        update_result = watchlist_collection.update_one(
            {"userId": userId, "taskId": taskId},
            {
                "$set": {
                    "isActive": isActive,
                    "updatedAt": datetime.now(timezone.utc),
                    "updatedBy": userId,
                }
            },
        )

        if update_result.modified_count == 0:
            return None
        return update_result

    @classmethod
    def create_parallel(cls, watchlist_model: WatchlistModel) -> WatchlistModel:
        print(watchlist_model)
        watchlists_collection = cls.get_collection()
        new_watchlist_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        watchlist_model.createdAt = now
        doc = watchlist_model.model_dump(by_alias=True)
        doc["_id"] = new_watchlist_id

        def write_mongo():
            client = cls.get_client()
            with client.start_session() as session:
                with session.start_transaction():
                    insert_result = watchlists_collection.insert_one(doc, session=session)
                    return insert_result.inserted_id

        def write_postgres():
            task_instance = PostgresTask.objects.get(id=watchlist_model.taskId)
            user_instance = PostgresUser.objects.get(id=watchlist_model.userId)
            print(user_instance)
            with transaction.atomic():
                PostgresWatchlist.objects.create(
                    id=new_watchlist_id,
                    user=user_instance,
                    task=task_instance,
                    is_active=True,
                    created_at=now,
                    created_by=watchlist_model.createdBy,
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
                watchlists_collection.delete_one({"_id": new_watchlist_id})
                print(f"[COMPENSATION] Rolled back Mongo for watchlist {new_watchlist_id}")
            if postgres_done and not mongo_id:
                with transaction.atomic():
                    PostgresWatchlist.objects.filter(id=new_watchlist_id).delete()
                print(f"[COMPENSATION] Rolled back Postgres for watchlist {new_watchlist_id}")
            raise Exception(f"Watchlist creation failed: {exceptions}")

        watchlist_model.id = mongo_id
        return watchlist_model
