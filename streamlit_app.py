# -*- coding: utf-8 -*-
"""
streamlit_app.py — نقطة دخول ستريمليت (اللي بيتفتح على Streamlit Cloud)
الكود الأساسي كله في Vodafone_fixed.py — الملف ده بيشغّله وبس ويعرض الحالة.

البوت محتاج سِرّين (Secrets) بس: BOT_TOKEN و ADMIN_IDS
"""

import traceback

import streamlit as st

try:
    from config import BOT_NAME
except Exception:
    BOT_NAME = "VodafoneServices"

st.set_page_config(page_title=BOT_NAME, page_icon="🤖", layout="centered")
st.title(f"🤖 {BOT_NAME} — بوت خدمات فودافون")

try:
    # استيراد الكود الأساسي (أول سطر فيه بيفحص إعدادات .env / Secrets)
    import Vodafone_fixed as core

    # شغّل البوت في خيط خلفية — آمن ضد التكرار مع كل rerun
    core.start()
    status = core.get_status()

    if status["running"]:
        st.success("✅ البوت شغال دلوقتي (المستخدمين + لوحة التحكم على نفس البوت)")
        if status.get("since"):
            st.caption(f"شغال من: `{status['since']}`")
    else:
        st.warning("البوت لم يبدأ بعد")

    st.info("📱 افتح تليجرام وابعت /start — الأدمن هيفتح له لوحة التحكم، وباقي المستخدمين القائمة العادية.")

    st.divider()
    st.markdown("**🔐 حالة الإعدادات (من Secrets / .env)**")
    st.caption(
        f"- `BOT_TOKEN`: {'✅ موجود' if core.BOT_TOKEN else '❌ ناقص'}\n"
        f"- `ADMIN_IDS`: {'✅ ' + str(len(core.ADMINS)) + ' أدمن' if core.ADMINS else '❌ ناقص'}"
        f"{(' — ' + ', '.join(str(a) for a in sorted(core.ADMINS))) if core.ADMINS else ''}\n"
        f"- مفتاح التشفير VAULT_KEY: ✅ {core.VAULT_KEY_SOURCE}\n"
        f"- المطور الأساسي DEV_ID: `{core.DEV_ID}`"
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
        "وبعدين اعمل **Restart** للتطبيق. (مفيش أي إعدادات تانية مطلوبة — "
        "مفتاح التشفير بيتشتق تلقائياً من `BOT_TOKEN`.)"
    )

except Exception as e:
    st.error(f"❌ خطأ أثناء التشغيل: {e}")
    st.code(traceback.format_exc())
    st.warning("تأكد إن ملف Vodafone_fixed.py موجود جنب streamlit_app.py في الريبو.")
