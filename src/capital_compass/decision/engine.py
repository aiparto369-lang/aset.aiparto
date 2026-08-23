from capital_compass.decision.constraint_governor import pre_direction_gate,post_direction_cap,apply_unknown_floor
def _r(inp,a,p,s,rc):
    return {"decision_id":inp["decision_id"],"allowed_actions":a,"preferred_action":p,"size_capability":s,
            "reason_codes":rc,"invalidation":[],"review_triggers":[],
            "audit_id":"AUD-"+inp["decision_id"].replace("DEC-","")}
def decide(inp):
    g=pre_direction_gate(inp)
    if g is not None:return apply_unknown_floor(inp,g)
    s=inp["states"];fx=s["fx_price"];x=s["xau_price"];t=s["timing"];gp=s["gold_premium"];cp=s["coin_premium"];st=s["fx_stress"]
    if fx=="DISLOCATED" or st=="DISLOCATED":return post_direction_cap(inp,_r(inp,["WAIT","HOLD","REDUCE"],"WAIT","ZERO",["RC-FX-DISLOCATED"]))
    if fx=="DOWNTREND" and x in {"DOWNTREND","EXTENDED_DOWN"}:
        b=_r(inp,["REDUCE","EXIT"],"REDUCE","ZERO",["RC-DIRECTION-NEGATIVE"]) if inp.get("existing_position") in {"SMALL","MODERATE","LARGE"} else _r(inp,["AVOID","WAIT"],"AVOID","ZERO",["RC-DIRECTION-NEGATIVE"])
        return post_direction_cap(inp,b)
    if fx in {"RANGE","TRANSITION","UNKNOWN"} and x in {"RANGE","TRANSITION","UNKNOWN"}:
        return post_direction_cap(inp,_r(inp,["WAIT","INSUFFICIENT_EDGE"],"INSUFFICIENT_EDGE","ZERO",["RC-NO-EDGE"]))
    if (fx=="UPTREND" and x in {"DOWNTREND","EXTENDED_DOWN"}) or (fx=="DOWNTREND" and x in {"UPTREND","EXTENDED_UP"}):
        b=_r(inp,["STAGED_ENTRY","TACTICAL_ENTRY","WAIT"],"STAGED_ENTRY","SMALL",["RC-DIRECTION-MIXED"]) if t in {"SETUP_CONFIRMED","RETESTING","SETUP_FORMING"} and gp!="HIGH" else _r(inp,["WAIT"],"WAIT","ZERO",["RC-DIRECTION-MIXED"])
        return post_direction_cap(inp,b)
    if fx=="UPTREND" and x in {"UPTREND","EXTENDED_UP"}:
        if inp["instrument"]=="EMAMI_COIN" and cp=="HIGH":b=_r(inp,["WAIT","STAGED_ENTRY"],"WAIT","PROBE",["RC-COIN-PREMIUM-HIGH"])
        elif t in {"EXTENDED","INVALIDATED","NO_SETUP","UNKNOWN"} or x=="EXTENDED_UP":b=_r(inp,["WAIT","STAGED_ENTRY"],"WAIT","PROBE",["RC-TIMING-CAP"])
        elif gp=="HIGH":b=_r(inp,["STAGED_ENTRY","WAIT"],"STAGED_ENTRY","SMALL",["RC-PREMIUM-HIGH"])
        elif st in {"ELEVATED","HIGH"}:b=_r(inp,["STAGED_ENTRY","WAIT"],"STAGED_ENTRY","SMALL",["RC-STRESS-LIMIT"])
        else:b=_r(inp,["ACCUMULATE","STAGED_ENTRY"],"ACCUMULATE","MODERATE",["RC-FX-DIRECTION-SUPPORT","RC-XAU-DIRECTION-SUPPORT"]+(["RC-PREMIUM-ACCEPTABLE"] if gp in {"LOW","NORMAL"} else ["RC-PREMIUM-UNKNOWN"])+(["RC-TIMING-CONFIRMED"] if t=="SETUP_CONFIRMED" else ["RC-TIMING-"+t.replace("_","-")]))
        return post_direction_cap(inp,b)
    if fx=="UPTREND" or x in {"UPTREND","EXTENDED_UP"}:
        b=_r(inp,["STAGED_ENTRY","WAIT"],"STAGED_ENTRY","SMALL",["RC-SINGLE-DRIVER"]) if t in {"SETUP_CONFIRMED","RETESTING","SETUP_FORMING"} and gp!="HIGH" else _r(inp,["WAIT"],"WAIT","ZERO",["RC-SINGLE-DRIVER"])
        return post_direction_cap(inp,b)
    return post_direction_cap(inp,_r(inp,["WAIT","INSUFFICIENT_EDGE"],"WAIT","ZERO",["RC-DEFAULT-CAUTION"]))
