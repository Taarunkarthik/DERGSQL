import sys
import types

try:
    import neo4j  # noqa: F401
except ImportError:
    fake = types.ModuleType("neo4j")
    fake.Driver = object
    fake.GraphDatabase = object()
    sys.modules["neo4j"] = fake

from app.incidents import confirm_report, ingest_report, reject_report, resolve_report
from app.models import ReportInput


class Result:
    def __init__(self, record=None):
        self.record = record

    def single(self):
        return self.record

    def consume(self):
        return None


class FakeTx:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.queries = []

    def run(self, query, **params):
        self.queries.append((query, params))
        return Result(next(self.responses))


class FakeSession:
    def __init__(self, tx):
        self.tx = tx

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute_write(self, callback):
        return callback(self.tx)

    def run(self, query, **params):
        return self.tx.run(query, **params)


class FakeDriver:
    def __init__(self, responses):
        self.tx = FakeTx(responses)

    def session(self):
        return FakeSession(self.tx)


def sample_report():
    return ReportInput(
        report_id="report-1", source="dispatcher", raw_text="Two lanes blocked",
        location_text="Road AB", severity="high", delay_seconds=120,
        affected_road_ids=["AB"], confidence=0.9,
    )


def test_ingest_rejects_unknown_segment_transactionally():
    driver = FakeDriver([None, {"missing": ["unknown"]}])
    try:
        ingest_report(driver, sample_report())
    except ValueError as exc:
        assert "Unknown road" in str(exc)
    else:
        raise AssertionError("expected unknown road validation")
    assert len(driver.tx.queries) == 2


def test_confirm_stages_an_incident_transactionally():
    tx = FakeTx([{"id": "report-1", "road_ids": ["AB"]}, None, None, None])
    driver = FakeDriver([])
    driver.tx = tx
    result = confirm_report(driver, "report-1")
    assert result == {"id": "report-1", "status": "confirmed", "affected_segments": 1}
    assert len(tx.queries) == 4
    assert "impact.active=true" in tx.queries[2][0]
    assert "explicitly_confirmed=true" in tx.queries[1][0]


def test_reject_pending_report_does_not_create_incident():
    driver = FakeDriver([{"id": "report-1", "status": "rejected"}])
    result = reject_report(driver, "report-1")
    assert result["status"] == "rejected"
    query = driver.tx.queries[0][0]
    assert "r.status='pending'" in query
    assert "Incident" not in query


def test_resolve_deactivates_impact_and_recomputes_segment():
    tx = FakeTx([{"status": "confirmed"}, {"road_ids": ["AB"]}, None, None, None])
    driver = FakeDriver([])
    driver.tx = tx
    result = resolve_report(driver, "report-1")
    assert result["status"] == "resolved"
    assert "collect(DISTINCT s.id)" in tx.queries[1][0]
    assert "impact.active=false" in tx.queries[2][0]
    assert "SET r.status='resolved'" in tx.queries[3][0]
    assert "s.effective_seconds=s.baseline_seconds + delay" in tx.queries[4][0]
