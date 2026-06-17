"""
messaging.py — بناء نص الطلب (عربي/إنجليزي) وتوليد رابط wa.me (بدون أسرار أو شبكة).

الإرسال عبر wa.me فقط:
    https://wa.me/<رقم>?text=<نص مُرمّز URL-encoded>
قيد الطول: واتساب يقطع النصوص الطويلة، والعربية تتضخّم بعد الترميز،
لذا نتحوّل تلقائياً للصيغة المختصرة إن تجاوز النص حدّاً آمناً.
"""
from __future__ import annotations
import urllib.parse

from i18n import t

# حدّ آمن لطول النص بعد الترميز قبل التحوّل للمختصر (واتساب يقطع قرب ~2000)
SAFE_ENCODED_LEN = 1800


def fmt_money(value: float | None, lang: str = "ar") -> str:
    """تنسيق محاسبي: فاصلة آلاف + ثلاث خانات عشرية (الدينار) + العملة."""
    if value is None:
        return "-"
    return f"{value:,.3f} {t('currency', lang)}"


def _short(text: str, limit: int = 22) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_full(order: dict, company: str, lang: str = "ar", show_price: bool = True) -> str:
    """الصيغة الكاملة. show_price=False يحذف الأسعار والإجمالي من النص."""
    lines = [t("msg_new_order", lang, company=company), t("msg_date", lang, d=order["date"])]
    if order.get("customer"):
        lines.append(t("msg_customer", lang, c=order["customer"]))
    lines.append("—————————————")
    for i, it in enumerate(order["items"], 1):
        unit = it.get("unit") or ""
        qty_str = f"{it['qty']} {unit}".strip()
        if show_price and it.get("price") is not None:
            line_total = it["price"] * it["qty"]
            lines.append(f"{i}. {it['name']} — {qty_str} = {fmt_money(line_total, lang)}")
        else:
            lines.append(f"{i}. {it['name']} — {qty_str}")
    lines.append("—————————————")
    if show_price:
        lines.append(t("msg_total", lang, t=fmt_money(order["total"], lang)))
    return "\n".join(lines)


def format_compact(order: dict, company: str, lang: str = "ar", show_price: bool = True) -> str:
    """الصيغة المختصرة: «الكود ×الكمية» (+ الإجمالي إن كان السعر ظاهراً)."""
    lines = [t("msg_order_short", lang, company=company, d=order["date"])]
    if order.get("customer"):
        lines.append(t("msg_customer", lang, c=order["customer"]))
    for it in order["items"]:
        tag = it.get("code") or _short(it["name"])
        unit = it.get("unit") or ""
        lines.append(f"{tag} ×{it['qty']} {unit}".strip())
    if show_price:
        lines.append(t("msg_total", lang, t=fmt_money(order["total"], lang)))
    return "\n".join(lines)


def build_message(order: dict, company: str, lang: str = "ar", mode: str = "auto",
                  show_price: bool = True) -> tuple[str, bool]:
    """يبني نص الرسالة. mode ∈ {auto, full, compact}. يعيد (النص, هل_مختصر)."""
    if mode == "compact":
        return format_compact(order, company, lang, show_price), True
    full = format_full(order, company, lang, show_price)
    if mode == "full":
        return full, False
    if len(urllib.parse.quote(full)) <= SAFE_ENCODED_LEN:
        return full, False
    return format_compact(order, company, lang, show_price), True


def clean_number(number: str) -> str:
    """يُبقي الأرقام فقط (يزيل + ومسافات ورموزاً). صيغة دولية بدون +."""
    return "".join(ch for ch in str(number) if ch.isdigit())


def whatsapp_link(number: str, text: str) -> str:
    """يولّد رابط wa.me بنص مُرمّز. بدون رقم: يختار المستخدم جهة الاتصال."""
    num = clean_number(number)
    encoded = urllib.parse.quote(text)
    return f"https://wa.me/{num}?text={encoded}" if num else f"https://wa.me/?text={encoded}"
