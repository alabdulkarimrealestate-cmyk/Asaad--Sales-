"""
data_loader.py — تحميل ملف الأصناف، كشف صيغة Shopify، الربط (Mapping)،
                 والتطبيع إلى جدول قياسي موحّد.

الجدول القياسي الناتج (قائمة قواميس)، كل عنصر = منتج فريد واحد:
    {
        "name":   str,          # اسم الصنف
        "code":   str,          # الكود/SKU (قد يكون فارغاً)
        "price":  float | None, # السعر (None لو مفقود)
        "stock":  float | None, # المخزون المتاح (None لو غير معروف)
        "unit":   str,          # الوحدة
        "images": list[str],    # روابط أونلاين (قد تكون فارغة)
    }

منطق التنظيف الأساسي لملف Shopify:
  - الملف ~2556 صفاً لكن المنتجات الفريدة أقل بكثير؛ الصفوف الزائدة صور إضافية.
  - نوحّد حسب عمود "Handle" ونأخذ الصف الأول الذي يحمل "Title" كصف رئيسي.
  - نجمّع كل روابط "Image Src" تحت نفس الـ Handle كقائمة صور للمنتج.
  - نعرض فقط المنتجات التي Status == active في صفها الرئيسي (نتجاهل draft/archived).
"""
from __future__ import annotations
import io
import pandas as pd

# الحقول القياسية التي يربط إليها المستخدم في واجهة الـ Mapping
STANDARD_FIELDS = {
    "name":     "اسم الصنف *",
    "price":    "السعر",
    "image":    "الصورة (رابط)",
    "code":     "الكود",
    "unit":     "الوحدة (قطعة/كرتون)",
    "stock":    "المخزون المتاح",
    "category": "الفئة",
    "status":   "الحالة (active/draft)",
}
REQUIRED_FIELDS = ["name"]  # الحد الأدنى لعمل التطبيق

# توقيع أعمدة تصدير Shopify
_SHOPIFY_SIGNATURE = {"Handle", "Title", "Variant Price", "Image Src"}


def is_url(value: str) -> bool:
    """هل القيمة رابط أونلاين؟ (نضع placeholder لغيرها وقت العرض)"""
    return isinstance(value, str) and value.strip().lower().startswith(("http://", "https://"))


def read_file(uploaded_file) -> pd.DataFrame:
    """
    يقرأ ملفاً (CSV أو Excel) إلى DataFrame.
    يرفع ValueError برسالة عربية واضحة عند الفشل.
    """
    name = (getattr(uploaded_file, "name", "") or "").lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file, dtype=str)
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("cp1256", errors="replace")  # ترميز عربي قديم احتياطي
            return pd.read_csv(io.StringIO(text), dtype=str)
        return pd.read_csv(uploaded_file, dtype=str)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"تعذّرت قراءة الملف: {exc}") from exc


def read_path(path: str) -> pd.DataFrame:
    """يقرأ ملف الأصناف المُضمّن مع التطبيق من مسار على القرص (CSV/Excel)."""
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig")


def is_shopify(df: pd.DataFrame) -> bool:
    """يتحقق إن كان الملف تصدير Shopify عبر توقيع الأعمدة."""
    return _SHOPIFY_SIGNATURE.issubset(set(df.columns))


