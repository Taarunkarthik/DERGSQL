import sys
import types

import pytest
from fastapi.testclient import TestClient

try:
    import neo4j  # noqa: F401
except ImportError:
    fake = types.ModuleType("neo4j")
    fake.Driver = object
    fake.GraphDatabase = object()
    sys.modules["neo4j"] = fake

try:
    import pydantic_settings  # noqa: F401
except ImportError:
    pytest.skip("Install project dependencies for API tests", allow_module_level=True)

import app.main as main


class FakeDriver:
    def close(self):
        pass


def test_seed_validates_endpoints_before_database_write(monkeypatch):
    monkeypatch.setattr(main, "create_driver", FakeDriver)
    monkeypatch.setattr(main, "initialize_schema", lambda driver: None)
    monkeypatch.setattr(
        main, "seed_network", lambda *args: (_ for _ in ()).throw(AssertionError("unexpected seed"))
    )
    with TestClient(main.app) as client:
        response = client.post(
            "/network/seed",
            json={
                "intersections": [{"id": "A", "name": "A", "latitude": 0, "longitude": 0}],
                "roads": [{"id": "AB", "start_id": "A", "end_id": "B", "baseline_seconds": 5, "length_m": 10}],
            },
        )
    assert response.status_code == 422


def test_nearby_endpoint_rejects_invalid_query_ranges_before_database_call(monkeypatch):
    monkeypatch.setattr(main, "create_driver", FakeDriver)
    monkeypatch.setattr(main, "initialize_schema", lambda driver: None)
    monkeypatch.setattr(
        main,
        "nearest_segments",
        lambda *args: (_ for _ in ()).throw(AssertionError("unexpected database call")),
    )
    with TestClient(main.app) as client:
        latitude = client.get("/roads/nearby?latitude=91&longitude=0")
        longitude = client.get("/roads/nearby?latitude=0&longitude=181")
        radius = client.get("/roads/nearby?latitude=0&longitude=0&radius_m=50001")
        zero_radius = client.get("/roads/nearby?latitude=0&longitude=0&radius_m=0")
    assert [r.status_code for r in (latitude, longitude, radius, zero_radius)] == [422] * 4


def test_incidents_endpoint_supports_bounded_pagination(monkeypatch):
    monkeypatch.setattr(main, "create_driver", FakeDriver)
    monkeypatch.setattr(main, "initialize_schema", lambda driver: None)
    calls = []
    monkeypatch.setattr(
        main, "list_incidents", lambda driver, status, **kwargs: calls.append((status, kwargs)) or []
    )
    with TestClient(main.app) as client:
        response = client.get("/incidents?status=resolved&limit=25&offset=50")
        too_large = client.get("/incidents?limit=501")
        negative_offset = client.get("/incidents?offset=-1")
    assert response.status_code == 200
    assert calls == [("resolved", {"limit": 25, "offset": 50})]
    assert too_large.status_code == 422
    assert negative_offset.status_code == 422


def test_extract_endpoint_stages_parsed_incident_but_never_confirms(monkeypatch):
    monkeypatch.setattr(main, "create_driver", FakeDriver)
    monkeypatch.setattr(main, "initialize_schema", lambda driver: None)
    captured = {}

    def fake_candidate(driver, **kwargs):
        captured.update(kwargs)
        return {"id": kwargs["report_id"], "status": "pending", "review_required": True}

    monkeypatch.setattr(main, "create_candidate_report", fake_candidate)
    with TestClient(main.app) as client:
        response = client.post(
            "/reports/extract",
            json={
                "report_id": "test-1",
                "source": "operator-note",
                "raw_text": "Incident near junction",
                "extraction": {
                    "incident_type": "collision",
                    "location_text": "A",
                    "severity": "high",
                    "confidence": 0.4,
                    "latitude": 12.0,
                    "longitude": 77.0,
                },
            },
        )
    assert response.status_code == 201
    assert captured["extraction"].incident_type == "collision"
    assert response.json()["status"] == "pending"


def test_extract_endpoint_rejects_unpaired_coordinates(monkeypatch):
    monkeypatch.setattr(main, "create_driver", FakeDriver)
    monkeypatch.setattr(main, "initialize_schema", lambda driver: None)
    with TestClient(main.app) as client:
        response = client.post(
            "/reports/extract",
            json={
                "report_id": "test-2",
                "source": "operator-note",
                "raw_text": "Incident near junction",
                "extraction": {
                    "incident_type": "collision",
                    "location_text": "A",
                    "severity": "high",
                    "confidence": 0.9,
                    "latitude": 12.0,
                },
            },
        )
    assert response.status_code == 422
