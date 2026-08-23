import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
schema = json.loads((ROOT/"contracts"/"source-registry.schema.json").read_text(encoding="utf-8"))
data = json.loads((ROOT/"config"/"sources.json").read_text(encoding="utf-8"))

errors = list(Draft202012Validator(schema).iter_errors(data))
if errors:
    for e in errors:
        print(e.message)
    raise SystemExit(1)
print("Source registry schema PASS")
