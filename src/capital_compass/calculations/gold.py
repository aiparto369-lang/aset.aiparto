from __future__ import annotations

TROY_OUNCE_GRAMS = 31.1034768

def pure_gold_irr_per_gram(xau_usd_per_oz: float, usd_irr: float) -> float:
    if xau_usd_per_oz <= 0 or usd_irr <= 0:
        raise ValueError("inputs must be positive")
    return (xau_usd_per_oz / TROY_OUNCE_GRAMS) * usd_irr

def gold_18k_implied_irr_per_gram(xau_usd_per_oz: float, usd_irr: float) -> float:
    return pure_gold_irr_per_gram(xau_usd_per_oz, usd_irr) * 0.75

def premium_fraction(observed: float, implied: float) -> float:
    if observed <= 0 or implied <= 0:
        raise ValueError("inputs must be positive")
    return (observed - implied) / implied
