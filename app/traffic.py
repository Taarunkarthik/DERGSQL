from collections.abc import Iterable


def effective_segment_state(
    baseline_seconds: float, impacts: Iterable[dict]
) -> dict[str, float | str]:
    """Combine currently active impacts using the MVP's additive-delay policy.

    Duplicate reports must be deduplicated into a single Incident before they
    reach this function. Any active closure marks the segment closed; delays
    from all active incidents are summed, including on closed segments so the
    cost remains explainable if a closure is cleared.
    """
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
