# -*- coding: utf-8 -*-
"""
Vodafone_fixed.py — بوت تليجرام كامل لإدارة مجموعة Vodafone Red + لوحة تحكم الأدمن
====================================================================================
بوت واحد بيخدم المستخدمين ولوحة التحكم في نفس الوقت (bot is user_bot is admin_bot).

المستخدم العادي:
    /start            → قائمة الخدمات (نظام الاشتراك + مجموعة Red)
    تسجيل دخول فودافون → إرسال دعوة / قبول / تقسيم الباقة / إخراج عضو /
                          عمليات تلقائية / تغيير المالك

الأدمن (ADMIN_IDS):
    /start            → لوحة التحكم (إحصائيات، بث، سجل تدقيق، إعدادات، اشتراكات)

طريقة التشغيل:
    • من Streamlit : streamlit run streamlit_app.py   (يبدأ البوت في خيط خلفي)
    • من الكونسول  : python Vodafone_fixed.py

الإعدادات (سِرّين بس): BOT_TOKEN + ADMIN_IDS — انظر config.py و .env.example
"""

from __future__ import annotations

import contextlib
import io
import os
import sqlite3
import threading
import time
import traceback
from datetime import datetime

import requests
import telebot
from telebot import types

from config import (
    ADMINS,
    BOT_NAME,
    BOT_TOKEN,
    DB_FILE,
    DELETE_OLD_DB_ON_START,
    DEV_ID,
    DEV_USERNAME,
    SUBSCRIPTION_ENABLED,
    SUBSCRIPTION_PRICE,
    VODAFONE_CASH_NUMBER,
    VAULT_KEY,
    VAULT_KEY_SOURCE,
    VODA_CLIENT_SECRET,
    validate_config,
)
from security import (
    STATE_LOCK,
    PasswordVault,
    RateLimiter,
    audit,
    is_egyptian_mobile,
    sanitize_text,
)

# فشل الإعدادات الحرجّة → SystemExit برسالة واضحة (Streamlit بيقفها ويعرضها)
validate_config()

# سر عميل تطبيق "أنا فودافون" (القيمة الافتراضية من التطبيق — لو عندك سر خاص حطه في .env)
_DEFAULT_CLIENT_SECRET = "95fd95fb-7489-4958-8ae6-d31a525cd20a"

try:
    vault = PasswordVault(VAULT_KEY.encode("utf-8"))
except Exception:  # cryptography ناقصة أو مفتاح غير صالح — الخزنة تبقى معطّلة
    vault = None

# قفل تسلسل عمليات فودافون (redirect_stdout عام في العملية)
OPS_LOCK = threading.RLock()

# مقييد محاولات تسجيل دخول فودافون: 5 محاولات كل 15 دقيقة لكل مستخدم
login_limiter = RateLimiter(max_hits=5, window_seconds=900)

# =====================================================================
# 1) طبقة الخدمات — كلاس VodafoneRed (من الكونسول إلى البوت، بلا input())
# =====================================================================

QUOTA_PRESETS = [
    ("15,000 ميجا · 2,000 د · 200 ر", "15000", "2000", "200"),
    ("25,000 ميجا · 2,500 د · 200 ر", "25000", "2500", "200"),
    ("28,000 ميجا · 3,000 د · 200 ر", "28000", "3000", "200"),
    ("30,000 ميجا · 3,500 د · 200 ر", "30000", "3500", "200"),
    ("35,000 ميجا · 4,500 د · 200 ر", "35000", "4500", "200"),
    ("40,000 ميجا · 6,000 د · 200 ر", "40000", "6000", "200"),
    ("45,000 ميجا · 6,000 د · 200 ر", "45000", "6000", "200"),
    ("50,000 ميجا · 7,000 د · 200 ر", "50000", "7000", "200"),
    ("55,000 ميجا · 7,000 د · 200 ر", "55000", "7000", "200"),
    ("60,000 ميجا · 8,000 د · 200 ر", "60000", "8000", "200"),
    ("65,000 ميجا · 8,000 د · 200 ر", "65000", "8000", "200"),
    ("75,000 ميجا · 9,500 د · 200 ر", "75000", "9500", "200"),
    ("87,000 ميجا · 9,950 د · 200 ر", "87000", "9950", "200"),
    ("110,000 ميجا · 10,000 د · 200 ر", "110000", "10000", "200"),
    ("200,000 ميجا · 10,300 د · 200 ر", "200000", "10300", "200"),
    ("250 جيجا · 20,000 د · 200 ر", "250000", "20000", "200"),
]


