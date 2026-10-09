import sys
import types

fake = types.ModuleType("neo4j")
fake.Driver = object
fake.GraphDatabase = object()
sys.modules.setdefault("neo4j", fake)

from app.incident_recompute import recompute_segments


class Result:
    def consume(self):
        return None


class Tx:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        return Result()


def test_recompute_sorts_and_deduplicates_segment_ids():
    tx = Tx()
    recompute_segments(tx, ["b", "a", "b"])
    assert tx.calls[0][1]["road_ids"] == ["a", "b"]
    assert "s.effective_seconds=s.baseline_seconds + delay" in tx.calls[0][0]


def test_recompute_skips_empty_segment_list():
    tx = Tx()
    recompute_segments(tx, [])
    assert tx.calls == []
