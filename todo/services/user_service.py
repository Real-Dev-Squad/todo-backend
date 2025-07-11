from todo.models.user import UserModel
from todo.repositories.user_repository import UserRepository
from todo.constants.messages import ValidationErrors, RepositoryErrors
from todo.exceptions.exception_handler import (
    UserNotFoundException,
    APIException,
)
from rest_framework.exceptions import ValidationError as DRFValidationError


class UserService:
    @classmethod
    def create_or_update_user(cls, google_user_data: dict) -> UserModel:
        try:
            cls._validate_google_user_data(google_user_data)
            return UserRepository.create_or_update(google_user_data)
        except (UserNotFoundException, APIException, DRFValidationError):
            raise
        except Exception as e:
            raise APIException(
                RepositoryErrors.USER_CREATE_UPDATE_FAILED.format(str(e))
            ) from e

    @classmethod
    def get_user_by_id(cls, user_id: str) -> UserModel:
        user = UserRepository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException()
        return user

    @classmethod
    def _validate_google_user_data(cls, google_user_data: dict) -> None:
        validation_errors = {}

        if not google_user_data.get("google_id"):
            validation_errors["google_id"] = ValidationErrors.MISSING_GOOGLE_ID

        if not google_user_data.get("email"):
            validation_errors["email"] = ValidationErrors.MISSING_EMAIL

        if not google_user_data.get("name"):
            validation_errors["name"] = ValidationErrors.MISSING_NAME

        if not google_user_data.get("picture"):
            validation_errors["picture"] = ValidationErrors.MISSING_PICTURE

        if validation_errors:
            raise DRFValidationError(validation_errors)