class VodafoneRed:
    """عمليات مجموعة Vodafone Red — كل الدوال ترجع bool وتطبع تفاصيلها عشان تتسجّل."""

    def __init__(self, number, password):
        self.number = number
        self.password = password
        self.access_token = None
        self.req = requests.Session()

    # ---------------------------------------------------------------- login
    def login(self):
        """تسجيل الدخول والحصول على توكن"""
        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "silentLogin": "false",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "mobile.vodafone.com.eg",
            "User-Agent": "okhttp/4.11.0",
        }
        data = {
            "username": self.number,
            "password": self.password,
            "grant_type": "password",
            "client_secret": VODA_CLIENT_SECRET or _DEFAULT_CLIENT_SECRET,
            "client_id": "ana-vodafone-app",
        }
        for attempt in range(3):
            try:
                print(f"[→] محاولة {attempt + 1} من 3...")
                response = self.req.post(url, headers=headers, data=data, timeout=30)
                result = response.json()
                if "access_token" in result:
                    self.access_token = result["access_token"]
                    print(f"[✅] تم تسجيل الدخول بنجاح للرقم {self.number}")
                    return True
                print(f"[❌] فشل تسجيل الدخول: {result.get('error_description', 'بيانات غير صحيحة')}")
                return False
            except Exception as e:
                print(f"[❌] محاولة {attempt + 1} فشلت: {e}")
                if attempt < 2:
                    print("[→] إعادة المحاولة بعد 3 ثواني...")
                    time.sleep(3)
                else:
                    print("[❌] فشل الاتصال بعد 3 محاولات")
                    return False
        return False

    # --------------------------------------------------------------- headers
    def get_headers(self, token=None, msisdn=None, additional_headers=None):
        """إنشاء الهيدرز الموحدة"""
        headers = {
            "Authorization": f"Bearer {token or self.access_token}",
            "api-version": "v2",
            "x-agent-operatingsystem": "16",
            "clientId": "AnaVodafoneAndroid",
            "x-agent-device": "Samsung SM-S938B",
            "x-agent-version": "2026.6.2",
            "x-agent-build": "1171",
            "msisdn": msisdn or self.number,
            "Accept": "application/json",
            "Accept-Language": "ar",
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "mobile.vodafone.com.eg",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "User-Agent": "okhttp/4.12.0",
        }
        if additional_headers:
            headers.update(additional_headers)
        return headers

    def choose_quota(self):
        """كمية التقسيم الافتراضية (الواجهة التفاعلية في البوت عبر أزرار الكوتكود)"""
        return "15000", "2000", "200"

    # ----------------------------------------------------------- invitations
    def send_invitation_auto(self, member2):
        """إرسال دعوة بدون تفاعل المستخدم"""
        if not member2:
            print("[❌] الرقم لا يمكن أن يكون فارغاً")
            return False
        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        headers = self.get_headers()
        headers.update({"device-id": "9837e2b64f728632", "x-agent-operatingsystem": "16"})
        data_invite = {
            "category": [
                {"listHierarchyId": "PackageID", "value": "8804"},
                {"listHierarchyId": "TemplateID", "value": "880"},
                {"listHierarchyId": "TierID", "value": "8804"},
            ],
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "MI", "value": "5"},
                        {"characteristicName": "Voice", "value": "5"},
                        {"characteristicName": "extraMember", "value": "0"},
                    ]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"},
                ],
            },
            "type": "SendInvitation",
        }
        try:
            print("[→] جاري إرسال الدعوة...")
            response = self.req.post(url, headers=headers, json=data_invite, timeout=30)
            if response.status_code in (200, 201):
                print(f"[✅] تم إرسال الدعوة بنجاح إلى {member2}")
                try:
                    print(f"[→] الرد: {response.json()}")
                except Exception:
                    pass
                return True
            print(f"[❌] فشل الإرسال - رمز الخطأ: {response.status_code}")
            if response.text:
                print(response.text)
            return False
        except Exception as e:
            print(f"[❌] خطأ في الإرسال: {e}")
            return False

    def accept_invitation_with_retry(self, member2, password2, max_retries=3, delay=5):
        """قبول دعوة مع إعادة محاولة تلقائية (يسجّل دخول العضو الثاني ثم يقبل)"""
        print(f"[→] بدء قبول الدعوة مع {max_retries} محاولات...")
        url_token = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        headers_token = {
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "mobile.vodafone.com.eg",
            "User-Agent": "okhttp/4.11.0",
        }
        data_token = {
            "username": member2,
            "password": password2,
            "grant_type": "password",
            "client_secret": VODA_CLIENT_SECRET or _DEFAULT_CLIENT_SECRET,
            "client_id": "ana-vodafone-app",
        }
        url_accept = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        data_accept = {
            "category": [{"listHierarchyId": "TemplateID", "value": "880"}],
            "name": "EnterpriseRedFamily",
            "parts": {
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"},
                ]
            },
            "type": "AcceptInvitation",
        }
        for attempt in range(1, max_retries + 1):
            print(f"[→] محاولة قبول الدعوة رقم {attempt} من {max_retries}")
            try:
                res_token = requests.post(url_token, headers=headers_token, data=data_token, timeout=30)
                if res_token.status_code != 200:
                    print(f"[❌] فشل تسجيل الدخول - رمز الخطأ: {res_token.status_code}")
                    if attempt < max_retries:
                        print(f"[→] انتظار {delay} ثواني ثم إعادة المحاولة...")
                        time.sleep(delay)
                        continue
                    return False
                token_data = res_token.json()
                if "access_token" not in token_data:
                    print(f"[❌] فشل تسجيل الدخول: {token_data.get('error_description', 'توكن غير موجود')}")
                    if attempt < max_retries:
                        time.sleep(delay)
                        continue
                    return False
                token_member2 = token_data["access_token"]
                print("[✅] تم تسجيل دخول الرقم الثاني")

                headers_accept = self.get_headers(token=token_member2, msisdn=member2)
                headers_accept.update({
                    "x-agent-operatingsystem": "16",
                    "device-id": "9837e2b64f728632",
                    "api_id": "APP",
                })
                print("[→] جاري قبول الدعوة...")
                response = requests.patch(url_accept, headers=headers_accept, json=data_accept, timeout=30)
                if response.status_code in (200, 201):
                    print(f"[✅] تم قبول الدعوة بنجاح في المحاولة رقم {attempt}")
                    try:
                        print(f"[→] الرد: {response.json()}")
                    except Exception:
                        pass
                    return True
                print(f"[❌] فشل قبول الدعوة - رمز الخطأ: {response.status_code}")
                if response.text:
                    print(f"[→] رسالة الخطأ: {response.text[:200]}")
                if attempt < max_retries:
                    time.sleep(delay)
            except requests.exceptions.Timeout:
                print("[❌] انتهت المهلة (Timeout)")
                if attempt < max_retries:
                    time.sleep(delay)
            except requests.exceptions.ConnectionError:
                print("[❌] مشكلة في الاتصال بالإنترنت")
                if attempt < max_retries:
                    time.sleep(delay)
            except Exception as e:
                print(f"[❌] خطأ غير متوقع: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
        print("[❌] تم استنفاذ جميع المحاولات")
        return False

    # --------------------------------------------------------------- quota
    def redistribute_quota(self, member2=None, mi=None, voice=None, sms=None):
        """تقسيم الباقة (لو الكمية مش محددة يتاخد الاختيار الافتراضي)"""
        if not member2:
            print("[❌] الرقم لا يمكن أن يكون فارغاً")
            return False
        if not mi or not voice or not sms:
            mi, voice, sms = self.choose_quota()
        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        headers = self.get_headers()
        headers.update({
            "device-id": "9837e2b64f728632",
            "x-agent-operatingsystem": "16",
            "Connection": "close",
        })
        data = {
            "category": [{"listHierarchyId": "TemplateID", "value": "880"}],
            "createdBy": {"value": "MobileApp"},
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "MI", "value": str(mi)},
                        {"characteristicName": "Voice", "value": str(voice)},
                        {"characteristicName": "SMS", "value": str(sms)},
                    ]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"},
                ],
            },
            "type": "QuotaRedistribution",
        }
        for attempt in range(3):
            try:
                print(f"[→] جاري تقسيم الباقة... محاولة {attempt + 1} من 3")
                response = self.req.patch(url, headers=headers, json=data, timeout=30)
                if response.status_code in (200, 201):
                    print("[✅] تم تقسيم الباقة بنجاح")
                    print(f"[→] {mi} ميجا، {voice} دقيقة، {sms} رسالة للرقم {member2}")
                    try:
                        print(f"[→] الرد: {response.json()}")
                    except Exception:
                        pass
                    return True
                print(f"[❌] فشل التقسيم - رمز الخطأ: {response.status_code}")
                if response.text:
                    print(response.text)
                return False
            except Exception as e:
                print(f"[❌] محاولة {attempt + 1} فشلت: {e}")
                if attempt < 2:
                    time.sleep(3)
                else:
                    print("[❌] فشل تقسيم الباقة بعد 3 محاولات")
                    return False
        return False

    def cancel_invitation(self, member2=None):
        """إخراج عضو من الباقة / إلغاء دعوة"""
        if not member2:
            print("[❌] الرقم لا يمكن أن يكون فارغاً")
            return False
        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        headers = self.get_headers()
        headers.update({"device-id": "9837e2b64f728632", "x-agent-operatingsystem": "16"})
        data = {
            "category": [{"listHierarchyId": "TemplateID", "value": "880"}],
            "createdBy": {"value": "MobileApp"},
            "name": "EnterpriseRedFamily",
            "parts": {
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": member2}], "type": "Member"},
                    {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Owner"},
                ]
            },
            "type": "CancelInvitation",
        }
        try:
            print("[→] جاري إخراج العضو من الباقة...")
            response = self.req.patch(url, headers=headers, json=data, timeout=30)
            if response.status_code in (200, 201):
                print(f"[✅] تم إخراج العضو {member2} من الباقة بنجاح")
                try:
                    print(f"[→] الرد: {response.json()}")
                except Exception:
                    pass
                return True
            print(f"[❌] فشل الإخراج - رمز الخطأ: {response.status_code}")
            if response.text:
                print(response.text)
            return False
        except Exception as e:
            print(f"[❌] خطأ: {e}")
            return False

    # ------------------------------------------------------------ change owner
    def change_owner(self, new_owner=None, new_owner_password=None):
        """تغيير مالك الباقة (يسجّل دخول المالك الجديد ثم يحوّل الملكية)"""
        if not new_owner or not new_owner_password:
            print("[❌] الرقم وكلمة المرور مطلوبان")
            return False
        print(f"[→] جاري تسجيل دخول المالك الجديد {new_owner} ...")
        url_token = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        headers_token = {
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "mobile.vodafone.com.eg",
            "User-Agent": "okhttp/4.11.0",
        }
        data_token = {
            "username": new_owner,
            "password": new_owner_password,
            "grant_type": "password",
            "client_secret": VODA_CLIENT_SECRET or _DEFAULT_CLIENT_SECRET,
            "client_id": "ana-vodafone-app",
        }
        try:
            res_token = requests.post(url_token, headers=headers_token, data=data_token, timeout=30)
            if res_token.status_code != 200:
                print(f"[❌] فشل تسجيل دخول المالك الجديد - رمز الخطأ: {res_token.status_code}")
                return False
            token_data = res_token.json()
            if "access_token" not in token_data:
                print(f"[❌] فشل تسجيل الدخول: {token_data.get('error_description', 'توكن غير موجود')}")
                return False
            token_new_owner = token_data["access_token"]
            print("[✅] تم تسجيل دخول المالك الجديد")

            url_change = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
            headers_change = self.get_headers(token=token_new_owner, msisdn=new_owner)
            headers_change.update({
                "device-id": "9837e2b64f728632",
                "x-agent-operatingsystem": "16",
                "api_id": "APP",
            })
            data_change = {
                "category": [{"listHierarchyId": "TemplateID", "value": "880"}],
                "createdBy": {"value": "MobileApp"},
                "parts": {
                    "member": [
                        {"id": [{"schemeName": "MSISDN", "value": self.number}], "type": "Member"},
                        {"id": [{"schemeName": "MSISDN", "value": new_owner}], "type": "Owner"},
                    ]
                },
                "type": "ChangeOwner",
            }
            print(f"[→] تغيير المالك: {self.number} ← {new_owner}")
            response = requests.patch(url_change, headers=headers_change, json=data_change, timeout=30)
            if response.status_code in (200, 201):
                print("[✅] تم تغيير المالك بنجاح")
                print(f"[→] المالك الجديد: {new_owner} — و{self.number} أصبح عضواً")
                try:
                    print(f"[→] الرد: {response.json()}")
                except Exception:
                    pass
                self.number = new_owner
                return True
            print(f"[❌] فشل تغيير المالك - رمز الخطأ: {response.status_code}")
            if response.text:
                print(response.text)
            return False
        except Exception as e:
            print(f"[❌] خطأ: {e}")
            return False

    # ----------------------------------------------------------- عمليات مركبة
    def send_then_auto_accept(self, member2, password2, wait_seconds=20):
        """إرسال دعوة ← انتظار ← قبول تلقائي مع إعادة المحاولة"""
        print("=" * 50)
        print("[→] الخطوة 1: إرسال الدعوة")
        if not self.send_invitation_auto(member2):
            print("[❌] فشل إرسال الدعوة، لن يتم المتابعة")
            return False
        print(f"[→] الخطوة 2: انتظار {wait_seconds} ثانية حتى تظهر الدعوة...")
        time.sleep(wait_seconds)
        print("[✅] انتظار انتهى")
        print("[→] الخطوة 3: قبول الدعوة مع إعادة المحاولة")
        ok = self.accept_invitation_with_retry(member2, password2, max_retries=3, delay=5)
        if ok:
            print("[✅] اكتملت العملية بنجاح")
        else:
            print("[❌] فشلت العملية بعد 3 محاولات")
            print("[→] تأكد إن الدعوة لسه فعالة والرقم الثاني صحيح")
        return ok

    def redistribute_then_auto_cancel(self, member2, mi=None, voice=None, sms=None, wait_seconds=20):
        """تقسيم ← انتظار ← إلغاء تلقائي"""
        print("=" * 50)
        if not self.redistribute_quota(member2, mi, voice, sms):
            return False
        print(f"[→] انتظار {wait_seconds} ثانية ثم إلغاء الدعوة تلقائياً...")
        time.sleep(wait_seconds)
        print("[✅] انتظار انتهى")
        ok = self.cancel_invitation(member2)
        if ok:
            print("[✅] اكتملت العملية بنجاح")
        else:
            print("[❌] فشلت عملية الإلغاء")
        return ok


