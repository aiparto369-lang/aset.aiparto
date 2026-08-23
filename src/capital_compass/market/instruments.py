"""
Iranian gold/coin instrument specifications.

Every constant here is a published, independently verifiable physical spec —
not a calibrated parameter. That distinction matters: these numbers need no
historical data and cannot drift, which is exactly why the cross-sectional
engine built on top of them is deployable with a single snapshot.

Sources for the specs are recorded per instrument so an auditor can check them.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

TROY_OUNCE_GRAMS = 31.1034768
MESGHAL_GRAMS = 4.6083  # Iranian mesghal, the wholesale quoting unit


@dataclass(frozen=True)
class Instrument:
    """A tradable Iranian gold instrument with a known gold content."""
    instrument_id: str
    fa: str
    gross_grams: float
    purity: float          # fineness as a fraction, e.g. 0.900 = عیار ۹۰۰
    quote_unit: str        # what one market quote refers to
    kind: str              # COIN | BULLION | RETAIL
    spec_source: str
    divisible: bool        # can you buy a fraction? affects arbitrage practicality
    retail_accessible: bool = True   # can an ordinary buyer actually purchase this?

    @property
    def fine_grams(self) -> float:
        """Grams of pure (24k) gold in one unit."""
        return self.gross_grams * self.purity


# --- Coins (Central Bank of Iran / Imam Khomeini design) -------------------
# Full Bahar Azadi / Emami: 8.133 g gross at 900 fineness is the CBI published
# spec. Half/quarter/gram coins are exact fractions of the full coin.
_COIN_SRC = "CBI published coin specification (gross 8.133 g, fineness 900)"

EMAMI = Instrument(
    "SEKKE_EMAMI", "سکه امامی", 8.133, 0.900,
    "IRR_PER_COIN", "COIN", _COIN_SRC, divisible=False,
)
BAHAR = Instrument(
    "SEKKE_BAHAR", "سکه بهار آزادی", 8.133, 0.900,
    "IRR_PER_COIN", "COIN", _COIN_SRC, divisible=False,
)
NIM = Instrument(
    "NIM_SEKKE", "نیم‌سکه", 4.0665, 0.900,
    "IRR_PER_COIN", "COIN", _COIN_SRC + " (half)", divisible=False,
)
ROB = Instrument(
    "ROB_SEKKE", "ربع‌سکه", 2.03325, 0.900,
    "IRR_PER_COIN", "COIN", _COIN_SRC + " (quarter)", divisible=False,
)
GERAMI = Instrument(
    "SEKKE_GERAMI", "سکه گرمی", 1.016, 0.900,
    "IRR_PER_COIN", "COIN", _COIN_SRC + " (one-gram)", divisible=False,
)

# --- Bullion / wholesale ---------------------------------------------------
ABSHODE = Instrument(
    "ABSHODE", "طلای آب‌شده", 1.0, 0.995,
    "IRR_PER_GRAM", "BULLION", "Market convention: melted bar at ~995 fineness",
    divisible=True,
)
MESGHAL = Instrument(
    "MESGHAL_17", "مظنه (مثقال ۱۷ عیار)", MESGHAL_GRAMS, 0.705,
    "IRR_PER_MESGHAL", "BULLION",
    "Tehran wholesale convention: 1 mesghal = 4.6083 g at 705 fineness",
    divisible=True, retail_accessible=False,
)

# --- Retail ----------------------------------------------------------------
# NOTE: an 18k retail quote is NOT a pure melt-value quote. Depending on the
# venue it may or may not embed ojrat/profit/VAT. The engine therefore treats
# retail instruments separately and never mixes them into the pure-gold
# arbitrage table without an explicit cost model. See mispricing.RETAIL_KINDS.
GOLD_18K = Instrument(
    "GOLD_18K", "طلای ۱۸ عیار (گرم)", 1.0, 0.750,
    "IRR_PER_GRAM", "RETAIL", "Iranian 18-carat standard: fineness 750",
    divisible=True,
)

INSTRUMENTS: dict[str, Instrument] = {
    i.instrument_id: i for i in
    (EMAMI, BAHAR, NIM, ROB, GERAMI, ABSHODE, MESGHAL, GOLD_18K)
}

COIN_IDS = tuple(i.instrument_id for i in INSTRUMENTS.values() if i.kind == "COIN")
BULLION_IDS = tuple(i.instrument_id for i in INSTRUMENTS.values() if i.kind == "BULLION")
RETAIL_IDS = tuple(i.instrument_id for i in INSTRUMENTS.values() if i.kind == "RETAIL")


def get(instrument_id: str) -> Instrument:
    try:
        return INSTRUMENTS[instrument_id]
    except KeyError:
        raise KeyError(f"unknown instrument_id: {instrument_id}") from None


def pure_gold_irr_per_gram(xau_usd_per_oz: float, usd_irr: float) -> float:
    """IRR value of one gram of 24k gold. The anchor for everything else."""
    if xau_usd_per_oz <= 0 or usd_irr <= 0:
        raise ValueError("xau_usd_per_oz and usd_irr must be positive")
    return (xau_usd_per_oz / TROY_OUNCE_GRAMS) * usd_irr


def intrinsic_irr(instrument_id: str, xau_usd_per_oz: float, usd_irr: float) -> float:
    """Melt value of one unit of the instrument, in IRR."""
    return get(instrument_id).fine_grams * pure_gold_irr_per_gram(xau_usd_per_oz, usd_irr)


def spec_table() -> list[dict]:
    """Machine-readable spec dump — used by the audit record and the UI."""
    out = []
    for i in INSTRUMENTS.values():
        d = asdict(i)
        d["fine_grams"] = round(i.fine_grams, 6)
        out.append(d)
    return out
