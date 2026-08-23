"""
Cross-sectional mispricing engine.

Everything in this module is computable from a SINGLE snapshot. There is no
lookback window, no baseline, no calibration and therefore no minimum sample
size. That is a deliberate design choice, not a limitation: the Iranian gold
market's most-used signal (حباب) is a relative-value measure, and relative
value is cross-sectional by nature.

Four outputs, in increasing order of how rare they are in the market:

  1. bubble()           — premium of market price over melt value. Common.
  2. arbitrage_table()  — every instrument normalised to IRR per gram of PURE
                          gold, so they are directly comparable. Rare.
  3. implied_usd_irr()  — invert an instrument's price to recover the USD/IRR
                          the gold market is implicitly pricing. Not seen in
                          any Iranian public product at time of writing.
  4. breakeven_*()      — what would have to change for a trade to make sense.

A note on honesty: every function returns UNKNOWN rather than a number when an
input is missing. None of them ever substitutes a default.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from capital_compass.market.instruments import (
    INSTRUMENTS, TROY_OUNCE_GRAMS, get, pure_gold_irr_per_gram, intrinsic_irr,
)

# Retail quotes may embed ojrat/profit/VAT, so they are excluded from the pure
# arbitrage comparison unless the caller supplies a cost model.
RETAIL_KINDS = {"RETAIL"}

# Deep, low-premium instruments suitable for inferring an implied FX rate.
# Small coins are excluded on purpose: their premium is structural market
# behaviour, not a pricing error, so including them would corrupt the estimate.
FX_BENCHMARK_IDS = {"SEKKE_EMAMI", "SEKKE_BAHAR", "ABSHODE", "MESGHAL_17"}

# Plausibility bands. These are NOT calibrated thresholds — they are physical
# sanity limits used to catch unit errors and typos, which is why they are
# deliberately wide. A value outside these is a data fault, not a market event.
PLAUSIBLE = {
    "xau_usd_per_oz": (200.0, 50_000.0),
    "usd_irr": (10_000.0, 100_000_000.0),
}


@dataclass
class Quote:
    """One observed market price for one instrument."""
    instrument_id: str
    price_irr: float
    source: str
    observed_at: str
    quote_type: str = "MID"


@dataclass
class Bubble:
    instrument_id: str
    fa: str
    market_irr: float | None
    intrinsic_irr: float | None
    bubble_irr: float | None
    bubble_pct: float | None
    per_pure_gram_irr: float | None
    status: str                      # OK | NO_QUOTE | IMPLAUSIBLE
    notes: list[str] = field(default_factory=list)


def _check_inputs(xau: float | None, usd_irr: float | None) -> list[str]:
    """Return a list of fault strings; empty means inputs are usable."""
    faults = []
    if xau is None:
        faults.append("XAU_MISSING")
    elif not (PLAUSIBLE["xau_usd_per_oz"][0] <= xau <= PLAUSIBLE["xau_usd_per_oz"][1]):
        faults.append(f"XAU_IMPLAUSIBLE({xau})")
    if usd_irr is None:
        faults.append("USD_IRR_MISSING")
    elif not (PLAUSIBLE["usd_irr"][0] <= usd_irr <= PLAUSIBLE["usd_irr"][1]):
        faults.append(f"USD_IRR_IMPLAUSIBLE({usd_irr})")
    return faults


def bubble(instrument_id: str, market_irr: float | None,
           xau_usd_per_oz: float | None, usd_irr: float | None) -> Bubble:
    """Premium (حباب) of market price over melt value, for one instrument."""
    inst = get(instrument_id)
    faults = _check_inputs(xau_usd_per_oz, usd_irr)
    if faults:
        return Bubble(instrument_id, inst.fa, market_irr, None, None, None, None,
                      "IMPLAUSIBLE", faults)
    if market_irr is None or market_irr <= 0:
        intr = intrinsic_irr(instrument_id, xau_usd_per_oz, usd_irr)
        return Bubble(instrument_id, inst.fa, None, intr, None, None, None,
                      "NO_QUOTE", ["No market quote supplied."])

    intr = intrinsic_irr(instrument_id, xau_usd_per_oz, usd_irr)
    notes: list[str] = []
    if inst.kind in RETAIL_KINDS:
        notes.append(
            "قیمت خرده‌فروشی ممکن است اجرت/سود/مالیات را در خود داشته باشد؛ "
            "این عدد «حباب خالص» نیست."
        )
    return Bubble(
        instrument_id, inst.fa, market_irr, intr,
        market_irr - intr, (market_irr - intr) / intr,
        market_irr / inst.fine_grams, "OK", notes,
    )


def implied_usd_irr(instrument_id: str, market_irr: float,
                    xau_usd_per_oz: float, *, assumed_bubble: float = 0.0
                    ) -> float | None:
    """
    THE DIFFERENTIATOR.

    Invert the pricing identity to recover the USD/IRR rate that the gold
    market is implicitly using:

        market_price = fine_grams x (XAU / 31.1035) x USD_IRR x (1 + bubble)

    Solving for USD_IRR gives the dollar rate the gold market is pricing in.
    Comparing it to the FX market's own rate is informative in both directions:

      implied >> spot FX   ->  gold market pricing a weaker rial than FX market
                               (either a real bubble, or gold is leading FX)
      implied << spot FX   ->  gold cheap versus FX, or the FX quote is stale

    `assumed_bubble` lets a caller strip out a known structural premium before
    inverting; leave at 0 to get the raw implied rate.
    """
    inst = get(instrument_id)
    if market_irr <= 0 or xau_usd_per_oz <= 0:
        return None
    denom = inst.fine_grams * (xau_usd_per_oz / TROY_OUNCE_GRAMS) * (1.0 + assumed_bubble)
    if denom <= 0:
        return None
    return market_irr / denom


def arbitrage_table(quotes: dict[str, float], xau_usd_per_oz: float | None,
                    usd_irr: float | None, *, include_retail: bool = False
                    ) -> dict:
    """
    Normalise every quoted instrument to IRR per gram of PURE gold so they are
    directly comparable, then rank them cheapest-first.

    This is what turns "حباب سکه ۱۲٪" into an actual decision: it answers
    "which instrument should I actually buy right now?".
    """
    faults = _check_inputs(xau_usd_per_oz, usd_irr)
    rows: list[dict] = []
    for iid, price in quotes.items():
        if iid not in INSTRUMENTS or price is None or price <= 0:
            continue
        inst = get(iid)
        if inst.kind in RETAIL_KINDS and not include_retail:
            continue
        b = bubble(iid, price, xau_usd_per_oz, usd_irr)
        rows.append({
            "instrument_id": iid,
            "fa": inst.fa,
            "kind": inst.kind,
            "divisible": inst.divisible,
            "fine_grams": round(inst.fine_grams, 6),
            "market_irr": price,
            "per_pure_gram_irr": price / inst.fine_grams,
            "intrinsic_irr": b.intrinsic_irr,
            "bubble_pct": b.bubble_pct,
            "implied_usd_irr": (
                implied_usd_irr(iid, price, xau_usd_per_oz)
                if not faults else None
            ),
        })

    rows.sort(key=lambda r: r["per_pure_gram_irr"])
    result = {
        "rows": rows,
        "faults": faults,
        "reference_pure_gram_irr": (
            pure_gold_irr_per_gram(xau_usd_per_oz, usd_irr) if not faults else None
        ),
    }
    if len(rows) >= 2:
        cheap, rich = rows[0], rows[-1]
        spread = (rich["per_pure_gram_irr"] / cheap["per_pure_gram_irr"]) - 1.0
        result["spread"] = {
            "cheapest": cheap["instrument_id"],
            "cheapest_fa": cheap["fa"],
            "richest": rich["instrument_id"],
            "richest_fa": rich["fa"],
            "spread_pct": spread,
            "statement_fa": (
                f"{rich['fa']} به ازای هر گرم طلای خالص "
                f"{spread * 100:.1f}٪ گران‌تر از {cheap['fa']} است."
            ),
        }
    return result


def breakeven_usd_irr(instrument_id: str, market_irr: float,
                      xau_usd_per_oz: float, *, target_bubble: float = 0.0
                      ) -> float | None:
    """USD/IRR at which this instrument's bubble would equal `target_bubble`."""
    return implied_usd_irr(instrument_id, market_irr, xau_usd_per_oz,
                           assumed_bubble=target_bubble)


