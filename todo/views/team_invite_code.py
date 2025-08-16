from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request

from todo.serializers.team_invite_code_serializer import (
    GenerateTeamInviteCodeSerializer,
    VerifyTeamInviteCodeSerializer,
)
from todo.services.team_invite_code_service import TeamInviteCodeService
from todo.repositories.team_invite_code_repository import TeamInviteCodeRepository
from todo.dto.team_invite_code_dto import GenerateTeamInviteCodeDTO, VerifyTeamInviteCodeDTO
from todo.dto.responses.generate_team_invite_code_response import GenerateTeamInviteCodeResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class GenerateTeamInviteCodeView(APIView):
    @extend_schema(
        operation_id="generate_team_invite_code",
        summary="Generate a new team invite code",
        description="Generate a new team creation invite code. This code can only be used once and is required for team creation. Only admins can generate these codes.",
        tags=["team-invite-codes"],
        request=GenerateTeamInviteCodeSerializer,
        examples=[
            OpenApiExample(
                "Generate with description",
                value={"description": "Code for marketing team creation"},
                description="Generate a team invite code with a description",
            ),
            OpenApiExample(
                "Generate without description", value={}, description="Generate a team invite code without description"
            ),
        ],
        responses={
            201: OpenApiResponse(
                response=GenerateTeamInviteCodeResponse, description="Team invite code generated successfully"
            ),
            400: OpenApiResponse(description="Bad request - validation error"),
            401: OpenApiResponse(description="Unauthorized - authentication required"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """
        Generate a new team invite code.
        """
        serializer = GenerateTeamInviteCodeSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        dto = GenerateTeamInviteCodeDTO(**serializer.validated_data)
        created_by_user_id = request.user_id
        response: GenerateTeamInviteCodeResponse = TeamInviteCodeService.generate_code(dto, created_by_user_id)
        data = response.model_dump(mode="json")
        return Response(data=data, status=status.HTTP_201_CREATED)


class VerifyTeamInviteCodeView(APIView):
    @extend_schema(
        operation_id="verify_team_invite_code",
        summary="Verify a team invite code",
        description="Verify a team creation invite code. Returns success if the code is valid and unused.",
        tags=["team-invite-codes"],
        request=VerifyTeamInviteCodeSerializer,
        examples=[
            OpenApiExample(
                "Verify valid code", value={"code": "ABC123"}, description="Verify a valid team invite code"
            ),
        ],
        responses={
            200: OpenApiResponse(response=dict, description="Team invite code verified successfully."),
            400: OpenApiResponse(description="Bad request - invalid or already used code"),
            401: OpenApiResponse(description="Unauthorized - authentication required"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def post(self, request: Request):
        """
        Verify a team invite code.
        """
        serializer = VerifyTeamInviteCodeSerializer(data=request.data)

        if not serializer.is_valid():
            return self._handle_validation_errors(serializer.errors)

        dto = VerifyTeamInviteCodeDTO(**serializer.validated_data)
        code_data = TeamInviteCodeRepository.is_code_valid(dto.code)

        if not code_data:
            return Response(
                data={"message": "Invalid or already used team invite code"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(data={"message": "Team invite code verified successfully"}, status=status.HTTP_200_OK)
