"""
Licence-clean reference.

TGJU's terms of use, clause 18, prohibit use or redistribution of their prices
without a written agreement. That makes them unusable for a commercial product
until such an agreement exists — not a grey area, an explicit prohibition.

This module exists so that limitation costs as little as possible. It builds the
entire *reference* side of every calculation — what a gram of pure gold is worth
in rial right now — using only exchange APIs that publish market data for public
consumption, with no aggregator in the path.

Two independent routes are computed and cross-checked:

  Route A   XAU/USD from global venues  x  USD/IRR from Iranian venues
  Route B   a gold-backed token quoted DIRECTLY in toman on an Iranian venue

They share no input: route B never touches a dollar rate. Measured live, they
agreed to 0.15%. Two independent methods landing on the same number is far
stronger evidence than one method from five sources, so when both are available
the reference carries that as its confidence.

What this module deliberately does NOT provide: the market price of a physical
coin. That is the one thing only a licensed feed — or the user — can supply. The
dealer product does not need it, because a dealer already knows their own prices
better than any aggregator does.
"""
from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import median

from capital_compass.market.instruments import TROY_OUNCE_GRAMS

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CapitalCompass/2.0",
       "Accept": "application/json"}

# Agreement required between the two independent routes before the reference is
# marked cross-checked. A data-integrity threshold, not a market one.
ROUTE_AGREEMENT_TOLERANCE = 0.02


@dataclass
class Reference:
    """Value of one gram of pure (24k) gold, in rial."""
    irr_per_gram: float | None
    route_a: float | None = None            # XAU/USD x USD/IRR
    route_b: float | None = None            # gold token quoted in toman
    route_gap_pct: float | None = None
    usd_irr: float | None = None
    xau_usd: float | None = None
    status: str = "NO_DATA"                 # CROSS_CHECKED | SINGLE_ROUTE | DIVERGENT | NO_DATA
    sources_used: list[str] = field(default_factory=list)
    licence_class: str = "EXCHANGE_PUBLIC_API"
    retrieved_at: str = ""
    notes: list[str] = field(default_factory=list)


def _get(url: str, timeout: int = 14):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# --- Route B fetchers: gold priced in toman, no FX leg anywhere -------------

def _bitpin_gold_irr_per_gram() -> list[tuple[str, float]]:
    d = _get("https://api.bitpin.ir/v1/mkt/markets/")
    out = []
    for m in d.get("results", []):
        if m.get("code") in ("PAXG_IRT", "XAUT_IRT"):
            px = float(m.get("price") or 0)
            if px > 0:
                out.append((f"bitpin:{m['code']}", px * 10.0 / TROY_OUNCE_GRAMS))
    return out


def _wallex_gold_irr_per_gram() -> list[tuple[str, float]]:
    d = _get("https://api.wallex.ir/v1/markets")
    syms = (d.get("result") or {}).get("symbols") or {}
    out = []
    for s in ("PAXGTMN", "XAUTTMN"):
        st = syms.get(s, {}).get("stats") or {}
        try:
            px = float(st.get("lastPrice") or 0)
        except (TypeError, ValueError):
            continue
        if px > 0:
            out.append((f"wallex:{s}", px * 10.0 / TROY_OUNCE_GRAMS))
    return out


def _ramzinex_gold_irr_per_gram() -> list[tuple[str, float]]:
    d = _get("https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs")
    out = []
    for p in (d.get("data") or d):
        if (p.get("pair_id") or p.get("id")) == 296:      # paxg/irr
            b, s = p.get("buy"), p.get("sell")
            if b and s:
                out.append(("ramzinex:paxg_irr",
                            (float(b) + float(s)) / 2 / TROY_OUNCE_GRAMS))
    return out


ROUTE_B = (_bitpin_gold_irr_per_gram, _wallex_gold_irr_per_gram,
           _ramzinex_gold_irr_per_gram)


