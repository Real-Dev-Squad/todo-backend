from unittest import TestCase
from unittest.mock import patch

from todo.services.label_service import LabelService
from todo.dto.responses.get_labels_response import GetLabelsResponse
from todo.dto.responses.paginated_response import LinksData
from todo.constants.messages import ApiErrors
from todo.tests.fixtures.label import label_models


class LabelServiceTests(TestCase):
    def setUp(self):
        self.page = 1
        self.limit = 10
        self.search = ""

    @patch("todo.services.label_service.LabelRepository.get_all")
    def test_get_labels_returns_paginated_response_with_data(self, mock_get_all):
        mock_get_all.return_value = (2, label_models)

        response: GetLabelsResponse = LabelService.get_labels(page=self.page, limit=self.limit, search=self.search)

        self.assertIsInstance(response, GetLabelsResponse)
        self.assertEqual(response.total, 2)
        self.assertEqual(len(response.labels), len(label_models))
        self.assertEqual(response.page, self.page)
        self.assertEqual(response.limit, self.limit)
        self.assertIsInstance(response.links, LinksData)

    @patch("todo.services.label_service.LabelRepository.get_all")
    def test_get_labels_returns_empty_response_when_no_labels_found(self, mock_get_all):
        mock_get_all.return_value = (0, [])

        response: GetLabelsResponse = LabelService.get_labels(page=self.page, limit=self.limit, search=self.search)

        self.assertIsInstance(response, GetLabelsResponse)
        self.assertEqual(response.total, 0)
        self.assertEqual(response.labels, [])
        self.assertEqual(response.page, self.page)
        self.assertEqual(response.limit, self.limit)
        self.assertIsNone(response.links)
        self.assertIsNone(response.error)

    @patch("todo.services.label_service.LabelRepository.get_all")
    def test_get_labels_handles_invalid_regex_gracefully(self, mock_get_all):
        mock_get_all.return_value = (0, [])

        response: GetLabelsResponse = LabelService.get_labels(page=self.page, limit=self.limit, search="122[]")

        self.assertIsInstance(response, GetLabelsResponse)
        self.assertEqual(response.total, 0)
        self.assertEqual(response.labels, [])
        self.assertEqual(response.page, self.page)
        self.assertEqual(response.limit, self.limit)
        self.assertIsNone(response.links)
        self.assertIsNone(response.error)

    @patch("todo.services.label_service.LabelRepository.get_all")
    def test_get_labels_returns_page_not_found_if_page_exceeds_total_pages(self, mock_get_all):
        mock_get_all.return_value = (2, label_models)
        requested_page = 3
        limit = 2

        response: GetLabelsResponse = LabelService.get_labels(page=requested_page, limit=limit, search=self.search)

        self.assertEqual(response.labels, [])
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error["code"], "PAGE_NOT_FOUND")
        self.assertEqual(response.error["message"], ApiErrors.PAGE_NOT_FOUND)

    @patch("todo.services.label_service.LabelRepository.get_all")
    def test_get_labels_handles_exception_and_returns_error_response(self, mock_get_all):
        mock_get_all.side_effect = Exception("Database error")

        response: GetLabelsResponse = LabelService.get_labels(page=self.page, limit=self.limit, search=self.search)

        self.assertEqual(response.labels, [])
        self.assertIsNone(response.links)
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error["code"], "INTERNAL_ERROR")
        self.assertEqual(response.error["message"], ApiErrors.UNEXPECTED_ERROR_OCCURRED)

    def test_prepare_label_dto_maps_model_to_dto(self):
        model = label_models[0]
        dto = LabelService.prepare_label_dto(model)

        self.assertEqual(dto.id, str(model.id))
        self.assertEqual(dto.name, model.name)
        self.assertEqual(dto.color, model.color)

    def test_build_page_url(self):
        page = 2
        limit = 10
        search = "urgent"

        result = LabelService.build_page_url(page, limit, search)
        self.assertEqual(result, "/v1/labels?page=2&limit=10&search=urgent")

    def test_prepare_pagination_links_handles_first_page(self):
        result = LabelService.prepare_pagination_links(page=1, total_pages=3, limit=10, search="")
        self.assertIsNone(result.prev)
        self.assertIn("page=2", result.next)

    def test_prepare_pagination_links_handles_last_page(self):
        result = LabelService.prepare_pagination_links(page=3, total_pages=3, limit=10, search="")
        self.assertIsNone(result.next)
        self.assertIn("page=2", result.prev)

    def test_prepare_pagination_links_handles_both_first_and_last_page(self):
        result = LabelService.prepare_pagination_links(page=2, total_pages=3, limit=10, search="")
        self.assertIsNotNone(result.prev)
        self.assertIsNotNone(result.next)
        self.assertIn("page=1", result.prev)
        self.assertIn("page=3", result.next)
