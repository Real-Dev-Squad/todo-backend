from todo.dto.team_dto import CreateTeamDTO, TeamDTO
from todo.dto.responses.create_team_response import CreateTeamResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.team_repository import TeamRepository, UserTeamDetailsRepository
from todo.constants.messages import AppMessages

DEFAULT_ROLE_ID = "1"


class TeamService:
    @classmethod
    def create_team(cls, dto: CreateTeamDTO, created_by_user_id: str) -> CreateTeamResponse:
        """
        Create a new team with members and POC.

        Args:
            dto: Team creation data including name, description, POC, and members
            created_by_user_id: ID of the user creating the team

        Returns:
            CreateTeamResponse with the created team details and success message

        Raises:
            ValueError: If team creation fails
        """
        try:
            # Member IDs and POC ID validation is handled at DTO level
            member_ids = dto.member_ids or []

            # Create team
            team = TeamModel(
                name=dto.name,
                description=dto.description,
                poc_id=PyObjectId(dto.poc_id) if dto.poc_id else None,
                created_by=PyObjectId(created_by_user_id),
                updated_by=PyObjectId(created_by_user_id),
            )

            created_team = TeamRepository.create(team)

            # Create user-team relationships
            user_teams = []

            # Add members to the team
            if member_ids:
                for user_id in member_ids:
                    user_team = UserTeamDetailsModel(
                        user_id=PyObjectId(user_id),
                        team_id=created_team.id,
                        role_id=DEFAULT_ROLE_ID,
                        created_by=PyObjectId(created_by_user_id),
                        updated_by=PyObjectId(created_by_user_id),
                    )
                    user_teams.append(user_team)

            # Add POC if provided and not already in member_ids
            if dto.poc_id and (not member_ids or dto.poc_id not in member_ids):
                poc_user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(dto.poc_id),
                    team_id=created_team.id,
                    role_id=DEFAULT_ROLE_ID,
                    created_by=PyObjectId(created_by_user_id),
                    updated_by=PyObjectId(created_by_user_id),
                )
                user_teams.append(poc_user_team)

            # Create all user-team relationships
            if user_teams:
                UserTeamDetailsRepository.create_many(user_teams)

            # Convert to DTO
            team_dto = TeamDTO(
                id=str(created_team.id),
                name=created_team.name,
                description=created_team.description,
                poc_id=str(created_team.poc_id) if created_team.poc_id else None,
                created_by=str(created_team.created_by),
                updated_by=str(created_team.updated_by),
                created_at=created_team.created_at,
                updated_at=created_team.updated_at,
            )

            return CreateTeamResponse(team=team_dto, message=AppMessages.TEAM_CREATED)

        except Exception as e:
            raise ValueError(str(e))
