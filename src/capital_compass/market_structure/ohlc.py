from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class Bar: ts:str;open:float;high:float;low:float;close:float;stale:bool=False
@dataclass(frozen=True)
class Pivot: index:int;ts:str;kind:str;price:float;confirmed_index:int;confirmed_at:str
@dataclass(frozen=True)
class StructureResult: state:str;pivots:list;last_break:str|None;confidence:str;reason_codes:list;limitations:list
def valid(b):return b.open>0 and b.low>0 and b.high>=max(b.open,b.close,b.low) and b.low<=min(b.open,b.close,b.high)
def sanitize(bars):
    o=[];seen=set()
    for b in bars:
        k=(b.ts,b.open,b.high,b.low,b.close)
        if b.stale or not valid(b) or k in seen:continue
        seen.add(k);o.append(b)
    return o
def pivots(bars,left=2,right=2):
    x=sanitize(bars);o=[]
    for i in range(left,len(x)-right):
        w=x[i-left:i+right+1];ci=i+right
        if x[i].high==max(z.high for z in w) and sum(z.high==x[i].high for z in w)==1:o.append(Pivot(i,x[i].ts,"HIGH",x[i].high,ci,x[ci].ts))
        if x[i].low==min(z.low for z in w) and sum(z.low==x[i].low for z in w)==1:o.append(Pivot(i,x[i].ts,"LOW",x[i].low,ci,x[ci].ts))
    return sorted(o,key=lambda p:(p.confirmed_index,p.kind))
def classify(bars,left=2,right=2):
    x=sanitize(bars)
    if len(x)<max(7,left+right+3):return StructureResult("UNKNOWN",[],None,"HIGH",["MS-INSUFFICIENT-BARS"],[])
    ps=pivots(x,left,right);hs=[p for p in ps if p.kind=="HIGH"];ls=[p for p in ps if p.kind=="LOW"]
    if len(hs)<2 or len(ls)<2:return StructureResult("UNKNOWN",[asdict(p) for p in ps],None,"HIGH",["MS-INSUFFICIENT-PIVOTS"],[])
    h1,h2=hs[-2:];l1,l2=ls[-2:];hh=h2.price>h1.price;hl=l2.price>l1.price;lh=h2.price<h1.price;ll=l2.price<l1.price
    br="BOS_UP" if x[-1].close>h2.price else ("BOS_DOWN" if x[-1].close<l2.price else None)
    if hh and hl:s,rc="UPTREND",["MS-HH","MS-HL"]
    elif lh and ll:s,rc="DOWNTREND",["MS-LH","MS-LL"]
    elif (hh and ll) or (lh and hl):s,rc="TRANSITION",["MS-MIXED-PIVOTS"]
    else:s,rc="RANGE",["MS-NO-DIRECTIONAL-SEQUENCE"]
    return StructureResult(s,[asdict(p) for p in ps],br,"MODERATE",rc,[])
def detect_retest(bars,result,tolerance):
    if tolerance is None or tolerance<=0:raise ValueError("retest tolerance must be calibrated/configured")
    x=sanitize(bars)
    if not x:return "UNKNOWN"
    hs=[p for p in result.pivots if p["kind"]=="HIGH"];ls=[p for p in result.pivots if p["kind"]=="LOW"];last=x[-1]
    if result.state=="UPTREND" and hs:
        lv=hs[-1]["price"]
        if last.low<=lv*(1+tolerance) and last.close>=lv:return "RETESTING"
    if result.state=="DOWNTREND" and ls:
        lv=ls[-1]["price"]
        if last.high>=lv*(1-tolerance) and last.close<=lv:return "RETESTING"
    return "NO_SETUP"
