from todo.dto.team_dto import CreateTeamDTO, TeamDTO
from todo.dto.update_team_dto import UpdateTeamDTO
from todo.dto.responses.create_team_response import CreateTeamResponse
from todo.dto.responses.get_user_teams_response import GetUserTeamsResponse
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.models.common.pyobjectid import PyObjectId
from todo.repositories.team_repository import TeamRepository, UserTeamDetailsRepository
from todo.constants.messages import AppMessages
from todo.utils.invite_code_utils import generate_invite_code
from typing import List

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

            # Generate invite code
            invite_code = generate_invite_code(dto.name)

            # Create team
            team = TeamModel(
                name=dto.name,
                description=dto.description if dto.description else None,
                poc_id=PyObjectId(dto.poc_id) if dto.poc_id else None,
                invite_code=invite_code,
                created_by=PyObjectId(created_by_user_id),
                updated_by=PyObjectId(created_by_user_id),
            )

            created_team = TeamRepository.create(team)

            # Create user-team relationships
            user_teams = []

            # Add members to the team
            for member_id in member_ids:
                user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(member_id),
                    team_id=created_team.id,
                    role_id=DEFAULT_ROLE_ID,
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
                    role_id=DEFAULT_ROLE_ID,
                    is_active=True,
                    created_by=PyObjectId(created_by_user_id),
                    updated_by=PyObjectId(created_by_user_id),
                )
                user_teams.append(user_team)

            # Always add the creator as a member if not already in member_ids or as POC
            if created_by_user_id not in member_ids and created_by_user_id != dto.poc_id:
                user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(created_by_user_id),
                    team_id=created_team.id,
                    role_id=DEFAULT_ROLE_ID,
                    is_active=True,
                    created_by=PyObjectId(created_by_user_id),
                    updated_by=PyObjectId(created_by_user_id),
                )
                user_teams.append(user_team)

            # Create all user-team relationships
            if user_teams:
                UserTeamDetailsRepository.create_many(user_teams)

            # Convert to DTO
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
        # 1. Find the team by invite code
        team = TeamRepository.get_by_invite_code(invite_code)
        if not team:
            raise ValueError("Invalid invite code or team does not exist.")

        # 2. Check if user is already a member
        from todo.repositories.team_repository import UserTeamDetailsRepository

        user_teams = UserTeamDetailsRepository.get_by_user_id(user_id)
        for user_team in user_teams:
            if str(user_team.team_id) == str(team.id) and user_team.is_active:
                raise ValueError("User is already a member of this team.")

        # 3. Add user to the team
        from todo.models.common.pyobjectid import PyObjectId
        from todo.models.team import UserTeamDetailsModel

        user_team = UserTeamDetailsModel(
            user_id=PyObjectId(user_id),
            team_id=team.id,
            role_id=DEFAULT_ROLE_ID,
            is_active=True,
            created_by=PyObjectId(user_id),
            updated_by=PyObjectId(user_id),
        )
        UserTeamDetailsRepository.create(user_team)

        # 4. Return team details
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
    def update_team(cls, team_id: str, dto: UpdateTeamDTO, updated_by_user_id: str) -> TeamDTO:
        """
        Update a team by its ID.

        Args:
            team_id: ID of the team to update
            dto: Team update data including name, description, and POC
            updated_by_user_id: ID of the user updating the team

        Returns:
            TeamDTO with the updated team details

        Raises:
            ValueError: If team update fails or team not found
        """
        try:
            # Check if team exists
            existing_team = TeamRepository.get_by_id(team_id)
            if not existing_team:
                raise ValueError(f"Team with id {team_id} not found")

            # Prepare update data
            update_data = {}
            if dto.name is not None:
                update_data["name"] = dto.name
            if dto.description is not None:
                update_data["description"] = dto.description
            if dto.poc_id is not None:
                update_data["poc_id"] = PyObjectId(dto.poc_id)

            # Update the team
            updated_team = TeamRepository.update(team_id, update_data, updated_by_user_id)
            if not updated_team:
                raise ValueError(f"Failed to update team with id {team_id}")

            # Handle member updates if provided
            if dto.member_ids is not None:
                from todo.repositories.team_repository import UserTeamDetailsRepository

                success = UserTeamDetailsRepository.update_team_members(team_id, dto.member_ids, updated_by_user_id)
                if not success:
                    raise ValueError(f"Failed to update team members for team with id {team_id}")

            # Convert to DTO
            return TeamDTO(
                id=str(updated_team.id),
                name=updated_team.name,
                description=updated_team.description,
                poc_id=str(updated_team.poc_id) if updated_team.poc_id else None,
                invite_code=updated_team.invite_code,
                created_by=str(updated_team.created_by),
                updated_by=str(updated_team.updated_by),
                created_at=updated_team.created_at,
                updated_at=updated_team.updated_at,
            )

        except Exception as e:
            raise ValueError(f"Failed to update team: {str(e)}")

    @classmethod
    def add_team_members(cls, team_id: str, member_ids: List[str], added_by_user_id: str) -> TeamDTO:
        """
        Add members to a team. Only existing team members can add new members.

        Args:
            team_id: ID of the team to add members to
            member_ids: List of user IDs to add to the team
            added_by_user_id: ID of the user adding the members

        Returns:
            TeamDTO with the updated team details

        Raises:
            ValueError: If user is not a team member, team not found, or operation fails
        """
        try:
            # Check if team exists
            team = TeamRepository.get_by_id(team_id)
            if not team:
                raise ValueError(f"Team with id {team_id} not found")

            # Check if the user adding members is already a team member
            from todo.repositories.team_repository import UserTeamDetailsRepository

            user_teams = UserTeamDetailsRepository.get_by_user_id(added_by_user_id)
            user_is_member = any(str(user_team.team_id) == team_id and user_team.is_active for user_team in user_teams)

            if not user_is_member:
                raise ValueError("You must be a member of the team to add other members")

            # Validate that all users exist
            from todo.repositories.user_repository import UserRepository

            for member_id in member_ids:
                user = UserRepository.get_by_id(member_id)
                if not user:
                    raise ValueError(f"User with id {member_id} not found")

            # Check if any users are already team members
            existing_members = UserTeamDetailsRepository.get_users_by_team_id(team_id)
            already_members = [member_id for member_id in member_ids if member_id in existing_members]

            if already_members:
                raise ValueError(f"Users {', '.join(already_members)} are already team members")

            # Add new members to the team
            from todo.models.team import UserTeamDetailsModel
            from todo.models.common.pyobjectid import PyObjectId

            new_user_teams = []
            for member_id in member_ids:
                user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(member_id),
                    team_id=team.id,
                    role_id=DEFAULT_ROLE_ID,
                    is_active=True,
                    created_by=PyObjectId(added_by_user_id),
                    updated_by=PyObjectId(added_by_user_id),
                )
                new_user_teams.append(user_team)

            if new_user_teams:
                UserTeamDetailsRepository.create_many(new_user_teams)

            # Return updated team details
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

        except Exception as e:
            raise ValueError(f"Failed to add team members: {str(e)}")

    class TeamOrUserNotFound(Exception):
        pass

    @classmethod
    def remove_member_from_team(cls, user_id: str, team_id: str):
        from todo.repositories.user_team_details_repository import UserTeamDetailsRepository
        success = UserTeamDetailsRepository.remove_member_from_team(user_id=user_id, team_id=team_id)
        if not success:
            raise cls.TeamOrUserNotFound()
        return True
