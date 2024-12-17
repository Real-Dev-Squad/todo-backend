from pydantic import BaseModel


class LinksData(BaseModel):
    next: str | None = None
    prev: str | None = None


class PaginatedResponse(BaseModel):
    links: LinksData | None = None
