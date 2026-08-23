"""
Dashboard renderer — Persian, RTL, two-layer, chart-first.

Governance context (see adi/DDR-001): this artifact was NOT produced by the ADI
pipeline, which cannot build a UI at v0.1.0. What IS carried over from ADI is the
one thing its implemented stage actually produced: the Load Manifest's
`risk_signal: confirmed-high-risk`, which under risk/high-risk-ui-policy.md §5
sets `no_autonomous_release = true`. That flag is rendered on the page rather than
kept in a file, because a governance flag nobody sees governs nothing.

Design intent, in one line: the first screen answers the question in a sentence and
a picture; the numbers a professional needs are one disclosure away, never deleted.

Charts are hand-built inline SVG. No library, no external fetch — the page must
render identically offline and inside a strict CSP.
"""
from __future__ import annotations

from datetime import datetime

from capital_compass.market.advisor import plain_summary, dealer_view

# ---- formatting ----------------------------------------------------------

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def toman(irr: float | None, *, fa: bool = False) -> str:
    if irr is None:
        return "—"
    s = f"{irr / 10:,.0f}"
    return s.translate(FA_DIGITS) if fa else s


def pct(x: float | None, digits: int = 2) -> str:
    return "—" if x is None else f"{x * 100:+.{digits}f}٪"


def band_of(p: float | None) -> str:
    if p is None:
        return "unknown"
    if p >= 0.12:
        return "very_high"
    if p >= 0.06:
        return "high"
    if p >= 0.02:
        return "slight"
    if p <= -0.02:
        return "cheap"
    return "fair"


# ---- charts --------------------------------------------------------------

