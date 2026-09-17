# -*- coding: utf-8 -*-
"""
Streamlit - مجرد مشغل للكود الأساسي
الكود الأساسي كله في vodafone_telegram_bot.py
Streamlit بيدور على الملف ده عشان يشغله
"""

import streamlit as st
import threading
import time

st.set_page_config(page_title="Vodafone Bot - Running", page_icon="🤖", layout="centered")

st.title("🤖 بوت فودافون شغال")
st.caption("الكود الأساسي: `vodafone_telegram_bot.py` | الملف ده مجرد مشغل لـ Streamlit")

# تشغيل البوت في الخلفية
try:
    import vodafone_telegram_bot as core

    # شغل بوت تليجرام في ثريد منفصل عشان Streamlit ميعلقش
    if "bot_started" not in st.session_state:
        st.session_state.bot_started = False

    if not st.session_state.bot_started:
        def run_bot():
            try:
                core.bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
            except Exception as e:
                print(f"Bot error: {e}")

        threading.Thread(target=run_bot, daemon=True).start()
        st.session_state.bot_started = True
        time.sleep(1)

    # واجهة بسيطة
    st.success("✅ البوت شغال على تليجرام دلوقتي")
    st.info(f"🔗 رابط فودافون: `{core.VODAFONE_URL[:70]}...`")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🔁 معلق", core.MAX_RETRIES)
    col2.metric("🔐 باسورد غلط", core.MAX_RETRIES_WRONG_PASSWORD)
    col3.metric("⏰ تلقائي", f"{core.AUTO_CHECK_INTERVAL_MINUTES}د")

    st.divider()
    st.markdown("**📱 افتح تليجرام ودوس /start عشان تستخدم البوت**")
    st.caption("💡 البوت هيفضل شغال طول ما صفحة Streamlit مفتوحة. على Streamlit Cloud هيفضل شغال 24 ساعة")

    # عرض حالة
    st.divider()
    if st.button("🔄 تحديث الحالة"):
        st.rerun()

    with st.expander("📄 الكود الأساسي", expanded=False):
        st.caption("كل المنطق في vodafone_telegram_bot.py (1339 سطر). الملف ده 40 سطر بس.")
        try:
            code = open("vodafone_telegram_bot.py", "r", encoding="utf-8").read()
            st.code(code[:3000] + "\n\n... (1339 سطر)", language="python")
        except:
            st.code("vodafone_telegram_bot.py مش موجود")

except Exception as e:
    st.error(f"❌ خطأ: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.warning("تأكد ان vodafone_telegram_bot.py موجود جنب streamlit_app.py")
