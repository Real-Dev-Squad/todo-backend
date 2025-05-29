from django.urls import path
from todo.views.task import TaskListView, TaskDetailView
from todo.views.health import HealthView


urlpatterns = [
    path("tasks", TaskListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskDetailView.as_view(), name="task_detail"),
    path("health", HealthView.as_view(), name="health"),
]
