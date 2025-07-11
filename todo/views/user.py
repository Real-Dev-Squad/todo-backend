from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from todo.constants.messages import ApiErrors
from todo.middlewares.jwt_auth import get_current_user_info
from todo.services.user_service import UserService


class UsersView(APIView):
    def get(self, request: Request):
        profile = request.query_params.get("profile")
        if profile == "true":
            userData = UserService.get_user_by_id(request.user_id)
            if not userData:
                return Response(
                    {
                        "statusCode": 404,
                        "message": ApiErrors.USER_NOT_FOUND,
                        "data": None,
                    },
                    status=404,
                )
            userData = userData.model_dump(mode="json", exclude_none=True)
            userResponse = {
                "userId": userData["id"],
                "email": userData["email_id"],
                "name": userData.get("name"),
                "picture": userData.get("picture"),
            }
            return Response(
                {
                    "statusCode": 200,
                    "message": "Current user details fetched successfully",
                    "data": userResponse,
                },
                status=200,
            )
        return Response(
            {"statusCode": 404, "message": "Route does not exist.", "data": None},
            status=404,
        )
