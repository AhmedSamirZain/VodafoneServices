# -*- coding: utf-8 -*-
"""
tests/test_two_secrets.py — اختبارات فعلية لتعديل "سِرّين بس"
==============================================================
بتتحقق إن:
  1) config.py بيقرا BOT_TOKEN و ADMIN_IDS بس، وبيشتق VAULT_KEY من التوكن.
  2) validate_config() بيوقف البوت (SystemExit) لو أي واحد من الاتنين ناقص.
  3) Vodafone_fixed.py بقى بوت واحد (bot is user_bot is admin_bot).
  4) لوحة التحكم بتوصل للأدمن عن طريق التحويل من معالجات البوت
     (start_command / handle_callbacks / handle_text_messages).
  5) start() بتشغّل خيط استماع واحد بس (مش اتنين على نفس التوكن).

التشغيل:  python -m unittest discover -s tests -v
"""

import base64
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

BOT_TOKEN = "123456789:AAExampleTokenForTestsOnly"
ADMIN_A, ADMIN_B, USER_ID = 111111111, 222222222, 333333333


def _clean_env(**extra):
    """بيئة نظيفة من أي توكنات قديمة + المتغيرات المطلوبة"""
    env = {k: v for k, v in os.environ.items()
           if k not in {"BOT_TOKEN", "USER_BOT_TOKEN", "ADMIN_BOT_TOKEN",
                        "TELEGRAM_BOT_TOKEN", "ADMIN_IDS", "DEV_ID", "VAULT_KEY"}}
    env.update({k: str(v) for k, v in extra.items()})
    return env


# ------------------------------------------------------------------
# اختبارات config.py — كل سيناريو في عملية مستقلة (لأن config بيتحمّل مرة واحدة)
# ------------------------------------------------------------------
_PROBE = r"""
import sys; sys.path.insert(0, {root!r})
import config
print("BOT_TOKEN=", config.BOT_TOKEN)
print("ADMIN_IDS=", config.ADMIN_IDS)
print("ADMINS=", sorted(config.ADMINS))
print("DEV_ID=", config.DEV_ID)
print("ASSISTANT_ADMIN_ID=", config.ASSISTANT_ADMIN_ID)
print("VAULT_KEY=", config.VAULT_KEY)
print("VAULT_KEY_SOURCE=", config.VAULT_KEY_SOURCE)
config.validate_config()
print("VALIDATE=OK")
"""


def _run_config_probe(**env):
    code = _PROBE.format(root=REPO_ROOT)
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True,
                          cwd=REPO_ROOT, env=_clean_env(**env))
    return proc


class TestConfigTwoSecrets(unittest.TestCase):

    def test_reads_only_the_two_secrets(self):
        p = _run_config_probe(BOT_TOKEN=BOT_TOKEN,
                              ADMIN_IDS=f"{ADMIN_A}, {ADMIN_B}",
                              DB_FILE=os.devnull)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = p.stdout
        self.assertIn(f"BOT_TOKEN= {BOT_TOKEN}", out)
        self.assertIn(f"ADMIN_IDS= [{ADMIN_A}, {ADMIN_B}]", out)
        self.assertIn(f"DEV_ID= {ADMIN_A}", out)          # أول رقم = المطور
        self.assertIn(f"ASSISTANT_ADMIN_ID= {ADMIN_B}", out)
        self.assertIn("VALIDATE=OK", out)                 # مفيش إعداد تاني مطلوب

    def test_admin_ids_parsing_variants(self):
        p = _run_config_probe(BOT_TOKEN=BOT_TOKEN,
                              ADMIN_IDS=f"{ADMIN_A};{ADMIN_B} 444\n555, 0")
        self.assertEqual(p.returncode, 0, p.stderr)
        # الصفر بيتجاهل (كان قيمة DEV_ID الافتراضية القديمة)
        self.assertIn(f"ADMIN_IDS= [{ADMIN_A}, {ADMIN_B}, 444, 555]", p.stdout)

    def test_vault_key_derived_from_token_and_valid(self):
        p = _run_config_probe(BOT_TOKEN=BOT_TOKEN, ADMIN_IDS=ADMIN_A)
        self.assertEqual(p.returncode, 0, p.stderr)
        key = [l.split("= ", 1)[1] for l in p.stdout.splitlines() if l.startswith("VAULT_KEY= ")][0]
        self.assertIn("VAULT_KEY_SOURCE= مشتق تلقائياً من BOT_TOKEN", p.stdout)
        # مفتاح Fernet صالح فعلاً؟ (32 بايت base64url) + تشفير/فك حقيقي
        from cryptography.fernet import Fernet
        raw = base64.urlsafe_b64decode(key.encode("ascii"))
        self.assertEqual(len(raw), 32)
        token = Fernet(key.encode()).encrypt(b"secret-password")
        self.assertEqual(Fernet(key.encode()).decrypt(token), b"secret-password")

    def test_derived_key_is_stable_across_runs(self):
        p1 = _run_config_probe(BOT_TOKEN=BOT_TOKEN, ADMIN_IDS=ADMIN_A)
        p2 = _run_config_probe(BOT_TOKEN=BOT_TOKEN, ADMIN_IDS=ADMIN_A)
        k1 = [l for l in p1.stdout.splitlines() if l.startswith("VAULT_KEY= ")][0]
        k2 = [l for l in p2.stdout.splitlines() if l.startswith("VAULT_KEY= ")][0]
        self.assertEqual(k1, k2)  # ثابت → كلمات المرور المحفوظة تفضل تفك بعد الريستارت

    def test_explicit_vault_key_wins(self):
        from cryptography.fernet import Fernet
        explicit = Fernet.generate_key().decode()
        p = _run_config_probe(BOT_TOKEN=BOT_TOKEN, ADMIN_IDS=ADMIN_A, VAULT_KEY=explicit)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"VAULT_KEY= {explicit}", p.stdout)
        self.assertIn("VAULT_KEY_SOURCE= VAULT_KEY من الـ Secrets/.env", p.stdout)

    def test_legacy_token_name_still_works(self):
        p = _run_config_probe(USER_BOT_TOKEN=BOT_TOKEN, ADMIN_IDS=ADMIN_A)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"BOT_TOKEN= {BOT_TOKEN}", p.stdout)

    def test_fail_fast_when_token_missing(self):
        p = _run_config_probe(ADMIN_IDS=ADMIN_A)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("BOT_TOKEN", p.stderr)

    def test_fail_fast_when_admin_ids_missing(self):
        p = _run_config_probe(BOT_TOKEN=BOT_TOKEN)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("ADMIN_IDS", p.stderr)
        self.assertNotIn("VAULT_KEY ناقص", p.stderr)  # المفتاح المشتق مش مطلوب كسِرّ


