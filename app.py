"""
app.py — كتالوج مبيعات بوضعين (Streamlit، عربي/إنجليزي) وإرسال طلبات عبر wa.me.

وضعان عبر query parameters:
  • وضع المندوب (?mode=rep): يتصفح الكتالوج ويولّد رابط عميل يحمل رقمه.
  • وضع العميل  (?rep=<رقم>): كتالوج نظيف، سعر ظاهر، اختيار وكميات، زر واتساب.

الأسعار: تُدمج من 3 قوائم أسعار (SalesPriceList-*.xlsx) — أقل سعر لكل كود؛
وغير الموجود في القوائم يبقى بسعر Shopify. اللغة قابلة للتبديل (عربي/إنجليزي).
"""
from __future__ import annotations
import datetime as dt
import glob
import os
from collections import Counter
import streamlit as st
import streamlit.components.v1 as components

import data_loader as dl
import messaging as msg
import store
from i18n import t, LANGS, unit_name

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(BASE_DIR, "products_export_1 (1).csv")
PRICE_GLOB = os.path.join(BASE_DIR, "SalesPriceList-*.xlsx")
LOGO = os.path.join(BASE_DIR, "logo.png")
COMPANY = "Asaad Alabdulkarim & Partner Co."
PLACEHOLDER = "https://placehold.co/300x300?text=No+Image"
ALL_CAT = "__ALL__"   # قيمة ثابتة لخيار «كل الفئات» (مستقرة عبر اللغات)

# ----------------------------- اللغة والاتجاه -----------------------------
ss = st.session_state
ss.setdefault("lang", "ar")
ss.setdefault("qty", {})
ss.setdefault("custom_catalog", None)
ss.setdefault("page", 1)

LANG = ss["lang"]
RTL = LANG == "ar"
DIRECTION = "rtl" if RTL else "ltr"
ALIGN = "right" if RTL else "left"

PAGE_SIZE = 24
COLS = 2

st.set_page_config(page_title=t("page_title", LANG), page_icon="🛍️", layout="wide")

