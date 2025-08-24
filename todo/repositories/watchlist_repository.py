from datetime import datetime, timezone
from typing import List, Tuple
from typing import Optional

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.watchlist import WatchlistModel
from todo.dto.watchlist_dto import WatchlistDTO
from bson import ObjectId
from todo.services.enhanced_dual_write_service import EnhancedDualWriteService


def _convert_objectids_to_str(obj):
    """Recursively convert all ObjectId values in a dict/list to strings."""
    if isinstance(obj, dict):
        return {k: _convert_objectids_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_objectids_to_str(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj


class WatchlistRepository(MongoRepository):
    collection_name = WatchlistModel.collection_name

    @classmethod
    def get_by_user_and_task(cls, user_id: str, task_id: str) -> Optional[WatchlistModel]:
        doc = cls.get_collection().find_one({"userId": user_id, "taskId": task_id})
        if doc:
            # Convert ObjectId fields to strings for the model
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

        dual_write_service = EnhancedDualWriteService()
        watchlist_data = {
            "task_id": str(watchlist_model.taskId),
            "user_id": str(watchlist_model.userId),
            "is_active": watchlist_model.isActive,
            "created_by": str(watchlist_model.createdBy),
            "created_at": watchlist_model.createdAt,
            "updated_by": str(watchlist_model.updatedBy) if watchlist_model.updatedBy else None,
            "updated_at": watchlist_model.updatedAt,
        }

        dual_write_success = dual_write_service.create_document(
            collection_name="watchlist", data=watchlist_data, mongo_id=str(watchlist_model.id)
        )

        if not dual_write_success:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to sync watchlist {watchlist_model.id} to Postgres")

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
                                "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", {"$toObjectId": "$$taskIdStr"}]}}}],
                                "as": "task",
                            }
                        },
                        {"$unwind": "$task"},
                        {
                            "$lookup": {
                                "from": "users",
                                "let": {"createdById": "$task.createdBy"},
                                "pipeline": [
                                    {"$match": {"$expr": {"$eq": ["$_id", {"$toObjectId": "$$createdById"}]}}}
                                ],
                                "as": "created_by_user",
                            }
                        },
                        {
                            "$lookup": {
                                "from": "task_details",
                                "let": {"taskIdStr": "$taskId"},
                                "pipeline": [
                                    {
                                        "$match": {
                                            "$expr": {
                                                "$and": [
                                                    {"$eq": ["$task_id", {"$toObjectId": "$$taskIdStr"}]},
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
                                            "deferredDetails": "$task.deferredDetails",
                                            "createdBy": {
                                                "id": {"$toString": {"$arrayElemAt": ["$created_by_user._id", 0]}},
                                                "name": {"$arrayElemAt": ["$created_by_user.name", 0]},
                                                "addedOn": {"$arrayElemAt": ["$created_by_user.addedOn", 0]},
                                                "tasksAssignedCount": {
                                                    "$arrayElemAt": ["$created_by_user.tasksAssignedCount", 0]
                                                },
                                            },
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

        tasks = [_convert_objectids_to_str(doc) for doc in result.get("data", [])]

        # If assignee is null, try to fetch it separately
        for task in tasks:
            if not task.get("assignee"):
                task["assignee"] = cls._get_assignee_for_task(task.get("taskId"))

            # If createdBy is null or still an ID, try to fetch user details separately
            if not task.get("createdBy") or (
                isinstance(task.get("createdBy"), str) and ObjectId.is_valid(task.get("createdBy", ""))
            ):
                task["createdBy"] = cls._get_user_dto_for_id(task.get("createdBy"))

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
    def _get_user_dto_for_id(cls, user_id: str):
        """
        Fallback method to get user details for createdBy field.
        """
        if not user_id:
            return None

        try:
            from todo.repositories.user_repository import UserRepository

            # Get user details
            user = UserRepository.get_by_id(user_id)
            if user:
                return {
                    "id": str(user.id),
                    "name": user.name,
                    "addedOn": getattr(user, "addedOn", None),
                    "tasksAssignedCount": getattr(user, "tasksAssignedCount", None),
                }
        except Exception:
            # If any error occurs, return None
            pass

        return None

    @classmethod
    def update(cls, taskId: ObjectId, isActive: bool, userId: ObjectId) -> dict:
        watchlist_collection = cls.get_collection()

        # Get current watchlist entry first
        current_watchlist = cls.get_by_user_and_task(str(userId), str(taskId))
        if not current_watchlist:
            return None

        update_result = watchlist_collection.update_one(
            {"userId": str(userId), "taskId": str(taskId)},
            {
                "$set": {
                    "isActive": isActive,
                    "updatedAt": datetime.now(timezone.utc),
                    "updatedBy": userId,
                }
            },
        )

        if update_result.modified_count > 0:
            # Sync to PostgreSQL
            dual_write_service = EnhancedDualWriteService()
            watchlist_data = {
                "task_id": str(current_watchlist.taskId),
                "user_id": str(current_watchlist.userId),
                "is_active": isActive,
                "created_by": str(current_watchlist.createdBy),
                "created_at": current_watchlist.createdAt,
                "updated_by": str(userId),
                "updated_at": datetime.now(timezone.utc),
            }

            dual_write_success = dual_write_service.update_document(
                collection_name="watchlist", data=watchlist_data, mongo_id=str(current_watchlist.id)
            )

            if not dual_write_success:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to sync watchlist update {current_watchlist.id} to Postgres")

        if update_result.modified_count == 0:
            return None
        return update_result
