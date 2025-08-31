from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId
from todo.middlewares.jwt_auth import get_current_user_info
from todo.constants.messages import ApiErrors
from todo.serializers.update_watchlist_serializer import UpdateWatchlistSerializer
from todo.services.watchlist_service import WatchlistService
from todo.serializers.create_watchlist_serializer import CreateWatchlistSerializer
from todo.serializers.get_watchlist_tasks_serializer import GetWatchlistTaskQueryParamsSerializer
from todo.dto.responses.error_response import ApiErrorResponse
from todo.dto.watchlist_dto import CreateWatchlistDTO
from todo.dto.responses.create_watchlist_response import CreateWatchlistResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from todo.dto.responses.get_watchlist_task_response import GetWatchlistTasksResponse
from todo.repositories.watchlist_repository import WatchlistRepository


class WatchlistListView(APIView):
    @extend_schema(
        operation_id="get_watchlist_tasks",
        summary="Get paginated list of watchlisted tasks",
        description="Retrieve a paginated list of tasks that are added to the authenticated user's watchlist. Each task includes assignee details showing who the task belongs to (who is responsible for completing the task).",
        tags=["watchlist"],
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of tasks per page (default: 10, max: 100)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=GetWatchlistTasksResponse,
                description="Paginated list of watchlisted tasks with assignee details (task ownership) returned successfully",
            ),
            400: OpenApiResponse(response=ApiErrorResponse, description="Bad request - validation error"),
            500: OpenApiResponse(response=ApiErrorResponse, description="Internal server error"),
        },
    )
    def get(self, request: Request):
        """
        Retrieve a paginated list of tasks that are added to watchlist.
        """
        query = GetWatchlistTaskQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        user = get_current_user_info(request)

        response = WatchlistService.get_watchlisted_tasks(
            page=query.validated_data["page"],
            limit=query.validated_data["limit"],
            user_id=user["user_id"],
        )
        return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="add_task_to_watchlist",
        summary="Add a task to the watchlist",
        description="Add a task to the authenticated user's watchlist.",
        tags=["watchlist"],
        request=CreateWatchlistSerializer,
        responses={
            201: OpenApiResponse(response=CreateWatchlistResponse, description="Task added to watchlist successfully"),
            400: OpenApiResponse(
                response=ApiErrorResponse, description="Bad request - validation error or already in watchlist"
            ),
            500: OpenApiResponse(response=ApiErrorResponse, description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """
        Add a task to the watchlist.
        """
        user = get_current_user_info(request)

        serializer = CreateWatchlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dto = CreateWatchlistDTO(**serializer.validated_data, userId=user["user_id"], createdBy=user["user_id"])
            response: CreateWatchlistResponse = WatchlistService.add_task(dto)
            return Response(data=response.model_dump(mode="json"), status=status.HTTP_201_CREATED)

        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                error_response = e.args[0]
                return Response(data=error_response.model_dump(mode="json"), status=error_response.statusCode)

            fallback_response = ApiErrorResponse(
                statusCode=500,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[{"detail": ApiErrors.INTERNAL_SERVER_ERROR}],
            )
            return Response(
                data=fallback_response.model_dump(mode="json"), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WatchlistDetailView(APIView):
    @extend_schema(
        operation_id="update_watchlist_task",
        summary="Update watchlist status of a task",
        description="Update the isActive status of a task in the authenticated user's watchlist. This allows users to activate or deactivate watching a specific task.",
        tags=["watchlist"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="Unique identifier of the task to update in the watchlist",
                required=True,
            ),
        ],
        request=UpdateWatchlistSerializer,
        responses={
            200: OpenApiResponse(description="Watchlist task status updated successfully"),
            400: OpenApiResponse(response=ApiErrorResponse, description="Bad request - validation error"),
            404: OpenApiResponse(response=ApiErrorResponse, description="Task not found in watchlist"),
            500: OpenApiResponse(response=ApiErrorResponse, description="Internal server error"),
        },
    )
    def patch(self, request: Request, task_id: str):
        """
        Update the watchlist status of a task.
        """
        user = get_current_user_info(request)
        task_id = ObjectId(task_id)
        serializer = UpdateWatchlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        WatchlistService.update_task(task_id, serializer.validated_data, ObjectId(user["user_id"]))
        return Response(status=status.HTTP_200_OK)


class WatchlistCheckView(APIView):
    @extend_schema(
        operation_id="check_task_in_watchlist",
        summary="Check if a task is in the user's watchlist",
        description="Returns the watchlist status for the given task_id: true if actively watched, false if in watchlist but inactive, or null if not in watchlist.",
        tags=["watchlist"],
        parameters=[
            OpenApiParameter(
                name="task_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Task ID to check",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(response=None, description="Returns { 'in_watchlist': true/false/null }"),
            400: OpenApiResponse(response=ApiErrorResponse, description="Bad request - validation error"),
            401: OpenApiResponse(response=ApiErrorResponse, description="Unauthorized"),
        },
    )
    def get(self, request: Request):
        user = get_current_user_info(request)
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response({"message": "task_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not ObjectId.is_valid(task_id):
            return Response({"message": "Invalid task_id"}, status=status.HTTP_400_BAD_REQUEST)
        in_watchlist = None
        watchlist_entry = WatchlistRepository.get_by_user_and_task(user["user_id"], task_id)
        if watchlist_entry:
            in_watchlist = watchlist_entry.isActive
        return Response({"in_watchlist": in_watchlist}, status=status.HTTP_200_OK)
