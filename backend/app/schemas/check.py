from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, HttpUrl, field_serializer


class CheckRequest(BaseModel):
    url: HttpUrl


class CheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    status: Literal["up", "down"]
    status_code: int | None
    response_time_ms: float | None
    error_message: str | None
    checked_at: datetime

    @field_serializer("checked_at")
    def serialize_checked_at(self, value: datetime) -> str:
        # SQLite returns naive datetimes; we always store UTC, so label it as such.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")


class CheckListResponse(BaseModel):
    items: list[CheckResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total_checks: int
    successful_checks: int
    failed_checks: int
    average_response_time_ms: float | None
