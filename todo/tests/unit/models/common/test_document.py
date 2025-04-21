from typing import ClassVar
from unittest import TestCase
from bson import ObjectId
from pydantic import Field
from todo.models.common.document import Document


class DocumentTests(TestCase):
    def test_subclass_without_collection_name_raises_error(self):
        with self.assertRaises(TypeError) as context:

            class InvalidDocument(Document):
                pass

        self.assertIn("must define a static `collection_name` field as a string", str(context.exception))

    def test_subclass_with_invalid_collection_name_type_raises_error(self):
        with self.assertRaises(TypeError):

            class InvalidDocument(Document):
                collection_name: ClassVar[str] = 123

    def test_subclass_with_valid_collection_name(self):
        try:

            class ValidDocument(Document):
                collection_name: ClassVar[str] = "valid_collection"
        except TypeError as e:
            print(e)
            self.fail("TypeError raised for valid Document subclass")

    def test_id_field_alias(self):
        class TestDocument(Document):
            collection_name: ClassVar[str] = "test_collection"

        obj_id = ObjectId()
        doc = TestDocument.model_validate({"_id": obj_id})
        self.assertEqual(doc.id, obj_id)
        self.assertEqual(doc.model_dump(mode="json", by_alias=True)["_id"], str(obj_id))

    def test_json_encoder_serializes_objectid(self):
        class TestDocument(Document):
            collection_name: ClassVar[str] = "test_collection"

        obj_id = ObjectId()
        doc = TestDocument(id=obj_id)
        serialized = doc.model_dump_json()
        self.assertIn(str(obj_id), serialized)

    def test_populate_by_name_behavior(self):
        class TestDocument(Document):
            collection_name: ClassVar[str] = "test_collection"
            field_one: str = Field(..., alias="fieldOne")

        data = {"_id": ObjectId(), "fieldOne": "value"}
        doc = TestDocument.model_validate(data)
        self.assertEqual(doc.field_one, "value")
        self.assertEqual(doc.model_dump(by_alias=True)["fieldOne"], "value")
