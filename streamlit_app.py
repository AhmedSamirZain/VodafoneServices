# -*- coding: utf-8 -*-
"""
streamlit_app.py — نقطة دخول Streamlit Cloud.

يدعم نوعين من ملف Vodafone_fixed.py:
1) بوت تليجرام حديث يحتوي على start()/run_bot()/bot.infinity_polling.
2) ملف "تطير فودافون ريد" الكونسول الذي يحتوي على class VodafoneRed.
"""

import builtins
import contextlib
import io
import threading
import traceback
from datetime import datetime

import streamlit as st

try:
    from config import BOT_NAME, VAULT_KEY_SOURCE
except Exception:
    BOT_NAME = "VodafoneServices"
    VAULT_KEY_SOURCE = ""


st.set_page_config(page_title=BOT_NAME, page_icon="🤖", layout="centered")
st.title(f"🤖 {BOT_NAME}")


def _capture_output(func, *args, **kwargs):
    """تشغيل دالة وعرض كل print ظهر منها داخل Streamlit."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = func(*args, **kwargs)
        return result, buf.getvalue()
    except Exception:
        return False, buf.getvalue() + "\n" + traceback.format_exc()


def _has_bot_launcher(core):
    return (
        (hasattr(core, "start") and callable(core.start))
        or (hasattr(core, "main") and callable(core.main))
        or (hasattr(core, "run_bot") and callable(core.run_bot))
        or (hasattr(core, "bot") and hasattr(core.bot, "infinity_polling"))
    )


def _start_telegram_bot(core):
    """تشغيل بوت تليجرام في الخلفية، مع دعم النسخ القديمة التي لا تحتوي على start()."""
    if hasattr(core, "start") and callable(core.start):
        core.start()
        if hasattr(core, "get_status") and callable(core.get_status):
            return core.get_status()
        return {"running": True, "since": None, "admins": len(getattr(core, "ADMINS", []) or [])}

    if getattr(core, "_STREAMLIT_COMPAT_STARTED", False):
        return {
            "running": True,
            "since": getattr(core, "_STREAMLIT_COMPAT_SINCE", None),
            "admins": len(getattr(core, "ADMINS", []) or []),
            "mode": "compat",
        }

    if hasattr(core, "main") and callable(core.main):
        target = core.main
    elif hasattr(core, "run_bot") and callable(core.run_bot):
        target = core.run_bot
    elif hasattr(core, "bot") and hasattr(core.bot, "infinity_polling"):
        target = core.bot.infinity_polling
    else:
        raise AttributeError("لا توجد دالة مناسبة لتشغيل بوت تليجرام داخل Vodafone_fixed.py")

    core._STREAMLIT_COMPAT_STARTED = True
    core._STREAMLIT_COMPAT_SINCE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    threading.Thread(target=target, daemon=True).start()
    return {
        "running": True,
        "since": core._STREAMLIT_COMPAT_SINCE,
        "admins": len(getattr(core, "ADMINS", []) or []),
        "mode": "compat",
    }


def _render_telegram_bot_page(core):
    status = _start_telegram_bot(core)

    if status.get("running"):
        st.success("✅ البوت شغال دلوقتي")
        if status.get("since"):
            st.caption(f"شغال من: `{status['since']}`")
        if status.get("mode") == "compat":
            st.caption("وضع التوافق: تم تشغيل الملف رغم عدم وجود دالة start() داخله.")
    else:
        st.warning("البوت لم يبدأ بعد")

    st.info("📱 افتح تليجرام وابعت /start.")
    st.divider()

    bot_token = getattr(core, "BOT_TOKEN", "") or getattr(core, "TOKEN", "") or getattr(core, "token", "")
    admins = getattr(core, "ADMINS", None)
    if admins is None:
        admins = getattr(core, "ADMIN_IDS", [])
    try:
        admin_count = len(admins or [])
        admin_list = ", ".join(str(a) for a in sorted(admins)) if admins else ""
    except Exception:
        admin_count = 1 if admins else 0
        admin_list = str(admins) if admins else ""

    st.markdown("**🔐 حالة الإعدادات**")
    st.caption(
        f"- `BOT_TOKEN`: {'✅ موجود' if bot_token else '⚠️ غير ظاهر باسم BOT_TOKEN داخل الملف'}\n"
        f"- `ADMIN_IDS`: {'✅ ' + str(admin_count) + ' أدمن' if admin_count else '⚠️ غير ظاهر باسم ADMIN_IDS/ADMINS داخل الملف'}"
        f"{(' — ' + admin_list) if admin_list else ''}\n"
        f"- `VAULT_KEY`: {VAULT_KEY_SOURCE or '⚠️ غير متاح'}"
    )


def _quota_options():
    return {
        "15000 ميجا - 2000 دقيقة - 200 رسالة": ("15000", "2000", "200"),
        "25000 ميجا - 2500 دقيقة - 200 رسالة": ("25000", "2500", "200"),
        "28000 ميجا - 3000 دقيقة - 200 رسالة": ("28000", "3000", "200"),
        "30000 ميجا - 3500 دقيقة - 200 رسالة": ("30000", "3500", "200"),
        "35000 ميجا - 4500 دقيقة - 200 رسالة": ("35000", "4500", "200"),
        "40000 ميجا - 6000 دقيقة - 200 رسالة": ("40000", "6000", "200"),
        "45000 ميجا - 6000 دقيقة - 200 رسالة": ("45000", "6000", "200"),
        "50000 ميجا - 7000 دقيقة - 200 رسالة": ("50000", "7000", "200"),
        "55000 ميجا - 7000 دقيقة - 200 رسالة": ("55000", "7000", "200"),
        "60000 ميجا - 8000 دقيقة - 200 رسالة": ("60000", "8000", "200"),
        "65000 ميجا - 8000 دقيقة - 200 رسالة": ("65000", "8000", "200"),
        "75000 ميجا - 9500 دقيقة - 200 رسالة": ("75000", "9500", "200"),
        "87000 ميجا - 9950 دقيقة - 200 رسالة": ("87000", "9950", "200"),
        "110000 ميجا - 10000 دقيقة - 200 رسالة": ("110000", "10000", "200"),
        "200000 ميجا - 10300 دقيقة - 200 رسالة": ("200000", "10300", "200"),
        "250000 ميجا - 20000 دقيقة - 200 رسالة": ("250000", "20000", "200"),
        "مخصص": None,
    }


def _render_vodafone_red_page(core):
    st.subheader("برنامج التحكم في مجموعة Vodafone Red")
    st.warning("استخدم الأداة على رقمك أو برقم عندك إذن صريح من صاحبه فقط. البيانات لا يتم حفظها في ملفات.")

    with st.form("login_form"):
        number = st.text_input("رقم المالك", placeholder="01xxxxxxxxx")
        password = st.text_input("كلمة مرور أنا فودافون", type="password")
        login_clicked = st.form_submit_button("تسجيل الدخول")

    if login_clicked:
        if not number or not password:
            st.error("الرقم وكلمة المرور مطلوبين")
        else:
            app = core.VodafoneRed(number.strip(), password)
            with st.spinner("جاري تسجيل الدخول..."):
                ok, log = _capture_output(app.login)
            st.code(log or "لا يوجد إخراج", language="text")
            if ok:
                st.session_state["vodafone_red_app"] = app
                st.session_state["vodafone_red_number"] = number.strip()
                st.success("✅ تم تسجيل الدخول بنجاح")
            else:
                st.error("❌ فشل تسجيل الدخول")

    app = st.session_state.get("vodafone_red_app")
    if not app:
        st.info("سجل دخول الأول عشان تظهر العمليات.")
        return

    st.divider()
    st.success(f"✅ الجلسة الحالية للمالك: {st.session_state.get('vodafone_red_number', app.number)}")

    operation = st.selectbox(
        "اختار العملية",
        [
            "إرسال دعوة",
            "قبول دعوة",
            "تقسيم الباقة",
            "إخراج/إلغاء عضو",
            "إرسال دعوة ثم قبول تلقائي",
            "تغيير مالك الباقة",
        ],
    )

    member = st.text_input("رقم العضو / الرقم الثاني", placeholder="01xxxxxxxxx")

    member_password = None
    quota_values = None
    new_owner_password = None

    if operation in {"قبول دعوة", "إرسال دعوة ثم قبول تلقائي"}:
        member_password = st.text_input("كلمة مرور الرقم الثاني", type="password")

    if operation == "تقسيم الباقة":
        options = _quota_options()
        selected = st.selectbox("كمية التقسيم", list(options.keys()))
        if selected == "مخصص":
            col1, col2, col3 = st.columns(3)
            with col1:
                mi = st.text_input("الميجابايتس", value="15000")
            with col2:
                voice = st.text_input("الدقائق", value="2000")
            with col3:
                sms = st.text_input("الرسائل", value="200")
            quota_values = (mi, voice, sms)
        else:
            quota_values = options[selected]

    if operation == "تغيير مالك الباقة":
        new_owner_password = st.text_input("كلمة مرور المالك الجديد", type="password")

    if st.button("تنفيذ العملية", type="primary"):
        if not member:
            st.error("اكتب رقم العضو / الرقم الثاني الأول")
            return

        with st.spinner("جاري التنفيذ..."):
            if operation == "إرسال دعوة":
                ok, log = _capture_output(app.send_invitation_auto, member.strip())

            elif operation == "قبول دعوة":
                if not member_password:
                    st.error("كلمة مرور الرقم الثاني مطلوبة")
                    return
                ok, log = _capture_output(app.accept_invitation_with_retry, member.strip(), member_password, 3, 5)

            elif operation == "تقسيم الباقة":
                app.choose_quota = lambda: quota_values
                ok, log = _capture_output(app.redistribute_quota, member.strip())

            elif operation == "إخراج/إلغاء عضو":
                ok, log = _capture_output(app.cancel_invitation, member.strip())

            elif operation == "إرسال دعوة ثم قبول تلقائي":
                if not member_password:
                    st.error("كلمة مرور الرقم الثاني مطلوبة")
                    return
                ok1, log1 = _capture_output(app.send_invitation_auto, member.strip())
                if ok1:
                    ok2, log2 = _capture_output(app.accept_invitation_with_retry, member.strip(), member_password, 3, 5)
                    ok, log = ok2, log1 + "\n" + log2
                else:
                    ok, log = False, log1

            elif operation == "تغيير مالك الباقة":
                if not new_owner_password:
                    st.error("كلمة مرور المالك الجديد مطلوبة")
                    return
                answers = iter([member.strip(), new_owner_password])
                original_input = builtins.input
                builtins.input = lambda *a, **k: next(answers)
                try:
                    ok, log = _capture_output(app.change_owner)
                finally:
                    builtins.input = original_input
                if ok:
                    st.session_state["vodafone_red_number"] = member.strip()

            else:
                ok, log = False, "عملية غير معروفة"

        st.code(log or "لا يوجد إخراج", language="text")
        if ok:
            st.success("✅ تمت العملية بنجاح")
        else:
            st.error("❌ العملية فشلت أو رجعت برد غير ناجح")


try:
    import Vodafone_fixed as core

    if _has_bot_launcher(core):
        _render_telegram_bot_page(core)
    elif hasattr(core, "VodafoneRed"):
        _render_vodafone_red_page(core)
    else:
        raise AttributeError("Vodafone_fixed.py لا يحتوي على بوت تليجرام ولا class VodafoneRed")

except SystemExit as e:
    st.error("❌ التطبيق لم يعمل — في إعدادات ناقصة")
    st.code(str(e))
    st.markdown(
        "لو بتشغل بوت تليجرام، أضف في Streamlit Secrets:\n\n"
        "```toml\n"
        'BOT_TOKEN = "123456789:AA..."\n'
        'ADMIN_IDS = "111111111"\n'
        "```"
    )

except Exception as e:
    st.error(f"❌ خطأ أثناء التشغيل: {e}")
    st.code(traceback.format_exc())
    st.warning("تأكد إن Vodafone_fixed.py موجود جنب streamlit_app.py ومناسب للتشغيل.")
