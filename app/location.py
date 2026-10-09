from __future__ import annotations

from math import cos, hypot, pi


def nearest_road_ids(
    intersections: list[dict], roads: list[dict], latitude: float, longitude: float, radius_m: float
) -> list[str]:
    """Find road segments whose endpoint is within radius of a reported point.

    This intentionally uses a local equirectangular approximation appropriate for
    the small demo networks; production geospatial matching should use road
    geometries and a routing/spatial engine.
    """
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    points = {point["id"]: (point["latitude"], point["longitude"]) for point in intersections}
    matches = []
    cos_lat = cos(latitude * pi / 180)
    for road in roads:
        nearest_m = float("inf")
        for endpoint in (road["start_id"], road["end_id"]):
            if endpoint not in points:
                continue
            point_lat, point_lon = points[endpoint]
            north_m = (point_lat - latitude) * 111_320
            east_m = (point_lon - longitude) * 111_320 * cos_lat
            nearest_m = min(nearest_m, hypot(north_m, east_m))
        if nearest_m <= radius_m:
            matches.append((nearest_m, road["id"]))
    return [road_id for _, road_id in sorted(matches)]
