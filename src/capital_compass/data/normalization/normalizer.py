from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import json

UNIT_CONVERSIONS = {
    ("TOMAN_PER_USD","IRR_PER_USD"): lambda x: float(x) * 10.0,
    ("IRR_PER_USD","IRR_PER_USD"): lambda x: float(x),
    ("TOMAN_PER_GRAM","IRR_PER_GRAM"): lambda x: float(x) * 10.0,
    ("IRR_PER_GRAM","IRR_PER_GRAM"): lambda x: float(x),
    ("TOMAN_PER_COIN","IRR_PER_COIN"): lambda x: float(x) * 10.0,
    ("IRR_PER_COIN","IRR_PER_COIN"): lambda x: float(x),
    ("USD_PER_TROY_OUNCE","USD_PER_TROY_OUNCE"): lambda x: float(x),
    ("IRR","IRR"): lambda x: float(x),
    ("TOMAN","IRR"): lambda x: float(x) * 10.0,
}

def canonical_unit(variable_id: str) -> str:
    mapping = {
        "XAUUSD":"USD_PER_TROY_OUNCE",
        "USD_IRR_FREE_MARKET":"IRR_PER_USD",
        "GOLD_18K_IRR_GRAM":"IRR_PER_GRAM",
        "MELTED_GOLD_IRR":"IRR",
        "EMAMI_COIN_IRR":"IRR_PER_COIN",
    }
    if variable_id not in mapping:
        raise KeyError(f"unknown variable_id: {variable_id}")
    return mapping[variable_id]

def normalize_observation(raw, *, evidence_id: str, source_class: str, materiality: str = "M1") -> dict:
    target = canonical_unit(raw.variable_id)
    key = (raw.raw_unit, target)
    if key not in UNIT_CONVERSIONS:
        raise ValueError(f"unsupported explicit conversion: {raw.raw_unit} -> {target}")
    value = UNIT_CONVERSIONS[key](raw.raw_value)
    if value <= 0:
        raise ValueError("market observation must be positive")

    return {
        "evidence_id": evidence_id,
        "variable_id": raw.variable_id,
        "asset": raw.asset,
        "market": raw.market,
        "value": value,
        "unit": target,
        "quote_type": raw.quote_type,
        "observation_time": raw.observation_time,
        "retrieval_time": raw.retrieval_time,
        "source": {
            "source_id": raw.source_id,
            "class": source_class,
            "origin_id": raw.source_origin,
            "name": None,
            "uri": None
        },
        "quality": {
            "freshness": "UNKNOWN",
            "verification": "UNVERIFIED",
            "conflict": "NONE",
            "quality_class": "DQ-C"
        },
        "materiality": materiality,
        "lineage": {
            "raw_reference": raw.source_origin,
            "derived": False,
            "formula_id": None,
            "formula_version": None,
            "input_evidence_ids": []
        },
        "limitations": ["Pilot observation; quality state must be assigned by validation pipeline."]
    }

def canonical_json_hash(obj: dict) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8")
    return sha256(payload).hexdigest()