def breakeven_xau(instrument_id: str, market_irr: float, usd_irr: float,
                  *, target_bubble: float = 0.0) -> float | None:
    """XAU/USD at which this instrument's bubble would equal `target_bubble`."""
    inst = get(instrument_id)
    if market_irr <= 0 or usd_irr <= 0:
        return None
    denom = inst.fine_grams * (usd_irr / TROY_OUNCE_GRAMS) * (1.0 + target_bubble)
    return market_irr / denom if denom > 0 else None


def detect_unit_scale_error(quotes: dict[str, float], xau_usd_per_oz: float | None,
                            usd_irr: float | None) -> dict | None:
    """
    Catch the single most common data fault in Iranian finance: a toman figure
    entered where a rial figure is expected (or the reverse).

    A fixed plausibility band cannot catch this — 192,700 is a perfectly
    plausible-looking IRR/USD rate, it is just wrong by exactly 10x. What DOES
    catch it is cross-validation: any gold quote independently implies a
    USD/IRR, and a ratio sitting on a power of ten is a unit error, not a
    market move. Markets do not move by exactly 10x.

    Returns a fault dict, or None when nothing decade-shaped is detected.
    """
    if not usd_irr or not xau_usd_per_oz or usd_irr <= 0 or xau_usd_per_oz <= 0:
        return None
    ratios = []
    for iid, price in quotes.items():
        if iid not in INSTRUMENTS or not price or price <= 0:
            continue
        if get(iid).kind in RETAIL_KINDS:
            continue
        r = implied_usd_irr(iid, price, xau_usd_per_oz)
        if r:
            ratios.append(r / usd_irr)
    if not ratios:
        return None

    avg = sum(ratios) / len(ratios)
    for decade, label in ((10.0, "TOMAN_AS_RIAL"), (0.1, "RIAL_AS_TOMAN")):
        if abs(avg / decade - 1.0) < 0.15:      # within 15% of an exact decade
            corrected = usd_irr * decade
            return {
                "fault": label,
                "observed_ratio": avg,
                "supplied_usd_irr": usd_irr,
                "suggested_usd_irr": corrected,
                "message_fa": (
                    f"نرخ ارز واردشده {usd_irr:,.0f} احتمالاً به تومان است نه ریال. "
                    f"قیمت طلا نرخ {corrected:,.0f} ریال "
                    f"({corrected / 10:,.0f} تومان) را ایجاب می‌کند."
                    if label == "TOMAN_AS_RIAL" else
                    f"نرخ ارز واردشده {usd_irr:,.0f} احتمالاً به ریال است نه تومان. "
                    f"قیمت طلا نرخ {corrected:,.0f} را ایجاب می‌کند."
                ),
            }
    return None


