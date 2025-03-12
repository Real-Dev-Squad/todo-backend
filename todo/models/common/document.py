from abc import ABC
from bson import ObjectId

from pydantic import BaseModel, Field

from todo.models.common.pyobjectid import PyObjectId


class Document(BaseModel, ABC):
    id: PyObjectId | None = Field(None, alias="_id")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "collection_name") or not isinstance(cls.collection_name, str):
            raise TypeError(f"Class {cls.__name__} must define a static `collection_name` field as a string.")

    class Config:
        from_attributes = True
        json_encoders = {ObjectId: str}
        populate_by_name = True
