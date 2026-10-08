from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IncidentStatus(StrEnum):
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class IntersectionInput(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RoadInput(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    start_id: str
    end_id: str
    baseline_seconds: float = Field(gt=0)
    length_m: float = Field(gt=0)
    status: Literal["open", "closed"] = "open"


class NetworkSeed(BaseModel):
    intersections: list[IntersectionInput]
    roads: list[RoadInput]


class ReportInput(BaseModel):
    report_id: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=200)
    raw_text: str = Field(min_length=1, max_length=10000)
    location_text: str = Field(min_length=1, max_length=500)
    severity: Literal["low", "medium", "high", "critical"]
    delay_seconds: int = Field(default=0, ge=0, le=86400)
    affected_road_ids: list[str] = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    closure: bool = False
    received_at: datetime = Field(default_factory=utc_now)

    @field_validator("received_at")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("received_at must include a timezone")
        return value


class RouteRequest(BaseModel):
    origin_id: str
    destination_id: str
    vehicle_type: str = "ambulance"


class RouteResponse(BaseModel):
    intersections: list[str]
    road_ids: list[str]
    estimated_seconds: float
    calculated_at: datetime
    traffic_version: int
