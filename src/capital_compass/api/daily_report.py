"""
Build the daily market report: fetch live data, run the cross-sectional
engine, emit a machine-readable payload plus a Persian HTML dashboard.

This is the product surface. Everything it shows is derived from the engine,
and every number carries its source and timestamp — no figure appears on the
page that cannot be traced back to a fetch.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from capital_compass.data.providers.aggregator import fetch_all, summarize
from capital_compass.data.providers.iran_market import (
    fetch_tgju_bundle, fetch_tgju_series, fetch_wallex, gold_usd_from_tokens,
    ProviderError,
)
from capital_compass.market.instruments import get, TROY_OUNCE_GRAMS
from capital_compass.market.compass import premium_series, read_compass
from capital_compass.api.compass_ui import render as render_compass
from capital_compass.market.advisor import plain_summary
from capital_compass.market.mispricing import (
    arbitrage_table, consistency_check, detect_unit_scale_error,
    breakeven_usd_irr, implied_usd_irr,
)

REPORT_INSTRUMENTS = ("MESGHAL_17", "SEKKE_EMAMI", "NIM_SEKKE",
                      "ROB_SEKKE", "SEKKE_GERAMI")

# Sample inventory used to render the dealer panel. Clearly a demo shape, not a
# real holding - a dealer supplies their own via the API.
DEMO_INVENTORY = {"SEKKE_EMAMI": 40, "NIM_SEKKE": 25, "ROB_SEKKE": 60,
                  "SEKKE_GERAMI": 100}


def build_payload(*, max_bars: int = 120) -> dict:
    """Fetch everything and assemble the full report payload."""
    generated_at = datetime.now(timezone.utc).isoformat()
    faults: list[str] = []

    try:
        tg = fetch_tgju_bundle(max_bars=max_bars)
    except ProviderError as e:
        tg = {}
        faults.append(f"TGJU unavailable: {e}")
    # Multi-venue consensus replaces the old single-Wallex read. Nine quotes
    # across six venues, reduced by median per asset - a stale print from any one
    # venue can no longer move the anchor.
    agg = None
    try:
        agg = fetch_all()
    except Exception as e:  # noqa: BLE001
        faults.append(f"aggregator unavailable: {type(e).__name__}: {e}")

    if agg:
        xau = agg["xau_usd"]
        usd_irr_crypto = agg["usd_irr"].value
        usdt_spread = agg["usd_spread_bps"]
        faults.extend(agg["usd_irr"].notes)
        for n in agg["xau_notes"]:
            if "غیرعادی" in n:
                faults.append(n)
    else:
        xau = usd_irr_crypto = usdt_spread = None

    cash = tg.get("USD_IRR_FREE")
    usd_irr_cash = cash.latest.close if cash and cash.latest else None

    quotes: dict[str, float] = {}
    quote_meta: dict[str, dict] = {}
    for iid in REPORT_INSTRUMENTS:
        s = tg.get(iid)
        if s and s.latest:
            quotes[iid] = s.latest.close
            quote_meta[iid] = {"observed_date": s.latest.ts,
                               "observed_jalali": s.latest.ts_jalali,
                               "source": s.source, "bars_available": len(s.bars)}

    # The crypto rate is the preferred anchor: it is same-instant with the gold
    # leg. Cash is used only when crypto is unavailable, and we say which.
    anchor = usd_irr_crypto or usd_irr_cash
    anchor_kind = ("USDT_LIVE" if usd_irr_crypto
                   else "CASH_DAILY" if usd_irr_cash else None)
    if anchor_kind == "CASH_DAILY":
        faults.append("Falling back to daily cash FX; gold and FX legs are no "
                      "longer same-instant.")

    table = arbitrage_table(quotes, xau, anchor) if (quotes and xau and anchor) else {
        "rows": [], "faults": ["insufficient inputs"], "reference_pure_gram_irr": None}
    cons = consistency_check(quotes, xau, anchor) if (quotes and xau and anchor) else {
        "status": "CANNOT_CHECK", "notes": []}
    unit_fault = detect_unit_scale_error(quotes, xau, anchor) if (quotes and xau and anchor) else None

    tether_premium = None
    if usd_irr_crypto and usd_irr_cash:
        tether_premium = (usd_irr_crypto - usd_irr_cash) / usd_irr_cash

    breakevens = {}
    for iid, price in quotes.items():
        if xau and get(iid).kind == "COIN":
            be = breakeven_usd_irr(iid, price, xau, target_bubble=0.0)
            if be:
                breakevens[iid] = be

    # Compass reading. The premium fed to the percentile MUST be computed on the
    # same source basis as the history, so both use the TGJU ons/dollar legs.
    # The percentile is only meaningful against the FULL series. The display
    # bundle is truncated to keep the payload small, so the compass legs are
    # re-fetched untruncated - using the truncated bundle here silently cut the
    # history from ~2,400 aligned days to 91 and moved the reading by 20+
    # percentile points.
    bearing = None
    try:
        cb = fetch_tgju_series("sekee")
        ob = fetch_tgju_series("ons")
        ub = fetch_tgju_series("price_dollar_rl")
        if cb and ob and ub:
            hist = [v for _, v in premium_series(cb.bars, ob.bars, ub.bars)]
            if len(hist) < 200:
                faults.append(
                    f"premium history only {len(hist)} aligned days; "
                    "percentile reading is weak.")
            inst = get("SEKKE_EMAMI")
            c0, o0, u0 = cb.latest.close, ob.latest.close, ub.latest.close
            same_basis_premium = c0 / (inst.fine_grams * (o0 / TROY_OUNCE_GRAMS) * u0) - 1
            bearing = read_compass(
                tether_irr=usd_irr_crypto, cash_irr=usd_irr_cash,
                implied_irr=implied_usd_irr("SEKKE_EMAMI", c0, o0),
                current_premium=same_basis_premium, premium_history=hist)
    except Exception as e:
        faults.append(f"compass unavailable: {type(e).__name__}: {e}")

    return {
        "generated_at": generated_at,
        "engine_version": "2.0.0",
        "_bearing": bearing,
        "anchors": {
            "xau_usd": xau,
            "xau_source": "multi-venue median",
            "xau_status": agg["xau_status"] if agg else "NO_DATA",
            "xau_divergence_pct": (agg["xaut"].dispersion_pct if agg else None),
            "usd_irr_crypto": usd_irr_crypto,
            "usd_irr_cash": usd_irr_cash,
            "usd_irr_used": anchor,
            "anchor_kind": anchor_kind,
            "usdt_spread_bps": usdt_spread,
            "tether_premium_pct": tether_premium,
            "same_instant_legs": anchor_kind == "USDT_LIVE",
        },
        "sources": summarize(agg) if agg else None,
        "quotes": quotes,
        "quote_meta": quote_meta,
        "arbitrage": table,
        "consistency": cons,
        "unit_fault": unit_fault,
        "breakeven_usd_irr_at_zero_bubble": breakevens,
        "faults": faults,
        "disclaimer": (
            "این گزارش تحلیل ارزش نسبی مبتنی بر داده عمومی است و توصیه "
            "سرمایه‌گذاری نیست. ارقام حباب از مشخصات فیزیکی منتشرشده ابزارها "
            "و قیمت‌های لحظه‌ای بازار محاسبه شده‌اند."
        ),
    }


# --------------------------------------------------------------------------

def _t(irr: float | None) -> str:
    """Rial -> toman, grouped."""
    return "—" if irr is None else f"{irr / 10:,.0f}"


def _pct(x: float | None, digits: int = 2) -> str:
    return "—" if x is None else f"{x * 100:+.{digits}f}٪"


def _bubble_class(p: float | None) -> str:
    if p is None:
        return "n"
    if p >= 0.10:
        return "hot"
    if p >= 0.03:
        return "warm"
    if p <= -0.01:
        return "cold"
    return "flat"


def render_html(p: dict) -> str:
    a = p["anchors"]
    rows = p["arbitrage"].get("rows", [])
    ts = datetime.fromisoformat(p["generated_at"]).strftime("%Y-%m-%d %H:%M UTC")

    tr = []
    for r in rows:
        be = p["breakeven_usd_irr_at_zero_bubble"].get(r["instrument_id"])
        tr.append(
            f'<tr><td class="ins">{r["fa"]}</td>'
            f'<td class="n">{_t(r["market_irr"])}</td>'
            f'<td class="n">{r["fine_grams"]:.4f}</td>'
            f'<td class="n em">{_t(r["per_pure_gram_irr"])}</td>'
            f'<td class="n"><span class="b {_bubble_class(r["bubble_pct"])}">'
            f'{_pct(r["bubble_pct"])}</span></td>'
            f'<td class="n">{_t(r["implied_usd_irr"]) if r["implied_usd_irr"] else "—"}</td>'
            f'<td class="n sub">{_t(be) if be else "—"}</td></tr>'
        )

    ps = plain_summary(p)
    conf_fa = {"HIGH": "بالا", "MEDIUM": "متوسط", "LOW": "پایین", "NONE": "—"}
    opts = "".join(
        f'<li class="{"best" if v.is_best else ""}">'
        f'<span class="rk">{v.rank}</span>'
        f'<div><b>{v.fa}</b><span class="tag {v.band}">{v.headline.split("—")[-1].strip()}</span>'
        f'<p>{v.detail}</p>'
        + "".join(f'<small>· {c}</small>' for c in v.caveats)
        + '</div></li>'
        for v in ps["verdicts"])
    warn_items = "".join(f"<li>{w}</li>" for w in ps["warnings"])
    plain = (
        f'<section class="plain">'
        f'<div class="ans"><b>پاسخ کوتاه</b><p>{ps["answer"]}</p>'
        f'<p class="why">{ps["why"]}</p>'
        + (f'<p class="why">{ps["market_note"]}</p>' if ps.get("market_note") else "")
        + f'<span class="conf">اطمینان: {conf_fa.get(ps["confidence"], "—")}</span></div>'
        + (f'<div class="wn"><b>چیزهایی که باید بدانید</b><ul>{warn_items}</ul></div>' if warn_items else "")
        + f'<ol class="opts">{opts}</ol>'
        f'<details class="adv"><summary>نمای حرفه‌ای — جزئیات فنی</summary>'
        f'<div id="advanced"></div></details></section>')

    spread = p["arbitrage"].get("spread") or {}
    headline = spread.get("statement_fa", "داده کافی برای مقایسه موجود نیست.")

    cons = p["consistency"]
    cons_notes = "".join(f"<li>{n}</li>" for n in cons.get("notes", []))
    faults = "".join(f"<li>{f}</li>" for f in p.get("faults", []))
    uf = p.get("unit_fault")

    warn = ""
    if uf:
        warn += f'<div class="alert crit"><b>خطای مقیاس واحد</b><p>{uf["message_fa"]}</p></div>'
    if a.get("xau_status") == "DIVERGENT":
        warn += (f'<div class="alert warn"><b>واگرایی منابع طلا</b>'
                 f'<p>XAUT و PAXG {a["xau_divergence_pct"] * 100:.1f}٪ اختلاف دارند. '
                 f'منبع نقدشونده‌تر ({a["xau_source"]}) انتخاب شد.</p></div>')
    if faults:
        warn += f'<div class="alert warn"><b>هشدار داده</b><ul>{faults}</ul></div>'

    legs = ("هر دو لنگر از یک منبع و یک لحظه" if a["same_instant_legs"]
            else "لنگرها هم‌زمان نیستند")

    return f"""<title>قطب‌نما — حباب زنده</title>