def bubble_chart(rows: list[dict]) -> str:
    """
    Horizontal bar chart of premium per instrument.

    Diverging from a zero baseline rather than growing from the left edge: the
    sign of a premium is the whole point, so zero has to be a visible position on
    the axis, not an implied edge.
    """
    if not rows:
        return ""
    vals = [r.get("bubble_pct") or 0.0 for r in rows]
    lo, hi = min(vals + [0.0]), max(vals + [0.0])
    span = max(hi - lo, 0.04)
    pad = span * 0.12
    lo, hi = lo - pad, hi + pad
    span = hi - lo

    row_h, gap, top = 30, 10, 26
    h = top + len(rows) * (row_h + gap) + 22
    w, lab_w = 660, 132
    plot_w = w - lab_w - 78

    def x_of(v: float) -> float:
        return lab_w + (v - lo) / span * plot_w

    zero_x = x_of(0.0)
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" width="100%" '
        f'aria-label="نمودار حباب هر ابزار نسبت به ارزش ذاتی طلای آن">',
        f'<line x1="{zero_x:.1f}" y1="{top - 12}" x2="{zero_x:.1f}" y2="{h - 18}" '
        f'class="ax"/>',
        f'<text x="{zero_x:.1f}" y="{h - 5}" class="axl" text-anchor="middle">'
        f'ارزش ذاتی</text>',
    ]
    for i, r in enumerate(rows):
        y = top + i * (row_h + gap)
        v = r.get("bubble_pct") or 0.0
        bx = x_of(v)
        x0, bw = (zero_x, bx - zero_x) if v >= 0 else (bx, zero_x - bx)
        bw = max(bw, 1.5)
        cls = band_of(r.get("bubble_pct"))
        parts.append(
            f'<rect x="{x0:.1f}" y="{y}" width="{bw:.1f}" height="{row_h}" rx="4" '
            f'class="bar {cls}"/>'
        )
        parts.append(
            f'<text x="{lab_w - 10}" y="{y + row_h / 2 + 5:.0f}" class="lbl" '
            f'text-anchor="end">{r["fa"]}</text>'
        )
        tx = (x0 + bw + 8) if v >= 0 else (x0 - 8)
        anc = "start" if v >= 0 else "end"
        parts.append(
            f'<text x="{tx:.1f}" y="{y + row_h / 2 + 5:.0f}" class="val {cls}" '
            f'text-anchor="{anc}">{pct(r.get("bubble_pct"), 1)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def cost_chart(rows: list[dict], reference_irr: float | None) -> str:
    """
    Cost of one gram of PURE gold through each route, against the melt reference.

    This is the chart that makes the product's core claim visible without a single
    number being read: the bars are what you actually pay, the dashed line is what
    the gold is worth.
    """
    if not rows or not reference_irr:
        return ""
    vals = [r["per_pure_gram_irr"] for r in rows] + [reference_irr]
    hi = max(vals) * 1.06
    lo = min(vals) * 0.965
    span = max(hi - lo, 1.0)

    w, h = 660, 250
    left, bottom, top = 8, 44, 18
    plot_h = h - bottom - top
    n = len(rows)
    slot = (w - left - 16) / n
    bw = min(slot * 0.56, 66)

    def y_of(v: float) -> float:
        return top + (hi - v) / span * plot_h

    ref_y = y_of(reference_irr)
    parts = [
        f'<svg viewBox="0 0 {w} {h}" role="img" width="100%" '
        f'aria-label="نمودار هزینه هر گرم طلای خالص از هر مسیر خرید">'
    ]
    for i, r in enumerate(rows):
        cx = left + slot * i + slot / 2
        v = r["per_pure_gram_irr"]
        y = y_of(v)
        cls = band_of(r.get("bubble_pct"))
        parts.append(
            f'<rect x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
            f'height="{(top + plot_h) - y:.1f}" rx="5" class="bar {cls}"/>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{y - 7:.1f}" class="val {cls}" '
            f'text-anchor="middle">{toman(v)}</text>'
        )
        parts.append(
            f'<text x="{cx:.1f}" y="{h - 24:.0f}" class="lbl" '
            f'text-anchor="middle">{r["fa"]}</text>'
        )
    parts.append(
        f'<line x1="{left}" y1="{ref_y:.1f}" x2="{w - 16}" y2="{ref_y:.1f}" class="ref"/>'
    )
    parts.append(
        f'<text x="{w - 18}" y="{ref_y - 8:.1f}" class="refl" text-anchor="end">'
        f'ارزش خود طلا · {toman(reference_irr)} تومان</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def fx_gauge(implied: float | None, actual: float | None) -> str:
    """Two dollar rates on one axis: what gold implies vs what FX actually trades."""
    if not implied or not actual:
        return ""
    lo, hi = min(implied, actual), max(implied, actual)
    mid = (lo + hi) / 2
    pad = max((hi - lo) * 2.2, mid * 0.012)
    a, b = mid - pad, mid + pad
    w, h = 660, 92

    def x(v):
        return 28 + (v - a) / (b - a) * (w - 56)

    gap = (implied - actual) / actual
    return (
        f'<svg viewBox="0 0 {w} {h}" role="img" width="100%" '
        f'aria-label="مقایسه دلار ضمنی بازار طلا با نرخ واقعی ارز">'
        f'<line x1="28" y1="52" x2="{w - 28}" y2="52" class="ax"/>'
        f'<circle cx="{x(actual):.1f}" cy="52" r="7" class="dot actual"/>'
        f'<text x="{x(actual):.1f}" y="34" class="lbl" text-anchor="middle">'
        f'نرخ بازار ارز</text>'
        f'<text x="{x(actual):.1f}" y="76" class="val" text-anchor="middle">'
        f'{toman(actual)}</text>'
        f'<circle cx="{x(implied):.1f}" cy="52" r="7" class="dot implied"/>'
        f'<text x="{x(implied):.1f}" y="34" class="lbl" text-anchor="middle">'
        f'دلاری که بازار طلا حساب می‌کند</text>'
        f'<text x="{x(implied):.1f}" y="76" class="val implied" text-anchor="middle">'
        f'{toman(implied)}</text>'
        f'<text x="{w / 2:.0f}" y="16" class="axl" text-anchor="middle">'
        f'اختلاف {pct(gap, 1)}</text>'
        f'</svg>'
    )


# ---- page ----------------------------------------------------------------

CSS = """
:root{--bg:#0D1211;--s1:#151C1A;--s2:#1C2422;--s3:#232C29;
--ink:#EAEFEC;--ink2:#9BA8A3;--ink3:#6E7A75;--line:#27312E;
--acc:#4FC9B7;--acc2:#2E8F82;
--cheap:#63B3ED;--fair:#79C98A;--slight:#E8B54B;--high:#EE8B5F;--vhigh:#F26D5B;
--unknown:#5A6663;--crit:#F26D5B;}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);direction:rtl;text-align:right;
font-family:Vazirmatn,"IRANSansX","Segoe UI",Tahoma,"Noto Sans Arabic",sans-serif;
line-height:1.85;padding:20px 16px 64px;font-size:15px}
.w{max-width:1000px;margin:0 auto}
.mono{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;
unicode-bidi:isolate;font-variant-numeric:tabular-nums}
header{margin-bottom:20px}
h1{margin:0 0 5px;font-size:clamp(22px,4.4vw,30px);font-weight:800;letter-spacing:-.015em}
.sub{color:var(--ink3);font-size:12.5px;margin:0}
.gov{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0 22px}
.chip{font-size:11px;padding:3px 11px;border-radius:20px;border:1px solid var(--line);
color:var(--ink3);background:var(--s1)}
.chip.risk{border-color:var(--slight);color:var(--slight);background:rgba(232,181,75,.08)}
.ans{background:linear-gradient(165deg,#153630,#112825);border:1px solid #2C4F48;
border-right:4px solid var(--acc);border-radius:12px;padding:22px 24px;margin-bottom:16px}
.ans .eb{color:var(--acc);font-size:11px;letter-spacing:.15em;display:block;margin-bottom:11px}
.ans h2{margin:0 0 8px;font-size:clamp(19px,3.4vw,25px);font-weight:800;line-height:1.5;color:var(--ink)}
.ans p{margin:0 0 5px;font-size:14.5px;color:var(--ink2)}
.conf{display:inline-block;margin-top:10px;font-size:11.5px;color:var(--ink3);
border:1px solid var(--line);border-radius:20px;padding:2px 12px}
.card{background:var(--s1);border:1px solid var(--line);border-radius:11px;
padding:18px 20px;margin-bottom:16px}
.card>h3{margin:0 0 4px;font-size:15px;font-weight:700}
.card>p.hint{margin:0 0 14px;font-size:12.5px;color:var(--ink3);line-height:1.7}
svg{display:block;max-width:100%;height:auto;overflow:visible}
.bar.cheap{fill:var(--cheap)}.bar.fair{fill:var(--fair)}.bar.slight{fill:var(--slight)}
.bar.high{fill:var(--high)}.bar.very_high{fill:var(--vhigh)}.bar.unknown{fill:var(--unknown)}
.ax{stroke:var(--ink3);stroke-width:1}
.ref{stroke:var(--acc);stroke-width:1.5;stroke-dasharray:5 4}
.refl{fill:var(--acc);font-size:11px;font-family:inherit}
.axl{fill:var(--ink3);font-size:10.5px;font-family:inherit}
.lbl{fill:var(--ink2);font-size:12px;font-family:inherit}
.val{fill:var(--ink);font-size:11.5px;font-weight:700;
font-family:"JetBrains Mono",Consolas,monospace;direction:ltr}
.val.cheap{fill:var(--cheap)}.val.fair{fill:var(--fair)}.val.slight{fill:var(--slight)}
.val.high{fill:var(--high)}.val.very_high{fill:var(--vhigh)}.val.implied{fill:var(--acc)}
.dot.actual{fill:var(--ink2)}.dot.implied{fill:var(--acc)}
.opts{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
.opts li{display:grid;grid-template-columns:30px 1fr;gap:12px;align-items:start;
background:var(--s1);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.opts li.best{border-color:var(--acc2);background:rgba(79,201,183,.055)}
.rk{width:26px;height:26px;border-radius:50%;background:var(--s3);color:var(--ink2);
display:grid;place-items:center;font-size:12px;font-weight:700}
.opts li.best .rk{background:var(--acc);color:#0D1211}
.opts b{font-size:15px}
.tag{font-size:11px;padding:2px 10px;border-radius:20px;font-weight:700;margin-right:8px}
.tag.cheap{background:rgba(99,179,237,.15);color:var(--cheap)}
.tag.fair{background:rgba(121,201,138,.15);color:var(--fair)}
.tag.slight{background:rgba(232,181,75,.15);color:var(--slight)}
.tag.high{background:rgba(238,139,95,.15);color:var(--high)}
.tag.very_high{background:rgba(242,109,91,.15);color:var(--vhigh)}
.tag.unknown{background:var(--s3);color:var(--ink3)}
.opts p{margin:6px 0 0;font-size:13.5px;color:var(--ink2);line-height:1.75}
.opts small{display:block;color:var(--ink3);font-size:12px;margin-top:4px}
.grid{display:grid;gap:9px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:16px}
.k{background:var(--s1);border:1px solid var(--line);border-radius:9px;padding:13px 15px}
.k dt{font-size:10.5px;letter-spacing:.09em;color:var(--ink3);margin:0 0 5px}
.k dd{margin:0;font-size:19px;font-weight:700}
.k dd small{font-size:11px;color:var(--ink3);font-weight:400;margin-right:3px}
.alert{border-radius:10px;padding:14px 17px;margin-bottom:14px;font-size:13.5px;
border:1px solid;border-right-width:3px}
.alert b{display:block;margin-bottom:5px;font-size:13px}
.alert ul{margin:0;padding-right:19px;color:var(--ink2);font-size:13px}
.alert.warn{border-color:var(--slight);background:rgba(232,181,75,.07)}
.alert.warn b{color:var(--slight)}
.alert.crit{border-color:var(--crit);background:rgba(242,109,91,.08)}
.alert.crit b{color:var(--crit)}
.alert.ok{border-color:var(--acc2);background:rgba(79,201,183,.06)}
.alert.ok b{color:var(--acc)}
details{border:1px solid var(--line);border-radius:11px;background:var(--s1);
margin-bottom:16px;overflow:hidden}
summary{cursor:pointer;padding:15px 20px;font-size:14px;color:var(--acc);
font-weight:700;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▾";display:inline-block;margin-left:8px;font-size:11px;
transition:transform .18s}
details[open] summary::before{transform:rotate(180deg)}
details[open] summary{border-bottom:1px solid var(--line)}
.dbody{padding:18px 20px}
summary:focus-visible,a:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:9px;background:var(--s1)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:640px}
th{background:var(--s2);padding:10px 12px;text-align:right;font-size:11px;
color:var(--ink2);border-bottom:1px solid var(--line);white-space:nowrap;font-weight:700}
td{padding:10px 12px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
td.n{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;
unicode-bidi:isolate;text-align:left;font-variant-numeric:tabular-nums;white-space:nowrap}
td.em{font-weight:700}
td.sub{color:var(--ink3)}
footer{margin-top:26px;padding-top:18px;border-top:1px solid var(--line);
color:var(--ink3);font-size:12px}
footer p{margin:0 0 8px;line-height:1.8}
footer b{color:var(--ink2)}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
"""


def render(payload: dict, *, dealer_inventory: dict | None = None) -> str:
    a = payload["anchors"]
    rows = (payload.get("arbitrage") or {}).get("rows") or []
    ps = plain_summary(payload)
    ts = datetime.fromisoformat(payload["generated_at"]).strftime("%Y-%m-%d %H:%M UTC")
    conf_fa = {"HIGH": "بالا", "MEDIUM": "متوسط", "LOW": "پایین", "NONE": "نامشخص"}

    opts = "".join(
        f'<li class="{"best" if v.is_best else ""}">'
        f'<span class="rk">{v.rank}</span><div>'
        f'<b>{v.fa}</b><span class="tag {v.band}">{v.headline.split("—")[-1].strip()}</span>'
        f'<p>{v.detail}</p>'
        + "".join(f"<small>· {c}</small>" for c in v.caveats)
        + "</div></li>"
        for v in ps["verdicts"]
    )

    alerts = ""
    if ps["warnings"]:
        alerts += ('<div class="alert warn"><b>چیزهایی که باید بدانید</b><ul>'
                   + "".join(f"<li>{w}</li>" for w in ps["warnings"]) + "</ul></div>")

    tr = "".join(
        f'<tr><td>{r["fa"]}</td>'
        f'<td class="n">{toman(r["market_irr"])}</td>'
        f'<td class="n">{r["fine_grams"]:.4f}</td>'
        f'<td class="n em">{toman(r["per_pure_gram_irr"])}</td>'
        f'<td class="n">{pct(r.get("bubble_pct"))}</td>'
        f'<td class="n sub">{toman(r.get("implied_usd_irr"))}</td></tr>'
        for r in rows
    )

    implied_med = (payload.get("consistency") or {}).get("implied_median_usd_irr")
    gauge = fx_gauge(implied_med, a.get("usd_irr_used"))

    dealer_html = ""
    if dealer_inventory:
        d = dealer_view(payload, dealer_inventory)
        if d.get("status") == "OK":
            dl = "".join(
                f'<tr><td>{l["fa"]}</td><td class="n">{l["qty"]:,.0f}</td>'
                f'<td class="n">{l["market_toman"]:,.0f}</td>'
                f'<td class="n em">{l["premium_toman"]:,.0f}</td></tr>'
                for l in d["lines"]
            )
            dealer_html = (
                '<details><summary>حالت طلافروش — ارزش‌گذاری موجودی</summary>'
                '<div class="dbody">'
                '<div class="tw"><table><thead><tr><th>ابزار</th><th>تعداد</th>'
                '<th>ارزش بازار (تومان)</th><th>از این مبلغ، حباب</th></tr></thead>'
                f'<tbody>{dl}</tbody></table></div>'
                '<div class="alert ok" style="margin-top:14px"><b>خلاصه</b><ul>'
                + "".join(f"<li>{n}</li>" for n in d["notes"]) + "</ul></div>"
                "</div></details>"
            )

    return f"""<title>قطب‌نما طلا</title>
<style>{CSS}</style>
<div class="w">
<header>
  <h1>قطب‌نما — امروز طلا را چطور بخریم؟</h1>
  <p class="sub mono">{ts} · engine v{payload["engine_version"]}</p>
  <div class="gov">
    <span class="chip risk">دامنه پرریسک (مالی) — نیازمند بازبینی انسانی</span>
    <span class="chip">وضعیت: تعریف‌شده / تأییدنشده</span>
    <span class="chip">{"لنگرها هم‌زمان" if a["same_instant_legs"] else "لنگرها ناهم‌زمان"}</span>
  </div>
</header>

<div class="ans">
  <span class="eb">پاسخ کوتاه</span>
  <h2>{ps["answer"]}</h2>
  <p>{ps["why"]}</p>
  {f'<p>{ps["market_note"]}</p>' if ps.get("market_note") else ""}
  <span class="conf">اطمینان: {conf_fa.get(ps["confidence"], "—")}</span>
</div>

{alerts}

<div class="card">
  <h3>هر گرم طلای واقعی، از هر راه چقدر تمام می‌شود؟</h3>
  <p class="hint">ستون‌ها یعنی چقدر می‌پردازید. خط چین یعنی خودِ طلا چقدر می‌ارزد.
  هرچه ستون از خط چین بالاتر باشد، بیشتر بابت «شکلِ» طلا پول داده‌اید تا خودِ طلا.</p>
  {cost_chart(rows, (payload.get("arbitrage") or {}).get("reference_pure_gram_irr"))}
</div>

<div class="card">
  <h3>چقدر بیشتر از ارزش طلای داخلش می‌دهید؟</h3>
  <p class="hint">سمت راستِ خط یعنی گران‌تر از ارزش ذاتی، سمت چپ یعنی ارزان‌تر.</p>
  {bubble_chart(rows)}
</div>

<ol class="opts">{opts}</ol>

{dealer_html}

<details>
  <summary>نمای حرفه‌ای — اعداد کامل و روش محاسبه</summary>
  <div class="dbody">
    <div class="grid">
      <div class="k"><dt>طلای جهانی</dt><dd class="mono">{a["xau_usd"]:,.2f}<small>$/oz</small></dd></div>
      <div class="k"><dt>دلار (لحظه‌ای)</dt><dd class="mono">{toman(a["usd_irr_crypto"])}<small>ت</small></dd></div>
      <div class="k"><dt>دلار آزاد (روزانه)</dt><dd class="mono">{toman(a["usd_irr_cash"])}<small>ت</small></dd></div>
      <div class="k"><dt>پرمیوم تتر</dt><dd class="mono">{pct(a["tether_premium_pct"])}</dd></div>
      <div class="k"><dt>اسپرد</dt><dd class="mono">{a["usdt_spread_bps"]:.1f}<small>bps</small></dd></div>
      <div class="k"><dt>هر گرم طلای خالص</dt><dd class="mono">{toman((payload.get("arbitrage") or {}).get("reference_pure_gram_irr"))}<small>ت</small></dd></div>
    </div>

    {f'<h3 style="font-size:14px;margin:18px 0 4px">دلاری که بازار طلا حساب می‌کند</h3><p class="hint">اگر این دو خیلی از هم فاصله بگیرند، یا بازار طلا جلوتر از بازار ارز حرکت کرده یا یکی از قیمت‌ها کهنه است.</p>{gauge}' if gauge else ""}

    <div class="tw" style="margin-top:16px"><table>
      <thead><tr><th>ابزار</th><th>قیمت بازار (ت)</th><th>گرم طلای خالص</th>
      <th>تومان به ازای گرم خالص</th><th>حباب</th><th>دلار ضمنی (ت)</th></tr></thead>
      <tbody>{tr}</tbody>
    </table></div>

    <div class="alert ok" style="margin-top:16px">
      <b>روش محاسبه</b>
      <ul>
        <li>ارزش ذاتی = وزن × عیار × قیمت هر گرم طلای خالص.</li>
        <li>قیمت هر گرم طلای خالص = (انس جهانی ÷ ۳۱٫۱۰۳۵) × نرخ دلار.</li>
        <li>مشخصات وزن و عیار سکه‌ها از استاندارد منتشرشده بانک مرکزی؛ ثابت فیزیکی‌اند و کالیبره نمی‌شوند.</li>
        <li>«دلار ضمنی» با معکوس‌کردن همین رابطه از قیمت هر ابزار به‌دست می‌آید.</li>
      </ul>
    </div>
  </div>
</details>

<footer>
  <p><b>وضعیت این صفحه:</b> تعریف‌شده / تأییدنشده. دامنه مالی طبق سیاست ریسک،
  پرریسک طبقه‌بندی می‌شود و تا ثبت یک بازبینی انسانی، منتشرشده تلقی نمی‌شود.</p>
  <p><b>منابع:</b> قیمت ابزارهای داخلی از TGJU؛ نرخ لحظه‌ای دلار و طلای جهانی از
  Wallex (تتر و توکن‌های طلا). مشخصات فیزیکی سکه از استاندارد بانک مرکزی.</p>
  <p>{payload["disclaimer"]}</p>
</footer>
</div>"""
