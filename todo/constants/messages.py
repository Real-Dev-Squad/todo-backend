# Application Messages
class AppMessages:
    TASK_CREATED = "Task created successfully"


# Repository error messages
class RepositoryErrors:
    TASK_CREATION_FAILED = "Failed to create task: {0}"
    DB_INIT_FAILED = "Failed to initialize database: {0}"


# API error messages
class ApiErrors:
    REPOSITORY_ERROR = "Repository Error"
    SERVER_ERROR = "Server Error"
    UNEXPECTED_ERROR = "Unexpected Error"
    INTERNAL_SERVER_ERROR = "Internal server error"
    VALIDATION_ERROR = "Validation Error"
    INVALID_LABELS = "Invalid Labels"
    INVALID_LABEL_IDS = "Invalid Label IDs"
    PAGE_NOT_FOUND = "Requested page exceeds available results"
    UNEXPECTED_ERROR_OCCURRED = "An unexpected error occurred"


# Validation error messages
class ValidationErrors:
    BLANK_TITLE = "Title must not be blank."
    INVALID_OBJECT_ID = "{0} is not a valid ObjectId."
    PAST_DUE_DATE = "Due date must be in the future."
    PAGE_POSITIVE = "Page must be a positive integer"
    LIMIT_POSITIVE = "Limit must be a positive integer"
    MAX_LIMIT_EXCEEDED = "Maximum limit of {0} exceeded"
    MISSING_LABEL_IDS = "The following label IDs do not exist: {0}"
