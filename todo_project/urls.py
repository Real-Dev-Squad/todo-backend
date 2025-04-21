from django.urls import path, include

urlpatterns = [
    path("v1/", include("todo.urls"), name="api"),
]
