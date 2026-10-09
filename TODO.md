# DERGSQL Implementation Checklist

## MVP implementation

- [x] Python package layout, dependency manifest, configuration, and safe local environment defaults.
- [x] Neo4j schema constraints and idempotent sample-network seeding.
- [x] Request/response models for network seeding, reports, structured extraction, and routes.
- [x] Report intake with provenance and review state; only confirmed reports affect routing.
- [x] Structured extractor intake for LLM-produced JSON candidates.
- [x] Coordinate-radius and exact-intersection-name road matching.
- [x] Transactional segment impacts with baseline costs preserved, closure handling, and incident resolution.
- [x] Deterministic vehicle-aware Dijkstra routing over eligible directed road segments.
- [x] Network inspection, nearby-roads, report audit, incident list, confirm/reject/resolve, and route endpoints.
- [x] Docker Compose, `.env.example`, `.gitignore`, and sample network data.
- [x] Unit and API tests for routing, validation, extraction, matching, incident lifecycle, audit, and recomputation.
- [x] Optional live Neo4j integration test gated by `DERGSQL_NEO4J_INTEGRATION=1`.
- [x] README with setup, run, test, and safety limitations.

## Verification / handoff

- [x] Run automated tests available in the environment.
- [x] Compile Python modules.
- [x] Run `git diff --check`.
- [x] Confirm secrets and local `.env` are not committed.
- [x] Tell the maintainer when changes are ready to push; do not push without explicit instruction.

## Remaining beyond educational MVP

- [ ] Add authentication and roles for operators/admins.
- [ ] Replace simple endpoint matching with real road geometry/geocoder integration.
- [ ] Add actual trusted incident-feed ingestion.
- [ ] Add monitoring, backups, and deployment hardening.
- [ ] Perform operational safety validation before any real dispatch use.