# =====================================================================
# 2) بوت التليجرام — بوت واحد (مستخدمين + أدمن)
# =====================================================================

bot = telebot.TeleBot(BOT_TOKEN)
user_bot = bot
admin_bot = bot

# حالة البوت المشتركة (is_running / admin_action / since / started ...)
bot_status = {
    "is_running": True,        # المعالجات جاهزة للرد
    "admin_action": None,      # إجراء أدمن منتظر (بث / تعديل إعداد)
    "started": False,          # استُدعي start() ومشغّل خيط البولنغ
    "since": None,
    "last_error": None,
}

# جلسات المستخدمين في الذاكرة (الخطوة الحالية + كلاس VodafoneRed بعد تسجيل الدخول)
user_sessions: dict = {}


def _session(uid: int) -> dict:
    with STATE_LOCK:
        s = user_sessions.get(uid)
        if s is None:
            s = {"step": None, "op": None, "member": None, "member_pw": None,
                 "msisdn": None, "app": None}
            user_sessions[uid] = s
        return s


def _clear_flow(uid: int) -> None:
    with STATE_LOCK:
        s = user_sessions.setdefault(uid, {"step": None, "op": None, "member": None,
                                           "member_pw": None, "msisdn": None, "app": None})
        s.update(step=None, op=None, member=None, member_pw=None)


# --------------------------------------------------------------- قاعدة البيانات
_db_lock = threading.Lock()
_db_ready = False


