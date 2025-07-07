from rest_framework import serializers
from django.conf import settings

from todo.constants.task import SORT_FIELDS, SORT_ORDERS, SORT_FIELD_CREATED_AT


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
        default=settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["DEFAULT_PAGE_LIMIT"],
        min_value=1,
        max_value=settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"],
        error_messages={
            "min_value": "limit must be greater than or equal to 1",
        },
    )
    sort_by = serializers.ChoiceField(
        choices=SORT_FIELDS,
        required=False,
        default=SORT_FIELD_CREATED_AT,
    )
    order = serializers.ChoiceField(
        choices=SORT_ORDERS,
        required=False,
    )
