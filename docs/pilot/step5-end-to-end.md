# Step 5 — First Pilot Record & End-to-End Decision Pipeline

## وضعیت
از این مرحله به بعد، مسیر کامل زیر پیاده شده است:

`Decision Input → Hard Gates → Decision Engine → Audit Record → Persian Decision Card`

اما هنوز برای **تصمیم واقعی بازار** باید Snapshot واقعی و Stateهای حاصل از همان Snapshot وارد شوند.

## اجرای نمونه‌ی کنترل‌شده
این ورودی فقط Fixture تست است و داده بازار واقعی نیست:

```bash
PYTHONPATH=src python -m capital_compass.orchestration.pilot_decision   --decision-input fixtures/pilot/records/decision-input-sample.json   --output-dir fixtures/pilot/records/run-sample
```

## اولین Pilot واقعی
برای اولین Pilot واقعی:
1. XAU provider باید Preflight حقوق/فنی را PASS کند.
2. دو Observation مستقل USD/IRR ثبت شوند.
3. Snapshot واقعی ساخته و Freeze شود.
4. State Classifier روی Snapshot اجرا شود.
5. هر State همراه Evidence IDs ثبت شود.
6. `decision-input.json` از Structured States ساخته شود.
7. Decision Engine اجرا شود.
8. Audit Record و Decision Card تولید شوند.
9. Human label مستقل، قبل از دیدن Decision، روی Snapshot ثبت شود.
10. نتیجه وارد Pilot Dataset شود.

## اصل مهم
در این فاز هیچ ابزار اجازه ندارد state یا price مفقود را حدس بزند. اگر ورودی واقعی ناقص است، `READY_LIMITED / REVIEW_REQUIRED / BLOCKED` باید استفاده شود.
