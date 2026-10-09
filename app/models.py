from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.extraction import ExtractedIncident


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
    allowed_vehicle_types: list[Literal["ambulance", "fire", "police", "general"]] = Field(
        default_factory=lambda: ["ambulance", "fire", "police", "general"]
    )

    @field_validator("allowed_vehicle_types")
    @classmethod
    def validate_unique_vehicles(cls, values: list[str]) -> list[str]:
        if not values or len(values) != len(set(values)):
            raise ValueError("allowed_vehicle_types must be non-empty and unique")
        return values


class NetworkSeed(BaseModel):
    intersections: list[IntersectionInput] = Field(min_length=1)
    roads: list[RoadInput] = Field(min_length=1)


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

    @field_validator("affected_road_ids")
    @classmethod
    def unique_roads(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("affected_road_ids must not contain duplicates")
        return values

    @field_validator("received_at")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("received_at must include a timezone")
        return value


class ExtractionIntake(BaseModel):
    report_id: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=200)
    raw_text: str = Field(min_length=1, max_length=10000)
    extraction: ExtractedIncident
    radius_m: float = Field(default=1000, gt=0, le=50000)
    confidence_threshold: float = Field(default=0.6, ge=0, le=1)


class RouteRequest(BaseModel):
    origin_id: str = Field(min_length=1, max_length=100)
    destination_id: str = Field(min_length=1, max_length=100)
    vehicle_type: Literal["ambulance", "fire", "police", "general"] = "ambulance"


class RouteResponse(BaseModel):
    intersections: list[str]
    road_ids: list[str]
    estimated_seconds: float
    calculated_at: datetime
    traffic_version: str
    vehicle_type: str = "ambulance"
