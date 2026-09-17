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


# ==================== توكنات البوت (سرية - من .env) ====================
USER_BOT_TOKEN = os.getenv("USER_BOT_TOKEN", "")      # توكن بوت المستخدمين
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")    # توكن بوت لوحة التحكم

# ==================== هويات الإدارة ====================
DEV_ID = int(os.getenv("DEV_ID", "0"))                    # ID المطور
ASSISTANT_ADMIN_ID = int(os.getenv("ASSISTANT_ADMIN_ID", "0"))  # ID مساعد الإدارة
DEV_USERNAME = os.getenv("DEV_USERNAME", "@B_R_S_H_M")    # يوزر المطور (بدون @ في الرسائل)

# ==================== نظام الاشتراك المدفوع ====================
SUBSCRIPTION_PRICE = int(os.getenv("SUBSCRIPTION_PRICE", "250"))      # السعر بالجنيه شهرياً
VODAFONE_CASH_NUMBER = os.getenv("VODAFONE_CASH_NUMBER", "")          # رقم الاستقبال
SUBSCRIPTION_ENABLED = os.getenv("SUBSCRIPTION_ENABLED", "True").lower() == "true"

# ==================== القنوات المطلوب الاشتراك فيها ====================
CHANNELS = [
    {"name": "BRSHAMH FLEX15", "link": "https://t.me/BRSHAMH_FLEX15", "chat_id": "@BRSHAMH_FLEX15"},
    {"name": "BRSHAMHFLEX15", "link": "https://t.me/BRSHAMHFLEX15", "chat_id": "@BRSHAMHFLEX15"},
]

# ==================== قاعدة البيانات ====================
DB_FILE = os.getenv("DB_FILE", "spartan_new.db")
DELETE_OLD_DB_ON_START = os.getenv("DELETE_OLD_DB_ON_START", "False").lower() == "true"

# ==================== مفاتيح الأمان ====================
# مفتاح Fernet لتشفير كلمات المرور المحفوظة (لا يعمل بدون cryptography)
# توليده: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
VAULT_KEY = os.getenv("VAULT_KEY", "")

# ملف سجل العمليات الحساسة
AUDIT_LOG_FILE = os.getenv("AUDIT_LOG_FILE", "audit.log")

# ==================== بيانات عميل تطبيق فودافون ====================
# ⚠️ هذه بيانات عميل التطبيق الرسمي لـ "أنا فودافون" والمطلوبة لمطابقة الـ API.
# معروفة من داخل التطبيق وليست سرية خاصة بك، لكن نتركها في .env لتسهيل التغيير.
VODA_CLIENT_ID = os.getenv("VODA_CLIENT_ID", "ana-vodafone-app")
VODA_CLIENT_SECRET = os.getenv("VODA_CLIENT_SECRET", "")


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
    if DEV_ID == 0:
        missing.append("DEV_ID")
    if missing:
        raise SystemExit(
            "❌ إعدادات حرجة ناقصة في ملف .env: " + ", ".join(missing)
            + "\nانسخ .env.example إلى .env واملأ القيم ثم شغّل البوت مجدداً."
        )
