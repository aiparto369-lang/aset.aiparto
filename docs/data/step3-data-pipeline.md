# Step 3 — Data Acquisition & Snapshot Pipeline v0.1

## هدف
در این مرحله هنوز **scraper تولیدی** یا feed تجاری انتخاب نمی‌کنیم. ابتدا Contract و Pipeline را تثبیت می‌کنیم تا هر Provider بعدی مجبور باشد به semantics یکسان وارد شود.

## اجزای اضافه‌شده
- Source Registry schema
- Source Registry اولیه با status حقوق/دسترسی
- Variable Registry
- Collector Protocol
- Manual Pilot Collector
- Explicit Unit Normalization
- Basic temporal/source conflict validation
- Deterministic gold conversion/premium calculations
- Immutable Snapshot Builder
- Data-pipeline tests

## تصمیم‌های عمدی
1. هیچ endpoint اینترنتی جعل نشده است.
2. TGJU/Bonbast به‌عنوان `MARKET_OBSERVATION` ثبت شده‌اند، نه منبع رسمی.
3. استفاده خودکار/تجاری از هر منبع قبل از بررسی terms/licensing به Production نمی‌رود.
4. LBMA benchmark با XAUUSD live یکی فرض نشده است.
5. هیچ threshold عددی برای conflict/spread/premium در این مرحله اختراع نشده است.
6. واحدها فقط با mapping صریح تبدیل می‌شوند؛ unit guessing ممنوع است.
7. Snapshot بعد از freeze با hash محافظت می‌شود.
8. داده Manual برای Pilot مجاز است، اما برای M1 باید provenance و cross-check داشته باشد.

## Provider Selection Gate
قبل از نوشتن Collector واقعی برای یک Source، این موارد باید PASS شوند:
- Semantic fit
- Timestamp semantics
- Quote type semantics
- Access reliability
- Terms/licensing
- Commercial-use rights
- Fallback availability
- Independence from cross-check source
- Failure behavior

## مرحله بعد
بعد از این Pipeline، کار بعدی انتخاب و اتصال **یک XAUUSD provider approved** و **دو observation route مستقل برای USD/IRR** است، سپس اولین Snapshotهای واقعی ثبت می‌شوند.
