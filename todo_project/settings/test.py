from .base import *
import os

DUAL_WRITE_ENABLED = False
POSTGRES_SYNC_ENABLED = False

# Remove PostgreSQL database configuration for tests
DATABASES = {}


os.environ.setdefault("POSTGRES_SYNC_ENABLED", "False")
os.environ.setdefault("DUAL_WRITE_ENABLED", "False")
