from dataclasses import dataclass
from statistics import median
@dataclass(frozen=True)
class PremiumCalibration:
    status:str; sample_size:int; median:float|None; mad:float|None; low_threshold:float|None; high_threshold:float|None; reason:str
def calibrate(values,min_samples=60,mad_multiplier=2.5):
    x=[float(v) for v in values if v is not None]
    if len(x)<min_samples:return PremiumCalibration("INSUFFICIENT_SAMPLE",len(x),median(x) if x else None,None,None,None,f"Need >= {min_samples}.")
    m=median(x);mad=median([abs(v-m) for v in x])
    if mad<=1e-12:return PremiumCalibration("DEGENERATE_SAMPLE",len(x),m,mad,None,None,"Zero MAD.")
    return PremiumCalibration("CALIBRATED",len(x),m,mad,m-mad_multiplier*mad,m+mad_multiplier*mad,"Median/MAD.")
def classify(value,c):
    if c.status!="CALIBRATED":return "UNKNOWN"
    return "LOW" if value<c.low_threshold else ("HIGH" if value>c.high_threshold else "NORMAL")
