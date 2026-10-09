# DERGSQL — Dynamic Emergency Routing Graph

DERGSQL is a database-centered educational MVP for dynamic emergency routing. It stores a directed city road graph in Neo4j, stages unstructured/LLM-extracted incident reports for human review, applies confirmed traffic impacts transactionally, and computes Dijkstra routes over the current graph state.

> Safety note: this is a learning/demo project. It is not validated for real emergency dispatch, does not authenticate operators, and should not be used to route actual emergency vehicles.

## Current features

- Neo4j schema constraints for intersections, road segments, reports, and incidents.
- Idempotent sample-network seeding.
- Network inspection endpoints for the full graph, individual roads, and nearby roads.
- Manual report intake with provenance and review status.
- Structured extractor intake for caller-supplied LLM JSON; extracted reports remain pending until confirmed.
- Coordinate-radius and exact-intersection-name matching to candidate road segments.
- Confirm/reject/resolve incident lifecycle.
- Transactional recomputation of segment status and effective travel time.
- Vehicle-aware Dijkstra routing for `ambulance`, `fire`, `police`, and `general` vehicles.
- Route responses include a stable traffic snapshot fingerprint.
- Audit endpoint showing source text, extraction metadata, proposed roads, and active impacted roads.
- Unit/API tests plus optional live Neo4j integration tests.

## Stack

- Python 3.11+
- FastAPI
- Neo4j Community Edition
- Pydantic / pydantic-settings
- pytest

## Setup

```powershell
cd "C:\Users\HP\OneDrive\Documents\deepseek-harness\default-workspace\DERGSQL"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create `.env` from `.env.example` and set a local Neo4j password:

```powershell
Copy-Item .env.example .env
```

## Start Neo4j

Docker Desktop is required for the provided Compose file:

```powershell
docker compose up -d
```

Neo4j Browser: `http://localhost:7474`

Bolt URI: `bolt://localhost:7687`

If Docker is not installed, start a Neo4j 5 instance manually and set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` in `.env`.

## Run the API

```powershell
uvicorn app.main:app --reload
```

Open the API docs at `http://127.0.0.1:8000/docs`.

## Demo workflow

1. Seed the graph with `POST /network/seed` using `data/sample-network.json`.
2. Inspect the graph with `GET /network` or `GET /roads/{road_id}`.
3. Optionally find nearby candidate roads with `GET /roads/nearby?latitude=...&longitude=...&radius_m=...`.
4. Create a pending report with either:
   - `POST /reports` for manually structured reports, or
   - `POST /reports/extract` for validated structured LLM/extractor output.
5. Review provenance with `GET /reports/{report_id}/audit`.
6. Apply the incident with `POST /reports/{report_id}/confirm`.
7. Request a route using `POST /routes`:

```json
{
  "origin_id": "A",
  "destination_id": "D",
  "vehicle_type": "ambulance"
}
```

8. Resolve the incident with `POST /reports/{report_id}/resolve` and rerun routing.

## Structured extraction payload

`POST /reports/extract` accepts already-produced structured JSON. It does not scrape sources or call an LLM by itself.

```json
{
  "report_id": "report-outer-ring-1",
  "source": "operator-note",
  "raw_text": "Accident near Central Station, two lanes blocked",
  "radius_m": 1000,
  "confidence_threshold": 0.6,
  "extraction": {
    "incident_type": "collision",
    "location_text": "Central Station",
    "severity": "high",
    "delay_seconds": 600,
    "closure": false,
    "confidence": 0.82,
    "latitude": 12.9716,
    "longitude": 77.5946
  }
}
```

Low-confidence extraction is marked `review_required`; it is still only a pending candidate until confirmed.

## Testing

Run the standard test suite:

```powershell
pytest -q -p no:cacheprovider
```

Optional live Neo4j integration test:

```powershell
$env:DERGSQL_NEO4J_INTEGRATION="1"
pytest tests/test_neo4j_integration.py -q -p no:cacheprovider
```

The integration test needs a running Neo4j instance configured through `.env`.

## Important limitations

- No authentication/authorization yet.
- No real social-media/radio feed ingestion.
- No external geocoder or full road-geometry map matching.
- No live traffic provider integration.
- No operational safety certification.

The project demonstrates DBMS design, transactional graph updates, provenance, review workflow, and route computation for a classroom/demo setting.
