from __future__ import annotations
import json
from pathlib import Path

class PreflightBlocked(RuntimeError):
    pass

def load_provider_selection(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def check_xau_activation(selection: dict, provider: str, *, rights_ack: bool, technical_ready: bool):
    if provider not in {"ALPHA_VANTAGE","METALS_API"}:
        raise PreflightBlocked("unsupported provider")
    if not rights_ack:
        raise PreflightBlocked("provider rights/licensing acknowledgement missing")
    if not technical_ready:
        raise PreflightBlocked("provider not technically ready")
    return True
