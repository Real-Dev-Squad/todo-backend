from todo.repositories.team_invite_code_repository import TeamInviteCodeRepository
from todo.models.team_invite_code import TeamInviteCodeModel
from todo.dto.team_invite_code_dto import GenerateTeamInviteCodeDTO
from todo.dto.responses.generate_team_invite_code_response import GenerateTeamInviteCodeResponse
from todo.utils.invite_code_utils import generate_invite_code


class TeamInviteCodeService:
    """Service for team invite code operations."""

    @classmethod
    def generate_code(cls, dto: GenerateTeamInviteCodeDTO, created_by: str) -> GenerateTeamInviteCodeResponse:
        """Generate a new team invite code."""
        code = generate_invite_code(dto.description)

        team_invite_code = TeamInviteCodeModel(code=code, description=dto.description, created_by=created_by)

        saved_code = TeamInviteCodeRepository.create(team_invite_code)

        return GenerateTeamInviteCodeResponse(
            code=saved_code.code,
            description=saved_code.description,
            message="Team creation invite code generated successfully",
        )

    @classmethod
    def consume_invite_code(cls, code: str, user_id: str) -> bool:
        """Consume a team invite code for the given user."""
        print(f"Consuming invite code {code} for user {user_id}")
        try:
            success = TeamInviteCodeRepository.consume_code(code, user_id)
            print(f"Result: {success}")
            return success
        except Exception:
            return False
