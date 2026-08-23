from __future__ import annotations

ORDERED_ACTIONS = {
    "DECISION_BLOCKED":0,
    "EXIT":0,
    "AVOID":0,
    "REDUCE":1,
    "WAIT":2,
    "INSUFFICIENT_EDGE":2,
    "HOLD":3,
    "TACTICAL_ENTRY":4,
    "STAGED_ENTRY":5,
    "ACCUMULATE":6,
}

def assert_monotonic_nonincrease(old_result: dict, new_result: dict, *, dimension: str):
    """
    Used for metamorphic tests:
    worse data/risk/portfolio/event conditions must never increase aggression.
    """
    a=ORDERED_ACTIONS[old_result["preferred_action"]]
    b=ORDERED_ACTIONS[new_result["preferred_action"]]
    if b > a:
        raise AssertionError(
            f"{dimension} deterioration increased aggressiveness: "
            f"{old_result['preferred_action']} -> {new_result['preferred_action']}"
        )
