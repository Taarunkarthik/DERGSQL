from app.location import nearest_road_ids


def test_nearest_endpoint_matching_respects_radius_and_orders_by_distance():
    intersections = [
        {"id": "near", "latitude": 12.0, "longitude": 77.0},
        {"id": "far", "latitude": 12.02, "longitude": 77.0},
        {"id": "other", "latitude": 12.0, "longitude": 77.005},
    ]
    roads = [
        {"id": "far-road", "start_id": "far", "end_id": "other"},
        {"id": "near-road", "start_id": "near", "end_id": "other"},
    ]
    assert nearest_road_ids(intersections, roads, 12.0, 77.0, 500) == ["near-road"]


def test_radius_must_be_positive():
    try:
        nearest_road_ids([], [], 0, 0, 0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected invalid radius")
