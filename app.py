"""
🌐 Flask Server لخدمة Mini App على Render
"""
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import sys
import sqlite3
from datetime import datetime
import threading
import subprocess
import random
import hashlib
import requests  # لجلب سعر TON

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
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8481889290:AAHpTFQYm-261ra5lu4HXVsjYNmCp7uHqqk')
ADMIN_IDS = [1797127532, 6603009212]

def send_withdrawal_notification_to_admin(user_id, username, full_name, amount, withdrawal_type, wallet_address, phone_number, withdrawal_id):
    """إرسال إشعار للأدمن في البوت عند طلب سحب"""
    try:
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
            """
        else:
            message = f"""
🆕 <b>طلب سحب جديد - TON Wallet</b>

👤 <b>المستخدم:</b> {full_name}
🆔 <b>ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{username if username else 'N/A'}

💰 <b>المبلغ:</b> {amount} TON
💳 <b>عنوان المحفظة:</b>
<code>{wallet_address}</code>

⏰ <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔢 <b>رقم الطلب:</b> #{withdrawal_id}
            """
        
        # إنشاء أزرار inline keyboard
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

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)  # السماح بـ CORS

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
        default_prizes = [
            ('0.01 TON', 0.01, 30, '#9370db', '🪙', 0),
            ('0.05 TON', 0.05, 10, '#00bfff', '💎', 1),
            ('0.1 TON', 0.1, 5, '#ffa500', '💰', 2),
            ('0.2 TON', 0.2, 3, '#ff6347', '🎁', 3),
            ('0.5 TON', 0.5, 1, '#32cd32', '🏆', 4),
            ('1.0 TON', 1.0, 0.5, '#ff1493', '👑', 5),
            ('حظ أوفر', 0, 50.5, '#808080', '😔', 6)
        ]
        for name, value, prob, color, emoji, pos in default_prizes:
            cursor.execute("""
                INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (name, value, prob, color, emoji, pos, now))
    
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
# 🌐 ROUTES - Static Files
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return send_from_directory('public', 'index.html')

@app.route('/admin')
def admin():
    """صفحة الأدمن - محمية للأدمن فقط"""
    # الحصول على user_id من query params
    user_id = request.args.get('user_id')
    
    # قائمة الأدمن
    ADMIN_IDS = [1797127532, 6603009212]
    
    # التحقق من أن الطلب من Telegram
    if not user_id:
        return jsonify({
            'error': 'غير مسموح! هدا الصفحة تعمل فقط من خلال Telegram Bot',
            'message': 'Access Denied: This page only works through Telegram Mini App'
        }), 403
    
    # التحقق من أن المستخدم أدمن
    try:
        user_id_int = int(user_id)
        if user_id_int not in ADMIN_IDS:
            return jsonify({
                'error': 'غير مسموح! هده الصفحة للمسؤولين فقط',
                'message': 'Access Denied: Admin only',
                'your_id': user_id_int
            }), 403
    except ValueError:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    return send_from_directory('public', 'admin.html')

@app.route('/<path:path>')
def serve_static(path):
    """خدمة الملفات الثابتة (CSS, JS, Images)"""
    return send_from_directory('public', path)

