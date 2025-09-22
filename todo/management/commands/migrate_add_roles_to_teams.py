from django.core.management.base import BaseCommand
from todo.repositories.user_role_repository import UserRoleRepository
from todo.repositories.team_repository import TeamRepository, UserTeamDetailsRepository
from todo.constants.role import RoleScope, RoleName


class Command(BaseCommand):
    help = "Backfill user_roles so roles are present for every team member and fix incorrect assigned roles"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("\n--- Starting Team Roles Fix Script ---"))
        teams_data = TeamRepository.get_collection().find({})
        roles_scope = RoleScope.TEAM.value

        roles_ensured = 0
        roles_deactivated = 0
        for team in teams_data:
            team_id = str(team["_id"])
            team_owner = team["created_by"]
            team_members = list(UserTeamDetailsRepository.get_by_team_id(team_id))
            for member in team_members:
                member_id = str(member.user_id)
                if member_id == team_owner:
                    for role in RoleName:
                        if role.value != RoleName.MODERATOR.value:
                            result = UserRoleRepository.assign_role(member_id, role.value, roles_scope, team_id)
                            roles_ensured += 1
                else:
                    user_roles = UserRoleRepository.get_user_roles(member_id, roles_scope, team_id)
                    has_member_role = False
                    for role in user_roles:
                        if role.role_name == RoleName.MEMBER.value:
                            has_member_role = True
                        else:
                            result = UserRoleRepository.remove_role_by_id(member_id, str(role.id), roles_scope, team_id)
                            if result:
                                roles_deactivated += 1
                    if not has_member_role:
                        UserRoleRepository.assign_role(member_id, RoleName.MEMBER.value, roles_scope, team_id)
                        roles_ensured += 1

        self.stdout.write(self.style.SUCCESS(f"Roles Ensured (Created or Already Existed): {roles_ensured}"))
        self.stdout.write(self.style.SUCCESS(f"Incorrect Roles Removed: {roles_deactivated}"))
