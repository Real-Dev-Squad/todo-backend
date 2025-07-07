import unittest
from todo.serializers.get_tasks_serializer import GetTaskQueryParamsSerializer
from todo.constants.task import (
    SORT_FIELD_PRIORITY,
    SORT_FIELD_DUE_AT,
    SORT_FIELD_CREATED_AT,
    SORT_FIELD_ASSIGNEE,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
)


class GetTaskQueryParamsSerializerSortingTests(unittest.TestCase):
    def test_valid_sort_by_fields(self):
        valid_sort_fields = [SORT_FIELD_PRIORITY, SORT_FIELD_DUE_AT, SORT_FIELD_CREATED_AT, SORT_FIELD_ASSIGNEE]

        for sort_field in valid_sort_fields:
            with self.subTest(sort_field=sort_field):
                serializer = GetTaskQueryParamsSerializer(data={"sort_by": sort_field})
                self.assertTrue(
                    serializer.is_valid(), f"sort_by='{sort_field}' should be valid. Errors: {serializer.errors}"
                )
                self.assertEqual(serializer.validated_data["sort_by"], sort_field)

    def test_valid_order_values(self):
        valid_orders = [SORT_ORDER_ASC, SORT_ORDER_DESC]

        for order in valid_orders:
            with self.subTest(order=order):
                serializer = GetTaskQueryParamsSerializer(data={"sort_by": SORT_FIELD_PRIORITY, "order": order})
                self.assertTrue(serializer.is_valid(), f"order='{order}' should be valid. Errors: {serializer.errors}")
                self.assertEqual(serializer.validated_data["order"], order)

    def test_invalid_sort_by_field(self):
        invalid_sort_fields = ["invalid_field", "title", "description", "status", "", None, 123]

        for sort_field in invalid_sort_fields:
            with self.subTest(sort_field=sort_field):
                serializer = GetTaskQueryParamsSerializer(data={"sort_by": sort_field})
                self.assertFalse(serializer.is_valid(), f"sort_by='{sort_field}' should be invalid")
                self.assertIn("sort_by", serializer.errors)

    def test_invalid_order_value(self):
        invalid_orders = ["invalid_order", "ascending", "descending", "up", "down", "", None, 123]

        for order in invalid_orders:
            with self.subTest(order=order):
                serializer = GetTaskQueryParamsSerializer(data={"sort_by": SORT_FIELD_PRIORITY, "order": order})
                self.assertFalse(serializer.is_valid(), f"order='{order}' should be invalid")
                self.assertIn("order", serializer.errors)

    def test_sort_by_defaults_to_created_at(self):
        serializer = GetTaskQueryParamsSerializer(data={})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["sort_by"], SORT_FIELD_CREATED_AT)

    def test_order_has_no_default(self):
        serializer = GetTaskQueryParamsSerializer(data={})
        self.assertTrue(serializer.is_valid())

        self.assertNotIn("order", serializer.validated_data)

    def test_sort_by_with_no_order(self):
        serializer = GetTaskQueryParamsSerializer(data={"sort_by": SORT_FIELD_DUE_AT})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["sort_by"], SORT_FIELD_DUE_AT)
        self.assertNotIn("order", serializer.validated_data)

    def test_order_with_no_sort_by(self):
        serializer = GetTaskQueryParamsSerializer(data={"order": SORT_ORDER_ASC})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["sort_by"], SORT_FIELD_CREATED_AT)
        self.assertEqual(serializer.validated_data["order"], SORT_ORDER_ASC)

    def test_sorting_with_pagination(self):
        data = {"page": 2, "limit": 15, "sort_by": SORT_FIELD_PRIORITY, "order": SORT_ORDER_DESC}
        serializer = GetTaskQueryParamsSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        self.assertEqual(serializer.validated_data["page"], 2)
        self.assertEqual(serializer.validated_data["limit"], 15)
        self.assertEqual(serializer.validated_data["sort_by"], SORT_FIELD_PRIORITY)
        self.assertEqual(serializer.validated_data["order"], SORT_ORDER_DESC)

    def test_case_sensitivity(self):
        """Test that sort parameters are case sensitive"""

        serializer = GetTaskQueryParamsSerializer(data={"sort_by": "Priority"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("sort_by", serializer.errors)

        serializer = GetTaskQueryParamsSerializer(data={"sort_by": SORT_FIELD_PRIORITY, "order": "DESC"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("order", serializer.errors)

    def test_empty_string_parameters(self):
        serializer = GetTaskQueryParamsSerializer(data={"sort_by": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("sort_by", serializer.errors)

        serializer = GetTaskQueryParamsSerializer(data={"sort_by": SORT_FIELD_PRIORITY, "order": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("order", serializer.errors)

    def test_all_valid_combinations(self):
        sort_fields = [SORT_FIELD_PRIORITY, SORT_FIELD_DUE_AT, SORT_FIELD_CREATED_AT, SORT_FIELD_ASSIGNEE]
        orders = [SORT_ORDER_ASC, SORT_ORDER_DESC]

        for sort_field in sort_fields:
            for order in orders:
                with self.subTest(sort_field=sort_field, order=order):
                    serializer = GetTaskQueryParamsSerializer(data={"sort_by": sort_field, "order": order})
                    self.assertTrue(
                        serializer.is_valid(),
                        f"Combination sort_by='{sort_field}', order='{order}' should be valid. "
                        f"Errors: {serializer.errors}",
                    )
                    self.assertEqual(serializer.validated_data["sort_by"], sort_field)
                    self.assertEqual(serializer.validated_data["order"], order)
