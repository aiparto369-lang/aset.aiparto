# Step 8 — Blind Human A/B Labeling & Adjudication

## هدف
این مرحله عمداً **Human Judgment** را از System Judgment جدا می‌کند. هیچ Label انسانی در این بسته جعل نشده است.

## طراحی
- 9 packet برای Labeler A
- 9 packet برای Labeler B
- هر packet شامل Snapshot/Evidence است
- Decision Result و System State از packet حذف شده
- Future outcome نیز مخفی است
- submissionهای A/B در دو مسیر جدا ذخیره می‌شوند
- Agreement فقط روی submissionهای کامل محاسبه می‌شود
- disagreementها خودکار وارد adjudication queue می‌شوند

## Workflow
1. Labeler A فقط پوشه `labeling/packets/A` را ببیند.
2. Labeler B فقط پوشه `labeling/packets/B` را ببیند.
3. هرکدام فایل متناظر `labeling/submissions/<A|B>/PKT-xxx.json` را کامل کنند.
4. هیچ‌کدام `fixtures/live/.../decision-*` یا `states.json` را قبل از submission نبینند.
5. پس از تکمیل هر دو:
   ```bash
   PYTHONPATH=src python -m capital_compass.labeling.run_agreement .
   ```
6. `labeling/reports/agreement-report.json` بررسی شود.
7. فقط disagreementها وارد `labeling/adjudication/queue.json` شوند.
8. Adjudicator final label را ثبت کند.
9. سپس و فقط سپس Human-vs-System comparison اجرا شود.

## معیارها
برای این 9 record، عدد Kappa به‌تنهایی معیار Release نیست؛ sample کوچک است. تمرکز:
- raw agreement
- field-level disagreement
- ambiguity
- critical disagreement
- UNKNOWN-vs-directional disagreements

## Gate
تا زمانی که دو Labeler مستقل واقعی submission نکرده‌اند:
`HUMAN_VALIDATION_STATUS = PENDING`

هیچ ادعای Human agreement یا classifier accuracy مجاز نیست.
