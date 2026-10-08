import pytest
from pydantic import ValidationError

from app.models import ReportInput, RoadInput


def test_report_requires_timezone():
    with pytest.raises(ValidationError, match="timezone"):
        ReportInput(
            report_id="r1",
            source="operator",
            raw_text="Crash, lane blocked",
            location_text="Road A",
            severity="high",
            affected_road_ids=["road-a"],
            received_at="2026-10-06T21:23:00",
        )


def test_road_requires_positive_travel_time():
    with pytest.raises(ValidationError):
        RoadInput(id="r", start_id="a", end_id="b", baseline_seconds=0, length_m=10)
