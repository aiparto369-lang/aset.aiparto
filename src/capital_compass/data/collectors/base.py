from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Protocol, Optional

@dataclass(frozen=True)
class RawObservation:
    variable_id: str
    raw_value: float | str
    raw_unit: str
    quote_type: str | None
    observation_time: str
    retrieval_time: str
    source_id: str
    source_origin: str
    market: str
    asset: str
    note: str | None = None

class Collector(Protocol):
    source_id: str
    def collect(self) -> list[RawObservation]:
        ...

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
