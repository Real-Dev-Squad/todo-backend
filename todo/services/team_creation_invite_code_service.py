from todo.repositories.team_creation_invite_code_repository import TeamCreationInviteCodeRepository
from todo.repositories.audit_log_repository import AuditLogRepository
from todo.models.team_creation_invite_code import TeamCreationInviteCodeModel
from todo.models.audit_log import AuditLogModel
from todo.models.common.pyobjectid import PyObjectId
from todo.dto.team_creation_invite_code_dto import GenerateTeamCreationInviteCodeDTO
from todo.dto.responses.generate_team_creation_invite_code_response import GenerateTeamCreationInviteCodeResponse
from todo.dto.responses.get_team_creation_invite_codes_response import (
    GetTeamCreationInviteCodesResponse,
    TeamCreationInviteCodeListItemDTO,
)
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

    @classmethod
    def get_all_codes(cls, page: int = 1, limit: int = 10, base_url: str = "") -> GetTeamCreationInviteCodesResponse:
        """Get paginated team creation invite codes with user details."""
        try:
            codes_data, total_count = TeamCreationInviteCodeRepository.get_all_codes_with_user_details(page, limit)
            
            codes = []
            for code_data in codes_data:
                code_dto = TeamCreationInviteCodeListItemDTO(
                    id=code_data["id"],
                    code=code_data["code"],
                    description=code_data.get("description"),
                    created_by=code_data["created_by"],
                    created_at=code_data["created_at"],
                    used_at=code_data.get("used_at"),
                    used_by=code_data.get("used_by"),
                    is_used=code_data["is_used"]
                )
                codes.append(code_dto)  
            
            total_pages = (total_count + limit - 1)
            has_next = page < total_pages
            has_previous = page > 1
            
            previous_url = f"{base_url}?page={page-1}&limit={limit}" if has_previous else None
            next_url = f"{base_url}?page={page+1}&limit={limit}" if has_next else None
            
            return GetTeamCreationInviteCodesResponse(
                codes=codes,
                previous_url=previous_url,
                next_url=next_url,
                message="Team creation invite codes retrieved successfully"
            )
        except Exception as e:
            raise ValueError(f"Failed to get team creation invite codes: {str(e)}")
