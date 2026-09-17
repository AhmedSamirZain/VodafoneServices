# -*- coding: utf-8 -*-
"""
config.py — الإعدادات المركزية للبوت
=================================================
الغرض: سحب كل الأسرار والإعدادات من الكود وتحميلها من متغيرات البيئة
(ملف .env) حتى لا يتسرب أي توكن أو رقم دفع مع الكود.

طريقة الاستخدام:
    1) انسخ .env.example إلى .env
    2) ضع القيم الحقيقية في .env
    3) لا ترفع ملف .env أبداً إلى Git أو أرسله لأي شخص

تنبيه أمني مهم:
    توكنات البوتين القديمة كانت مكتوبة في الكود ومكشوفة →
    اعتبرهما مسربتين ويجب إعادة توليدهما من @BotFather قبل التشغيل.
"""

import os


def _load_dotenv(path: str = ".env") -> None:
    """قارئ .env بسيط بدون اعتماديات خارجية (لا يعيد القيم الموجودة مسبقاً في البيئة)"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _st_secret(name: str) -> str:
    """
    لو شغالين جوا ستريمليت (زي Streamlit Cloud)، اقرأ القيمة من st.secrets
    كمان — احتياطياً لو الـ Secrets مش ظاهرة كمتغيرات بيئة.
    """
    try:
        import streamlit as st  # noqa: F401
        val = st.secrets.get(name)
        if val is not None:
            return str(val)
    except Exception:
        pass
    return ""


def _get(name: str, default: str = "") -> str:
    """متغير بيئة أولاً، ثم Secrets ستريمليت، ثم القيمة الافتراضية"""
    val = os.getenv(name)
    if val is not None and val != "":
        return val
    val = _st_secret(name)
    return val if val else default


# ==================== توكنات البوت (سرية - من .env / Secrets) ====================
USER_BOT_TOKEN = _get("USER_BOT_TOKEN", "")      # توكن بوت المستخدمين
ADMIN_BOT_TOKEN = _get("ADMIN_BOT_TOKEN", "")    # توكن بوت لوحة التحكم

# ==================== هويات الإدارة ====================
DEV_ID = int(_get("DEV_ID", "0") or 0)                    # ID المطور
ASSISTANT_ADMIN_ID = int(_get("ASSISTANT_ADMIN_ID", "0") or 0)  # ID مساعد الإدارة
DEV_USERNAME = _get("DEV_USERNAME", "@B_R_S_H_M")    # يوزر المطور (بدون @ في الرسائل)

# ==================== نظام الاشتراك المدفوع ====================
SUBSCRIPTION_PRICE = int(_get("SUBSCRIPTION_PRICE", "250") or 250)      # السعر بالجنيه شهرياً
VODAFONE_CASH_NUMBER = _get("VODAFONE_CASH_NUMBER", "")          # رقم الاستقبال
SUBSCRIPTION_ENABLED = _get("SUBSCRIPTION_ENABLED", "True").lower() == "true"

# ==================== القنوات المطلوب الاشتراك فيها ====================
CHANNELS = [
    {"name": "BRSHAMH FLEX15", "link": "https://t.me/BRSHAMH_FLEX15", "chat_id": "@BRSHAMH_FLEX15"},
    {"name": "BRSHAMHFLEX15", "link": "https://t.me/BRSHAMHFLEX15", "chat_id": "@BRSHAMHFLEX15"},
]

# ==================== قاعدة البيانات ====================
DB_FILE = _get("DB_FILE", "spartan_new.db")
DELETE_OLD_DB_ON_START = _get("DELETE_OLD_DB_ON_START", "False").lower() == "true"

# ==================== مفاتيح الأمان ====================
# مفتاح Fernet لتشفير كلمات المرور المحفوظة (لا يعمل بدون cryptography)
# توليده: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
VAULT_KEY = _get("VAULT_KEY", "")

# ملف سجل العمليات الحساسة
AUDIT_LOG_FILE = _get("AUDIT_LOG_FILE", "audit.log")

# ==================== بيانات عميل تطبيق فودافون ====================
# ⚠️ هذه بيانات عميل التطبيق الرسمي لـ "أنا فودافون" والمطلوبة لمطابقة الـ API.
# معروفة من داخل التطبيق وليست سرية خاصة بك، لكن نتركها في .env لتسهيل التغيير.
VODA_CLIENT_ID = _get("VODA_CLIENT_ID", "ana-vodafone-app")
VODA_CLIENT_SECRET = _get("VODA_CLIENT_SECRET", "")


def validate_config() -> None:
    """
    فحص فوري عند الإقلاع: لو في إعداد حرج ناقص → إيقاف البوت برسالة واضحة
    بدل ما يشتغل بدون حماية (مبدأ Fail-Fast).
    """
    missing = []
    if not USER_BOT_TOKEN:
        missing.append("USER_BOT_TOKEN")
    if not ADMIN_BOT_TOKEN:
        missing.append("ADMIN_BOT_TOKEN")
    if not VAULT_KEY:
        missing.append("VAULT_KEY")
    else:
        # [SECURITY] التأكد إن مفتاح التشفير صالح فعلاً (Fernet)
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            Fernet = None  # المكتبة هتتسطب من requirements.txt — الفحص يتم وقتها
        if Fernet is not None:
            try:
                Fernet(VAULT_KEY.encode("utf-8"))
            except Exception:
                raise SystemExit(
                    "❌ مفتاح التشفير VAULT_KEY غير صالح!\n"
                    "لازم يكون مفتاح Fernet صحيح. ولّد واحد جديد بالأمر:\n"
                    "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
    if DEV_ID == 0:
        missing.append("DEV_ID")
    if missing:
        raise SystemExit(
            "❌ إعدادات حرجة ناقصة: " + ", ".join(missing) + "\n"
            "على Streamlit Cloud: افتح التطبيق ← تبويب Secrets وأضف المتغيرات الناقصة بنفس "
            "الأسماء ثم اعمل Restart للتطبيق.\n"
            "على جهازك: انسخ .env.example إلى .env واملأ القيم ثم شغّل البوت مجدداً."
        )
