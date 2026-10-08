from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver


def list_network(driver: Driver) -> dict:
    """Return intersections and segments with current routing state."""
    with driver.session() as session:
        intersections = [
            dict(row)
            for row in session.run(
                "MATCH (n:Intersection) "
                "RETURN n.id AS id, n.name AS name, n.latitude AS latitude, "
                "n.longitude AS longitude ORDER BY id"
            )
        ]
        roads = [
            dict(row)
            for row in session.run(
                "MATCH (a:Intersection)-[:ROAD_TO]->(r:RoadSegment)-[:ROAD_TO]->(b:Intersection) "
                "RETURN r.id AS id, a.id AS start_id, b.id AS end_id, "
                "r.length_m AS length_m, r.baseline_seconds AS baseline_seconds, "
                "r.effective_seconds AS effective_seconds, r.status AS status ORDER BY id"
            )
        ]
    return {"intersections": intersections, "roads": roads}


def get_segment(driver: Driver, road_id: str) -> dict:
    query = (
        "MATCH (a:Intersection)-[:ROAD_TO]->(r:RoadSegment {id:$id})-[:ROAD_TO]->(b:Intersection) "
        "RETURN r.id AS id, a.id AS start_id, b.id AS end_id, "
        "r.length_m AS length_m, r.baseline_seconds AS baseline_seconds, "
        "r.effective_seconds AS effective_seconds, r.status AS status"
    )
    with driver.session() as session:
        record = session.run(query, id=road_id).single()
        if record is None:
            raise LookupError(f"Road segment not found: {road_id}")
        return dict(record)
