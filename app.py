"""
🌐 Flask Server لخدمة Mini App على Render

⚠️ ملاحظة مهمة:
هذا الملف يحتوي على قاعدة البيانات المشتركة بين:
- الموقع (Mini App)
- صفحة الأدمن
- البوت (panda_giveaways_bot.py)

جميع العمليات يجب أن تتم على نفس قاعدة البيانات لضمان:
✅ نفس المستخدمين
✅ نفس الإحالات
✅ نفس القنوات الإجبارية
✅ نفس اللفات والرصيد
"""
from flask import Flask, send_from_directory, request, jsonify, session
from flask_cors import CORS
import os
import sys
import sqlite3
from datetime import datetime, timedelta
import threading
import subprocess
import random
import hashlib
import secrets
import requests  # لجلب سعر TON
import jwt  # For JWT tokens
from functools import wraps

# إضافة المسار الحالي لـ 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# دالة لجلب سعر TON بالدولار
def get_ton_price_usd():
    """جلب سعر TON من HTX API"""
    try:
        response = requests.get(
            'https://www.htx.com/-/x/pro/market/history/kline?period=1day&size=1&symbol=tonusdt',
            timeout=5
        )
        data = response.json()
        if data and 'data' in data and len(data['data']) > 0:
            # سعر الإغلاق
            price = float(data['data'][0]['close'])
            return price
        return 5.0  # سعر افتراضي
    except Exception as e:
        print(f"خطأ في جلب سعر TON: {e}")
        return 5.0  # سعر افتراضي

def calculate_egp_amount(ton_amount):
    """حساب المبلغ بالجنيه المصري"""
    ton_price_usd = get_ton_price_usd()
    usd_to_egp = 47  # سعر الدولار بالجنيه
    egp_amount = ton_amount * ton_price_usd * usd_to_egp
    return round(egp_amount, 2)

# BOT TOKEN & ADMIN IDS
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = [1797127532, 6603009212]

# 🔐 ADMIN LOGIN CREDENTIALS (من متغيرات البيئة)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'OmarShehata@123')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
# إذا لم يكن هناك password hash، استخدم كلمة سر افتراضية (للتطوير فقط)
if not ADMIN_PASSWORD_HASH:
    # Default password: Ommsaa#@123 (يجب تغييرها في الإنتاج!)
    ADMIN_PASSWORD_HASH = hashlib.sha256('Ommsaa#@123'.encode()).hexdigest()
    print("⚠️ WARNING: Using default admin password! Set ADMIN_PASSWORD_HASH environment variable.")

# JWT Secret Key
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
ADMIN_SESSION_DURATION = timedelta(hours=24)  # صلاحية الجلسة 24 ساعة

# ═══════════════════════════════════════════════════════════════
# 🛡️ ADMIN PROTECTION DECORATOR
# ═══════════════════════════════════════════════════════════════

def verify_admin_token(token):
    """
    🔐 التحقق من صحة Admin JWT Token
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        # التحقق من انتهاء الصلاحية
        exp_timestamp = payload.get('exp')
        if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < datetime.now():
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_admin_auth(f):
    """
    🛡️ Decorator للتحقق من admin authentication
    يتحقق من:
    1. Telegram authentication (is_admin من ADMIN_IDS)
    2. Admin login token (username/password)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # التحقق من Telegram admin (من require_telegram_auth)
        if not kwargs.get('is_admin', False):
            return jsonify({
                'success': False,
                'error': 'Forbidden',
                'message': 'صلاحيات الأدمن فقط - ممنوع الوصول'
            }), 403
        
        # التحقق من Admin Login Token
        admin_token = request.headers.get('X-Admin-Token')
        if not admin_token:
            admin_token = request.json.get('admin_token') if request.is_json else None
        
        if not admin_token:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'يجب تسجيل الدخول كمسؤول أولاً',
                'require_login': True
            }), 401
        
        # التحقق من صحة التوكن
        token_payload = verify_admin_token(admin_token)
        if not token_payload:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'جلسة المسؤول منتهية أو غير صحيحة',
                'require_login': True
            }), 401
        
        # إضافة بيانات Admin للـ kwargs
        kwargs['admin_username'] = token_payload.get('username')
        kwargs['admin_user_id'] = token_payload.get('user_id')
        
        return f(*args, **kwargs)
    
    return decorated_function

# Keep old decorator for backward compatibility (redirect to new one)
def require_admin(f):
    """
    🛡️ Decorator للتحقق من أن المستخدم أدمن (Legacy)
    استخدم require_admin_auth بدلاً منه
    """
    return require_admin_auth(f)

# ═══════════════════════════════════════════════════════════════
# 🔐 TELEGRAM AUTHENTICATION - Security Fix
# ═══════════════════════════════════════════════════════════════

