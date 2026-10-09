from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver

from app.config import settings


def open_session(driver: Driver):
    try:
        return driver.session(database=settings.neo4j_database)
    except TypeError:
        return driver.session()


def create_driver() -> Driver:
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )


def initialize_schema(driver: Driver) -> None:
    constraints = [
        "CREATE CONSTRAINT intersection_id IF NOT EXISTS FOR (n:Intersection) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT road_id IF NOT EXISTS FOR (n:RoadSegment) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (n:Incident) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT report_id IF NOT EXISTS FOR (n:Report) REQUIRE n.id IS UNIQUE",
    ]
    with open_session(driver) as session:
        for statement in constraints:
            session.run(statement).consume()


def seed_network(driver: Driver, intersections: list[dict], roads: list[dict]) -> None:
    with open_session(driver) as session:
        def seed(tx) -> None:
            tx.run(
                "UNWIND $items AS item MERGE (n:Intersection {id:item.id}) "
                "SET n.name=item.name, n.latitude=item.latitude, n.longitude=item.longitude",
                items=intersections,
            ).consume()
            tx.run(
                "UNWIND $items AS item "
                "MATCH (a:Intersection {id:item.start_id}), (b:Intersection {id:item.end_id}) "
                "MERGE (r:RoadSegment {id:item.id}) "
                "ON CREATE SET r.baseline_seconds=item.baseline_seconds, "
                "r.effective_seconds=item.baseline_seconds, r.length_m=item.length_m, "
                "r.status=item.status, r.allowed_vehicle_types=item.allowed_vehicle_types "
                "MERGE (a)-[:ROAD_TO]->(r) MERGE (r)-[:ROAD_TO]->(b)",
                items=roads,
            ).consume()
        session.execute_write(seed)
