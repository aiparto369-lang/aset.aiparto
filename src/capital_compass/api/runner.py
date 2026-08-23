"""
Scheduled runner — turns the report from a command into a service.

Responsibilities, in order of how much they matter:

  1. Never publish a bad reading. A run that cannot assemble trustworthy inputs
     writes nothing and keeps the previous good output in place. A dashboard
     showing yesterday's number with yesterday's timestamp is safe; one showing
     a broken number with today's timestamp is not.
  2. Keep a history. Every accepted run is appended to a JSONL ledger, which is
     what later turns into out-of-sample validation — the thing the audit said
     was missing and could only be fixed by time passing. Starting the clock is
     the whole point of running this on a schedule.
  3. Only speak when there is something to say. Telegram delivery fires on a
     material change or on the daily digest, never on every tick.

Runs on the standard library alone: no cron, no APScheduler, no service manager.
"""
from __future__ import annotations

import json
import time
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from capital_compass.api.compass_ui import render as render_compass
from capital_compass.api.dealer_ui import render as render_dealer
from capital_compass.api.daily_report import DEMO_INVENTORY, build_payload
from capital_compass.data.providers.aggregator import clear_cache

# Iran has no DST, so a fixed offset is correct here and a tz database is not
# needed. Getting this wrong shifts every Jalali date near midnight.
TEHRAN = timezone(timedelta(hours=3, minutes=30))

# A run is rejected outright below this. These are integrity gates, not market
# thresholds: each one marks an output we would not stand behind.
MIN_INSTRUMENTS = 3
MIN_COMPASS_CONFIDENCE = 0.4

# Change large enough to be worth interrupting someone for.
ALERT_PREMIUM_MOVE_PP = 1.5      # percentage points of coin premium
ALERT_FX_MOVE_PCT = 0.015        # 1.5% move in the dollar anchor