def validate_telegram_init_data(init_data_str):
    """
    التحقق من صحة initData من Telegram WebApp
    يمنع أي محاولة للتلاعب بـ user_id
    """
    try:
        import hmac
        import json
        from urllib.parse import parse_qsl, unquote
        
        if not init_data_str or not BOT_TOKEN:
            print("⚠️ Missing init_data or BOT_TOKEN")
            return None
            
        # تحليل البيانات
        parsed_data = dict(parse_qsl(init_data_str, keep_blank_values=True))
        
        if 'hash' not in parsed_data:
            print("⚠️ No hash in init_data")
            return None
            
        received_hash = parsed_data.pop('hash')
        
        # التحقق من auth_date (تجاهل للأدمن)
        if 'auth_date' in parsed_data:
            auth_date = int(parsed_data['auth_date'])
            current_time = int(datetime.now().timestamp())
            age_hours = (current_time - auth_date) / 3600
            
            # التحقق من user_id لتحديد إذا كان أدمن
            is_admin_user = False
            if 'user' in parsed_data:
                try:
                    user_data_temp = json.loads(unquote(parsed_data['user']))
                    is_admin_user = user_data_temp.get('id') in ADMIN_IDS
                except:
                    pass
            
            # للأدمن: صلاحية 7 أيام، للمستخدمين العاديين: 48 ساعة
            max_age = 604800 if is_admin_user else 172800
            
            if current_time - auth_date > max_age:
                print(f"⚠️ Expired auth_date: {age_hours:.1f} hours old (max: {max_age/3600:.1f}h)")
                return None
            
            print(f"✅ auth_date valid: {age_hours:.1f} hours old (admin: {is_admin_user})")
        
        # إنشاء البيانات للتحقق
        data_check_string = '\n'.join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        # حساب الـ secret key
        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # حساب الـ hash المتوقع
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # مقارنة الـ hashes
        if calculated_hash != received_hash:
            print(f"⚠️ Hash mismatch! Auth failed.")
            return None
        
        # استخراج بيانات المستخدم
        if 'user' in parsed_data:
            user_data = json.loads(unquote(parsed_data['user']))
            print(f"✅ Valid Telegram auth for user {user_data.get('id')}")
            return {
                'user_id': user_data.get('id'),
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'is_premium': user_data.get('is_premium', False),
                'language_code': user_data.get('language_code', 'en')
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Error validating Telegram init_data: {e}")
        import traceback
        traceback.print_exc()
        return None

def require_telegram_auth(f):
    """
    🔐 Decorator للتحقق من صحة المصادقة في كل request
    ✅ يتحقق من Telegram initData للجميع (بما في ذلك الأدمن)
    ❌ لا يسمح بتزوير user_id من URL أو JSON
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 🔐 التحقق الإجباري من init_data للجميع (بدون استثناءات)
        init_data = None
        
        # محاولة الحصول من headers (الأفضل)
        init_data = request.headers.get('X-Telegram-Init-Data')
        
        # محاولة الحصول من query params
        if not init_data:
            init_data = request.args.get('init_data')
        
        # محاولة الحصول من JSON body
        if not init_data and request.is_json:
            init_data = request.json.get('init_data')
        
        if not init_data:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'يجب تشغيل التطبيق من خلال Telegram Bot فقط'
            }), 401
        
        # التحقق من صحة البيانات والتوقيع
        user_data = validate_telegram_init_data(init_data)
        
        if not user_data:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'بيانات مصادقة غير صحيحة أو منتهية الصلاحية'
            }), 401
        
        # ✅ استخدام user_id المُتحقق منه فقط (من initData الموقع)
        verified_user_id = user_data['user_id']
        kwargs['authenticated_user_id'] = verified_user_id
        
        # ✅ إضافة flag للتحقق من صلاحيات الأدمن
        kwargs['is_admin'] = verified_user_id in ADMIN_IDS
        
        return f(*args, **kwargs)
    
    return decorated_function

def send_withdrawal_notification_to_admin(user_id, username, full_name, amount, withdrawal_type, wallet_address, phone_number, withdrawal_id, auto_process=False):
    """إرسال إشعار للأدمن في البوت عند طلب سحب - دفع يدوي فقط"""
    try:
        # إذا كان السحب تلقائي، لا ترسل إشعار (لكن السحب التلقائي معطل الآن)
        if auto_process:
            print(f"⚠️ Auto-processing is DISABLED - Manual payment required")
            # نستمر في الإرسال حتى لو كان auto_process=True
        
        # إنشاء رسالة مختلفة حسب نوع السحب
        if withdrawal_type.upper() == 'VODAFONE' or withdrawal_type.upper() == 'VODAFONE_CASH':
            egp_amount = calculate_egp_amount(amount)
            vodafone_code = f"*9*7*{phone_number}*{int(egp_amount)}#"
            
            message = f"""
🆕 <b>طلب سحب جديد - فودافون كاش</b>

👤 <b>المستخدم:</b> {full_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{username if username else 'N/A'}

💰 <b>المبلغ:</b> {amount} TON
💵 <b>المبلغ بالجنيه:</b> {egp_amount} EGP
📞 <b>رقم فودافون:</b> <code>{phone_number}</code>

📋 <b>كود التحويل:</b>
<code>{vodafone_code}</code>

⏰ <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔢 <b>رقم الطلب:</b> #{withdrawal_id}

⚠️ <b>ملاحظة:</b> الدفع يدوي فقط لأسباب أمنية
            """
        else:
            # إنشاء رابط دفع مباشر لـ TON مع كومنت
            # Comment format: W{withdrawal_id}-{user_id}
            payment_comment = f"W{withdrawal_id}-{user_id}"
            
            # رابط TON للدفع المباشر (يفتح في محفظة Tonkeeper)
            ton_payment_link = f"ton://transfer/{wallet_address}?amount={int(amount * 1_000_000_000)}&text={payment_comment}"
            
            message = f"""
🆕 <b>طلب سحب جديد - TON Wallet</b>

👤 <b>المستخدم:</b> {full_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{username if username else 'N/A'}

💰 <b>المبلغ:</b> {amount} TON
💳 <b>عنوان المحفظة:</b>
<code>{wallet_address}</code>

💬 <b>Comment (مهم!):</b> <code>{payment_comment}</code>

⏰ <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔢 <b>رقم الطلب:</b> #{withdrawal_id}

⚠️ <b>تعليمات الدفع:</b>
1. افتح محفظة TON الخاصة بك
2. أرسل {amount} TON للعنوان أعلاه
3. <b>مهم جداً:</b> اكتب Comment: <code>{payment_comment}</code>
4. البوت سيكتشف المعاملة تلقائياً وينشرها في قناة السحوبات

⚠️ <b>ملاحظة:</b> الدفع التلقائي معطل نهائياً لأسباب أمنية
            """
        
        # إنشاء أزرار inline keyboard
        if withdrawal_type.upper() in ['TON', 'TON_WALLET']:
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💎 فتح في Tonkeeper", "url": ton_payment_link}],
                    [
                        {"text": "✅ قبول (بعد الدفع)", "callback_data": f"approve_withdrawal_{withdrawal_id}"},
                        {"text": "❌ رفض", "callback_data": f"reject_withdrawal_{withdrawal_id}"}
                    ]
                ]
            }
        else:
            keyboard = {
                "inline_keyboard": [[
                    {"text": "✅ قبول", "callback_data": f"approve_withdrawal_{withdrawal_id}"},
                    {"text": "❌ رفض", "callback_data": f"reject_withdrawal_{withdrawal_id}"}
                ]]
            }
        
        # إرسال الرسالة لكل أدمن باستخدام HTTP API
        for admin_id in ADMIN_IDS:
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": admin_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "reply_markup": keyboard
                }
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ Notification sent to admin {admin_id}")
                else:
                    print(f"⚠️ Failed to send to admin {admin_id}: {response.text}")
                    
            except Exception as e:
                print(f"❌ Failed to send to admin {admin_id}: {e}")
        
        print(f"✅ Withdrawal notification processing complete")
        
    except Exception as e:
        print(f"❌ Error sending withdrawal notification: {e}")
        import traceback
        traceback.print_exc()

app = Flask(__name__)  # إزالة static_folder لأن الملفات ستكون في Vercel
# إعداد CORS للسماح بالوصول من Vercel
CORS(app, 
    resources={
        r"/api/*": {
            "origins": [
                'https://panda-giveawaays.vercel.app',
                'http://localhost:3000',
                'http://127.0.0.1:5000',
                'http://localhost:5000'
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type", 
                "Accept", 
                "Authorization",
                "X-Telegram-Init-Data",
                "X-User-Id",
                "X-Session-Id",
                "X-Admin-Token"  # ✅ إضافة Admin Token header
            ],
            "supports_credentials": False
        }
    }
)  # السماح بـ CORS من المواقع المحددة

# ═══════════════════════════════════════════════════════════════
# 🤖 BOT STARTUP IN BACKGROUND
# ═══════════════════════════════════════════════════════════════

def start_telegram_bot():
    """تشغيل البوت في thread منفصل"""
    try:
        print("🤖 Starting Telegram Bot in background...")
        # تشغيل البوت كـ subprocess
        subprocess.Popen(
            [sys.executable, "panda_giveaways_bot.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        print("✅ Bot process started")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")

# تشغيل البوت في thread منفصل عند بدء التشغيل
if not os.environ.get('RENDER'):
    # محلياً فقط، شغل البوت في الخلفية
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    print("🎉 Bot thread started locally")
else:
    # على Render، شغل البوت في الخلفية كمان
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    print("🚀 Bot thread started on Render")

# ═══════════════════════════════════════════════════════════════
# 🗄️ DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════

# Use absolute path on Render to ensure both bot and Flask use same database
if os.environ.get('RENDER'):
    DATABASE_PATH = os.getenv('DATABASE_PATH', '/opt/render/project/src/panda_giveaways.db')
else:
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'panda_giveaways.db')

print(f"📂 Using database at: {DATABASE_PATH}")

def init_database():
    """إنشاء قاعدة البيانات إذا لم تكن موجودة"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            total_spins INTEGER DEFAULT 0,
            available_spins INTEGER DEFAULT 0,
            total_referrals INTEGER DEFAULT 0,
            valid_referrals INTEGER DEFAULT 0,
            referrer_id INTEGER,
            created_at TEXT NOT NULL,
            last_active TEXT,
            is_banned INTEGER DEFAULT 0,
            last_spin_time TEXT,
            spin_count_today INTEGER DEFAULT 0,
            last_withdrawal_time TEXT,
            ton_wallet TEXT,
            vodafone_number TEXT
        )
    """)
    
    # جدول الإحالات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            is_valid INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            validated_at TEXT,
            channels_checked INTEGER DEFAULT 0,
            device_verified INTEGER DEFAULT 0,
            UNIQUE(referrer_id, referred_id)
        )
    """)
    
    # جدول اللفات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prize_name TEXT NOT NULL,
            prize_amount REAL NOT NULL,
            spin_time TEXT NOT NULL,
            spin_hash TEXT NOT NULL UNIQUE,
            ip_address TEXT
        )
    """)
    
    # جدول السحوبات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            withdrawal_type TEXT NOT NULL,
            wallet_address TEXT,
            phone_number TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_at TEXT NOT NULL,
            processed_at TEXT,
            processed_by INTEGER,
            tx_hash TEXT,
            rejection_reason TEXT
        )
    """)
    
    # جدول المهام
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            task_name TEXT NOT NULL,
            task_description TEXT,
            task_link TEXT,
            channel_username TEXT,
            is_pinned INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            added_by INTEGER NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    
    # التحقق من الأعمدة الجديدة وإضافتها إن لم تكن موجودة
    try:
        cursor.execute("SELECT is_pinned FROM tasks LIMIT 1")
    except:
        cursor.execute("ALTER TABLE tasks ADD COLUMN is_pinned INTEGER DEFAULT 0")
        
    try:
        cursor.execute("SELECT task_link FROM tasks LIMIT 1")
    except:
        cursor.execute("ALTER TABLE tasks ADD COLUMN task_link TEXT")
        
    try:
        cursor.execute("SELECT channel_username FROM tasks LIMIT 1")
    except:
        cursor.execute("ALTER TABLE tasks ADD COLUMN channel_username TEXT")

    
    # جدول إنجاز المهام
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            verified INTEGER DEFAULT 0,
            UNIQUE(user_id, task_id)
        )
    """)
    
    # جدول القنوات الإجبارية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL UNIQUE,
            channel_name TEXT NOT NULL,
            channel_url TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            added_by INTEGER NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    
    # جدول التحقق من الأجهزة - device fingerprinting
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            fingerprint TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            user_agent TEXT,
            timezone TEXT,
            screen_resolution TEXT,
            canvas_fp TEXT,
            audio_fp TEXT,
            local_id TEXT,
            verified_at TEXT NOT NULL,
            last_seen TEXT,
            is_blocked INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # جدول سجل محاولات التحقق
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fingerprint TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            attempt_time TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # جدول tokens التحقق المؤقتة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # جدول إعدادات النظام - تحكم في التحقق من التعدد
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by INTEGER
        )
    """)
    
    # تفعيل التحقق من التعدد افتراضياً
    cursor.execute("""
        INSERT OR IGNORE INTO system_settings (setting_key, setting_value, updated_at)
        VALUES ('verification_enabled', 'true', ?)
    """, (datetime.now().isoformat(),))
    
    # جدول جوائز العجلة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wheel_prizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            probability REAL NOT NULL,
            color TEXT NOT NULL,
            emoji TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            position INTEGER DEFAULT 0,
            added_at TEXT NOT NULL,
            updated_at TEXT
        )
    """)
    
    # إضافة القنوات الإجبارية الافتراضية إذا لم تكن موجودة
    cursor.execute("SELECT COUNT(*) FROM required_channels")
    count = cursor.fetchone()[0]  # الوصول بالـ index وليس بالـ key
    if count == 0:
        now = datetime.now().isoformat()
        default_channels = [
            ('@PandaAdds', 'Panda Adds', 'https://t.me/PandaAdds', 1797127532),
            ('@CRYPTO_FLASSH', 'Crypto Flash', 'https://t.me/CRYPTO_FLASSH', 1797127532)
        ]
        for channel_id, name, url, admin_id in default_channels:
            cursor.execute("""
                INSERT INTO required_channels (channel_id, channel_name, channel_url, is_active, added_by, added_at)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (channel_id, name, url, admin_id, now))
    
    # إضافة الجوائز الافتراضية إذا لم تكن موجودة
    cursor.execute("SELECT COUNT(*) FROM wheel_prizes")
    count = cursor.fetchone()[0]
    if count == 0:
        now = datetime.now().isoformat()
        # الجوائز مطابقة لـ config.js: 0.05@94%, 0.1@5%, 0.15@1%, باقي 0%
        default_prizes = [
            ('0.05 TON', 0.05, 94, '#4CAF50', '🎯', 0),
            ('0.1 TON', 0.1, 5, '#2196F3', '💎', 1),
            ('0.15 TON', 0.15, 1, '#FF9800', '⭐', 2),
            ('0.5 TON', 0.5, 0, '#9C27B0', '🌟', 3),
            ('1.0 TON', 1.0, 0, '#FFD700', '💰', 4),
            ('0.25 TON', 0.25, 0, '#E91E63', '✨', 5)
        ]
        for name, value, prob, color, emoji, pos in default_prizes:
            cursor.execute("""
                INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (name, value, prob, color, emoji, pos, now))
    
    # إضافة أعمدة التحقق للجداول القديمة
    try:
        cursor.execute("ALTER TABLE referrals ADD COLUMN channels_checked INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # العمود موجود بالفعل
    
    try:
        cursor.execute("ALTER TABLE referrals ADD COLUMN device_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # العمود موجود بالفعل
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_device_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # العمود موجود بالفعل
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN verification_required INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # العمود موجود بالفعل
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT")
    except sqlite3.OperationalError:
        pass  # العمود موجود بالفعل
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# تهيئة قاعدة البيانات عند بدء التشغيل
init_database()

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def get_user(user_id):
    """الحصول على بيانات مستخدم"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user_if_not_exists(user_id, username="", full_name="User"):
    """إنشاء مستخدم إذا لم يكن موجوداً"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, full_name, created_at, last_active)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, full_name, now, now))
        conn.commit()
    except Exception as e:
        print(f"Error creating user: {e}")
    finally:
        conn.close()

def get_user_referrals_db(user_id):
    """الحصول على إحالات المستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, u.username, u.full_name, u.created_at as joined_at
            FROM referrals r
            LEFT JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,))
        referrals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return referrals
    except Exception as e:
        print(f"Error in get_user_referrals_db: {e}")
        conn.close()
        return []

