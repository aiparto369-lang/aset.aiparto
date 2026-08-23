"""
Telegram delivery.

Two things this deliberately does not do:

  * It does not send on every cycle. An alert channel that fires constantly gets
    muted, and a muted channel is worth nothing on the day it matters. The runner
    decides materiality; this module only formats and sends.
  * It does not tell anyone to buy or sell. Messages state what was measured and
    what changed. The distinction is not cosmetic — a signal service and a
    decision-support tool sit on different sides of a regulatory line.

Credentials come from the environment, never from a file in the repo:
    CC_TELEGRAM_TOKEN   bot token from @BotFather
    CC_TELEGRAM_CHAT    chat id (a channel id looks like -100xxxxxxxxxx)
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.telegram.org/bot{token}/{method}"
TEHRAN = timezone(timedelta(hours=3, minutes=30))


class TelegramNotConfigured(RuntimeError):
    pass


def _credentials() -> tuple[str, str]:
    tok = os.getenv("CC_TELEGRAM_TOKEN")
    chat = os.getenv("CC_TELEGRAM_CHAT")
    if not tok or not chat:
        raise TelegramNotConfigured(
            "CC_TELEGRAM_TOKEN and CC_TELEGRAM_CHAT must be set. "
            "Nothing is sent without them."
        )
    return tok, chat


def send(text: str, *, disable_preview: bool = True) -> dict:
    tok, chat = _credentials()
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true" if disable_preview else "false",
    }).encode()
    req = urllib.request.Request(API.format(token=tok, method="sendMessage"), data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def check() -> dict:
    """Verify the bot credentials without sending anything to the channel."""
    tok, _ = _credentials()
    with urllib.request.urlopen(API.format(token=tok, method="getMe"), timeout=15) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _t(irr: float | None) -> str:
    return "—" if irr is None else f"{irr / 10:,.0f}"


def format_alert(entry: dict, *, url: str | None = None) -> str:
    """
    The message.

    Structured so the first line survives a lock-screen notification: what
    changed, then the numbers, then why we sent it.
    """
    when = entry.get("at_tehran", "")
    prem = entry.get("coin_premium")
    lines = [
        f"<b>قطب‌نما · {entry.get('label', '—')}</b>",
        f"<code>{when}</code> به وقت تهران",
        "",
    ]
    for r in entry.get("change_reasons") or []:
        lines.append(f"• {r}")
    if entry.get("change_reasons"):
        lines.append("")

    lines += [
        f"حباب سکه امامی: <b>{prem * 100:+.2f}٪</b>" if prem is not None
        else "حباب سکه: نامشخص",
        f"دلار: <b>{_t(entry.get('usd_irr'))}</b> تومان",
        f"طلای جهانی: <b>{entry.get('xau_usd', 0):,.2f}</b> دلار",
    ]
    tp = entry.get("tether_premium_pct")
    if tp is not None:
        lines.append(f"پرمیوم تتر: <b>{tp * 100:+.2f}٪</b>")

    conf = entry.get("confidence")
    if conf is not None:
        lines.append(f"اطمینان خوانش: {conf * 100:.0f}٪")

    if url:
        lines += ["", f'<a href="{url}">مشاهده قطب‌نمای کامل</a>']

    lines += [
        "",
        "<i>تحلیل ارزش نسبی بر پایه داده عمومی. توصیه سرمایه‌گذاری نیست.</i>",
    ]
    return "\n".join(lines)


def format_digest(rows: list[dict]) -> str:
    """End-of-day summary from the ledger — sent once, not per tick."""
    if not rows:
        return "امروز هیچ خوانش معتبری ثبت نشد."
    first, last = rows[0], rows[-1]
    p0, p1 = first.get("coin_premium"), last.get("coin_premium")
    f0, f1 = first.get("usd_irr"), last.get("usd_irr")
    out = [
        f"<b>خلاصه روز · {last.get('at_tehran', '')[:10]}</b>",
        f"تعداد خوانش معتبر: {len(rows)}",
        "",
    ]
    if p0 is not None and p1 is not None:
        out.append(f"حباب سکه: {p0 * 100:+.2f}٪ ← <b>{p1 * 100:+.2f}٪</b> "
                   f"({(p1 - p0) * 100:+.2f} واحد)")
    if f0 and f1:
        out.append(f"دلار: {_t(f0)} ← <b>{_t(f1)}</b> تومان "
                   f"({(f1 - f0) / f0 * 100:+.2f}٪)")
    labels = [r.get("label") for r in rows if r.get("label")]
    if labels:
        out.append(f"جهت پایان روز: <b>{labels[-1]}</b>")
        if len(set(labels)) > 1:
            out.append(f"جهت در طول روز {len(set(labels))} بار تغییر کرد.")
    out += ["", "<i>توصیه سرمایه‌گذاری نیست.</i>"]
    return "\n".join(out)


def notifier(url: str | None = None):
    """
    Build the callback the runner invokes on a material change.

    Returns a function that never raises: a Telegram outage must not stop the
    schedule, so a send failure is reported and swallowed.
    """
    def _send(entry: dict) -> None:
        try:
            send(format_alert(entry, url=url))
            print("   → telegram sent")
        except TelegramNotConfigured as e:
            print(f"   → telegram skipped: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"   → telegram failed: {type(e).__name__}: {e}")
    return _send


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Telegram delivery for Capital Compass")
    ap.add_argument("--check", action="store_true", help="verify bot credentials")
    ap.add_argument("--digest", action="store_true", help="send today's digest")
    ap.add_argument("--ledger", default="reports/ledger.jsonl")
    ap.add_argument("--url", default=None, help="link included in messages")
    args = ap.parse_args()

    if args.check:
        print(json.dumps(check(), ensure_ascii=False, indent=2))
        return
    if args.digest:
        from capital_compass.api.runner import history
        today = datetime.now(TEHRAN).strftime("%Y-%m-%d")
        rows = [r for r in history(args.ledger)
                if str(r.get("at_tehran", "")).startswith(today)]
        print(send(format_digest(rows)).get("ok"))


if __name__ == "__main__":
    main()
