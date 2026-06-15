"""
i18n.py — جدول الترجمة (عربي/إنجليزي) ودالة t().

ملاحظة: أسماء المنتجات نفسها تبقى كما هي في الملف (إنجليزية) — نترجم الواجهة فقط.
"""
from __future__ import annotations

LANGS = {"ar": "العربية", "en": "English"}

TR = {
    # عام
    "page_title":      {"ar": "كتالوج المبيعات", "en": "Sales Catalog"},
    "lang_label":      {"ar": "اللغة", "en": "Language"},
    "currency":        {"ar": "د.ك", "en": "KWD"},

    # وضع العميل
    "catalog_title":   {"ar": "🛍️ كتالوج {company}", "en": "🛍️ {company} Catalog"},
    "cart_empty_title":{"ar": "🛒 سلتك فارغة", "en": "🛒 Your cart is empty"},
    "cart_empty_hint": {"ar": "اختر أصنافاً وكمياتها من الكتالوج بالأسفل.",
                        "en": "Pick products and quantities from the catalog below."},
    "cart_summary":    {"ar": "🛒 سلتك: {n} صنف &nbsp;—&nbsp; الإجمالي: <span style='color:#0a7d2c'>{total}</span>",
                        "en": "🛒 Cart: {n} item(s) &nbsp;—&nbsp; Total: <span style='color:#0a7d2c'>{total}</span>"},
    "your_name":       {"ar": "👤 اسمك (اختياري)", "en": "👤 Your name (optional)"},
    "send_whatsapp":   {"ar": "📲 إرسال الطلب عبر واتساب", "en": "📲 Send order via WhatsApp"},
    "bad_rep":         {"ar": "رقم المندوب في الرابط غير صالح — اطلب من المندوب رابطاً صحيحاً.",
                        "en": "The rep number in the link is invalid — ask the rep for a correct link."},
    "compact_note":    {"ar": "ℹ️ الطلب كبير — استُخدمت صيغة مختصرة لتفادي قطع واتساب للرسالة.",
                        "en": "ℹ️ Large order — a compact format was used to avoid WhatsApp truncation."},
    "order_details":   {"ar": "👁️ تفاصيل الطلب", "en": "👁️ Order details"},

    # الفلاتر والكتالوج
    "category":        {"ar": "📂 اختر الفئة", "en": "📂 Choose category"},
    "all_categories":  {"ar": "كل الفئات ({n})", "en": "All categories ({n})"},
    "cat_with_count":  {"ar": "{c} ({n})", "en": "{c} ({n})"},
    "search":          {"ar": "🔍 بحث", "en": "🔍 Search"},
    "search_scope":    {"ar": "نطاق البحث", "en": "Search in"},
    "scope_all":       {"ar": "الكل", "en": "All"},
    "scope_name":      {"ar": "الاسم", "en": "Name"},
    "scope_code":      {"ar": "الكود", "en": "Code"},
    "scope_category":  {"ar": "الفئة", "en": "Category"},
    "showing":         {"ar": "عرض {a} من {b} صنف — صفحة {p}/{tp}",
                        "en": "Showing {a} of {b} items — page {p}/{tp}"},
    "prev":            {"ar": "⬅️ السابق", "en": "⬅️ Previous"},
    "next":            {"ar": "التالي ➡️", "en": "Next ➡️"},
    "page_x":          {"ar": "صفحة {p} / {tp}", "en": "Page {p} / {tp}"},

    # الكرت
    "code_label":      {"ar": "كود: {c}", "en": "Code: {c}"},
    "unit_label":      {"ar": "الوحدة: {u}", "en": "Unit: {u}"},
    "qty_label":       {"ar": "الكمية ({u})", "en": "Qty ({u})"},
    "in_stock":        {"ar": "متوفر", "en": "In stock"},
    "out_stock":       {"ar": "نافد", "en": "Out of stock"},
    "price_on_request":{"ar": "السعر عند الطلب", "en": "Price on request"},
    "no_image":        {"ar": "🖼️ لا توجد صورة", "en": "🖼️ No image"},

    # وضع المندوب
    "rep_title":       {"ar": "🧑‍💼 وضع المندوب", "en": "🧑‍💼 Rep mode"},
    "rep_caption":     {"ar": "تصفّح الكتالوج، وولّد رابطاً مخصصاً لعملائك يحمل رقمك.",
                        "en": "Browse the catalog and generate a custom link for your customers carrying your number."},
    "gen_link":        {"ar": "🔗 توليد رابط العميل", "en": "🔗 Generate customer link"},
    "rep_number":      {"ar": "📱 رقمك على واتساب (صيغة دولية بدون + أو أصفار، مثال: 9659xxxxxxx)",
                        "en": "📱 Your WhatsApp number (international format, no + or leading zeros, e.g. 9659xxxxxxx)"},
    "enter_number":    {"ar": "أدخل رقمك لتوليد الرابط.", "en": "Enter your number to generate the link."},
    "link_ready":      {"ar": "✅ رابط عميلك جاهز — انسخه وأرسله على واتساب:",
                        "en": "✅ Your customer link is ready — copy and share it on WhatsApp:"},
    "copy_link":       {"ar": "📋 نسخ الرابط", "en": "📋 Copy link"},
    "copied":          {"ar": "✅ تم النسخ", "en": "✅ Copied"},
    "replace_file":    {"ar": "📂 استبدال ملف الكتالوج (اختياري — لجلستك فقط)",
                        "en": "📂 Replace catalog file (optional — your session only)"},
    "replace_hint":    {"ar": "لتجربة ملف بترويسة مختلفة وضبط ربط الأعمدة يدوياً. العملاء يرون دائماً الملف المُضمّن.",
                        "en": "To try a file with a different header and map columns manually. Customers always see the bundled file."},
    "browse_catalog":  {"ar": "📖 تصفّح الكتالوج", "en": "📖 Browse catalog"},
    "rep_banner":      {"ar": "👋 أنت في وضع المندوب. للوصول كعميل استخدم رابطاً يحوي ?rep=رقمك.",
                        "en": "👋 You are in rep mode. To access as a customer, use a link containing ?rep=yourNumber."},
    "upload":          {"ar": "ارفع CSV/Excel", "en": "Upload CSV/Excel"},
    "back_bundled":    {"ar": "↩️ العودة للملف المُضمّن", "en": "↩️ Back to bundled file"},
    "loaded_n":        {"ar": "تم تحميل {n} صنفاً من ملفك (جلستك فقط).",
                        "en": "Loaded {n} items from your file (your session only)."},
    "load_error":      {"ar": "تعذّر تحميل ملف الكتالوج «{f}»: {e}",
                        "en": "Failed to load catalog file \"{f}\": {e}"},

    # نص الطلب (الرسالة)
    "msg_new_order":   {"ar": "🧾 طلب جديد — {company}", "en": "🧾 New order — {company}"},
    "msg_date":        {"ar": "التاريخ: {d}", "en": "Date: {d}"},
    "msg_customer":    {"ar": "العميل: {c}", "en": "Customer: {c}"},
    "msg_total":       {"ar": "الإجمالي: {t}", "en": "Total: {t}"},
    "msg_order_short": {"ar": "طلب — {company} — {d}", "en": "Order — {company} — {d}"},
}


