from __future__ import annotations
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence

VALID_FX_STATES = {"UPTREND","DOWNTREND","RANGE","TRANSITION","DISLOCATED","UNKNOWN"}
VALID_XAU_STATES = {"UPTREND","DOWNTREND","RANGE","TRANSITION","EXTENDED_UP","EXTENDED_DOWN","UNKNOWN"}

@dataclass(frozen=True)
class Bar:
    high: float
    low: float
    close: float

def _swing_highs(bars: Sequence[Bar], window: int = 2):
    out = []
    for i in range(window, len(bars)-window):
        v = bars[i].high
        if all(v > bars[j].high for j in range(i-window, i)) and all(v >= bars[j].high for j in range(i+1, i+window+1)):
            out.append((i, v))
    return out

def _swing_lows(bars: Sequence[Bar], window: int = 2):
    out = []
    for i in range(window, len(bars)-window):
        v = bars[i].low
        if all(v < bars[j].low for j in range(i-window, i)) and all(v <= bars[j].low for j in range(i+1, i+window+1)):
            out.append((i, v))
    return out

def classify_structure(bars: Sequence[Bar], *, dislocated: bool = False) -> str:
    """
    Transparent MVP classifier:
    - DISLOCATED overrides clean trend.
    - Uses last two swing highs and lows.
    - If insufficient swings -> UNKNOWN.
    - HH+HL -> UPTREND
    - LH+LL -> DOWNTREND
    - mixed -> TRANSITION
    - nearly flat extrema -> RANGE
    """
    if dislocated:
        return "DISLOCATED"
    if len(bars) < 9:
        return "UNKNOWN"

    highs = _swing_highs(bars)
    lows = _swing_lows(bars)
    if len(highs) < 2 or len(lows) < 2:
        return "UNKNOWN"

    h1, h2 = highs[-2][1], highs[-1][1]
    l1, l2 = lows[-2][1], lows[-1][1]

    # Tiny changes treated as range/flat structure. This epsilon is numerical only,
    # not a market-calibrated threshold.
    eps = 1e-12
    high_dir = 1 if h2 > h1 + eps else (-1 if h2 < h1 - eps else 0)
    low_dir  = 1 if l2 > l1 + eps else (-1 if l2 < l1 - eps else 0)

    if high_dir == 1 and low_dir == 1:
        return "UPTREND"
    if high_dir == -1 and low_dir == -1:
        return "DOWNTREND"
    if high_dir == 0 and low_dir == 0:
        return "RANGE"
    return "TRANSITION"

def classify_data_state(*, critical_missing: bool, critical_invalid: bool,
                        material_conflict: bool, supporting_limited: bool) -> str:
    if critical_missing or critical_invalid:
        return "BLOCKED"
    if material_conflict:
        return "REVIEW_REQUIRED"
    if supporting_limited:
        return "READY_LIMITED"
    return "READY"

def classify_evidence_conflict(*, critical: bool=False, material: bool=False,
                               minor: bool=False) -> str:
    if critical:
        return "CRITICAL"
    if material:
        return "MATERIAL"
    if minor:
        return "MINOR"
    return "NONE"

def classify_fx_stress(*, source_divergence: str, spread_state: str,
                       quote_continuity: str) -> str:
    """
    MVP categorical routing. Inputs must already be normalized by deterministic
    pre-classifiers; no arbitrary market thresholds are embedded here.
    """
    vals = [source_divergence, spread_state, quote_continuity]
    if "DISLOCATED" in vals:
        return "DISLOCATED"
    high_count = sum(v == "HIGH" for v in vals)
    elevated_count = sum(v == "ELEVATED" for v in vals)
    if high_count >= 2:
        return "HIGH"
    if high_count == 1 or elevated_count >= 2:
        return "ELEVATED"
    if all(v == "NORMAL" for v in vals):
        return "NORMAL"
    return "UNKNOWN"
