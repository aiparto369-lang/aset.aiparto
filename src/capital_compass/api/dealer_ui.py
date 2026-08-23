"""
Dealer console.

A static page cannot ask a dealer for their inventory, so this one embeds the
current price table and the instrument specs and recomputes everything in the
browser as they type. No server, no account, no upload — which also means the
inventory never leaves their machine, and for someone typing the contents of
their safe into a web page, that is a feature worth stating plainly on the page.

Quantities persist in localStorage so the page is useful on the second visit.
Prices do not: they are stamped at build time and the page says how old they
are, because a dealer acting on a stale valuation is the one failure mode that
actually costs money here.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from capital_compass.api.compass_ui import stamp_fa
from capital_compass.market.instruments import INSTRUMENTS

TEHRAN = timezone(timedelta(hours=3, minutes=30))

CSS = """
:root{--ink:#05080C;--s1:#0C131B;--s2:#131C26;--etch:#1A2531;--etch2:#26333F;
--txt:#E2EAF1;--txt2:#8B9BA9;--txt3:#7E8F9E;--brass:#C9A227;--brass2:#B89430;
--glow:#5BE0C8;--warn:#E0B341;--bad:#F2604E;--good:#5BD6A0;}
*{box-sizing:border-box}
body{margin:0;background:var(--ink);color:var(--txt);direction:rtl;text-align:right;
font-family:Vazirmatn,"IRANSansX","Segoe UI",Tahoma,sans-serif;line-height:1.8;
padding:24px 16px 70px;font-size:15px}
.w{max-width:980px;margin:0 auto}
.mn{font-family:"JetBrains Mono",Consolas,monospace;direction:ltr;unicode-bidi:isolate;
font-variant-numeric:tabular-nums}
.hd{border-bottom:1px solid var(--etch2);padding-bottom:14px;margin-bottom:10px}
h1{margin:0 0 4px;font-size:clamp(20px,3.8vw,26px);font-weight:800}
h1 span{color:var(--brass);font-weight:400}
.sub{margin:0;font-size:12.5px;color:var(--txt3)}
.stale{display:inline-block;margin:12px 0 24px;font-size:12px;padding:5px 13px;
border:1px solid var(--brass2);color:var(--brass)}
.stale.old{border-color:var(--bad);color:var(--bad)}
.priv{font-size:12px;color:var(--txt3);border-inline-start:2px solid var(--etch2);
padding-inline-start:12px;margin:0 0 26px}
h2{font-size:15px;margin:30px 0 12px;font-weight:700;padding-top:20px;
border-top:1px solid var(--etch2)}
h2:first-of-type{border-top:0;padding-top:0;margin-top:0}
.inv{border:1px solid var(--etch2)}
.invr{display:grid;grid-template-columns:1fr 96px 128px 1fr;gap:14px;align-items:center;
padding:12px 16px;border-bottom:1px solid var(--etch)}
.invr:last-child{border-bottom:0}
.invr .nm{font-weight:600;font-size:14.5px}
.invr .nm small{display:block;color:var(--txt3);font-size:11.5px;font-weight:400}
.invr input{width:100%;background:var(--s2);border:1px solid var(--etch2);color:var(--txt);
padding:9px 11px;font-size:15px;text-align:center;font-family:"JetBrains Mono",monospace;
border-radius:0}
.invr input:focus{outline:none;border-color:var(--glow)}
.invr .vl{text-align:left;font-family:"JetBrains Mono",monospace;font-size:13px;
color:var(--txt2);direction:ltr}
.invr .vl b{color:var(--txt);display:block;font-size:14.5px}
.invr .vl s{color:var(--txt3);text-decoration:none;font-size:11.5px}
.tot{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
border:1px solid var(--etch2);border-top:0;background:var(--s1)}
.tot>div{padding:15px 17px;border-inline-end:1px solid var(--etch2)}
.tot>div:last-child{border-inline-end:0}
.tot dt{font-size:10.5px;letter-spacing:.09em;color:var(--txt3);margin:0 0 5px}
.tot dd{margin:0;font-size:19px;font-weight:700;font-family:"JetBrains Mono",monospace;
direction:ltr;text-align:right}
.tot dd small{font-size:11px;color:var(--txt3);font-weight:400;margin-inline-start:3px}
.tot dd.risk{color:var(--warn)}
.stress{border:1px solid var(--etch2);padding:0}
.sh{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;
padding:14px 17px;border-bottom:1px solid var(--etch)}
.sh b{font-size:14px}
.sh .d{font-family:"JetBrains Mono",monospace;font-size:17px;font-weight:700;direction:ltr}
.sh .d.neg{color:var(--bad)}.sh .d.pos{color:var(--good)}
.sn{padding:12px 17px;font-size:12px;color:var(--txt3);line-height:1.75}
.act{border-inline-start:2px solid var(--warn);padding:12px 16px;margin-bottom:9px;
background:var(--s1);font-size:13.5px}
.act b{color:var(--warn);font-size:12px;display:block;margin-bottom:4px}
.empty{color:var(--txt3);font-size:13.5px;padding:18px 0}
.tw{overflow-x:auto;border:1px solid var(--etch2)}
table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:520px}
th{background:var(--s2);padding:9px 12px;text-align:right;font-size:10.5px;
color:var(--txt2);border-bottom:1px solid var(--etch2);white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid var(--etch)}
tr:last-child td{border-bottom:0}
td.n{font-family:"JetBrains Mono",monospace;direction:ltr;text-align:left;
font-variant-numeric:tabular-nums;white-space:nowrap}
td.n.neg{color:var(--bad)}
footer{border-top:1px solid var(--etch2);margin-top:32px;padding-top:18px;
color:var(--txt3);font-size:11.5px}
footer p{margin:0 0 8px;line-height:1.85}
button{background:none;border:1px solid var(--etch2);color:var(--txt3);
padding:7px 15px;font-family:inherit;font-size:12px;cursor:pointer}
button:hover{border-color:var(--brass2);color:var(--brass)}
button:focus-visible{outline:2px solid var(--glow);outline-offset:2px}
input:focus-visible{outline:none}
"""

JS = """
const F=new Intl.NumberFormat('en-US');
const $=id=>document.getElementById(id);
function money(t){return F.format(Math.round(t));}
function pct(x,d){return (x>=0?'+':'')+(x*100).toFixed(d===undefined?1:d)+'\\u066A';}
function load(){try{return JSON.parse(localStorage.getItem('cc_inv')||'{}');}catch(e){return {};}}
function save(v){try{localStorage.setItem('cc_inv',JSON.stringify(v));}catch(e){}}

