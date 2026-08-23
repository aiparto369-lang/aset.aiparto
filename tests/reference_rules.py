from __future__ import annotations

AGGRESSION = {
    "DECISION_BLOCKED": -1,
    "EXIT": 0,
    "AVOID": 0,
    "REDUCE": 1,
    "WAIT": 2,
    "INSUFFICIENT_EDGE": 2,
    "HOLD": 3,
    "TACTICAL_ENTRY": 4,
    "STAGED_ENTRY": 5,
    "ACCUMULATE": 6,
}

def decide(inp: dict) -> dict:
    s = inp["states"]
    c = inp["constraints"]

    # Hard gates
    if s["data_state"] == "BLOCKED":
        return _result(inp, ["DECISION_BLOCKED"], "DECISION_BLOCKED", "ZERO", ["RC-DATA-BLOCK"])
    if c["risk"] == "BLOCK":
        return _result(inp, ["DECISION_BLOCKED"], "DECISION_BLOCKED", "ZERO", ["RC-RISK-BLOCK"])
    if c["portfolio"] == "BLOCK":
        return _result(inp, ["AVOID"], "AVOID", "ZERO", ["RC-PORT-BLOCK"])
    if s["evidence_conflict"] == "CRITICAL":
        return _result(inp, ["DECISION_BLOCKED"], "DECISION_BLOCKED", "ZERO", ["RC-EVIDENCE-CRITICAL"])

    # Explicit uncertainty / review
    if s["data_state"] == "REVIEW_REQUIRED" or s["evidence_conflict"] == "MATERIAL":
        return _result(inp, ["WAIT"], "WAIT", "ZERO", ["RC-REVIEW-REQUIRED"])

    # Risk / portfolio limits
    no_increase = c["portfolio"] in {"NO_INCREASE", "REDUCE"}
    size_limited = c["risk"] in {"SIZE_LIMIT", "ENTRY_LIMIT", "REDUCE_REQUIRED"}

    fx, xau = s["fx_price"], s["xau_price"]
    timing = s["timing"]
    premium = s["gold_premium"]
    stress = s["fx_stress"]

    # Dislocation is not a clean trend
    if fx == "DISLOCATED" or stress == "DISLOCATED":
        if inp.get("existing_position") in {"MODERATE","LARGE"}:
            return _result(inp, ["HOLD","REDUCE","WAIT"], "WAIT", "ZERO", ["RC-FX-DISLOCATED"])
        return _result(inp, ["WAIT"], "WAIT", "ZERO", ["RC-FX-DISLOCATED"])

    # Strongly negative
    if fx == "DOWNTREND" and xau == "DOWNTREND":
        if inp.get("existing_position") in {"SMALL","MODERATE","LARGE"}:
            return _result(inp, ["REDUCE","EXIT"], "REDUCE", "ZERO", ["RC-DIRECTION-NEGATIVE"])
        return _result(inp, ["AVOID","WAIT"], "AVOID", "ZERO", ["RC-DIRECTION-NEGATIVE"])

    # No clear edge
    if fx in {"RANGE","UNKNOWN","TRANSITION"} and xau in {"RANGE","UNKNOWN","TRANSITION"}:
        return _result(inp, ["WAIT","INSUFFICIENT_EDGE"], "INSUFFICIENT_EDGE", "ZERO", ["RC-NO-EDGE"])

    # Mixed directions
    if (fx == "UPTREND" and xau == "DOWNTREND") or (fx == "DOWNTREND" and xau == "UPTREND"):
        if timing in {"SETUP_CONFIRMED","RETESTING","SETUP_FORMING"} and premium != "HIGH":
            preferred = "STAGED_ENTRY"
            if no_increase:
                return _result(inp, ["HOLD","WAIT"], "HOLD", "ZERO", ["RC-PORT-NO-INCREASE"])
            return _result(inp, ["STAGED_ENTRY","TACTICAL_ENTRY","WAIT"], preferred, "SMALL", ["RC-DIRECTION-MIXED"])
        return _result(inp, ["WAIT"], "WAIT", "ZERO", ["RC-DIRECTION-MIXED"])

    # Positive alignment
    if fx == "UPTREND" and xau == "UPTREND":
        if no_increase:
            return _result(inp, ["HOLD","WAIT"], "HOLD", "ZERO", ["RC-PORT-NO-INCREASE"])
        if timing in {"EXTENDED","INVALIDATED","NO_SETUP","UNKNOWN"}:
            return _result(inp, ["WAIT","STAGED_ENTRY"], "WAIT", "PROBE", ["RC-TIMING-CAP"])
        if premium == "HIGH":
            return _result(inp, ["STAGED_ENTRY","WAIT"], "STAGED_ENTRY", "SMALL", ["RC-PREMIUM-HIGH"])
        if c["event"] in {"LIMIT_ENTRY","BLOCK"}:
            return _result(inp, ["WAIT","STAGED_ENTRY"], "WAIT", "PROBE", ["RC-EVENT-LIMIT"])
        if size_limited or s["data_state"] == "READY_LIMITED" or stress in {"ELEVATED","HIGH"}:
            return _result(inp, ["STAGED_ENTRY","WAIT"], "STAGED_ENTRY", "SMALL", ["RC-SIZE-LIMIT"])
        return _result(inp, ["ACCUMULATE","STAGED_ENTRY"], "ACCUMULATE", "MODERATE", [
            "RC-FX-DIRECTION-SUPPORT","RC-XAU-DIRECTION-SUPPORT","RC-PREMIUM-ACCEPTABLE","RC-TIMING-CONFIRMED"
        ])

    # Single positive driver
    if fx == "UPTREND" or xau == "UPTREND":
        if no_increase:
            return _result(inp, ["HOLD","WAIT"], "HOLD", "ZERO", ["RC-PORT-NO-INCREASE"])
        if timing in {"SETUP_CONFIRMED","RETESTING","SETUP_FORMING"} and premium != "HIGH":
            return _result(inp, ["STAGED_ENTRY","WAIT"], "STAGED_ENTRY", "SMALL", ["RC-SINGLE-DRIVER"])
        return _result(inp, ["WAIT"], "WAIT", "ZERO", ["RC-SINGLE-DRIVER"])

    return _result(inp, ["WAIT","INSUFFICIENT_EDGE"], "WAIT", "ZERO", ["RC-DEFAULT-CAUTION"])

def _result(inp, allowed, preferred, size, reasons):
    return {
        "decision_id": inp["decision_id"],
        "allowed_actions": allowed,
        "preferred_action": preferred,
        "size_capability": size,
        "reason_codes": reasons,
        "invalidation": [],
        "review_triggers": [],
        "audit_id": "AUD-" + inp["decision_id"].replace("DEC-","")
    }
