"""
The instrument face.

Deliberately not a dashboard of rounded cards — that look is everywhere and it
frames numbers as content to scroll past. This renders an instrument: engraved
rule-work, tick marks, a rose, and readouts placed around the dial the way a
real gauge labels itself. The visual language is the astrolabe, which is the
right reference for two reasons rather than one: it is the historical Persian
instrument for taking a bearing, and its eight-point rose is the same geometry
as the شمسه. The convergence is real, so the ornament is structural.

Everything is inline SVG. No library, no font CDN, no external request — the
page renders identically offline and under a strict CSP.

The needle only ever points where compass.py measured. When an axis is missing
the needle shortens and the dial says so, because an instrument that always
reads confidently is an instrument nobody should trust.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

# Minimal Jalali conversion. Iran has no DST, so a fixed offset is correct and
# no tz database is needed. Implemented here rather than pulled in as a
# dependency because it is ~15 lines and the project ships stdlib-only.
def to_jalali(y: int, m: int, d: int) -> tuple[int, int, int]:
    g_d_m = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy2 = y - 1600
    gm2 = m - 1
    days = (365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
            + d - 1 + g_d_m[gm2])
    if gm2 > 1 and ((y % 4 == 0 and y % 100 != 0) or y % 400 == 0):
        days += 1
    days -= 79
    j_np = days // 12053
    days %= 12053
    jy = 979 + 33 * j_np + 4 * (days // 1461)
    days %= 1461
    if days >= 366:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


JALALI_MONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                 "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")


def stamp_fa(dt: datetime) -> str:
    """Jalali date + Tehran clock — what an Iranian reader actually expects."""
    t = dt.astimezone(TEHRAN_TZ)
    jy, jm, jd = to_jalali(t.year, t.month, t.day)
    return f"{jd} {JALALI_MONTHS[jm - 1]} {jy} · ساعت {t:%H:%M} تهران"

from capital_compass.market.advisor import plain_summary, dealer_view

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def t(irr: float | None) -> str:
    return "—" if irr is None else f"{irr / 10:,.0f}"


def pc(x: float | None, d: int = 2) -> str:
    return "—" if x is None else f"{x * 100:+.{d}f}٪"


def band(p: float | None) -> str:
    if p is None:
        return "unk"
    if p >= 0.12:
        return "b4"
    if p >= 0.06:
        return "b3"
    if p >= 0.02:
        return "b2"
    if p <= -0.02:
        return "b0"
    return "b1"


# --------------------------------------------------------------------------
# The rose
# --------------------------------------------------------------------------

def compass_rose(bearing) -> str:
    """
    The dial. Size 460x460, centred at (230, 230).

    Layers, outermost first: degree ticks, the cardinal axis labels naming what
    each direction MEASURES, the eight-point rose, the needle, the hub.
    """
    cx = cy = 230.0
    R = 196.0
    p: list[str] = [
        '<svg viewBox="0 0 460 460" class="rose" role="img" '
        f'aria-label="قطب‌نمای بازار — جهت فعلی: {bearing.label}">'
    ]

    # --- degree ticks -----------------------------------------------------
    for deg in range(0, 360, 3):
        major = deg % 45 == 0
        mid = deg % 15 == 0
        ln = 15 if major else (9 if mid else 4.5)
        a = math.radians(deg - 90)
        x1, y1 = cx + math.cos(a) * R, cy + math.sin(a) * R
        x2, y2 = cx + math.cos(a) * (R - ln), cy + math.sin(a) * (R - ln)
        cls = "tk maj" if major else ("tk mid" if mid else "tk")
        p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}"/>')

    p.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" class="ring"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="{R - 22}" class="ring thin"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="104" class="ring thin"/>')

    # --- eight-point rose (شمسه geometry) ---------------------------------
    for i in range(8):
        deg = i * 45
        a = math.radians(deg - 90)
        long_pt = (i % 2 == 0)
        L = 100.0 if long_pt else 62.0
        w = 15.0 if long_pt else 10.0
        tipx, tipy = cx + math.cos(a) * L, cy + math.sin(a) * L
        pa = a + math.pi / 2
        lx, ly = cx + math.cos(pa) * w, cy + math.sin(pa) * w
        rx, ry = cx - math.cos(pa) * w, cy - math.sin(pa) * w
        cls = "pt lit" if long_pt else "pt"
        p.append(f'<path d="M{cx},{cy} L{lx:.1f},{ly:.1f} L{tipx:.1f},{tipy:.1f} Z" class="{cls} a"/>')
        p.append(f'<path d="M{cx},{cy} L{rx:.1f},{ry:.1f} L{tipx:.1f},{tipy:.1f} Z" class="{cls} b"/>')

    # --- axis labels: name what the direction MEASURES --------------------
    axes = [
        (0,   "فشار ارزی ↑",   "بالا = ریال زیر فشار"),
        (90,  "حباب ↑",        "راست = حباب باز شده"),
        (180, "فشار ارزی ↓",   "پایین = بازار ارز آرام"),
        (270, "حباب ↓",        "چپ = حباب جمع شده"),
    ]
    for deg, lab, sub in axes:
        a = math.radians(deg - 90)
        lx, ly = cx + math.cos(a) * (R + 26), cy + math.sin(a) * (R + 26)
        p.append(f'<text x="{lx:.0f}" y="{ly:.0f}" class="cd" text-anchor="middle">{lab}</text>')
        sx, sy = cx + math.cos(a) * (R + 42), cy + math.sin(a) * (R + 42)
        p.append(f'<text x="{sx:.0f}" y="{sy:.0f}" class="cdsub" text-anchor="middle">{sub}</text>')

    # --- needle -----------------------------------------------------------
    if bearing.angle_deg is None or bearing.magnitude <= 0.02:
        p.append(f'<circle cx="{cx}" cy="{cy}" r="30" class="deadzone"/>')
        p.append(f'<text x="{cx}" y="{cy + 5}" class="dead" text-anchor="middle">بدون جهت</text>')
    else:
        a = math.radians(bearing.angle_deg - 90)
        reach = 60 + bearing.magnitude * 118
        tipx, tipy = cx + math.cos(a) * reach, cy + math.sin(a) * reach
        tailx, taily = cx - math.cos(a) * (reach * 0.42), cy - math.sin(a) * (reach * 0.42)
        pa = a + math.pi / 2
        w = 11.0
        p.append(
            f'<path d="M{tipx:.1f},{tipy:.1f} '
            f'L{cx + math.cos(pa) * w:.1f},{cy + math.sin(pa) * w:.1f} '
            f'L{cx - math.cos(pa) * w:.1f},{cy - math.sin(pa) * w:.1f} Z" class="ndl n"/>'
        )
        p.append(
            f'<path d="M{tailx:.1f},{taily:.1f} '
            f'L{cx + math.cos(pa) * w:.1f},{cy + math.sin(pa) * w:.1f} '
            f'L{cx - math.cos(pa) * w:.1f},{cy - math.sin(pa) * w:.1f} Z" class="ndl s"/>'
        )
        p.append(f'<circle cx="{tipx:.1f}" cy="{tipy:.1f}" r="4.5" class="ndot"/>')

    p.append(f'<circle cx="{cx}" cy="{cy}" r="13" class="hub"/>')
    p.append(f'<circle cx="{cx}" cy="{cy}" r="5" class="hubin"/>')
    p.append("</svg>")
    return "".join(p)


def axis_meter(label: str, value: float | None, lo_fa: str, hi_fa: str,
               detail: str) -> str:
    """A linear readout for one axis — the numeric companion to the needle."""
    if value is None:
        return (f'<div class="mtr off"><span class="ml">{label}</span>'
                f'<div class="mbar"><i style="right:50%"></i></div>'
                f'<span class="mv">خوانده نشد</span></div>')
    posr = (1 - (value + 1) / 2) * 100
    sign = "pos" if value >= 0 else "neg"
    return (
        f'<div class="mtr"><span class="ml">{label}</span>'
        f'<div class="mbar {sign}"><span class="mid"></span>'
        f'<i style="right:{posr:.1f}%"></i></div>'
        f'<div class="mends"><span>{lo_fa}</span><span>{hi_fa}</span></div>'
        f'<span class="mv">{detail}</span></div>'
    )


def cost_ladder(rows: list[dict], ref: float | None) -> str:
    """Cost of one gram of pure gold by route, drawn as an engraved scale."""
    if not rows or not ref:
        return ""
    vals = [r["per_pure_gram_irr"] for r in rows] + [ref]
    hi, lo = max(vals) * 1.02, min(vals) * 0.985
    span = max(hi - lo, 1.0)
    w, rowh, top = 640, 34, 16
    h = top + len(rows) * rowh + 34
    lab = 118
    plot = w - lab - 96

    def x(v):
        return lab + (v - lo) / span * plot

    p = [f'<svg viewBox="0 0 {w} {h}" class="ladder" role="img" '
         f'aria-label="هزینه هر گرم طلای خالص از هر مسیر خرید">']
    rx = x(ref)
    p.append(f'<line x1="{rx:.1f}" y1="{top - 8}" x2="{rx:.1f}" y2="{h - 26}" class="refline"/>')
    p.append(f'<text x="{rx:.1f}" y="{h - 12}" class="reftx" text-anchor="middle">'
             f'ارزش خود طلا</text>')
    for i, r in enumerate(rows):
        y = top + i * rowh + rowh / 2
        v = r["per_pure_gram_irr"]
        vx = x(v)
        c = band(r.get("bubble_pct"))
        p.append(f'<line x1="{rx:.1f}" y1="{y:.1f}" x2="{vx:.1f}" y2="{y:.1f}" class="lk {c}"/>')
        p.append(f'<circle cx="{vx:.1f}" cy="{y:.1f}" r="5.5" class="lp {c}"/>')
        p.append(f'<text x="{lab - 12}" y="{y + 4:.1f}" class="lnm" text-anchor="end">{r["fa"]}</text>')
        p.append(f'<text x="{vx + 12:.1f}" y="{y + 4:.1f}" class="lv {c}">'
                 f'{t(v)} <tspan class="lvp">{pc(r.get("bubble_pct"), 1)}</tspan></text>')
    p.append("</svg>")
    return "".join(p)


CSS = """
:root{
--ink:#05080C;--panel:#0A0F16;--etch:#141C26;--etch2:#1E2A38;
--txt:#DCE6EF;--txt2:#8798A8;--txt3:#7E8F9E;
--brass:#C9A227;--brass2:#B89430;--glow:#5BE0C8;
--b0:#5AA9E6;--b1:#5BD6A0;--b2:#E0B341;--b3:#EE8B4F;--b4:#F2604E;--unk:#7A8896;}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:
radial-gradient(ellipse 90% 60% at 50% 0%,#0C1420 0%,var(--ink) 62%);
color:var(--txt);direction:rtl;text-align:right;min-height:100vh;
font-family:Vazirmatn,"IRANSansX","Segoe UI",Tahoma,"Noto Sans Arabic",sans-serif;
line-height:1.85;padding:26px 16px 70px;font-size:15px}
.w{max-width:940px;margin:0 auto}
.mn{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;
unicode-bidi:isolate;font-variant-numeric:tabular-nums}
.hd{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;
border-bottom:1px solid var(--etch2);padding-bottom:12px;margin-bottom:8px;flex-wrap:wrap}
h1{margin:0;font-size:clamp(19px,3.6vw,25px);font-weight:800;letter-spacing:-.01em}
h1 span{color:var(--brass);font-weight:400}
.stamp{font-size:10.5px;color:var(--txt3);letter-spacing:.1em}
.rail{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 26px}
.tagx{font-size:10.5px;padding:3px 10px;border:1px solid var(--etch2);color:var(--txt3);
letter-spacing:.05em}
.tagx.risk{border-color:var(--brass2);color:var(--brass)}
.dial{display:grid;gap:26px;align-items:center;margin-bottom:34px}
@media(min-width:800px){.dial{grid-template-columns:1fr 300px}}
.rose{display:block;width:100%;max-width:460px;margin:0 auto;height:auto;overflow:visible}
.tk{stroke:var(--etch2);stroke-width:1}
.tk.mid{stroke:#2A3846;stroke-width:1.2}
.tk.maj{stroke:var(--brass2);stroke-width:1.8}
.ring{fill:none;stroke:var(--etch2);stroke-width:1.2}
.ring.thin{stroke:var(--etch);stroke-width:1}
.pt{stroke:var(--etch2);stroke-width:.8}
.pt.a{fill:#0E1721}.pt.b{fill:#070C12}
.pt.lit.a{fill:#1A2634;stroke:var(--brass2)}
.pt.lit.b{fill:#0B1219;stroke:var(--brass2)}
.cd{fill:var(--txt2);font-size:12px;font-family:inherit;font-weight:700}
.cdsub{fill:var(--txt3);font-size:9.5px;font-family:inherit}
.ndl.n{fill:var(--glow)}
.ndl.s{fill:#33414F}
.ndot{fill:var(--glow)}
.hub{fill:#0A1119;stroke:var(--brass);stroke-width:1.6}
.hubin{fill:var(--brass)}
.deadzone{fill:none;stroke:var(--etch2);stroke-width:1;stroke-dasharray:3 4}
.dead{fill:var(--txt3);font-size:11px;font-family:inherit}
.read{border-inline-start:2px solid var(--brass2);padding-inline-start:18px}
.read .lb{font-size:10.5px;letter-spacing:.14em;color:var(--brass);display:block;margin-bottom:8px}
.read h2{margin:0 0 8px;font-size:clamp(21px,3.6vw,27px);font-weight:800;line-height:1.4}
.read p{margin:0 0 12px;font-size:13.5px;color:var(--txt2);line-height:1.8}
.mtr{margin-bottom:16px}
.mtr .ml{font-size:11px;color:var(--txt3);letter-spacing:.06em}
.mbar{position:relative;height:6px;background:var(--etch);margin:7px 0 4px;
border:1px solid var(--etch2)}
.mbar .mid{position:absolute;right:50%;top:-3px;bottom:-3px;width:1px;background:var(--etch2)}
.mbar i{position:absolute;top:-4px;width:2px;height:14px;background:var(--glow);
margin-inline-start:-1px}
.mtr.off .mbar i{background:var(--unk)}
.mends{display:flex;justify-content:space-between;font-size:9.5px;color:var(--txt3)}
.mv{font-size:12px;color:var(--txt2);font-family:"JetBrains Mono",Consolas,monospace;
direction:ltr;unicode-bidi:isolate;display:block;margin-top:3px}
.sec{border-top:1px solid var(--etch2);padding-top:22px;margin-bottom:30px}
.sec>h3{margin:0 0 3px;font-size:14px;font-weight:700}
.sec>p.h{margin:0 0 16px;font-size:12.5px;color:var(--txt3);line-height:1.75}
.ladder{width:100%;height:auto;overflow:visible}
.refline{stroke:var(--brass);stroke-width:1.3;stroke-dasharray:4 4}
.reftx{fill:var(--brass);font-size:10.5px;font-family:inherit}
.lk{stroke-width:1.4}.lk.b0{stroke:var(--b0)}.lk.b1{stroke:var(--b1)}
.lk.b2{stroke:var(--b2)}.lk.b3{stroke:var(--b3)}.lk.b4{stroke:var(--b4)}
.lk.unk{stroke:var(--unk)}
.lp.b0{fill:var(--b0)}.lp.b1{fill:var(--b1)}.lp.b2{fill:var(--b2)}
.lp.b3{fill:var(--b3)}.lp.b4{fill:var(--b4)}.lp.unk{fill:var(--unk)}
.lnm{fill:var(--txt2);font-size:12px;font-family:inherit}
.lv{font-size:11.5px;font-family:"JetBrains Mono",Consolas,monospace;fill:var(--txt)}
.lv.b0{fill:var(--b0)}.lv.b1{fill:var(--b1)}.lv.b2{fill:var(--b2)}
.lv.b3{fill:var(--b3)}.lv.b4{fill:var(--b4)}
.lvp{font-size:10px;opacity:.8}
.gr{display:grid;gap:0;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
border:1px solid var(--etch2);margin-bottom:22px}
.gr>div{padding:13px 15px;border-inline-end:1px solid var(--etch2)}
.gr>div:last-child{border-inline-end:0}
.gr dt{font-size:10px;letter-spacing:.1em;color:var(--txt3);margin:0 0 4px}
.gr dd{margin:0;font-size:18px;font-weight:700;font-family:"JetBrains Mono",Consolas,monospace;
direction:ltr;unicode-bidi:isolate;text-align:right}
.gr dd small{font-size:10.5px;color:var(--txt3);font-weight:400;margin-inline-start:3px}
ol.op{list-style:none;margin:0;padding:0;counter-reset:o}
ol.op li{display:grid;grid-template-columns:26px 1fr;gap:12px;padding:13px 0;
border-bottom:1px solid var(--etch)}
ol.op li:last-child{border-bottom:0}
ol.op .n{color:var(--txt3);font-size:12px;font-family:"JetBrains Mono",Consolas,monospace}
ol.op li.best .n{color:var(--brass)}
ol.op b{font-size:14.5px}
ol.op li.best b{color:var(--glow)}
.pill{font-size:10.5px;padding:1px 9px;margin-inline-start:8px;border:1px solid}
.pill.b0{color:var(--b0);border-color:var(--b0)}.pill.b1{color:var(--b1);border-color:var(--b1)}
.pill.b2{color:var(--b2);border-color:var(--b2)}.pill.b3{color:var(--b3);border-color:var(--b3)}
.pill.b4{color:var(--b4);border-color:var(--b4)}.pill.unk{color:var(--unk);border-color:var(--unk)}
ol.op p{margin:5px 0 0;font-size:13px;color:var(--txt2);line-height:1.75}
ol.op small{display:block;color:var(--txt3);font-size:11.5px;margin-top:3px}
.note{border:1px solid var(--etch2);border-inline-start:2px solid var(--b2);padding:13px 16px;
margin-bottom:14px;font-size:13px}
.note b{display:block;color:var(--b2);font-size:12px;margin-bottom:5px}
.note ul{margin:0;padding-inline-start:18px;color:var(--txt2)}
details{border-top:1px solid var(--etch2);margin-bottom:8px}
summary{cursor:pointer;padding:15px 0;font-size:13.5px;color:var(--brass);font-weight:700;
list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"+";margin-inline-end:9px;font-family:monospace}
details[open] summary::before{content:"−"}
summary:focus-visible{outline:1px solid var(--brass);outline-offset:3px}
.db{padding:0 0 22px}
.tw{overflow-x:auto;border:1px solid var(--etch2)}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:600px}
th{background:var(--etch);padding:9px 12px;text-align:right;font-size:10.5px;
color:var(--txt2);border-bottom:1px solid var(--etch2);white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid var(--etch)}
tr:last-child td{border-bottom:0}
td.n{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;unicode-bidi:isolate;
text-align:left;font-variant-numeric:tabular-nums;white-space:nowrap}
footer{border-top:1px solid var(--etch2);padding-top:18px;margin-top:26px;
color:var(--txt3);font-size:11.5px}
footer p{margin:0 0 8px;line-height:1.85}
footer b{color:var(--txt2)}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""


def render(payload: dict, bearing, *, dealer_inventory: dict | None = None) -> str:
    a = payload["anchors"]
    rows = (payload.get("arbitrage") or {}).get("rows") or []
    ps = plain_summary(payload)
    ref = (payload.get("arbitrage") or {}).get("reference_pure_gram_irr")
    ts = stamp_fa(datetime.fromisoformat(payload["generated_at"]))

    fx, pr = bearing.fx_axis, bearing.premium_axis
    fx_detail = "—"
    if fx.raw.get("tether_gap") is not None:
        fx_detail = f"تتر {pc(fx.raw['tether_gap'], 2)}"
        if fx.raw.get("implied_gap") is not None:
            fx_detail += f" · طلا {pc(fx.raw['implied_gap'], 2)}"
    pr_detail = "—"
    if pr.raw.get("percentile") is not None:
        pr_detail = (f"صدک {pr.raw['percentile'] * 100:.0f} از "
                     f"{pr.raw.get('history_days', 0):,} روز")

    meters = (
        axis_meter("فشار ارزی", fx.value, "آرام", "زیر فشار", fx_detail)
        + axis_meter("فشار حباب", pr.value, "جمع‌شده", "باز‌شده", pr_detail)
    )

    warn = ""
    if ps["warnings"] or bearing.notes or pr.notes:
        items = "".join(f"<li>{x}</li>" for x in
                        (ps["warnings"] + bearing.notes + pr.notes))
        warn = f'<div class="note"><b>محدودیت‌های این خوانش</b><ul>{items}</ul></div>'

    opts = "".join(
        f'<li class="{"best" if v.is_best else ""}"><span class="n">{v.rank}</span><div>'
        f'<b>{v.fa}</b><span class="pill {band(v.premium_pct)}">'
        f'{v.headline.split("—")[-1].strip()}</span><p>{v.detail}</p>'
        + "".join(f"<small>· {c}</small>" for c in v.caveats) + "</div></li>"
        for v in ps["verdicts"])

    sens = pr.raw.get("window_sensitivity") or {}
    sens_rows = "".join(
        f'<tr><td>{k if k != "all" else "کل تاریخچه"} روز</td>'
        f'<td class="n">{v["days"]:,}</td>'
        f'<td class="n">{v["median"] * 100:+.2f}٪</td>'
        f'<td class="n">{v["percentile"] * 100:.1f}٪</td></tr>'
        for k, v in (sens.get("windows") or {}).items())

    tr = "".join(
        f'<tr><td>{r["fa"]}</td><td class="n">{t(r["market_irr"])}</td>'
        f'<td class="n">{r["fine_grams"]:.4f}</td>'
        f'<td class="n">{t(r["per_pure_gram_irr"])}</td>'
        f'<td class="n">{pc(r.get("bubble_pct"))}</td>'
        f'<td class="n">{t(r.get("implied_usd_irr"))}</td></tr>' for r in rows)

    dealer = ""
    if dealer_inventory:
        d = dealer_view(payload, dealer_inventory)
        if d.get("status") == "OK":
            dl = "".join(
                f'<tr><td>{l["fa"]}</td><td class="n">{l["qty"]:,.0f}</td>'
                f'<td class="n">{l["market_toman"]:,.0f}</td>'
                f'<td class="n">{l["premium_toman"]:,.0f}</td></tr>'
                for l in d["lines"])
            dealer = (
                '<details><summary>حالت طلافروش — ارزش‌گذاری موجودی</summary>'
                '<div class="db"><div class="tw"><table><thead><tr><th>ابزار</th>'
                '<th>تعداد</th><th>ارزش بازار (ت)</th><th>از این مبلغ، حباب</th></tr>'
                f'</thead><tbody>{dl}</tbody></table></div>'
                '<div class="note" style="margin-top:14px"><b>خلاصه</b><ul>'
                + "".join(f"<li>{n}</li>" for n in d["notes"]) + '</ul></div></div></details>')

    return f"""<title>قطب‌نمای بازار طلا</title>
<style>{CSS}</style>
<div class="w" dir="rtl" lang="fa">
<div class="hd">
  <h1>قطب‌نما <span>· بازار طلا و سکه</span></h1>
  <span class="stamp mn">{ts}</span>
</div>
<div class="rail">
  <span class="tagx risk">دامنه مالی — نیازمند بازبینی انسانی</span>
  <span class="tagx">تعریف‌شده / تأییدنشده</span>
  <span class="tagx">{"لنگرها هم‌زمان" if a["same_instant_legs"] else "لنگرها ناهم‌زمان"}</span>
  <span class="tagx mn">اطمینان {bearing.confidence * 100:.0f}٪</span>
</div>

<div class="dial">
  {compass_rose(bearing)}
  <div class="read">
    <span class="lb">جهت فعلی بازار</span>
    <h2>{bearing.label}</h2>
    <p>{bearing.description}</p>
    {meters}
  </div>
</div>

<div class="sec">
  <h3>{ps["answer"]}</h3>
  <p class="h">{ps["why"]}{" " + ps["market_note"] if ps.get("market_note") else ""}</p>
  {warn}
  <ol class="op">{opts}</ol>
</div>

<div class="sec">
  <h3>هر گرم طلای واقعی، از هر راه چقدر تمام می‌شود؟</h3>
  <p class="h">خط‌چین طلایی یعنی خودِ طلا چقدر می‌ارزد. هرچه نقطه از آن دورتر باشد،
  بیشتر بابت شکلِ طلا پول داده‌اید تا خودِ طلا.</p>
  {cost_ladder(rows, ref)}
</div>

{dealer}

<details>
  <summary>عقربه از کجا می‌آید — روش و حساسیت</summary>
  <div class="db">
    <p class="h">عقربه روی دو کمیت اندازه‌گیری‌شده می‌ایستد، نه روی حدس.
    محور عمودی از اختلاف تتر با دلار نقدی و اختلاف دلار ضمنی طلا با دلار بازار
    ساخته می‌شود. محور افقی، حباب امروز را با تاریخچه خودش می‌سنجد.</p>
    <p class="h"><b>یک هشدار صادقانه:</b> انتخاب بازه تاریخی، خوانش محور حباب را
    جابه‌جا می‌کند. به‌جای پنهان کردن، هر چهار بازه را نشان می‌دهیم:</p>
    <div class="tw"><table>
      <thead><tr><th>بازه</th><th>تعداد روز</th><th>میانه حباب</th><th>صدک امروز</th></tr></thead>
      <tbody>{sens_rows}</tbody></table></div>
    <p class="h" style="margin-top:12px">اختلاف صدک بین بازه‌ها:
    <b class="mn">{sens.get("spread_pp") or 0:.1f}</b> واحد.</p>
  </div>
</details>

<details>
  <summary>اعداد کامل</summary>
  <div class="db">
    <div class="gr">
      <div><dt>طلای جهانی</dt><dd>{a["xau_usd"]:,.2f}<small lang="en">$/oz</small></dd></div>
      <div><dt>دلار لحظه‌ای</dt><dd>{t(a["usd_irr_crypto"])}<small>ت</small></dd></div>
      <div><dt>دلار نقدی</dt><dd>{t(a["usd_irr_cash"])}<small>ت</small></dd></div>
      <div><dt>پرمیوم تتر</dt><dd>{pc(a["tether_premium_pct"])}</dd></div>
      <div><dt>هر گرم خالص</dt><dd>{t(ref)}<small>ت</small></dd></div>
    </div>
    <div class="tw"><table>
      <thead><tr><th>ابزار</th><th>قیمت بازار (ت)</th><th>گرم خالص</th>
      <th>ت/گرم خالص</th><th>حباب</th><th>دلار ضمنی (ت)</th></tr></thead>
      <tbody>{tr}</tbody></table></div>
  </div>
</details>

<footer>
  <p><b>وضعیت:</b> تعریف‌شده / تأییدنشده. دامنه مالی طبق سیاست ریسک پرریسک
  طبقه‌بندی می‌شود و تا ثبت بازبینی انسانی، منتشرشده تلقی نمی‌شود.</p>
  <p><b>منابع:</b> قیمت ابزارهای داخلی و تاریخچه از <span lang="en">TGJU</span>؛ نرخ لحظه‌ای دلار و طلای
  جهانی از بازار توکن‌های طلا. مشخصات فیزیکی سکه از استاندارد بانک مرکزی —
  ثابت فیزیکی‌اند و کالیبره نمی‌شوند.</p>
  <p>{payload["disclaimer"]}</p>
</footer>
</div>"""
