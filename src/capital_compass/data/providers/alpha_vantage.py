from __future__ import annotations
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from .base import ProviderQuote, ProviderDisabled, ProviderContractError
from .http import get_json

class AlphaVantageGoldProvider:
    provider_name = "ALPHA_VANTAGE"
    base_url = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str | None = None, enabled: bool | None = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if enabled is None:
            enabled = os.getenv("CC_ENABLE_ALPHA_VANTAGE","false").lower() == "true"
        self.enabled = enabled

    def fetch_xauusd(self) -> list[ProviderQuote]:
        if not self.enabled:
            raise ProviderDisabled(
                "Alpha Vantage adapter is disabled until API key and commercial/data-use rights are confirmed."
            )
        if not self.api_key:
            raise ProviderDisabled("ALPHAVANTAGE_API_KEY is missing.")

        url = self.base_url + "?" + urlencode({
            "function":"GOLD_SILVER_SPOT",
            "symbol":"XAU",
            "apikey":self.api_key
        })
        data = get_json(url)
        now = datetime.now(timezone.utc).isoformat()

        # Provider response formats can evolve. We only accept explicit numeric fields;
        # unknown shapes fail closed rather than guessing.
        candidates = []
        def walk(obj, prefix=""):
            if isinstance(obj, dict):
                for k,v in obj.items():
                    lk = k.lower()
                    if isinstance(v,(int,float)):
                        candidates.append((k,float(v)))
                    elif isinstance(v,str):
                        try:
                            fv=float(v)
                            candidates.append((k,fv))
                        except ValueError:
                            pass
                    elif isinstance(v,(dict,list)):
                        walk(v, prefix+k+".")
            elif isinstance(obj,list):
                for v in obj:
                    walk(v,prefix)
        walk(data)

        # Prefer fields whose names explicitly suggest price.
        explicit = [(k,v) for k,v in candidates if "price" in k.lower() or "spot" in k.lower()]
        if len(explicit) != 1:
            raise ProviderContractError(
                f"Alpha Vantage response shape is not safely recognized; explicit price candidates={explicit}"
            )
        _, price = explicit[0]
        if price <= 0:
            raise ProviderContractError("Non-positive XAU price.")

        return [ProviderQuote(
            provider=self.provider_name,
            variable_id="XAUUSD",
            value=price,
            unit="USD_PER_TROY_OUNCE",
            quote_type="LAST",
            observation_time=now,
            retrieval_time=now,
            source_origin="alpha-vantage:GOLD_SILVER_SPOT:XAU"
        )]
