"""
Live Iranian market providers.

Two independent routes, deliberately chosen so they do NOT share an upstream:

  TGJU   — daily OHLC history for domestic instruments (coins, 18k, mesghal,
           abshode, free-market USD). Thousands of records per series, which
           is what unblocks every calibration in this codebase.

  WALLEX — live crypto order book. USDT/TMN gives an FX anchor that is genuinely
           independent of the domestic cash market, and XAUT/PAXG (gold-backed
           tokens, 1 token = 1 fine troy ounce) give a gold anchor quoted at the
           *same instant* as the FX anchor.

That last point is the reason this module exists. The original pipeline paired
a previous-day XAU close with an intraday Tehran quote — a 16.5 hour gap on a
measurement whose whole signal is ~1-3%. Taking both legs from one order book
at one timestamp removes that error term entirely.

Discipline carried over from the audit: observation_time is whatever the source
actually reports, never `now()`. Freshness is computed, never asserted.
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone

TGJU_BASE = "https://api.tgju.org/v1/market/indicator/summary-table-data/"
WALLEX_MARKETS = "https://api.wallex.ir/v1/markets"
WALLEX_DEPTH = "https://api.wallex.ir/v1/depth?symbol={symbol}"

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CapitalCompass/2.0"}

# TGJU indicator slug -> our instrument_id. Values are in RIAL.
TGJU_MAP = {
    "sekee":           "SEKKE_EMAMI",
    "nim":             "NIM_SEKKE",
    "rob":             "ROB_SEKKE",
    "gerami":          "SEKKE_GERAMI",
    "geram18":         "GOLD_18K",
    "mesghal":         "MESGHAL_17",
    "price_dollar_rl": "USD_IRR_FREE",
    "ons":             "XAU_USD",
    "geram24":         "GOLD_24K",
    "gold_17":         "ABSHODE_MESGHAL",
}
# These TGJU series are not quoted in rial.
NON_RIAL = {"ons"}


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Bar:
    """One daily OHLC record, as reported by the source."""
    ts: str            # gregorian YYYY-MM-DD
    ts_jalali: str
    open: float
    low: float
    high: float
    close: float

    @property
    def valid(self) -> bool:
        return (self.low > 0 and self.open > 0 and self.close > 0
                and self.high >= max(self.open, self.close, self.low)
                and self.low <= min(self.open, self.close, self.high))


@dataclass
class Series:
    instrument_id: str
    slug: str
    unit: str
    bars: list[Bar]
    source: str = "TGJU"
    retrieved_at: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def latest(self) -> Bar | None:
        return self.bars[-1] if self.bars else None

    def closes(self, n: int | None = None) -> list[float]:
        c = [b.close for b in self.bars]
        return c[-n:] if n else c


def _get_json(url: str, timeout: int = 25) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001 - surfaced as ProviderError with context
        raise ProviderError(f"{type(e).__name__} fetching {url[:80]}: {e}") from e


def _num(cell) -> float:
    """TGJU cells can carry HTML spans and thousands separators."""
    s = re.sub(r"<[^>]+>", "", str(cell)).replace(",", "").strip()
    return float(s)


def fetch_tgju_series(slug: str, *, max_bars: int | None = None) -> Series:
    """
    Daily OHLC for one TGJU indicator, oldest-first.

    TGJU returns newest-first; we reverse so downstream structure code sees
    chronological order, which is what every bar-based routine assumes.
    """
    if slug not in TGJU_MAP:
        raise ProviderError(f"unmapped TGJU slug: {slug}")
    payload = _get_json(TGJU_BASE + slug)
    rows = payload.get("data") or []
    if not rows:
        raise ProviderError(f"TGJU returned no rows for {slug}")

    bars: list[Bar] = []
    dropped = 0
    for r in rows:
        try:
            b = Bar(str(r[6]).replace("/", "-"), str(r[7]),
                    _num(r[0]), _num(r[1]), _num(r[2]), _num(r[3]))
        except (IndexError, ValueError):
            dropped += 1
            continue
        if not b.valid:
            dropped += 1
            continue
        bars.append(b)

    bars.reverse()
    if max_bars:
        bars = bars[-max_bars:]

    notes = []
    if dropped:
        notes.append(f"{dropped} malformed/invalid rows dropped by OHLC validity check.")
    notes.append("Daily close series; not an intraday executable quote.")

    return Series(
        instrument_id=TGJU_MAP[slug], slug=slug,
        unit="USD_PER_TROY_OUNCE" if slug in NON_RIAL else "IRR",
        bars=bars, retrieved_at=datetime.now(timezone.utc).isoformat(),
        notes=notes,
    )


def fetch_tgju_bundle(slugs: list[str] | None = None, *, max_bars: int | None = None
                      ) -> dict[str, Series]:
    """Fetch several indicators. Failures are reported, never silently defaulted."""
    slugs = slugs or list(TGJU_MAP)
    out: dict[str, Series] = {}
    errors: list[str] = []
    for s in slugs:
        try:
            out[TGJU_MAP[s]] = fetch_tgju_series(s, max_bars=max_bars)
        except ProviderError as e:
            errors.append(f"{s}: {e}")
    if errors and not out:
        raise ProviderError("all TGJU fetches failed: " + "; ".join(errors))
    for s in out.values():
        if errors:
            s.notes.append(f"Bundle had {len(errors)} failed series.")
    return out


# --------------------------------------------------------------------------
# Wallex — live, same-instant FX and gold anchors
# --------------------------------------------------------------------------

@dataclass
class LiveQuote:
    symbol: str
    last: float | None
    bid: float | None
    ask: float | None
    spread_bps: float | None
    volume_24h: float | None
    source: str = "WALLEX"
    retrieved_at: str = ""

    @property
    def mid(self) -> float | None:
        if self.bid and self.ask and self.ask >= self.bid:
            return (self.bid + self.ask) / 2.0
        return self.last


def fetch_wallex(symbols: tuple[str, ...] = ("USDTTMN", "XAUTUSDT", "PAXGUSDT",
                                             "XAUTTMN", "PAXGTMN")
                 ) -> dict[str, LiveQuote]:
    """
    Live quotes with a REAL bid/ask spread.

    The spread is the input `calibrate_stress` always needed and never had. We
    take it from the top of book rather than a synthetic estimate.
    """
    payload = _get_json(WALLEX_MARKETS)
    syms = (payload.get("result") or {}).get("symbols") or {}
    now = datetime.now(timezone.utc).isoformat()

    out: dict[str, LiveQuote] = {}
    for s in symbols:
        v = syms.get(s)
        if not v:
            continue
        st = v.get("stats") or {}

        def f(key):
            try:
                x = float(st[key])
                return x if x > 0 else None
            except (KeyError, TypeError, ValueError):
                return None

        bid, ask, last = f("bidPrice"), f("askPrice"), f("lastPrice")
        spread = None
        # Only a well-formed book yields a spread. A crossed book is a fault,
        # not a negative spread, so we refuse to report a number for it.
        if bid and ask and ask >= bid:
            spread = (ask - bid) / ((ask + bid) / 2.0) * 10_000.0
        out[s] = LiveQuote(s, last, bid, ask, spread, f("24h_volume"),
                           retrieved_at=now)
    if not out:
        raise ProviderError("Wallex returned none of the requested symbols")
    return out


def gold_usd_from_tokens(q: dict[str, LiveQuote], *, max_divergence: float = 0.02
                         ) -> dict:
    """
    Derive XAU/USD from gold-backed tokens, and cross-check them.

    XAUT and PAXG are each redeemable for one fine troy ounce, so both should
    track spot. When they disagree materially one of them is simply stale on
    this venue — we report the disagreement instead of silently picking one.
    Liquidity breaks the tie, because a stale print is the usual cause.
    """
    cands = {}
    for sym, key in (("XAUTUSDT", "XAUT"), ("PAXGUSDT", "PAXG")):
        lq = q.get(sym)
        if lq and lq.mid:
            cands[key] = {"price": lq.mid, "volume": lq.volume_24h or 0.0,
                          "spread_bps": lq.spread_bps}
    if not cands:
        return {"status": "NO_GOLD_TOKEN", "xau_usd": None, "candidates": {}}
    if len(cands) == 1:
        k, v = next(iter(cands.items()))
        return {"status": "SINGLE_SOURCE", "xau_usd": v["price"], "chosen": k,
                "candidates": cands,
                "notes": [f"Only {k} available; no independent cross-check."]}

    prices = [v["price"] for v in cands.values()]
    div = (max(prices) - min(prices)) / (sum(prices) / len(prices))
    chosen = max(cands.items(), key=lambda kv: kv[1]["volume"])
    notes = []
    status = "CROSS_CHECKED"
    if div > max_divergence:
        status = "DIVERGENT"
        notes.append(
            f"XAUT و PAXG {div * 100:.1f}٪ اختلاف دارند؛ "
            f"{chosen[0]} با حجم بالاتر انتخاب شد."
        )
    return {"status": status, "xau_usd": chosen[1]["price"], "chosen": chosen[0],
            "divergence_pct": div, "candidates": cands, "notes": notes}