<style>
:root{{--bg:#0E1412;--card:#161D1B;--card2:#1D2523;--ink:#E8EDEA;--ink2:#95A29E;
--ink3:#6B7772;--line:#28322F;--acc:#4FC3B4;--hot:#FF7A6B;--warm:#F0B450;
--cold:#6FB3F0;--flat:#7FCB8A;--crit:#FF6B5E;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);direction:rtl;text-align:right;
font-family:Vazirmatn,"Segoe UI",Tahoma,sans-serif;line-height:1.8;
padding:22px 16px 60px}}
.w{{max-width:1080px;margin:0 auto}}
header{{border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:22px}}
h1{{margin:0 0 6px;font-size:26px;font-weight:800;letter-spacing:-.01em}}
.sub{{color:var(--ink2);font-size:13.5px;margin:0}}
.mono{{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;
unicode-bidi:isolate;font-variant-numeric:tabular-nums}}
.head{{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);
border-right:3px solid var(--acc);border-radius:8px;padding:18px 20px;margin-bottom:20px}}
.head b{{color:var(--acc);font-size:11px;letter-spacing:.14em;display:block;margin-bottom:8px}}
.head p{{margin:0;font-size:19px;font-weight:700;line-height:1.6}}
.grid{{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));margin-bottom:20px}}
.k{{background:var(--card);border:1px solid var(--line);border-radius:7px;padding:13px 15px}}
.k dt{{font-size:10.5px;letter-spacing:.1em;color:var(--ink3);margin:0 0 5px}}
.k dd{{margin:0;font-size:20px;font-weight:700}}
.k dd small{{font-size:11px;color:var(--ink3);font-weight:400;margin-right:3px}}
.tw{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card);margin-bottom:20px}}
table{{width:100%;border-collapse:collapse;font-size:13.5px;min-width:660px}}
th{{background:var(--card2);padding:10px 12px;text-align:right;font-size:11px;
letter-spacing:.05em;color:var(--ink2);border-bottom:1px solid var(--line);white-space:nowrap}}
td{{padding:10px 12px;border-bottom:1px solid var(--line)}}
tr:last-child td{{border-bottom:0}}
td.n{{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;unicode-bidi:isolate;
text-align:left;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.em{{font-weight:700;color:var(--ink)}}
td.sub{{color:var(--ink3)}}
td.ins{{font-weight:600}}
.b{{padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700}}
.b.hot{{background:rgba(255,122,107,.15);color:var(--hot)}}
.b.warm{{background:rgba(240,180,80,.15);color:var(--warm)}}
.b.flat{{background:rgba(127,203,138,.13);color:var(--flat)}}
.b.cold{{background:rgba(111,179,240,.13);color:var(--cold)}}
.b.n{{color:var(--ink3)}}
.alert{{border-radius:7px;padding:12px 16px;margin-bottom:12px;font-size:13.5px;
border:1px solid;border-right-width:3px}}
.alert b{{display:block;margin-bottom:4px;font-size:13px}}
.alert p,.alert ul{{margin:0;font-size:13px;color:var(--ink2)}}
.alert ul{{padding-right:18px}}
.alert.crit{{border-color:var(--crit);background:rgba(255,107,94,.08)}}
.alert.crit b{{color:var(--crit)}}
.alert.warn{{border-color:var(--warm);background:rgba(240,180,80,.07)}}
.alert.warn b{{color:var(--warm)}}
.alert.ok{{border-color:var(--acc);background:rgba(79,195,180,.07)}}
.alert.ok b{{color:var(--acc)}}
.plain{{margin-bottom:26px}}
.ans{{background:linear-gradient(180deg,#14322E,#122926);border:1px solid #2A4B46;
border-right:4px solid var(--acc);border-radius:10px;padding:20px 22px;margin-bottom:14px}}
.ans b{{color:var(--acc);font-size:11px;letter-spacing:.14em;display:block;margin-bottom:10px}}
.ans p{{margin:0 0 7px;font-size:22px;font-weight:800;line-height:1.55}}
.ans p.why{{font-size:14.5px;font-weight:400;color:var(--ink2);line-height:1.75}}
.conf{{display:inline-block;margin-top:8px;font-size:11.5px;color:var(--ink3);
border:1px solid var(--line);border-radius:20px;padding:2px 12px}}
.wn{{background:rgba(240,180,80,.07);border:1px solid var(--warm);border-right-width:3px;
border-radius:8px;padding:13px 17px;margin-bottom:14px}}
.wn b{{color:var(--warm);font-size:12.5px;display:block;margin-bottom:6px}}
.wn ul{{margin:0;padding-right:18px;font-size:13px;color:var(--ink2)}}
.opts{{list-style:none;margin:0 0 14px;padding:0;display:flex;flex-direction:column;gap:8px}}
.opts li{{display:grid;grid-template-columns:34px 1fr;gap:12px;align-items:start;
background:var(--card);border:1px solid var(--line);border-radius:9px;padding:13px 15px}}
.opts li.best{{border-color:var(--acc);background:rgba(79,195,180,.06)}}
.rk{{width:26px;height:26px;border-radius:50%;background:var(--card2);color:var(--ink2);
display:grid;place-items:center;font-size:12px;font-weight:700}}
.opts li.best .rk{{background:var(--acc);color:#0E1412}}
.opts b{{font-size:15px;margin-left:8px}}
.opts p{{margin:5px 0 0;font-size:13.5px;color:var(--ink2);line-height:1.7}}
.opts small{{display:block;color:var(--ink3);font-size:12px;margin-top:3px}}
.tag{{font-size:11px;padding:2px 9px;border-radius:20px;font-weight:700}}
.tag.cheap,.tag.fair{{background:rgba(127,203,138,.14);color:var(--flat)}}
.tag.slight{{background:rgba(240,180,80,.14);color:var(--warm)}}
.tag.high,.tag.very_high{{background:rgba(255,122,107,.14);color:var(--hot)}}
.tag.unknown{{background:var(--card2);color:var(--ink3)}}
.adv{{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:0 16px}}
.adv summary{{cursor:pointer;padding:13px 0;font-size:13.5px;color:var(--acc);font-weight:600;list-style:none}}
.adv summary::-webkit-details-marker{{display:none}}
.adv summary::before{{content:"▾ ";font-size:11px}}
.adv[open] summary{{border-bottom:1px solid var(--line)}}
h2{{font-size:15px;margin:26px 0 11px;color:var(--ink2);font-weight:700}}
footer{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);
color:var(--ink3);font-size:12px}}
footer p{{margin:0 0 7px}}
</style>
<div class="w">
<header>
  <h1>قطب‌نما — حباب و آربیتراژ زنده</h1>
  <p class="sub mono">{ts} · engine v{p["engine_version"]} · {legs}</p>
</header>

{warn}

{plain}

<div class="head" id="pro">
  <b>خلاصه بازار — نمای حرفه‌ای</b>
  <p>{headline}</p>
</div>

<div class="grid">
  <div class="k"><dt>طلای جهانی</dt><dd class="mono">{a["xau_usd"]:,.2f}<small>$/oz</small></dd></div>
  <div class="k"><dt>دلار تتری (لحظه‌ای)</dt><dd class="mono">{_t(a["usd_irr_crypto"])}<small>ت</small></dd></div>
  <div class="k"><dt>دلار آزاد (روزانه)</dt><dd class="mono">{_t(a["usd_irr_cash"])}<small>ت</small></dd></div>
  <div class="k"><dt>پرمیوم تتر</dt><dd class="mono">{_pct(a["tether_premium_pct"])}</dd></div>
  <div class="k"><dt>اسپرد تتر</dt><dd class="mono">{a["usdt_spread_bps"]:.1f}<small>bps</small></dd></div>
  <div class="k"><dt>هر گرم طلای خالص</dt><dd class="mono">{_t(p["arbitrage"]["reference_pure_gram_irr"])}<small>ت</small></dd></div>
</div>

<h2>جدول آربیتراژ — همه ابزارها بر مبنای گرم طلای خالص</h2>
<div class="tw"><table>
<thead><tr>
  <th>ابزار</th><th>قیمت بازار (ت)</th><th>گرم خالص</th>
  <th>تومان/گرم خالص</th><th>حباب</th><th>دلار ضمنی (ت)</th><th>دلار سربه‌سر (ت)</th>
</tr></thead>
<tbody>{"".join(tr)}</tbody>
</table></div>

<div class="alert {'ok' if cons.get('status') == 'CONSISTENT' else 'warn'}">
  <b>بررسی یکپارچگی داده: {cons.get("status", "—")}</b>
  <ul>{cons_notes or "<li>بدون مورد.</li>"}</ul>
</div>

<footer>
  <p><b>چطور خوانده می‌شود:</b> ستون «تومان/گرم خالص» همه ابزارها را قابل مقایسه
  می‌کند. پایین‌ترین عدد، ارزان‌ترین راه خرید طلاست. «دلار ضمنی» نرخی است که
  بازار طلا در قیمت آن ابزار لحاظ کرده؛ «دلار سربه‌سر» نرخی است که در آن حباب
  صفر می‌شود.</p>
  <p><b>منابع:</b> قیمت ابزارهای داخلی از TGJU (بسته روزانه)؛ نرخ لحظه‌ای دلار و
  طلای جهانی از Wallex (USDT و توکن‌های طلا). مشخصات فیزیکی سکه‌ها از استاندارد
  منتشرشده بانک مرکزی.</p>
  <p>{p["disclaimer"]}</p>
</footer>
</div>"""


def main(outdir: str = "reports/live") -> tuple[Path, Path]:
    p = build_payload()
    d = Path(outdir)
    d.mkdir(parents=True, exist_ok=True)
    jf = d / "report.json"
    hf = d / "report.html"
    import dataclasses
    b_json = p.get("_bearing")
    p_json = {k: v for k, v in p.items() if k != "_bearing"}
    if b_json is not None:
        p_json["compass"] = {"label": b_json.label, "angle_deg": b_json.angle_deg,
                             "magnitude": b_json.magnitude, "confidence": b_json.confidence,
                             "quadrant": b_json.quadrant, "description": b_json.description,
                             "fx_axis": dataclasses.asdict(b_json.fx_axis),
                             "premium_axis": dataclasses.asdict(b_json.premium_axis)}
    jf.write_text(json.dumps(p_json, ensure_ascii=False, indent=2), encoding="utf-8")
    b = p.pop("_bearing", None)
    if b is None:
        raise RuntimeError("compass reading unavailable: " + "; ".join(p.get("faults") or ["unknown"]))
    hf.write_text(render_compass(p, b, dealer_inventory=DEMO_INVENTORY), encoding="utf-8")
    return jf, hf


if __name__ == "__main__":
    j, h = main()
    print(j)
    print(h)
