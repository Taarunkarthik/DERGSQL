from neo4j import Driver

from app.models import ReportInput


def ingest_report(driver: Driver, report: ReportInput) -> dict:
    data = report.model_dump(mode="json")
    with driver.session() as session:
        def write(tx) -> dict:
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
                "MATCH (s:RoadSegment {id:road_id}) "
                "MERGE (r)-[:PROPOSES_IMPACT]->(s) "
                "RETURN r.id AS id, r.status AS status",
                id=report.report_id,
                source=report.source,
                raw_text=report.raw_text,
                location_text=report.location_text,
                severity=report.severity,
                delay_seconds=report.delay_seconds,
                confidence=report.confidence,
                closure=report.closure,
                received_at=data["received_at"],
                road_ids=report.affected_road_ids,
            ).single()
            return dict(record)
        return session.execute_write(write)


def confirm_report(driver: Driver, report_id: str) -> dict:
    with driver.session() as session:
        def write(tx) -> dict:
            record = tx.run(
                "MATCH (r:Report {id:$id}) "
                "OPTIONAL MATCH (r)-[:PROPOSES_IMPACT]->(s:RoadSegment) "
                "WITH r, collect(s) AS roads "
                "WHERE r.status IN ['pending', 'confirmed'] AND size(roads) > 0 "
                "SET r.status='confirmed', r.reviewed_at=datetime() "
                "WITH r, roads "
                "UNWIND roads AS s "
                "MERGE (i:Incident {id:'incident:' + r.id}) "
                "SET i.severity=r.severity, i.status='confirmed', i.reported_at=r.received_at "
                "SET i.explicitly_confirmed=true "
                "MERGE (r)-[:DESCRIBES]->(i) "
                "MERGE (i)-[impact:AFFECTS]->(s) "
                "SET impact.delay_seconds=r.delay_seconds, impact.closure=r.closure, "
                "impact.active=true "
                "WITH r, roads "
                "UNWIND roads AS s "
                "OPTIONAL MATCH (other:Incident {status:'confirmed', explicitly_confirmed:true}) "
                "-[active:AFFECTS {active:true}]->(s) "
                "WITH r, s, collect(active) AS impacts "
                "WITH r, s, impacts, any(x IN impacts WHERE x.closure=true) AS closed, "
                "reduce(total=0, x IN impacts | total + coalesce(x.delay_seconds, 0)) AS delay "
                "SET s.status=CASE WHEN closed THEN 'closed' ELSE 'open' END, "
                "s.effective_seconds=s.baseline_seconds + delay "
                "WITH r, count(s) AS affected_segments "
                "RETURN r.id AS id, r.status AS status, affected_segments",
                id=report_id,
            ).single()
            if record is None:
                exists = tx.run("MATCH (r:Report {id:$id}) RETURN r.status AS status", id=report_id).single()
                if exists is None:
                    raise ValueError(f"Report not found: {report_id}")
                if exists["status"] == "rejected":
                    raise ValueError("Rejected reports cannot be confirmed")
                raise ValueError("Report has no linked road segments")
            return dict(record)
        return session.execute_write(write)


def resolve_report(driver: Driver, report_id: str) -> dict:
    with driver.session() as session:
        def write(tx) -> dict:
            record = tx.run(
                "MATCH (r:Report {id:$id})-[:DESCRIBES]->(i:Incident) "
                "OPTIONAL MATCH (i)-[impact:AFFECTS]->(s:RoadSegment) "
                "WITH r, i, collect(DISTINCT s) AS roads "
                "SET r.status='resolved', i.status='resolved', i.resolved_at=datetime() "
                "WITH r, i, roads "
                "OPTIONAL MATCH (i)-[old:AFFECTS]->() SET old.active=false "
                "WITH r, i, roads UNWIND roads AS s "
                "OPTIONAL MATCH (other:Incident {status:'confirmed', explicitly_confirmed:true}) "
                "-[active:AFFECTS {active:true}]->(s) WHERE other <> i "
                "WITH r, s, collect(active) AS impacts "
                "WITH r, s, impacts, any(x IN impacts WHERE x.closure=true) AS closed, "
                "reduce(total=0, x IN impacts | total + coalesce(x.delay_seconds, 0)) AS delay "
                "SET s.status=CASE WHEN closed THEN 'closed' ELSE 'open' END, "
                "s.effective_seconds=s.baseline_seconds + delay "
                "RETURN r.id AS id, r.status AS status",
                id=report_id,
            ).single()
            if record is None:
                raise ValueError(f"Confirmed report not found: {report_id}")
            return dict(record)
        return session.execute_write(write)


def list_incidents(driver: Driver, status: str | None = None) -> list[dict]:
    query = (
        "MATCH (i:Incident) OPTIONAL MATCH (r:Report)-[:DESCRIBES]->(i) "
        "WHERE $status IS NULL OR i.status=$status "
        "RETURN i.id AS id, i.severity AS severity, i.status AS status, "
        "i.reported_at AS reported_at, collect(r.id) AS reports ORDER BY reported_at DESC"
    )
    with driver.session() as session:
        return [dict(row) for row in session.run(query, status=status)]
