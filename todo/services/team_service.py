from todo.dto.team_dto import CreateTeamDTO, TeamDTO
from todo.dto.responses.create_team_response import CreateTeamResponse
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.team_repository import TeamRepository, UserTeamDetailsRepository
from todo.repositories.role_repository import RoleRepository
from todo.models.role import RoleModel
from todo.constants.role import RoleScope
from todo.constants.messages import AppMessages
from todo.utils.invite_code_utils import generate_invite_code


class TeamService:
    @classmethod
    def _get_or_create_role(cls, role_name: str, role_scope: RoleScope = RoleScope.TEAM) -> str:
        """Get or create a role by name and return its ID"""
        collection = RoleRepository.get_collection()
        existing_role = collection.find_one({"name": role_name, "scope": role_scope.value})

        if existing_role:
            return str(existing_role["_id"])

        role_model = RoleModel(
            name=role_name,
            description=f"Team {role_name} role",
            scope=role_scope,
            is_active=True,
            created_by="system",
        )

        created_role = RoleRepository.create(role_model)
        return str(created_role.id)

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
            owner_role_id = cls._get_or_create_role("owner")
            member_role_id = cls._get_or_create_role("member")

            member_ids = dto.member_ids or []
            invite_code = generate_invite_code(dto.name)

            team = TeamModel(
                name=dto.name,
                description=dto.description if dto.description else None,
                poc_id=PyObjectId(dto.poc_id) if dto.poc_id else None,
                invite_code=invite_code,
                created_by=PyObjectId(created_by_user_id),
                updated_by=PyObjectId(created_by_user_id),
            )

            created_team = TeamRepository.create(team)
            user_teams = []

            # Add members to the team
            for member_id in member_ids:
                user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(member_id),
                    team_id=created_team.id,
                    role_id=member_role_id,
                    is_active=True,
                    created_by=PyObjectId(created_by_user_id),
                    updated_by=PyObjectId(created_by_user_id),
                )
                user_teams.append(user_team)

            # Add POC to the team if specified and not already in members
            if dto.poc_id and dto.poc_id not in member_ids:
                user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(dto.poc_id),
                    team_id=created_team.id,
                    role_id=member_role_id,
                    is_active=True,
                    created_by=PyObjectId(created_by_user_id),
                    updated_by=PyObjectId(created_by_user_id),
                )
                user_teams.append(user_team)

            user_team = UserTeamDetailsModel(
                user_id=PyObjectId(created_by_user_id),
                team_id=created_team.id,
                role_id=owner_role_id,
                is_active=True,
                created_by=PyObjectId(created_by_user_id),
                updated_by=PyObjectId(created_by_user_id),
            )
            user_teams.append(user_team)

            if user_teams:
                UserTeamDetailsRepository.create_many(user_teams)

            team_dto = TeamDTO(
                id=str(created_team.id),
                name=created_team.name,
                description=created_team.description,
                poc_id=str(created_team.poc_id) if created_team.poc_id else None,
                invite_code=created_team.invite_code,
                created_by=str(created_team.created_by),
                updated_by=str(created_team.updated_by),
                created_at=created_team.created_at,
                updated_at=created_team.updated_at,
            )

            return CreateTeamResponse(
                team=team_dto,
                message=AppMessages.TEAM_CREATED,
            )

        except Exception as e:
            raise ValueError(f"Failed to create team: {str(e)}")

    @classmethod
    def get_user_teams(cls, user_id: str) -> GetUserTeamsResponse:
        """
        Get all teams assigned to a specific user.

        Args:
            user_id: ID of the user to get teams for

        Returns:
            GetUserTeamsResponse with the list of teams and total count

        Raises:
            ValueError: If getting user teams fails
        """
        try:
            # Get user-team relationships
            user_team_details = UserTeamDetailsRepository.get_by_user_id(user_id)

            if not user_team_details:
                return GetUserTeamsResponse(teams=[], total=0)

            # Get team details for each relationship
            teams = []
            for user_team in user_team_details:
                team = TeamRepository.get_by_id(str(user_team.team_id))
                if team:
                    team_dto = TeamDTO(
                        id=str(team.id),
                        name=team.name,
                        description=team.description,
                        poc_id=str(team.poc_id) if team.poc_id else None,
                        invite_code=team.invite_code,
                        created_by=str(team.created_by),
                        updated_by=str(team.updated_by),
                        created_at=team.created_at,
                        updated_at=team.updated_at,
                    )
                    teams.append(team_dto)

            return GetUserTeamsResponse(teams=teams, total=len(teams))

        except Exception as e:
            raise ValueError(f"Failed to get user teams: {str(e)}")

    @classmethod
    def get_team_by_id(cls, team_id: str) -> TeamDTO:
        """
        Get a team by its ID.

        Args:
            team_id: ID of the team to retrieve

        Returns:
            TeamDTO with the team details

        Raises:
            ValueError: If the team is not found
        """
        team = TeamRepository.get_by_id(team_id)
        if not team:
            raise ValueError(f"Team with id {team_id} not found")
        return TeamDTO(
            id=str(team.id),
            name=team.name,
            description=team.description,
            poc_id=str(team.poc_id) if team.poc_id else None,
            invite_code=team.invite_code,
            created_by=str(team.created_by),
            updated_by=str(team.updated_by),
            created_at=team.created_at,
            updated_at=team.updated_at,
        )

    @classmethod
    def join_team_by_invite_code(cls, invite_code: str, user_id: str) -> TeamDTO:
        """
        Join a team using an invite code.

        Args:
            invite_code: The invite code for the team
            user_id: The user who wants to join

        Returns:
            TeamDTO with the team details

        Raises:
            ValueError: If invite code is invalid, team not found, or user already a member
        """
        # Find the team by invite code
        team = TeamRepository.get_by_invite_code(invite_code)
        if not team:
            raise ValueError("Invalid invite code or team does not exist.")

        user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)
        for user_team in user_teams:
            if str(user_team.team_id) == str(team.id) and user_team.is_active:
                raise ValueError("User is already a member of this team.")

        member_role_id = cls._get_or_create_role("member")

        user_team = UserTeamDetailsModel(
            user_id=PyObjectId(user_id),
            team_id=team.id,
            role_id=member_role_id,
            is_active=True,
            created_by=PyObjectId(user_id),
            updated_by=PyObjectId(user_id),
        )
        UserTeamDetailsRepository.create(user_team)

        return TeamDTO(
            id=str(team.id),
            name=team.name,
            description=team.description,
            poc_id=str(team.poc_id) if team.poc_id else None,
            invite_code=team.invite_code,
            created_by=str(team.created_by),
            updated_by=str(team.updated_by),
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
