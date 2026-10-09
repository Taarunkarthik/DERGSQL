"""Optional live Neo4j tests. Enable with DERGSQL_NEO4J_INTEGRATION=1."""

import os
import uuid

import pytest

if os.getenv("DERGSQL_NEO4J_INTEGRATION") != "1":
    pytest.skip("Set DERGSQL_NEO4J_INTEGRATION=1 to run live Neo4j tests", allow_module_level=True)

from app.config import settings
from app.db import create_driver, initialize_schema, seed_network
from app.incidents import confirm_report, ingest_report, resolve_report
from app.models import ReportInput
from app.routing import find_route


@pytest.fixture
def neo4j_driver():
    driver = create_driver()
    initialize_schema(driver)
    try:
        driver.verify_connectivity()
        yield driver
    finally:
        driver.close()


def test_seed_report_confirm_route_resolve_round_trip(neo4j_driver):
    suffix = uuid.uuid4().hex[:10]
    a, b, c = (f"{suffix}-{key}" for key in ("a", "b", "c"))
    road_ab, road_bc, road_ac = (f"{suffix}-{key}" for key in ("ab", "bc", "ac"))
    report_id = f"{suffix}-report"
    intersections = [
        {"id": a, "name": "A", "latitude": 0.0, "longitude": 0.0},
        {"id": b, "name": "B", "latitude": 0.0, "longitude": 0.01},
        {"id": c, "name": "C", "latitude": 0.01, "longitude": 0.01},
    ]
    roads = [
        {"id": road_ab, "start_id": a, "end_id": b, "baseline_seconds": 30.0, "length_m": 1000.0, "status": "open", "allowed_vehicle_types": ["ambulance"]},
        {"id": road_bc, "start_id": b, "end_id": c, "baseline_seconds": 30.0, "length_m": 1000.0, "status": "open", "allowed_vehicle_types": ["ambulance"]},
        {"id": road_ac, "start_id": a, "end_id": c, "baseline_seconds": 100.0, "length_m": 2000.0, "status": "open", "allowed_vehicle_types": ["ambulance"]},
    ]
    seed_network(neo4j_driver, intersections, roads)
    try:
        report = ReportInput(
            report_id=report_id, source="integration-test", raw_text="road blocked",
            location_text="A-B", severity="critical", delay_seconds=120,
            affected_road_ids=[road_ab], confidence=1.0, closure=True,
        )
        ingest_report(neo4j_driver, report)
        assert find_route(neo4j_driver, a, c)["road_ids"] == [road_ab, road_bc]
        confirm_report(neo4j_driver, report_id)
        assert find_route(neo4j_driver, a, c)["road_ids"] == [road_ac]
        resolve_report(neo4j_driver, report_id)
        assert find_route(neo4j_driver, a, c)["road_ids"] == [road_ab, road_bc]
    finally:
        with neo4j_driver.session(database=settings.neo4j_database) as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[a, b, c, road_ab, road_bc, road_ac, report_id, f"incident:{report_id}"],
            ).consume()
