from __future__ import annotations

RECOMPUTE_SEGMENTS_QUERY = (
    "UNWIND $road_ids AS road_id "
    "MATCH (s:RoadSegment {id:road_id}) "
    "OPTIONAL MATCH (i:Incident {status:'confirmed', explicitly_confirmed:true}) "
    "-[impact:AFFECTS {active:true}]->(s) "
    "WITH s, collect(impact) AS impacts "
    "WITH s, impacts, any(x IN impacts WHERE x.closure=true) AS closed, "
    "reduce(total=0, x IN impacts | total + coalesce(x.delay_seconds, 0)) AS delay "
    "SET s.status=CASE WHEN closed THEN 'closed' ELSE 'open' END, "
    "s.effective_seconds=s.baseline_seconds + delay"
)


def recompute_segments(tx, road_ids: list[str]) -> None:
    if road_ids:
        tx.run(RECOMPUTE_SEGMENTS_QUERY, road_ids=sorted(set(road_ids))).consume()


def clear_road_impacts(tx, incident_id: str) -> list[str]:
    roads = tx.run(
        "MATCH (i:Incident {id:$id})-[impact:AFFECTS]->(s:RoadSegment) "
        "RETURN collect(DISTINCT s.id) AS road_ids",
        id=incident_id,
    ).single()["road_ids"]
    tx.run(
        "MATCH (i:Incident {id:$id})-[impact:AFFECTS]->() SET impact.active=false",
        id=incident_id,
    ).consume()
    return roads
