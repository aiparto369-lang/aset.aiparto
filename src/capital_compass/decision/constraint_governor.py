# Ordinal size lattice. Caps must take the MINIMUM of the current and the
# capped size, never assign. Assigning was the root cause of UNKNOWN
# granting a LARGER position than an adverse known state.
SIZE_ORDER = ["ZERO", "PROBE", "SMALL", "MODERATE", "LARGE_ELIGIBLE"]

def size_min(a, b):
    """Return the more conservative of two size capabilities."""
    try:
        return a if SIZE_ORDER.index(a) <= SIZE_ORDER.index(b) else b
    except ValueError:
        return "ZERO"   # unknown size token -> fail closed

def cap(res, allowed, preferred, size, codes):
    """Apply a cap to an existing result: never widen size, never lose reasons."""
    return {**res,
            "allowed_actions": allowed,
            "preferred_action": preferred,
            "size_capability": size_min(res.get("size_capability", "ZERO"), size),
            "reason_codes": list(dict.fromkeys(list(res.get("reason_codes", [])) + codes))}

INCREASING={"ACCUMULATE","STAGED_ENTRY","TACTICAL_ENTRY"}
def _r(inp,a,p,s,rc):
    return {"decision_id":inp["decision_id"],"allowed_actions":a,"preferred_action":p,"size_capability":s,
            "reason_codes":rc,"invalidation":[],"review_triggers":[],
            "audit_id":"AUD-"+inp["decision_id"].replace("DEC-","")}

# Fail-closed UNKNOWN policy.
#
# The stated rule is "UNKNOWN must never create or strengthen conviction".
# Capping alone cannot deliver it: an adverse KNOWN value (risk=BLOCK) exits
# early from pre_direction_gate at ZERO, while UNKNOWN flows through the engine
# and gets capped to PROBE. The two paths never meet, so PROBE > ZERO survives.
#
# The correct invariant is per-dimension: UNKNOWN must be at least as
# conservative as the MOST conservative known value of the same dimension,
# because any of those values might be the true one. That is fail-closed.
#
# Product consequence, stated explicitly: when the user's risk or portfolio
# profile is UNKNOWN the engine will not size a position at all. That is
# intended - it refuses to personalise on absent data, and drives profile
# completion instead of guessing.
UNKNOWN_SIZE_CAP = {
    "risk":         "ZERO",   # worst known: BLOCK -> ZERO
    "portfolio":    "ZERO",   # worst known: BLOCK -> ZERO
    "event":        "ZERO",   # worst known: BLOCK -> ZERO
    "fx_stress":    "ZERO",   # worst known: DISLOCATED -> ZERO
    "gold_premium": "ZERO",   # worst known: HIGH -> ZERO
    "coin_premium": "PROBE",  # worst known: HIGH -> PROBE
    "fx_price":     "ZERO",   # worst known: DISLOCATED -> ZERO
    "xau_price":    "PROBE",  # worst known: EXTENDED_UP -> PROBE
}

def apply_unknown_floor(inp, res):
    """Clamp size to the fail-closed cap for every UNKNOWN dimension."""
    s = inp["states"]; c = inp["constraints"]
    for dim, capsize in UNKNOWN_SIZE_CAP.items():
        val = c.get(dim) if dim in ("risk", "portfolio", "event") else s.get(dim)
        if val == "UNKNOWN":
            res = cap(res, res["allowed_actions"], res["preferred_action"],
                      capsize, [f"RC-{dim.upper().replace('_','-')}-UNKNOWN"])
    return res