function compute(){
  const inv={}; let mv=0,iv=0,fg=0;
  const lines=[];
  for(const p of PRICES){
    const el=$('q_'+p.id); if(!el) continue;
    const pe=$('p_'+p.id);
    const unit=(parseFloat(pe&&pe.value)||0)*10;
    const q=parseFloat(el.value)||0;
    if(q>0) inv[p.id]={q:q,p:unit/10};
    const ie=$('i_'+p.id); if(ie) ie.textContent=F.format(Math.round(p.intrinsic/10));
    const m=q*unit, n=q*p.intrinsic;
    mv+=m; iv+=n; fg+=q*p.fine;
    const row=$('v_'+p.id);
    if(row){
      row.innerHTML = q>0
        ? '<b>'+money(m/10)+'</b><s>حباب '+money((m-n)/10)+' تومان</s>'
        : '<s>—</s>';
    }
    if(q>0&&n>0) lines.push({fa:p.fa,q:q,m:m,n:n,prem:(unit-p.intrinsic)/p.intrinsic});
  }
  save(inv);
  const pv=mv-iv;
  $('t_market').textContent=money(mv/10);
  $('t_intrinsic').textContent=money(iv/10);
  $('t_premium').textContent=money(pv/10);
  $('t_grams').textContent=fg.toFixed(1);
  $('t_share').textContent = mv>0 ? pct(pv/mv,1) : '—';

  const box=$('stressbox');
  if(mv<=0){ box.innerHTML='<div class="empty">برای دیدن سناریوها، تعداد اقلام را وارد کنید.</div>'; $('actbox').innerHTML=''; return; }

  let html='';
  for(const sc of SCENARIOS){
    let after=0;
    for(const l of lines) after += l.n*(1+sc.target);
    const d=after-mv, dp=d/mv;
    html += '<div class="stress"><div class="sh"><b>'+sc.label+'</b>'
         +  '<span class="d '+(d<0?'neg':'pos')+'">'+(d<0?'':'+')+money(d/10)+' تومان ('+pct(dp,1)+')</span></div>'
         +  '<div class="sn">'+sc.note+'</div></div>';
  }
  box.innerHTML=html;

  const acts=lines.filter(l=>l.prem!==null&&l.prem>0.03)
                  .sort((a,b)=>(b.m-b.n)-(a.m-a.n));
  $('actbox').innerHTML = acts.length
    ? acts.map(l=>'<div class="act"><b>حباب انباشته</b>«'+l.fa+'» با حباب '
        +pct(l.prem,1)+' مجموعاً <b style="display:inline;color:var(--txt)">'
        +money((l.m-l.n)/10)+'</b> تومان حباب روی دست شما دارد.</div>').join('')
    : '<div class="empty">هیچ قلمی با حباب قابل توجه در موجودی شما نیست.</div>';
}

