# 🐼 Panda Giveaways - Architecture Deployment

## 🎯 نظرة عامة

تم تقسيم المشروع إلى جزئين لتحسين الأداء والتكلفة:

- **Frontend (الموقع)**: Vercel → [https://panda-giveawaays.vercel.app](https://panda-giveawaays.vercel.app)
- **Backend (API + Bot)**: Render → [https://pandagiveawaays.onrender.com](https://pandagiveawaays.onrender.com)

## 🚀 خطوات النشر

### 1. نشر الموقع على Vercel

```bash
# 1. تحضير ملفات الموقع فقط (public folder + config files)
git add .
git commit -m "Separate frontend for Vercel"

# 2. ادخل إلى Vercel Dashboard
# 3. Import Repository
# 4. اختر المجلد الحالي
# 5. سيتم تشغيل النشر تلقائياً باستخدام vercel.json
```

**ملفات المطلوبة للموقع:**
- `public/` (كل ملفات HTML, CSS, JS, Images)
- `vercel.json` (إعدادات النشر)
- `package.json` (البيانات الأساسية)
- `.vercelignore` (لاستبعاد ملفات السيرفر)

### 2. نشر السيرفر والبوت على Render

```bash
# 1. نفس الـ Repository
# 2. الدخول إلى Render Dashboard
# 3. Create Web Service
# 4. ربط نفس الـ Repository
# 5. استخدم إعدادات render.yaml
```

**ملفات المطلوبة للسيرفر:**
- `app.py` (Flask API Server)
- `panda_giveaways_bot.py` (Telegram Bot)
- `requirements.txt` (Python dependencies)
- `render.yaml` (Render configuration)
- `start_render.sh` (Startup script)
- `Procfile` (Alternative startup)

## ⚙️ متغيرات البيئة

### Vercel (موقع فقط)
لا توجد متغيرات مطلوبة - static files فقط.

### Render (سيرفر + بوت)
```env
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=PandaGiveawaysBot
DATABASE_URL=your_database_url
MINI_APP_URL=https://panda-giveawaays.vercel.app
API_BASE_URL=https://pandagiveawaays.onrender.com/api
FRONTEND_URL=https://panda-giveawaays.vercel.app
PAYMENT_PROOF_CHANNEL=@YourChannel
ADMIN_IDS=1797127532,6603009212
```

## 🔗 الربط بين الموقع والسيرفر

### 1. CORS Configuration
تم إعداد CORS في `app.py` للسماح للموقع بالوصول للـ API:
```python
CORS(app, origins=[
    'https://panda-giveawaays.vercel.app',
    'http://localhost:3000',
    'http://127.0.0.1:5000'
])
```

### 2. API Endpoints
جميع استدعاءات الـ API من الموقع تذهب إلى:
```
https://pandagiveawaays.onrender.com/api
```

### 3. Redirects
السيرفر يقوم بإعادة توجيه الزوار للموقع الجديد في Vercel.

## 📁 بنية الملفات

```
Project/
├── public/                   # → Vercel
│   ├── index.html
│   ├── admin.html
│   ├── css/
│   ├── js/
│   └── img/
├── vercel.json              # → Vercel
├── package.json            # → Vercel  
├── .vercelignore           # → Vercel
├── app.py                  # → Render
├── panda_giveaways_bot.py  # → Render
├── requirements.txt        # → Render
├── render.yaml            # → Render
├── start_render.sh        # → Render
└── Procfile               # → Render
```

## ✅ التحقق من النشر

### الموقع (Vercel)
- [ ] يفتح على https://panda-giveawaays.vercel.app
- [ ] صفحات HTML تعمل بشكل صحيح
- [ ] CSS & JavaScript يحملان
- [ ] لا توجد أخطاء في Console

### السيرفر (Render)
- [ ] API يستجيب على https://pandagiveawaays.onrender.com/api
- [ ] البوت يعمل ويرد على الرسائل
- [ ] قاعدة البيانات متصلة
- [ ] لا توجد أخطاء في Logs

### الربط
- [ ] الموقع يتصل بالسيرفر بنجاح
- [ ] البوت يفتح الموقع الصحيح
- [ ] CORS يعمل بدون أخطاء
- [ ] Admin Panel يعمل للمسؤولين فقط

## 🐛 استكشاف الأخطاء

### مشاكل شائعة:

1. **CORS Error**: تأكد من أن الدومين مضاف في app.py
2. **API Connection**: تحقق من الروابط في config.js
3. **Bot Not Working**: راجع متغيرات البيئة في Render
4. **Database Issues**: تأكد من DATABASE_URL في Render  

## 📞 الدعم

في حالة وجود مشاكل، تحقق من:
- Vercel Deployment Logs
- Render Application Logs  
- Browser Console Errors
- Bot Webhook Status