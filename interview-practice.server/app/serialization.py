from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

# Free text in a request: trimmed, 1 to 200 characters.
ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class ApiModel(BaseModel):
    """Base for every request/response schema: snake_case in Python, camelCase in JSON.

    Only field names are converted; enum values and dict keys are left alone.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


def to_json(schema: type[BaseModel], obj: object) -> dict[str, Any]:
    """Map an object (typically an ORM model) to the JSON-safe dict `schema` defines.

    Only the fields declared on `schema` are copied, so anything it leaves out can
    never leak into a response; enums, UUIDs and datetimes are converted to their JSON
    forms (ISO 8601 for datetimes).
    """
    return schema.model_validate(obj, from_attributes=True).model_dump(mode="json")


def to_json_list(
    schema: type[BaseModel], objs: Iterable[object]
) -> list[dict[str, Any]]:
    return [to_json(schema, obj) for obj in objs]
