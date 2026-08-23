from dataclasses import dataclass
from statistics import median
@dataclass(frozen=True)
class StressCalibration:
    status:str; spread_median:float|None; spread_mad:float|None; dispersion_median:float|None; dispersion_mad:float|None; sample_size:int; reason:str
def _mad(xs):
    m=median(xs);return m,median([abs(x-m) for x in xs])
def calibrate_stress(spread_history_bps,dispersion_history_bps,min_samples=30):
    s=[float(x) for x in spread_history_bps if x is not None and x>=0];d=[float(x) for x in dispersion_history_bps if x is not None and x>=0];n=min(len(s),len(d))
    if n<min_samples:return StressCalibration("INSUFFICIENT_SAMPLE",None,None,None,None,n,f"Need >= {min_samples}.")
    sm,smad=_mad(s[-n:]);dm,dmad=_mad(d[-n:])
    if smad<=1e-12 or dmad<=1e-12:return StressCalibration("DEGENERATE_SAMPLE",sm,smad,dm,dmad,n,"Zero MAD.")
    return StressCalibration("CALIBRATED",sm,smad,dm,dmad,n,"Median/MAD baseline.")
def current_dispersion_bps(q):
    q=[float(x) for x in q if x is not None and x>0]
    if len(q)<2:return None
    m=median(q);return max(abs(x-m)/m*10000 for x in q)
def classify_stress(*,current_spread_bps,source_quotes,calibration,elevated_z=2.5,high_z=4.0,dislocated_z=7.0):
    if calibration.status!="CALIBRATED" or current_spread_bps is None:return {"state":"UNKNOWN","reason_codes":["STRESS-UNCALIBRATED"]}
    d=current_dispersion_bps(source_quotes)
    if d is None:return {"state":"UNKNOWN","reason_codes":["STRESS-INSUFFICIENT-SOURCES"]}
    sz=(float(current_spread_bps)-calibration.spread_median)/calibration.spread_mad;dz=(d-calibration.dispersion_median)/calibration.dispersion_mad;z=max(sz,dz)
    st="DISLOCATED" if z>=dislocated_z else ("HIGH" if z>=high_z else ("ELEVATED" if z>=elevated_z else "NORMAL"))
    return {"state":st,"spread_robust_z":sz,"dispersion_robust_z":dz,"max_robust_z":z,"reason_codes":["STRESS-ROBUST-BASELINE"]}
