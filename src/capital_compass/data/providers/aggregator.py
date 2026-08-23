"""
Multi-source aggregation.

One source is a single point of failure that reports no error when it fails —
it just returns a stale number confidently. That already happened here: Wallex's
PAXG print sat ~3% away from spot, and with one source there was no way to know
whether gold had moved or the print was old. Probing five venues answered it in
one call: PAXG trades near 4590 and XAUT near 4581 across Kraken, Gate, Bitpin
and Ramzinex alike, so the ~0.2% PAXG/XAUT basis is real and the 3% was stale.

Hence the rules here:

  * Median, never mean. One stale print cannot drag a median.
  * Group before combining. PAXG and XAUT are different instruments with a
    genuine basis between them; averaging across that basis would invent a
    number that no venue quotes.
  * Outliers are reported, not silently dropped. A venue that disagrees is
    evidence about that venue.
  * A single surviving source is labelled as such. It is still usable, but the
    caller must be able to see that nothing cross-checked it.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import median

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CapitalCompass/2.0",
       "Accept": "application/json"}

# Deviation from the group median beyond which a quote is flagged as an outlier
# and excluded from the consensus. Wide on purpose: this catches stale prints and
# broken parses, not ordinary venue spread. It is a data-integrity threshold, not
# a market threshold.
OUTLIER_TOLERANCE = 0.015


@dataclass
class SourceQuote:
    source: str
    asset: str            # "USD_IRR" | "PAXG" | "XAUT"
    value: float          # IRR per USD, or USD per troy ounce
    bid: float | None = None
    ask: float | None = None
    retrieved_at: str = ""
    ok: bool = True
    error: str | None = None

    @property
    def spread_bps(self) -> float | None:
        if self.bid and self.ask and self.ask >= self.bid:
            return (self.ask - self.bid) / ((self.ask + self.bid) / 2) * 10_000
        return None


@dataclass
class Consensus:
    asset: str
    value: float | None
    n_sources: int
    n_outliers: int
    dispersion_pct: float | None
    quotes: list[SourceQuote] = field(default_factory=list)
    outliers: list[SourceQuote] = field(default_factory=list)
    status: str = "OK"          # OK | SINGLE_SOURCE | NO_DATA
    notes: list[str] = field(default_factory=list)


# Several venues expose one fat endpoint that carries every market, and we read
# two assets from some of them. Without a per-run cache the same 385-symbol
# payload gets pulled twice, which was most of a 14s round.
_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 20.0
_CACHE_LOCK = threading.Lock()


def _get(url: str, timeout: int = 12):
    now = time.time()
    with _CACHE_LOCK:
        hit = _CACHE.get(url)
        if hit and now - hit[0] < _CACHE_TTL:
            return hit[1]
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    with _CACHE_LOCK:
        _CACHE[url] = (now, data)
    return data


def clear_cache() -> None:
    """Drop cached payloads — call between scheduled runs."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Fetchers. Each returns a SourceQuote or raises; failures are captured by the
# runner so one dead venue never takes the batch down.
# --------------------------------------------------------------------------

def _wallex(symbol: str, asset: str, mul: float = 1.0) -> SourceQuote:
    d = _get("https://api.wallex.ir/v1/markets")
    st = ((d.get("result") or {}).get("symbols") or {}).get(symbol, {}).get("stats") or {}

    def f(k):
        try:
            v = float(st[k])
            return v if v > 0 else None
        except (KeyError, TypeError, ValueError):
            return None

    bid, ask, last = f("bidPrice"), f("askPrice"), f("lastPrice")
    mid = (bid + ask) / 2 if (bid and ask and ask >= bid) else last
    if not mid:
        raise ValueError(f"wallex {symbol}: no usable price")
    return SourceQuote("wallex", asset, mid * mul, bid and bid * mul,
                       ask and ask * mul, _now())


def _ramzinex(pair_id: int, asset: str, mul: float = 1.0) -> SourceQuote:
    d = _get("https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs")
    for p in (d.get("data") or d):
        if (p.get("pair_id") or p.get("id")) == pair_id:
            buy, sell = p.get("buy"), p.get("sell")
            if not buy or not sell:
                raise ValueError(f"ramzinex {pair_id}: no buy/sell")
            buy, sell = float(buy), float(sell)
            return SourceQuote("ramzinex", asset, (buy + sell) / 2 * mul,
                               buy * mul, sell * mul, _now())
    raise ValueError(f"ramzinex: pair {pair_id} not found")


