# -*- coding: utf-8 -*-
"""
streamlit_app.py — نقطة دخول ستريمليت (اللي بيتفتح على Streamlit Cloud)
الكود الأساسي كله في Vodafone_fixed.py — الملف ده بيشغّله وبس ويعرض الحالة.

البوت محتاج سِرّين (Secrets) بس: BOT_TOKEN و ADMIN_IDS

ملاحظة مهمة:
الصفحة دي متوافقة مع نسخ مختلفة من Vodafone_fixed.py:
- لو الملف فيه start()/get_status() هتستخدمهم مباشرة.
- لو الملف قديم أو مستبدل ومفيهوش start، هتشغّل main() أو run_bot() في خيط خلفية.
"""

import threading
import traceback
from datetime import datetime

import streamlit as st

try:
    from config import BOT_NAME
except Exception:
    BOT_NAME = "VodafoneServices"


st.set_page_config(page_title=BOT_NAME, page_icon="🤖", layout="centered")
st.title(f"🤖 {BOT_NAME} — بوت خدمات فودافون")


def _start_compatible(core):
    """تشغيل Vodafone_fixed.py حتى لو النسخة المرفوعة لا تحتوي على دالة start()."""
    # النسخة الحديثة: فيها start/get_status ومتأمنة ضد تكرار خيوط ستريمليت.
    if hasattr(core, "start") and callable(core.start):
        core.start()
        if hasattr(core, "get_status") and callable(core.get_status):
            return core.get_status()
        return {"running": True, "since": None, "admins": len(getattr(core, "ADMINS", []) or [])}

    # توافق مع نسخة قديمة/ملف مستبدل: شغل main أو run_bot أو bot.infinity_polling في الخلفية مرة واحدة.
    if getattr(core, "_STREAMLIT_COMPAT_STARTED", False):
        return {
            "running": True,
            "since": getattr(core, "_STREAMLIT_COMPAT_SINCE", None),
            "admins": len(getattr(core, "ADMINS", []) or []),
            "mode": "compat",
        }

    target = None
    if hasattr(core, "main") and callable(core.main):
        target = core.main
    elif hasattr(core, "run_bot") and callable(core.run_bot):
        target = core.run_bot
    elif hasattr(core, "bot") and hasattr(core.bot, "infinity_polling"):
        target = core.bot.infinity_polling

    if target is None:
        raise AttributeError(
            "ملف Vodafone_fixed.py لا يحتوي على start أو main أو run_bot أو bot.infinity_polling"
        )

    core._STREAMLIT_COMPAT_STARTED = True
    core._STREAMLIT_COMPAT_SINCE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    threading.Thread(target=target, daemon=True).start()
    return {
        "running": True,
        "since": core._STREAMLIT_COMPAT_SINCE,
        "admins": len(getattr(core, "ADMINS", []) or []),
        "mode": "compat",
    }


try:
    # استيراد الكود الأساسي (أول سطر فيه بيفحص إعدادات .env / Secrets لو config مستخدم)
    import Vodafone_fixed as core

    status = _start_compatible(core)

    if status.get("running"):
        st.success("✅ البوت شغال دلوقتي")
        if status.get("since"):
            st.caption(f"شغال من: `{status['since']}`")
        if status.get("mode") == "compat":
            st.caption("وضع التوافق: تم تشغيل الملف رغم عدم وجود دالة start() داخله.")
    else:
        st.warning("البوت لم يبدأ بعد")

    st.info("📱 افتح تليجرام وابعت /start — الأدمن هيفتح له لوحة التحكم، وباقي المستخدمين القائمة العادية.")

    st.divider()
    st.markdown("**🔐 حالة الإعدادات (من Secrets / .env)**")

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

    vault_source = getattr(core, "VAULT_KEY_SOURCE", "غير مستخدم في الملف الحالي")
    dev_id = getattr(core, "DEV_ID", "غير محدد")

    st.caption(
        f"- `BOT_TOKEN`: {'✅ موجود' if bot_token else '⚠️ غير ظاهر باسم BOT_TOKEN داخل الملف'}\n"
        f"- `ADMIN_IDS`: {'✅ ' + str(admin_count) + ' أدمن' if admin_count else '⚠️ غير ظاهر باسم ADMIN_IDS/ADMINS داخل الملف'}"
        f"{(' — ' + admin_list) if admin_list else ''}\n"
        f"- مفتاح التشفير VAULT_KEY: {vault_source}\n"
        f"- المطور الأساسي DEV_ID: `{dev_id}`"
    )

    st.divider()
    st.caption(
        "💡 البوت بيفضل شغال طول ما تطبيق ستريمليت ده شغال. "
        "لو عدّلت الـ Secrets أو الكود اعمل Restart للتطبيق من لوحة Streamlit Cloud."
    )

except SystemExit as e:
    # validate_config() بيقفّل البوت لو في إعداد ناقص
    st.error("❌ البوت لم يعمل — في إعدادات ناقصة")
    st.code(str(e))
    st.markdown(
        "**الحل:** على Streamlit Cloud افتح تطبيقك ← تبويب **Secrets** وتأكد إن "
        "السِرّين دول موجودين بنفس الأسماء بالظبط:\n\n"
        "```toml\n"
        'BOT_TOKEN = "123456789:AA..."\n'
        'ADMIN_IDS = "111111111, 222222222"\n'
        "```\n\n"
        "وبعدين اعمل **Restart** للتطبيق."
    )

except Exception as e:
    st.error(f"❌ خطأ أثناء التشغيل: {e}")
    st.code(traceback.format_exc())
    st.warning("تأكد إن ملف Vodafone_fixed.py موجود جنب streamlit_app.py في الريبو، وإنه يحتوي على كود بوت تليجرام صالح.")
