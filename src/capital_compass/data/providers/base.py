from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ProviderQuote:
    provider: str
    variable_id: str
    value: float
    unit: str
    quote_type: str
    observation_time: str
    retrieval_time: str
    source_origin: str

class ProviderDisabled(RuntimeError):
    pass

class ProviderContractError(RuntimeError):
    pass

class MarketProvider(Protocol):
    provider_name: str
    def fetch_xauusd(self) -> list[ProviderQuote]:
        ...
