from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, field=None):
        if value is None:
            return None
        if value is not None and ObjectId.is_valid(value):
            return ObjectId(value)
        raise ValueError(f"Invalid ObjectId: {value}")