def pre_direction_gate(inp):
    s=inp["states"];c=inp["constraints"];pos=inp.get("existing_position","UNKNOWN")
    if s["data_state"]=="BLOCKED":return _r(inp,["DECISION_BLOCKED"],"DECISION_BLOCKED","ZERO",["RC-DATA-BLOCK"])
    if s["evidence_conflict"]=="CRITICAL":return _r(inp,["DECISION_BLOCKED"],"DECISION_BLOCKED","ZERO",["RC-EVIDENCE-CRITICAL"])
    if s["data_state"]=="REVIEW_REQUIRED" or s["evidence_conflict"]=="MATERIAL":return _r(inp,["WAIT"],"WAIT","ZERO",["RC-REVIEW-REQUIRED"])
    if c["portfolio"]=="BLOCK":return _r(inp,["AVOID"],"AVOID","ZERO",["RC-PORT-BLOCK"])
    if c["portfolio"]=="REDUCE":
        return _r(inp,["REDUCE"],"REDUCE","ZERO",["RC-PORT-REDUCE"]) if pos in {"SMALL","MODERATE","LARGE"} else _r(inp,["AVOID","WAIT"],"AVOID","ZERO",["RC-PORT-REDUCE-NO-POSITION"])
    if c["risk"]=="BLOCK":return _r(inp,["DECISION_BLOCKED"],"DECISION_BLOCKED","ZERO",["RC-RISK-BLOCK"])
    if c["risk"]=="REDUCE_REQUIRED":
        return _r(inp,["REDUCE"],"REDUCE","ZERO",["RC-RISK-REDUCE"]) if pos in {"SMALL","MODERATE","LARGE"} else _r(inp,["WAIT"],"WAIT","ZERO",["RC-RISK-REDUCE-NO-POSITION"])
    if c["event"]=="BLOCK":return _r(inp,["HOLD","REDUCE","WAIT"],"WAIT","ZERO",["RC-EVENT-BLOCK"]) if pos in {"SMALL","MODERATE","LARGE"} else _r(inp,["WAIT"],"WAIT","ZERO",["RC-EVENT-BLOCK"])
    return None
def post_direction_cap(inp,res):
    c=inp["constraints"];s=inp["states"];pos=inp.get("existing_position","UNKNOWN")
    if c["portfolio"]=="NO_INCREASE":
        return cap(res,["HOLD","WAIT"],"HOLD","ZERO",["RC-PORT-NO-INCREASE"]) if pos in {"SMALL","MODERATE","LARGE"} else cap(res,["WAIT"],"WAIT","ZERO",["RC-PORT-NO-INCREASE"])
    if c["portfolio"]=="UNKNOWN" or c["risk"]=="UNKNOWN":
        if res["preferred_action"] in INCREASING:
            res=cap(res,["WAIT","STAGED_ENTRY"],"WAIT","PROBE",["RC-CONSTRAINT-UNKNOWN"])
        else:
            res=cap(res,res["allowed_actions"],res["preferred_action"],"PROBE",["RC-CONSTRAINT-UNKNOWN"])
    if c["risk"]=="ENTRY_LIMIT" or c["event"]=="LIMIT_ENTRY":
        if res["preferred_action"] in INCREASING:
            res=cap(res,["WAIT","TACTICAL_ENTRY"],"WAIT","PROBE",["RC-ENTRY-LIMIT"])
        else:
            res=cap(res,res["allowed_actions"],res["preferred_action"],"PROBE",["RC-ENTRY-LIMIT"])
    if c["risk"]=="SIZE_LIMIT" or c["event"] in {"CAUTION","UNKNOWN"}:
        if res["preferred_action"]=="ACCUMULATE":
            res=cap(res,["STAGED_ENTRY","WAIT"],"STAGED_ENTRY","SMALL",["RC-SIZE-LIMIT"])
        else:
            res=cap(res,res["allowed_actions"],res["preferred_action"],"SMALL",["RC-SIZE-LIMIT"])
    if s["data_state"]=="READY_LIMITED" or s["fx_stress"]=="UNKNOWN":
        if res["preferred_action"]=="ACCUMULATE":
            res=cap(res,["STAGED_ENTRY","WAIT"],"STAGED_ENTRY","SMALL",["RC-DATA-OR-STRESS-LIMIT"])
        else:
            res=cap(res,res["allowed_actions"],res["preferred_action"],"SMALL",["RC-DATA-OR-STRESS-LIMIT"])
    for dim,key in (("fx_stress","fx_stress"),("gold_premium","gold_premium"),("coin_premium","coin_premium")):
        pass
    return apply_unknown_floor(inp,res)
