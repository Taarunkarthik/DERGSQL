from __future__ import annotations

from typing import TYPE_CHECKING

from app.db import open_session

if TYPE_CHECKING:
    from neo4j import Driver


def list_network(driver: Driver) -> dict:
    """Return intersections and segments with current routing state."""
    with open_session(driver) as session:
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
                "r.effective_seconds AS effective_seconds, r.status AS status, "
                "r.allowed_vehicle_types AS allowed_vehicle_types ORDER BY id"
            )
        ]
    return {"intersections": intersections, "roads": roads}


def get_segment(driver: Driver, road_id: str) -> dict:
    query = (
        "MATCH (a:Intersection)-[:ROAD_TO]->(r:RoadSegment {id:$id})-[:ROAD_TO]->(b:Intersection) "
        "RETURN r.id AS id, a.id AS start_id, b.id AS end_id, "
        "r.length_m AS length_m, r.baseline_seconds AS baseline_seconds, "
        "r.effective_seconds AS effective_seconds, r.status AS status, "
        "r.allowed_vehicle_types AS allowed_vehicle_types"
    )
    with open_session(driver) as session:
        record = session.run(query, id=road_id).single()
        if record is None:
            raise LookupError(f"Road segment not found: {road_id}")
        return dict(record)


def nearest_segments(
    driver: Driver, latitude: float, longitude: float, radius_m: float
) -> list[dict]:
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("latitude/longitude are out of range")
    if not 0 < radius_m <= 50_000:
        raise ValueError("radius_m must be greater than zero and at most 50000")
    query = (
        "MATCH (a:Intersection)-[:ROAD_TO]->(r:RoadSegment)-[:ROAD_TO]->(b:Intersection) "
        "WITH r, a, b, point.distance(point({latitude:$latitude, longitude:$longitude}), "
        "point({latitude:a.latitude, longitude:a.longitude})) AS da, "
        "point.distance(point({latitude:$latitude, longitude:$longitude}), "
        "point({latitude:b.latitude, longitude:b.longitude})) AS db "
        "WITH r, a, b, CASE WHEN da < db THEN da ELSE db END AS nearest_m "
        "WHERE nearest_m <= $radius_m "
        "RETURN r.id AS id, a.id AS start_id, b.id AS end_id, "
        "r.status AS status, r.effective_seconds AS effective_seconds, nearest_m "
        "ORDER BY nearest_m, id"
    )
    with open_session(driver) as session:
        return [
            dict(row)
            for row in session.run(
                query, latitude=latitude, longitude=longitude, radius_m=radius_m
            )
        ]
