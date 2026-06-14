"""
app.py — كتالوج مبيعات بوضعين (Streamlit، عربي RTL) وإرسال طلبات عبر wa.me.

وضعان عبر query parameters في الرابط — نفس الكود يخدم الاثنين:
  • وضع المندوب  (?mode=rep): يتصفح الكتالوج كاملاً، ويُدخل رقمه ليولّد رابط
    عميل مخصصاً (يحمل ?rep=<رقمه>) لينسخه ويرسله لعملائه.
  • وضع العميل   (?rep=<رقم المندوب>): كتالوج نظيف، السعر ظاهر دائماً،
    يختار الأصناف والكميات، وزر واحد يفتح واتساب على رقم المندوب بالطلب جاهزاً.

البيانات: ملف Shopify المُضمّن يُحمّل تلقائياً (لا يرفع العميل شيئاً).
تشغيل:  streamlit run app.py
"""
from __future__ import annotations
import datetime as dt
import os
import streamlit as st
import streamlit.components.v1 as components

import data_loader as dl
import messaging as msg

# مسار ملف الأصناف المُضمّن — يُحسب نسبةً لمجلد هذا الملف (صامد ضد مجلد التشغيل)
DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "products_export_1 (1).csv")
COMPANY = "متجري"                             # اسم الشركة في الرسالة
PLACEHOLDER = "https://placehold.co/300x300?text=No+Image"  # صورة بديلة عند الفشل

st.set_page_config(page_title="كتالوج المبيعات", page_icon="🛍️", layout="wide")

