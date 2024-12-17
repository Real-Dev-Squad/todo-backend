from django.urls import path
from todo.views.health import HealthView


urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
]
