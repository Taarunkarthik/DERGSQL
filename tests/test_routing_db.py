import sys
import types

fake = types.ModuleType("neo4j")
fake.Driver = object
fake.GraphDatabase = object()
sys.modules.setdefault("neo4j", fake)

from app.routing import find_route


class Record(dict):
    pass


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
                Record(start_id="A", end_id="B", id="AB", effective_seconds=4, status="open", allowed_vehicle_types=["ambulance"]),
                Record(start_id="B", end_id="D", id="BD", effective_seconds=3, status="open", allowed_vehicle_types=["ambulance"]),
                Record(start_id="A", end_id="D", id="AD", effective_seconds=1, status="closed", allowed_vehicle_types=["ambulance"]),
            ])
        return iter([Record(id="A"), Record(id="B"), Record(id="D")])


class Driver:
    def session(self):
        self.current_session = Session()
        return self.current_session


def test_find_route_loads_db_edges_skips_closed_segments_and_labels_snapshot():
    result = find_route(Driver(), "A", "D", "ambulance")
    assert result["road_ids"] == ["AB", "BD"]
    assert result["estimated_seconds"] == 7
    assert result["vehicle_type"] == "ambulance"
    assert len(result["traffic_version"]) == 16
