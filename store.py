"""
store.py — تخزين تعديلات الأدمن بشكل دائم (طبقة فوق الكتالوج الأساسي).

الحفظ في ملف JSON داخل DATA_DIR:
  - على Railway: عيّن متغير البيئة DATA_DIR = مسار Volume دائم (مثل /data).
  - محلياً (تطوير): يستخدم مجلد ./data بجوار الكود.

بنية الملف:
{
  "edits":  { "<id>": {price, name, name_ar, category, stock} },  # تعديلات على أصناف موجودة
  "added":  [ {name, name_ar, code, unit, price, category, stock, images:[...]} ],  # أصناف يدوية
  "hidden": [ "<id>", ... ]   # أصناف مخفية
}
"""
from __future__ import annotations
import json
import os

_BASE = os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    d = os.environ.get("DATA_DIR", os.path.join(_BASE, "data"))
    os.makedirs(d, exist_ok=True)
    return d


def _path() -> str:
    return os.path.join(data_dir(), "overrides.json")


def load_overrides() -> dict:
    try:
        with open(_path(), encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("edits", {})
    data.setdefault("added", [])
    data.setdefault("hidden", [])
    return data


def save_overrides(data: dict) -> None:
    with open(_path(), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def entry_id(prod: dict) -> str:
    """معرّف ثابت للصنف: الكود|الوحدة، أو الاسم لو بلا كود."""
    code = " ".join(str(prod.get("code") or "").strip().upper().split())
    unit = str(prod.get("unit") or "").strip()
    return f"{code}|{unit}" if code else "n:" + str(prod.get("name") or "").strip()


def _to_float(v):
    try:
        s = str(v).strip().replace(",", "")
        return float(s) if s not in ("", "nan", "None") else None
    except (ValueError, TypeError):
        return None


def apply_overrides(catalog: list[dict], ov: dict) -> list[dict]:
    """يطبّق التعديلات/الإخفاء ويضيف الأصناف اليدوية فوق الكتالوج الأساسي."""
    hidden = set(ov.get("hidden", []))
    edits = ov.get("edits", {})
    out: list[dict] = []
    for p in catalog:
        pid = entry_id(p)
        if pid in hidden:
            continue
        if pid in edits:
            p = dict(p)
            for k, v in edits[pid].items():
                if v in (None, ""):
                    continue
                p[k] = _to_float(v) if k in ("price", "stock") else v
        out.append(p)
    for a in ov.get("added", []):
        item = dict(a)
        item.setdefault("images", [])
        item["price"] = _to_float(item.get("price"))
        item["stock"] = _to_float(item.get("stock"))
        item.setdefault("category", "أخرى")
        item.setdefault("name_ar", "")
        item.setdefault("unit", "PC")
        out.append(item)
    return out
