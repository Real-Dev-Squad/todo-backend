from dataclasses import dataclass
from django.conf import settings
from django.urls import reverse_lazy
from urllib.parse import urlencode

from todo.dto.responses.paginated_response import LinksData
from todo.repositories.label_repository import LabelRepository
from todo.dto.responses.get_labels_response import GetLabelsResponse
from todo.models.label import LabelModel
from todo.dto.label_dto import LabelDTO
from todo.constants.messages import ApiErrors


@dataclass
class PaginationConfig:
    DEFAULT_PAGE: int = 1
    DEFAULT_LIMIT: int = 10
    MAX_LIMIT: int = settings.REST_FRAMEWORK["DEFAULT_PAGINATION_SETTINGS"]["MAX_PAGE_LIMIT"]
    SEARCH: str = ""


class LabelService:
    @classmethod
    def get_labels(
        cls,
        page: int = PaginationConfig.DEFAULT_PAGE,
        limit: int = PaginationConfig.DEFAULT_LIMIT,
        search=PaginationConfig.SEARCH,
    ) -> GetLabelsResponse:
        try:
            [total_count, labels] = LabelRepository.get_all(page, limit, search)
            total_pages = (total_count + limit - 1) // limit

            if total_count > 0 and page > total_pages:
                return GetLabelsResponse(
                    labels=[],
                    limit=limit,
                    links=None,
                    error={"message": ApiErrors.PAGE_NOT_FOUND, "code": "PAGE_NOT_FOUND"},
                )
            if not labels:
                return GetLabelsResponse(
                    labels=[],
                    total=total_count,
                    page=page,
                    limit=limit,
                    links=None,
                )

            label_dtos = [cls.prepare_label_dto(label) for label in labels]

            links = cls.prepare_pagination_links(page=page, total_pages=total_pages, limit=limit, search=search)

            return GetLabelsResponse(labels=label_dtos, total=total_count, page=page, limit=limit, links=links)

        except Exception:
            return GetLabelsResponse(
                labels=[],
                limit=limit,
                links=None,
                error={"message": ApiErrors.UNEXPECTED_ERROR_OCCURRED, "code": "INTERNAL_ERROR"},
            )

    @classmethod
    def prepare_pagination_links(cls, page: int, total_pages: int, limit: int, search: str) -> LinksData:
        next_link = None
        prev_link = None

        if page < total_pages:
            next_page = page + 1
            next_link = cls.build_page_url(next_page, limit, search)

        if page > 1:
            prev_page = page - 1
            prev_link = cls.build_page_url(prev_page, limit, search)

        return LinksData(next=next_link, prev=prev_link)

    @classmethod
    def build_page_url(cls, page: int, limit: int, search: str) -> str:
        base_url = reverse_lazy("labels")
        query_params = urlencode({"page": page, "limit": limit, "search": search})
        return f"{base_url}?{query_params}"

    @classmethod
    def prepare_label_dto(cls, label_model: LabelModel) -> LabelDTO:
        from todo.dto.user_dto import UserDTO

        created_by_dto = None
        if label_model.createdBy:
            if label_model.createdBy == "system":
                created_by_dto = UserDTO(id="system", name="System")
            else:
                created_by_dto = UserDTO(id=label_model.createdBy, name="User")

        updated_by_dto = None
        if label_model.updatedBy:
            if label_model.updatedBy == "system":
                updated_by_dto = UserDTO(id="system", name="System")
            else:
                updated_by_dto = UserDTO(id=label_model.updatedBy, name="User")

        return LabelDTO(
            id=str(label_model.id),
            name=label_model.name,
            color=label_model.color,
            createdAt=label_model.createdAt,
            updatedAt=label_model.updatedAt,
            createdBy=created_by_dto,
            updatedBy=updated_by_dto,
        )
