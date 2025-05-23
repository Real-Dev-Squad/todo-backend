from django.urls import path
from todo.views.task import TaskView
from todo.views.health import HealthView


urlpatterns = [
    path("tasks", TaskView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskView.as_view(), name="task_detail"),
    path("health", HealthView.as_view(), name="health"),
]
