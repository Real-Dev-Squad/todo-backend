from django.urls import path
from todo.views.task import TaskListView, TaskDetailView
from todo.views.health import HealthView
from todo.views.user import UsersView
from todo.views.auth import (
    GoogleLoginView,
    GoogleCallbackView,
)
from todo.views.role import RoleListView, RoleDetailView
from todo.views.label import LabelListView
from todo.views.team import TeamListView
from todo.views.auth import (
    GoogleLogoutView,
)
from todo.views.watchlist import WatchlistListView

urlpatterns = [
    path("teams", TeamListView.as_view(), name="teams"),
    path("tasks", TaskListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskDetailView.as_view(), name="task_detail"),
    path("roles", RoleListView.as_view(), name="roles"),
    path("roles/<str:role_id>", RoleDetailView.as_view(), name="role_detail"),
    path("health", HealthView.as_view(), name="health"),
    path("labels", LabelListView.as_view(), name="labels"),
    path("watchlist/tasks", WatchlistListView.as_view(), name="watchlist"),
    path("auth/google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback/", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/google/logout/", GoogleLogoutView.as_view(), name="google_logout"),
    path("users", UsersView.as_view(), name="users"),
]
