from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ExtractedIncident(BaseModel):
    """Untrusted candidate fields parsed from a supplied report by an LLM adapter."""

    model_config = ConfigDict(extra="forbid")

    incident_type: Literal["collision", "closure", "flooding", "construction", "other"]
    location_text: str = Field(min_length=1, max_length=500)
    severity: Literal["low", "medium", "high", "critical"]
    delay_seconds: int = Field(default=0, ge=0, le=86400)
    closure: bool = False
    confidence: float = Field(ge=0, le=1)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_are_paired(self) -> "ExtractedIncident":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must either both be supplied or both be omitted")
        return self


def parse_extraction_json(payload: str) -> ExtractedIncident:
    """Parse and validate provider output; never treats it as a confirmed event."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Extraction output must be valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("Extraction output must be a JSON object")
    try:
        return ExtractedIncident.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid extracted incident fields: {exc}") from exc
