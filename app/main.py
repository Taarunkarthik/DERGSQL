from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.audit import report_audit
from app.db import create_driver, initialize_schema, seed_network
from app.incidents import (
    confirm_report,
    ingest_report,
    list_incidents,
    reject_report,
    resolve_report,
)
from app.models import NetworkSeed, ReportInput, RouteRequest
from app.network import get_segment, list_network
from app.routing import find_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.driver = create_driver()
    try:
        initialize_schema(app.state.driver)
        yield
    finally:
        app.state.driver.close()


app = FastAPI(
    title="DERGSQL Emergency Routing API",
    description="A database-backed MVP for incident-aware emergency routing.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    try:
        with app.state.driver.session() as session:
            session.run("RETURN 1").consume()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.post("/network/seed")
def network_seed(payload: NetworkSeed):
    known = {point.id for point in payload.intersections}
    if len(known) != len(payload.intersections):
        raise HTTPException(status_code=422, detail="Intersection IDs must be unique")
    road_ids = [road.id for road in payload.roads]
    if len(set(road_ids)) != len(road_ids):
        raise HTTPException(status_code=422, detail="Road IDs must be unique")
    if any(road.start_id not in known or road.end_id not in known for road in payload.roads):
        raise HTTPException(status_code=422, detail="Every road endpoint must be in the seed payload")
    seed_network(
        app.state.driver,
        [item.model_dump() for item in payload.intersections],
        [item.model_dump() for item in payload.roads],
    )
    return {"intersections": len(known), "roads": len(payload.roads), "status": "seeded"}


@app.get("/network")
def network():
    return list_network(app.state.driver)


@app.get("/roads/{road_id}")
def road(road_id: str):
    try:
        return get_segment(app.state.driver, road_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/reports", status_code=201)
def create_report(payload: ReportInput):
    try:
        return ingest_report(app.state.driver, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/reports/{report_id}/confirm")
def confirm(report_id: str):
    try:
        return confirm_report(app.state.driver, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/reports/{report_id}/reject")
def reject(report_id: str):
    try:
        return reject_report(app.state.driver, report_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message.startswith("Report not found") else 409
        raise HTTPException(status_code=status_code, detail=message) from exc


@app.post("/reports/{report_id}/resolve")
def resolve(report_id: str):
    try:
        return resolve_report(app.state.driver, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/reports/{report_id}/audit")
def report_history(report_id: str):
    try:
        return report_audit(app.state.driver, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/incidents")
def incidents(status: str | None = None):
    return list_incidents(app.state.driver, status)


@app.post("/routes")
def route(payload: RouteRequest):
    try:
        return find_route(
            app.state.driver,
            payload.origin_id,
            payload.destination_id,
            payload.vehicle_type,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
