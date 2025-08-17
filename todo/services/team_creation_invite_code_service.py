from todo.repositories.team_creation_invite_code_repository import TeamCreationInviteCodeRepository
from todo.repositories.audit_log_repository import AuditLogRepository
from todo.models.team_creation_invite_code import TeamCreationInviteCodeModel
from todo.models.audit_log import AuditLogModel
from todo.models.common.pyobjectid import PyObjectId
from todo.dto.team_creation_invite_code_dto import GenerateTeamCreationInviteCodeDTO
from todo.dto.responses.generate_team_creation_invite_code_response import GenerateTeamCreationInviteCodeResponse
from todo.utils.invite_code_utils import generate_invite_code


class TeamCreationInviteCodeService:
    """Service for team creation invite code operations."""

    @classmethod
    def generate_code(
        cls, dto: GenerateTeamCreationInviteCodeDTO, created_by: str
    ) -> GenerateTeamCreationInviteCodeResponse:
        """Generate a new team creation invite code."""
        code = generate_invite_code(dto.description)

        team_invite_code = TeamCreationInviteCodeModel(code=code, description=dto.description, created_by=created_by)

        saved_code = TeamCreationInviteCodeRepository.create(team_invite_code)

        AuditLogRepository.create(
            AuditLogModel(
                action="team_creation_invite_code_generated",
                performed_by=PyObjectId(created_by),
            )
        )

        return GenerateTeamCreationInviteCodeResponse(
            code=saved_code.code,
            description=saved_code.description,
            message="Team creation invite code generated successfully",
        )
