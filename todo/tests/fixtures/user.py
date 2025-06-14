from datetime import datetime, timezone

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
