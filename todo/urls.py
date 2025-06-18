from django.urls import path
from todo.views.task import TaskListView, TaskDetailView
from todo.views.health import HealthView
from todo.views.auth import (
    GoogleLoginView,
    GoogleCallbackView,
    GoogleRefreshView,
    GoogleLogoutView,
    GoogleAuthStatusView,
)

urlpatterns = [
    path("tasks", TaskListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskDetailView.as_view(), name="task_detail"),
    path("health", HealthView.as_view(), name="health"),
    path("auth/google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/google/status/", GoogleAuthStatusView.as_view(), name="google_status"),
    path("auth/google/refresh/", GoogleRefreshView.as_view(), name="google_refresh"),
    path("auth/google/logout/", GoogleLogoutView.as_view(), name="google_logout"),
]