def _db():
    """اتصال SQLite (يُنشأ عند أول استخدام) — لو فشل يرجع None والاستخدامات تتخطّاه."""
    global _db_ready
    try:
        with _db_lock:
            if not _db_ready:
                if (DELETE_OLD_DB_ON_START and DB_FILE not in ("", ":memory:")
                        and os.path.exists(DB_FILE)):
                    try:
                        os.remove(DB_FILE)
                    except OSError:
                        pass
                conn = sqlite3.connect(DB_FILE, timeout=15)
                conn.row_factory = sqlite3.Row
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT DEFAULT '',
                        first_name TEXT DEFAULT '',
                        subscribed INTEGER DEFAULT 0,
                        pending_payment INTEGER DEFAULT 0,
                        vf_msisdn TEXT DEFAULT '',
                        vf_pass_sealed TEXT DEFAULT '',
                        created_at TEXT,
                        last_seen TEXT
                    )"""
                )
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS settings (
                        k TEXT PRIMARY KEY, v TEXT
                    )"""
                )
                conn.commit()
                conn.close()
                _db_ready = True
        conn = sqlite3.connect(DB_FILE, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _touch_user(message) -> None:
    uid = message.from_user.id
    uname = getattr(message.from_user, "username", "") or ""
    fname = getattr(message.from_user, "first_name", "") or ""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = _db()
        if conn is None:
            return
        with conn:
            conn.execute(
                """INSERT INTO users (user_id, username, first_name, created_at, last_seen)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     username=excluded.username, first_name=excluded.first_name,
                     last_seen=excluded.last_seen""",
                (uid, uname, fname, now, now),
            )
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _user_row(uid: int):
    try:
        conn = _db()
        if conn is None:
            return None
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        return row
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _set_user_fields(uid: int, **fields) -> None:
    if not fields:
        return
    try:
        conn = _db()
        if conn is None:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        with conn:
            conn.execute(f"UPDATE users SET {cols} WHERE user_id=?", (*fields.values(), uid))
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _all_user_ids() -> list:
    try:
        conn = _db()
        if conn is None:
            return []
        return [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _counts() -> dict:
    out = {"total": 0, "subscribed": 0, "pending": 0}
    try:
        conn = _db()
        if conn is None:
            return out
        out["total"] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        out["subscribed"] = conn.execute(
            "SELECT COUNT(*) FROM users WHERE subscribed=1").fetchone()[0]
        out["pending"] = conn.execute(
            "SELECT COUNT(*) FROM users WHERE pending_payment=1").fetchone()[0]
        return out
    except Exception:
        return out
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _setting(k: str, default: str) -> str:
    try:
        conn = _db()
        if conn is None:
            return default
        row = conn.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
        return row[0] if row else default
    except Exception:
        return default
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _set_setting(k: str, v: str) -> None:
    try:
        conn = _db()
        if conn is None:
            return
        with conn:
            conn.execute(
                "INSERT INTO settings (k, v) VALUES (?, ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (k, str(v)),
            )
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _subscribed(uid: int) -> bool:
    if uid in ADMINS:
        return True
    if not SUBSCRIPTION_ENABLED:
        return True
    row = _user_row(uid)
    if row is None:
        return False
    return bool(row["subscribed"])


# --------------------------------------------------------------- لجان البناء
def _main_menu(uid: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("👥 مجموعة Vodafone Red", callback_data="red"))
    kb.add(types.InlineKeyboardButton("📦 خدماتي واشتراكي", callback_data="my_services"))
    if DEV_USERNAME:
        kb.add(types.InlineKeyboardButton("📞 تواصل مع المطور", callback_data="contact_dev"))
    kb.add(types.InlineKeyboardButton("ℹ️ حول", callback_data="about"),
           types.InlineKeyboardButton("❓ مساعدة", callback_data="help"))
    return kb


def _red_entry_kb(uid: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    row = _user_row(uid)
    if row is not None and row["vf_msisdn"] and vault is not None:
        kb.add(types.InlineKeyboardButton("⚡ دخول سريع (رقم محفوظ)", callback_data="quick_login"))
    kb.add(types.InlineKeyboardButton("🔐 تسجيل دخول فودافون", callback_data="login_start"))
    kb.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="menu"))
    return kb


def _red_menu_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📨 إرسال دعوة", callback_data="op_invite"),
        types.InlineKeyboardButton("✅ قبول دعوة", callback_data="op_accept"),
    )
    kb.add(
        types.InlineKeyboardButton("📊 تقسيم الباقة", callback_data="op_split"),
        types.InlineKeyboardButton("🚪 إخراج عضو", callback_data="op_remove"),
    )
    kb.add(
        types.InlineKeyboardButton("⚡ إرسال ← قبول تلقائي", callback_data="op_auto_accept"),
        types.InlineKeyboardButton("🔄 تقسيم ← إلغاء تلقائية", callback_data="op_auto_split"),
    )
    kb.add(types.InlineKeyboardButton("👑 تغيير مالك الباقة", callback_data="op_owner"))
    kb.add(
        types.InlineKeyboardButton("🔄 جلسة جديدة (إعادة دخول)", callback_data="relogin"),
        types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="menu"),
    )
    return kb


def _quota_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for label, mi, voice, sms in QUOTA_PRESETS:
        kb.add(types.InlineKeyboardButton(label, callback_data=f"quota:{mi}:{voice}:{sms}"))
    kb.add(types.InlineKeyboardButton("✏️ كمية مخصصة (ترسل بالرسالة)", callback_data="quota_custom"))
    kb.add(types.InlineKeyboardButton("↩️ رجوع", callback_data="red_menu"))
    return kb


def _subscribe_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("✅ أنا دفعت — تأكيد العملية", callback_data="pay_request"))
    kb.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="menu"))
    return kb


def _admin_kb():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
        types.InlineKeyboardButton("📋 سجل التدقيق", callback_data="admin_audit"),
    )
    kb.add(
        types.InlineKeyboardButton("📢 بث رسالة", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("👥 المستخدمون", callback_data="admin_users"),
    )
    kb.add(
        types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings"),
        types.InlineKeyboardButton("🔄 تحديث اللوحة", callback_data="admin_refresh"),
    )
    return kb


def _admin_settings_kb():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("💵 تعديل سعر الاشتراك", callback_data="admin_set_price"))
    kb.add(types.InlineKeyboardButton("📱 تعديل رقم فودافون كاش", callback_data="admin_set_cash"))
    kb.add(types.InlineKeyboardButton("↩️ رجوع للوحة", callback_data="admin_panel"))
    return kb


def _sub_decision_kb(uid: int):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"sub_ok:{uid}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"sub_no:{uid}"),
    )
    return kb


# --------------------------------------------------------------- أدوات عامة
def _capture(fn, *args, **kwargs):
    """تشغيل دالة و التقاط كل print اللي طلع منها (يعمل تحت قفل تسلسل العمليات)"""
    buf = io.StringIO()
    try:
        with OPS_LOCK, contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = fn(*args, **kwargs)
        return bool(result), buf.getvalue()
    except Exception:
        return False, buf.getvalue() + "\n" + traceback.format_exc()


def _safe_send(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, sanitize_text(text), **kwargs)
    except Exception:
        return None


def _notify_admins(text: str) -> None:
    for aid in sorted(ADMINS):
        _safe_send(aid, text)


def _submit_op(chat_id, caption, fn, *args, on_done=None, markup=None):
    """تنفيذ عملية فودافون في خيط خلفي + رسالة نتيجة (يعمل concurrency-friendly)"""
    _safe_send(chat_id, f"⏳ {caption}")

    def worker():
        ok, log = _capture(fn, *args)
        head = "✅ نجحت العملية\n\n" if ok else "❌ فشلت العملية\n\n"
        body = (log or "").strip() or "(لا يوجد إخراج إضافي)"
        text = head + body
        kw = {"reply_markup": markup} if (markup is not None and ok) else {}
        _safe_send(chat_id, text, **kw)
        audit.log("vodafone_op", chat_id, f"{getattr(fn, '__name__', 'op')}={'ok' if ok else 'fail'}")
        if on_done:
            try:
                on_done(ok, log)
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True, name=f"vf-op-{chat_id}").start()


def _welcome_text(uid: int, first_name: str) -> str:
    lines = [f"أهلاً {first_name} 👋", f"أنا {BOT_NAME} — بوت خدمات فودافون.", ""]
    if SUBSCRIPTION_ENABLED:
        if uid in ADMINS:
            lines.append("🔑 حسابك: أدمن — كل الصلاحيات مفتوحة.")
        else:
            price = _setting("price", str(SUBSCRIPTION_PRICE))
            lines.append(
                f"📦 الاشتراك الشهري: {price} جنيه — يفتح كل خدمات المجموعة."
                if not _subscribed(uid)
                else "✅ اشتراكك فعّال — كل الخدمات متاحة."
            )
    lines.append("")
    lines.append("اختار من الأزرار تحت 👇")
    return "\n".join(lines)


