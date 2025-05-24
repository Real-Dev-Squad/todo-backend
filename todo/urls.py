from django.urls import path
from todo.views.task import TaskView
from todo.views.health import HealthView


urlpatterns = [
    path("tasks", TaskView.as_view(), name="tasks"),
    path("tasks/<str:task_id>/labels", TaskView.as_view({"post": "post_label"}), name="task_labels"),
    path("health", HealthView.as_view(), name="health"),
]
