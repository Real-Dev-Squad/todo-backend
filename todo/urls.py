from django.urls import path
from todo.views.task import TaskListView, TaskDetailView
from todo.views.label import LabelListView
from todo.views.health import HealthView
from todo.views.user import UsersView
from todo.views.auth import (
    GoogleLoginView,
    GoogleCallbackView,
    LogoutView,
)

urlpatterns = [
    path("tasks", TaskListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskDetailView.as_view(), name="task_detail"),
    path("health", HealthView.as_view(), name="health"),
    path("labels", LabelListView.as_view(), name="labels"),
    path("auth/google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/logout/", LogoutView.as_view(), name="google_logout"),
    path("users", UsersView.as_view(), name="users"),
]