# ═══════════════════════════════════════════════════════════════
# 🔌 API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_data(user_id):
    """الحصول على بيانات المستخدم"""
    try:
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
def update_user_profile(user_id):
    """تحديث username و full_name للمستخدم من Telegram"""
    try:
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
def get_user_referrals(user_id):
    """الحصول على إحالات المستخدم"""
    try:
        referrals = get_user_referrals_db(user_id)
        return jsonify({
            'success': True,
            'data': referrals
        })
    except Exception as e:
        print(f"Error in get_user_referrals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/<int:user_id>/spins', methods=['GET'])
def get_user_spins(user_id):
    """الحصول على تاريخ لفات المستخدم"""
    try:
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
def perform_spin():
    """تنفيذ لفة العجلة"""
    import random
    import hashlib
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
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
        
        # Define prizes with probabilities
        prizes = [
            {'name': '0.01 TON', 'amount': 0.01, 'probability': 40, 'color': '#ffa500', 'emoji': '🪙'},
            {'name': '0.05 TON', 'amount': 0.05, 'probability': 25, 'color': '#4a9eff', 'emoji': '💎'},
            {'name': '0.1 TON', 'amount': 0.1, 'probability': 15, 'color': '#66bb6a', 'emoji': '💰'},
            {'name': '0.5 TON', 'amount': 0.5, 'probability': 10, 'color': '#ef5350', 'emoji': '🎁'},
            {'name': '1.0 TON', 'amount': 1.0, 'probability': 5, 'color': '#ab47bc', 'emoji': '🏆'},
            {'name': 'حظ أوفر', 'amount': 0.0, 'probability': 5, 'color': '#90a4ae', 'emoji': '😔'}
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
def get_user_completed_tasks(user_id):
    """الحصول على المهام المكتملة للمستخدم"""
    try:
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
                # إرسال طلب للبوت للتحقق من الاشتراك
                import requests
                bot_url = 'http://localhost:8081/verify-subscription'
                verify_response = requests.post(bot_url, json={
                    'user_id': user_id,
                    'channel_username': channel_username
                }, timeout=5)
                
                verify_data = verify_response.json()
                
                if not verify_data.get('is_subscribed', False):
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'message': '❌ لم يتم العثور على اشتراكك! تأكد من الاشتراك في القناة أولاً'
                    })
                    
            except Exception as e:
                print(f"Error verifying subscription: {e}")
                conn.close()
                return jsonify({
                    'success': False,
                    'message': '❌ خطأ في التحقق من الاشتراك. حاول مرة أخرى'
                })
        
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
def get_user_withdrawals(user_id):
    """الحصول على طلبات السحب للمستخدم"""
    try:
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
def request_withdrawal():
    """طلب سحب جديد"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
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
        
        # التحقق من تفعيل السحب التلقائي
        conn_check = get_db_connection()
        cursor_check = conn_check.cursor()
        cursor_check.execute("SELECT setting_value FROM bot_settings WHERE setting_key = 'auto_withdrawal_enabled'")
        auto_withdrawal_row = cursor_check.fetchone()
        conn_check.close()
        
        auto_withdrawal_enabled = auto_withdrawal_row and auto_withdrawal_row['setting_value'] == 'true' if auto_withdrawal_row else False
        
        # إذا كان السحب التلقائي مفعّل ونوع السحب TON
        if auto_withdrawal_enabled and withdrawal_type.upper() == 'TON' and wallet_address:
            print(f"🚀 Auto-withdrawal is enabled! Processing withdrawal #{withdrawal_id} automatically...")
            try:
                # استدعاء endpoint البوت لمعالجة السحب التلقائي
                import requests
                bot_api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
                
                # إرسال أمر خاص للبوت لمعالجة السحب تلقائياً
                requests.post(bot_api_url, json={
                    'chat_id': ADMIN_IDS[0],  # إرسال للأدمن الأول
                    'text': f'🤖 AUTO_PROCESS_WITHDRAWAL_{withdrawal_id}'
                }, timeout=5)
                
                print(f"✅ Auto-withdrawal request sent for withdrawal #{withdrawal_id}")
            except Exception as auto_error:
                print(f"⚠️ Auto-withdrawal trigger failed: {auto_error}")
        
        # إرسال إشعار للأدمن في البوت
        try:
            send_withdrawal_notification_to_admin(
                user_id=user_id,
                username=user['username'],
                full_name=user['full_name'],
                amount=amount,
                withdrawal_type=withdrawal_type,
                wallet_address=wallet_address,
                phone_number=phone_number,
                withdrawal_id=withdrawal_id
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
    """تسجيل إحالة جديدة"""
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
            
            return jsonify({
                'success': True,
                'message': 'Referral registered successfully'
            })
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Referral already exists'
            }), 400
            
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
                }, timeout=5)
                
                verify_data = verify_response.json()
                
                if not verify_data.get('is_subscribed', False):
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

@app.route('/api/admin/channels', methods=['GET', 'POST', 'DELETE'])
def manage_channels():
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
def manage_tasks():
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
def manage_prizes():
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
            color = data.get('color')
            emoji = data.get('emoji')
            position = data.get('position', 0)
            
            if not all([name, value is not None, probability is not None, color, emoji]):
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
            color = data.get('color')
            emoji = data.get('emoji')
            position = data.get('position', 0)
            
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

# ═══════════════════════════════════════════════════════════════
# 👤 ADD SPINS TO USER
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/add-spins', methods=['POST'])
def add_spins_to_user():
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
def get_all_users():
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
                is_banned
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
                'is_banned': bool(row['is_banned'])
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
# 👥 USER REFERRALS FOR ADMIN
# ═══════════════════════════════════════════════════════════════

@app.route('/api/admin/user-referrals', methods=['GET'])
def get_admin_user_referrals():
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
                'name': row['name'] or 'Unknown',
                'joined_at': row['joined_at'],
                'is_verified': bool(row['is_valid'])
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': referrals,
            'count': len(referrals)
        })
        
    except Exception as e:
        print(f"Error in get_admin_user_referrals: {e}")
        import traceback
        traceback.print_exc()
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
    port = int(os.environ.get('PORT', 8080))
    print(f"🌐 Starting Flask Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

