from datetime import datetime, timezone

from bson import ObjectId

users_db_data = [
    {
        "google_id": "123456789",
        "email_id": "test@example.com",
        "name": "Test User",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    },
    {
        "google_id": "987654321",
        "email_id": "another@example.com",
        "name": "Another User",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    },
]

google_auth_user_payload = {
    "user_id": str(ObjectId()),
    "google_id": "test_google_id",
    "email": "test@example.com",
    "name": "Test User",
}
