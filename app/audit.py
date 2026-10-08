from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver


def report_audit(driver: Driver, report_id: str) -> dict:
    """Return source provenance and affected roads for an incident report."""
    query = (
        "MATCH (r:Report {id:$id}) "
        "OPTIONAL MATCH (r)-[:PROPOSES_IMPACT]->(proposed:RoadSegment) "
        "OPTIONAL MATCH (r)-[:DESCRIBES]->(i:Incident)-[impact:AFFECTS]->(affected:RoadSegment) "
        "RETURN r.id AS report_id, r.source AS source, r.raw_text AS raw_text, "
        "r.location_text AS location_text, r.severity AS severity, "
        "r.confidence AS confidence, r.status AS report_status, "
        "r.received_at AS received_at, i.id AS incident_id, i.status AS incident_status, "
        "collect(DISTINCT proposed.id) AS proposed_road_ids, "
        "collect(DISTINCT CASE WHEN impact.active=true THEN affected.id ELSE null END) "
        "AS active_road_ids"
    )
    with driver.session() as session:
        record = session.run(query, id=report_id).single()
        if record is None:
            raise LookupError(f"Report not found: {report_id}")
        return dict(record)
