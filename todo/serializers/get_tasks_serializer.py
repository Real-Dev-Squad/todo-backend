from rest_framework import serializers

from todo.constants.task import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT


class GetTaskQueryParamsSerializer(serializers.Serializer):
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        error_messages={
            "min_value": "page must be greater than or equal to 1",
        },
    )
    limit = serializers.IntegerField(
        required=False,
        default=DEFAULT_PAGE_LIMIT,
        min_value=1,
        max_value=MAX_PAGE_LIMIT,
        error_messages={
            "min_value": "limit must be greater than or equal to 1",
        },
    )
