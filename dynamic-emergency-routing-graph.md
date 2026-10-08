# Dynamic Emergency Routing Graph

## Project Overview

**Dynamic Emergency Routing Graph** is a database-centered system for maintaining a current, queryable model of a city's road network and emergency-related traffic conditions. It helps dispatchers identify suitable routes for ambulances and other response vehicles as road conditions change.

The project is primarily a **DBMS application**: its main responsibilities are road-network data modeling, incident ingestion and validation, maintaining time-sensitive traffic state, preserving an audit trail, and serving reliable route-query inputs. Dijkstra's algorithm is used as a routing operation over the current graph; it is an important feature, but not the project's primary contribution.

## Problem Statement

Emergency routing depends on data that changes quickly. Accidents, lane closures, construction, flooding, and temporary restrictions can make a route that was previously fast unsafe or slow. Incident reports may arrive as unstructured radio transcripts, operator notes, or other permitted feeds. A useful system must convert those reports into structured, reviewable records and apply their effects consistently to the road network.

A routing algorithm alone does not solve this data-management problem. The system needs a dependable database that knows which roads are affected, when the information was received, how reliable it is, and when its effect should expire or be cleared.

## Goals

- Store a normalized, connected representation of intersections and road segments.
- Record incidents and their evidence, location, severity, status, and time range.
- Associate each incident with affected road segments and maintain their current traffic state.
- Calculate and expose route results using current, eligible edge costs.
- Support auditability, freshness checks, and recovery from incorrect or stale updates.
- Make the database schema, transactions, constraints, and queries central to the project.

## System Components

### 1. Road-network database

Represent the city as a directed graph persisted in a graph database such as Neo4j, or in a relational database with graph/spatial capabilities. The graph can contain:

- **Intersection nodes:** stable ID, name or code, geographic coordinates, and optional administrative area.
- **Road-segment relationships/edges:** stable ID, direction, endpoints, road class, baseline travel time, length, current travel-time estimate, and operational status.
- **Restrictions:** closures, vehicle restrictions, access conditions, and validity periods.

A road segment should have a stable identity independent of a particular incident. This allows multiple incidents or data sources to affect the same segment without losing the underlying network record.

### 2. Incident and report records

Store each received report as a first-class database record rather than applying an untraceable direct weight change. Suggested fields include:

- Incident ID and source/report ID
- Raw report text or a protected reference to it
- Parsed location, incident type, severity, and reported delay
- Received time, event time (if known), and last-updated time
- Extraction confidence and evidence text
- Review/verification status and operator decision
- Incident status (reported, confirmed, resolved, rejected, or expired)
- Affected road-segment IDs and the method used to match them
- Valid-from and valid-until timestamps

Keeping the report, extraction, verification, and road impact separate makes updates explainable and reversible.

### 3. LLM-assisted incident intake

An LLM can transform authorized unstructured reports—such as dispatcher notes or permitted radio-transcript feeds—into a proposed structure, for example:

```json
{
  "incident_type": "collision",
  "location_text": "Outer Ring Road, near Junction 12",
  "severity": "high",
  "lanes_blocked": 2,
  "delay_minutes": 18,
  "reported_at": "2026-10-06T21:23:00+05:30",
  "evidence": "Accident on Outer Ring Road, two lanes blocked",
  "confidence": 0.87
}
```

This output is a candidate record, not authoritative truth. The intake service should validate the schema, resolve the location to one or more road segments, retain provenance, and request human review when confidence or location precision is insufficient. The system should avoid treating social-media posts as verified incidents without corroboration. Privacy, retention, and source-use rules should be considered for all feeds.

### 4. Database update and route-query service

After validation, a transactional update records the incident and its impact on affected segments. The route service reads a consistent snapshot of eligible road costs and runs Dijkstra's shortest-path algorithm (or a graph database's supported path procedure) to find the minimum-cost path between a dispatch location and destination.

The algorithm consumes database state; it does not replace the database's duties to enforce valid data, resolve conflicting reports, manage expiry, or provide a consistent view of traffic conditions.

## Database Design and State Management

A robust design distinguishes **baseline cost**, **reported impacts**, and **effective current cost**:

- `baseline_travel_time`: normal expected time for a segment.
- Incident impact records: reported delay, closure, severity, source, confidence, and validity interval.
- `effective_travel_time`: derived or materialized value used for routing, computed from active impacts according to documented rules.
- `status`: open, restricted, or closed, with vehicle-specific applicability where needed.

