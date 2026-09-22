# رفع وتشغيل البوت على GitHub + Streamlit Cloud

الريبو جاهز للتشغيل على Streamlit Cloud. الملف الرئيسي هو:

```text
streamlit_app.py
```

## 1) قبل الرفع على GitHub

تأكد إنك **لا ترفع أي أسرار**:

- لا ترفع ملف `.env`
- لا ترفع `.streamlit/secrets.toml`
- لا ترفع ملفات قاعدة البيانات أو اللوجات مثل `*.db` و `*.log`

الملف `.gitignore` مجهز بالفعل لمنع رفع الملفات دي.

## 2) ملفات مهمة لازم تكون موجودة في GitHub

ارفع الملفات دي كلها:

```text
Vodafone_fixed.py
streamlit_app.py
config.py
security.py
requirements.txt
README.md
.env.example
.streamlit/config.toml
```

## 3) إعداد Streamlit Cloud

1. افتح: https://share.streamlit.io/
2. اختار **New app**
3. اختار الريبو من GitHub
4. في خانة **Main file path** اكتب:

```text
streamlit_app.py
```

5. قبل التشغيل افتح **Advanced settings / Secrets** وحط السطرين دول فقط:

```toml
BOT_TOKEN = "توكن_البوت_من_BotFather"
ADMIN_IDS = "ايدي_تليجرام_بتاعك"
```

لو عندك أكتر من أدمن:

```toml
BOT_TOKEN = "توكن_البوت_من_BotFather"
ADMIN_IDS = "111111111, 222222222"
```

## 4) بعد التشغيل

- افتح صفحة تطبيق Streamlit، لازم تلاقي رسالة إن البوت شغال.
- افتح تليجرام وابعت للبوت:

```text
/start
```

لو حسابك موجود في `ADMIN_IDS` هتفتحلك لوحة التحكم. لو مش موجود هتظهر قائمة المستخدم العادية.

## 5) تشغيل محلي للتجربة

```bash
cp .env.example .env
# عدّل BOT_TOKEN و ADMIN_IDS داخل .env
pip install -r requirements.txt
streamlit run streamlit_app.py
```

أو تشغيل البوت مباشرة بدون واجهة Streamlit:

```bash
python Vodafone_fixed.py
```