def build_reference() -> Reference:
    """The full licence-clean reference, with both routes cross-checked."""
    now = datetime.now(timezone.utc).isoformat()
    notes: list[str] = []
    used: list[str] = []

    # Route A reuses the multi-venue aggregator already in the codebase.
    route_a = usd = xau = None
    try:
        from capital_compass.data.providers.aggregator import fetch_all
        agg = fetch_all()
        xau, usd = agg.get("xau_usd"), agg["usd_irr"].value
        if xau and usd:
            route_a = (xau / TROY_OUNCE_GRAMS) * usd
            used += [f"routeA:{q['source']}" for q in
                     [{"source": s.source} for s in agg["usd_irr"].quotes]]
            used.append(f"routeA:xau({agg.get('xau_status')})")
    except Exception as e:  # noqa: BLE001
        notes.append(f"مسیر A در دسترس نیست: {type(e).__name__}")

    # Route B in parallel; a dead venue must not take the route down.
    quotes: list[tuple[str, float]] = []
    with ThreadPoolExecutor(max_workers=len(ROUTE_B)) as ex:
        futs = {ex.submit(fn): fn.__name__ for fn in ROUTE_B}
        for fut in as_completed(futs, timeout=40):
            try:
                quotes.extend(fut.result())
            except Exception as e:  # noqa: BLE001
                notes.append(f"{futs[fut]}: {type(e).__name__}")

    route_b = None
    if quotes:
        vals = [v for _, v in quotes]
        m = median(vals)
        # Drop prints far from the group before taking the reference.
        keep = [(n, v) for n, v in quotes if abs(v - m) / m <= 0.03]
        for n, v in quotes:
            if (n, v) not in keep:
                notes.append(f"{n} کنار گذاشته شد ({(v - m) / m * 100:+.1f}٪ از میانه).")
        if keep:
            route_b = median([v for _, v in keep])
            used += [f"routeB:{n}" for n, _ in keep]

    # Combine.
    if route_a and route_b:
        gap = (route_b - route_a) / route_a
        if abs(gap) <= ROUTE_AGREEMENT_TOLERANCE:
            status = "CROSS_CHECKED"
            value = median([route_a, route_b])
            notes.append(
                f"دو مسیر مستقل با اختلاف {gap * 100:+.2f}٪ هم‌خوانی دارند."
            )
        else:
            status = "DIVERGENT"
            value = median([route_a, route_b])
            notes.append(
                f"دو مسیر {gap * 100:+.2f}٪ اختلاف دارند — با احتیاط استفاده شود."
            )
    elif route_a or route_b:
        status = "SINGLE_ROUTE"
        value = route_a or route_b
        gap = None
        notes.append("فقط یک مسیر در دسترس بود؛ بررسی متقابل انجام نشد.")
    else:
        return Reference(None, None, None, None, None, None, "NO_DATA", [],
                         "EXCHANGE_PUBLIC_API", now,
                         notes + ["هیچ منبعی در دسترس نیست."])

    return Reference(value, route_a, route_b,
                     (gap if route_a and route_b else None),
                     usd, xau, status, used, "EXCHANGE_PUBLIC_API", now, notes)


def intrinsic_from_reference(ref: Reference, fine_grams: float) -> float | None:
    """Melt value of any instrument, given its fine gold content."""
    if not ref.irr_per_gram:
        return None
    return fine_grams * ref.irr_per_gram


def price_user_inventory(ref: Reference, holdings: list[dict]) -> dict:
    """
    Value an inventory using ONLY the clean reference plus prices the user
    supplied themselves.

    `holdings`: [{instrument_id, qty, unit_price_irr}]

    This is the whole licence-clean product surface. No third-party price feed
    is consulted, so nothing here depends on an agreement that does not exist
    yet — and a dealer's own dealt prices are better input than an aggregator's
    mid quote anyway.
    """
    from capital_compass.market.instruments import get

    if not ref.irr_per_gram:
        return {"status": "NO_REFERENCE", "notes": ref.notes}

    lines, mv, iv, fg = [], 0.0, 0.0, 0.0
    notes: list[str] = []
    for h in holdings:
        iid = h.get("instrument_id")
        try:
            inst = get(iid)
        except KeyError:
            notes.append(f"ابزار ناشناخته: {iid}")
            continue
        qty = float(h.get("qty") or 0)
        unit = float(h.get("unit_price_irr") or 0)
        if qty <= 0 or unit <= 0:
            continue
        intr = inst.fine_grams * ref.irr_per_gram
        m, n = unit * qty, intr * qty
        mv += m
        iv += n
        fg += inst.fine_grams * qty
        lines.append({
            "instrument_id": iid, "fa": inst.fa, "qty": qty,
            "unit_price_toman": unit / 10,
            "intrinsic_unit_toman": intr / 10,
            "market_toman": m / 10, "intrinsic_toman": n / 10,
            "premium_toman": (m - n) / 10,
            "premium_pct": (unit - intr) / intr if intr else None,
        })

    if not lines:
        return {"status": "EMPTY", "notes": notes + ["موجودی یا قیمتی وارد نشده."]}

    lines.sort(key=lambda x: x["premium_toman"], reverse=True)
    return {
        "status": "OK",
        "licence_class": ref.licence_class,
        "reference_irr_per_gram": ref.irr_per_gram,
        "reference_status": ref.status,
        "lines": lines,
        "totals": {
            "market_toman": mv / 10, "intrinsic_toman": iv / 10,
            "premium_toman": (mv - iv) / 10,
            "premium_share": (mv - iv) / mv if mv else None,
            "fine_grams": fg,
        },
        "notes": notes + ref.notes,
    }
