"""
Dealer engine.

A طلافروش does not need a market opinion. They need four numbers about the
metal already sitting in their safe:

  1. What is it worth right now?
  2. How much of that worth is gold, and how much is premium?
  3. If the premium reverts to its historical normal, what happens?
  4. Which items should I be selling and which should I be buying?

Point 3 is the one nobody else answers, and it is the reason this is worth
paying for. Premium is the part of inventory value that can evaporate without
the gold price moving at all — a dealer holding small coins is carrying a large
unhedged premium position and usually does not have it quantified anywhere.

Every figure here is derived from the same cross-sectional engine the rest of
the product uses. Nothing is modelled, fitted, or forecast: the stress test asks
"what if premium returns to its own median" and states that assumption plainly
rather than dressing it up as a prediction.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capital_compass.market.instruments import INSTRUMENTS, get


@dataclass
class Holding:
    instrument_id: str
    qty: float
    fa: str = ""
    market_irr: float = 0.0
    intrinsic_irr: float = 0.0
    premium_pct: float | None = None

    @property
    def market_value(self) -> float:
        return self.market_irr * self.qty

    @property
    def intrinsic_value(self) -> float:
        return self.intrinsic_irr * self.qty

    @property
    def premium_value(self) -> float:
        return self.market_value - self.intrinsic_value

    @property
    def fine_grams_total(self) -> float:
        return get(self.instrument_id).fine_grams * self.qty


@dataclass
class DealerReport:
    holdings: list[Holding] = field(default_factory=list)
    total_market: float = 0.0
    total_intrinsic: float = 0.0
    total_premium: float = 0.0
    total_fine_grams: float = 0.0
    premium_share: float | None = None
    stress: dict = field(default_factory=dict)
    actions: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: str = "OK"


def build(payload: dict, inventory: dict[str, float]) -> DealerReport:
    """Value an inventory against the current cross-sectional table."""
    rows = {r["instrument_id"]: r
            for r in (payload.get("arbitrage") or {}).get("rows") or []}
    rep = DealerReport()

    for iid, qty in (inventory or {}).items():
        if iid not in INSTRUMENTS:
            rep.notes.append(f"ابزار ناشناخته نادیده گرفته شد: {iid}")
            continue
        try:
            qty = float(qty)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        r = rows.get(iid)
        if not r:
            rep.notes.append(f"قیمت «{get(iid).fa}» امروز در دسترس نیست؛ "
                             "از محاسبه کنار گذاشته شد.")
            continue
        rep.holdings.append(Holding(
            iid, qty, r["fa"], r["market_irr"], r.get("intrinsic_irr") or 0.0,
            r.get("bubble_pct")))

    if not rep.holdings:
        rep.status = "EMPTY"
        rep.notes.append("موجودی وارد نشده یا هیچ‌کدام قابل قیمت‌گذاری نبود.")
        return rep

    rep.total_market = sum(h.market_value for h in rep.holdings)
    rep.total_intrinsic = sum(h.intrinsic_value for h in rep.holdings)
    rep.total_premium = rep.total_market - rep.total_intrinsic
    rep.total_fine_grams = sum(h.fine_grams_total for h in rep.holdings)
    rep.premium_share = (rep.total_premium / rep.total_market
                         if rep.total_market else None)
    rep.holdings.sort(key=lambda h: h.premium_value, reverse=True)
    return rep


def stress_test(rep: DealerReport, *, target_premium: float,
                label: str = "میانه تاریخی") -> dict:
    """
    What happens to inventory value if every premium reverts to `target_premium`.

    This is a scenario, not a forecast. It answers a bounded question — "how much
    of my inventory value is premium that could revert?" — and the answer is
    arithmetic, not opinion. The gold price is deliberately held fixed so the
    number isolates premium risk from price risk.
    """
    if rep.status != "OK":
        return {"status": "NO_DATA"}

    lines, after_total = [], 0.0
    for h in rep.holdings:
        after = h.intrinsic_value * (1.0 + target_premium)
        after_total += after
        lines.append({
            "instrument_id": h.instrument_id,
            "fa": h.fa,
            "qty": h.qty,
            "now_toman": h.market_value / 10,
            "after_toman": after / 10,
            "delta_toman": (after - h.market_value) / 10,
            "delta_pct": ((after - h.market_value) / h.market_value
                          if h.market_value else None),
        })

    delta = after_total - rep.total_market
    lines.sort(key=lambda x: x["delta_toman"])
    return {
        "status": "OK",
        "scenario": label,
        "target_premium": target_premium,
        "now_toman": rep.total_market / 10,
        "after_toman": after_total / 10,
        "delta_toman": delta / 10,
        "delta_pct": delta / rep.total_market if rep.total_market else None,
        "lines": lines,
        "assumption": (
            f"فرض: حباب همه اقلام به {target_premium * 100:+.1f}٪ ({label}) برگردد "
            "و قیمت طلای جهانی و نرخ ارز ثابت بماند. این یک سناریو است، نه پیش‌بینی."
        ),
    }


def rebalance_actions(rep: DealerReport, table_rows: list[dict], *,
                      spread_threshold: float = 0.03) -> list[dict]:
    """
    Where the inventory is expensive versus where the market is cheap.

    Deliberately framed as relative value, never as "sell this". A dealer decides
    on inventory turnover and customer demand too, and this tool sees neither.
    `spread_threshold` is a reporting floor so trivial gaps are not surfaced as
    if they were opportunities.
    """
    if rep.status != "OK" or not table_rows:
        return []

    priced = [r for r in table_rows if r.get("per_pure_gram_irr")]
    if len(priced) < 2:
        return []
    cheapest = min(priced, key=lambda r: r["per_pure_gram_irr"])

    out = []
    for h in rep.holdings:
        row = next((r for r in priced if r["instrument_id"] == h.instrument_id), None)
        if not row or row["instrument_id"] == cheapest["instrument_id"]:
            continue
        gap = (row["per_pure_gram_irr"] / cheapest["per_pure_gram_irr"]) - 1.0
        if gap < spread_threshold:
            continue
        out.append({
            "instrument_id": h.instrument_id,
            "fa": h.fa,
            "gap_pct": gap,
            "premium_value_toman": h.premium_value / 10,
            "vs_fa": cheapest["fa"],
            "statement": (
                f"«{h.fa}» به ازای هر گرم طلای خالص {gap * 100:.0f}٪ گران‌تر از "
                f"«{cheapest['fa']}» است. حباب انباشته روی این قلم "
                f"{h.premium_value / 10:,.0f} تومان است."
            ),
        })
    out.sort(key=lambda x: x["premium_value_toman"], reverse=True)
    return out


def full_report(payload: dict, inventory: dict[str, float],
                *, historical_median_premium: float | None = None) -> dict:
    """Everything a dealer panel needs, in one JSON-safe structure."""
    rep = build(payload, inventory)
    rows = (payload.get("arbitrage") or {}).get("rows") or []

    scenarios = {}
    if rep.status == "OK":
        scenarios["zero"] = stress_test(rep, target_premium=0.0,
                                        label="حباب صفر")
        if historical_median_premium is not None:
            scenarios["median"] = stress_test(
                rep, target_premium=historical_median_premium,
                label="میانه تاریخی حباب")

    return {
        "status": rep.status,
        "holdings": [{
            "instrument_id": h.instrument_id, "fa": h.fa, "qty": h.qty,
            "unit_price_toman": h.market_irr / 10,
            "market_toman": h.market_value / 10,
            "intrinsic_toman": h.intrinsic_value / 10,
            "premium_toman": h.premium_value / 10,
            "premium_pct": h.premium_pct,
            "fine_grams": h.fine_grams_total,
        } for h in rep.holdings],
        "totals": {
            "market_toman": rep.total_market / 10,
            "intrinsic_toman": rep.total_intrinsic / 10,
            "premium_toman": rep.total_premium / 10,
            "premium_share": rep.premium_share,
            "fine_grams": rep.total_fine_grams,
        },
        "scenarios": scenarios,
        "actions": rebalance_actions(rep, rows),
        "notes": rep.notes,
    }
