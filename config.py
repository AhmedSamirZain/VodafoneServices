# -*- coding: utf-8 -*-
"""
config.py — الإعدادات المركزية للبوت
=================================================
البوت كله محتاج سِرّين (Secrets) بس — مفيش غيرهم:

    BOT_TOKEN   ← توكن البوت من @BotFather
    ADMIN_IDS   ← أرقام تليجرام الأدمن (واحد أو أكتر، مفصولة بفواصل)

على Streamlit Cloud حطّهم في تبويب Secrets بالشكل ده:

    BOT_TOKEN = "123456789:AA...."
    ADMIN_IDS = "111111111, 222222222"

على جهازك: انسخ .env.example إلى .env واملأ نفس القيمتين.

ملاحظات:
    * البوت بقى بوت واحد (مستخدمين + لوحة تحكم في نفس البوت)، فاللي بيحدد
      الأدمن هو ADMIN_IDS مش بوت تاني.
    * أول رقم في ADMIN_IDS = المطور الأساسي (DEV_ID)، والباقي أدمن بنفس الصلاحيات.
    * مفتاح تشفير كلمات المرور (VAULT_KEY) بقى بيتشتق تلقائياً من BOT_TOKEN،
      يعني مش محتاج تضيفه في الـ Secrets. لو حبيت مفتاح مستقل، ضيف VAULT_KEY
      وهو هيتقدّم على المفتاح المشتق.
"""

import base64
import hashlib
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


def _st_secret(name: str):
    """
    لو شغالين جوا ستريمليت (زي Streamlit Cloud)، اقرأ القيمة من st.secrets
    كمان — احتياطياً لو الـ Secrets مش ظاهرة كمتغيرات بيئة.
    """
    try:
        import streamlit as st  # noqa: F401
        val = st.secrets.get(name)
        if val is not None:
            return val
    except Exception:
        pass
    return None


def _raw(name: str, *fallbacks: str):
    """
    متغير بيئة أولاً، ثم Secrets ستريمليت، ثم أسماء قديمة (لو موجودة) —
    عشان الإعدادات القديمة ماتكسرش.
    """
    val = os.getenv(name)
    if val is not None and val != "":
        return val
    val = _st_secret(name)
    if val is not None and val != "":
        return val
    for alt in fallbacks:
        val = os.getenv(alt)
        if val is not None and val != "":
            return val
        val = _st_secret(alt)
        if val is not None and val != "":
            return val
    return None


def _get(name: str, default: str = "", *fallbacks: str) -> str:
    """نفس _raw لكن بيرجّع نص دايماً (القوائم بتتحول لنص مفصول بفواصل)"""
    val = _raw(name, *fallbacks)
    if val is None:
        return default
    if isinstance(val, (list, tuple, set)):
        return ", ".join(str(v) for v in val)
    return str(val)


def _parse_ids(value: str) -> list:
    """
    تحويل نص الأرقام لنصوص أرقام صحيحة.
    بيقبل الفواصل والمسافات والأسطر الجديدة:  "111, 222 333\n444"
    """
    ids = []
    for chunk in (value or "").replace(";", ",").replace("\n", ",").replace(" ", ",").split(","):
        chunk = chunk.strip()
        if chunk.lstrip("-").isdigit():
            num = int(chunk)
            if num != 0 and num not in ids:
                ids.append(num)
    return ids


# ==================== 1) توكن البوت (السِرّ الوحيد الإجباري) ====================
# BOT_TOKEN هو الاسم الأساسي. الأسماء القديمة (USER_BOT_TOKEN / ADMIN_BOT_TOKEN)
# بتشتغل كخطة بديلة لو لسه موجودة عندك.
BOT_TOKEN = _get("BOT_TOKEN", "", "USER_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")

# ==================== 2) هويات الإدارة (السِرّ التاني الإجباري) ====================
ADMIN_IDS = _parse_ids(_get("ADMIN_IDS", "", "DEV_ID"))

# أسماء قديمة لسه مستخدمة جوا الكود — بتتشتق من ADMIN_IDS أوتوماتيك:
DEV_ID = ADMIN_IDS[0] if ADMIN_IDS else 0                      # المطور الأساسي
ASSISTANT_ADMIN_ID = ADMIN_IDS[1] if len(ADMIN_IDS) > 1 else 0  # أول مساعد
ADMINS = set(ADMIN_IDS)                                        # كل الأدمن (مجموعة)

# اسم البوت للعرض في العناوين والرسائل
BOT_NAME = _get("BOT_NAME", "VodafoneServices")

# يوزر المطور للعرض فقط (مش سِر) — حط يوزرك من .env / Secrets عشان زرار "تواصل مع المطور" يشتغل.
# لو فاضي، الزرار مش هيظهر ومفيش حاجة هتتكسر.
DEV_USERNAME = _get("DEV_USERNAME", "")


