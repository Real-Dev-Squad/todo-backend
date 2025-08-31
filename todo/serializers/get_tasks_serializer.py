from rest_framework import serializers
from django.conf import settings

from todo.constants.task import SORT_FIELDS, SORT_ORDERS, SORT_FIELD_UPDATED_AT, SORT_FIELD_DEFAULT_ORDERS, TaskStatus


class CaseInsensitiveChoiceField(serializers.ChoiceField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.upper()
        return super().to_internal_value(data)


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

    profile = serializers.BooleanField(required=False, error_messages={"invalid": "profile must be a boolean value."})

    sort_by = serializers.ChoiceField(
        choices=SORT_FIELDS,
        required=False,
        default=SORT_FIELD_UPDATED_AT,
    )
    order = serializers.ChoiceField(
        choices=SORT_ORDERS,
        required=False,
    )

    teamId = serializers.CharField(required=False, allow_blank=False, allow_null=True)

    status = CaseInsensitiveChoiceField(
        choices=[status.value for status in TaskStatus],
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if "order" not in validated_data or validated_data["order"] is None:
            sort_by = validated_data.get("sort_by", SORT_FIELD_UPDATED_AT)
            validated_data["order"] = SORT_FIELD_DEFAULT_ORDERS[sort_by]

        return validated_data
