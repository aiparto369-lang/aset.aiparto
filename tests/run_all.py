from pathlib import Path
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
TESTS = [
    "tests/validate_fixtures.py",
    "tests/classification/test_classifier.py",
    "tests/data_pipeline/test_source_registry.py",
    "tests/data_pipeline/test_pipeline.py",
    "tests/providers/test_provider_adapters.py",
    "tests/end_to_end/test_pilot_e2e.py",
    "tests/live_pilot/test_real_pilot_001.py",
    "tests/live_pilot/test_pilot_series_002_010.py",
    "tests/labeling/test_labeling_pipeline.py",
    "tests/labeling/test_blind_context_window.py",
    "tests/validation/test_step10_validation.py",
    "tests/market_structure/test_step11.py",
    "tests/step12/test_hostile_fixes.py",
    "tests/release/test_release_readiness.py",
]

for rel in TESTS:
    p = subprocess.run([sys.executable, str(ROOT / rel)], cwd=ROOT, env=ENV, text=True, capture_output=True)
    if p.returncode:
        print(f"FAIL: {rel}\n{p.stdout}\n{p.stderr}")
        raise SystemExit(p.returncode)
    print(p.stdout.strip() or f"PASS: {rel}")
print(f"ALL TESTS PASS ({len(TESTS)})")
