from __future__ import annotations

from typing import TYPE_CHECKING

from app.db import open_session

if TYPE_CHECKING:
    from neo4j import Driver


def report_audit(driver: Driver, report_id: str) -> dict:
    query = (
        "MATCH (r:Report {id:$id}) "
        "OPTIONAL MATCH (r)-[:PROPOSES_IMPACT]->(proposed:RoadSegment) "
        "OPTIONAL MATCH (r)-[:DESCRIBES]->(i:Incident) "
        "OPTIONAL MATCH (i)-[active:AFFECTS {active:true}]->(activeRoad:RoadSegment) "
        "RETURN r.id AS report_id, r.source AS source, r.raw_text AS raw_text, "
        "r.location_text AS location_text, r.severity AS severity, "
        "r.confidence AS confidence, r.status AS report_status, "
        "r.received_at AS received_at, r.incident_type AS incident_type, "
        "r.location_method AS location_method, r.location_radius_m AS location_radius_m, "
        "r.review_required AS review_required, i.id AS incident_id, i.status AS incident_status, "
        "collect(DISTINCT proposed.id) AS proposed_road_ids, "
        "collect(DISTINCT activeRoad.id) AS active_road_ids"
    )
    with open_session(driver) as session:
        record = session.run(query, id=report_id).single()
        if record is None:
            raise LookupError(f"Report not found: {report_id}")
        return dict(record)
