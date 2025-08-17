from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request

from todo.serializers.team_creation_invite_code_serializer import (
    GenerateTeamCreationInviteCodeSerializer,
    VerifyTeamCreationInviteCodeSerializer,
)
from todo.services.team_creation_invite_code_service import TeamCreationInviteCodeService
from todo.repositories.team_creation_invite_code_repository import TeamCreationInviteCodeRepository
from todo.dto.team_creation_invite_code_dto import GenerateTeamCreationInviteCodeDTO, VerifyTeamCreationInviteCodeDTO
from todo.dto.responses.generate_team_creation_invite_code_response import GenerateTeamCreationInviteCodeResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


AUTHORIZED_USER_IDS = [
    "687544d3814217e020e3d03a",  # Admin user_id
]


class GenerateTeamCreationInviteCodeView(APIView):
    def _check_authorization(self, user_id: str) -> bool:
        """Check if the user is authorized to access team creation invite code functionality."""
        return user_id in AUTHORIZED_USER_IDS

    @extend_schema(
        operation_id="generate_team_creation_invite_code",
        summary="Generate a new team creation invite code",
        description="Generate a new team creation invite code. This code can only be used once and is required for team creation. Only admins can generate these codes.",
        tags=["team-creation-invite-codes"],
        request=GenerateTeamCreationInviteCodeSerializer,
        examples=[
            OpenApiExample(
                "Generate with description",
                value={"description": "Code for marketing team creation"},
                description="Generate a team creation invite code with a description",
            ),
            OpenApiExample(
                "Generate without description",
                value={},
                description="Generate a team creation invite code without description",
            ),
        ],
        responses={
            201: OpenApiResponse(
                response=GenerateTeamCreationInviteCodeResponse,
                description="Team creation invite code generated successfully",
            ),
            400: OpenApiResponse(description="Bad request - validation error"),
            401: OpenApiResponse(description="Unauthorized - authentication required"),
            403: OpenApiResponse(description="Forbidden - user not authorized to generate invite codes"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """
        Generate a new team creation invite code.
        """
        if not self._check_authorization(request.user_id):
            return Response(
                data={"message": "You are not authorized to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GenerateTeamCreationInviteCodeSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        dto = GenerateTeamCreationInviteCodeDTO(**serializer.validated_data)
        created_by_user_id = request.user_id
        response: GenerateTeamCreationInviteCodeResponse = TeamCreationInviteCodeService.generate_code(
            dto, created_by_user_id
        )
        data = response.model_dump(mode="json")
        return Response(data=data, status=status.HTTP_201_CREATED)


class VerifyTeamCreationInviteCodeView(APIView):
    @extend_schema(
        operation_id="verify_team_creation_invite_code",
        summary="Verify a team creation invite code",
        description="Verify a team creation invite code. Returns success if the code is valid and unused.",
        tags=["team-creation-invite-codes"],
        request=VerifyTeamCreationInviteCodeSerializer,
        examples=[
            OpenApiExample(
                "Verify valid code", value={"code": "ABC123"}, description="Verify a valid team creation invite code"
            ),
        ],
        responses={
            200: OpenApiResponse(response=dict, description="Team creation invite code verified successfully."),
            400: OpenApiResponse(description="Bad request - invalid or already used code"),
            401: OpenApiResponse(description="Unauthorized - authentication required"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """
        Verify a team creation invite code.
        """
        serializer = VerifyTeamCreationInviteCodeSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        dto = VerifyTeamCreationInviteCodeDTO(**serializer.validated_data)
        code_data = TeamCreationInviteCodeRepository.is_code_valid(dto.code)

        if not code_data:
            return Response(
                data={"message": "Invalid or already used team creation invite code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(data={"message": "Team creation invite code verified successfully"}, status=status.HTTP_200_OK)