def _j(o):
    """JSON-safe: dataclasses and anything exotic become plain structures."""
    if is_dataclass(o) and not isinstance(o, type):
        return {k: _j(v) for k, v in asdict(o).items()}
    if isinstance(o, dict):
        return {k: _j(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_j(v) for v in o]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


class RunRejected(RuntimeError):
    pass


def validate(payload: dict, bearing) -> list[str]:
    """Return blocking reasons. Empty list means the run may be published."""
    bad: list[str] = []
    rows = (payload.get("arbitrage") or {}).get("rows") or []
    a = payload.get("anchors") or {}

    if len(rows) < MIN_INSTRUMENTS:
        bad.append(f"only {len(rows)} instruments priced (need {MIN_INSTRUMENTS})")
    if not a.get("xau_usd"):
        bad.append("no global gold anchor")
    if not a.get("usd_irr_used"):
        bad.append("no FX anchor")
    if payload.get("unit_fault"):
        bad.append(f"unit-scale fault: {payload['unit_fault'].get('fault')}")
    if bearing is None:
        bad.append("compass unavailable")
    elif bearing.confidence < MIN_COMPASS_CONFIDENCE:
        bad.append(f"compass confidence {bearing.confidence:.2f} below "
                   f"{MIN_COMPASS_CONFIDENCE}")
    return bad


def _premium_of(payload: dict) -> float | None:
    for r in (payload.get("arbitrage") or {}).get("rows") or []:
        if r["instrument_id"] == "SEKKE_EMAMI":
            return r.get("bubble_pct")
    return None


def material_change(prev: dict | None, payload: dict, bearing) -> tuple[bool, list[str]]:
    """Is this run different enough from the last one to be worth sending?"""
    if prev is None:
        return True, ["اولین گزارش."]
    reasons: list[str] = []

    p0, p1 = prev.get("coin_premium"), _premium_of(payload)
    if p0 is not None and p1 is not None:
        move = (p1 - p0) * 100
        if abs(move) >= ALERT_PREMIUM_MOVE_PP:
            reasons.append(f"حباب سکه {move:+.1f} واحد درصد تغییر کرد.")

    f0 = prev.get("usd_irr")
    f1 = (payload.get("anchors") or {}).get("usd_irr_used")
    if f0 and f1 and abs(f1 - f0) / f0 >= ALERT_FX_MOVE_PCT:
        reasons.append(f"نرخ دلار {(f1 - f0) / f0 * 100:+.1f}٪ تغییر کرد.")

    if bearing and prev.get("quadrant") and bearing.quadrant:
        if list(prev["quadrant"]) != list(bearing.quadrant):
            reasons.append(f"جهت قطب‌نما به «{bearing.label}» تغییر کرد.")

    return bool(reasons), reasons


def run_once(outdir: str | Path = "reports/live",
             ledger: str | Path = "reports/ledger.jsonl") -> dict:
    """One cycle: fetch, validate, publish only if sound, append to the ledger."""
    started = time.time()
    out, led = Path(outdir), Path(ledger)
    out.mkdir(parents=True, exist_ok=True)
    led.parent.mkdir(parents=True, exist_ok=True)

    clear_cache()
    payload = build_payload()
    bearing = payload.pop("_bearing", None)

    blocking = validate(payload, bearing)
    now = datetime.now(timezone.utc)
    entry = {
        "at": now.isoformat(),
        "at_tehran": now.astimezone(TEHRAN).strftime("%Y-%m-%d %H:%M"),
        "elapsed_s": round(time.time() - started, 1),
        "accepted": not blocking,
        "blocking": blocking,
        "faults": payload.get("faults") or [],
    }

    if blocking:
        # Explicitly leave the previous output untouched.
        entry["note"] = "run rejected; previous published output left in place"
        with led.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        raise RunRejected("; ".join(blocking))

    a = payload["anchors"]
    entry.update({
        "xau_usd": a.get("xau_usd"),
        "usd_irr": a.get("usd_irr_used"),
        "usd_irr_cash": a.get("usd_irr_cash"),
        "tether_premium_pct": a.get("tether_premium_pct"),
        "coin_premium": _premium_of(payload),
        "quadrant": list(bearing.quadrant) if bearing.quadrant else None,
        "label": bearing.label,
        "angle_deg": bearing.angle_deg,
        "confidence": bearing.confidence,
    })

    prev = last_accepted(led)
    changed, reasons = material_change(prev, payload, bearing)
    entry["material_change"] = changed
    entry["change_reasons"] = reasons

    # Both surfaces are rendered from the SAME payload. Rendering them from
    # separate fetches let the shared XAU x USD anchor move between them, which
    # showed up as a uniform ~0.24% disagreement on every instrument's melt
    # value - harmless-looking, and exactly the kind of drift a dealer would
    # rightly not trust.
    (out / "report.html").write_text(
        render_compass(payload, bearing, dealer_inventory=DEMO_INVENTORY),
        encoding="utf-8")

    median_prem = None
    try:
        ws = (bearing.premium_axis.raw or {}).get("window_sensitivity") or {}
        w = (ws.get("windows") or {}).get("720")
        median_prem = w.get("median") if w else None
    except Exception:  # noqa: BLE001
        median_prem = None
    (out / "dealer.html").write_text(
        render_dealer(payload, historical_median_premium=median_prem),
        encoding="utf-8")
    doc = _j(payload)
    doc["compass"] = _j(bearing)
    (out / "report.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    with led.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def last_accepted(ledger: str | Path) -> dict | None:
    p = Path(ledger)
    if not p.exists():
        return None
    best = None
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("accepted"):
            best = r
    return best


def history(ledger: str | Path, limit: int = 500) -> list[dict]:
    p = Path(ledger)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("accepted"):
            rows.append(r)
    return rows[-limit:]


def loop(interval_min: int = 30, outdir: str = "reports/live",
         ledger: str = "reports/ledger.jsonl", *, max_cycles: int | None = None,
         notify=None) -> None:
    """
    Run forever on an interval.

    A failed cycle is logged and slept through rather than crashing the service:
    one dead venue must not end the schedule.
    """
    n = 0
    while max_cycles is None or n < max_cycles:
        n += 1
        stamp = datetime.now(TEHRAN).strftime("%H:%M")
        try:
            e = run_once(outdir, ledger)
            flag = "★" if e["material_change"] else " "
            print(f"[{stamp}] {flag} ok  {e['label']}  "
                  f"حباب={e['coin_premium'] * 100:+.2f}%  "
                  f"دلار={e['usd_irr'] / 10:,.0f}T  ({e['elapsed_s']}s)")
            if notify and e["material_change"]:
                notify(e)
        except RunRejected as ex:
            print(f"[{stamp}] ✗ rejected: {ex}")
        except Exception:  # noqa: BLE001 - the schedule must survive anything
            print(f"[{stamp}] ! error:\n{traceback.format_exc()}")
        if max_cycles is None or n < max_cycles:
            time.sleep(interval_min * 60)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Capital Compass scheduled runner")
    ap.add_argument("--once", action="store_true", help="single cycle then exit")
    ap.add_argument("--interval", type=int, default=30, help="minutes")
    ap.add_argument("--cycles", type=int, default=None)
    ap.add_argument("--outdir", default="reports/live")
    ap.add_argument("--ledger", default="reports/ledger.jsonl")
    ap.add_argument("--telegram", action="store_true",
                    help="send alerts (needs CC_TELEGRAM_TOKEN and CC_TELEGRAM_CHAT)")
    args = ap.parse_args()

    notify = None
    if args.telegram:
        from capital_compass.api.telegram import notifier
        notify = notifier()

    if args.once:
        try:
            e = run_once(args.outdir, args.ledger)
            print(json.dumps(e, ensure_ascii=False, indent=2))
            if notify and e["material_change"]:
                notify(e)
        except RunRejected as ex:
            print(f"REJECTED: {ex}")
            raise SystemExit(2)
    else:
        loop(args.interval, args.outdir, args.ledger,
             max_cycles=args.cycles, notify=notify)


if __name__ == "__main__":
    main()
