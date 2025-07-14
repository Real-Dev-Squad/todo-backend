from django.core.management.base import BaseCommand
from bson import ObjectId
from todo.models.team import TeamModel, UserTeamDetailsModel
from todo.repositories.team_repository import TeamRepository, UserTeamDetailsRepository
from todo.models.common.pyobjectid import PyObjectId

class Command(BaseCommand):
    help = "Backfill user_team_details so every team has its creator as an active member."

    def handle(self, *args, **options):
        teams = TeamRepository.get_collection().find({"is_deleted": False})
        updated = 0
        for team in teams:
            team_id = team["_id"]
            creator_id = team["created_by"]
            # Check if creator is already an active member
            exists = UserTeamDetailsRepository.get_collection().find_one({
                "team_id": team_id,
                "user_id": creator_id,
                "is_active": True,
            })
            if not exists:
                user_team = UserTeamDetailsModel(
                    user_id=PyObjectId(creator_id),
                    team_id=PyObjectId(team_id),
                    role_id="1",
                    is_active=True,
                    created_by=PyObjectId(creator_id),
                    updated_by=PyObjectId(creator_id),
                )
                UserTeamDetailsRepository.create(user_team)
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Added creator as member to {updated} teams.")) 