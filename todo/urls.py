from django.urls import path
from todo.views.task import TaskListView, TaskDetailView
from todo.views.label import LabelListView
from todo.views.health import HealthView
from todo.views.auth import (
    GoogleLoginView,
    GoogleCallbackView,
    GoogleRefreshView,
    GoogleLogoutView,
)

urlpatterns = [
    path("tasks", TaskListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskDetailView.as_view(), name="task_detail"),
    path("health", HealthView.as_view(), name="health"),
    path("labels", LabelListView.as_view(), name="labels"),
    path("auth/google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/google/refresh/", GoogleRefreshView.as_view(), name="google_refresh"),
    path("auth/google/logout/", GoogleLogoutView.as_view(), name="google_logout"),
]