def _bitpin(code: str, asset: str, mul: float = 1.0) -> SourceQuote:
    d = _get("https://api.bitpin.ir/v1/mkt/markets/")
    for m in d.get("results", []):
        if m.get("code") == code:
            px = float(m.get("price") or 0)
            if px <= 0:
                raise ValueError(f"bitpin {code}: non-positive price")
            return SourceQuote("bitpin", asset, px * mul, retrieved_at=_now())
    raise ValueError(f"bitpin: market {code} not found")


def _kraken(pair: str, asset: str) -> SourceQuote:
    d = _get(f"https://api.kraken.com/0/public/Ticker?pair={pair}")
    if d.get("error"):
        raise ValueError(f"kraken: {d['error']}")
    r = next(iter((d.get("result") or {}).values()))
    bid, ask = float(r["b"][0]), float(r["a"][0])
    return SourceQuote("kraken", asset, (bid + ask) / 2, bid, ask, _now())


def _okx(inst: str, asset: str) -> SourceQuote:
    d = _get(f"https://www.okx.com/api/v5/market/ticker?instId={inst}")
    row = (d.get("data") or [{}])[0]
    bid, ask = float(row.get("bidPx") or 0), float(row.get("askPx") or 0)
    last = float(row.get("last") or 0)
    mid = (bid + ask) / 2 if (bid and ask) else last
    if not mid:
        raise ValueError(f"okx {inst}: no price")
    return SourceQuote("okx", asset, mid, bid or None, ask or None, _now())


def _gate(pair: str, asset: str) -> SourceQuote:
    d = _get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={pair}")
    row = (d or [{}])[0]
    bid = float(row.get("highest_bid") or 0)
    ask = float(row.get("lowest_ask") or 0)
    last = float(row.get("last") or 0)
    mid = (bid + ask) / 2 if (bid and ask) else last
    if not mid:
        raise ValueError(f"gate {pair}: no price")
    return SourceQuote("gate", asset, mid, bid or None, ask or None, _now())


# TMN -> IRR is x10; Ramzinex already quotes IRR.
USD_IRR_SOURCES = [
    ("wallex",   lambda: _wallex("USDTTMN", "USD_IRR", 10.0)),
    ("ramzinex", lambda: _ramzinex(11, "USD_IRR", 1.0)),
    ("bitpin",   lambda: _bitpin("USDT_IRT", "USD_IRR", 10.0)),
]
PAXG_SOURCES = [
    ("kraken", lambda: _kraken("PAXGUSD", "PAXG")),
    ("gate",   lambda: _gate("PAXG_USDT", "PAXG")),
    ("bitpin", lambda: _bitpin("PAXG_USDT", "PAXG")),
]
XAUT_SOURCES = [
    ("okx",    lambda: _okx("XAUT-USDT", "XAUT")),
    ("gate",   lambda: _gate("XAUT_USDT", "XAUT")),
    ("wallex", lambda: _wallex("XAUTUSDT", "XAUT")),
]


def _run(sources) -> tuple[list[SourceQuote], list[SourceQuote]]:
    """Fetch all sources in parallel; return (ok, failed)."""
    ok: list[SourceQuote] = []
    bad: list[SourceQuote] = []
    with ThreadPoolExecutor(max_workers=len(sources)) as ex:
        futs = {ex.submit(fn): name for name, fn in sources}
        for fut in as_completed(futs, timeout=40):
            name = futs[fut]
            try:
                ok.append(fut.result())
            except Exception as e:  # noqa: BLE001 - recorded, not swallowed
                bad.append(SourceQuote(name, "?", 0.0, ok=False,
                                       error=f"{type(e).__name__}: {e}"[:140]))
    return ok, bad


