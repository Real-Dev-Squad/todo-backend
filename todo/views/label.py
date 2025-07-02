from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from todo.serializers.get_labels_serializer import GetLabelQueryParamsSerializer
from todo.services.label_service import LabelService


class LabelListView(APIView):
    def get(self, request: Request):
        """
        Retrieve a paginated list of labels.
        """
        query = GetLabelQueryParamsSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        response = LabelService.get_labels(
            page=query.validated_data["page"],
            limit=query.validated_data["limit"],
            search=query.validated_data["search"].strip(),
        )
        return Response(
            data=response.model_dump(mode="json", exclude_none=True), 
            status=status.HTTP_200_OK
        )