# ------------------------------------------------------------------
# اختبارات الملف الرئيسي Vodafone_fixed.py (بوت واحد + التحويل للأدمن)
# ------------------------------------------------------------------
_TMP_DB = os.path.join(tempfile.gettempdir(), "vf_test_bot.db")
os.environ.update(_clean_env(BOT_TOKEN=BOT_TOKEN,
                             ADMIN_IDS=f"{ADMIN_A}, {ADMIN_B}",
                             DB_FILE=_TMP_DB,
                             VAULT_KEY=""))

# منع أي نداء شبكة حقيقي لتليجرام قبل استيراد الملف الرئيسي
import telebot  # noqa: E402
CALLS = {"set_my_commands": 0, "polling": 0}
telebot.TeleBot.set_my_commands = lambda self, *a, **k: CALLS.__setitem__("set_my_commands", CALLS["set_my_commands"] + 1)
telebot.TeleBot.infinity_polling = lambda self, *a, **k: (CALLS.__setitem__("polling", CALLS["polling"] + 1), time.sleep(0.3))[0]

import Vodafone_fixed as core  # noqa: E402


def _msg(user_id, text="/start"):
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(id=user_id, username="tester", first_name="Tester"),
        chat=SimpleNamespace(id=user_id),
        message_id=1,
        content_type="text",
    )


def _call(user_id, data):
    return SimpleNamespace(
        id="cb1", data=data,
        from_user=SimpleNamespace(id=user_id, username="tester", first_name="Tester"),
        message=SimpleNamespace(chat=SimpleNamespace(id=user_id), message_id=1),
    )


class TestSingleBot(unittest.TestCase):

    def test_one_bot_object_for_both_roles(self):
        self.assertTrue(core.bot is core.user_bot is core.admin_bot)
        self.assertEqual(CALLS["set_my_commands"], 1)  # أوامر البوت بتتعيّن مرة واحدة

    def test_admins_loaded_from_admin_ids(self):
        self.assertEqual(core.ADMINS, {ADMIN_A, ADMIN_B})
        self.assertEqual(core.DEV_ID, ADMIN_A)

    def test_admin_functions_are_not_registered_twice(self):
        """لو اتسجلت كـ handlers كمان كانت هتتعارض مع معالجات البوت الرئيسية"""
        registered = [h["function"] for h in core.bot.message_handlers]
        self.assertNotIn(core.admin_start, registered)
        self.assertNotIn(core.admin_handle_text, registered)
        self.assertIn(core.start_command, registered)
        self.assertIn(core.handle_text_messages, registered)

    def test_start_spawns_a_single_polling_thread(self):
        before = CALLS["polling"]
        self.assertTrue(core.start())      # أول مرة → بتشغّل
        self.assertFalse(core.start())     # تاني مرة → بتتسكت (حماية الريرون)
        time.sleep(0.1)
        self.assertEqual(CALLS["polling"], before + 1)
        self.assertEqual(len(core.get_status()), 3)
        self.assertTrue(core.get_status()["running"])