window.addEventListener('DOMContentLoaded',()=>{
  const inv=load();
  for(const p of PRICES){
    const el=$('q_'+p.id);
    const pe=$('p_'+p.id);
    if(el){
      const v=inv[p.id];
      if(v&&typeof v==='object'){ el.value=v.q; if(pe&&v.p) pe.value=v.p; }
      else if(v){ el.value=v; }
      el.addEventListener('input',compute);
    }
    if(pe) pe.addEventListener('input',compute);
  }
  $('clear').addEventListener('click',()=>{
    for(const p of PRICES){const el=$('q_'+p.id); if(el) el.value='';}
    compute();
  });
  compute();
});
"""


def render(payload: dict, *, historical_median_premium: float | None = None) -> str:
    rows = {r["instrument_id"]: r
            for r in (payload.get("arbitrage") or {}).get("rows") or []}
    gen = datetime.fromisoformat(payload["generated_at"])
    age_min = (datetime.now(timezone.utc) - gen).total_seconds() / 60
    stamp = stamp_fa(gen)

    prices = []
    inputs = []
    for iid, inst in INSTRUMENTS.items():
        r = rows.get(iid)
        if not r:
            continue
        prices.append({
            "id": iid, "fa": inst.fa,
            "market": r["market_irr"],
            "intrinsic": r.get("intrinsic_irr") or 0.0,
            "fine": inst.fine_grams,
            "premium": r.get("bubble_pct"),
        })
        inputs.append(
            f'<div class="invr"><div class="nm">{inst.fa}'
            f'<small>ارزش طلای داخلش: <span id="i_{iid}">—</span> ت</small></div>'
            f'<input id="q_{iid}" type="number" min="0" step="any" inputmode="decimal" '
            f'placeholder="0" aria-label="تعداد {inst.fa}">'
            f'<input id="p_{iid}" type="number" min="0" step="any" inputmode="decimal" '
            f'value="{r["market_irr"] / 10:.0f}" aria-label="قیمت واحد {inst.fa} به تومان">'
            f'<div class="vl" id="v_{iid}"><s>—</s></div></div>'
        )

    scenarios = [{
        "label": "اگر حباب صفر شود",
        "target": 0.0,
        "note": ("فرض: حباب همه اقلام به صفر برسد و قیمت طلای جهانی و نرخ ارز "
                 "ثابت بماند. سناریو است، نه پیش‌بینی."),
    }]
    if historical_median_premium is not None:
        scenarios.append({
            "label": f"اگر حباب به میانه تاریخی برگردد "
                     f"({historical_median_premium * 100:+.1f}٪)",
            "target": historical_median_premium,
            "note": ("فرض: حباب به میانه چندساله خودش برگردد، با ثابت ماندن "
                     "طلای جهانی و نرخ ارز."),
        })

    stale_cls = "stale old" if age_min > 90 else "stale"
    stale_txt = (f"قیمت‌ها {age_min:,.0f} دقیقه پیش ثبت شده‌اند"
                 if age_min >= 1 else "قیمت‌ها همین الان ثبت شده‌اند")

    return f"""<title>کنسول طلافروش</title>
