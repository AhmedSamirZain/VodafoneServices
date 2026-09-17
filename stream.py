# -*- coding: utf-8 -*-
"""
stream.py — مشغّل الكونسول:
    - على جهازك:  python stream.py
    - جوا ستريمليت (لو اتفتح كملف رئيسي): بيشغّل البوت ويعرض صفحة حالة بسيطة.

ملاحظة: على Streamlit Cloud الأفضل تختار `streamlit_app.py` هو الملف الرئيسي
(الإعدادات ← Main file path) عشان تظهرلك صفحة الحالة الكاملة.
"""

from Vodafone_fixed import main

main()

# لو اتفتحنا جوا ستريمليت، اعرض صفحة حالة بسيطة بدل الصفحة الفاضية
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx() is not None:
        import streamlit as st
        import Vodafone_fixed as core

        st.set_page_config(page_title="Vodafone Bot", page_icon="🤖")
        st.title("🤖 بوت فودافون")
        status = core.get_status()
        if status["running"]:
            st.success("✅ البوتين شغالين دلوقتي — ابعت /start في تليجرام")
            if status.get("since"):
                st.caption(f"شغال من: `{status['since']}`")
        else:
            st.warning("البوت لم يبدأ بعد")
        st.caption(
            f"- توكن بوت المستخدمين: {'✅' if core.USER_BOT_TOKEN else '❌ ناقص'}\n"
            f"- توكن بوت التحكم: {'✅' if core.ADMIN_BOT_TOKEN else '❌ ناقص'}\n"
            f"- VAULT_KEY: {'✅' if core.VAULT_KEY else '❌ ناقص'} | DEV_ID: {core.DEV_ID}"
        )
except ImportError:
    pass  # ستريمليت مش متسطب — إحنا في كونسول عادي
