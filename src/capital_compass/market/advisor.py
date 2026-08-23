"""
Plain-language layer.

The engine produces exact numbers. Most people who need those numbers do not
know what "حباب" or "دلار ضمنی" mean, and will not learn them to use a tool.
This module turns the engine's output into ordinary Persian sentences without
throwing away a single figure — the technical layer stays intact underneath and
is rendered alongside, never instead.

Rule followed throughout: translate the concept, never display the jargon alone.
"حباب ۱۱٪" becomes "۱۱٪ بیشتر از ارزش طلای داخلش قیمت دارد" — same number, no
vocabulary barrier.

Nothing here invents a recommendation the engine did not produce. Where the data
does not support a statement, it says so in plain words rather than softening it
into a number.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from capital_compass.market.instruments import get

# Bands for describing a premium in words. These are DESCRIPTIVE labels for the
# UI, not decision thresholds — nothing in the decision engine reads them. They
# are set from the observed structure of the Iranian coin market, where small
# coins carry a permanent premium and large coins trade near melt.
PREMIUM_BANDS = [
    (-0.02, "زیر ارزش ذاتی", "cheap",
     "کمتر از ارزش طلایی که داخلش هست قیمت دارد."),
    (0.02,  "تقریباً منصفانه", "fair",
     "قیمتش تقریباً برابر ارزش طلای داخلش است."),
    (0.06,  "کمی گران", "slight",
     "کمی بیشتر از ارزش طلای داخلش می‌دهید."),
    (0.12,  "گران", "high",
     "به‌طور محسوسی بیشتر از ارزش طلای داخلش می‌دهید."),
    (float("inf"), "خیلی گران", "very_high",
     "خیلی بیشتر از ارزش طلای داخلش می‌دهید."),
]


@dataclass
class PlainVerdict:
    """One instrument, explained the way you would explain it out loud."""
    instrument_id: str
    fa: str
    headline: str
    detail: str
    band: str
    premium_pct: float | None
    per_gram_toman: float | None
    rank: int | None = None
    is_best: bool = False
    caveats: list[str] = field(default_factory=list)


def describe_premium(p: float | None) -> tuple[str, str, str]:
    """(label, band_key, sentence) for a premium fraction."""
    if p is None:
        return ("نامشخص", "unknown",
                "برای این مورد داده کافی نداریم، پس عددی نمی‌گوییم.")
    for edge, label, key, sentence in PREMIUM_BANDS:
        if p < edge:
            return label, key, sentence
    return PREMIUM_BANDS[-1][1], PREMIUM_BANDS[-1][2], PREMIUM_BANDS[-1][3]


def explain_instrument(row: dict, cheapest_per_gram: float | None) -> PlainVerdict:
    inst = get(row["instrument_id"])
    p = row.get("bubble_pct")
    label, band, sentence = describe_premium(p)
    per_gram_t = (row["per_pure_gram_irr"] / 10.0) if row.get("per_pure_gram_irr") else None

    caveats = []
    if not inst.retail_accessible:
        caveats.append("این یک نرخ عمده‌فروشی است و مبنای مقایسه؛ مشتری خرد "
                       "معمولاً نمی‌تواند مستقیم با این نرخ بخرد.")
    if not inst.divisible:
        caveats.append("این ابزار تکه‌تکه فروخته نمی‌شود؛ باید کامل بخرید.")
    if inst.kind == "RETAIL":
        caveats.append("قیمت خرده‌فروشی معمولاً اجرت و مالیات هم دارد که اینجا حساب نشده.")

    extra = ""
    if cheapest_per_gram and per_gram_t:
        over = (per_gram_t / cheapest_per_gram) - 1.0
        if over > 0.005:
            extra = (f" یعنی هر گرم طلای خالص از این راه "
                     f"{over * 100:.0f}٪ گران‌تر از ارزان‌ترین گزینه تمام می‌شود.")

    headline = f"{inst.fa} — {label}"
    detail = sentence + extra
    return PlainVerdict(row["instrument_id"], inst.fa, headline, detail, band,
                        p, per_gram_t, caveats=caveats)


def plain_summary(payload: dict) -> dict:
    """
    Build the whole plain-language view from a daily_report payload.

    Returns the one-line answer, a ranked explanation per instrument, and any
    warnings the user genuinely needs — each already phrased for a non-expert.
    """
    rows = (payload.get("arbitrage") or {}).get("rows") or []
    anchors = payload.get("anchors") or {}

    # The headline recommendation must name something the reader can actually
    # buy. Mesghal is a wholesale quoting convention, so it stays in the
    # comparison (it is the truest melt benchmark) but never becomes the answer.
    buyable = [r for r in rows if get(r["instrument_id"]).retail_accessible]

    if not rows:
        return {
            "answer": "امروز داده کافی برای مقایسه نداریم.",
            "why": "تا وقتی قیمت‌ها کامل نشده، حدس نمی‌زنیم.",
            "verdicts": [], "warnings": [], "confidence": "NONE",
        }

    cheapest = (buyable or rows)[0]
    cheapest_per_gram = cheapest["per_pure_gram_irr"] / 10.0

    verdicts = []
    for i, r in enumerate(rows):
        v = explain_instrument(r, cheapest_per_gram)
        v.rank = i + 1
        v.is_best = (i == 0)
        verdicts.append(v)

    # The single sentence that has to survive being read on a phone.
    ranked_buyable = [v for v in verdicts if get(v.instrument_id).retail_accessible]
    best = (ranked_buyable or verdicts)[0]
    worst = (ranked_buyable or verdicts)[-1]
    best.is_best = True
    for v in verdicts:
        if v is not best:
            v.is_best = False
    gap = None
    if best.per_gram_toman and worst.per_gram_toman and worst is not best:
        gap = (worst.per_gram_toman / best.per_gram_toman) - 1.0

    answer = f"اگر امروز می‌خواهید طلا بخرید، ارزان‌ترین راه «{best.fa}» است."
    if gap and gap > 0.02:
        why = (f"همین مقدار طلا اگر به‌شکل «{worst.fa}» بخرید، "
               f"{gap * 100:.0f}٪ گران‌تر تمام می‌شود.")
    else:
        why = "اختلاف گزینه‌ها امروز کم است؛ فرق چندانی نمی‌کند."

    warnings = []
    if payload.get("unit_fault"):
        warnings.append("یکی از قیمت‌های ورودی احتمالاً اشتباه وارد شده؛ "
                        "تا بررسی نشده به این اعداد تکیه نکنید.")
    if anchors.get("xau_status") == "DIVERGENT":
        warnings.append("دو منبع قیمت طلای جهانی با هم اختلاف دارند؛ "
                        "منبع معتبرتر انتخاب شده ولی عدد ممکن است کمی جابه‌جا شود.")
    if not anchors.get("same_instant_legs"):
        warnings.append("قیمت طلای جهانی و نرخ دلار هم‌زمان نیستند؛ "
                        "ارقام حباب ممکن است چند دهم درصد خطا داشته باشند.")
    cons = (payload.get("consistency") or {}).get("status")
    if cons in {"DISPERSED", "FX_DIVERGENCE"}:
        warnings.append("قیمت‌های بازار امروز کاملاً با هم نمی‌خوانند؛ "
                        "این معمولاً یعنی بازار پرنوسان است.")

    confidence = "HIGH"
    if warnings:
        confidence = "MEDIUM"
    if payload.get("unit_fault") or not anchors.get("xau_usd"):
        confidence = "LOW"

    tether = anchors.get("tether_premium_pct")
    market_note = None
    if tether is not None:
        if tether > 0.02:
            market_note = ("دلار تتری از دلار نقدی جلوتر است — معمولاً نشانه "
                           "فشار روی بازار ارز است.")
        elif tether < -0.02:
            market_note = "دلار تتری از دلار نقدی عقب‌تر است."
        else:
            market_note = "بازار ارز امروز آرام است."

    return {
        "answer": answer,
        "why": why,
        "market_note": market_note,
        "verdicts": verdicts,
        "warnings": warnings,
        "confidence": confidence,
    }


def dealer_view(payload: dict, inventory: dict[str, float]) -> dict:
    """
    Dealer mode: value an actual inventory, and say where the premium risk sits.

    `inventory` maps instrument_id -> unit count. This is the feature a طلافروش
    will pay for, because it answers a question they ask every morning: how much
    of what I hold is real gold value, and how much is premium that can vanish?
    """
    rows = {r["instrument_id"]: r for r in (payload.get("arbitrage") or {}).get("rows") or []}
    lines, total_market, total_intrinsic = [], 0.0, 0.0

    for iid, qty in inventory.items():
        r = rows.get(iid)
        if not r or not qty:
            continue
        mv = r["market_irr"] * qty
        iv = (r["intrinsic_irr"] or 0.0) * qty
        total_market += mv
        total_intrinsic += iv
        lines.append({
            "instrument_id": iid,
            "fa": r["fa"],
            "qty": qty,
            "market_toman": mv / 10.0,
            "intrinsic_toman": iv / 10.0,
            "premium_toman": (mv - iv) / 10.0,
            "premium_pct": r.get("bubble_pct"),
        })

    if not lines:
        return {"status": "EMPTY", "lines": [], "notes": ["موجودی وارد نشده است."]}

    at_risk = total_market - total_intrinsic
    lines.sort(key=lambda x: x["premium_toman"], reverse=True)
    top = lines[0]

    notes = [
        f"ارزش کل موجودی به قیمت امروز: {total_market / 10:,.0f} تومان.",
        f"از این مبلغ {total_intrinsic / 10:,.0f} تومان ارزش خودِ طلاست.",
    ]
    if at_risk > 0:
        notes.append(
            f"{at_risk / 10:,.0f} تومان حباب است — یعنی مبلغی که اگر حباب بازار "
            f"جمع شود، از ارزش موجودی کم می‌شود."
        )
        notes.append(f"بیشترین حباب روی «{top['fa']}» است.")
    else:
        notes.append("موجودی شما زیر ارزش ذاتی طلا قیمت‌گذاری شده است.")

    return {
        "status": "OK",
        "lines": lines,
        "total_market_toman": total_market / 10.0,
        "total_intrinsic_toman": total_intrinsic / 10.0,
        "premium_at_risk_toman": at_risk / 10.0,
        "premium_share": (at_risk / total_market) if total_market else None,
        "notes": notes,
    }
