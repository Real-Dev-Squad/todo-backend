from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

from todo.middlewares.jwt_auth import get_current_user_info
from todo.constants.messages import ApiErrors
from todo.services.watchlist_service import WatchlistService
from todo.serializers.create_watchlist_serializer import CreateWatchlistSerializer
from todo.serializers.get_watchlist_tasks_serializer import GetWatchlistTaskQueryParamsSerializer
from todo.dto.responses.error_response import ApiErrorResponse
from todo.dto.watchlist_dto import CreateWatchlistDTO
from todo.dto.responses.create_watchlist_response import CreateWatchlistResponse


class WatchlistListView(APIView):
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

    def post(self, request: Request):
        """
        Add a task to the watchlist.
        """
        user = get_current_user_info(request)
        if not user:
            raise AuthenticationFailed(ApiErrors.AUTHENTICATION_FAILED)

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
