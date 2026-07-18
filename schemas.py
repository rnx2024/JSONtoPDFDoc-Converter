from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str | None = None
    type: Literal["paragraph", "table", "list", "kv"]
    text: str | None = None
    headers: list[Any] | None = None
    rows: list[list[Any]] | None = None
    items: list[Any] | dict[str, Any] | None = None

class StructuredDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    sections: list[Section]