def _services_text(uid: int) -> str:
    row = _user_row(uid)
    price = _setting("price", str(SUBSCRIPTION_PRICE))
    cash = _setting("cash", VODAFONE_CASH_NUMBER or "—")
    if uid in ADMINS:
        state = "🔑 أدمن"
    elif not SUBSCRIPTION_ENABLED:
        state = "✅ (نظام الاشتراك متوقف — كل شيء مفتوح)"
    elif row is not None and row["subscribed"]:
        state = "✅ مشترك فعّال"
    elif row is not None and row["pending_payment"]:
        state = "⏳ بانتظار تأكيد الدفع"
    else:
        state = "❌ غير مشترك"
    logged = "✅ مسجّل" if (row is not None and row["vf_msisdn"]) else "—"
    return (
        "📦 خدماتي واشتراكي\n"
        "────────────────\n"
        f"الحالة: {state}\n"
        f"سعر الاشتراك: {price} جنيه/شهر\n"
        f"فودافون كاش: {cash}\n"
        f"رقم فودافون المحفوظ: {logged}\n\n"
        "👥 مجموعة Vodafone Red:\n"
        "إرسال/قبول الدعوات، تقسيم الباقة، إخراج عضو، تغيير المالك — كله من زرار واحد."
    )


# =====================================================================
# 3) معالجات المستخدم — مسجّلة على البوت
# =====================================================================

def start_command(message):
    """/start — أدمن يفتح لوحة التحكم، المستخدم العادي يفتح قائمة الخدمات"""
    try:
        uid = message.from_user.id
        first_name = getattr(message.from_user, "first_name", "") or "صديقي"
        if uid in ADMINS:
            admin_start(message)
            return
        _touch_user(message)
        if not bot_status.get("is_running"):
            # مسار مختصر قبل أي نداء شبكة آخر
            bot.reply_to(
                message,
                f"أهلاً {first_name} 👋\n{BOT_NAME} لسه بجهّز نفسه — اضغط /start بعد شوية.",
            )
            return
        _safe_send(
            message.chat.id,
            _welcome_text(uid, first_name),
            reply_markup=_main_menu(uid),
        )
    except Exception:
        try:
            bot.reply_to(message, "حصل خطأ غير متوقع — جرّب /start تاني.")
        except Exception:
            pass


def handle_text_messages(message):
    """كل الرسائل النصية — توجيه إجراء الأدمن المنتظر أو مسار المستخدم العادي"""
    try:
        uid = message.from_user.id
        text = (message.text or "").strip()

        # إجراء أدمن منتظر (بث / تعديل إعداد) → لوحة التحكم
        if uid in ADMINS and bot_status.get("admin_action"):
            admin_handle_text(message)
            return

        _touch_user(message)

        if text in ("/help", "/start@help", "❓ مساعدة", "مساعدة"):
            _safe_send(
                message.chat.id,
                "❓ المساعدة\n"
                "────────────────\n"
                "/start — القائمة الرئيسية\n"
                "/cancel — إلغاء الخطوة الحالية\n"
                "👥 مجموعة Red: سجّل دخول برقمك (أو رقم عندك إذنه) ونفّذ العمليات.\n"
                "📦 الاشتراك: يتفعّل بعد موافقة الأدمن على الدفع.\n"
                "لو واجهت مشكلة راسل المطور من زر «تواصل مع المطور».",
                reply_markup=_main_menu(uid),
            )
            return

        if text in ("/cancel", "إلغاء", "🔙 إلغاء"):
            _clear_flow(uid)
            _safe_send(message.chat.id, "↩️ تم إلغاء الخطوة الحالية.",
                       reply_markup=_main_menu(uid))
            return

        if text == "/menu":
            _safe_send(message.chat.id, _welcome_text(
                uid, getattr(message.from_user, "first_name", "") or "صديقي"),
                reply_markup=_main_menu(uid))
            return

        _handle_user_text(message, text)
    except Exception:
        try:
            bot.send_message(message.chat.id, "⚠️ حصل خطأ — جرّب تاني أو /cancel.")
        except Exception:
            pass


def _handle_user_text(message, text):
    """محادثة المستخدم: تسجيل الدخول + خطوات العمليات"""
    uid = message.from_user.id
    chat_id = message.chat.id
    s = _session(uid)
    step = s.get("step")

    # ---------- رقم فودافون ----------
    if step == "wait_number":
        number = text.replace(" ", "").replace("-", "")
        if not is_egyptian_mobile(number):
            _safe_send(chat_id, "❌ الرقم لازم يكون مصري صحيح (01xxxxxxxxx) — ابعته تاني:")
            return
        s["msisdn"] = number
        s["step"] = "wait_password"
        _safe_send(chat_id, f"🔑 ابعت كلمة مرور «أنا فودافون» للرقم {number}:\n"
                            "(تُستخدم مرة واحدة ولا تُحفظ كنص صريح)")
        return

    # ---------- كلمة مرور المالك ----------
    if step == "wait_password":
        if not login_limiter.allow(uid):
            wait = int(login_limiter.retry_after(uid)) + 1
            _safe_send(chat_id, f"⏳ تجاوزت حد المحاولات — جرّب بعد {wait} ثانية.")
            return
        number = s.get("msisdn")
        password = text
        app = VodafoneRed(number, password)

        def on_done(ok, _log):
            if not ok:
                audit.log("login_fail", uid, number or "")
                return
            audit.log("login_success", uid, number or "")
            with STATE_LOCK:
                s.update(app=app, msisdn=number, step=None, op=None)
            if vault is not None:
                try:
                    _set_user_fields(uid, vf_msisdn=number, vf_pass_sealed=vault.seal(password))
                except Exception:
                    pass
            _safe_send(chat_id, f"✅ أهلاً {number} — اختار العملية:", reply_markup=_red_menu_kb())

        _submit_op(chat_id, f"جاري تسجيل الدخول للرقم {number} ...", app.login, on_done=on_done)
        s["step"] = None
        return

    # ---------- رقم العضو الثاني ----------
    if step == "wait_member":
        member = text.replace(" ", "").replace("-", "")
        if not is_egyptian_mobile(member):
            _safe_send(chat_id, "❌ الرقم لازم يكون مصري صحيح (01xxxxxxxxx) — ابعته تاني:")
            return
        if s.get("msisdn") and member == s["msisdn"]:
            _safe_send(chat_id, "❌ ده رقم المالك نفسه — ابعت رقم العضو الآخر.")
            return
        s["member"] = member
        op = s.get("op")
        app = s.get("app")
        if app is None:
            s["step"] = None
            _safe_send(chat_id, "❌ الجلسة انتهت — سجّل دخول تاني.", reply_markup=_red_entry_kb())
            return

        if op == "invite":
            s["step"] = None
            _submit_op(chat_id, f"جاري إرسال دعوة إلى {member} ...",
                       app.send_invitation_auto, member)
        elif op == "remove":
            s["step"] = None
            _submit_op(chat_id, f"جاري إخراج {member} من الباقة ...",
                       app.cancel_invitation, member)
        elif op == "accept":
            s["step"] = "wait_member_pw"
            _safe_send(chat_id, "🔑 ابعت كلمة مرور الرقم الثاني (للقبول — لا تُحفظ):")
        elif op == "auto_accept":
            s["step"] = "wait_member_pw"
            _safe_send(chat_id, "🔑 ابعت كلمة مرور الرقم الثاني (للقبول التلقائي — لا تُحفظ):")
        elif op == "owner":
            s["step"] = "wait_owner_pw"
            _safe_send(chat_id, "🔑 ابعت كلمة مرور المالك الجديد (لا تُحفظ):")
        elif op in ("split", "auto_split"):
            s["step"] = "wait_quota"
            _safe_send(chat_id, "📊 اختار كمية التقسيم:", reply_markup=_quota_kb())
        else:
            s["step"] = None
            _safe_send(chat_id, "↩️ اختار عملية من القائمة:", reply_markup=_red_menu_kb())
        return

    # ---------- كلمة مرور العضو (قبول / تلقائي) ----------
    if step == "wait_member_pw":
        member, op, app = s.get("member"), s.get("op"), s.get("app")
        s.update(step=None, member_pw=None)
        if app is None or not member:
            _safe_send(chat_id, "❌ الجلسة انتهت — سجّل دخول تاني.", reply_markup=_red_entry_kb())
            return
        pw = text
        if op == "accept":
            _submit_op(chat_id, f"جاري قبول الدعوة من {member} (حتى 3 محاولات) ...",
                       app.accept_invitation_with_retry, member, pw, 3, 5)
        else:
            _submit_op(chat_id, f"جاري: إرسال دعوة إلى {member} ← انتظار ← قبول تلقائي ...",
                       app.send_then_auto_accept, member, pw)
        audit.log("accept_flow", uid, member)
        return

    # ---------- كلمة مرور المالك الجديد ----------
    if step == "wait_owner_pw":
        member, app = s.get("member"), s.get("app")
        s["step"] = None
        if app is None or not member:
            _safe_send(chat_id, "❌ الجلسة انتهت — سجّل دخول تاني.", reply_markup=_red_entry_kb())
            return
        new_owner, pw = member, text

        def on_done(ok, _log):
            if ok:
                audit.log("owner_changed", uid, new_owner)
                with STATE_LOCK:
                    s["msisdn"] = app.number
                _safe_send(chat_id, "👑 تغيير المالك تم — القائمة الجديدة:",
                           reply_markup=_red_menu_kb())

        _submit_op(chat_id, f"جاري تغيير المالك إلى {new_owner} ...",
                   app.change_owner, new_owner, pw, on_done=on_done)
        return

    # ---------- كمية مخصصة ----------
    if step == "wait_custom_quota":
        parts = [p.strip() for p in text.replace("،", ",").split(",")]
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            _safe_send(chat_id, "❌ الصيغة: ميجا, دقائق, رسائل\nمثال: 30000,3000,200")
            return
        s["step"] = None
        _run_split(chat_id, uid, parts[0], parts[1], parts[2])
        return

    # ---------- رسالة عادية (تواصل مع المطور / اقتراح) ----------
    if text in ("📞 تواصل مع المطور", "تواصل مع المطور"):
        if DEV_USERNAME:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("فتح محادثة المطور",
                                              url=f"https://t.me/{DEV_USERNAME.lstrip('@')}"))
            bot.send_message(chat_id, "ابعت لل على تليجرام:", reply_markup=kb)
        else:
            bot.send_message(chat_id, "📞 DEV_USERNAME مش مضبوط في الإعدادات — من فضلك ضبطه في "
                                      ".env / Secrets عشان الزرار يشتغل.")
        return

    # رسالة غير متوقعة → القائمة
    _safe_send(chat_id, "🤔 مش فاهم الخطوة دي — اختار من القائمة:",
               reply_markup=_main_menu(uid))


