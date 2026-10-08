import sys
import types

fake = types.ModuleType("neo4j")
fake.Driver = object
fake.GraphDatabase = object()
sys.modules.setdefault("neo4j", fake)

from app.routing import find_route


class Record(dict):
    def single(self):
        return self


class Session:
    def __init__(self):
        self.query_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def run(self, query):
        self.query_count += 1
        if self.query_count == 1:
            return iter([
                Record(start_id="A", end_id="B", id="AB", effective_seconds=4, status="open"),
                Record(start_id="B", end_id="D", id="BD", effective_seconds=3, status="open"),
                Record(start_id="A", end_id="D", id="AD", effective_seconds=1, status="closed"),
            ])
        return Record(count=3, cost_sum=8)


class Driver:
    def session(self):
        self.current_session = Session()
        return self.current_session


def test_find_route_loads_db_edges_and_skips_closed_segments():
    result = find_route(Driver(), "A", "D")
    assert result["road_ids"] == ["AB", "BD"]
    assert result["estimated_seconds"] == 7
    assert result["traffic_version"] == 11
