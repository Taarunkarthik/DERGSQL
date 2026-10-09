import sys
import types

fake = types.ModuleType("neo4j")
fake.Driver = object
fake.GraphDatabase = object()
sys.modules.setdefault("neo4j", fake)

import pytest

from app.extraction import ExtractedIncident
from app.intake import create_candidate_report


class Record(dict):
    pass


class Result:
    def __init__(self, rows=(), record=None):
        self.rows = list(rows)
        self.record = record

    def __iter__(self):
        return iter(self.rows)

    def single(self):
        return self.record

    def consume(self):
        return None


class Session:
    def __init__(self, driver):
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, query, **params):
        if "MATCH (r:Report {id:$id}) RETURN r.source" in query:
            return Result(record=None)
        if "UNWIND $ids AS id" in query:
            return Result(record={"missing": []})
        if "MERGE (r:Report" in query:
            return Result(record={"id": params["id"], "status": "pending"})
        if "SET r.incident_type" in query:
            self.driver.metadata = params
            return Result()
        raise AssertionError(f"unexpected query: {query}")

    def execute_write(self, callback):
        return callback(self)


class Driver:
    def __init__(self):
        self.metadata = None

    def session(self):
        return Session(self)


def test_intake_matches_nearby_coordinates_and_marks_low_confidence(monkeypatch):
    driver = Driver()
    network = {
        "intersections": [
            {"id": "A", "name": "A", "latitude": 12.0, "longitude": 77.0},
            {"id": "B", "name": "B", "latitude": 12.01, "longitude": 77.0},
        ],
        "roads": [{"id": "AB", "start_id": "A", "end_id": "B"}],
    }
    monkeypatch.setattr("app.intake.list_network", lambda _driver: network)
    result = create_candidate_report(
        driver,
        report_id="candidate-1",
        source="operator",
        raw_text="collision nearby",
        extraction=ExtractedIncident(
            incident_type="collision", location_text="Near A", severity="high",
            delay_seconds=30, confidence=0.4, latitude=12.0, longitude=77.0,
        ),
        radius_m=250,
        confidence_threshold=0.6,
    )
    assert result["matched_road_ids"] == ["AB"]
    assert result["review_required"] is True
    assert result["status"] == "pending"
    assert driver.metadata["location_method"] == "coordinate-radius"


def test_intake_exact_name_matches_connected_segments(monkeypatch):
    monkeypatch.setattr(
        "app.intake.list_network",
        lambda _driver: {
            "intersections": [{"id": "J1", "name": "Junction One", "latitude": 0, "longitude": 0}],
            "roads": [{"id": "r1", "start_id": "J1", "end_id": "J2"}],
        },
    )
    result = create_candidate_report(
        Driver(), report_id="candidate-2", source="radio", raw_text="incident",
        extraction=ExtractedIncident(
            incident_type="other", location_text="Junction One", severity="medium", confidence=0.9,
        ),
        radius_m=500, confidence_threshold=0.5,
    )
    assert result["matched_road_ids"] == ["r1"]
    assert result["location_method"] == "exact-intersection-name"
