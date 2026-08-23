def validate_decision_result(r):
    if not r.get("allowed_actions"):raise ValueError("allowed_actions empty")
    if r.get("preferred_action") not in r["allowed_actions"]:raise ValueError("preferred_action must be allowed")
    return True