# ----------------------------- اتجاه RTL -----------------------------
st.markdown(
    """
    <style>
      .stApp, section.main { direction: rtl; }
      html, body, [class*="css"] { font-family: "Segoe UI", Tahoma, sans-serif; }
      h1,h2,h3,h4,p,label,.stMarkdown { text-align: right; }
      .card { border:1px solid #e6e6e6; border-radius:12px; padding:10px;
              margin-bottom:12px; background:#fff; }
      /* توحيد ارتفاع الصور = شبكة أنظف وأسرع بصرياً */
      [data-testid="stImage"] img { height:150px; object-fit:contain; width:100%; }
      .price { color:#0a7d2c; font-weight:700; font-size:1.05rem; }
      .code  { color:#999; font-size:.78rem; }
      .in    { color:#0a7d2c; font-size:.8rem; }
      .out   { color:#c0392b; font-size:.8rem; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state
ss.setdefault("qty", {})            # {index المنتج: الكمية}
ss.setdefault("custom_catalog", None)  # كتالوج بديل رفعه المندوب (جلسة فقط)
ss.setdefault("page", 1)           # رقم صفحة الكتالوج الحالية

PAGE_SIZE = 24                     # عدد الأصناف في الصفحة الواحدة (للسرعة)
COLS = 2                           # عمودان — أنسب للموبايل


# ----------------------------- تحميل الكتالوج -----------------------------
@st.cache_data(show_spinner="جارٍ تحميل الكتالوج...")
def load_default_catalog() -> list[dict]:
    """يحمّل ويبني الكتالوج من الملف المُضمّن (active فقط). مُخزّن مؤقتاً."""
    df = dl.read_path(DEFAULT_FILE)
    mapping = dl.auto_mapping(df)
    return dl.build_catalog(df, mapping, only_active=True)


def get_catalog() -> list[dict]:
    """كتالوج الجلسة (ملف المندوب البديل إن وُجد) وإلا المُضمّن."""
    if ss.custom_catalog is not None:
        return ss.custom_catalog
    try:
        return load_default_catalog()
    except Exception as e:  # noqa: BLE001
        st.error(f"تعذّر تحميل ملف الكتالوج «{DEFAULT_FILE}»: {e}")
        return []


# ----------------------------- عناصر مشتركة -----------------------------
def stock_badge(stock):
    if stock is None:
        return ""
    return '<span class="out">نافد</span>' if stock == 0 else '<span class="in">متوفر</span>'


def product_image(prod):
    src = prod["images"][0] if prod["images"] and dl.is_url(prod["images"][0]) else PLACEHOLDER
    try:
        st.image(src, use_container_width=True)
    except Exception:  # noqa: BLE001
        st.image(PLACEHOLDER, use_container_width=True)


def _set_qty(idx):
    """تُستدعى فور تغيير الكمية (on_change) فتحدّث السلة قبل إعادة رسم الصفحة."""
    v = int(st.session_state.get(f"q{idx}", 0))
    if v > 0:
        ss.qty[idx] = v
    else:
        ss.qty.pop(idx, None)


def _render_cards(page_items, selectable):
    """يرسم كروت صفحة واحدة (عمودان). selectable=True يضيف عدّاد الكمية."""
    for s in range(0, len(page_items), COLS):
        for col, (idx, prod) in zip(st.columns(COLS), page_items[s:s + COLS]):
            with col:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                product_image(prod)
                st.markdown(f"**{prod['name']}**")
                meta = []
                if prod["code"]:
                    meta.append(f'كود: {prod["code"]}')
                meta.append(f'الوحدة: {prod["unit"]}')
                st.markdown(f'<span class="code">{" · ".join(meta)}</span>', unsafe_allow_html=True)
                st.markdown(
                    f'<span class="price">{msg.fmt_money(prod["price"])}</span> &nbsp; {stock_badge(prod["stock"])}',
                    unsafe_allow_html=True,
                )
                if selectable:
                    out = prod["stock"] == 0
                    key = f"q{idx}"
                    # نزرع القيمة من السلة (تبقى محفوظة عبر الصفحات)
                    if key not in st.session_state:
                        st.session_state[key] = int(ss.qty.get(idx, 0))
                    st.number_input(f"الكمية ({prod['unit']})", min_value=0, step=1,
                                    key=key, on_change=_set_qty, args=(idx,), disabled=out)
                st.markdown("</div>", unsafe_allow_html=True)


def browse(catalog, selectable):
    """فلترة بالفئة + بحث + تقسيم لصفحات + شبكة الكروت."""
    cats = sorted({p.get("category") or "أخرى" for p in catalog})
    f1, f2 = st.columns(2)
    sel_cat = f1.selectbox("📂 الفئة", ["كل الفئات"] + cats, key="flt_cat")
    q = f2.text_input("🔍 بحث بالاسم", key="flt_q").strip().lower()

    items = [
        (i, p) for i, p in enumerate(catalog)
        if (sel_cat == "كل الفئات" or (p.get("category") or "أخرى") == sel_cat)
        and (not q or q in p["name"].lower())
    ]

    # إعادة الصفحة للأولى عند تغيّر الفلتر/البحث
    sig = (sel_cat, q)
    if ss.get("_flt_sig") != sig:
        ss._flt_sig = sig
        ss.page = 1

    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, ss.get("page", 1)), total_pages)
    ss.page = page
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]

    st.caption(f"عرض {len(page_items)} من {len(items)} صنف — صفحة {page}/{total_pages}")
    _render_cards(page_items, selectable)

    if total_pages > 1:
        prev, info, nxt = st.columns(3)
        if prev.button("⬅️ السابق", disabled=page <= 1, use_container_width=True, key="pg_prev"):
            ss.page = page - 1
            st.rerun()
        info.markdown(f"<div style='text-align:center;padding-top:8px'>صفحة {page} / {total_pages}</div>",
                      unsafe_allow_html=True)
        if nxt.button("التالي ➡️", disabled=page >= total_pages, use_container_width=True, key="pg_next"):
            ss.page = page + 1
            st.rerun()


# ----------------------------- وضع العميل -----------------------------
def customer_view(catalog, rep_number):
    st.title(f"🛍️ كتالوج {COMPANY}")
    cart_panel(catalog, rep_number)   # السلة ظاهرة دائماً في الأعلى
    st.divider()
    browse(catalog, selectable=True)


def cart_panel(catalog, rep_number):
    """سلة الطلب ظاهرة أعلى الصفحة: العدد + الإجمالي + زر واتساب."""
    selected = [
        {"name": catalog[i]["name"], "code": catalog[i]["code"], "price": catalog[i]["price"],
         "unit": catalog[i]["unit"], "qty": q}
        for i, q in ss.qty.items() if i < len(catalog)
    ]
    with st.container(border=True):
        if not selected:
            st.markdown("### 🛒 سلتك فارغة")
            st.caption("اختر أصنافاً وكمياتها من الكتالوج بالأسفل.")
            return

        total = sum((it["price"] or 0) * it["qty"] for it in selected)
        st.markdown(f"### 🛒 سلتك: {len(selected)} صنف &nbsp;—&nbsp; الإجمالي: "
                    f"<span style='color:#0a7d2c'>{msg.fmt_money(total)}</span>",
                    unsafe_allow_html=True)

        st.text_input("👤 اسمك (اختياري)", key="cust_name")
        order = {
            "customer": st.session_state.get("cust_name", ""),
            "date": dt.date.today().strftime("%Y-%m-%d"),
            "items": selected,
            "total": total,
        }
        text, used_compact = msg.build_message(order, COMPANY, mode="auto")

        if msg.clean_number(rep_number):
            link = msg.whatsapp_link(rep_number, text)
            st.link_button("📲 إرسال الطلب عبر واتساب", link,
                           type="primary", use_container_width=True)
        else:
            st.error("رقم المندوب في الرابط غير صالح — اطلب من المندوب رابطاً صحيحاً.")
        if used_compact:
            st.caption("ℹ️ الطلب كبير — استُخدمت صيغة مختصرة لتفادي قطع واتساب للرسالة.")

        with st.expander("👁️ تفاصيل الطلب"):
            for it in selected:
                lt = (it["price"] or 0) * it["qty"]
                st.write(f"• {it['name']} — {it['qty']} {it['unit']} = {msg.fmt_money(lt)}")


# ----------------------------- وضع المندوب -----------------------------
def rep_view(catalog):
    st.title("🧑‍💼 وضع المندوب")
    st.caption("تصفّح الكتالوج، وولّد رابطاً مخصصاً لعملائك يحمل رقمك.")

    with st.expander("🔗 توليد رابط العميل", expanded=True):
        rep_number = st.text_input(
            "📱 رقمك على واتساب (صيغة دولية بدون + أو أصفار، مثال: 9659xxxxxxx)")
        clean = msg.clean_number(rep_number)
        if clean:
            # نولّد الرابط الكامل تلقائياً من عنوان التطبيق الحالي (JS داخل المتصفح)،
            # فلا يحتاج المندوب لصق أي رابط يدوياً. المكوّن يعمل داخل iframe لذا
            # نقرأ عنوان الصفحة الأم عبر window.parent.location.
            components.html(
                f"""
                <div dir="rtl" style="font-family:'Segoe UI',Tahoma,sans-serif;">
                  <div style="background:#0a7d2c;color:#fff;padding:10px 12px;border-radius:8px;
                              margin-bottom:8px;font-weight:700;">
                    ✅ رابط عميلك جاهز — انسخه وأرسله على واتساب:
                  </div>
                  <input id="repLink" readonly
                         style="width:100%;box-sizing:border-box;padding:12px;font-size:14px;
                                border:1px solid #ccc;border-radius:8px;direction:ltr;text-align:left;"/>
                  <button id="cpy"
                     onclick="navigator.clipboard.writeText(document.getElementById('repLink').value);
                              this.innerText='✅ تم النسخ';setTimeout(()=>this.innerText='📋 نسخ الرابط',1500);"
                     style="margin-top:8px;width:100%;padding:12px;background:#25D366;color:#fff;
                            border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;">
                    📋 نسخ الرابط
                  </button>
                  <script>
                    (function(){{
                      var loc = window.parent.location;
                      var base = (loc.origin + loc.pathname).replace(/\\/+$/,'');
                      document.getElementById('repLink').value = base + '/?rep={clean}';
                    }})();
                  </script>
                </div>
                """,
                height=170,
            )
        else:
            st.info("أدخل رقمك لتوليد الرابط.")

    with st.expander("📂 استبدال ملف الكتالوج (اختياري — لجلستك فقط)"):
        st.caption("لتجربة ملف بترويسة مختلفة وضبط ربط الأعمدة يدوياً. "
                   "العملاء يرون دائماً الملف المُضمّن مع التطبيق.")
        _rep_upload()

    st.divider()
    st.subheader("📖 تصفّح الكتالوج")
    browse(catalog, selectable=False)


def _rep_upload():
    up = st.file_uploader("ارفع CSV/Excel", type=["csv", "xlsx", "xls"], key="rep_up")
    if up is None:
        if st.button("↩️ العودة للملف المُضمّن"):
            ss.custom_catalog = None
            st.rerun()
        return
    try:
        df = dl.read_file(up)
    except ValueError as e:
        st.error(str(e))
        return
    mapping = dl.auto_mapping(df)
    cols = ["—"] + list(df.columns)
    new_map = {}
    c1, c2, c3 = st.columns(3)
    for i, (field, label) in enumerate(dl.STANDARD_FIELDS.items()):
        cur = mapping.get(field)
        sel = (c1, c2, c3)[i % 3].selectbox(
            label, cols, index=cols.index(cur) if cur in cols else 0, key=f"m_{field}")
        new_map[field] = None if sel == "—" else sel
    try:
        ss.custom_catalog = dl.build_catalog(df, new_map, only_active=True)
        st.success(f"تم تحميل {len(ss.custom_catalog)} صنفاً من ملفك (جلستك فقط).")
    except ValueError as e:
        st.warning(str(e))


# ----------------------------- التوجيه حسب الرابط -----------------------------
params = st.query_params
rep_param = params.get("rep")
mode_param = params.get("mode")

catalog = get_catalog()

if rep_param:                       # وجود ?rep=<رقم> ⇒ وضع العميل
    customer_view(catalog, rep_param)
else:                               # ?mode=rep أو الافتراضي ⇒ وضع المندوب
    if mode_param != "rep":
        st.info("👋 أنت في وضع المندوب. للوصول كعميل استخدم رابطاً يحوي `?rep=<رقمك>`.")
    rep_view(catalog)