Do not blindly add every reported delay to an edge. Reports may describe the same event, overlap, conflict, or be outdated. Define a policy for corroboration, deduplication, severity precedence, confidence, and how multiple impacts combine. Store enough source data to recompute the effective cost if that policy changes.

### Example logical entities

| Entity | Purpose | Example attributes |
|---|---|---|
| `Intersection` | Network junction | ID, name, latitude, longitude |
| `RoadSegment` | Directed traversable segment | ID, from-node, to-node, length, baseline time, direction |
| `Incident` | Real-world event | ID, type, severity, status, reported/event times |
| `Report` | Source-specific observation | ID, incident ID, source, raw text/reference, confidence, received time |
| `SegmentImpact` | Link between incident and affected edge | incident ID, segment ID, delay, closure state, validity interval |
| `RouteRequest` | Reproducible dispatch query | origin, destination, vehicle type, requested time |
| `RouteResult` | Result and snapshot metadata | path segment IDs, total cost, calculated time, graph version/time |

The exact implementation can use Neo4j nodes and relationships, or relational tables with foreign keys and spatial indexing. The important requirement is to preserve integrity and traceable relationships between reports, incidents, impacted segments, and route results.

## Database Operations

The project can demonstrate core DBMS concepts through the following operations:

1. **Ingestion:** validate and persist a report with its source and timestamps.
2. **Entity resolution:** match textual locations to network geometry and candidate segments.
3. **Transaction:** create or update an incident and all affected segment impacts atomically.
4. **Conflict handling:** deduplicate reports and prevent stale updates from overwriting newer verified state.
5. **Derived state:** calculate effective travel costs from active, accepted impacts.
6. **Expiry and recovery:** expire temporary impacts, resolve incidents, and restore baseline conditions without losing history.
7. **Query:** retrieve nearby active incidents, affected segments, current segment status, and a route under explicit constraints.
8. **Audit:** reproduce why a segment had a given cost and which data snapshot informed a route.

## Routing and Dijkstra's Algorithm

For a route request, intersections are vertices and traversable road segments are weighted edges. The weight can be travel time, provided all active edge weights are nonnegative. Dijkstra's algorithm then finds a minimum-total-weight path. A route query should also account for vehicle restrictions, closed segments, and the time at which the network state is evaluated.

The result should include more than a list of intersections. Store or return the road-segment sequence, total estimated time, calculation timestamp, and traffic-state/version identifier. This makes the result explainable and enables later comparison with actual travel outcomes.

## Example Database Questions

- Which active, verified incidents affect segments within a specified area?
- Which segments are currently closed to ambulances?
- What is the latest accepted impact for a given road segment?
- Which reports contributed to a segment's effective travel-time estimate?
- Which route minimizes estimated travel time for a vehicle at a specified time?
- How did the route change after a particular incident was confirmed or cleared?
- Which active impacts have not been refreshed within the configured freshness window?

## Reliability, Safety, and Evaluation

Because emergency decisions are safety-critical, the prototype should clearly identify estimated or unverified data and should not be presented as an autonomous dispatch authority. Include operator oversight, fallback behavior when data is unavailable, and safeguards against confidently routing through a closure. Protect sensitive location and operational data with access controls and appropriate retention limits.

Useful evaluation measures include:

- Correctness of incident-to-segment matching
- Time from report receipt to validated database update
- Freshness and expiry correctness of traffic state
- Route computation latency and route validity under restrictions
- Difference between estimated and observed journey time
- Audit completeness: ability to explain the data behind a route

## Suggested MVP

Build a small, clearly bounded road network and a database-backed workflow with:

1. Intersections and directed road segments with baseline travel times.
2. Incident/report records with evidence, timestamps, confidence, and review status.
3. A manual review step to confirm incident-to-segment mapping.
4. Transactional creation and resolution of segment impacts.
5. Expiry of temporary incidents and restoration of baseline state.
6. A route endpoint or query that runs Dijkstra over the current eligible graph.
7. An audit view showing which active records produced each route's edge costs.

This scope demonstrates database design, integrity, transactions, temporal state, graph queries, and provenance before expanding into live feeds or city-scale routing.

## Summary

Dynamic Emergency Routing Graph is best framed as a **real-time graph data management system for emergency routing**. The LLM assists with turning messy incident reports into proposed structured records; the database validates, relates, timestamps, and applies those records to a persistent road network; Dijkstra's algorithm uses the resulting graph state to calculate a fast route. The core project value lies in maintaining reliable, explainable, up-to-date data—not merely implementing a shortest-path algorithm.
