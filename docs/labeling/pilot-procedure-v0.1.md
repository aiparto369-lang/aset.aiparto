# Gold/FX Pilot Dataset Procedure v0.1

## هدف
جمع‌آوری **60 Snapshot routine** + Snapshotهای event/stress/transition واقعی، بدون جعل داده و بدون استفاده از داده آینده.

## ترتیب اجرا
1. `capture-plan.json` را به‌عنوان برنامه‌ی ثبت routine استفاده کن.
2. هر Capture واقعی باید با Source Registry معتبر پر شود.
3. Snapshot ناقص را حذف نکن؛ با `DATA_STATE` مناسب نگه دار تا Failure Modeها هم در Dataset بمانند.
4. بعد از تکمیل هر Snapshot، hash و timestamp ثبت و فایل immutable شود.
5. Labeler A و B مستقل برچسب بزنند.
6. Labelerها تصمیم سیستم و داده بعد از `as_of` را نبینند.
7. اختلاف‌ها به adjudication بروند.
8. بعد از 30–50 Snapshot اول، Manual بازبینی شود.
9. بعد از اصلاح Manual، Pilot ادامه یابد.
10. Threshold عددی premium/spread/stress از همین Pilot به‌تنهایی نهایی نشود؛ فقط distribution اولیه ساخته شود.

## Coverage هدف
Routine تنها کافی نیست. تا پایان Pilot باید حداقل نمونه‌هایی از این وضعیت‌ها دیده/ثبت شوند:
- uptrend
- downtrend
- range
- transition
- data conflict
- stress/dislocation
- elevated premium
- event-driven move

اگر بازار در طول Pilot یکی از این وضعیت‌ها را تولید نکرد، آن coverage به G2 adversarial/synthetic testing واگذار می‌شود و به‌عنوان Live coverage ادعا نمی‌شود.

## خروجی Pilot
- Snapshot count
- State distribution
- Missing-data rate
- Conflict rate
- Labeler agreement
- Ambiguity rate
- Critical classification errors
- Decision stability
- Unnecessary block rate
