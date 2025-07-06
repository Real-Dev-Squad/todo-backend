from rest_framework import serializers
from django.conf import settings


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
        choices=["priority", "dueAt", "createdAt", "assignee"],
        required=False,
        default="createdAt",
        error_messages={
            "invalid_choice": "sort_by must be one of: priority, dueAt, createdAt, assignee",
        },
    )
    order = serializers.ChoiceField(
        choices=["asc", "desc"],
        required=False,
        error_messages={
            "invalid_choice": "order must be one of: asc, desc",
        },
    )

    def validate(self, attrs):
        """
        Apply default order based on sort_by field if order is not provided.
        """
        sort_by = attrs.get("sort_by", "createdAt")
        order = attrs.get("order")

        if order is None:
            if sort_by == "createdAt":
                attrs["order"] = "desc"
            elif sort_by == "dueAt":
                attrs["order"] = "asc"
            elif sort_by == "priority":
                attrs["order"] = "desc"
            elif sort_by == "assignee":
                attrs["order"] = "asc"

        return attrs
