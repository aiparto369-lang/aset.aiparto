from __future__ import annotations
from .base import RawObservation, utc_now_iso

class ManualCollector:
    """
    Controlled manual ingestion for pilot collection.
    Does not scrape or invent data.
    """
    source_id = "SRC-MANUAL-IRAN"

    @staticmethod
    def from_record(record: dict) -> RawObservation:
        required = [
            "variable_id","raw_value","raw_unit","observation_time",
            "source_origin","market","asset"
        ]
        missing = [k for k in required if k not in record]
        if missing:
            raise ValueError(f"missing manual observation fields: {missing}")
        return RawObservation(
            variable_id=record["variable_id"],
            raw_value=record["raw_value"],
            raw_unit=record["raw_unit"],
            quote_type=record.get("quote_type"),
            observation_time=record["observation_time"],
            retrieval_time=record.get("retrieval_time") or utc_now_iso(),
            source_id=record.get("source_id") or ManualCollector.source_id,
            source_origin=record["source_origin"],
            market=record["market"],
            asset=record["asset"],
            note=record.get("note")
        )

    def collect(self):
        raise RuntimeError("ManualCollector.collect() is intentionally not automatic; use from_record().")
