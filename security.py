# -*- coding: utf-8 -*-
"""
security.py — أدوات الأمان المضافة للبوت
=================================================
يحتوي على 5 مكونات:

1. PasswordVault   : خزنة كلمات مرور مشفرة (Fernet = AES-128-CBC + HMAC-SHA256)
                     — كلمات المرور لم تعد محفوظة plaintext في الذاكرة.
2. RateLimiter     : مقيّد معدل المحاولات (نافذة منزلقة) — حماية تسجيل الدخول
                     من هجمات التخمين المتكررة.
3. STATE_LOCK      : قفل عام (RLock) لحماية الحالة المشتركة (الجلسات والتوكنات)
                     من تعارض خيوط متعددة.
4. AuditLogger     : سجل عمليات حساسة (تسجيل دخول، موافقة اشتراك، حظر، بث...)
                     بنية JSONL في ملف audit.log — لتتبع أي حدث لاحقاً.
5. أدوات تحقق      : is_egyptian_mobile / sanitize_text
"""

import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict

# ------------------------------------------------------------------
# 1) خزنة كلمات المرور المشفرة
# ------------------------------------------------------------------
try:
    from cryptography.fernet import Fernet
    _HAS_FERNET = True
except ImportError:  # يُكتشف عند الإنشاء
    _HAS_FERNET = False


class PasswordVault:
    """
    تخزين آمن لكلمات المرور:
    - التشفير: Fernet (مفتاح متماثل 128-bit + توقيع HMAC)
    - المفتاح: من متغير البيئة VAULT_KEY (لا يُكتب في الكود أبداً)
    - كل كلمة تُشفر بقيمة عشوائية (IV) مختلفة → نفس الكلمة تنتج نصاً مشفراً مختلفاً
    """

    def __init__(self, key: bytes = None):
        if not _HAS_FERNET:
            raise RuntimeError(
                "مكتبة cryptography غير مثبتة — شغّل: pip install cryptography"
            )
        if key is None:
            key = os.getenv("VAULT_KEY", "").encode("utf-8")
        if not key:
            raise RuntimeError(
                "VAULT_KEY ناقصة في .env — ولّد مفتاحاً بـ: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._f = Fernet(key)

    def seal(self, plaintext: str) -> str:
        """تشفير كلمة مرور → سلاسلة base64 آمنة للحفظ"""
        return self._f.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def open(self, token: str) -> str:
        """فك التشفير — يرمي استثناءً لو النص مُعدّل (HMAC يكتشف أي عبث)"""
        return self._f.decrypt(token.encode("ascii")).decode("utf-8")


# ------------------------------------------------------------------
# 2) مقيّد المعدل (Sliding Window Rate Limiter)
# ------------------------------------------------------------------
class RateLimiter:
    """
    يسمح بحد أقصى max_hits لكل مفتاح (مثل user_id) خلال window_seconds.
    مثالي لحماية تسجيل الدخول: 5 محاولات كل 15 دقيقة.
    """

    def __init__(self, max_hits: int, window_seconds: float):
        self.max_hits = max_hits
        self.window = window_seconds
        self._hits: Dict[Any, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: Any) -> bool:
        """هل المسموح بمحاولة جديدة؟ (يسجل المحاولة عند السماح)"""
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_hits:
                return False
            q.append(now)
            return True

    def retry_after(self, key: Any) -> float:
        """ثواني متبقية حتى يتجدد المسموح به (0 = مسموح الآن)"""
        now = time.time()
        with self._lock:
            q = self._hits[key]
            if len(q) < self.max_hits:
                return 0.0
            return max(0.0, self.window - (now - q[0]))

    def reset(self, key: Any) -> None:
        """مسح عداد مفتاح (مثلاً بعد نجاح تسجيل الدخول)"""
        with self._lock:
            self._hits.pop(key, None)


# ------------------------------------------------------------------
# 3) قفل الحالة المشتركة
# ------------------------------------------------------------------
# البوت يعمل بخيوط متعددة (بوت المستخدمين + بوت الإدارة + خيط تجديد التوكنات).
# كل الدوال اللي تقرأ/تكتب في القوام المشتركة (user_sessions, phone_tokens)
# لازم تعمل جوا: with STATE_LOCK:  — وهو RLock عشان الدوال المتداخلة لا تميت بعضها.
STATE_LOCK = threading.RLock()


# ------------------------------------------------------------------
# 4) سجل العمليات الحساسة (Audit Log)
# ------------------------------------------------------------------
class AuditLogger:
    """
    كتابة حدث واحد لكل سطر (JSON Lines) في ملف مستقل audit.log:
    {"ts": "...", "action": "login_success", "user_id": 123, "details": "010..."}
    مخصص للتحقيق: مين سجل دخول، مين حُظر، مين وافق على اشتراك، عمليات التحويل...
    """

    def __init__(self, path: str = "audit.log"):
        self.path = path
        self._lock = threading.Lock()

    def log(self, action: str, user_id: Any, details: str = "") -> None:
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "user_id": user_id,
            "details": details,
        }
        try:
            with self._lock:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            # فشل كتابة السجل لا يجب أن يكسر خدمة المستخدم
            pass


audit = AuditLogger(os.getenv("AUDIT_LOG_FILE", "audit.log"))


# ------------------------------------------------------------------
# 5) أدوات التحقق والتنظيف
# ------------------------------------------------------------------
def is_egyptian_mobile(phone: str) -> bool:
    """رقم جوال مصري صحيح: 01 + 9 أرقام (11 رقماً)"""
    return bool(re.fullmatch(r"01[0-9]{9}", (phone or "").strip()))


def sanitize_text(text: str, max_len: int = 4000) -> str:
    """قص أي إدخال على طول آمن (حد تليجرام للرسالة 4096 حرف)"""
    return (text or "")[:max_len]
