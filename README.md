# 🧾 تطبيق مندوب المبيعات

تطبيق Streamlit عربي (RTL) لعرض كتالوج الأصناف، توليد أمر بيع، وإرساله عبر تليجرام أو واتساب.

## التشغيل

```bash
pip install -r requirements.txt
copy .env.example .env      # ثم املأ القيم
streamlit run app.py
```

## إعداد المفاتيح (`.env`)

| المفتاح | من أين تحصل عليه |
|---|---|
| `TELEGRAM_BOT_TOKEN` | أنشئ بوتاً عبر [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | أرسل رسالة للبوت ثم افتح `https://api.telegram.org/bot<TOKEN>/getUpdates` وخذ `chat.id` |
| `WHATSAPP_DEFAULT_NUMBER` | رقم اختياري بصيغة دولية بدون `+` |
| `COMPANY_NAME` / `CURRENCY` | اسم الشركة ورمز العملة في الرسالة |

## ملاحظات

- **الصور:** يدعم روابط أونلاين ومسارات محلية معاً.
- **مفتاح السعر:** عند إخفائه يختفي السعر من العرض **ومن الرسالة المُرسَلة**.
- **Shopify:** يُكتشف تلقائياً ويُجمّع الصفوف حسب `Handle` (منتج واحد بصور متعددة).
- **واتساب:** رابط `wa.me` فقط (الإرسال يدوي). الإرسال التلقائي الكامل يتطلب
  **WhatsApp Cloud API المدفوع** — غير مشمول.
```
```
