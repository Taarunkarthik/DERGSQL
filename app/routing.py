from __future__ import annotations

import heapq
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver


def shortest_path(edges: list[dict], origin_id: str, destination_id: str) -> dict:
    """Compute a minimum-travel-time route over directed, nonnegative edges."""
    adjacency: dict[str, list[tuple[str, float, str]]] = {}
    for edge in edges:
        if edge["status"] == "closed":
            continue
        cost = float(edge["effective_seconds"])
        if cost < 0:
            raise ValueError("Dijkstra routing requires nonnegative edge weights")
        adjacency.setdefault(edge["start_id"], []).append((edge["end_id"], cost, edge["id"]))

    distances = {origin_id: 0.0}
    previous: dict[str, tuple[str, str]] = {}
    queue = [(0.0, origin_id)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node == destination_id:
            break
        for neighbor, weight, road_id in adjacency.get(node, []):
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = (node, road_id)
                heapq.heappush(queue, (candidate, neighbor))

    if destination_id not in distances:
        raise LookupError("No open route exists between the requested intersections")

    nodes = [destination_id]
    roads = []
    current = destination_id
    while current != origin_id:
        parent, road_id = previous[current]
        roads.append(road_id)
        nodes.append(parent)
        current = parent
    return {
        "intersections": list(reversed(nodes)),
        "road_ids": list(reversed(roads)),
        "estimated_seconds": distances[destination_id],
        "calculated_at": datetime.now(timezone.utc),
    }


def find_route(driver: Driver, origin_id: str, destination_id: str) -> dict:
    with driver.session() as session:
        rows = session.run(
            "MATCH (a:Intersection)-[:ROAD_TO]->(r:RoadSegment)-[:ROAD_TO]->(b:Intersection) "
            "RETURN a.id AS start_id, b.id AS end_id, r.id AS id, "
            "r.effective_seconds AS effective_seconds, r.status AS status"
        )
        edges = [dict(row) for row in rows]
        version = session.run(
            "MATCH (s:RoadSegment) RETURN count(s) AS count, "
            "coalesce(sum(s.effective_seconds), 0) AS cost_sum"
        ).single()
    route = shortest_path(edges, origin_id, destination_id)
    route["traffic_version"] = int(version["count"] + version["cost_sum"])
    return route
