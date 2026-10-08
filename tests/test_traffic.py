import pytest

from app.traffic import effective_segment_state


def test_sums_active_delays_and_ignores_inactive_impacts():
    result = effective_segment_state(
        100,
        [
            {"delay_seconds": 20, "closure": False, "active": True},
            {"delay_seconds": 90, "closure": True, "active": False},
            {"delay_seconds": 5, "closure": False, "active": True},
        ],
    )
    assert result == {"status": "open", "effective_seconds": 125}


def test_closure_overrides_open_state_but_preserves_time_cost():
    result = effective_segment_state(
        40,
        [{"delay_seconds": 10, "closure": True, "active": True}],
    )
    assert result == {"status": "closed", "effective_seconds": 50}


def test_invalid_baseline_or_negative_delay_rejected():
    with pytest.raises(ValueError):
        effective_segment_state(0, [])
    with pytest.raises(ValueError):
        effective_segment_state(10, [{"delay_seconds": -1}])