def auto_mapping(df: pd.DataFrame) -> dict:
    """
    يقترح ربطاً تلقائياً بين الحقول القياسية وأعمدة الملف.
      - Shopify: ربط معروف مسبقاً (مع اختيار عمود السعر الأكثر امتلاءً بالبيانات).
      - غيره: تخمين تقريبي بمطابقة كلمات في أسماء الأعمدة.
    يعيد قاموساً: {standard_field: column_name | None}
    """
    cols = list(df.columns)
    if is_shopify(df):
        # "Price / Kuwait" قد يكون شبه فارغ — نختار عمود السعر الأكثر امتلاءً
        price_candidates = [c for c in ("Variant Price", "Price / Kuwait") if c in cols]
        price_col = max(price_candidates, key=lambda c: df[c].notna().sum(), default=None)
        # عمود وحدة بيع صريح إن أضافه المستخدم لاحقاً (Shopify لا يوفّره افتراضياً)
        unit_col = next((c for c in cols if str(c).strip().lower() in ("unit", "uom")
                         or "الوحدة" in str(c) or "وحدة" in str(c)), None)
        # الفئة: نفضّل "Type" المختصر على "Product Category" المتشعّب
        cat_col = "Type" if "Type" in cols else ("Product Category" if "Product Category" in cols else None)
        return {
            "name":     "Title",
            "price":    price_col,
            "image":    "Image Src",
            "code":     "Variant SKU" if "Variant SKU" in cols else None,
            "unit":     unit_col,
            "stock":    "Variant Inventory Qty" if "Variant Inventory Qty" in cols else None,
            "category": cat_col,
            "status":   "Status" if "Status" in cols else None,
        }

    # تخمين عام: مطابقة كلمات شائعة (عربي/إنجليزي) في أسماء الأعمدة
    lowered = {c: str(c).strip().lower() for c in cols}
    hints = {
        "name":     ["name", "title", "product", "اسم", "الصنف", "المنتج"],
        "price":    ["price", "سعر", "السعر"],
        "image":    ["image", "img", "photo", "صورة", "الصورة", "رابط"],
        "code":     ["sku", "code", "barcode", "كود", "الكود"],
        "unit":     ["unit", "uom", "وحدة", "الوحدة"],
        "stock":    ["qty", "quantity", "stock", "inventory", "مخزون", "الكمية", "المتاح"],
        "category": ["category", "type", "cat", "فئة", "الفئة", "تصنيف", "القسم"],
        "status":   ["status", "state", "الحالة"],
    }
    mapping = {}
    for field, words in hints.items():
        mapping[field] = next((c for c, low in lowered.items() if any(w in low for w in words)), None)
    return mapping


def _to_float(value) -> float | None:
    """تحويل آمن إلى رقم — يعيد None عند الفشل أو الفراغ."""
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if s == "" or s.lower() == "nan":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build_catalog(df: pd.DataFrame, mapping: dict, only_active: bool = True) -> list[dict]:
    """
    يحوّل DataFrame + mapping إلى الجدول القياسي (قائمة منتجات فريدة).

    Shopify: نجمّع حسب Handle (منتج واحد بصور متعددة) ونفلتر بحالة الصف الرئيسي.
    غيره:    كل صف = منتج واحد بصورة واحدة (إن وُجدت).
    """
    name_col = mapping.get("name")
    if not name_col or name_col not in df.columns:
        raise ValueError("يجب ربط عمود «اسم الصنف» على الأقل قبل عرض الكتالوج.")

    img_col, price_col = mapping.get("image"), mapping.get("price")
    code_col, stock_col, status_col = mapping.get("code"), mapping.get("stock"), mapping.get("status")
    unit_col, cat_col = mapping.get("unit"), mapping.get("category")

    def cell(row, col):
        if not col or col not in df.columns:
            return ""
        val = row.get(col)
        return "" if val is None or str(val).strip().lower() == "nan" else str(val).strip()

    catalog: list[dict] = []

    if is_shopify(df) and "Handle" in df.columns:
        for _handle, group in df.groupby("Handle", sort=False):
            # الصف الرئيسي = أول صف يحمل اسماً (Title)
            head_rows = group[group[name_col].fillna("").str.strip() != ""]
            if head_rows.empty:
                continue
            head = head_rows.iloc[0]

            # فلترة الحالة من الصف الرئيسي فقط (صفوف الصور حالتها فارغة)
            if only_active and status_col:
                if cell(head, status_col).lower() != "active":
                    continue

            images = [cell(r, img_col) for _, r in group.iterrows() if cell(r, img_col)]
            catalog.append({
                "name":     cell(head, name_col),
                "code":     cell(head, code_col),
                "price":    _to_float(cell(head, price_col)),
                "stock":    _to_float(cell(head, stock_col)),
                "unit":     cell(head, unit_col) or "قطعة",
                "category": cell(head, cat_col) or "أخرى",
                "images":   images,
            })
    else:
        for _, row in df.iterrows():
            name = cell(row, name_col)
            if not name:
                continue
            if only_active and status_col and cell(row, status_col).lower() not in ("active", ""):
                continue
            img = cell(row, img_col)
            catalog.append({
                "name":     name,
                "code":     cell(row, code_col),
                "price":    _to_float(cell(row, price_col)),
                "stock":    _to_float(cell(row, stock_col)),
                "unit":     cell(row, unit_col) or "قطعة",
                "category": cell(row, cat_col) or "أخرى",
                "images":   [img] if img else [],
            })

    return catalog
