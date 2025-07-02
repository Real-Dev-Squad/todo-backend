from unittest import TestCase
from unittest.mock import patch, MagicMock
from pymongo.collection import Collection
import re

from todo.models.label import LabelModel
from todo.repositories.label_repository import LabelRepository
from todo.tests.fixtures.label import label_db_data


class LabelRepositoryTests(TestCase):
    def setUp(self):
        self.label_ids = [label_data["_id"] for label_data in label_db_data]
        self.label_data = label_db_data

        self.patcher_get_collection = patch("todo.repositories.label_repository.LabelRepository.get_collection")
        self.mock_get_collection = self.patcher_get_collection.start()
        self.mock_collection = MagicMock(spec=Collection)
        self.mock_get_collection.return_value = self.mock_collection

    def tearDown(self):
        self.patcher_get_collection.stop()

    def test_list_by_ids_returns_label_models(self):
        self.mock_collection.find.return_value = self.label_data

        result = LabelRepository.list_by_ids(self.label_ids)

        self.assertEqual(len(result), len(self.label_data))
        self.assertTrue(all(isinstance(label, LabelModel) for label in result))

    def test_list_by_ids_returns_empty_list_if_not_found(self):
        self.mock_collection.find.return_value = []

        result = LabelRepository.list_by_ids([self.label_ids[0]])

        self.assertEqual(result, [])

    def test_list_by_ids_skips_db_call_for_empty_input(self):
        result = LabelRepository.list_by_ids([])

        self.assertEqual(result, [])
        self.mock_get_collection.assert_not_called()
        self.mock_collection.assert_not_called()

    def test_get_all_returns_paginated_labels(self):
        mock_agg_result = iter(
            [
                {
                    "total": [{"count": len(self.label_data)}],
                    "data": self.label_data,
                }
            ]
        )
        self.mock_collection.aggregate.return_value = mock_agg_result

        total, labels = LabelRepository.get_all(page=1, limit=2, search="")

        self.assertEqual(total, len(self.label_data))
        self.assertEqual(len(labels), len(self.label_data))
        self.assertTrue(all(isinstance(label, LabelModel) for label in labels))
        self.mock_collection.aggregate.assert_called_once()

    def test_get_all_applies_search_filter(self):
        search_term = "Label 1"
        escaped_search = re.escape(search_term)
        mock_agg_result = iter(
            [
                {
                    "total": [{"count": 1}],
                    "data": self.label_data[:1],
                }
            ]
        )
        self.mock_collection.aggregate.return_value = mock_agg_result

        total, labels = LabelRepository.get_all(page=1, limit=2, search=search_term)
        pipeline_arg = self.mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline_arg[0]["$match"]

        self.assertEqual(total, 1)
        self.assertEqual(len(labels), 1)
        self.mock_collection.aggregate.assert_called_once()
        self.assertEqual(match_stage["name"], {"$regex": escaped_search, "$options": "i"})

    def test_get_all_returns_empty_list_when_no_labels(self):
        mock_agg_result = iter(
            [
                {
                    "total": [],
                    "data": [],
                }
            ]
        )
        self.mock_collection.aggregate.return_value = mock_agg_result

        total, labels = LabelRepository.get_all(page=1, limit=2, search="")

        self.assertEqual(total, 0)
        self.assertEqual(labels, [])
        self.mock_collection.aggregate.assert_called_once()

    def test_get_all_returns_empty_list_when_search_term_does_not_match(self):
        search_term = "random search term"
        escaped_search = re.escape(search_term)
        mock_agg_result = iter(
            [
                {
                    "total": [],
                    "data": [],
                }
            ]
        )
        self.mock_collection.aggregate.return_value = mock_agg_result

        total, labels = LabelRepository.get_all(page=1, limit=2, search=search_term)
        pipeline_arg = self.mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline_arg[0]["$match"]

        self.assertEqual(total, 0)
        self.assertEqual(labels, [])
        self.mock_collection.aggregate.assert_called_once()
        self.assertEqual(match_stage["name"]["$regex"], escaped_search)

    def test_get_all_escapes_invalid_regex_characters(self):
        search_term = "122[]"
        escaped_search = re.escape(search_term)
        mock_agg_result = iter(
            [
                {
                    "total": [],
                    "data": [],
                }
            ]
        )
        self.mock_collection.aggregate.return_value = mock_agg_result

        total, labels = LabelRepository.get_all(page=1, limit=10, search=search_term)
        pipeline_arg = self.mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline_arg[0]["$match"]

        self.assertEqual(total, 0)
        self.assertEqual(labels, [])
        self.mock_collection.aggregate.assert_called_once()
        self.assertEqual(match_stage["name"]["$regex"], escaped_search)
