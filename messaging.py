"""
messaging.py — بناء نص الطلب وتوليد رابط wa.me (بدون أي أسرار أو شبكة).

الإرسال عبر wa.me فقط:
    https://wa.me/<رقم>?text=<نص مُرمّز URL-encoded>
هذا يفتح محادثة واتساب بالنص جاهزاً؛ العميل يضغط «إرسال». (لا إرسال تلقائي.)

قيد الطول: واتساب يقطع النصوص الطويلة، والعربية تتضخّم بعد الترميز
(كل حرف عربي ≈ 9 أحرف %XX). لذا:
  - نبني النص الكامل، نُرمّزه، وإن تجاوز حدّاً آمناً نتحوّل تلقائياً
    إلى صيغة مختصرة («الكود ×الكمية» + الإجمالي).
"""
from __future__ import annotations
import urllib.parse

CURRENCY = "د.ك"
# حدّ آمن لطول النص بعد الترميز قبل التحوّل للمختصر (واتساب يقطع قرب ~2000)
SAFE_ENCODED_LEN = 1800


def fmt_money(value: float | None) -> str:
    """تنسيق محاسبي: فاصلة آلاف + ثلاث خانات عشرية (الدينار) + العملة."""
    if value is None:
        return "-"
    return f"{value:,.3f} {CURRENCY}"


def _short(text: str, limit: int = 22) -> str:
    """اسم مقتطع للصيغة المختصرة حين لا يوجد كود."""
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_full(order: dict, company: str) -> str:
    """الصيغة الكاملة: أسماء كاملة + سعر الوحدة + إجمالي السطر + الإجمالي."""
    lines = [
        f"🧾 طلب جديد — {company}",
        f"التاريخ: {order['date']}",
    ]
    if order.get("customer"):
        lines.append(f"العميل: {order['customer']}")
    lines.append("—————————————")
    for i, it in enumerate(order["items"], 1):
        unit = it.get("unit") or "قطعة"
        unit_price = it.get("price")
        if unit_price is not None:
            line_total = unit_price * it["qty"]
            lines.append(f"{i}. {it['name']} — {it['qty']} {unit} = {fmt_money(line_total)}")
        else:
            lines.append(f"{i}. {it['name']} — {it['qty']} {unit}")
    lines.append("—————————————")
    lines.append(f"الإجمالي: {fmt_money(order['total'])}")
    return "\n".join(lines)


def format_compact(order: dict, company: str) -> str:
    """الصيغة المختصرة: «الكود ×الكمية» (أو اسم مقتطع) + الإجمالي فقط."""
    lines = [f"طلب — {company} — {order['date']}"]
    if order.get("customer"):
        lines.append(f"العميل: {order['customer']}")
    for it in order["items"]:
        tag = it.get("code") or _short(it["name"])
        unit = it.get("unit") or "قطعة"
        lines.append(f"{tag} ×{it['qty']} {unit}")
    lines.append(f"الإجمالي: {fmt_money(order['total'])}")
    return "\n".join(lines)


def build_message(order: dict, company: str, mode: str = "auto") -> tuple[str, bool]:
    """
    يبني نص الرسالة. mode ∈ {auto, full, compact}.
    يعيد (النص, هل_استُخدم_المختصر).
    auto: كامل ما لم يتجاوز الطول المُرمّز الحدّ الآمن، عندها مختصر.
    """
    if mode == "compact":
        return format_compact(order, company), True
    full = format_full(order, company)
    if mode == "full":
        return full, False
    if len(urllib.parse.quote(full)) <= SAFE_ENCODED_LEN:
        return full, False
    return format_compact(order, company), True


def clean_number(number: str) -> str:
    """يُبقي الأرقام فقط (يزيل + ومسافات ورموزاً). صيغة دولية بدون +."""
    return "".join(ch for ch in str(number) if ch.isdigit())


def whatsapp_link(number: str, text: str) -> str:
    """يولّد رابط wa.me بنص مُرمّز. بدون رقم: يختار المستخدم جهة الاتصال."""
    num = clean_number(number)
    encoded = urllib.parse.quote(text)
    return f"https://wa.me/{num}?text={encoded}" if num else f"https://wa.me/?text={encoded}"
