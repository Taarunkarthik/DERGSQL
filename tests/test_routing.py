import pytest

from app.routing import shortest_path


@pytest.fixture
def edges():
    return [
        {"id": "AB", "start_id": "A", "end_id": "B", "effective_seconds": 2, "status": "open"},
        {"id": "BD", "start_id": "B", "end_id": "D", "effective_seconds": 2, "status": "open"},
        {"id": "AC", "start_id": "A", "end_id": "C", "effective_seconds": 3, "status": "open"},
        {"id": "CD", "start_id": "C", "end_id": "D", "effective_seconds": 3, "status": "open"},
    ]


def test_chooses_minimum_cost_path(edges):
    result = shortest_path(edges, "A", "D")
    assert result["intersections"] == ["A", "B", "D"]
    assert result["road_ids"] == ["AB", "BD"]
    assert result["estimated_seconds"] == 4


def test_avoids_closed_edge(edges):
    edges[0]["status"] = "closed"
    result = shortest_path(edges, "A", "D")
    assert result["road_ids"] == ["AC", "CD"]


def test_no_route_raises(edges):
    with pytest.raises(LookupError):
        shortest_path(edges, "missing", "D")


def test_negative_cost_rejected(edges):
    edges[0]["effective_seconds"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        shortest_path(edges, "A", "D")
