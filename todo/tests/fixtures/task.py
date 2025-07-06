from todo.constants.task import TaskPriority
from todo.models.task import TaskModel
from todo.constants.task import TaskStatus
from todo.dto.task_dto import TaskDTO
from bson import ObjectId

tasks_db_data = [
    {
        "id": ObjectId("672f7c5b775ee9f4471ff1dd"),
        "displayId": "#1",
        "title": "Task 1",
        "description": "Test task 1",
        "priority": TaskPriority.HIGH.value,
        "status": TaskStatus.TODO.value,
        "assignee": "qMbT6M2GB65W7UHgJS4g",
        "isAcknowledged": True,
        "labels": [ObjectId("67588c1ac2195684a575840c"), ObjectId("67478036eac9d93db7f59c35")],
        "createdAt": "2024-11-08T10:14:35",
        "isDeleted": False,
        "updatedAt": "2024-11-08T15:14:35",
        "createdBy": "qMbT6M2GB65W7UHgJS4g",
        "updatedBy": "qMbT6M2GB65W7UHgJS4g",
    },
    {
        "id": ObjectId("674c726ca89aab38040cb964"),
        "displayId": "#2",
        "title": "Task 2",
        "description": "Test task 2",
        "priority": TaskPriority.MEDIUM.value,
        "status": TaskStatus.IN_PROGRESS.value,
        "assignee": "qMbT6M2GB65W7UHgJS4g",
        "isAcknowledged": False,
        "labels": [ObjectId("67588c1ac2195684a575840c"), ObjectId("67478036eac9d93db7f59c35")],
        "createdAt": "2024-11-08T10:14:35",
        "updatedAt": "2024-11-08T15:14:35",
        "createdBy": "qMbT6M2GB65W7UHgJS4g",
        "updatedBy": "qMbT6M2GB65W7UHgJS4g",
    },
]

tasks_models = [TaskModel(**data) for data in tasks_db_data]


task_dtos = [
    TaskDTO(
        id="672f7c5b775ee9f4471ff1dd",
        displayId="#1",
        title="created rest api",
        priority=1,
        status="TODO",
        assignee={"id": "qMbT6M2GB65W7UHgJS4g", "name": "SYSTEM"},
        isAcknowledged=False,
        labels=[{"id": "label-1", "name": "Beginner Friendly", "color": "#fa1e4e"}],
        isDeleted=False,
        startedAt="2024-11-09T15:14:35.724000",
        dueAt="2024-11-09T15:14:35.724000",
        createdAt="2024-11-09T15:14:35.724000",
        updatedAt="2024-10-18T15:55:14.802000Z",
        createdBy={"id": "xQ1CkCncM8Novk252oAj", "name": "SYSTEM"},
        updatedBy={"id": "Kn5N4Z3mdvpkv0HpqUCt", "name": "SYSTEM"},
    ),
    TaskDTO(
        id="674c726ca89aab38040cb964",
        displayId="#1",
        title="task 2",
        priority=1,
        status="TODO",
        assignee={"id": "qMbT6M2GB65W7UHgJS4g", "name": "SYSTEM"},
        isAcknowledged=True,
        labels=[{"id": "label-1", "name": "Beginner Friendly", "color": "#fa1e4e"}],
        isDeleted=False,
        startedAt="2024-11-09T15:14:35.724000",
        dueAt="2024-11-09T15:14:35.724000",
        createdAt="2024-11-09T15:14:35.724000",
        updatedAt="2024-10-18T15:55:14.802000Z",
        createdBy={"id": "xQ1CkCncM8Novk252oAj", "name": "SYSTEM"},
        updatedBy={"id": "Kn5N4Z3mdvpkv0HpqUCt", "name": "SYSTEM"},
    ),
]
