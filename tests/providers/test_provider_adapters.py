import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))

from capital_compass.data.providers.base import ProviderDisabled, ProviderContractError
from capital_compass.data.providers.alpha_vantage import AlphaVantageGoldProvider
from capital_compass.data.providers.metals_api import MetalsApiGoldProvider
from capital_compass.data.ingestion.manual_fx_routes import ingest_manual_fx

def run():
    # Disabled-by-default is a governance requirement.
    try:
        AlphaVantageGoldProvider(api_key="x", enabled=False).fetch_xauusd()
        raise AssertionError("Alpha provider must be disabled by default")
    except ProviderDisabled:
        pass

    try:
        MetalsApiGoldProvider(api_key="x", enabled=False).fetch_xauusd()
        raise AssertionError("Metals provider must be disabled by default")
    except ProviderDisabled:
        pass

    # Contract parsing tests use mocked provider payloads only.
    with patch("capital_compass.data.providers.alpha_vantage.get_json") as g:
        g.return_value = {"symbol":"XAU","spot_price":"2500.25"}
        q = AlphaVantageGoldProvider(api_key="x", enabled=True).fetch_xauusd()
        assert len(q) == 1
        assert abs(q[0].value - 2500.25) < 1e-9
        assert q[0].unit == "USD_PER_TROY_OUNCE"

    with patch("capital_compass.data.providers.metals_api.get_json") as g:
        g.return_value = {"success":True, "rates":{"XAU-BID":1/2499.0, "XAU-ASK":1/2501.0}}
        q = MetalsApiGoldProvider(api_key="x", enabled=True).fetch_xauusd()
        assert len(q) == 2
        vals = {x.quote_type:x.value for x in q}
        assert abs(vals["BID"] - 2499.0) < 1e-6
        assert abs(vals["ASK"] - 2501.0) < 1e-6

    ev = ingest_manual_fx("IRAN-FX-MANUAL-TGJU", {
        "variable_id":"USD_IRR_FREE_MARKET",
        "raw_value":100000,
        "raw_unit":"TOMAN_PER_USD",
        "quote_type":"REFERENCE",
        "observation_time":"2026-08-22T10:00:00+00:00",
        "source_origin":"manual:tgju:test",
        "market":"IRAN_FREE_MARKET",
        "asset":"USD_IRR"
    }, "EV-FX-MANUAL-001")
    assert ev["source"]["source_id"] == "SRC-TGJU"
    assert ev["value"] == 1000000.0

    print("Provider adapter tests PASS")

if __name__ == "__main__":
    run()
