# -*- coding: utf-8 -*-
"""
streamlit_app.py — نقطة دخول ستريمليت (اللي بيتفتح على Streamlit Cloud)
الكود الأساسي كله في Vodafone_fixed.py — الملف ده بيشغّله وبس ويعرض الحالة.
"""

import traceback

import streamlit as st

st.set_page_config(page_title="Vodafone Bot", page_icon="🤖", layout="centered")
st.title("🤖 بوت فودافون — BRSHAMH FLEX")

try:
    # استيراد الكود الأساسي (أول سطر فيه بيفحص إعدادات .env / Secrets)
    import Vodafone_fixed as core

    # شغّل البوتين في خيوط خلفية — آمنة ضد التكرار مع كل rerun
    core.start()
    status = core.get_status()

    if status["running"]:
        st.success("✅ البوتين شغالين دلوقتي (بوت المستخدمين + بوت التحكم)")
        if status.get("since"):
            st.caption(f"شغال من: `{status['since']}`")
    else:
        st.warning("البوت لم يبدأ بعد")

    st.info("📱 افتح تليجرام وابعت /start لبوت المستخدمين عشان تستخدمه.")

    st.divider()
    st.markdown("**🔐 حالة الإعدادات (من Secrets / .env)**")
    st.caption(
        f"- توكن بوت المستخدمين: {'✅ موجود' if core.USER_BOT_TOKEN else '❌ ناقص'}\n"
        f"- توكن بوت التحكم: {'✅ موجود' if core.ADMIN_BOT_TOKEN else '❌ ناقص'}\n"
        f"- مفتاح التشفير VAULT_KEY: {'✅ موجود' if core.VAULT_KEY else '❌ ناقص'}\n"
        f"- DEV_ID: {core.DEV_ID}"
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
        "المتغيرات دي موجودة بنفس الأسماء بالظبط:\n\n"
        "`USER_BOT_TOKEN` و `ADMIN_BOT_TOKEN` و `VAULT_KEY` و `DEV_ID`\n\n"
        "وبعدين اعمل **Restart** للتطبيق."
    )

except Exception as e:
    st.error(f"❌ خطأ أثناء التشغيل: {e}")
    st.code(traceback.format_exc())
    st.warning("تأكد إن ملف Vodafone_fixed.py موجود جنب streamlit_app.py في الريبو.")
