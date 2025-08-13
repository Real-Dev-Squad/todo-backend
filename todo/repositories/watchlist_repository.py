from datetime import datetime, timezone
from typing import List, Tuple
from typing import Optional

from todo.repositories.common.mongo_repository import MongoRepository
from todo.models.watchlist import WatchlistModel
from todo.dto.watchlist_dto import WatchlistDTO
from bson import ObjectId


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
                                    {
                                        "$match": {
                                            "$expr": {"$eq": ["$_id", {"$toObjectId": "$$createdById"}]}
                                        }
                                    }
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
    def update(cls, taskId: ObjectId, isActive: bool, userId: ObjectId) -> dict:
        """
        Update the watchlist status of a task.
        """
        watchlist_collection = cls.get_collection()
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

        if update_result.modified_count == 0:
            return None
        return update_result
