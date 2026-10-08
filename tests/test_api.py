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
        main,
        "seed_network",
        lambda *args: (_ for _ in ()).throw(AssertionError("unexpected seed")),
    )
    with TestClient(main.app) as client:
        response = client.post(
            "/network/seed",
            json={
                "intersections": [{"id": "A", "name": "A", "latitude": 0, "longitude": 0}],
                "roads": [
                    {
                        "id": "AB",
                        "start_id": "A",
                        "end_id": "B",
                        "baseline_seconds": 5,
                        "length_m": 10,
                    }
                ],
            },
        )
    assert response.status_code == 422
    assert "endpoint" in response.json()["detail"]