def _run_split(chat_id, uid, mi, voice, sms):
    s = _session(uid)
    member, app = s.get("member"), s.get("app")
    if app is None or not member:
        _safe_send(chat_id, "❌ الجلسة انتهت — سجّل دخول تاني.", reply_markup=_red_entry_kb())
        return
    _submit_op(chat_id, f"جاري تقسيم {mi} ميجا / {voice} دقيقة / {sms} رسالة إلى {member} ...",
               app.redistribute_quota, member, mi, voice, sms)


# =====================================================================
# 4) معالج الأزرار — توجيه الأدمن ثم مسار المستخدم
# =====================================================================

def handle_callbacks(call):
    """كل ضغطة أزرار — الأدمن يُحوَّل للوحة التحكم، والباقي مسار المستخدم"""
    try:
        uid = call.from_user.id
        data = call.data or ""
        if uid in ADMINS and (
            data.startswith("admin_")
            or data.startswith("sub_ok")
            or data.startswith("sub_no")
            or bot_status.get("admin_action")
        ):
            admin_handle_callbacks(call)
            return
        try:
            bot.answer_callback_query(call.id, "✓")
        except Exception:
            pass
        if not bot_status.get("is_running"):
            return
        _dispatch_user_callback(call, data)
    except Exception:
        try:
            bot.answer_callback_query(call.id, "⚠️ خطأ مؤقت")
        except Exception:
            pass


