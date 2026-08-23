# Capital Compass v3 — Gold/FX Labeling Manual v0.1.0

## هدف
این Manual برای ساخت Golden Set اولیه است. Labeler فقط وضعیت بازار در **لحظه Snapshot** را برچسب می‌زند. داده آینده، نتیجه معامله و تصمیم سیستم باید از Labeler پنهان بماند.

## قواعد عمومی
1. `UNKNOWN` با `NEUTRAL/RANGE` فرق دارد: UNKNOWN یعنی داده کافی نیست.
2. `TRANSITION` فقط وقتی استفاده شود که ساختار قبلی در حال تغییر است ولی ساختار جدید هنوز تأیید نشده.
3. خبر یا روایت به‌تنهایی Price State نمی‌سازد.
4. یک Quote غیرعادی نباید Trend بسازد.
5. اگر اختلاف داده Material است، ابتدا `EVIDENCE_CONFLICT_STATE` را ثبت کن؛ سپس سایر Stateها فقط در صورت امکان قابل اتکا Label شوند.
6. Label بر اساس داده‌ی موجود در Snapshot است، نه آنچه بعداً اتفاق افتاد.
7. اگر دو Label حرفه‌ای قابل دفاع‌اند، `ambiguity=AMBIGUOUS` و alternative label ثبت شود.

---

## DATA_STATE

### READY
همه ورودی‌های M1 موردنیاز موجود، تازه، semantic-compatible و بدون تعارض مادی‌اند.

### READY_LIMITED
ورودی‌های Critical کافی‌اند ولی یک یا چند ورودی Supporting محدود/قدیمی/ناقص است.

### REVIEW_REQUIRED
تعارض مادی، timestamp mismatch قابل توجه، ambiguity در instrument یا anomaly حل‌نشده وجود دارد.

### BLOCKED
یک ورودی Critical مفقود/نامعتبر است یا unit/source integrity قابل اعتماد نیست.

---

## FX_PRICE_STATE

### UPTREND
ساختار قیمت معتبر نشان‌دهنده Higher High + Higher Low است و افزایش صرفاً حاصل یک quote منفرد یا dislocation نیست.

### DOWNTREND
Lower High + Lower Low یا شکست معتبر ساختار حمایتی.

### RANGE
سقف/کف مشخص و نبود sequence جهت‌دار معتبر.

### TRANSITION
ساختار قبلی در حال شکستن است اما روند جدید هنوز تأیید نشده.

### DISLOCATED
Price discovery قابل اعتماد نیست؛ معمولاً همراه با spread غیرعادی، divergence بین منابع یا quote continuity ضعیف.

### UNKNOWN
داده ساختاری کافی وجود ندارد.

---

## FX_STRESS_STATE

### NORMAL
spread، dispersion و quote continuity در محدوده عادی همان نمونه/دوره‌اند.

### ELEVATED
نشانه‌های اولیه stress وجود دارد ولی market functioning هنوز قابل اتکاست.

### HIGH
چند علامت مادی stress همزمان دیده می‌شود: widening spread، dispersion، jump velocity یا دسترسی ضعیف.

### DISLOCATED
price discovery به حدی مختل شده که Trend clean قابل اتکا نیست.

### UNKNOWN
داده microstructure کافی نیست.

> تا قبل از Calibration از thresholdهای عددی ثابت استفاده نکن.

---

## XAU_PRICE_STATE

### UPTREND / DOWNTREND / RANGE / TRANSITION
همان منطق Market Structure با داده XAUUSD.

### EXTENDED_UP / EXTENDED_DOWN
حرکت جهت‌دار معتبر است ولی فاصله از آخرین structure/retest و سرعت حرکت غیرعادی به نظر می‌رسد. در v0.1 این label باید با `AMBIGUOUS` علامت بخورد مگر شواهد بسیار روشن باشد.

### UNKNOWN
داده کافی نیست.

---

## GOLD_PREMIUM_STATE / COIN_PREMIUM_STATE

### LOW
Premium نسبت به baseline شناخته‌شده پایین است.

### NORMAL
Premium در محدوده معمول baseline موجود است.

### HIGH
Premium به‌طور مادی بالاتر از baseline است.

### UNKNOWN
baseline کافی نداریم یا inputهای implied value ناسازگارند.

> در Pilot اولیه، تا زمانی که baseline تاریخی معتبر ساخته نشده، `HIGH/LOW` فقط در caseهای واضح و با ambiguity flag استفاده شود.

---

## TIMING_STATE

### SETUP_FORMING
ساختار ورودی در حال شکل‌گیری است ولی confirmation کامل نشده.

### SETUP_CONFIRMED
شرایط Rule تعریف‌شده برای setup برقرار است.

### RETESTING
قیمت در حال test کردن سطح یا ساختار شکسته‌شده است.

### EXTENDED
ورود جدید از نظر geometry/price structure دیر شده است.

### INVALIDATED
Setup قبلی دیگر معتبر نیست.

### NO_SETUP
داده کافی است ولی setup قابل دفاعی وجود ندارد.

### UNKNOWN
داده کافی برای ارزیابی timing وجود ندارد.

---

## EVIDENCE_CONFLICT_STATE

### NONE
منابع مهم سازگارند یا اختلاف‌شان با semantics توضیح داده شده.

### MINOR
اختلاف وجود دارد ولی تصمیم مادی را تغییر نمی‌دهد.

### MATERIAL
اختلاف می‌تواند State یا Action را تغییر دهد.

### CRITICAL
نمی‌توان تعیین کرد کدام داده برای تصمیم معتبر است.

---

## Adjudication
اختلاف Labelerها فقط در موارد disagreement وارد صف adjudication شود. Adjudicator باید:
- final label
- rationale کوتاه
- evidence refs
- ambiguity flag
را ثبت کند.

## ممنوعیت‌ها
- دیدن داده آینده
- دیدن تصمیم سیستم قبل از Label
- تغییر Label صرفاً برای PASS شدن مدل
- استفاده از احساس بازار بدون evidence
