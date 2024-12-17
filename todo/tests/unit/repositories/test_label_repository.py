from unittest import TestCase
from unittest.mock import patch, MagicMock
from pymongo.collection import Collection
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