def consense(asset: str, sources) -> Consensus:
    """Fetch every source for one asset and reduce to a median consensus."""
    ok, bad = _run(sources)
    notes = [f"{q.source}: {q.error}" for q in bad]

    if not ok:
        return Consensus(asset, None, 0, 0, None, [], [], "NO_DATA",
                         notes + ["هیچ منبعی پاسخ نداد."])
    if len(ok) == 1:
        q = ok[0]
        return Consensus(asset, q.value, 1, 0, 0.0, ok, [], "SINGLE_SOURCE",
                         notes + [f"فقط {q.source} پاسخ داد؛ بدون بررسی متقابل."])

    med = median([q.value for q in ok])
    keep = [q for q in ok if abs(q.value - med) / med <= OUTLIER_TOLERANCE]
    drop = [q for q in ok if q not in keep]
    for q in drop:
        notes.append(
            f"{q.source} کنار گذاشته شد: {q.value:,.2f} با میانه "
            f"{med:,.2f} اختلاف {abs(q.value - med) / med * 100:.1f}٪ دارد "
            f"(احتمالاً قیمت کهنه)."
        )

    final = keep or ok
    val = median([q.value for q in final])
    vals = [q.value for q in final]
    disp = (max(vals) - min(vals)) / val if val else None
    return Consensus(asset, val, len(final), len(drop), disp, final, drop,
                     "OK" if len(final) > 1 else "SINGLE_SOURCE", notes)


def fetch_all() -> dict:
    """
    Every anchor, cross-checked.

    PAXG and XAUT are consensed separately and then reconciled, because the basis
    between them is a real market fact rather than noise to average away.
    """
    usd = consense("USD_IRR", USD_IRR_SOURCES)
    paxg = consense("PAXG", PAXG_SOURCES)
    xaut = consense("XAUT", XAUT_SOURCES)

    gold_notes: list[str] = []
    candidates = [c for c in (paxg, xaut) if c.value]
    if not candidates:
        gold = None
        gold_status = "NO_DATA"
        gold_notes.append("هیچ منبع طلای جهانی در دسترس نیست.")
    elif len(candidates) == 1:
        gold = candidates[0].value
        gold_status = "SINGLE_TOKEN"
        gold_notes.append(f"فقط {candidates[0].asset} در دسترس بود.")
    else:
        basis = abs(paxg.value - xaut.value) / xaut.value
        gold = median([paxg.value, xaut.value])
        gold_status = "CROSS_CHECKED"
        gold_notes.append(
            f"PAXG {paxg.value:,.2f} و XAUT {xaut.value:,.2f} — "
            f"اختلاف پایه {basis * 100:.2f}٪. میانه استفاده شد."
        )
        if basis > 0.01:
            gold_status = "BASIS_WIDE"
            gold_notes.append("اختلاف دو توکن طلا غیرعادی است؛ با احتیاط بخوانید.")

    spreads = [q.spread_bps for q in usd.quotes if q.spread_bps is not None]
    return {
        "retrieved_at": _now(),
        "usd_irr": usd,
        "paxg": paxg,
        "xaut": xaut,
        "xau_usd": gold,
        "xau_status": gold_status,
        "xau_notes": gold_notes,
        "usd_spread_bps": median(spreads) if spreads else None,
        "source_count": usd.n_sources + paxg.n_sources + xaut.n_sources,
    }


def summarize(agg: dict) -> dict:
    """Flat, JSON-safe view for the report payload and the API."""
    def c(x: Consensus) -> dict:
        return {"value": x.value, "n_sources": x.n_sources, "n_outliers": x.n_outliers,
                "dispersion_pct": x.dispersion_pct, "status": x.status,
                "sources": [{"source": q.source, "value": q.value,
                             "spread_bps": q.spread_bps} for q in x.quotes],
                "excluded": [{"source": q.source, "value": q.value} for q in x.outliers],
                "notes": x.notes}
    return {
        "retrieved_at": agg["retrieved_at"],
        "usd_irr": c(agg["usd_irr"]),
        "paxg": c(agg["paxg"]),
        "xaut": c(agg["xaut"]),
        "xau_usd": agg["xau_usd"],
        "xau_status": agg["xau_status"],
        "xau_notes": agg["xau_notes"],
        "usd_spread_bps": agg["usd_spread_bps"],
        "source_count": agg["source_count"],
    }
