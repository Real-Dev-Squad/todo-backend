import io
import os

from cloudinary import uploader
import cloudinary

from todo.exceptions.auth_exceptions import APIException


class CloudinaryService:
    @staticmethod
    def _require_config() -> tuple[str, str, str]:
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        if not cloud_name or not api_key or not api_secret:
            raise APIException(
                "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."
            )

        return str(cloud_name), str(api_key), str(api_secret)

    @staticmethod
    def _configure() -> None:
        cloud_name, api_key, api_secret = CloudinaryService._require_config()
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )

    @classmethod
    def upload_image(
        cls,
        *,
        file_data: bytes,
        user_id: str,
        image_name: str,
    ) -> str:
        cls._configure()

        if not image_name.strip():
            raise APIException("imageName must be a non-empty string")

        upload_folder = f"todo/users/{user_id}"
        public_id = f"{user_id}/{image_name.strip()}"

        file_obj = io.BytesIO(file_data)

        result = uploader.upload(
            file_obj,
            public_id=public_id,
            folder=upload_folder,
            overwrite=True,
            resource_type="image",
        )

        return result["secure_url"]
