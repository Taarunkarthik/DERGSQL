from collections.abc import Iterable


def effective_segment_state(baseline_seconds: float, impacts: Iterable[dict]) -> dict[str, float | str]:
    """Recompute a segment using active incident impacts and baseline cost."""
    if baseline_seconds <= 0:
        raise ValueError("baseline travel time must be positive")
    active = [impact for impact in impacts if impact.get("active", True)]
    delays = [float(impact.get("delay_seconds", 0)) for impact in active]
    if any(delay < 0 for delay in delays):
        raise ValueError("incident delays cannot be negative")
    return {
        "status": "closed" if any(impact.get("closure", False) for impact in active) else "open",
        "effective_seconds": baseline_seconds + sum(delays),
    }
