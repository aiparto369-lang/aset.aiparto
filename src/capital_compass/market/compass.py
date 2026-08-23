"""
The compass.

A needle that swings on a vibe is decoration, and decoration on a financial
instrument is a lie with a nice font. So this module defines the needle as a
bearing over two measured, signed, independently-sourced axes, each with a
stated formula and a stated failure mode:

    NORTH / SOUTH  — فشار ارزی (currency pressure)
        Is the rial under pressure right now, according to markets that trade
        continuously? Built from the tether-vs-cash spread and from the gap
        between the dollar the gold market implies and the dollar the FX market
        quotes. Both legs are live and signed.

    EAST / WEST    — فشار حباب (premium pressure)
        Is the coin premium expanding or compressing relative to its OWN
        history? Built from a percentile of today's premium against a multi-year
        daily series reconstructed from coin, ounce and dollar history.

The bearing is the resultant of the two. The needle's LENGTH is confidence, and
it shortens honestly: a missing or stale leg shortens the needle rather than
being silently treated as zero. A needle at the centre means "I don't know",
which is a reading the instrument is allowed to give.

What the quadrants mean is stated in QUADRANTS below, in the terms a buyer
actually thinks in, and each is a description of the two measurements — never a
prediction of where price goes next.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median

from capital_compass.market.instruments import TROY_OUNCE_GRAMS, get

# Reference instrument for the premium axis: deepest, most quoted, lowest
# structural premium of the Iranian coins.
PREMIUM_REF = "SEKKE_EMAMI"

# Percentile windows for the premium axis.
#
# There is no single defensible window here, and pretending otherwise would be
# the exact false-precision this project audits against. Measured on live data,
# the median premium is +8.9% over 365d, +19.0% over 720d, +12.8% over 1095d and
# +5.6% over the full series — so the window materially moves the reading.
#
# The instrument therefore computes ALL of them, drives the needle from the
# default, and reports the spread so a reader can see how window-dependent
# today's reading is. A wide spread is itself information.
PREMIUM_WINDOWS = (365, 720, 1095, None)   # None = full available history
PREMIUM_WINDOW_DEFAULT = 720
PREMIUM_WINDOW_DAYS = PREMIUM_WINDOW_DEFAULT   # backwards-compatible alias

QUADRANTS = {
    ("N", "E"): ("بازار داغ",
                 "هم فشار روی ریال هست و هم حباب در حال باز شدن. "
                 "خرید در این وضعیت گران‌ترین حالت ممکن است."),
    ("N", "W"): ("طلا عقب‌مانده",
                 "ریال تحت فشار است ولی حباب باز نشده. "
                 "طلا هنوز به نرخ ارز نرسیده."),
    ("S", "E"): ("حباب بدون پشتوانه",
                 "حباب باز شده اما بازار ارز آرام است. "
                 "این نوع حباب معمولاً دوام کمتری دارد."),
    ("S", "W"): ("بازار آرام",
                 "نه فشار ارزی محسوسی هست نه حباب. "
                 "از نظر قیمتی کم‌هزینه‌ترین وضعیت برای خرید است."),
}


@dataclass
class Axis:
    """One measured axis: a signed, normalised value plus its provenance."""
    key: str
    fa: str
    value: float | None          # normalised to roughly [-1, 1]
    raw: dict = field(default_factory=dict)
    confidence: float = 0.0      # 0..1 — how much of this axis is actually measured
    notes: list[str] = field(default_factory=list)


@dataclass
class Bearing:
    angle_deg: float | None      # 0 = North, clockwise
    magnitude: float             # 0..1 — needle length
    confidence: float            # 0..1
    quadrant: tuple[str, str] | None
    label: str
    description: str
    fx_axis: Axis
    premium_axis: Axis
    notes: list[str] = field(default_factory=list)


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# --------------------------------------------------------------------------
# Historical premium series — what makes the premium axis calibrated rather
# than asserted.
# --------------------------------------------------------------------------

def premium_series(coin_bars, ons_bars, usd_bars, *,
                   instrument_id: str = PREMIUM_REF) -> list[tuple[str, float]]:
    """
    Reconstruct the daily premium history of a coin.

    premium(t) = coin(t) / (fine_grams x ons(t)/31.1035 x usd(t)) - 1

    The three series are aligned on date, and a date missing from any one of
    them is dropped rather than forward-filled — a carried-forward ounce price
    would manufacture a premium move that never happened.
    """
    inst = get(instrument_id)
    ons_by = {b.ts: b.close for b in ons_bars if b.close > 0}
    usd_by = {b.ts: b.close for b in usd_bars if b.close > 0}
    out: list[tuple[str, float]] = []
    for b in coin_bars:
        o, u = ons_by.get(b.ts), usd_by.get(b.ts)
        if not o or not u or b.close <= 0:
            continue
        intrinsic = inst.fine_grams * (o / TROY_OUNCE_GRAMS) * u
        if intrinsic > 0:
            out.append((b.ts, b.close / intrinsic - 1.0))
    return out


def percentile_of(value: float, sample: list[float]) -> float | None:
    """Fraction of the sample at or below `value`. None if the sample is thin."""
    if len(sample) < 30:
        return None
    n = sum(1 for s in sample if s <= value)
    return n / len(sample)


# --------------------------------------------------------------------------
# Axes
# --------------------------------------------------------------------------

def fx_pressure_axis(*, tether_irr: float | None, cash_irr: float | None,
                     implied_irr: float | None,
                     full_scale: float = 0.04) -> Axis:
    """
    NORTH = rial under pressure.

    Two independent legs, averaged over whichever are available:
      1. tether premium   (tether - cash) / cash
      2. gold-implied gap (implied - cash) / cash

    `full_scale` is the deviation treated as a full-deflection reading. 4% is a
    presentation choice for needle travel — it scales the drawing, and is not
    used by any decision rule.
    """
    legs, raw, notes = [], {}, []

    if tether_irr and cash_irr:
        g = (tether_irr - cash_irr) / cash_irr
        legs.append(g)
        raw["tether_gap"] = g
    else:
        notes.append("نرخ تتر یا دلار نقدی در دسترس نیست.")

    if implied_irr and cash_irr:
        g = (implied_irr - cash_irr) / cash_irr
        legs.append(g)
        raw["implied_gap"] = g
    else:
        notes.append("دلار ضمنی بازار طلا قابل محاسبه نیست.")

    if not legs:
        return Axis("fx", "فشار ارزی", None, raw, 0.0,
                    notes + ["هیچ سنجه‌ای برای این محور موجود نیست."])

    val = _clamp(sum(legs) / len(legs) / full_scale)
    return Axis("fx", "فشار ارزی", val, raw, len(legs) / 2.0, notes)


def window_sensitivity(current_premium: float | None,
                       full_history: list[float]) -> dict:
    """
    Percentile of today's premium under every window, plus the spread.

    Reported so the window choice is visible rather than buried in a constant.
    """
    out: dict[str, dict] = {}
    if current_premium is None or not full_history:
        return {"windows": out, "spread_pp": None, "stable": None}
    for w in PREMIUM_WINDOWS:
        h = full_history if w is None else full_history[-w:]
        p = percentile_of(current_premium, h)
        if p is None:
            continue
        out[str(w or "all")] = {
            "days": len(h),
            "percentile": p,
            "median": median(h),
        }
    if not out:
        return {"windows": out, "spread_pp": None, "stable": None}
    ps = [v["percentile"] for v in out.values()]
    spread = (max(ps) - min(ps)) * 100.0
    return {"windows": out, "spread_pp": spread, "stable": spread <= 12.0}


def premium_pressure_axis(current_premium: float | None,
                          history: list[float]) -> Axis:
    """
    EAST = premium expanded relative to its own history.

    A percentile is used rather than a z-score because the premium distribution
    is skewed and bounded below — a z-score would overstate ordinary moves and
    understate the tails that matter.
    """
    raw, notes = {}, []
    if current_premium is None:
        return Axis("premium", "فشار حباب", None, raw, 0.0,
                    ["حباب فعلی قابل محاسبه نیست."])
    raw["current_premium"] = current_premium

    p = percentile_of(current_premium, history)
    if p is None:
        notes.append(
            f"تاریخچه کافی نیست ({len(history)} روز)؛ "
            "این محور بدون مبنای تاریخی خوانده نمی‌شود."
        )
        return Axis("premium", "فشار حباب", None, raw, 0.0, notes)

    raw["percentile"] = p
    raw["history_days"] = len(history)
    raw["history_median"] = median(history)
    return Axis("premium", "فشار حباب", _clamp((p - 0.5) * 2.0), raw, 1.0, notes)


# --------------------------------------------------------------------------
# Bearing
# --------------------------------------------------------------------------

def bearing(fx: Axis, prem: Axis) -> Bearing:
    """Combine the two axes into a compass bearing."""
    notes: list[str] = []
    fv = fx.value if fx.value is not None else 0.0
    pv = prem.value if prem.value is not None else 0.0
    conf = (fx.confidence + prem.confidence) / 2.0

    if fx.value is None:
        notes.append("محور ارزی خوانده نشد؛ عقربه فقط بر پایه حباب است.")
    if prem.value is None:
        notes.append("محور حباب خوانده نشد؛ عقربه فقط بر پایه فشار ارزی است.")

    mag = min(math.hypot(fv, pv), 1.0) * conf

    if conf <= 0.0 or (fx.value is None and prem.value is None):
        return Bearing(None, 0.0, 0.0, None, "نامشخص",
                       "داده کافی برای تعیین جهت وجود ندارد. "
                       "عقربه عمداً در مرکز می‌ماند.", fx, prem,
                       notes + ["هیچ محوری خوانده نشد."])

    # atan2(east, north) -> 0deg = North, increasing clockwise.
    ang = math.degrees(math.atan2(pv, fv)) % 360.0
    ns = "N" if fv >= 0 else "S"
    ew = "E" if pv >= 0 else "W"

    # A quadrant name asserts a reading on BOTH axes. When only one axis was
    # measured the other contributes 0.0, which silently lands the needle on a
    # quadrant boundary and produces a two-axis label from one-axis evidence -
    # e.g. "بازار داغ" when nothing about the premium was ever read. Single-axis
    # mode therefore gets its own labels, and the missing axis is named.
    if fx.value is None or prem.value is None:
        if prem.value is None:
            axis_fa, val = "فشار ارزی", fv
            missing = "حباب"
            up, down = "ریال زیر فشار است", "بازار ارز آرام است"
        else:
            axis_fa, val = "فشار حباب", pv
            missing = "فشار ارزی"
            up, down = "حباب باز شده است", "حباب جمع شده است"
        label = f"فقط {axis_fa}"
        desc = (
            f"{up if val >= 0 else down} — اما محور «{missing}» خوانده نشد، "
            f"پس این یک خوانش تک‌محوره است و جهت کامل بازار را نشان نمی‌دهد."
        )
        return Bearing(ang, mag, conf, None, label, desc, fx, prem, notes)

    label, desc = QUADRANTS[(ns, ew)]

    if mag < 0.18:
        label = "نزدیک تعادل"
        desc = ("هر دو سنجه نزدیک میانه‌اند. بازار در وضعیت خاصی نیست — "
                "و این خودش یک خبر است.")
    return Bearing(ang, mag, conf, (ns, ew), label, desc, fx, prem, notes)


def read_compass(*, tether_irr: float | None, cash_irr: float | None,
                 implied_irr: float | None, current_premium: float | None,
                 premium_history: list[float],
                 window: int | None = PREMIUM_WINDOW_DEFAULT) -> Bearing:
    """
    Full reading. This is the one function the UI and the API call.

    `premium_history` must be the FULL series; the window is applied here so the
    sensitivity across windows can be measured on the same input.

    `current_premium` must be computed on the SAME source basis as the history.
    Mixing bases (e.g. a TGJU-built history against a crypto-token premium) makes
    the percentile compare two different measurements. Live check showed that
    mismatch moves the percentile by ~1.2 points here — small, but it is an
    avoidable error, so the caller is required to keep the basis consistent.
    """
    sens = window_sensitivity(current_premium, premium_history)
    windowed = premium_history if window is None else premium_history[-window:]
    prem_axis = premium_pressure_axis(current_premium, windowed)
    prem_axis.raw["window_sensitivity"] = sens

    if sens.get("stable") is False:
        prem_axis.notes.append(
            f"خوانش این محور به بازه انتخابی حساس است "
            f"(اختلاف {sens['spread_pp']:.0f} واحد صدک بین بازه‌های مختلف)."
        )
    b = bearing(
        fx_pressure_axis(tether_irr=tether_irr, cash_irr=cash_irr,
                         implied_irr=implied_irr),
        prem_axis,
    )
    return b
