from todo.dto.team_dto import CreateTeamDTO, TeamDTO
from todo.dto.responses.create_team_response import CreateTeamResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.team_repository import TeamRepository, UserTeamDetailsRepository
from todo.repositories.user_repository import UserRepository


class TeamService:
    @classmethod
    def create_team(cls, dto: CreateTeamDTO, created_by_user_id: str) -> CreateTeamResponse:
        """
        Create a new team with members and POC.
        """
        try:
            # Validate that all member IDs exist
            if dto.member_ids:
                for user_id in dto.member_ids:
                    user = UserRepository.get_by_id(user_id)
                    if not user:
                        raise ValueError(f"User with ID {user_id} not found")

            # Validate POC exists if provided
            if dto.poc_id:
                poc_user = UserRepository.get_by_id(dto.poc_id)
                if not poc_user:
                    raise ValueError(f"POC user with ID {dto.poc_id} not found")

            # Create team
            team = TeamModel(
                name=dto.name,
                description=dto.description,
                poc_id=PyObjectId(dto.poc_id) if dto.poc_id else None,
                created_by=PyObjectId(created_by_user_id),
                updated_by=PyObjectId(created_by_user_id)
            )

            created_team = TeamRepository.create(team)

            # Create user-team relationships
            user_teams = []
            
            # Add members to the team
            if dto.member_ids:
                for user_id in dto.member_ids:
                    user_team = UserTeamDetailsModel(
                        user_id=PyObjectId(user_id),
                        team_id=created_team.id,
                        role_id="1",
                        created_by=PyObjectId(created_by_user_id),
                        updated_by=PyObjectId(created_by_user_id)
                    )
                    user_teams.append(user_team)

            # Add creator if not already in member_ids
            if created_by_user_id not in dto.member_ids:
                creator_user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(created_by_user_id),
                    team_id=created_team.id,
                    role_id="1",
                    created_by=PyObjectId(created_by_user_id),
                    updated_by=PyObjectId(created_by_user_id)
                )
                user_teams.append(creator_user_team)

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

            return CreateTeamResponse(team=team_dto)

        except Exception as e:
            raise ValueError(str(e)) 