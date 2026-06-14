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
              margin-bottom:12px; background:#fff; min-height:120px; }
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


def filtered(catalog):
    q = st.text_input("🔍 بحث عن صنف بالاسم", "").strip().lower()
    items = [(i, p) for i, p in enumerate(catalog) if (not q or q in p["name"].lower())]
    st.caption(f"المعروض: {len(items)} من {len(catalog)} صنف")
    return items


# ----------------------------- وضع العميل -----------------------------
def customer_view(catalog, rep_number):
    st.title(f"🛍️ كتالوج {COMPANY}")
    st.caption("اختر الأصناف والكميات، ثم أرسل طلبك عبر واتساب بضغطة زر.")

    items = filtered(catalog)
    cols_per_row = 4
    for start in range(0, len(items), cols_per_row):
        for col, (idx, prod) in zip(st.columns(cols_per_row), items[start:start + cols_per_row]):
            with col:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                product_image(prod)
                st.markdown(f"**{prod['name']}**")
                if prod["code"]:
                    st.markdown(f'<span class="code">كود: {prod["code"]}</span>', unsafe_allow_html=True)
                st.markdown(
                    f'<span class="price">{msg.fmt_money(prod["price"])}</span> &nbsp; {stock_badge(prod["stock"])}',
                    unsafe_allow_html=True,
                )
                out = prod["stock"] == 0
                qty = st.number_input("الكمية", min_value=0, step=1,
                                      value=int(ss.qty.get(idx, 0)),
                                      key=f"q{idx}", disabled=out)
                if qty > 0 and not out:
                    ss.qty[idx] = qty
                elif idx in ss.qty:
                    del ss.qty[idx]
                st.markdown("</div>", unsafe_allow_html=True)

    _order_sidebar(catalog, rep_number)


def _order_sidebar(catalog, rep_number):
    with st.sidebar:
        st.header("🛒 سلة الطلب")
        selected = [
            {"name": catalog[i]["name"], "code": catalog[i]["code"],
             "price": catalog[i]["price"], "qty": q}
            for i, q in ss.qty.items() if i < len(catalog)
        ]
        if not selected:
            st.info("لم تختر أصنافاً بعد.")
            return

        total = 0.0
        for it in selected:
            lt = (it["price"] or 0) * it["qty"]
            total += lt
            st.write(f"• {it['name']} ×{it['qty']} = {msg.fmt_money(lt)}")
        st.divider()
        st.subheader(f"الإجمالي: {msg.fmt_money(total)}")

        customer = st.text_input("👤 اسمك (اختياري)")
        order = {
            "customer": customer,
            "date": dt.date.today().strftime("%Y-%m-%d"),
            "items": selected,
            "total": total,
        }
        text, used_compact = msg.build_message(order, COMPANY, mode="auto")

        if not msg.clean_number(rep_number):
            st.error("رقم المندوب في الرابط غير صالح.")
            return

        link = msg.whatsapp_link(rep_number, text)
        st.link_button("📲 إرسال الطلب عبر واتساب", link,
                       type="primary", use_container_width=True)
        if used_compact:
            st.caption("ℹ️ الطلب كبير — استُخدمت صيغة مختصرة لتفادي قطع واتساب للرسالة.")
        with st.expander("👁️ معاينة نص الرسالة"):
            st.code(text, language=None)


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
    items = filtered(catalog)
    cols_per_row = 4
    for start in range(0, len(items), cols_per_row):
        for col, (_idx, prod) in zip(st.columns(cols_per_row), items[start:start + cols_per_row]):
            with col:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                product_image(prod)
                st.markdown(f"**{prod['name']}**")
                if prod["code"]:
                    st.markdown(f'<span class="code">كود: {prod["code"]}</span>', unsafe_allow_html=True)
                st.markdown(
                    f'<span class="price">{msg.fmt_money(prod["price"])}</span> &nbsp; {stock_badge(prod["stock"])}',
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)


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
