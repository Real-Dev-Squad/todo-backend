from .base import *

DUAL_WRITE_ENABLED = False

# Remove PostgreSQL database configuration for tests
# This prevents Django from trying to connect to PostgreSQL
DATABASES = {}

# Use MongoDB only for tests
# The tests will use testcontainers to spin up their own MongoDB instance
