from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver

from app.db import open_session
from app.incident_recompute import clear_road_impacts, recompute_segments
from app.models import ReportInput


def ingest_report(driver: Driver, report: ReportInput) -> dict:
    with open_session(driver) as session:
        return session.execute_write(lambda tx: ingest_report_in_transaction(tx, report))


def ingest_report_in_transaction(tx, report: ReportInput) -> dict:
    data = report.model_dump(mode="json")
    existing = tx.run(
        "MATCH (r:Report {id:$id}) RETURN r.source AS source, r.raw_text AS raw_text, "
        "r.location_text AS location_text, r.severity AS severity, "
        "r.delay_seconds AS delay_seconds, r.closure AS closure, "
        "r.confidence AS confidence, r.status AS status",
        id=report.report_id,
    ).single()
    expected = {
        "source": report.source,
        "raw_text": report.raw_text,
        "location_text": report.location_text,
        "severity": report.severity,
        "delay_seconds": report.delay_seconds,
        "closure": report.closure,
        "confidence": report.confidence,
    }
    if existing is not None:
        if any(existing[key] != value for key, value in expected.items()):
            raise ValueError("Report ID already exists with different content")
        if existing["status"] != "pending":
            raise ValueError(f"Report has already been reviewed ({existing['status']})")
    missing = tx.run(
        "UNWIND $ids AS id OPTIONAL MATCH (r:RoadSegment {id:id}) "
        "WITH id, r WHERE r IS NULL RETURN collect(id) AS missing",
        ids=report.affected_road_ids,
    ).single()["missing"]
    if missing:
        raise ValueError(f"Unknown road segment ids: {', '.join(missing)}")
    record = tx.run(
        "MERGE (r:Report {id:$id}) "
        "ON CREATE SET r.source=$source, r.raw_text=$raw_text, "
        "r.location_text=$location_text, r.severity=$severity, "
        "r.delay_seconds=$delay_seconds, r.confidence=$confidence, "
        "r.closure=$closure, r.received_at=datetime($received_at), r.status='pending' "
        "WITH r UNWIND $road_ids AS road_id "
        "MATCH (s:RoadSegment {id:road_id}) MERGE (r)-[:PROPOSES_IMPACT]->(s) "
        "RETURN r.id AS id, r.status AS status, r.source AS source, r.raw_text AS raw_text, "
        "r.severity AS severity, r.delay_seconds AS delay_seconds, r.closure AS closure, "
        "r.confidence AS confidence, r.location_text AS location_text",
        id=report.report_id, source=report.source, raw_text=report.raw_text,
        location_text=report.location_text, severity=report.severity,
        delay_seconds=report.delay_seconds, confidence=report.confidence,
        closure=report.closure, received_at=data["received_at"],
        road_ids=report.affected_road_ids,
    ).single()
    return dict(record)


def confirm_report(driver: Driver, report_id: str) -> dict:
    def write(tx) -> dict:
        pending = tx.run(
            "MATCH (r:Report {id:$id}) WHERE r.status='pending' "
            "OPTIONAL MATCH (r)-[:PROPOSES_IMPACT]->(s:RoadSegment) "
            "RETURN r.id AS id, collect(s.id) AS road_ids",
            id=report_id,
        ).single()
        if pending is None:
            existing = tx.run("MATCH (r:Report {id:$id}) RETURN r.status AS status", id=report_id).single()
            if existing is None:
                raise ValueError(f"Report not found: {report_id}")
            raise ValueError(f"Only pending reports can be confirmed (current: {existing['status']})")
        road_ids = pending["road_ids"]
        if not road_ids:
            raise ValueError("Pending report has no linked road segments")
        tx.run(
            "MATCH (r:Report {id:$id}) SET r.status='confirmed', r.reviewed_at=datetime() "
            "MERGE (i:Incident {id:'incident:' + r.id}) "
            "SET i.severity=r.severity, i.status='confirmed', i.reported_at=r.received_at, "
            "i.explicitly_confirmed=true MERGE (r)-[:DESCRIBES]->(i)",
            id=report_id,
        ).consume()
        tx.run(
            "MATCH (i:Incident {id:$incident_id}), (s:RoadSegment) WHERE s.id IN $road_ids "
            "MERGE (i)-[impact:AFFECTS]->(s) WITH i, impact, s "
            "MATCH (r:Report {id:$report_id}) "
            "SET impact.delay_seconds=r.delay_seconds, impact.closure=r.closure, impact.active=true",
            incident_id=f"incident:{report_id}", report_id=report_id, road_ids=road_ids,
        ).consume()
        recompute_segments(tx, road_ids)
        return {"id": report_id, "status": "confirmed", "affected_segments": len(road_ids)}

    with open_session(driver) as session:
        return session.execute_write(write)


def reject_report(driver: Driver, report_id: str) -> dict:
    with open_session(driver) as session:
        record = session.run(
            "MATCH (r:Report {id:$id}) WHERE r.status='pending' "
            "SET r.status='rejected', r.reviewed_at=datetime() "
            "RETURN r.id AS id, r.status AS status",
            id=report_id,
        ).single()
        if record is not None:
            return dict(record)
        existing = session.run(
            "MATCH (r:Report {id:$id}) RETURN r.status AS status", id=report_id
        ).single()
        if existing is None:
            raise ValueError(f"Report not found: {report_id}")
        raise ValueError(f"Only pending reports can be rejected (current: {existing['status']})")


def resolve_report(driver: Driver, report_id: str) -> dict:
    def write(tx) -> dict:
        incident_id = f"incident:{report_id}"
        status = tx.run(
            "MATCH (r:Report {id:$report_id})-[:DESCRIBES]->(i:Incident {id:$incident_id}) "
            "WHERE r.status='confirmed' AND i.status='confirmed' RETURN i.status AS status",
            report_id=report_id, incident_id=incident_id,
        ).single()
        if status is None:
            raise ValueError(f"Confirmed report not found: {report_id}")
        road_ids = clear_road_impacts(tx, incident_id)
        tx.run(
            "MATCH (r:Report {id:$report_id})-[:DESCRIBES]->(i:Incident {id:$incident_id}) "
            "SET r.status='resolved', r.resolved_at=datetime(), i.status='resolved', "
            "i.resolved_at=datetime()",
            report_id=report_id, incident_id=incident_id,
        ).consume()
        recompute_segments(tx, road_ids)
        return {"id": report_id, "status": "resolved"}

    with open_session(driver) as session:
        return session.execute_write(write)


def list_incidents(
    driver: Driver, status: str | None = None, limit: int = 100, offset: int = 0
) -> list[dict]:
    query = (
        "MATCH (i:Incident) WHERE $status IS NULL OR i.status=$status "
        "OPTIONAL MATCH (r:Report)-[:DESCRIBES]->(i) "
        "RETURN i.id AS id, i.severity AS severity, i.status AS status, "
        "i.reported_at AS reported_at, collect(r.id) AS reports "
        "ORDER BY reported_at DESC, id SKIP $offset LIMIT $limit"
    )
    with open_session(driver) as session:
        return [
            dict(row)
            for row in session.run(query, status=status, offset=offset, limit=limit)
        ]
