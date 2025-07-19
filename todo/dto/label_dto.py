from pydantic import BaseModel


class LabelDTO(BaseModel):
    id: str
    name: str
    color: str
