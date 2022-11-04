from django.db import models
from google.protobuf.json_format import MessageToDict
from google.protobuf.json_format import Parse as ParseJSON
from google.protobuf.json_format import ParseDict


class ProtoBufField(models.JSONField):

    description = "A protobuf object backed by a JSON Field"

    def __init__(self, *args, **kwargs):
        self.serializer = kwargs.pop("serializer")
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["serializer"] = self.serializer
        return name, path, args, kwargs

    @property
    def non_db_attrs(self):
        return super().non_db_attrs + ("serializer",)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return self.serializer()
        value = super().from_db_value(value, expression, connection)
        return ParseDict(value, self.serializer())

    def to_python(self, value):
        if isinstance(value, self.serializer) or value is None:
            return value
        if isinstance(value, str):
            return ParseJSON(value, self.serializer())
        return ParseDict(value, self.serializer())

    def get_prep_value(self, value):
        if value is None:
            return value
        return super().get_prep_value(MessageToDict(value))
