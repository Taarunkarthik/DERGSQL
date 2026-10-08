# DERGSQL Implementation Checklist

## MVP implementation

- [x] Create Python package layout, dependency manifest, configuration, and safe local environment defaults.
- [x] Define request/response models for intersections, road segments, reports, incident review, resolution, and route requests.
- [x] Implement Neo4j schema constraints and idempotent sample-network seeding.
- [x] Implement report intake with provenance and review state; only confirmed reports affect routing.
- [x] Implement transactional segment impacts with baseline costs preserved, closure handling, and incident resolution.
- [x] Implement deterministic Dijkstra routing over eligible directed road segments.
- [x] Expose FastAPI health, network bootstrap, report, confirm, resolve, incident listing, and route endpoints.
- [x] Add Docker Compose for local Neo4j, `.env.example`, and `.gitignore`.
- [x] Add unit tests for routing and validation; database integration testing remains a follow-up.
- [x] Update README with local run, seed, and test instructions; keep safety limitations clear.

## Verification / handoff

- [ ] Run automated tests and lint checks available in the environment.
- [ ] Review Git diff and ensure secrets and local state are excluded.
- [ ] Tell the maintainer when changes are ready to push; do not push without explicit instruction.
