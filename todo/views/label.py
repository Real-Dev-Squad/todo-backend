from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from todo.serializers.get_labels_serializer import GetLabelQueryParamsSerializer
from todo.services.label_service import LabelService
from todo.dto.responses.get_labels_response import GetLabelsResponse


class LabelListView(APIView):
    @extend_schema(
        operation_id="get_labels",
        summary="Get paginated list of labels",
        description="Retrieve a paginated list of labels with optional search functionality",
        tags=["labels"],
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page number for pagination (default: 1)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of labels per page (default: 10, max: 100)",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search term to filter labels by name",
                required=False,
            ),
        ],
        responses={
            200: GetLabelsResponse,
            400: OpenApiResponse(description="Bad request - Invalid query parameters"),
            500: OpenApiResponse(description="Internal server error"),
        },
    )
    def get(self, request: Request):
        """
        Retrieve a paginated list of labels.
        """
        query = GetLabelQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        response = LabelService.get_labels(
            page=query.validated_data["page"],
            limit=query.validated_data["limit"],
            search=query.validated_data["search"],
        )
        return Response(data=response.model_dump(mode="json"), status=status.HTTP_200_OK)