def _dispatch_user_callback(call, data):
    uid = call.from_user.id
    chat_id = call.message.chat.id if call.message else uid
    msg_id = call.message.message_id if call.message else None
    s = _session(uid)

    def edit(text, markup=None):
        try:
            bot.edit_message_text(sanitize_text(text), chat_id, msg_id, reply_markup=markup)
        except Exception:
            _safe_send(chat_id, text, reply_markup=markup)

    if data == "menu":
        _clear_flow(uid)
        edit(_welcome_text(uid, getattr(call.from_user, "first_name", "") or "صديقي"),
             _main_menu(uid))
        return

    if data == "help":
        edit("❓ اختار «👥 مجموعة Vodafone Red» وسجّل دخول، أو راسل المطور.",
             _main_menu(uid))
        return

    if data == "about":
        dev = f"\nالمطور: {DEV_USERNAME}" if DEV_USERNAME else ""
        edit(f"ℹ️ {BOT_NAME}\nبوت واحد لإدارة مجموعة Vodafone Red ونظام الاشتراك.\n"
             f"يعمل من Streamlit Cloud أو محلياً.{dev}", _main_menu(uid))
        return

    if data == "contact_dev":
        if DEV_USERNAME:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("فتح محادثة المطور",
                                              url=f"https://t.me/{DEV_USERNAME.lstrip('@')}"))
            _safe_send(chat_id, "ابعت لل على تليجرام:", reply_markup=kb)
        else:
            _safe_send(chat_id, "📞 DEV_USERNAME مش مضبوط في الإعدادات.")
        return

    if data == "my_services":
        kb = None
        if SUBSCRIPTION_ENABLED and uid not in ADMINS and not _subscribed(uid):
            kb = _subscribe_kb()
        else:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👥 مجموعة Vodafone Red", callback_data="red"))
            kb.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="menu"))
        edit(_services_text(uid), kb)
        return

    if data == "pay_request":
        row = _user_row(uid)
        if row is not None and row["subscribed"]:
            edit("✅ اشتراكك فعّال بالفعل.", _main_menu(uid))
            return
        _set_user_fields(uid, pending_payment=1)
        audit.log("sub_requested", uid, "pending")
        uname = getattr(call.from_user, "username", "") or ""
        price = _setting("price", str(SUBSCRIPTION_PRICE))
        _notify_admins(
            f"💰 طلب اشتراك جديد\nالمستخدم: {uid} @{uname}\nالسعر: {price} جنيه\n"
            "اضغط ✅ قبول أو ❌ رفض ↓"
        )
        # أزرار القرار تُرسل للأدمن
        for aid in sorted(ADMINS):
            _safe_send(aid, f"قرار الاشتراك للمستخدم {uid}:",
                       reply_markup=_sub_decision_kb(uid))
        edit("⏳ تم استلام طلبك — بانتظار تأكيد الأدمن بعد الدفع.", _main_menu(uid))
        return

    # ---------------- مجموعة Red ----------------
    if data == "red":
        _clear_flow(uid)
        if not _subscribed(uid):
            price = _setting("price", str(SUBSCRIPTION_PRICE))
            cash = _setting("cash", VODAFONE_CASH_NUMBER or "—")
            edit(
                "🔒 مجموعة Red تتطلب اشتراكاً\n"
                f"السعر: {price} جنيه/شهر\n"
                f"فودافون كاش: {cash}\n"
                "دفعت ثم اضغط «أنا دفعت» وستأكد الأدمن.",
                _subscribe_kb(),
            )
            return
        row = _user_row(uid)
        if s.get("app") is not None:
            edit(f"👥 مجموعة Red — جلسة {s.get('msisdn')}\nاختار العملية:",
                 _red_menu_kb())
        elif row is not None and row["vf_msisdn"] and row["vf_pass_sealed"] and vault is not None:
            edit(f"👥 مجموعة Red — عندك رقم محفوظ: {row['vf_msisdn']}\n"
                 "اختار دخول سريع أو سجّل دخول بجلسة جديدة.", _red_entry_kb())
        else:
            edit("👥 مجموعة Red — سجّل دخول برقم المالك وكلمة مرور «أنا فودافون».",
                 _red_entry_kb())
        return

    if data == "login_start":
        if not _subscribed(uid):
            edit("🔒 الاشتراك مطلوب الأول.", _subscribe_kb())
            return
        s.update(step="wait_number", op=None, app=None, member=None)
        _safe_send(chat_id, "📱 ابعت رقم المالك (صيغة 01xxxxxxxxx):")
        return

    if data == "quick_login":
        row = _user_row(uid)
        if row is None or not row["vf_msisdn"] or not row["vf_pass_sealed"] or vault is None:
            edit("❌ مفيش رقم محفوظ — سجّل دخول يدوياً.", _red_entry_kb())
            return
        try:
            pw = vault.open(row["vf_pass_sealed"])
        except Exception:
            edit("⚠️ تعذّر فك كلمة المرور المحفوظة — سجّل دخول تاني.", _red_entry_kb())
            return
        number = row["vf_msisdn"]
        app = VodafoneRed(number, pw)

        def on_done(ok, _log):
            if not ok:
                audit.log("login_fail", uid, number)
                _safe_send(chat_id, "❌ فشل الدخول السريع — سجل يدوياً.",
                           reply_markup=_red_entry_kb())
                return
            audit.log("login_success", uid, number)
            with STATE_LOCK:
                s.update(app=app, msisdn=number, step=None, op=None)
            _safe_send(chat_id, f"✅ أهلاً {number} — اختار العملية:",
                       reply_markup=_red_menu_kb())

        _submit_op(chat_id, f"جاري الدخول السريع للرقم {number} ...", app.login, on_done=on_done)
        return

    if data == "relogin":
        with STATE_LOCK:
            s.update(app=None, msisdn=None, step="wait_number", op=None, member=None)
        if vault is not None:
            _set_user_fields(uid, vf_msisdn="", vf_pass_sealed="")
        _safe_send(chat_id, "📱 ابعت رقم المالك الجديد (01xxxxxxxxx):")
        return

    if data == "red_menu":
        if s.get("app") is None:
            edit("🔐 سجّل دخول الأول.", _red_entry_kb())
        else:
            edit("👥 اختار العملية:", _red_menu_kb())
        return

    ops_map = {
        "op_invite": ("invite", "wait_member", "📨 إرسال دعوة — ابعت رقم العضو (01xxxxxxxxx):"),
        "op_accept": ("accept", "wait_member", "✅ قبول دعوة — ابعت رقم العضو (01xxxxxxxxx):"),
        "op_split": ("split", "wait_member", "📊 تقسيم الباقة — ابعت رقم العضو (01xxxxxxxxx):"),
        "op_remove": ("remove", "wait_member", "🚪 إخراج عضو — ابعت رقم العضو (01xxxxxxxxx):"),
        "op_auto_accept": ("auto_accept", "wait_member",
                           "⚡ تلقائي (إرسال ← قبول) — ابعت رقم العضو (01xxxxxxxxx):"),
        "op_auto_split": ("auto_split", "wait_member",
                          "🔄 تلقائي (تقسيم ← إلغاء) — ابعت رقم العضو (01xxxxxxxxx):"),
        "op_owner": ("owner", "wait_member",
                     "👑 تغيير المالك — ابعت الرقم الجديد (01xxxxxxxxx):"),
    }
    if data in ops_map:
        if s.get("app") is None:
            edit("🔐 الجلسة انتهت — سجّل دخول تاني.", _red_entry_kb())
            return
        if not _subscribed(uid):
            edit("🔒 الاشتراك مطلوب.", _subscribe_kb())
            return
        op, step, prompt = ops_map[data]
        s.update(op=op, step=step, member=None, member_pw=None)
        _safe_send(chat_id, prompt)
        return

    if data == "quota_custom":
        s["step"] = "wait_custom_quota"
        _safe_send(chat_id, "✏️ ابعت الكميات بالشكل:\n`ميجا, دقائق, رسائل`\nمثال: 30000,3000,200",
                   parse_mode="Markdown")
        return

    if data.startswith("quota:") and len(data.split(":")) == 4:
        _, mi, voice, sms = data.split(":")
        s["step"] = None
        _run_split(chat_id, uid, mi, voice, sms)
        return

    # زر غير معروف → تجاهل (تم الرد بالفعل)
    return


# =====================================================================
# 5) لوحة تحكم الأدمن — تُستدعى من معالجات البوت فقط (غير مسجّلة كـ handlers)
# =====================================================================

def admin_start(message):
    """فتح لوحة التحكم للأدمن"""
    uid = message.from_user.id
    st = bot_status.get("since") or "—"
    text = (
        f"🛠️ لوحة تحكم {BOT_NAME}\n"
        "────────────────\n"
        f"البوت شغال من: {st}\n"
        f"الأدمن: {len(ADMINS)} — {', '.join(str(a) for a in sorted(ADMINS))}\n"
        "اختار من الأزرار تحت 👇"
    )
    _safe_send(message.chat.id, text, reply_markup=_admin_kb())


