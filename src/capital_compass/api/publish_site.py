"""
Build the whole public site into one directory.

Called by CI. Its contract is narrow and strict: either it produces a complete,
internally consistent site, or it changes nothing and exits non-zero. A partial
site — a fresh landing page next to yesterday's compass — is worse than a stale
one, because the timestamps disagree and a reader cannot tell which number to
trust.

Two build modes, chosen by what data is actually licensed:

  full    Uses the licensed feed. Both compass axes read, the premium percentile
          has its history, and the public compass is meaningful.
  clean   Uses only exchange public APIs. The premium axis reports itself as
          unread, the needle shortens accordingly, and the dealer console — the
          part that earns — is fully functional.

Clean is the default, because shipping something we have the right to ship beats
shipping something better that we do not.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from capital_compass.api.compass_ui import render as render_compass
from capital_compass.api.dealer_clean import render as render_dealer_clean
from capital_compass.api.landing import render as render_landing
from capital_compass.data.providers.clean_reference import build_reference
from capital_compass.market.compass import read_compass


class BuildFailed(RuntimeError):
    pass


def build_clean(outdir: Path, *, site_url: str = "") -> dict:
    """Licence-clean build: exchange APIs only, no aggregator anywhere."""
    ref = build_reference()
    if not ref.irr_per_gram:
        raise BuildFailed("no gold reference available: " + "; ".join(ref.notes))

    # In clean mode the compass reads "نامشخص", and that is left alone on
    # purpose. The FX axis is a spread — tether against a cash rate — and there
    # is no licence-clean cash source, so there is nothing to measure against.
    #
    # There IS a clean signal waiting here: the gap between route A
    # (XAU/USD x USD/IRR) and route B (gold quoted directly in toman) is local
    # pressure on gold, computed entirely from exchange APIs. It is not used
    # yet because a gap of -0.4% means nothing without a baseline, and asserting
    # a threshold we have not measured is the exact defect this project was
    # audited for.
    #
    # The runner writes every route gap to reports/ledger.jsonl. Once that has a
    # few weeks of readings, this axis can be turned on with a real percentile
    # behind it — the same way the premium axis earned its own. Until then the
    # needle stays at the centre and says so.
    bearing = read_compass(
        tether_irr=ref.usd_irr, cash_irr=None, implied_irr=None,
        current_premium=None, premium_history=[],
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "2.1.0",
        "build_mode": "clean",
        "licence_class": ref.licence_class,
        "anchors": {
            "xau_usd": ref.xau_usd,
            "xau_source": "multi-venue median",
            "xau_status": ref.status,
            "xau_divergence_pct": ref.route_gap_pct,
            "usd_irr_crypto": ref.usd_irr,
            "usd_irr_cash": None,
            "usd_irr_used": ref.usd_irr,
            "anchor_kind": "EXCHANGE_LIVE",
            "usdt_spread_bps": None,
            "tether_premium_pct": None,
            "same_instant_legs": True,
        },
        "reference_irr_per_gram": ref.irr_per_gram,
        "reference_status": ref.status,
        # Logged every run so the clean stress axis can be calibrated later.
        "reference_routes": {"a": ref.route_a, "b": ref.route_b,
                             "gap_pct": ref.route_gap_pct},
        "sources_used": ref.sources_used,
        "arbitrage": {"rows": [], "faults": [], "reference_pure_gram_irr": ref.irr_per_gram},
        "consistency": {"status": "NOT_APPLICABLE", "notes": []},
        "unit_fault": None,
        "breakeven_usd_irr_at_zero_bubble": {},
        "faults": ref.notes,
        "disclaimer": (
            "این ابزار تحلیل ارزش نسبی بر پایه داده عمومی بازار است و توصیه "
            "سرمایه‌گذاری نیست."
        ),
    }

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "dealer.html").write_text(
        render_dealer_clean(ref), encoding="utf-8")
    (outdir / "index.html").write_text(
        # Clean mode ships no compass page. Pointing the hero CTA at /compass
        # sent the reader back to the page they were already on.
        render_landing(payload, dealer_example=None,
                       compass_url="/dealer", dealer_url="/dealer",
                       contact="از طریق همین صفحه یا تماس مستقیم."),
        encoding="utf-8")
    (outdir / "report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"mode": "clean", "reference": ref.irr_per_gram,
            "reference_status": ref.status, "compass_label": bearing.label,
            "compass_confidence": bearing.confidence,
            "files": sorted(p.name for p in outdir.iterdir() if p.is_file())}


def build_full(outdir: Path) -> dict:
    """Licensed build: requires a feed we have the right to use."""
    from capital_compass.api.daily_report import DEMO_INVENTORY, build_payload

    payload = build_payload()
    bearing = payload.pop("_bearing", None)
    rows = (payload.get("arbitrage") or {}).get("rows") or []
    if bearing is None or len(rows) < 3:
        raise BuildFailed(
            f"full build incomplete: {len(rows)} instruments, "
            f"compass={'ok' if bearing else 'missing'}"
        )

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "compass.html").write_text(
        render_compass(payload, bearing, dealer_inventory=DEMO_INVENTORY),
        encoding="utf-8")
    (outdir / "report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    return {"mode": "full", "instruments": len(rows),
            "compass_label": bearing.label,
            "compass_confidence": bearing.confidence}


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the public site")
    ap.add_argument("--outdir", default="public")
    ap.add_argument("--mode", choices=["clean", "full"], default="clean")
    ap.add_argument("--site-url", default="")
    args = ap.parse_args()

    out = Path(args.outdir)
    # Build into a staging dir and swap, so a failure never leaves a half-written
    # site being served.
    staging = out.with_name(out.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)

    try:
        info = (build_clean(staging, site_url=args.site_url)
                if args.mode == "clean" else build_full(staging))
    except BuildFailed as e:
        if staging.exists():
            shutil.rmtree(staging)
        print(f"BUILD REJECTED: {e}", file=sys.stderr)
        raise SystemExit(2)

    # Cloudflare config is SOURCE, kept in site/, and copied into every build.
    # It used to live in public/ and be preserved across rebuilds, which meant a
    # build from a clean tree shipped with no CSP and no security headers at all
    # — silently, because the site still rendered fine.
    site_cfg = Path("site")
    missing = []
    for name in ("_headers", "_redirects"):
        src = site_cfg / name
        if src.exists():
            shutil.copy2(src, staging / name)
        else:
            missing.append(name)
    if missing:
        shutil.rmtree(staging, ignore_errors=True)
        print(f"BUILD REJECTED: missing site config: {missing}", file=sys.stderr)
        raise SystemExit(2)

    if out.exists():
        shutil.rmtree(out)
    staging.rename(out)

    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
