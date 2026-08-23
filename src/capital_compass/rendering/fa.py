from __future__ import annotations

ACTION_FA = {
    "ACCUMULATE":"افزایش موقعیت",
    "STAGED_ENTRY":"ورود پله‌ای",
    "TACTICAL_ENTRY":"ورود تاکتیکی",
    "HOLD":"نگهداری",
    "WAIT":"صبر",
    "REDUCE":"کاهش موقعیت",
    "EXIT":"خروج",
    "AVOID":"عدم ورود",
    "INSUFFICIENT_EDGE":"مزیت کافی وجود ندارد",
    "DECISION_BLOCKED":"تصمیم مسدود است"
}
SIZE_FA = {
    "ZERO":"بدون موقعیت جدید",
    "PROBE":"آزمایشی",
    "SMALL":"کوچک",
    "MODERATE":"متوسط",
    "LARGE_ELIGIBLE":"واجد شرایط بررسی برای موقعیت بزرگ"
}

def render_fa(decision_input: dict, result: dict) -> str:
    instrument = decision_input["instrument"]
    action = ACTION_FA[result["preferred_action"]]
    size = SIZE_FA[result["size_capability"]]
    reasons = "، ".join(result["reason_codes"]) if result["reason_codes"] else "—"
    return (
        f"تصمیم فعلی\n"
        f"دارایی/ابزار: {instrument}\n"
        f"اقدام: {action}\n"
        f"شدت/اندازه مجاز: {size}\n"
        f"کد دلایل: {reasons}\n"
        f"این کارت خلاصه‌ی Structured Decision است و جایگزین Audit Record نیست."
    )
