import sys
import types

fake = types.ModuleType("neo4j")
fake.Driver = object
fake.GraphDatabase = object()
sys.modules.setdefault("neo4j", fake)

import pytest

from app.network import get_segment, list_network


class Result:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def single(self):
        return self.rows[0] if self.rows else None


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, _query, **_params):
        return Result(next(self.responses))


class Driver:
    def __init__(self, responses):
        self.responses = responses

    def session(self):
        return Session(self.responses)


def test_list_network_includes_current_cost_and_state():
    intersection = {"id": "A", "name": "Station", "latitude": 12.0, "longitude": 77.0}
    road = {
        "id": "AB", "start_id": "A", "end_id": "B", "length_m": 500,
        "baseline_seconds": 60, "effective_seconds": 90, "status": "open",
    }
    result = list_network(Driver([[intersection], [road]]))
    assert result["intersections"] == [intersection]
    assert result["roads"][0]["effective_seconds"] == 90


def test_get_segment_not_found():
    with pytest.raises(LookupError, match="not found"):
        get_segment(Driver([[]]), "missing")