def admin_handle_callbacks(call):
    """أزرار لوحة التحكم (admin_* + قرارات الاشتراك)"""
    try:
        data = call.data or ""
        chat_id = call.message.chat.id if call.message else call.from_user.id
        msg_id = call.message.message_id if call.message else None
        uid = call.from_user.id
        try:
            bot.answer_callback_query(call.id, "✓")
        except Exception:
            pass

        def edit(text, markup=None):
            try:
                bot.edit_message_text(sanitize_text(text), chat_id, msg_id, reply_markup=markup)
            except Exception:
                _safe_send(chat_id, text, reply_markup=markup)

        if data in ("admin_panel", "admin_refresh", "admin_back"):
            bot_status["admin_action"] = None
            st = bot_status.get("since") or "—"
            edit(f"🛠️ لوحة تحكم {BOT_NAME}\n────────────────\nالبوت شغال من: {st}",
                 _admin_kb())
            return

        if data == "admin_stats":
            c = _counts()
            st = bot_status.get("since") or "—"
            edit(
                "📊 إحصائيات\n"
                "────────────────\n"
                f"👥 المستخدمون: {c['total']}\n"
                f"✅ مشتركون: {c['subscribed']}\n"
                f"⏳ بانتظار الدفع: {c['pending']}\n"
                f"🛠️ الأدمن: {len(ADMINS)}\n"
                f"🕒 يعمل منذ: {st}\n"
                f"🔐 التشفير: {VAULT_KEY_SOURCE}",
                _admin_kb(),
            )
            return

        if data == "admin_broadcast":
            bot_status["admin_action"] = "waiting_broadcast"
            _safe_send(chat_id, "📢 ابعت نص البث الآن — هيُرسل لكل المستخدمين.\n"
                                "(/cancel يلغي من داخل مسار المستخدم — أو اضغط تحديث اللوحة)")
            return

        if data == "admin_audit":
            lines = []
            try:
                with open(os.getenv("AUDIT_LOG_FILE", "audit.log"), encoding="utf-8") as f:
                    lines = f.readlines()[-15:]
            except OSError:
                pass
            body = "".join(lines).strip() or "(السجل فاضي لسه)"
            edit(f"📋 آخر أحداث التدقيق:\n\n{body}", _admin_kb())
            return

        if data == "admin_users":
            try:
                conn = _db()
                rows = []
                if conn is not None:
                    rows = conn.execute(
                        "SELECT user_id, username, first_name, subscribed, pending_payment "
                        "FROM users ORDER BY last_seen DESC LIMIT 20"
                    ).fetchall()
                    conn.close()
            except Exception:
                rows = []
            if not rows:
                edit("👥 مفيش مستخدمين لسه.", _admin_kb())
                return
            out = ["👥 آخر المستخدمين:\n"]
            for r in rows:
                mark = "✅" if r["subscribed"] else ("⏳" if r["pending_payment"] else "—")
                out.append(f"{mark} {r['first_name']} (@{r['username'] or '—'}) — {r['user_id']}")
            edit("\n".join(out), _admin_kb())
            return

        if data == "admin_settings":
            price = _setting("price", str(SUBSCRIPTION_PRICE))
            cash = _setting("cash", VODAFONE_CASH_NUMBER or "—")
            edit(
                "⚙️ الإعدادات\n"
                "────────────────\n"
                f"💵 سعر الاشتراك: {price} جنيه\n"
                f"📱 فودافون كاش: {cash}\n"
                f"🔁 الاشتراك المدفوع: {'مفعّل' if SUBSCRIPTION_ENABLED else 'متوقف'}\n"
                f"🔐 مفتاح التشفير: {VAULT_KEY_SOURCE}",
                _admin_settings_kb(),
            )
            return

        if data == "admin_set_price":
            bot_status["admin_action"] = "waiting_price"
            _safe_send(chat_id, "💵 ابعت سعر الاشتراك الجديد (رقم بالجنيه):")
            return

        if data == "admin_set_cash":
            bot_status["admin_action"] = "waiting_cash"
            _safe_send(chat_id, "📱 ابعت رقم فودافون كاش الجديد:")
            return

        if data.startswith("sub_ok:") or data.startswith("sub_no:"):
            approve = data.startswith("sub_ok:")
            try:
                target = int(data.split(":", 1)[1])
            except (IndexError, ValueError):
                return
            if approve:
                _set_user_fields(target, subscribed=1, pending_payment=0)
                audit.log("sub_approved", uid, f"target={target}")
                _safe_send(target, "✅ تم تفعيل اشتراكك — افتح /start واستمتع بالخدمات.")
                edit(f"✅ تم قبول اشتراك {target}.", _admin_kb())
            else:
                _set_user_fields(target, subscribed=0, pending_payment=0)
                audit.log("sub_rejected", uid, f"target={target}")
                _safe_send(target, "❌ تم رفض طلب الاشتراك — تواصل مع المطور للتفاصيل.")
                edit(f"❌ تم رفض اشتراك {target}.", _admin_kb())
            return

        # زر أدمن غير معروف
    except Exception:
        pass


def admin_handle_text(message):
    """رسائل الأدمن أثناء وجود إجراء منتظر (بث / سعر / كاش)"""
    action = bot_status.get("admin_action")
    uid = message.from_user.id
    chat_id = message.chat.id
    text = (message.text or "").strip()
    bot_status["admin_action"] = None

    if action == "waiting_broadcast":
        targets = _all_user_ids()
        sent = failed = 0
        for t in targets:
            try:
                bot.send_message(t, sanitize_text(text))
                sent += 1
            except Exception:
                failed += 1
        audit.log("broadcast", uid, f"sent={sent} failed={failed}")
        _safe_send(chat_id, f"📢 تم الإرسال إلى {sent} مستخدم"
                            + (f" (فشل {failed})" if failed else "") + ".",
                   reply_markup=_admin_kb())
        return

    if action == "waiting_price":
        if not text.isdigit() or int(text) <= 0:
            _safe_send(chat_id, "❌ ابعت رقم موجب صحيح.", reply_markup=_admin_kb())
            return
        _set_setting("price", text)
        audit.log("setting_price", uid, text)
        _safe_send(chat_id, f"✅ سعر الاشتراك بقى {text} جنيه.", reply_markup=_admin_kb())
        return

    if action == "waiting_cash":
        cleaned = text.replace(" ", "").replace("-", "")
        if not is_egyptian_mobile(cleaned):
            _safe_send(chat_id, "❌ ابعت رقم مصري صحيح (01xxxxxxxxx).",
                       reply_markup=_admin_kb())
            return
        _set_setting("cash", cleaned)
        audit.log("setting_cash", uid, cleaned)
        _safe_send(chat_id, f"✅ فودافون كاش: {cleaned}", reply_markup=_admin_kb())
        return

    # مفيش إجراء فعلي — ردّ ودي
    _safe_send(chat_id, "👌 مفيش إجراء منتظر — اللوحة تحت:",
               reply_markup=_admin_kb())


# =====================================================================
# 6) تسجيل المعالجات على البوت (مرة واحدة — الأدمن يُستدعى بالتوجيه فقط)
# =====================================================================

bot.message_handler(commands=["start"])(start_command)
bot.message_handler(content_types=["text"])(handle_text_messages)
bot.callback_query_handler(func=lambda call: True)(handle_callbacks)


def _set_commands_once():
    try:
        bot.set_my_commands([
            types.BotCommand("start", "القائمة الرئيسية / لوحة التحكم"),
            types.BotCommand("help", "المساعدة"),
            types.BotCommand("menu", "القائمة الرئيسية"),
            types.BotCommand("cancel", "إلغاء الخطوة الحالية"),
        ])
    except Exception as e:
        # توكن غير صالح أو النت مقطوع — البوت يفضل يشتغل ويعيد المحاولة عند البولنغ
        print(f"⚠️ تعذّر تعيين أوامر البوت: {e}")


_set_commands_once()


# =====================================================================
# 7) التشغيل — start() / get_status() / main()
# =====================================================================

def _polling_loop():
    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=30, restart_on_change=False)
    except Exception as e:
        bot_status["last_error"] = str(e)
        print(f"⚠️ توقف البولنغ: {e}")


def start() -> bool:
    """
    تشغيل بوت التليجرام في خيط خلفي (مرة واحدة فقط — حماية من الريرون).
    يرجع True لو اشتغل دلوقتي، وFalse لو كان شغال بالفعل.
    """
    with STATE_LOCK:
        if bot_status.get("started"):
            return False
        bot_status["started"] = True
        bot_status["is_running"] = True
        bot_status["since"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        thread = threading.Thread(target=_polling_loop, name="vf-telegram-polling", daemon=True)
        bot_status["thread"] = thread
        thread.start()
        return True


def get_status() -> dict:
    """حالة البوت — 3 حقول بالظبط (running / since / admins)"""
    return {
        "running": bool(bot_status.get("started")),
        "since": bot_status.get("since"),
        "admins": len(ADMINS),
    }


def main():
    """نقطة دخول الكونسول: python Vodafone_fixed.py"""
    print("=" * 60)
    print(BOT_NAME.center(60))
    print("بوت تليجرام — مجموعة Vodafone Red + لوحة التحكم".center(60))
    print("=" * 60)
    print(f"\nالأدمن: {', '.join(str(a) for a in sorted(ADMINS)) or '—'}")
    print(f"مفتاح التشفير: {VAULT_KEY_SOURCE}")
    if start():
        print("\n[✅] البوت شغال — افتح تليجرام وابعت /start")
    else:
        print("\n[→] البوت كان شغال بالفعل")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[✅] مع السلامة!")


if __name__ == "__main__":
    main()
