from pydantic import BaseModel
from typing import Dict, Any, Optional


class LinksData(BaseModel):
    next: str | None = None
    prev: str | None = None


class PaginatedResponse(BaseModel):
    links: LinksData | None = None
    error: Optional[Dict[str, Any]] = None
