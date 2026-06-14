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
from i18n import t, LANGS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(BASE_DIR, "products_export_1 (1).csv")
PRICE_GLOB = os.path.join(BASE_DIR, "SalesPriceList-*.xlsx")
COMPANY = "متجري"
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


# ----------------------------- تحميل الكتالوج + دمج الأسعار -----------------------------
@st.cache_data(show_spinner=True)
def load_default_catalog() -> list[dict]:
    """يبني الكتالوج من ملف Shopify ثم يدمج أقل سعر من قوائم الأسعار الـ3."""
    df = dl.read_path(DEFAULT_FILE)
    mapping = dl.auto_mapping(df)
    catalog = dl.build_catalog(df, mapping, only_active=True)

    price_map = dl.build_price_map(sorted(glob.glob(PRICE_GLOB)))
    matched = 0
    for p in catalog:
        code = dl.normalize_code(p.get("code"))
        if code and code in price_map:
            p["price"] = price_map[code]   # أقل سعر من القوائم
            matched += 1
        # غير الموجود: يبقى بسعر Shopify كما هو (لا تغيير)
    return catalog


def get_catalog() -> list[dict]:
    if ss.custom_catalog is not None:
        return ss.custom_catalog
    try:
        return load_default_catalog()
    except Exception as e:  # noqa: BLE001
        st.error(t("load_error", LANG, f=os.path.basename(DEFAULT_FILE), e=e))
        return []


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


def _set_qty(idx):
    """on_change: يحدّث السلة فور تغيير الكمية (قبل إعادة الرسم)."""
    v = int(st.session_state.get(f"q{idx}", 0))
    if v > 0:
        ss.qty[idx] = v
    else:
        ss.qty.pop(idx, None)


def _render_cards(page_items, selectable):
    for s in range(0, len(page_items), COLS):
        for col, (idx, prod) in zip(st.columns(COLS), page_items[s:s + COLS]):
            with col:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                product_image(prod)
                st.markdown(f"**{prod['name']}**")
                meta = []
                if prod["code"]:
                    meta.append(t("code_label", LANG, c=prod["code"]))
                meta.append(t("unit_label", LANG, u=prod["unit"]))
                st.markdown(f'<span class="code">{" · ".join(meta)}</span>', unsafe_allow_html=True)
                st.markdown(f'{price_html(prod)} &nbsp; {stock_badge(prod["stock"])}',
                            unsafe_allow_html=True)
                if selectable:
                    out = prod["stock"] == 0
                    key = f"q{idx}"
                    if key not in st.session_state:
                        st.session_state[key] = int(ss.qty.get(idx, 0))
                    st.number_input(t("qty_label", LANG, u=prod["unit"]), min_value=0, step=1,
                                    key=key, on_change=_set_qty, args=(idx,), disabled=out)
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
        name = p["name"].lower()
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
    st.title(t("catalog_title", LANG, company=COMPANY))
    cart_panel(catalog, rep_number)
    st.divider()
    browse(catalog, selectable=True)


def cart_panel(catalog, rep_number):
    selected = [
        {"name": catalog[i]["name"], "code": catalog[i]["code"], "price": catalog[i]["price"],
         "unit": catalog[i]["unit"], "qty": q}
        for i, q in ss.qty.items() if i < len(catalog)
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
    st.title(t("rep_title", LANG))
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


# ----------------------------- شريط اللغة + التوجيه -----------------------------
top_l, top_r = st.columns([4, 1])
with top_r:
    st.radio(t("lang_label", LANG), list(LANGS.keys()),
             format_func=lambda c: LANGS[c], horizontal=True, key="lang")

params = st.query_params
rep_param = params.get("rep")
mode_param = params.get("mode")

catalog = get_catalog()

if rep_param:                       # ?rep=<رقم> ⇒ وضع العميل
    customer_view(catalog, rep_param)
else:                               # ?mode=rep أو الافتراضي ⇒ وضع المندوب
    if mode_param != "rep":
        st.info(t("rep_banner", LANG))
    rep_view(catalog)
