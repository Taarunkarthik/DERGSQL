from __future__ import annotations

from typing import TYPE_CHECKING

from app.db import open_session
from app.extraction import ExtractedIncident
from app.incidents import ingest_report_in_transaction
from app.location import nearest_road_ids
from app.models import ReportInput
from app.network import list_network

if TYPE_CHECKING:
    from neo4j import Driver


def create_candidate_report(
    driver: Driver,
    *,
    report_id: str,
    source: str,
    raw_text: str,
    extraction: ExtractedIncident,
    radius_m: float,
    confidence_threshold: float,
) -> dict:
    """Resolve extracted location to nearby roads and persist as pending review."""
    if not 0 <= confidence_threshold <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")
    network = list_network(driver)
    road_ids: list[str] = []
    location_method = "textual"
    if extraction.latitude is not None and extraction.longitude is not None:
        road_ids = nearest_road_ids(
            network["intersections"], network["roads"], extraction.latitude,
            extraction.longitude, radius_m,
        )
        location_method = "coordinate-radius"
    else:
        normalized = extraction.location_text.casefold().strip()
        named_intersections = [
            point for point in network["intersections"]
            if point["name"].casefold() == normalized or point["id"].casefold() == normalized
        ]
        if named_intersections:
            ids = {point["id"] for point in named_intersections}
            road_ids = [
                road["id"] for road in network["roads"]
                if road["start_id"] in ids or road["end_id"] in ids
            ]
            location_method = "exact-intersection-name"
    if not road_ids:
        raise ValueError("Could not match report location to any road segment")

    report = ReportInput(
        report_id=report_id,
        source=source,
        raw_text=raw_text,
        location_text=extraction.location_text,
        severity=extraction.severity,
        delay_seconds=extraction.delay_seconds,
        affected_road_ids=road_ids,
        confidence=extraction.confidence,
        closure=extraction.closure,
    )

    def persist(tx) -> dict:
        candidate = ingest_report_in_transaction(tx, report)
        tx.run(
            "MATCH (r:Report {id:$id}) "
            "SET r.incident_type=$incident_type, r.location_method=$location_method, "
            "r.location_radius_m=$radius_m, r.review_required=$review_required "
            "RETURN r.id",
            id=report_id,
            incident_type=extraction.incident_type,
            location_method=location_method,
            radius_m=radius_m,
            review_required=extraction.confidence < confidence_threshold,
        ).consume()
        return candidate

    with open_session(driver) as session:
        candidate = session.execute_write(persist)
    candidate.update(
        {
            "incident_type": extraction.incident_type,
            "location_method": location_method,
            "matched_road_ids": road_ids,
            "review_required": extraction.confidence < confidence_threshold,
            "confidence_threshold": confidence_threshold,
        }
    )
    return candidate


def new_report_id() -> str:
    from uuid import uuid4

    return f"llm-{uuid4()}"