# ==================== مفتاح التشفير (مشتق من BOT_TOKEN) ====================
def _derive_vault_key(bot_token: str) -> str:
    """
    توليد مفتاح Fernet صحيح من توكن البوت نفسه (SHA-256 → 32 بايت → base64url).
    ثابت لكل توكن، يعني كلمات المرور المحفوظة تفضل تفك بعد إعادة التشغيل.
    ⚠️ لو عملت Revoke للتوكن من @BotFather، المفتاح هيتغير وكلمات المرور
       المحفوظة هتتنسى (البوت بيتعامل معاها كأنها مش محفوظة — مفيش خطأ).
    """
    digest = hashlib.sha256(
        ("vodafone-bot::vault-v1::" + (bot_token or "")).encode("utf-8")
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


_vault_key_explicit = _get("VAULT_KEY", "")
if _vault_key_explicit:
    VAULT_KEY = _vault_key_explicit
    VAULT_KEY_SOURCE = "VAULT_KEY من الـ Secrets/.env"
else:
    VAULT_KEY = _derive_vault_key(BOT_TOKEN)
    VAULT_KEY_SOURCE = "مشتق تلقائياً من BOT_TOKEN"


# ==================== نظام الاشتراك المدفوع (اختياري) ====================
SUBSCRIPTION_PRICE = int(_get("SUBSCRIPTION_PRICE", "250") or 250)   # السعر بالجنيه شهرياً
VODAFONE_CASH_NUMBER = _get("VODAFONE_CASH_NUMBER", "")              # رقم الاستقبال
SUBSCRIPTION_ENABLED = _get("SUBSCRIPTION_ENABLED", "True").lower() == "true"

# ==================== قاعدة البيانات (اختياري) ====================
DB_FILE = _get("DB_FILE", "vodafoneservices.db")
# ترحيل تلقائي من اسم قاعدة البيانات القديم (أول تشغيل بعد التحديث فقط)
if DB_FILE == "vodafoneservices.db" and not os.path.exists(DB_FILE) and os.path.exists("spartan_new.db"):
    try:
        import shutil
        shutil.copy2("spartan_new.db", DB_FILE)
    except Exception:
        pass
DELETE_OLD_DB_ON_START = _get("DELETE_OLD_DB_ON_START", "False").lower() == "true"

# ملف سجل العمليات الحساسة
AUDIT_LOG_FILE = _get("AUDIT_LOG_FILE", "audit.log")

# ==================== بيانات عميل تطبيق فودافون (اختياري) ====================
# لو عندك سر عميل "أنا فودافون" حطه هنا، ولو مش عندك سيبه فاضي —
# البوت بيستخدم بيانات موقع فودافون كبديل تلقائي وتسجيل الدخول شغال من غيره.
VODA_CLIENT_ID = _get("VODA_CLIENT_ID", "ana-vodafone-app")
VODA_CLIENT_SECRET = _get("VODA_CLIENT_SECRET", "")


def validate_config() -> None:
    """
    فحص فوري عند الإقلاع: لو في إعداد حرج ناقص → إيقاف البوت برسالة واضحة
    بدل ما يشتغل بدون حماية (مبدأ Fail-Fast).
    المطلوب دلوقتي سِرّين بس: BOT_TOKEN و ADMIN_IDS.
    """
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not ADMIN_IDS:
        missing.append("ADMIN_IDS")

    if BOT_TOKEN and VAULT_KEY:
        # [SECURITY] التأكد إن مفتاح التشفير صالح فعلاً (Fernet)
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            Fernet = None  # المكتبة هتتسطب من requirements.txt — الفحص يتمها
        if Fernet is not None:
            try:
                Fernet(VAULT_KEY.encode("utf-8"))
            except Exception:
                raise SystemExit(
                    "❌ مفتاح التشفير VAULT_KEY غير صالح!\n"
                    "سيب VAULT_KEY فاضي وسيب البوت يشتقه من BOT_TOKEN، أو ولّد واحد جديد:\n"
                    "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )

    if missing:
        raise SystemExit(
            "❌ إعدادات حرجة ناقصة: " + ", ".join(missing) + "\n\n"
            "البوت محتاج سِرّين بس:\n"
            "  BOT_TOKEN  = توكن البوت من @BotFather\n"
            "  ADMIN_IDS  = أرقام تليجرام الأدمن (مثال: 111111111, 222222222)\n\n"
            "على Streamlit Cloud: افتح التطبيق ← تبويب Secrets وأضف الاتنين بنفس "
            "الأسماء ثم اعمل Restart للتطبيق.\n"
            "على جهازك: انسخ .env.example إلى .env واملأ القيمتين ثم شغّل البوت مجدداً."
        )
