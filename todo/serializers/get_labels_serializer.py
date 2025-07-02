from rest_framework import serializers
from django.conf import settings

from todo.constants.messages import ValidationErrors


class GetLabelQueryParamsSerializer(serializers.Serializer):
    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        error_messages={
            "min_value": ValidationErrors.PAGE_POSITIVE,
        },
    )
    limit = serializers.IntegerField(
        required=False,
        default=10,
        min_value=1,
        max_value=settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"],
        error_messages={
            "min_value": ValidationErrors.LIMIT_POSITIVE,
        },
    )
    search = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        error_messages={
            "invalid": ValidationErrors.INVALID_SEARCH_QUERY_TYPE,
        },
    )