def get_user_spins_db(user_id, limit=50):
    """الحصول على تاريخ اللفات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM spins
            WHERE user_id = ?
            ORDER BY spin_time DESC
            LIMIT ?
        """, (user_id, limit))
        spins = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return spins
    except Exception as e:
        print(f"Error in get_user_spins_db: {e}")
        conn.close()
        return []

def get_bot_stats():
    """إحصائيات البوت"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    cursor.execute("SELECT COUNT(*) as total FROM users")
    stats['total_users'] = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM referrals WHERE is_valid = 1")
    stats['total_referrals'] = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM spins")
    stats['total_spins'] = cursor.fetchone()['total']
    
    cursor.execute("SELECT SUM(prize_amount) as total FROM spins")
    result = cursor.fetchone()
    stats['total_distributed'] = result['total'] if result['total'] else 0
    
    cursor.execute("SELECT COUNT(*) as pending FROM withdrawals WHERE status = 'pending'")
    stats['pending_withdrawals'] = cursor.fetchone()['pending']
    
    cursor.execute("SELECT SUM(amount) as total FROM withdrawals WHERE status = 'completed'")
    result = cursor.fetchone()
    stats['total_withdrawn'] = result['total'] if result['total'] else 0
    
    conn.close()
    return stats

# ═══════════════════════════════════════════════════════════════
# 🌐 ROUTES - Redirects to Vercel Frontend
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """إعادة توجيه للموقع في Vercel"""
    from flask import redirect
    return redirect('https://panda-giveawaays.vercel.app', code=302)

@app.route('/admin')
def admin():
    """
    🔐 صفحة الأدمن - محمية بالكامل
    ✅ يتطلب Telegram initData صحيح
    ✅ يتطلب أن يكون user_id في قائمة ADMIN_IDS
    ❌ لا يقبل user_id من URL
    """
    from flask import redirect
    
    # 🔐 التحقق الإجباري من المصادقة عبر init_data
    init_data = request.args.get('init_data')
    
    if not init_data:
        return jsonify({
            'error': 'غير مسموح! هذه الصفحة تعمل فقط من خلال Telegram Bot',
            'message': 'Access Denied: This page only works through Telegram Mini App',
            'hint': 'لا يمكن فتح هذه الصفحة من المتصفح مباشرة'
        }), 403
    
    # التحقق من صحة البيانات والتوقيع
    user_data = validate_telegram_init_data(init_data)
    
    if not user_data:
        return jsonify({
            'error': 'بيانات مصادقة غير صحيحة',
            'message': 'Invalid or expired authentication data',
            'hint': 'حاول فتح الصفحة من البوت مرة أخرى'
        }), 401
    
    # التحقق من أن المستخدم أدمن
    if user_data['user_id'] not in ADMIN_IDS:
        return jsonify({
            'error': 'غير مسموح! هذه الصفحة للمسؤولين فقط',
            'message': 'Access Denied: Admin only',
            'your_id': user_data['user_id']
        }), 403
    
    # ✅ المستخدم أدمن مصادق عليه
    # إرسال init_data للفرونت إند للاستخدام في API requests
    return redirect(
        f'https://panda-giveawaays.vercel.app/admin#{request.query_string.decode()}',
        code=302
    )

@app.route('/api/admin/login', methods=['POST'])
@require_telegram_auth
def admin_login(authenticated_user_id=None, is_admin=False):
    """
    🔐 تسجيل دخول المسؤول بـ username/password
    يتطلب:
    1. Telegram authentication (من require_telegram_auth)
    2. Username & Password صحيح
    """
    try:
        # التحقق من أن المستخدم أدمن من ADMIN_IDS
        if not is_admin:
            return jsonify({
                'success': False,
                'error': 'غير مسموح! هذه الصفحة للمسؤولين فقط'
            }), 403
        
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'يرجى إدخال اسم المستخدم وكلمة السر'
            }), 400
        
        # التحقق من username
        if username != ADMIN_USERNAME:
            return jsonify({
                'success': False,
                'error': 'اسم المستخدم أو كلمة السر غير صحيحة'
            }), 401
        
        # التحقق من password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if password_hash != ADMIN_PASSWORD_HASH:
            return jsonify({
                'success': False,
                'error': 'اسم المستخدم أو كلمة السر غير صحيحة'
            }), 401
        
        # ✅ تسجيل دخول ناجح - إنشاء JWT token
        expiry = datetime.now() + ADMIN_SESSION_DURATION
        token_payload = {
            'username': username,
            'user_id': authenticated_user_id,
            'exp': expiry.timestamp(),
            'iat': datetime.now().timestamp()
        }
        
        admin_token = jwt.encode(token_payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الدخول بنجاح',
            'admin_token': admin_token,
            'expires_at': expiry.isoformat(),
            'username': username
        })
        
    except Exception as e:
        print(f"❌ Error in admin login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'حدث خطأ أثناء تسجيل الدخول'
        }), 500

@app.route('/api/admin/verify-session', methods=['POST'])
@require_telegram_auth
@require_admin_auth
def verify_admin_session(authenticated_user_id=None, is_admin=False, admin_username=None, admin_user_id=None):
    """
    ✅ التحقق من صحة جلسة المسؤول
    """
    return jsonify({
        'success': True,
        'valid': True,
        'username': admin_username,
        'user_id': admin_user_id
    })

@app.route('/fp.html')
@app.route('/fp')
def fingerprint_page():
    """إعادة توجيه لصفحة التحقق من الجهاز"""
    from flask import redirect
    return redirect('https://panda-giveawaays.vercel.app/fp.html', code=302)

# ═══════════════════════════════════════════════════════════════
# 🔌 API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/user/<int:user_id>', methods=['GET'])
@require_telegram_auth
def get_user_data(user_id, authenticated_user_id=None, is_admin=False):
    """الحصول على بيانات المستخدم"""
    try:
        # التحقق من أن user_id يطابق الـ authenticated_user_id
        if user_id != authenticated_user_id:
            return jsonify({
                'success': False, 
                'error': 'Unauthorized access - User ID mismatch'
            }), 403
        
        user = get_user(user_id)
        
        # إذا المستخدم غير موجود، أنشئه
        if not user:
            create_user_if_not_exists(user_id)
            user = get_user(user_id)
        
        if user:
            return jsonify({
                'success': True,
                'data': {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'balance': float(user['balance']),
                    'available_spins': user['available_spins'],
                    'total_spins': user['total_spins'],
                    'total_referrals': user['total_referrals'],
                    'created_at': user['created_at'],
                    'is_banned': user['is_banned']
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create user'
            }), 500
            
    except Exception as e:
        print(f"Error in get_user_data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/user/<int:user_id>/update-profile', methods=['POST'])
@require_telegram_auth
def update_user_profile(user_id, authenticated_user_id=None, is_admin=False):
    """تحديث username و full_name للمستخدم من Telegram"""
    try:
        # التحقق من المصادقة
        if user_id != authenticated_user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403
        
        data = request.get_json()
        username = data.get('username', '')
        full_name = data.get('full_name', 'User')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # التحقق من وجود المستخدم
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # تحديث البيانات
            cursor.execute("""
                UPDATE users 
                SET username = ?, full_name = ?, last_active = ?
                WHERE user_id = ?
            """, (username, full_name, now, user_id))
            conn.commit()
            print(f"✅ Updated user {user_id}: {username}, {full_name}")
        else:
            # إنشاء مستخدم جديد
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, now, now))
            conn.commit()
            print(f"✅ Created user {user_id}: {username}, {full_name}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        print(f"Error in update_user_profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/user/<int:user_id>/referrals', methods=['GET'])
@require_telegram_auth
def get_user_referrals(user_id, authenticated_user_id=None, is_admin=False):
    """الحصول على إحالات المستخدم"""
    try:
        # التحقق من المصادقة
        if user_id != authenticated_user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403
        
        referrals = get_user_referrals_db(user_id)
        return jsonify({
            'success': True,
            'data': referrals
        })
    except Exception as e:
        print(f"Error in get_user_referrals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/<int:user_id>/spins', methods=['GET'])
@require_telegram_auth
def get_user_spins(user_id, authenticated_user_id=None, is_admin=False):
    """الحصول على تاريخ لفات المستخدم"""
    try:
        # التحقق من المصادقة
        if user_id != authenticated_user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403
        
        limit = request.args.get('limit', 50, type=int)
        spins = get_user_spins_db(user_id, limit)
        return jsonify({
            'success': True,
            'data': spins
        })
    except Exception as e:
        print(f"Error in get_user_spins: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/spin', methods=['POST'])
@require_telegram_auth
def perform_spin(authenticated_user_id=None, is_admin=False):
    """تنفيذ لفة العجلة"""
    import random
    import hashlib
    try:
        # استخدام user_id المصادق عليه
        user_id = authenticated_user_id
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        # Get user
        user = get_user(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if user is banned
        if user['is_banned']:
            return jsonify({'success': False, 'error': 'تم حظرك من البوت'}), 403
        
        # Check available spins
        if user['available_spins'] <= 0:
            return jsonify({'success': False, 'error': 'ليس لديك لفات متاحة'}), 400
        
        # Define prizes with probabilities (مطابقة لـ config.js)
        prizes = [
            {'name': '0.05 TON', 'amount': 0.05, 'probability': 94},
            {'name': '0.1 TON', 'amount': 0.1, 'probability': 5},
            {'name': '0.15 TON', 'amount': 0.15, 'probability': 1},
            {'name': '0.5 TON', 'amount': 0.5, 'probability': 0},
            {'name': '1.0 TON', 'amount': 1.0, 'probability': 0},
            {'name': '0.25 TON', 'amount': 0.25, 'probability': 0}
        ]
        
        # Select prize based on probability
        total_probability = sum(p['probability'] for p in prizes)
        rand = random.uniform(0, total_probability)
        cumulative = 0
        selected_prize = prizes[-1]  # Default to last prize
        
        for prize in prizes:
            cumulative += prize['probability']
            if rand <= cumulative:
                selected_prize = prize
                break
        
        # Generate unique spin hash
        now = datetime.now().isoformat()
        spin_hash = hashlib.sha256(f"{user_id}{now}{random.random()}".encode()).hexdigest()
        
        # Update database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Add spin record
            cursor.execute("""
                INSERT INTO spins (user_id, prize_name, prize_amount, spin_time, spin_hash, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, selected_prize['name'], selected_prize['amount'], now, spin_hash, request.remote_addr))
            
            # Update user
            new_balance = user['balance'] + selected_prize['amount']
            new_spins = user['available_spins'] - 1
            new_total_spins = user['total_spins'] + 1
            
            cursor.execute("""
                UPDATE users 
                SET balance = ?,
                    available_spins = ?,
                    total_spins = ?,
                    last_spin_time = ?,
                    last_active = ?
                WHERE user_id = ?
            """, (new_balance, new_spins, new_total_spins, now, now, user_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'prize': selected_prize,
                    'new_balance': new_balance,
                    'new_spins': new_spins,
                    'spin_hash': spin_hash
                }
            })
            
        except Exception as db_error:
            conn.rollback()
            conn.close()
            print(f"Database error in spin: {db_error}")
            return jsonify({'success': False, 'error': 'خطأ في قاعدة البيانات'}), 500
        
    except Exception as e:
        print(f"Error in perform_spin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_bot_stats_route():
    """إحصائيات البوت (للأدمن)"""
    try:
        stats = get_bot_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        print(f"Error in get_bot_stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """الحصول على حالة البوت (مفعل/معطل)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT setting_value 
            FROM bot_settings 
            WHERE setting_key = 'bot_enabled'
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        bot_enabled = True  # افتراضياً مفعل
        if row:
            bot_enabled = row[0].lower() == 'true'
        
        return jsonify({
            'success': True,
            'bot_enabled': bot_enabled
        })
    except Exception as e:
        print(f"Error in get_bot_status: {e}")
        return jsonify({'success': True, 'bot_enabled': True}), 200

@app.route('/api/ping', methods=['GET'])
def ping():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """الحصول على المهام النشطة للمستخدمين"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, task_type, task_name, task_description, task_link, 
                   channel_username, is_pinned
            FROM tasks 
            WHERE is_active = 1 
            ORDER BY is_pinned DESC, id DESC
        """)
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'task_type': row[1],
                'task_name': row[2],
                'task_description': row[3],
                'task_link': row[4],
                'channel_username': row[5],
                'is_pinned': row[6]
            })
        
        conn.close()
        return jsonify({
            'success': True,
            'tasks': tasks
        })
        
    except Exception as e:
        print(f"Error in get_tasks: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/user/<int:user_id>/completed-tasks', methods=['GET'])
@require_telegram_auth
def get_user_completed_tasks(user_id, authenticated_user_id=None, is_admin=False):
    """الحصول على المهام المكتملة للمستخدم"""
    try:
        # التحقق من المصادقة
        if user_id != authenticated_user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, completed_at, verified
            FROM user_tasks
            WHERE user_id = ? AND verified = 1
        """, (user_id,))
        
        completed_tasks = []
        for row in cursor.fetchall():
            completed_tasks.append({
                'task_id': row[0],
                'completed_at': row[1],
                'verified': row[2]
            })
        
        conn.close()
        return jsonify({
            'success': True,
            'completed_tasks': completed_tasks
        })
        
    except Exception as e:
        print(f"Error in get_user_completed_tasks: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/verify', methods=['POST'])
def verify_task_completion(task_id):
    """التحقق من إتمام المهمة عبر البوت"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'معرف المستخدم مطلوب'}), 400
        
        # جلب بيانات المهمة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_type, channel_username
            FROM tasks
            WHERE id = ? AND is_active = 1
        """, (task_id,))
        
        task = cursor.fetchone()
        if not task:
            conn.close()
            return jsonify({'success': False, 'message': 'المهمة غير موجودة'}), 404
        
        task_type = task[0]
        channel_username = task[1]
        
        # التحقق من أن المستخدم لم يكمل المهمة من قبل
        cursor.execute("""
            SELECT id FROM user_tasks
            WHERE user_id = ? AND task_id = ? AND verified = 1
        """, (user_id, task_id))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'لقد أكملت هذه المهمة من قبل'})
        
        # إذا كانت قناة، التحقق من الاشتراك عبر البوت
        if task_type == 'channel' and channel_username:
            try:
                # إرسال طلب للبوت للتحقق من الاشتراك مع fallback
                try:
                    import requests
                    bot_url = 'http://localhost:8081/verify-subscription'
                    verify_response = requests.post(bot_url, json={
                        'user_id': user_id,
                        'channel_username': channel_username
                    }, timeout=15)  # زيادة timeout
                    
                    verify_data = verify_response.json()
                    
                    if not verify_data.get('is_subscribed', False):
                        conn.close()
                        return jsonify({
                            'success': False, 
                            'message': '❌ لم يتم العثور على اشتراكك! تأكد من الاشتراك في القناة أولاً'
                        })
                        
                except (requests.exceptions.RequestException, requests.exceptions.Timeout, ConnectionError) as e:
                    # في حالة عدم توفر البوت، نسمح بالمتابعة مؤقتاً
                    print(f"⚠️ Bot unavailable for verification (task {task_id}): {e}")
                    print(f"📝 Allowing task completion without bot verification for user {user_id}")
                    # نسمح بإتمام المهمة بدون التحقق من البوت
                    
            except Exception as e:
                print(f"Error verifying subscription: {e}")
                # نسمح بإتمام المهمة في حالة الخطأ
                print(f"📝 Allowing task completion due to verification error for user {user_id}")
        
        # تسجيل إتمام المهمة
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_tasks (user_id, task_id, completed_at, verified)
            VALUES (?, ?, ?, 1)
        """, (user_id, task_id, now))
        
        # التحقق من عدد المهام المكتملة
        cursor.execute("""
            SELECT COUNT(*) FROM user_tasks
            WHERE user_id = ? AND verified = 1
        """, (user_id,))
        
        completed_count = cursor.fetchone()[0]
        
        # كل 5 مهمات = 1 دورة
        new_spin = 0
        if completed_count % 5 == 0:
            cursor.execute("""
                UPDATE users 
                SET available_spins = available_spins + 1
                WHERE user_id = ?
            """, (user_id,))
            new_spin = 1
        
        conn.commit()
        
        # جلب الدورات الجديدة
        cursor.execute("SELECT available_spins FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        new_spins = result[0] if result else 0
        
        conn.close()
        
        message = f'✅ تم إتمام المهمة! ({completed_count}/5)'
        if new_spin:
            message = f'🎉 تم إتمام المهمة! حصلت على دورة جديدة! (أكملت 5 مهمات)'
        
        return jsonify({
            'success': True,
            'message': message,
            'completed_count': completed_count,
            'new_spin_awarded': new_spin == 1,
            'total_spins': new_spins
        })
        
    except Exception as e:
        print(f"Error in verify_task_completion: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطأ: {str(e)}'}), 500

@app.route('/api/user/<int:user_id>/withdrawals', methods=['GET'])
@require_telegram_auth
def get_user_withdrawals(user_id, authenticated_user_id=None, is_admin=False):
    """الحصول على طلبات السحب للمستخدم"""
    try:
        # التحقق من المصادقة
        if user_id != authenticated_user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized access'
            }), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM withdrawals
            WHERE user_id = ?
            ORDER BY requested_at DESC
        """, (user_id,))
        withdrawals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({
            'success': True,
            'data': withdrawals
        })
    except Exception as e:
        print(f"Error in get_user_withdrawals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/withdrawal/request', methods=['POST'])
@require_telegram_auth
def request_withdrawal(authenticated_user_id=None, is_admin=False):
    """طلب سحب جديد"""
    try:
        # استخدام user_id المصادق عليه
        user_id = authenticated_user_id
        
        data = request.get_json()
        amount = float(data.get('amount', 0))
        withdrawal_type = data.get('withdrawal_type') or data.get('type') or 'TON'
        wallet_address = data.get('wallet_address') or data.get('address', '')
        phone_number = data.get('phone_number', '')
        
        print(f"💸 Withdrawal request: user={user_id}, amount={amount}, type={withdrawal_type}")
        
        if not user_id or amount <= 0:
            return jsonify({'success': False, 'error': 'بيانات غير صالحة'}), 400
        
        # التحقق من الحد الأدنى للسحب
        min_withdrawal = 0.1
        if amount < min_withdrawal:
            return jsonify({
                'success': False,
                'error': f'الحد الأدنى للسحب {min_withdrawal} TON'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # التحقق من رصيد المستخدم
        cursor.execute('SELECT balance, username, full_name FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'مستخدم غير موجود'}), 404
            
        if user['balance'] < amount:
            conn.close()
            return jsonify({'success': False, 'error': 'رصيد غير كافٍ'}), 400
        
        # إنشاء طلب السحب
        cursor.execute("""
            INSERT INTO withdrawals (user_id, amount, withdrawal_type, wallet_address, phone_number, status, requested_at)
            VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (user_id, amount, withdrawal_type, wallet_address, phone_number))
        
        withdrawal_id = cursor.lastrowid
        
        # خصم المبلغ من رصيد المستخدم
        cursor.execute("""
            UPDATE users 
            SET balance = balance - ?,
                last_withdrawal_time = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (amount, user_id))
        
        conn.commit()
        
        # الحصول على الرصيد الجديد
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        new_balance = cursor.fetchone()['balance']
        
        conn.close()
        
        # ⛔ الدفع التلقائي معطل نهائياً لأسباب أمنية
        # كل الدفعات يدوية مع التحقق من Transaction عبر TON API فقط
        
        # إرسال إشعار للأدمن في البوت (دائماً - دفع يدوي)
        try:
            send_withdrawal_notification_to_admin(
                user_id=user_id,
                username=user['username'],
                full_name=user['full_name'],
                amount=amount,
                withdrawal_type=withdrawal_type,
                wallet_address=wallet_address,
                phone_number=phone_number,
                withdrawal_id=withdrawal_id,
                auto_process=False  # ⛔ دائماً False - الدفع يدوي فقط
            )
        except Exception as e:
            print(f"⚠️ Failed to send admin notification: {e}")
        
        return jsonify({
            'success': True,
            'message': 'تم إرسال طلب السحب بنجاح',
            'data': {
                'new_balance': new_balance,
                'withdrawal_id': withdrawal_id
            }
        })
        
    except Exception as e:
        print(f"Error in request_withdrawal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/withdrawals', methods=['GET'])
def get_all_withdrawals():
    """الحصول على جميع طلبات السحب (للأدمن)"""
    try:
        status = request.args.get('status', 'all')  # all, pending, completed, rejected
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if status == 'all':
            cursor.execute("""
                SELECT 
                    w.*,
                    u.full_name as user_name,
                    u.username
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                ORDER BY w.requested_at DESC
            """)
        else:
            cursor.execute("""
                SELECT 
                    w.*,
                    u.full_name as user_name,
                    u.username
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status = ?
                ORDER BY w.requested_at DESC
            """, (status,))
        
        withdrawals = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'data': withdrawals
        })
        
    except Exception as e:
        print(f"Error in get_all_withdrawals: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/withdrawal/approve', methods=['POST'])
def approve_withdrawal():
    """قبول طلب سحب"""
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        admin_id = data.get('admin_id')
        tx_hash = data.get('tx_hash', '')
        
        if not withdrawal_id:
            return jsonify({'success': False, 'error': 'withdrawal_id is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تحديث حالة الطلب
        cursor.execute("""
            UPDATE withdrawals 
            SET status = 'completed',
                processed_at = CURRENT_TIMESTAMP,
                processed_by = ?,
                tx_hash = ?
            WHERE id = ?
        """, (admin_id, tx_hash, withdrawal_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم قبول طلب السحب بنجاح'
        })
        
    except Exception as e:
        print(f"Error in approve_withdrawal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/withdrawal/reject', methods=['POST'])
def reject_withdrawal():
    """رفض طلب سحب وإرجاع المبلغ"""
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        admin_id = data.get('admin_id')
        reason = data.get('reason', 'لم يتم تحديد سبب')
        
        if not withdrawal_id:
            return jsonify({'success': False, 'error': 'withdrawal_id is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على معلومات الطلب
        cursor.execute('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,))
        withdrawal = cursor.fetchone()
        
        if not withdrawal:
            conn.close()
            return jsonify({'success': False, 'error': 'طلب السحب غير موجود'}), 404
        
        # إرجاع المبلغ للمستخدم
        cursor.execute("""
            UPDATE users 
            SET balance = balance + ?
            WHERE user_id = ?
        """, (withdrawal['amount'], withdrawal['user_id']))
        
        # تحديث حالة الطلب
        cursor.execute("""
            UPDATE withdrawals 
            SET status = 'rejected',
                processed_at = CURRENT_TIMESTAMP,
                processed_by = ?,
                rejection_reason = ?
            WHERE id = ?
        """, (admin_id, reason, withdrawal_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم رفض طلب السحب وإرجاع المبلغ'
        })
        
    except Exception as e:
        print(f"Error in reject_withdrawal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/referral/register', methods=['POST'])
def register_referral():
    """تسجيل إحالة جديدة مع تحسينات أداء"""
    try:
        data = request.get_json()
        referrer_id = data.get('referrer_id')
        referred_id = data.get('referred_id')
        
        if not referrer_id or not referred_id:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        # التحقق من عدم إحالة نفسه
        if referrer_id == referred_id:
            return jsonify({'success': False, 'error': 'Cannot refer yourself'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            # فحص سريع للإحالة المكررة أولاً
            cursor.execute("SELECT id FROM referrals WHERE referrer_id = ? AND referred_id = ? LIMIT 1", 
                          (referrer_id, referred_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': True, 'message': 'Referral already exists'}) # نرجع success لتجنب المحاولات
            
            # تسجيل الإحالة
            cursor.execute("""
                INSERT INTO referrals (referrer_id, referred_id, is_valid, created_at, validated_at)
                VALUES (?, ?, 1, ?, ?)
            """, (referrer_id, referred_id, now, now))
            
            # تحديث عدد الإحالات للـ referrer
            cursor.execute("""
                UPDATE users 
                SET total_referrals = total_referrals + 1,
                    valid_referrals = valid_referrals + 1
                WHERE user_id = ?
            """, (referrer_id,))
            
            # إضافة لفة مجانية كل 5 إحالات
            cursor.execute("SELECT valid_referrals FROM users WHERE user_id = ?", (referrer_id,))
            result = cursor.fetchone()
            if result and result['valid_referrals'] % 5 == 0:
                cursor.execute("""
                    UPDATE users 
                    SET available_spins = available_spins + 1
                    WHERE user_id = ?
                """, (referrer_id,))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Quick referral registered: {referrer_id} -> {referred_id}")
            return jsonify({
                'success': True,
                'message': 'Referral registered successfully'
            })
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({
                'success': True,  # تغيير من False إلى True لتجنب المحاولات المكررة
                'message': 'Referral already exists'
            })
            
    except Exception as e:
        print(f"Error in register_referral: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/task/complete', methods=['POST'])
def complete_task():
    """إكمال مهمة"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        task_id = data.get('task_id')
        
        if not user_id or not task_id:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            # التحقق من أن المهمة موجودة ونشطة
            cursor.execute("SELECT * FROM tasks WHERE id = ? AND is_active = 1", (task_id,))
            task = cursor.fetchone()
            
            if not task:
                conn.close()
                return jsonify({'success': False, 'error': 'Task not found'}), 404
            
            # تسجيل إنجاز المهمة
            cursor.execute("""
                INSERT INTO user_tasks (user_id, task_id, completed_at, verified)
                VALUES (?, ?, ?, 1)
            """, (user_id, task_id, now))
            
            # إضافة المكافأة للرصيد
            cursor.execute("""
                UPDATE users 
                SET balance = balance + ?
                WHERE user_id = ?
            """, (task['reward_amount'], user_id))
            
            # التحقق من عدد المهام المكتملة
            cursor.execute("""
                SELECT COUNT(*) as count FROM user_tasks WHERE user_id = ?
            """, (user_id,))
            tasks_count = cursor.fetchone()['count']
            
            # كل 5 مهمات = لفة إضافية
            if tasks_count % 5 == 0:
                cursor.execute("""
                    UPDATE users 
                    SET available_spins = available_spins + 1
                    WHERE user_id = ?
                """, (user_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Task completed successfully',
                'reward': task['reward_amount']
            })
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'error': 'Task already completed'}), 400
            
    except Exception as e:
        print(f"Error in complete_task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/required-channels', methods=['GET'])
def get_required_channels():
    """الحصول على القنوات الإجبارية النشطة للمستخدمين"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, channel_id, channel_name, channel_url
            FROM required_channels 
            WHERE is_active = 1 
            ORDER BY added_at DESC
        """)
        
        channels = []
        for row in cursor.fetchall():
            channels.append({
                'id': row[0],
                'channel_id': row[1],
                'channel_name': row[2],
                'channel_url': row[3]
            })
        
        conn.close()
        return jsonify({
            'success': True,
            'channels': channels
        })
        
    except Exception as e:
        print(f"Error in get_required_channels: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/verify-channels', methods=['POST'])
def verify_all_channels():
    """التحقق من اشتراك المستخدم في جميع القنوات الإجبارية"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'معرف المستخدم مطلوب'}), 400
        
        # جلب القنوات النشطة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT channel_id, channel_name
            FROM required_channels 
            WHERE is_active = 1
        """)
        
        channels = cursor.fetchall()
        conn.close()
        
        if not channels:
            return jsonify({
                'success': True,
                'all_subscribed': True,
                'not_subscribed': []
            })
        
        # التحقق من كل قناة
        not_subscribed = []
        
        for channel in channels:
            channel_id = channel[0]
            channel_name = channel[1]
            
            try:
                import requests as req
                bot_url = 'http://localhost:8081/verify-subscription'
                verify_response = req.post(bot_url, json={
                    'user_id': user_id,
                    'channel_username': channel_id
                }, timeout=15)  # زيادة timeout
                
                verify_data = verify_response.json()
                
                if not verify_data.get('is_subscribed', False):
                    not_subscribed.append({
                        'channel_id': channel_id,
                        'channel_name': channel_name
                    })
                    
            except (req.exceptions.RequestException, req.exceptions.Timeout, ConnectionError) as e:
                print(f"⚠️ Bot unavailable for channel verification {channel_id}: {e}")
                # في حالة عدم توفر البوت، نفترض عدم الاشتراك لأمان أكبر
                not_subscribed.append({
                    'channel_id': channel_id,
                    'channel_name': channel_name
                })
            except Exception as e:
                print(f"Error verifying channel {channel_id}: {e}")
                not_subscribed.append({
                    'channel_id': channel_id,
                    'channel_name': channel_name
                })
        
        return jsonify({
            'success': True,
            'all_subscribed': len(not_subscribed) == 0,
            'not_subscribed': not_subscribed
        })
        
    except Exception as e:
        print(f"Error in verify_all_channels: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# 🔐 DEVICE VERIFICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/fingerprint', methods=['POST', 'OPTIONS'])
def submit_fingerprint():
    """استقبال وحفظ بصمة الجهاز من صفحة التحقق"""
    # معالجة preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response, 200
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        fp_token = data.get('fp_token')
        fingerprint = data.get('fingerprint')
        meta = data.get('meta', {})
        
        # Logging للطلب
        print(f"📥 Fingerprint request received:")
        print(f"   User ID: {user_id}")
        print(f"   Token: {fp_token}")
        print(f"   Fingerprint: {fingerprint[:16] if fingerprint else 'None'}...")
        print(f"   Origin: {request.headers.get('Origin', 'Unknown')}")
        
        if not all([user_id, fp_token, fingerprint]):
            return jsonify({
                'ok': False,
                'error': 'Missing required fields'
            }), 400
        
        # التحقق من حالة نظام التحقق
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT setting_value FROM system_settings 
            WHERE setting_key = 'verification_enabled'
        """)
        setting = cursor.fetchone()
        verification_enabled = setting['setting_value'] == 'true' if setting else True
        
        # إذا كان التحقق معطلاً، نسمح مباشرة
        if not verification_enabled:
            # تسجيل المحاولة كنجاح بدون تحقق
            cursor.execute("""
                INSERT INTO verification_attempts 
                (user_id, fingerprint, ip_address, attempt_time, status, reason)
                VALUES (?, ?, ?, datetime('now'), 'bypassed', 'verification_disabled')
            """, (user_id, fingerprint, request.remote_addr))
            
            cursor.execute("""
                INSERT OR REPLACE INTO device_verifications 
                (user_id, fingerprint, ip_address, user_agent, timezone, 
                screen_resolution, canvas_fp, audio_fp, local_id, verified_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                user_id, fingerprint, request.remote_addr,
                meta.get('user_agent'), meta.get('timezone'),
                meta.get('resolution'), meta.get('canvas_fp'),
                meta.get('audio_fp'), meta.get('local_id')
            ))
            
            conn.commit()
            conn.close()
            
            # إشعار البوت
            try:
                import requests as req
                bot_notify_url = 'http://localhost:8081/device-verified'
                req.post(bot_notify_url, json={'user_id': user_id}, timeout=10)
            except (req.exceptions.RequestException, req.exceptions.Timeout, ConnectionError):
                print(f"⚠️ Bot unavailable for verification notification (user {user_id})")
            except Exception as e:
                print(f"⚠️ Could not notify bot: {e}")
            
            return jsonify({
                'ok': True,
                'message': 'تم التحقق بنجاح (التحقق معطل)'
            })
        
        # استكمال التحقق العادي إذا كان مفعلاً
        # 🔐 التحقق من صلاحية الـ token والتأكد من أنه يخص نفس المستخدم
        cursor.execute("""
            SELECT * FROM verification_tokens 
            WHERE user_id = ? AND token = ? AND used = 0
            AND datetime(expires_at) > datetime('now')
        """, (user_id, fp_token))
        
        token_row = cursor.fetchone()
        
        # ✅ Validation إضافي: التأكد من أن user_id الذي يستخدم التوكن هو نفسه الذي أُنشئ له
        if not token_row:
            # محاولة اكتشاف تلاعب: هل التوكن موجود لمستخدم آخر؟
            cursor.execute("""
                SELECT user_id FROM verification_tokens 
                WHERE token = ?
            """, (fp_token,))
            
            other_token = cursor.fetchone()
            if other_token and other_token['user_id'] != user_id:
                # 🚨 محاولة استخدام token مسروق!
                print(f"🚨 SECURITY ALERT: User {user_id} tried to use token belonging to user {other_token['user_id']}")
                
                # تسجيل المحاولة المشبوهة
                cursor.execute("""
                    INSERT INTO verification_attempts 
                    (user_id, fingerprint, ip_address, attempt_time, status, reason)
                    VALUES (?, ?, ?, datetime('now'), 'rejected', 'stolen_token_attempt')
                """, (user_id, fingerprint, ip_address))
                
                # حظر المستخدم المُتلاعب
                ban_reason = 'محاولة استخدام token مسروق - تلاعب مكتشف'
                cursor.execute("""
                    UPDATE users 
                    SET is_banned = 1, ban_reason = ?
                    WHERE user_id = ?
                """, (ban_reason, user_id))
                
                conn.commit()
                conn.close()
                
                return jsonify({
                    'ok': False,
                    'error': 'Token validation failed - Suspicious activity detected'
                }), 403
            
            # توكن غير موجود أو منتهي الصلاحية
            conn.close()
            return jsonify({
                'ok': False,
                'error': 'Invalid or expired token'
            }), 403
        
        # ✅ التوكن صحيح ومملوك للمستخدم الصحيح
        # تحديد التوكن كمستخدم لمنع إعادة الاستخدام
        cursor.execute("""
            UPDATE verification_tokens 
            SET used = 1 
            WHERE token = ?
        """, (fp_token,))
        
        # الحصول على IP address
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0]
        else:
            ip_address = request.remote_addr
        
        # التحقق من عدم وجود جهاز آخر بنفس البصمة
        cursor.execute("""
            SELECT user_id FROM device_verifications 
            WHERE fingerprint = ? AND user_id != ?
        """, (fingerprint, user_id))
        
        duplicate_device = cursor.fetchone()
        if duplicate_device:
            # تسجيل المحاولة الفاشلة
            cursor.execute("""
                INSERT INTO verification_attempts 
                (user_id, fingerprint, ip_address, attempt_time, status, reason)
                VALUES (?, ?, ?, datetime('now'), 'rejected', 'duplicate_device')
            """, (user_id, fingerprint, ip_address))
            
            # حظر المستخدم وحفظ السبب
            ban_reason = 'تم اكتشاف حسابات متعددة - جهاز مسجل مسبقاً'
            cursor.execute("""
                UPDATE users 
                SET is_banned = 1, ban_reason = ?
                WHERE user_id = ?
            """, (ban_reason, user_id))
            
            conn.commit()
            conn.close()
            
            # إرسال إشعار للبوت عن المستخدم المحظور
            try:
                import requests as req
                bot_notify_url = 'http://localhost:8081/user-banned'
                req.post(bot_notify_url, json={
                    'user_id': user_id,
                    'reason': 'duplicate_device',
                    'ban_reason': ban_reason
                }, timeout=3)
            except Exception as notify_error:
                print(f"⚠️ Could not notify bot about ban: {notify_error}")
            
            return jsonify({
                'ok': False,
                'error': 'هذا الجهاز مسجل بالفعل لمستخدم آخر',
                'reason': 'duplicate_device'
            }), 403
        
        # التحقق من عدم وجود IP address مكرر (اختياري - يمكن تعطيله)
        cursor.execute("""
            SELECT COUNT(*) FROM device_verifications 
            WHERE ip_address = ? AND user_id != ?
        """, (ip_address, user_id))
        
        ip_count = cursor.fetchone()[0]
        if ip_count >= 3:  # السماح بـ 3 أجهزة كحد أقصى من نفس الـ IP
            cursor.execute("""
                INSERT INTO verification_attempts 
                (user_id, fingerprint, ip_address, attempt_time, status, reason)
                VALUES (?, ?, ?, datetime('now'), 'rejected', 'ip_limit_exceeded')
            """, (user_id, fingerprint, ip_address))
            
            # حظر المستخدم وحفظ السبب
            ban_reason = 'تم اكتشاف حسابات متعددة - تجاوز الحد الأقصى للأجهزة من نفس الشبكة'
            cursor.execute("""
                UPDATE users 
                SET is_banned = 1, ban_reason = ?
                WHERE user_id = ?
            """, (ban_reason, user_id))
            
            conn.commit()
            conn.close()
            
            # إرسال إشعار للبوت عن المستخدم المحظور
            try:
                import requests as req
                bot_notify_url = 'http://localhost:8081/user-banned'
                req.post(bot_notify_url, json={
                    'user_id': user_id,
                    'reason': 'ip_limit_exceeded',
                    'ban_reason': ban_reason
                }, timeout=3)
            except Exception as notify_error:
                print(f"⚠️ Could not notify bot about ban: {notify_error}")
            
            return jsonify({
                'ok': False,
                'error': 'تم تجاوز الحد الأقصى للأجهزة من نفس الشبكة',
                'reason': 'ip_limit_exceeded'
            }), 403
        
        # حفظ بيانات التحقق
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO device_verifications 
            (user_id, fingerprint, ip_address, user_agent, timezone, 
             screen_resolution, canvas_fp, audio_fp, local_id, verified_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, fingerprint, ip_address,
            meta.get('ua', ''),
            meta.get('tz', ''),
            meta.get('rez', ''),
            meta.get('cfp', ''),
            meta.get('afp', ''),
            meta.get('lid', ''),
            now, now
        ))
        
        # تحديث حالة المستخدم
        cursor.execute("""
            UPDATE users 
            SET is_device_verified = 1, verification_required = 0
            WHERE user_id = ?
        """, (user_id,))
        
        # تسجيل المحاولة الناجحة
        cursor.execute("""
            INSERT INTO verification_attempts 
            (user_id, fingerprint, ip_address, attempt_time, status, reason)
            VALUES (?, ?, ?, datetime('now'), 'success', 'verified')
        """, (user_id, fingerprint, ip_address))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Device verified for user {user_id}")
        
        # إرسال إشعار للبوت للتحقق من الإحالة إن وجدت
        try:
            import requests as req
            bot_notify_url = 'http://localhost:8081/device-verified'
            req.post(bot_notify_url, json={'user_id': user_id}, timeout=10)
        except (req.exceptions.RequestException, req.exceptions.Timeout, ConnectionError) as notify_error:
            print(f"⚠️ Bot unavailable for device verification notification: {notify_error}")
        except Exception as notify_error:
            print(f"⚠️ Could not notify bot: {notify_error}")
        
        return jsonify({
            'ok': True,
            'message': 'تم التحقق من جهازك بنجاح'
        })
        
    except Exception as e:
        print(f"❌ Error in submit_fingerprint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'ok': False,
            'error': 'حدث خطأ أثناء التحقق'
        }), 500

