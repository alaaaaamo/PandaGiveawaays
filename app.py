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

# إضافة المسار الحالي لـ Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
if os.environ.get('RENDER'):
    # على Render، شغل البوت في الخلفية
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    print("🎉 Bot thread started on Render")

# ═══════════════════════════════════════════════════════════════
# 🗄️ DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════

DATABASE_PATH = os.getenv('DATABASE_PATH', 'panda_giveaways.db')

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
            channel_id TEXT,
            link_url TEXT,
            reward_amount REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            added_by INTEGER NOT NULL,
            added_at TEXT NOT NULL
        )
    """)
    
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
    """صفحة الأدمن"""
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
    """الحصول على المهام النشطة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE is_active = 1 ORDER BY added_at DESC")
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({
            'success': True,
            'data': tasks
        })
    except Exception as e:
        print(f"Error in get_tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/user/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    """الحصول على المهام المكتملة للمستخدم"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ut.*, t.task_name, t.reward_amount 
            FROM user_tasks ut
            JOIN tasks t ON ut.task_id = t.id
            WHERE ut.user_id = ?
            ORDER BY ut.completed_at DESC
        """, (user_id,))
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({
            'success': True,
            'data': tasks
        })
    except Exception as e:
        print(f"Error in get_user_tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            return jsonify({'success': True, 'data': channels})
        
        elif request.method == 'POST':
            # Add new channel
            data = request.get_json()
            channel_id = data.get('channel_id')
            channel_name = data.get('channel_name')
            channel_url = data.get('channel_url')
            admin_id = data.get('admin_id')
            
            if not all([channel_id, channel_name, channel_url, admin_id]):
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO required_channels (channel_id, channel_name, channel_url, added_by, added_at, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (channel_id, channel_name, channel_url, admin_id, now))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Channel added successfully'})
        
        elif request.method == 'DELETE':
            # Delete channel
            channel_id = request.args.get('channel_id')
            if not channel_id:
                return jsonify({'success': False, 'error': 'Channel ID required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE required_channels 
                SET is_active = 0 
                WHERE channel_id = ?
            """, (channel_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Channel removed'})
            
    except Exception as e:
        print(f"Error in manage_channels: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/tasks', methods=['POST', 'DELETE'])
def manage_tasks():
    """إدارة المهام"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            task_type = data.get('task_type')  # 'channel', 'link'
            task_name = data.get('task_name')
            task_description = data.get('task_description')
            reward_amount = data.get('reward_amount', 0)
            admin_id = data.get('admin_id')
            
            # For channel tasks
            channel_id = data.get('channel_id')
            # For link tasks
            link_url = data.get('link_url')
            duration = data.get('duration', 10)  # seconds
            
            if not all([task_type, task_name, admin_id]):
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO tasks (task_type, task_name, task_description, channel_id, link_url, reward_amount, is_active, added_by, added_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (task_type, task_name, task_description, channel_id, link_url, reward_amount, admin_id, now))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Task created successfully'})
        
        elif request.method == 'DELETE':
            task_id = request.args.get('task_id')
            if not task_id:
                return jsonify({'success': False, 'error': 'Task ID required'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET is_active = 0 WHERE id = ?", (task_id,))
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Task deleted'})
            
    except Exception as e:
        print(f"Error in manage_tasks: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check لـ Render"""
    return {'status': 'ok', 'service': 'Panda Giveaways Mini App'}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🌐 Starting Flask Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

