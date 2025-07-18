from django.urls import path
from todo.views.task import TaskListView, TaskDetailView
from todo.views.health import HealthView
from todo.views.user import UsersView
from todo.views.auth import GoogleLoginView, GoogleCallbackView, LogoutView
from todo.views.role import RoleListView, RoleDetailView
from todo.views.label import LabelListView
from todo.views.team import TeamListView, TeamDetailView, JoinTeamByInviteCodeView, AddTeamMembersView
from todo.views.watchlist import WatchlistListView, WatchlistDetailView, WatchlistCheckView
from todo.views.task_assignment import TaskAssignmentView, TaskAssignmentDetailView
from todo.views.task import AssignTaskToUserView

urlpatterns = [
    path("teams", TeamListView.as_view(), name="teams"),
    path("teams/join-by-invite", JoinTeamByInviteCodeView.as_view(), name="join_team_by_invite"),
    path("teams/<str:team_id>", TeamDetailView.as_view(), name="team_detail"),
    path("teams/<str:team_id>/members", AddTeamMembersView.as_view(), name="add_team_members"),
    path("tasks", TaskListView.as_view(), name="tasks"),
    path("tasks/<str:task_id>", TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<str:task_id>/assign", AssignTaskToUserView.as_view(), name="assign_task_to_user"),
    path("task-assignments", TaskAssignmentView.as_view(), name="task_assignments"),
    path("task-assignments/<str:task_id>", TaskAssignmentDetailView.as_view(), name="task_assignment_detail"),
    path("roles", RoleListView.as_view(), name="roles"),
    path("roles/<str:role_id>", RoleDetailView.as_view(), name="role_detail"),
    path("health", HealthView.as_view(), name="health"),
    path("labels", LabelListView.as_view(), name="labels"),
    path("watchlist/tasks", WatchlistListView.as_view(), name="watchlist"),
    path("watchlist/tasks/check", WatchlistCheckView.as_view(), name="watchlist_check"),
    path("watchlist/tasks/<str:task_id>", WatchlistDetailView.as_view(), name="watchlist_task"),
    path("auth/google/login", GoogleLoginView.as_view(), name="google_login"),
    path("auth/google/callback", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/logout", LogoutView.as_view(), name="google_logout"),
    path("users", UsersView.as_view(), name="users"),
]
