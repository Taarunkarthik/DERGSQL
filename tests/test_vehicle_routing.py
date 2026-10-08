from app.routing import shortest_path


def test_vehicle_restrictions_select_vehicle_eligible_path():
    edges = [
        {
            "id": "restricted",
            "start_id": "A",
            "end_id": "D",
            "effective_seconds": 1,
            "status": "open",
            "allowed_vehicle_types": ["general"],
        },
        {
            "id": "ambulance-road",
            "start_id": "A",
            "end_id": "B",
            "effective_seconds": 4,
            "status": "open",
            "allowed_vehicle_types": ["ambulance", "fire"],
        },
        {
            "id": "B-D",
            "start_id": "B",
            "end_id": "D",
            "effective_seconds": 4,
            "status": "open",
            "allowed_vehicle_types": ["ambulance", "fire", "general"],
        },
    ]
    ambulance = shortest_path(edges, "A", "D", "ambulance")
    general = shortest_path(edges, "A", "D", "general")
    assert ambulance["road_ids"] == ["ambulance-road", "B-D"]
    assert general["road_ids"] == ["restricted"]


def test_legacy_edges_without_vehicle_list_remain_traversable():
    edges = [{"id": "AB", "start_id": "A", "end_id": "B", "effective_seconds": 2, "status": "open"}]
    assert shortest_path(edges, "A", "B", "fire")["road_ids"] == ["AB"]
