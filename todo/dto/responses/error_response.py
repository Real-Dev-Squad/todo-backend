from enum import Enum
from typing import Dict, List
from pydantic import BaseModel


class ApiErrorSource(Enum):
    PARAMETER = "parameter"
    POINTER = "pointer"
    HEADER = "header"


class ApiErrorDetail(BaseModel):
    source: Dict[ApiErrorSource, str] | None = None
    title: str | None = None
    detail: str | None = None


class ApiErrorResponse(BaseModel):
    statusCode: int
    message: str
    errors: List[ApiErrorDetail]
