import unittest
from unittest.mock import patch, MagicMock
from todo.repositories.task_repository import TaskRepository
from todo.constants.task import (
    SORT_FIELD_PRIORITY,
    SORT_FIELD_DUE_AT,
    SORT_FIELD_CREATED_AT,
    SORT_FIELD_ASSIGNEE,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC,
)


class TaskRepositorySortingTests(unittest.TestCase):
    def setUp(self):
        self.patcher_get_collection = patch("todo.repositories.task_repository.TaskRepository.get_collection")
        self.mock_get_collection = self.patcher_get_collection.start()
        self.mock_collection = MagicMock()
        self.mock_get_collection.return_value = self.mock_collection

        self.mock_cursor = MagicMock()
        self.mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        self.mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = self.mock_cursor

    def tearDown(self):
        self.patcher_get_collection.stop()

    def test_list_sort_by_priority_desc(self):
        """Test sorting by priority descending (HIGH→MEDIUM→LOW)"""
        TaskRepository.list(1, 10, SORT_FIELD_PRIORITY, SORT_ORDER_DESC)

        self.mock_collection.find.assert_called_once()

        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_PRIORITY, 1)])

    def test_list_sort_by_priority_asc(self):
        TaskRepository.list(1, 10, SORT_FIELD_PRIORITY, SORT_ORDER_ASC)

        self.mock_collection.find.assert_called_once()

        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_PRIORITY, -1)])

    def test_list_sort_by_created_at_desc(self):
        TaskRepository.list(1, 10, SORT_FIELD_CREATED_AT, SORT_ORDER_DESC)

        self.mock_collection.find.assert_called_once()
        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_CREATED_AT, -1)])

    def test_list_sort_by_created_at_asc(self):
        TaskRepository.list(1, 10, SORT_FIELD_CREATED_AT, SORT_ORDER_ASC)

        self.mock_collection.find.assert_called_once()
        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_CREATED_AT, 1)])

    def test_list_sort_by_due_at_desc(self):
        TaskRepository.list(1, 10, SORT_FIELD_DUE_AT, SORT_ORDER_DESC)

        self.mock_collection.find.assert_called_once()
        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_DUE_AT, -1)])

    def test_list_sort_by_due_at_asc(self):
        TaskRepository.list(1, 10, SORT_FIELD_DUE_AT, SORT_ORDER_ASC)

        self.mock_collection.find.assert_called_once()
        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_DUE_AT, 1)])

    @patch("todo.repositories.task_repository.TaskRepository._list_sorted_by_assignee")
    def test_list_sort_by_assignee_calls_special_method(self, mock_assignee_sort):
        mock_assignee_sort.return_value = []

        TaskRepository.list(1, 10, SORT_FIELD_ASSIGNEE, SORT_ORDER_DESC)

        mock_assignee_sort.assert_called_once_with(1, 10, SORT_ORDER_DESC)

        self.mock_collection.find.assert_not_called()

    def test_list_sorted_by_assignee_desc(self):
        mock_pipeline_result = []
        self.mock_collection.aggregate.return_value = iter(mock_pipeline_result)

        TaskRepository._list_sorted_by_assignee(1, 10, SORT_ORDER_DESC)

        self.mock_collection.aggregate.assert_called_once()
        pipeline = self.mock_collection.aggregate.call_args[0][0]

        sort_stage = next((stage for stage in pipeline if "$sort" in stage), None)
        self.assertIsNotNone(sort_stage)
        self.assertEqual(sort_stage["$sort"]["assignee_name"], -1)

    def test_list_sorted_by_assignee_asc(self):
        mock_pipeline_result = []
        self.mock_collection.aggregate.return_value = iter(mock_pipeline_result)

        TaskRepository._list_sorted_by_assignee(1, 10, SORT_ORDER_ASC)

        self.mock_collection.aggregate.assert_called_once()
        pipeline = self.mock_collection.aggregate.call_args[0][0]

        sort_stage = next((stage for stage in pipeline if "$sort" in stage), None)
        self.assertIsNotNone(sort_stage)
        self.assertEqual(sort_stage["$sort"]["assignee_name"], 1)

    def test_list_pagination_with_sorting(self):
        page = 3
        limit = 5

        TaskRepository.list(page, limit, SORT_FIELD_CREATED_AT, SORT_ORDER_DESC)

        expected_skip = (page - 1) * limit

        self.mock_collection.find.return_value.sort.return_value.skip.assert_called_once_with(expected_skip)
        self.mock_collection.find.return_value.sort.return_value.skip.return_value.limit.assert_called_once_with(limit)

    def test_list_default_sort_parameters(self):
        TaskRepository.list(1, 10)

        self.mock_collection.find.assert_called_once()

        self.mock_collection.find.return_value.sort.assert_called_once_with([(SORT_FIELD_CREATED_AT, -1)])