st.markdown(
    f"""
    <style>
      .stApp, section.main {{ direction: {DIRECTION}; }}
      html, body, [class*="css"] {{ font-family: "Segoe UI", Tahoma, sans-serif; }}
      h1,h2,h3,h4,p,label,.stMarkdown {{ text-align: {ALIGN}; }}
      .card {{ border:1px solid #e6e6e6; border-radius:12px; padding:10px;
              margin-bottom:12px; background:#fff; }}
      [data-testid="stImage"] img {{ height:150px; object-fit:contain; width:100%; }}
      .price {{ color:#0a7d2c; font-weight:700; font-size:1.05rem; }}
      .code  {{ color:#999; font-size:.78rem; }}
      .in    {{ color:#0a7d2c; font-size:.8rem; }}
      .out   {{ color:#c0392b; font-size:.8rem; font-weight:700; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def money(v):
    """تنسيق سعر باللغة الحالية."""
    return msg.fmt_money(v, LANG)


def disp(prod):
    """اسم العرض: عربي من قوائم الأسعار إن وُجد ولغة الواجهة عربية، وإلا الإنجليزي."""
    if LANG == "ar" and prod.get("name_ar"):
        return prod["name_ar"]
    return prod["name"]


def show_header():
    """شعار الشركة أعلى الصفحة (في الوضعين)."""
    if os.path.exists(LOGO):
        st.image(LOGO, use_container_width=True)


# ----------------------------- تحميل الكتالوج + دمج الأسعار -----------------------------
@st.cache_data(show_spinner=True)
def build_base_catalog() -> list[dict]:
    """
    يبني الكتالوج من ملف Shopify، ثم لكل منتج يولّد صنفاً منفصلاً لكل وحدة بيع
    (قطعة/كرتون/ريم...) بأقل سعر لها من قوائم الأسعار — بنفس الصورة.
    المنتجات غير الموجودة في القوائم تبقى صنفاً واحداً بسعر Shopify.
    """
    df = dl.read_path(DEFAULT_FILE)
    mapping = dl.auto_mapping(df)
    base = dl.build_catalog(df, mapping, only_active=True)

    units = dl.build_price_units(sorted(glob.glob(PRICE_GLOB)))
    catalog: list[dict] = []
    for p in base:
        code = dl.normalize_code(p.get("code"))
        variants = units.get(code) if code else None
        if variants:
            for v in variants:                 # صنف منفصل لكل وحدة
                q = dict(p)
                q["price"] = v["price"]         # أقل سعر لهذه الوحدة
                q["unit"] = v["unit"]           # كود الوحدة (PC/Carton/...)
                q["name_ar"] = v["name_ar"] or ""
                catalog.append(q)
        else:
            p["unit"] = "PC"                    # غير موجود بالقوائم: قطعة بسعر Shopify
            p["name_ar"] = ""
            catalog.append(p)
    return catalog


def get_catalog() -> list[dict]:
    if ss.custom_catalog is not None:
        return ss.custom_catalog
    try:
        base = build_base_catalog()
    except Exception as e:  # noqa: BLE001
        st.error(t("load_error", LANG, f=os.path.basename(DEFAULT_FILE), e=e))
        return []
    # تعديلات الأدمن تُطبّق طازجة كل مرة (لا تحتاج مسح الكاش)
    return store.apply_overrides(base, store.load_overrides())


# ----------------------------- عناصر مشتركة -----------------------------
def stock_badge(stock):
    if stock is None:
        return ""
    if stock == 0:
        return f'<span class="out">{t("out_stock", LANG)}</span>'
    return f'<span class="in">{t("in_stock", LANG)}</span>'


def product_image(prod):
    src = prod["images"][0] if prod["images"] and dl.is_url(prod["images"][0]) else PLACEHOLDER
    try:
        st.image(src, use_container_width=True)
    except Exception:  # noqa: BLE001
        st.image(PLACEHOLDER, use_container_width=True)


def price_html(prod):
    if prod["price"] is None:
        return f'<span class="price">{t("price_on_request", LANG)}</span>'
    return f'<span class="price">{money(prod["price"])}</span>'


def _set_qty(wkey, pid):
    """on_change: يحدّث السلة بمعرّف الصنف الثابت (لا بالموقع) — آمن ضد تغيّر الترتيب."""
    v = int(st.session_state.get(wkey, 0))
    if v > 0:
        ss.qty[pid] = v
    else:
        ss.qty.pop(pid, None)


def _render_cards(page_items, selectable):
    for s in range(0, len(page_items), COLS):
        for col, (idx, prod) in zip(st.columns(COLS), page_items[s:s + COLS]):
            with col:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                product_image(prod)
                st.markdown(f"**{disp(prod)}**")
                meta = []
                if prod["code"]:
                    meta.append(t("code_label", LANG, c=prod["code"]))
                meta.append(t("unit_label", LANG, u=unit_name(prod["unit"], LANG)))
                st.markdown(f'<span class="code">{" · ".join(meta)}</span>', unsafe_allow_html=True)
                st.markdown(f'{price_html(prod)} &nbsp; {stock_badge(prod["stock"])}',
                            unsafe_allow_html=True)
                if selectable:
                    # النافد يظل قابلاً للطلب (طلب مسبق) مع بقاء شارة «نافد» كتنبيه
                    pid = store.entry_id(prod)
                    wkey = f"q{idx}"
                    # نزرع القيمة كل مرة من مصدر الحقيقة (السلة بالمعرّف الثابت)
                    st.session_state[wkey] = int(ss.qty.get(pid, 0))
                    st.number_input(t("qty_label", LANG, u=unit_name(prod["unit"], LANG)), min_value=0, step=1,
                                    key=wkey, on_change=_set_qty, args=(wkey, pid))
                st.markdown("</div>", unsafe_allow_html=True)


def browse(catalog, selectable):
    """فلترة بالفئة + بحث بنطاق + تقسيم لصفحات + شبكة الكروت."""
    counts = Counter((p.get("category") or "أخرى") for p in catalog)
    cats = sorted(counts)
    cat_options = [ALL_CAT] + cats

    f1, f2 = st.columns(2)
    sel_cat = f1.selectbox(
        t("category", LANG), cat_options, key="flt_cat",
        format_func=lambda c: (t("all_categories", LANG, n=len(catalog)) if c == ALL_CAT
                               else t("cat_with_count", LANG, c=c, n=counts[c])),
    )
    q = f2.text_input(t("search", LANG), key="flt_q").strip().lower()
    # نطاق البحث كفهرس ثابت (0=الكل 1=الاسم 2=الكود 3=الفئة) لاستقراره عبر اللغات
    scope_labels = [t("scope_all", LANG), t("scope_name", LANG),
                    t("scope_code", LANG), t("scope_category", LANG)]
    scope = st.radio(t("search_scope", LANG), [0, 1, 2, 3], horizontal=True,
                     format_func=lambda i: scope_labels[i], key="flt_scope")

    def _match(p):
        if sel_cat != ALL_CAT and (p.get("category") or "أخرى") != sel_cat:
            return False
        if not q:
            return True
        name = (p["name"] + " " + (p.get("name_ar") or "")).lower()  # بحث بالاسمين
        code = (p.get("code") or "").lower()
        cat = (p.get("category") or "").lower()
        if scope == 1:
            return q in name
        if scope == 2:
            return q in code
        if scope == 3:
            return q in cat
        return q in name or q in code or q in cat

    items = [(i, p) for i, p in enumerate(catalog) if _match(p)]

    sig = (sel_cat, q, scope)
    if ss.get("_flt_sig") != sig:
        ss._flt_sig = sig
        ss.page = 1

    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(max(1, ss.get("page", 1)), total_pages)
    ss.page = page
    start = (page - 1) * PAGE_SIZE
    page_items = items[start:start + PAGE_SIZE]

    st.caption(t("showing", LANG, a=len(page_items), b=len(items), p=page, tp=total_pages))
    _render_cards(page_items, selectable)

    if total_pages > 1:
        prev, info, nxt = st.columns(3)
        if prev.button(t("prev", LANG), disabled=page <= 1, use_container_width=True, key="pg_prev"):
            ss.page = page - 1
            st.rerun()
        info.markdown(f"<div style='text-align:center;padding-top:8px'>{t('page_x', LANG, p=page, tp=total_pages)}</div>",
                      unsafe_allow_html=True)
        if nxt.button(t("next", LANG), disabled=page >= total_pages, use_container_width=True, key="pg_next"):
            ss.page = page + 1
            st.rerun()


# ----------------------------- وضع العميل -----------------------------
def customer_view(catalog, rep_number):
    show_header()
    cart_panel(catalog, rep_number)
    st.divider()
    browse(catalog, selectable=True)


def cart_panel(catalog, rep_number):
    by_id = {store.entry_id(p): p for p in catalog}
    selected = [
        {"name": disp(by_id[pid]), "code": by_id[pid].get("code", ""),
         "price": by_id[pid].get("price"), "unit": unit_name(by_id[pid].get("unit"), LANG), "qty": q}
        for pid, q in ss.qty.items() if pid in by_id
    ]
    with st.container(border=True):
        if not selected:
            st.markdown(f"### {t('cart_empty_title', LANG)}")
            st.caption(t("cart_empty_hint", LANG))
            return

        total = sum((it["price"] or 0) * it["qty"] for it in selected)
        st.markdown(f"### {t('cart_summary', LANG, n=len(selected), total=money(total))}",
                    unsafe_allow_html=True)

        st.text_input(t("your_name", LANG), key="cust_name")
        order = {
            "customer": st.session_state.get("cust_name", ""),
            "date": dt.date.today().strftime("%Y-%m-%d"),
            "items": selected,
            "total": total,
        }
        text, used_compact = msg.build_message(order, COMPANY, LANG, mode="auto")

        if msg.clean_number(rep_number):
            link = msg.whatsapp_link(rep_number, text)
            st.link_button(t("send_whatsapp", LANG), link, type="primary", use_container_width=True)
        else:
            st.error(t("bad_rep", LANG))
        if used_compact:
            st.caption(t("compact_note", LANG))

        with st.expander(t("order_details", LANG)):
            for it in selected:
                lt = (it["price"] or 0) * it["qty"]
                st.write(f"• {it['name']} — {it['qty']} {it['unit']} = {money(lt)}")


# ----------------------------- وضع المندوب -----------------------------
def rep_view(catalog):
    show_header()
    st.subheader(t("rep_title", LANG))
    st.caption(t("rep_caption", LANG))

    with st.expander(t("gen_link", LANG), expanded=True):
        rep_number = st.text_input(t("rep_number", LANG))
        clean = msg.clean_number(rep_number)
        if clean:
            components.html(
                f"""
                <div dir="{DIRECTION}" style="font-family:'Segoe UI',Tahoma,sans-serif;">
                  <div style="background:#0a7d2c;color:#fff;padding:10px 12px;border-radius:8px;
                              margin-bottom:8px;font-weight:700;">{t('link_ready', LANG)}</div>
                  <input id="repLink" readonly
                         style="width:100%;box-sizing:border-box;padding:12px;font-size:14px;
                                border:1px solid #ccc;border-radius:8px;direction:ltr;text-align:left;"/>
                  <button id="cpy"
                     onclick="navigator.clipboard.writeText(document.getElementById('repLink').value);
                              this.innerText='{t('copied', LANG)}';
                              setTimeout(()=>this.innerText='{t('copy_link', LANG)}',1500);"
                     style="margin-top:8px;width:100%;padding:12px;background:#25D366;color:#fff;
                            border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;">
                    {t('copy_link', LANG)}
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
            st.info(t("enter_number", LANG))

    with st.expander(t("replace_file", LANG)):
        st.caption(t("replace_hint", LANG))
        _rep_upload()

    st.divider()
    st.subheader(t("browse_catalog", LANG))
    browse(catalog, selectable=False)


def _rep_upload():
    up = st.file_uploader(t("upload", LANG), type=["csv", "xlsx", "xls"], key="rep_up")
    if up is None:
        if st.button(t("back_bundled", LANG)):
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
        st.success(t("loaded_n", LANG, n=len(ss.custom_catalog)))
    except ValueError as e:
        st.warning(str(e))


# ----------------------------- وضع الأدمن -----------------------------
def admin_view():
    show_header()
    st.subheader("🔐 لوحة تحكم الأدمن")

    pw_env = os.environ.get("ADMIN_PASSWORD", "")
    if not ss.get("admin_ok"):
        pw = st.text_input("كلمة مرور الأدمن", type="password")
        if st.button("دخول"):
            ok = (pw == pw_env) if pw_env else (pw == "admin")
            if ok:
                ss.admin_ok = True
                st.rerun()
            else:
                st.error("كلمة مرور خاطئة.")
        if not pw_env:
            st.warning("⚠️ لم تُضبط ADMIN_PASSWORD بعد — كلمة المرور المؤقتة: «admin». "
                       "عيّنها في Railway → Variables ثم أعد المحاولة.")
        return

    tab_add, tab_edit = st.tabs(["➕ إضافة صنف يدوي", "✏️ تعديل / إخفاء صنف"])

    # ---- إضافة صنف ----
    with tab_add:
        with st.form("admin_add", clear_on_submit=True):
            name = st.text_input("الاسم (إنجليزي) *")
            name_ar = st.text_input("الاسم بالعربي")
            c1, c2 = st.columns(2)
            code = c1.text_input("الكود")
            unit = c2.text_input("الوحدة (PC/Carton/REAM...)", value="PC")
            c3, c4 = st.columns(2)
            price = c3.number_input("السعر (د.ك)", min_value=0.0, step=0.1, format="%.3f")
            stock = c4.number_input("المخزون", min_value=0, step=1, value=0)
            category = st.text_input("الفئة", value="أخرى")
            img = st.text_input("رابط الصورة (URL)")
            if st.form_submit_button("➕ إضافة الصنف", type="primary") and name.strip():
                ov = store.load_overrides()
                ov["added"].append({
                    "name": name.strip(), "name_ar": name_ar.strip(), "code": code.strip(),
                    "unit": unit.strip() or "PC", "price": price, "stock": stock,
                    "category": category.strip() or "أخرى",
                    "images": [img.strip()] if img.strip() else [],
                })
                store.save_overrides(ov)
                st.success(f"تمت إضافة «{name}» ✅")

    # ---- تعديل / إخفاء ----
    with tab_edit:
        cat = get_catalog()
        if not cat:
            st.info("لا توجد أصناف.")
            return
        labels = [
            f"{p['name']} — {unit_name(p.get('unit'), 'ar')} — {msg.fmt_money(p.get('price'))}"
            f"{(' — ' + p['code']) if p.get('code') else ''}"
            for p in cat
        ]
        idx = st.selectbox("اختر الصنف", range(len(cat)),
                           format_func=lambda i: labels[i], key="adm_pick")
        prod = cat[idx]
        pid = store.entry_id(prod)

        with st.form("admin_edit"):
            new_price = st.number_input("السعر (د.ك)", min_value=0.0, step=0.1, format="%.3f",
                                        value=float(prod.get("price") or 0))
            new_name = st.text_input("الاسم (إنجليزي)", value=prod.get("name", ""))
            new_name_ar = st.text_input("الاسم بالعربي (الوصف)", value=prod.get("name_ar", ""))
            cc1, cc2 = st.columns(2)
            new_cat = cc1.text_input("الفئة", value=prod.get("category", ""))
            new_stock = cc2.number_input("المخزون", min_value=0, step=1,
                                         value=int(prod.get("stock") or 0))
            col_s, col_h = st.columns(2)
            save = col_s.form_submit_button("💾 حفظ التعديل", type="primary")
            hide = col_h.form_submit_button("🙈 إخفاء الصنف")
        if save:
            ov = store.load_overrides()
            ov["edits"][pid] = {"price": new_price, "name": new_name, "name_ar": new_name_ar,
                                "category": new_cat, "stock": new_stock}
            store.save_overrides(ov)
            st.success("تم حفظ التعديل ✅")
            st.rerun()
        if hide:
            ov = store.load_overrides()
            if pid not in ov["hidden"]:
                ov["hidden"].append(pid)
            store.save_overrides(ov)
            st.success("تم إخفاء الصنف ✅")
            st.rerun()

        # استعادة المخفيّات
        ov = store.load_overrides()
        if ov.get("hidden"):
            with st.expander(f"🗂️ المخفيّات ({len(ov['hidden'])})"):
                for h in list(ov["hidden"]):
                    cols = st.columns([4, 1])
                    cols[0].write(h)
                    if cols[1].button("استعادة", key=f"unhide_{h}"):
                        ov["hidden"].remove(h)
                        store.save_overrides(ov)
                        st.rerun()


# ----------------------------- شريط اللغة + التوجيه -----------------------------
top_l, top_r = st.columns([4, 1])
with top_r:
    st.radio(t("lang_label", LANG), list(LANGS.keys()),
             format_func=lambda c: LANGS[c], horizontal=True, key="lang")

params = st.query_params
rep_param = params.get("rep")
mode_param = params.get("mode")
admin_param = params.get("admin")

if admin_param:                     # ?admin=1 ⇒ لوحة الأدمن
    admin_view()
elif rep_param:                     # ?rep=<رقم> ⇒ وضع العميل
    customer_view(get_catalog(), rep_param)
else:                               # ?mode=rep أو الافتراضي ⇒ وضع المندوب
    if mode_param != "rep":
        st.info(t("rep_banner", LANG))
    rep_view(get_catalog())
