from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetUploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: str
    content_type: str = Field(alias="contentType")
    data_base64: str = Field(alias="dataBase64")
    project_id: str | None = Field(default=None, alias="projectId")
    type: str = "image"

    @model_validator(mode="after")
    def validate_payload(self) -> "AssetUploadRequest":
        if not self.filename.strip():
            raise ValueError("filename is required for asset upload.")
        if not self.content_type.startswith("image/"):
            raise ValueError("Only image uploads are supported.")
        if not self.data_base64.strip():
            raise ValueError("dataBase64 is required for asset upload.")
        return self


class AssetOut(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    url: str
    project_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
