from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

from capital_compass.data.providers.alpha_vantage import AlphaVantageGoldProvider
from capital_compass.data.providers.metals_api import MetalsApiGoldProvider
from capital_compass.data.ingestion.provider_to_evidence import quote_to_evidence
from capital_compass.data.snapshot.builder import build_snapshot

def choose_provider(name: str):
    if name == "alpha":
        return AlphaVantageGoldProvider()
    if name == "metals":
        return MetalsApiGoldProvider()
    raise ValueError(name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xau-provider", choices=["alpha","metals"], required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    provider = choose_provider(args.xau_provider)
    quotes = provider.fetch_xauusd()
    evid = [
        quote_to_evidence(q, f"EV-LIVE-XAU-{i+1:03d}")
        for i,q in enumerate(quotes)
    ]

    as_of = datetime.now(timezone.utc).isoformat()
    snap, h = build_snapshot(
        snapshot_id="SNAP-LIVE-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        as_of=as_of,
        evidence_by_bucket={"xauusd":evid},
        iran_session="UNKNOWN",
        xau_session="OPEN"
    )
    out = Path(args.output)
    out.write_text(json.dumps({"snapshot":snap,"sha256":h}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
