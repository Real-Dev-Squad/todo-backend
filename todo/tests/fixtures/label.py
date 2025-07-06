from bson import ObjectId
from todo.models.label import LabelModel


label_db_data = [
    {
        "_id": ObjectId("67478036eac9d93db7f59c35"),
        "name": "Label 1",
        "color": "#fa1e4e",
        "createdAt": "2024-11-08T10:14:35",
        "createdBy": str(ObjectId()),
    },
    {
        "_id": ObjectId("67588c1ac2195684a575840c"),
        "name": "Label 2",
        "color": "#ea1e4e",
        "createdAt": "2024-11-08T10:14:35",
        "createdBy": str(ObjectId()),
    },
]

label_models = [LabelModel(**data) for data in label_db_data]