class TestAdminDispatch(unittest.TestCase):
    """التحويل الصريح من معالجات البوت → دوال لوحة التحكم"""

    def test_start_command_opens_admin_panel_for_admin(self):
        seen = []
        orig = core.admin_start
        core.admin_start = lambda m: seen.append(m.from_user.id)
        try:
            core.start_command(_msg(ADMIN_B))
        finally:
            core.admin_start = orig
        self.assertEqual(seen, [ADMIN_B])

    def test_start_command_keeps_normal_flow_for_regular_user(self):
        seen = []
        replies = []
        orig_admin, orig_bot_status = core.admin_start, dict(core.bot_status)
        core.admin_start = lambda m: seen.append(m.from_user.id)
        core.bot_status["is_running"] = False  # يوقف المعالج بدري قبل أي نداء شبكة
        core.bot.reply_to = lambda *a, **k: replies.append(a[1])
        try:
            core.start_command(_msg(USER_ID))
        finally:
            core.admin_start = orig_admin
            core.bot_status.update(orig_bot_status)
        self.assertEqual(seen, [])            # المستخدم العادي مايشوفش لوحة التحكم
        self.assertTrue(replies)              # وخد رد البوت العادي

    def test_admin_callback_is_routed(self):
        seen = []
        orig = core.admin_handle_callbacks
        core.admin_handle_callbacks = lambda c: seen.append(c.data)
        try:
            core.handle_callbacks(_call(ADMIN_A, "admin_stats"))
        finally:
            core.admin_handle_callbacks = orig
        self.assertEqual(seen, ["admin_stats"])

    def test_user_callback_is_not_routed_to_admin(self):
        seen, answered = [], []
        orig_admin = core.admin_handle_callbacks
        core.admin_handle_callbacks = lambda c: seen.append(c.data)
        core.bot.answer_callback_query = lambda *a, **k: answered.append(a[1:] or a)
        core.bot.send_message = lambda *a, **k: None
        core.bot.edit_message_text = lambda *a, **k: None
        core.bot_status["is_running"] = False  # يوقف المعالج بدري قبل باقي الفروع
        try:
            core.handle_callbacks(_call(USER_ID, "my_services"))
        finally:
            core.admin_handle_callbacks = orig_admin
            core.bot_status["is_running"] = True
        self.assertEqual(seen, [])            # زرار المستخدم مايتحوّلش للوحة التحكم
        self.assertTrue(answered)             # والمعالج العادي هو اللي رد

    def test_admin_text_is_routed_while_admin_action_pending(self):
        seen = []
        orig = core.admin_handle_text
        core.admin_handle_text = lambda m: seen.append(m.text)
        core.bot_status["admin_action"] = "waiting_broadcast"
        try:
            core.handle_text_messages(_msg(ADMIN_A, "رسالة البث"))
        finally:
            core.admin_handle_text = orig
            core.bot_status["admin_action"] = None
        self.assertEqual(seen, ["رسالة البث"])

    def test_admin_text_without_pending_action_stays_in_user_flow(self):
        seen, sent = [], []
        orig = core.admin_handle_text
        core.admin_handle_text = lambda m: seen.append(m.text)
        core.bot.send_message = lambda *a, **k: sent.append(a[1] if len(a) > 1 else a[0])
        core.bot_status["admin_action"] = None
        try:
            core.handle_text_messages(_msg(ADMIN_A, "📞 تواصل مع المطور"))
        finally:
            core.admin_handle_text = orig
        self.assertEqual(seen, [])   # مفيش إجراء لوحة تحكم → المعالجة العادية


class TestStreamlitPage(unittest.TestCase):
    """صفحة ستريمليت لازم تعرض حالة السِرّين من غير AttributeError"""

    def test_page_runs_and_shows_the_two_secrets(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            self.skipTest("streamlit غير مثبتة")
        at = AppTest.from_file(os.path.join(REPO_ROOT, "streamlit_app.py"),
                               default_timeout=30).run()
        self.assertFalse(at.exception, f"الصفحة رمت استثناء: {at.exception}")
        captions = "\n".join(c.value for c in at.caption)
        self.assertIn("BOT_TOKEN", captions)
        self.assertIn("✅ موجود", captions)
        self.assertIn("ADMIN_IDS", captions)
        self.assertIn("2 أدمن", captions)          # ADMIN_A + ADMIN_B من env الاختبار
        self.assertIn("مشتق تلقائياً من BOT_TOKEN", captions)
        self.assertTrue(at.success)                # البوت بدأ فعلاً من الصفحة


if __name__ == "__main__":
    unittest.main(verbosity=2)
