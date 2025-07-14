from datetime import datetime, timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from todo.models import Team, UserTeamDetails


class TeamRepository:
    @classmethod
    def get_by_id(cls, team_id: str) -> Optional[Team]:
        try:
            return Team.objects.get(id=team_id)
        except (ObjectDoesNotExist, ValueError):
            return None

    @classmethod
    def get_by_invite_code(cls, invite_code: str) -> Optional[Team]:
        try:
            return Team.objects.get(invite_code=invite_code)
        except ObjectDoesNotExist:
            return None

    @classmethod
    def create(cls, team_data: dict) -> Team:
        try:
            with transaction.atomic():
                team = Team.objects.create(
                    name=team_data['name'],
                    description=team_data.get('description'),
                    poc_id=team_data.get('poc_id'),
                    invite_code=team_data['invite_code'],
                    created_by=team_data['created_by'],
                    updated_by=team_data['updated_by'],
                    is_deleted=team_data.get('is_deleted', False),
                )
                
                return team
                
        except Exception as e:
            raise Exception(f"Error creating team: {str(e)}")

    @classmethod
    def update(cls, team_id: str, update_data: dict) -> Optional[Team]:
        try:
            with transaction.atomic():
                team = cls.get_by_id(team_id)
                if not team:
                    return None
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(team, field):
                        setattr(team, field, value)
                
                team.updated_at = datetime.now(timezone.utc)
                team.save()
                
                return team
                
        except Exception as e:
            raise Exception(f"Error updating team: {str(e)}")

    @classmethod
    def delete(cls, team_id: str) -> bool:
        try:
            team = cls.get_by_id(team_id)
            if not team:
                return False
            
            team.is_deleted = True
            team.save()
            return True
            
        except Exception as e:
            raise Exception(f"Error deleting team: {str(e)}")

    @classmethod
    def get_all_active(cls) -> List[Team]:
        try:
            return list(Team.objects.filter(is_deleted=False))
        except Exception as e:
            raise Exception(f"Error getting all active teams: {str(e)}")


class UserTeamDetailsRepository:
    @classmethod
    def get_by_user_id(cls, user_id: str) -> List[UserTeamDetails]:
        try:
            return list(UserTeamDetails.objects.filter(
                user_id=user_id,
                is_active=True
            ))
        except Exception as e:
            raise Exception(f"Error getting user team details: {str(e)}")

    @classmethod
    def get_by_team_id(cls, team_id: str) -> List[UserTeamDetails]:
        try:
            return list(UserTeamDetails.objects.filter(
                team_id=team_id,
                is_active=True
            ))
        except Exception as e:
            raise Exception(f"Error getting team user details: {str(e)}")

    @classmethod
    def create(cls, user_team_data: dict) -> UserTeamDetails:
        try:
            with transaction.atomic():
                user_team = UserTeamDetails.objects.create(
                    user_id=user_team_data['user_id'],
                    team_id=user_team_data['team_id'],
                    is_active=user_team_data.get('is_active', True),
                    role_id=user_team_data['role_id'],
                    created_by=user_team_data['created_by'],
                    updated_by=user_team_data['updated_by'],
                )
                
                return user_team
                
        except Exception as e:
            raise Exception(f"Error creating user team details: {str(e)}")

    @classmethod
    def update(cls, user_team_id: str, update_data: dict) -> Optional[UserTeamDetails]:
        try:
            with transaction.atomic():
                user_team = UserTeamDetails.objects.get(id=user_team_id)
                
                # Update fields
                for field, value in update_data.items():
                    if hasattr(user_team, field):
                        setattr(user_team, field, value)
                
                user_team.updated_at = datetime.now(timezone.utc)
                user_team.save()
                
                return user_team
                
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error updating user team details: {str(e)}")

    @classmethod
    def delete(cls, user_team_id: str) -> bool:
        try:
            user_team = UserTeamDetails.objects.get(id=user_team_id)
            user_team.is_active = False
            user_team.save()
            return True
            
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            raise Exception(f"Error deleting user team details: {str(e)}")

    @classmethod
    def get_by_user_and_team(cls, user_id: str, team_id: str) -> Optional[UserTeamDetails]:
        try:
            return UserTeamDetails.objects.get(
                user_id=user_id,
                team_id=team_id,
                is_active=True
            )
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            raise Exception(f"Error getting user team details: {str(e)}")
