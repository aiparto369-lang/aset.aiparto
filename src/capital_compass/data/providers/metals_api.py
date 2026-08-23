from __future__ import annotations
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from .base import ProviderQuote, ProviderDisabled, ProviderContractError
from .http import get_json

class MetalsApiGoldProvider:
    provider_name = "METALS_API"
    base_url = "https://api.metals-api.com/api/latest"

    def __init__(self, api_key: str | None = None, enabled: bool | None = None):
        self.api_key = api_key or os.getenv("METALS_API_KEY")
        if enabled is None:
            enabled = os.getenv("CC_ENABLE_METALS_API","false").lower() == "true"
        self.enabled = enabled

    def fetch_xauusd(self) -> list[ProviderQuote]:
        if not self.enabled:
            raise ProviderDisabled(
                "Metals-API adapter is disabled until paid-plan/data-rights/product-use review is confirmed."
            )
        if not self.api_key:
            raise ProviderDisabled("METALS_API_KEY is missing.")

        # Bid/ask endpoint documented as XAU-BID,XAU-ASK under latest.
        url = self.base_url + "?" + urlencode({
            "access_key":self.api_key,
            "base":"USD",
            "symbols":"XAU-BID,XAU-ASK"
        })
        data = get_json(url)
        now = datetime.now(timezone.utc).isoformat()

        if not data.get("success", True):
            raise ProviderContractError(f"Metals-API returned success=false: {data}")

        rates = data.get("rates")
        if not isinstance(rates, dict):
            raise ProviderContractError("Metals-API response missing rates object.")

        out = []
        for symbol, quote_type in [("XAU-BID","BID"),("XAU-ASK","ASK")]:
            raw = rates.get(symbol)
            if raw is None:
                continue
            try:
                raw = float(raw)
            except Exception as e:
                raise ProviderContractError(f"Non-numeric {symbol}: {raw}") from e
            if raw <= 0:
                raise ProviderContractError(f"Non-positive {symbol}")

            # Metals-API documents rates relative to USD; for XAU with USD base,
            # USD/oz is obtained by inverse of the returned XAU-per-USD rate.
            usd_per_oz = 1.0 / raw
            out.append(ProviderQuote(
                provider=self.provider_name,
                variable_id="XAUUSD",
                value=usd_per_oz,
                unit="USD_PER_TROY_OUNCE",
                quote_type=quote_type,
                observation_time=now,
                retrieval_time=now,
                source_origin=f"metals-api:latest:{symbol}"
            ))

        if not out:
            raise ProviderContractError("No XAU-BID/XAU-ASK values returned.")
        return out
