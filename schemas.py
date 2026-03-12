from typing import Any, Literal
from pydantic import BaseModel

class Section(BaseModel):
    heading: str | None = None
    type: Literal["paragraph", "table", "list", "kv"]
    text: str | None = None
    rows: list[list[Any]] | None = None
    items: list[Any] | dict[str, Any] | None = None

class StructuredDoc(BaseModel):
    title: str | None = None
    sections: list[Section]
