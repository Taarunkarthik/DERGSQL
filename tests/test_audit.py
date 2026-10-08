import sys
import types

fake = types.ModuleType("neo4j")
fake.Driver = object
fake.GraphDatabase = object()
sys.modules.setdefault("neo4j", fake)

import pytest

from app.audit import report_audit


class Result:
    def __init__(self, record):
        self.record = record

    def single(self):
        return self.record


class Session:
    def __init__(self, record):
        self.record = record

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, _query, **_params):
        return Result(self.record)


class Driver:
    def __init__(self, record):
        self.record = record

    def session(self):
        return Session(self.record)


def test_audit_returns_provenance_and_active_roads():
    record = {
        "report_id": "r-1",
        "source": "dispatch",
        "raw_text": "lane blocked",
        "report_status": "confirmed",
        "proposed_road_ids": ["road-1"],
        "active_road_ids": ["road-1"],
    }
    result = report_audit(Driver(record), "r-1")
    assert result["source"] == "dispatch"
    assert result["active_road_ids"] == ["road-1"]


def test_audit_missing_report_raises():
    with pytest.raises(LookupError, match="not found"):
        report_audit(Driver(None), "missing")