# ترجمة وحدات البيع (الاختصارات الإنجليزية في قوائم الأسعار)
UNITS = {
    "PC":      {"ar": "قطعة", "en": "Piece"},
    "PKT":     {"ar": "باكت", "en": "Packet"},
    "CARTON":  {"ar": "كرتون", "en": "Carton"},
    "BOX":     {"ar": "علبة", "en": "Box"},
    "SET":     {"ar": "طقم", "en": "Set"},
    "DOZ":     {"ar": "دستة", "en": "Dozen"},
    "ROLL":    {"ar": "رول", "en": "Roll"},
    "REAM":    {"ar": "ريم", "en": "Ream"},
    "FILE":    {"ar": "ملف", "en": "File"},
    "BAG":     {"ar": "كيس", "en": "Bag"},
    "STAND":   {"ar": "ستاند", "en": "Stand"},
    "DISPLAY": {"ar": "ديسبلاي", "en": "Display"},
    "TRIP":    {"ar": "عبوة", "en": "Trip"},
}


def unit_name(unit: str, lang: str = "ar") -> str:
    """اسم الوحدة باللغة المطلوبة؛ يرجع القيمة الأصلية لو غير معروفة."""
    if not unit:
        return "قطعة" if lang == "ar" else "Piece"
    e = UNITS.get(str(unit).strip().upper())
    return e.get(lang, unit) if e else unit


def t(key: str, lang: str = "ar", **kw) -> str:
    """يعيد النص المترجم للمفتاح؛ يتراجع للعربية ثم للمفتاح نفسه."""
    entry = TR.get(key, {})
    s = entry.get(lang) or entry.get("ar") or key
    return s.format(**kw) if kw else s
