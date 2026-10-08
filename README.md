# DERGSQL — Dynamic Emergency Routing Graph

> **Project status:** Concept and design documentation. This repository does not yet contain an implemented application. The instructions below describe a practical MVP implementation path; commands should be run from the repository root as the project is built.

## What it will do

DERGSQL is a database-centered emergency routing system. It stores a city's intersections and directed road segments, records incident reports and their provenance, updates time-bounded traffic impacts, and calculates routes against a consistent current network state. Dijkstra's algorithm is the routing operation; reliable graph data management is the core project focus.

The LLM-assisted intake is optional for the first milestone. Reports should be validated and reviewed before they affect operational routing. This prototype is not an autonomous dispatch authority.

## Proposed MVP stack

- **Graph DB:** Neo4j Community Edition
- **Application/API:** Python 3.11+ and FastAPI
- **Neo4j driver:** `neo4j` Python package
- **Input validation:** Pydantic models
- **Tests:** pytest
- **Optional LLM intake:** provider-independent extraction adapter that returns schema-validated candidate JSON; keep it disabled until deterministic ingestion and review workflows work.

A relational/PostGIS implementation is also possible, but this guide uses Neo4j to align with the graph model.

## Prerequisites

Install:

1. Git
2. Python 3.11 or newer
3. Docker Desktop with Docker Compose

Verify in a terminal:

```powershell
git --version
python --version
docker --version
docker compose version
```

## Build the project from scratch

### 1. Create the application layout

```text
DERGSQL/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── incidents.py
│   └── routing.py
├── data/
│   └── sample-network.json
├── tests/
│   ├── test_incidents.py
│   └── test_routing.py
├── .env.example
├── .gitignore
├── compose.yaml
├── pyproject.toml
└── README.md
```

### 2. Start Neo4j

Create `compose.yaml`:

```yaml
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/change-this-password
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p change-this-password 'RETURN 1' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
volumes:
  neo4j_data:
```

For local development only, create `.env` with a strong local password and configure Compose to read it; never commit secrets. Start the database:

```powershell
docker compose up -d
```

Neo4j Browser is available at `http://localhost:7474`; Bolt is at `bolt://localhost:7687`.

### 3. Set up Python dependencies

Create a virtual environment and install the application dependencies (`fastapi`, `uvicorn[standard]`, `neo4j`, `pydantic`, and `pydantic-settings`) plus development dependencies (`pytest`, `httpx`, and `ruff`). Record pinned or bounded versions in `pyproject.toml`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install fastapi "uvicorn[standard]" neo4j pydantic pydantic-settings pytest httpx ruff
```

Create `.env.example` with placeholders (not real credentials):

```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=replace-me
```

Copy it to `.env`, set the same local database credentials, and ensure `.env` and `.venv/` are ignored by Git.

### 4. Model and seed the road graph

Use stable IDs and explicit relationship direction. A minimal model is:

- `(:Intersection {id, name, latitude, longitude})`
- `(:Intersection)-[:ROAD_SEGMENT {id, baseline_seconds, effective_seconds, length_m, status, valid_from, valid_until}]->(:Intersection)`
- `(:Incident {id, type, severity, status, reported_at, expires_at})`
- `(:Report {id, source, received_at, raw_text, confidence, review_status})`
- `(Report)-[:DESCRIBES]->(Incident)`
- `(Incident)-[:AFFECTS {delay_seconds, closure, valid_from, valid_until}]->(RoadSegment)` or an equivalent separately modeled segment entity

Create uniqueness constraints for stable IDs before loading data. Seed a small sample network (a few intersections and alternate paths), then verify that all segment endpoints exist and costs are nonnegative. Keep baseline values separate from incident impacts so that resolving an incident can restore the correct state.

### 5. Implement incident ingestion and state updates

Define request schemas for reports and incidents. Validate required fields, timestamps, units, supported severity values, and confidence ranges. Preserve raw source text or a secure source reference, extraction evidence, and review status.

Implement a transactional workflow that:

1. Saves the report and candidate incident with provenance.
2. Resolves the reported location to candidate road segments.
3. Requires review when location matching or extraction confidence is ambiguous.
4. Records accepted, time-bounded impacts without destroying baseline data.
5. Recomputes effective segment costs using a documented policy for overlapping, duplicate, stale, or conflicting reports.
6. Expires or clears impacts and records who/what changed the state.

Do not let an unverified LLM response directly close a road or trigger a dispatch decision. Make updates idempotent so a retried report does not create duplicate impacts.

### 6. Implement routing

For the MVP, route over open directed segments using nonnegative `effective_seconds` weights. Dijkstra finds the minimum estimated travel-time path. Exclude closed or vehicle-ineligible segments. Return the ordered segment IDs, total estimated time, calculation time, and a graph/traffic-state version so a result is explainable and reproducible.

Use a small, deterministic sample graph to test routes, including a case where the fastest route changes after an incident and a case where a closure forces an alternate path. Keep routing logic separate from database access so it can be unit-tested independently.

### 7. Add API endpoints

A minimal API can expose:

- `GET /health` — API and database health.
- `POST /reports` — submit a report for validation/review.
- `POST /incidents/{id}/confirm` — accept an incident and apply impacts.
- `POST /incidents/{id}/resolve` — resolve and clear active impacts.
- `GET /incidents?status=active` — list current incidents.
- `POST /routes` — request a route for origin, destination, vehicle type, and optional departure time.

Document request/response schemas and return explicit validation errors. Add authentication and authorization before exposing anything beyond a local demo.

### 8. Test and run locally

Start Neo4j, activate the virtual environment, then run:

```powershell
pytest -q
ruff check .
uvicorn app.main:app --reload
```

Open the interactive API docs at `http://127.0.0.1:8000/docs`. Include integration tests against a disposable/test database for constraints, transactional updates, expiry, and route behavior; unit tests should cover parsing, validation, and Dijkstra edge cases.

### 9. Evaluate and harden

Before expanding the scope, verify:

- Incident-to-road matching is correct on the sample map.
- Duplicate reports do not double-count delays.
- Expired/resolved incidents no longer affect routes.
- Concurrent or stale updates cannot overwrite newer verified state.
- Route costs are nonnegative and closures/restrictions are respected.
- Every route can be traced to the traffic snapshot and active reports that informed it.
- Credentials, supplier/source data, and operational data are protected; secrets are never committed.

For a real deployment, use trusted incident feeds, human operational oversight, monitoring, backups, access controls, retention policies, and tested fallback behavior. Validate routing against authoritative road and traffic data before any real-world use.

## Suggested implementation milestones

1. **Database foundation:** schema, constraints, sample network, connectivity check.
2. **Incident lifecycle:** reports, review, segment impacts, expiry, audit history.
3. **Routing:** Dijkstra against current eligible edge costs and reproducible results.
4. **API and tests:** endpoints, validation, integration tests, API documentation.
5. **Assisted extraction:** optional LLM adapter, structured output validation, evidence capture, review queue.
6. **Operational readiness:** security, monitoring, real data integration, load and safety evaluation.

## Existing design document

See [dynamic-emergency-routing-graph.md](dynamic-emergency-routing-graph.md) for the concept, database design rationale, example data entities, and project scope.
