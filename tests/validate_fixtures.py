from pathlib import Path
import json, sys
from jsonschema import Draft202012Validator, RefResolver
from reference_rules import decide

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURES = ROOT / "fixtures" / "golden"

def load(name):
    return json.loads((CONTRACTS/name).read_text(encoding="utf-8"))

schemas = {n: load(n) for n in [
    "evidence.schema.json","snapshot.schema.json","state.schema.json",
    "decision-input.schema.json","decision-result.schema.json","audit-record.schema.json"
]}
store = {s["$id"]: s for s in schemas.values()}
store.update({f"https://capitalcompass.local/schemas/{k}":v for k,v in schemas.items()})

decision_validator = Draft202012Validator(schemas["decision-input.schema.json"])

failures = []
for fp in sorted(FIXTURES.glob("*.json")):
    case = json.loads(fp.read_text(encoding="utf-8"))
    inp = case["input"]
    errs = list(decision_validator.iter_errors(inp))
    if errs:
        failures.append((case["case_id"], "schema", "; ".join(e.message for e in errs)))
        continue

    result = decide(inp)
    exp = case["expected"]

    if "preferred_action" in exp and result["preferred_action"] != exp["preferred_action"]:
        failures.append((case["case_id"], "preferred_action", result["preferred_action"]))
    if "preferred_any" in exp and result["preferred_action"] not in exp["preferred_any"]:
        failures.append((case["case_id"], "preferred_any", result["preferred_action"]))
    if "must_not" in exp:
        bad = exp["must_not"]
        if bad in result.get("allowed_actions", []) or result.get("preferred_action") == bad or result.get("size_capability") == bad:
            failures.append((case["case_id"], "must_not", bad))
    if "allowed_any" in exp and not any(a in result["allowed_actions"] for a in exp["allowed_any"]):
        failures.append((case["case_id"], "allowed_any", result["allowed_actions"]))
    if "max_aggression" in exp:
        # current minimal check: review-required paths must never exceed WAIT
        if exp["max_aggression"] == "WAIT" and result["preferred_action"] not in {"WAIT","INSUFFICIENT_EDGE","AVOID","REDUCE","EXIT","DECISION_BLOCKED","HOLD"}:
            failures.append((case["case_id"], "max_aggression", result["preferred_action"]))

print(f"Validated {len(list(FIXTURES.glob('*.json')))} fixtures")
if failures:
    print(f"FAILURES: {len(failures)}")
    for x in failures:
        print(x)
    sys.exit(1)
print("PASS")