def consistency_check(quotes: dict[str, float], xau_usd_per_oz: float | None,
                      usd_irr: float | None, *, tolerance: float = 0.03) -> dict:
    """
    Data-integrity check nobody else in this market does.

    Each coin independently implies a USD/IRR. Coins of the same series share a
    fineness and differ only in weight, so — absent instrument-specific bubbles
    — their implied rates should agree. Wide disagreement means one of:
      * a bad quote (typo, stale, wrong instrument),
      * a stale XAU leg,
      * or a genuine instrument-specific bubble (small coins usually).

    We do not guess which. We report the dispersion and let the caller decide.
    `tolerance` is a reporting threshold, not a market threshold.

    IMPORTANT — why only benchmark instruments are used for FX inference:
    small Iranian coins carry a large, permanent structural premium (retail
    demand plus indivisibility). Live data shows this cleanly and consistently:
    emami ~0%, nim ~2%, rob ~11%, gerami ~17%. Feeding those into a dispersion
    test makes it fire on every single run, which is a false alarm, not a
    finding. So the FX inference uses only deep, low-premium benchmarks, and
    the small-coin premium is reported separately as the market structure it
    actually is.
    """
    faults = _check_inputs(xau_usd_per_oz, usd_irr)
    if faults:
        return {"status": "CANNOT_CHECK", "faults": faults, "implied": {}}

    implied, structural = {}, {}
    for iid, price in quotes.items():
        if iid not in INSTRUMENTS or price is None or price <= 0:
            continue
        if get(iid).kind in RETAIL_KINDS:
            continue
        r = implied_usd_irr(iid, price, xau_usd_per_oz)
        if not r:
            continue
        (implied if iid in FX_BENCHMARK_IDS else structural)[iid] = r

    if len(implied) < 2:
        # Not enough benchmarks to cross-check; report rather than invent one.
        return {"status": "INSUFFICIENT_BENCHMARKS", "faults": [],
                "implied": implied, "structural_premium_instruments": structural,
                "notes": [
                    "برای بررسی سازگاری، حداقل دو ابزار مرجع نقدشونده لازم است "
                    "(سکه امامی، آب‌شده، مظنه). سکه‌های خرد حباب ساختاری دارند "
                    "و برای استنتاج نرخ ارز مناسب نیستند."
                ]}

    vals = sorted(implied.values())
    mid = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
    disp = (max(vals) - min(vals)) / mid

    notes = []
    status = "CONSISTENT"
    if disp > tolerance:
        status = "DISPERSED"
        notes.append(
            f"نرخ دلار ضمنیِ ابزارهای مختلف {disp * 100:.1f}٪ با هم اختلاف دارد."
        )
    if usd_irr:
        gap = (mid - usd_irr) / usd_irr
        notes.append(
            f"دلار ضمنی بازار طلا {mid / 10:,.0f} تومان است، "
            f"در حالی که نرخ ارز ورودی {usd_irr / 10:,.0f} تومان است "
            f"({gap * 100:+.1f}٪)."
        )
        if abs(gap) > tolerance:
            status = "FX_DIVERGENCE" if status == "CONSISTENT" else status
    return {
        "status": status,
        "faults": [],
        "implied": implied,
        "structural_premium_instruments": structural,
        "implied_median_usd_irr": mid,
        "dispersion_pct": disp,
        "fx_gap_pct": ((mid - usd_irr) / usd_irr) if usd_irr else None,
        "notes": notes,
    }