@app.route('/api/verification/create-token', methods=['POST'])
def create_verification_token():
    """إنشاء token للتحقق من الجهاز"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID required'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حذف التوكنات القديمة غير المستخدمة لهذا المستخدم
        cursor.execute("""
            DELETE FROM verification_tokens 
            WHERE user_id = ? AND used = 0
        """, (user_id,))
        
        # إنشاء token عشوائي
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires_at = (now + timedelta(minutes=15)).isoformat()
        
        cursor.execute("""
            INSERT INTO verification_tokens 
            (user_id, token, created_at, expires_at, used)
            VALUES (?, ?, ?, ?, 0)
        """, (user_id, token, now.isoformat(), expires_at))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'token': token,
            'expires_in': 900  # 15 minutes in seconds
        })
        
    except Exception as e:
        print(f"Error in create_verification_token: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/verification/get-token', methods=['POST'])
@require_telegram_auth
def get_verification_token(authenticated_user_id=None, is_admin=False):
    """
    🔐 الحصول على token التحقق بشكل آمن
    يستخدم Telegram authentication للتحقق من هوية المستخدم
    ❌ لا يمكن نسخ التوكن لأنه لا يظهر في الرابط
    """
    try:
        # استخدام user_id المُصادق عليه من Telegram فقط
        user_id = authenticated_user_id
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'Unauthorized - Invalid Telegram authentication'
            }), 401
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن token صالح لهذا المستخدم
        cursor.execute("""
            SELECT token, expires_at, used 
            FROM verification_tokens 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (user_id,))
        
        token_row = cursor.fetchone()
        conn.close()
        
        if not token_row:
            return jsonify({
                'success': False,
                'error': 'No token found - Please request verification from bot'
            }), 404
        
        # التحقق من صلاحية التوكن
        expires_at = datetime.fromisoformat(token_row['expires_at'])
        now = datetime.now()
        
        if now > expires_at:
            return jsonify({
                'success': False,
                'error': 'Token expired - Please request new verification'
            }), 410
        
        if token_row['used'] == 1:
            return jsonify({
                'success': False,
                'error': 'Token already used'
            }), 410
        
        # ✅ إرجاع التوكن بشكل آمن
        return jsonify({
            'success': True,
            'token': token_row['token'],
            'expires_at': token_row['expires_at']
        })
        
    except Exception as e:
        print(f"Error in get_verification_token: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/verification/status/<int:user_id>', methods=['GET'])
def get_verification_status(user_id):
    """التحقق من حالة تحقق المستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود تحقق للمستخدم
        cursor.execute("""
            SELECT * FROM device_verifications 
            WHERE user_id = ?
        """, (user_id,))
        
        verification = cursor.fetchone()
        
        if verification:
            result = {
                'verified': True,
                'fingerprint': verification['fingerprint'],
                'ip_address': verification['ip_address'],
                'verified_at': verification['verified_at'],
                'is_blocked': bool(verification['is_blocked'])
            }
        else:
            result = {
                'verified': False,
                'fingerprint': None,
                'ip_address': None,
                'verified_at': None,
                'is_blocked': False
            }
        
        conn.close()
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        print(f"Error in get_verification_status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/channels', methods=['GET', 'POST', 'DELETE'])
@require_telegram_auth
@require_admin_auth
def manage_channels(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إدارة القنوات الإجبارية"""
    try:
        if request.method == 'GET':
            # Get all required channels
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM required_channels 
                WHERE is_active = 1 
                ORDER BY added_at DESC
            """)
            channels = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify({'success': True, 'channels': channels})
        
        elif request.method == 'POST':
            # Add new channel
            data = request.get_json()
            channel_id = data.get('channel_id')
            channel_name = data.get('channel_name')
            channel_url = data.get('channel_url')
            is_active = 1 if data.get('is_active', True) else 0
            admin_id = data.get('admin_id', 1797127532)
            
            if not all([channel_id, channel_name, channel_url]):
                return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'}), 400
            
            # التحقق من أن البوت مشرف في القناة
            try:
                import requests as req
                bot_url = 'http://localhost:8081/check-bot-admin'
                check_response = req.post(bot_url, json={
                    'channel_username': channel_id
                }, timeout=5)
                
                check_data = check_response.json()
                
                if not check_data.get('is_admin', False):
                    return jsonify({
                        'success': False,
                        'message': '❌ البوت ليس مشرف في هذه القناة! أضف البوت كمشرف أولاً'
                    }), 400
            except Exception as e:
                print(f"Error checking bot admin: {e}")
                # نكمل حتى لو فشل التحقق
                pass
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            try:
                cursor.execute("""
                    INSERT INTO required_channels (channel_id, channel_name, channel_url, added_by, added_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (channel_id, channel_name, channel_url, admin_id, now, is_active))
                
                conn.commit()
                conn.close()
                
                return jsonify({'success': True, 'message': 'تم إضافة القناة بنجاح'})
            except sqlite3.IntegrityError:
                conn.close()
                return jsonify({'success': False, 'message': 'القناة موجودة بالفعل'}), 400
        
        elif request.method == 'DELETE':
            # Delete channel
            channel_id = request.args.get('channel_id')
            if not channel_id:
                return jsonify({'success': False, 'message': 'معرف القناة مطلوب'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE required_channels 
                SET is_active = 0 
                WHERE channel_id = ?
            """, (channel_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'تم حذف القناة بنجاح'})
            
    except Exception as e:
        print(f"Error in manage_channels: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/tasks', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_telegram_auth
@require_admin_auth
def manage_tasks(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إدارة المهام"""
    try:
        if request.method == 'GET':
            # جلب جميع المهام للإدمن
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, task_type, task_name, task_description, task_link, 
                       channel_username, is_pinned, is_active, added_at
                FROM tasks
                ORDER BY is_pinned DESC, added_at DESC
            """)
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'task_type': row[1],
                    'task_name': row[2],
                    'task_description': row[3],
                    'task_link': row[4],
                    'channel_username': row[5],
                    'is_pinned': row[6],
                    'is_active': row[7],
                    'added_at': row[8]
                })
            
            conn.close()
            return jsonify({'success': True, 'tasks': tasks})
            
        elif request.method == 'POST':
            # إضافة مهمة جديدة
            data = request.get_json()
            
            task_name = data.get('task_name')
            task_link = data.get('task_link')
            task_type = data.get('task_type', 'link')
            task_description = data.get('task_description', '')
            channel_username = data.get('channel_username', '')
            is_pinned = 1 if data.get('is_pinned', False) else 0
            is_active = 1 if data.get('is_active', True) else 0
            
            # التحقق من البيانات المطلوبة
            if not task_name or not task_link:
                return jsonify({
                    'success': False, 
                    'message': 'اسم المهمة والرابط مطلوبان'
                }), 400
            
            # إذا كان نوع المهمة قناة، التحقق من أن البوت مشرف
            if task_type == 'channel' and channel_username:
                try:
                    import requests
                    bot_url = 'http://localhost:8081/check-bot-admin'
                    check_response = requests.post(bot_url, json={
                        'channel_username': channel_username
                    }, timeout=5)
                    
                    check_data = check_response.json()
                    
                    if not check_data.get('is_admin', False):
                        return jsonify({
                            'success': False,
                            'message': '❌ البوت ليس مشرف في هذه القناة! أضف البوت كمشرف أولاً'
                        }), 400
                except Exception as e:
                    print(f"Error checking bot admin: {e}")
                    # نكمل حتى لو فشل التحقق
                    pass
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            # افتراض admin_id = 1797127532 (يمكن تحديثه من Telegram WebApp)
            admin_id = 1797127532
            
            cursor.execute("""
                INSERT INTO tasks (
                    task_type, task_name, task_description, task_link, 
                    channel_username, is_pinned, is_active, 
                    added_by, added_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_type, task_name, task_description, task_link,
                channel_username, is_pinned, is_active,
                admin_id, now
            ))
            
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'تم إضافة المهمة بنجاح',
                'task_id': task_id
            })
            
        elif request.method == 'PUT':
            # تحديث مهمة موجودة
            data = request.get_json()
            
            task_id = data.get('task_id')
            if not task_id:
                return jsonify({'success': False, 'message': 'معرف المهمة مطلوب'}), 400
            
            task_name = data.get('task_name')
            task_link = data.get('task_link')
            task_type = data.get('task_type', 'link')
            task_description = data.get('task_description', '')
            channel_username = data.get('channel_username', '')
            is_pinned = 1 if data.get('is_pinned', False) else 0
            is_active = 1 if data.get('is_active', True) else 0
            
            # التحقق من البيانات المطلوبة
            if not task_name or not task_link:
                return jsonify({
                    'success': False, 
                    'message': 'اسم المهمة والرابط مطلوبان'
                }), 400
            
            # إذا كان نوع المهمة قناة، التحقق من أن البوت مشرف
            if task_type == 'channel' and channel_username:
                try:
                    import requests
                    bot_url = 'http://localhost:8081/check-bot-admin'
                    check_response = requests.post(bot_url, json={
                        'channel_username': channel_username
                    }, timeout=5)
                    
                    check_data = check_response.json()
                    
                    if not check_data.get('is_admin', False):
                        return jsonify({
                            'success': False,
                            'message': '❌ البوت ليس مشرف في هذه القناة! أضف البوت كمشرف أولاً'
                        }), 400
                except Exception as e:
                    print(f"Error checking bot admin: {e}")
                    # نكمل حتى لو فشل التحقق
                    pass
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE tasks 
                SET task_type = ?, task_name = ?, task_description = ?, 
                    task_link = ?, channel_username = ?, is_pinned = ?, is_active = ?
                WHERE id = ?
            """, (
                task_type, task_name, task_description, task_link,
                channel_username, is_pinned, is_active, task_id
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': 'تم تحديث المهمة بنجاح'
            })
            
        elif request.method == 'DELETE':
            # حذف مهمة
            task_id = request.args.get('task_id')
            if not task_id:
                return jsonify({'success': False, 'message': 'معرف المهمة مطلوب'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # تعطيل المهمة بدلاً من حذفها
            cursor.execute("""
                UPDATE tasks 
                SET is_active = 0 
                WHERE id = ?
            """, (task_id,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'تم تعطيل المهمة'})
            
    except Exception as e:
        print(f"Error in manage_tasks: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'خطأ في السيرفر: {str(e)}'}), 500

# ═══════════════════════════════════════════════════════════════
# 🎁 WHEEL PRIZES MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/prizes', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_telegram_auth
@require_admin_auth
def manage_prizes(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إدارة جوائز العجلة"""
    try:
        if request.method == 'GET':
            # Get all active prizes
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wheel_prizes 
                WHERE is_active = 1 
                ORDER BY position ASC
            """)
            prizes = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify({'success': True, 'data': prizes})
        
        elif request.method == 'POST':
            # Add new prize
            data = request.get_json()
            name = data.get('name')
            value = data.get('value')
            probability = data.get('probability')
            position = data.get('position', 0)
            
            # 🎨 اللون والإيموجي اختياري الآن (قيم افتراضية)
            color = data.get('color', '#808080')  # رمادي افتراضي
            emoji = data.get('emoji', '🎁')  # 🎁 افتراضي
            
            if not all([name, value is not None, probability is not None]):
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (name, value, probability, color, emoji, position, now))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Prize added successfully'})
        
        elif request.method == 'PUT':
            # Update prize
            data = request.get_json()
            prize_id = data.get('id')
            name = data.get('name')
            value = data.get('value')
            probability = data.get('probability')
            position = data.get('position', 0)
            
            # 🎨 اللون والإيموجي اختياري الآن (قيم افتراضية)
            color = data.get('color', '#808080')
            emoji = data.get('emoji', '🎁')
            
            if not prize_id:
                return jsonify({'success': False, 'error': 'Prize ID required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                UPDATE wheel_prizes 
                SET name = ?, value = ?, probability = ?, color = ?, emoji = ?, position = ?, updated_at = ?
                WHERE id = ?
            """, (name, value, probability, color, emoji, position, now, prize_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Prize updated successfully'})
        
        elif request.method == 'DELETE':
            # Delete prize
            prize_id = request.args.get('id')
            if not prize_id:
                return jsonify({'success': False, 'error': 'Prize ID required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE wheel_prizes 
                SET is_active = 0 
                WHERE id = ?
            """, (prize_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Prize removed'})
            
    except Exception as e:
        print(f"Error in manage_prizes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/reset-prizes', methods=['POST'])
@require_telegram_auth
@require_admin_auth
def reset_prizes_to_default(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إعادة تعيين الجوائز إلى القيم الافتراضية"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # حذف جميع الجوائز الحالية
        cursor.execute("DELETE FROM wheel_prizes")
        
        # إضافة الجوائز الافتراضية (مطابقة لـ config.js)
        now = datetime.now().isoformat()
        default_prizes = [
            ('0.05 TON', 0.05, 94, '#4CAF50', '🎯', 0),
            ('0.1 TON', 0.1, 5, '#2196F3', '💎', 1),
            ('0.15 TON', 0.15, 1, '#FF9800', '⭐', 2),
            ('0.5 TON', 0.5, 0, '#9C27B0', '🌟', 3),
            ('1.0 TON', 1.0, 0, '#FFD700', '💰', 4),
            ('0.25 TON', 0.25, 0, '#E91E63', '✨', 5)
        ]
        
        for name, value, prob, color, emoji, pos in default_prizes:
            cursor.execute("""
                INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (name, value, prob, color, emoji, pos, now))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'تم إعادة تعيين الجوائز إلى القيم الافتراضية بنجاح',
            'count': len(default_prizes)
        })
        
    except Exception as e:
        print(f"Error in reset_prizes_to_default: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# 👤 ADD SPINS TO USER
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/add-spins', methods=['POST'])
@require_telegram_auth
@require_admin_auth
def add_spins_to_user(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إضافة لفات لمستخدم معين"""
    try:
        data = request.get_json()
        username = data.get('username')
        spins_count = data.get('spins_count')
        admin_id = data.get('admin_id')
        
        if not all([username, spins_count, admin_id]):
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        # Remove @ if present
        username = username.replace('@', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find user by username
        cursor.execute("SELECT user_id, username FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user_id = user['user_id']
        
        # Add spins
        cursor.execute("""
            UPDATE users 
            SET available_spins = available_spins + ?
            WHERE user_id = ?
        """, (spins_count, user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Added {spins_count} spins to @{username}',
            'user_id': user_id
        })
        
    except Exception as e:
        print(f"Error in add_spins_to_user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# 👥 USERS LIST FOR ADMIN
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/users', methods=['GET'])
@require_telegram_auth
@require_admin_auth
def get_all_users(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """جلب جميع المستخدمين للأدمن"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                user_id,
                username,
                full_name,
                balance,
                available_spins as spins,
                total_referrals as referrals,
                created_at as joined,
                is_banned,
                ban_reason,
                is_device_verified
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row['user_id'],
                'name': row['full_name'] or 'Unknown',
                'username': f"@{row['username']}" if row['username'] else f"user_{row['user_id']}",
                'balance': row['balance'] or 0,
                'spins': row['spins'] or 0,
                'referrals': row['referrals'] or 0,
                'joined': row['joined'],
                'is_banned': bool(row['is_banned']),
                'ban_reason': row['ban_reason'] or '',
                'is_verified': bool(row['is_device_verified'])
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': users,
            'count': len(users)
        })
        
    except Exception as e:
        print(f"Error getting users: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# � ADMIN ADVANCED STATISTICS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/advanced-stats', methods=['GET'])
@require_telegram_auth
@require_admin_auth
def get_advanced_stats(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إحصائيات متقدمة للأدمن"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إجمالي المستخدمين
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        # المستخدمين النشطين (غير محظورين)
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE is_banned = 0")
        active_users = cursor.fetchone()['active']
        
        # المستخدمين المحظورين
        cursor.execute("SELECT COUNT(*) as banned FROM users WHERE is_banned = 1")
        banned_users = cursor.fetchone()['banned']
        
        # المستخدمين المتحقق منهم (بالجهاز)
        cursor.execute("SELECT COUNT(*) as verified FROM users WHERE is_device_verified = 1")
        verified_users = cursor.fetchone()['verified']
        
        # إجمالي عمليات الحظر
        cursor.execute("SELECT COUNT(*) as total_bans FROM users WHERE is_banned = 1")
        total_bans = cursor.fetchone()['total_bans']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'active_users': active_users,
                'banned_users': banned_users,
                'verified_users': verified_users,
                'total_bans': total_bans
            }
        })
        
    except Exception as e:
        print(f"Error getting advanced stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# ✅ UNBAN USER - ALLOW ACCESS WITHOUT VERIFICATION
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/unban-user', methods=['POST'])
@require_telegram_auth
@require_admin_auth
def unban_user(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """إلغاء حظر مستخدم والسماح له بالوصول بدون تحقق"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # إلغاء الحظر وتعيين أنه متحقق منه لتجنب التحقق مرة أخرى
        cursor.execute("""
            UPDATE users 
            SET is_banned = 0,
                ban_reason = NULL,
                is_device_verified = 1,
                last_active = ?
            WHERE user_id = ?
        """, (now, user_id))
        
        # حذف سجلات التحقق القديمة
        cursor.execute("DELETE FROM device_verifications WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'تم إلغاء الحظر والسماح للمستخدم بالوصول'
        })
        
    except Exception as e:
        print(f"Error unbanning user: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# �👥 USER REFERRALS FOR ADMIN
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/user-referrals', methods=['GET'])
@require_telegram_auth
@require_admin_auth
def get_admin_user_referrals(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """جلب إحالات مستخدم معين للأدمن"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب الإحالات
        cursor.execute("""
            SELECT 
                u.user_id as id,
                u.username,
                u.full_name as name,
                r.created_at as joined_at,
                r.is_valid
            FROM referrals r
            JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,))
        
        referrals = []
        for row in cursor.fetchall():
            referrals.append({
                'id': row['id'],
                'username': f"@{row['username']}" if row['username'] else f"user_{row['id']}",
                'name': row['name'],
                'joined_at': row['joined_at'],
                'is_valid': row['is_valid']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': referrals
        })
        
    except Exception as e:
        print(f"❌ Error in get_admin_user_referrals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# ⚙️ SYSTEM SETTINGS - التحكم في التحقق من التعدد
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/verification-settings', methods=['GET', 'POST'])
@require_telegram_auth
@require_admin_auth
def verification_settings(authenticated_user_id, is_admin, admin_username=None, admin_user_id=None):
    """الحصول على/تحديث إعدادات التحقق من التعدد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # جلب الإعدادات الحالية
            cursor.execute("""
                SELECT setting_value FROM system_settings 
                WHERE setting_key = 'verification_enabled'
            """)
            result = cursor.fetchone()
            is_enabled = result['setting_value'] == 'true' if result else True
            
            conn.close()
            return jsonify({
                'success': True,
                'verification_enabled': is_enabled
            })
        
        elif request.method == 'POST':
            # تحديث الإعدادات
            data = request.get_json()
            new_status = data.get('enabled', True)
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, updated_at, updated_by)
                VALUES ('verification_enabled', ?, ?, ?)
            """, ('true' if new_status else 'false', datetime.now().isoformat(), authenticated_user_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f"تم {'تفعيل' if new_status else 'إيقاف'} التحقق من التعدد بنجاح",
                'verification_enabled': new_status
            })
    
    except Exception as e:
        print(f"❌ Error in verification_settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# ⚙️ BOT SETTINGS API
# ═══════════════════════════════════════════════════════════════

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """الحصول على إعدادات البوت"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # جلب جميع الإعدادات
        cursor.execute("SELECT setting_key, setting_value FROM bot_settings")
        settings_rows = cursor.fetchall()
        
        settings = {}
        for row in settings_rows:
            settings[row['setting_key']] = row['setting_value']
        
        conn.close()
        
        # إضافة قيم افتراضية للإعدادات الأخرى
        return jsonify({
            'success': True,
            'data': {
                'auto_withdrawal_enabled': settings.get('auto_withdrawal_enabled', 'false') == 'true',
                'min_withdrawal': 0.1,
                'max_withdrawal': 100.0
            }
        })
        
    except Exception as e:
        print(f"Error getting settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """تحديث إعدادات البوت"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # تحديث السحب التلقائي
        if 'auto_withdrawal_enabled' in data:
            auto_withdrawal = 'true' if data['auto_withdrawal_enabled'] else 'false'
            cursor.execute("""
                INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
                VALUES ('auto_withdrawal_enabled', ?, ?)
            """, (auto_withdrawal, now))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Settings updated: {data}")
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الإعدادات بنجاح'
        })
        
    except Exception as e:
        print(f"Error updating settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 🏥 HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

@app.route('/health')
def health():
    """Health check لـ Render"""
    return {'status': 'ok', 'service': 'Panda Giveaways Mini App'}, 200

# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