<style>{CSS}</style>
<div class="w" dir="rtl" lang="fa">
<div class="hd">
  <h1>کنسول طلافروش <span>· قطب‌نما</span></h1>
  <p class="sub">{stamp}</p>
</div>
<span class="{stale_cls}">{stale_txt}</span>

<p class="priv">موجودی شما فقط در همین مرورگر ذخیره می‌شود و به هیچ سروری
ارسال نمی‌گردد. با بستن صفحه پاک نمی‌شود؛ با دکمه «پاک کردن» حذف می‌شود.</p>

<h2>موجودی خود را وارد کنید</h2>
<p class="priv" style="border-inline-start-color:var(--glow)">قیمت‌ها قابل ویرایش‌اند —
نرخ خودتان را بزنید. محاسبه فقط به ارزش ذاتی طلا تکیه می‌کند که از بازار
جهانی و صرافی‌های ایرانی می‌آید، نه به قیمت اعلامی هیچ سایتی.</p>
<div class="invr" style="background:var(--s2);font-size:11px;color:var(--txt3)">
<div>قلم</div><div style="text-align:center">تعداد</div>
<div style="text-align:center">قیمت واحد (ت)</div><div style="text-align:left">ارزش</div></div>
<div class="inv">{"".join(inputs)}</div>
<div class="tot">
  <div><dt>ارزش کل به قیمت امروز</dt><dd><span id="t_market">0</span><small>ت</small></dd></div>
  <div><dt>ارزش خودِ طلا</dt><dd><span id="t_intrinsic">0</span><small>ت</small></dd></div>
  <div><dt>حباب (در معرض ریسک)</dt><dd class="risk"><span id="t_premium">0</span><small>ت</small></dd></div>
  <div><dt>سهم حباب</dt><dd class="risk"><span id="t_share">—</span></dd></div>
  <div><dt>طلای خالص</dt><dd><span id="t_grams">0</span><small>گرم</small></dd></div>
</div>
<p style="margin-top:14px"><button id="clear" type="button">پاک کردن موجودی</button></p>

<h2>اگر حباب جمع شود چه می‌شود؟</h2>
<div id="stressbox"></div>

<h2>کجای موجودی، حباب انباشته دارد؟</h2>
<div id="actbox"></div>

<footer>
  <p><b>این ابزار چه می‌کند:</b> ارزش موجودی را به دو بخش تفکیک می‌کند —
  ارزش خودِ طلا، و حبابی که می‌تواند بدون هیچ تغییری در قیمت طلا از بین برود.
  سناریوها قیمت طلا و ارز را ثابت نگه می‌دارند تا فقط ریسک حباب جدا شود.</p>
  <p><b>چه نمی‌کند:</b> جهت بازار را پیش‌بینی نمی‌کند و نمی‌گوید چه بخرید یا
  بفروشید. گردش موجودی و تقاضای مشتری شما را نمی‌بیند.</p>
  <p>{payload.get("disclaimer", "")}</p>
</footer>
</div>
<script>
const PRICES={json.dumps(prices, ensure_ascii=False)};
const SCENARIOS={json.dumps(scenarios, ensure_ascii=False)};
{JS}
</script>"""
