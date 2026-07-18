from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Margin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    top: float = Field(default=12, ge=0, le=100)
    right: float = Field(default=12, ge=0, le=100)
    bottom: float = Field(default=16, ge=0, le=100)
    left: float = Field(default=12, ge=0, le=100)


ImagePosition = Literal["top", "bottom", "left", "right"]


class DocumentStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    margin: Margin = Field(default_factory=Margin)
    indentation: float = Field(default=0, ge=0, le=100)
    image_position: ImagePosition = "top"


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str | None = None
    type: Literal["paragraph", "table", "list", "kv"]
    text: str | None = None
    headers: list[Any] | None = None
    rows: list[list[Any]] | None = None
    items: list[Any] | dict[str, Any] | None = None
    indentation: float | None = Field(default=None, ge=0, le=100)
    heading_level: int | None = Field(default=None, ge=2, le=6)
    ordered: bool = False


class StructuredDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    sections: list[Section]
    style: DocumentStyle | None = None
