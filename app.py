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
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
import os
import sys
import sqlite3  # للتوافق مع IntegrityError في الكود القديم
from datetime import datetime, timedelta
import threading
import subprocess
import random
import hashlib
import secrets
import requests  # لجلب سعر TON

# إضافة المسار الحالي لـ 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# استيراد مدير قاعدة البيانات الجديد (يدعم PostgreSQL & SQLite)
from database import db_manager, get_db_connection

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

def send_withdrawal_notification_to_admin(user_id, username, full_name, amount, withdrawal_type, wallet_address, phone_number, withdrawal_id, auto_process=False):
    """إرسال إشعار للأدمن في البوت عند طلب سحب"""
    try:
        # إذا كان السحب تلقائي، لا ترسل إشعار
        if auto_process:
            print(f"🤖 Auto-processing enabled - Skipping admin notification for withdrawal #{withdrawal_id}")
            return
        
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
# تم نقل إدارة قاعدة البيانات إلى database.py
# يدعم الآن PostgreSQL (Neon) و SQLite للتطوير المحلي

print(f"📂 Using database: {'PostgreSQL (Neon)' if db_manager.use_postgres else 'SQLite (Local)'}")

def get_user(user_id):
    """الحصول على بيانات مستخدم"""
    return db_manager.execute_query(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,),
        fetch='one'
    )

def create_user_if_not_exists(user_id, username="", full_name="User"):
    """إنشاء مستخدم إذا لم يكن موجوداً"""
    now = datetime.now().isoformat()
    
    try:
        if db_manager.use_postgres:
            db_manager.execute_query("""
                INSERT INTO users (user_id, username, full_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, username, full_name, now, now))
        else:
            db_manager.execute_query("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, now, now))
    except Exception as e:
        print(f"Error creating user: {e}")

def get_user_referrals_db(user_id):
    """الحصول على إحالات المستخدم"""
    try:
        return db_manager.execute_query("""
            SELECT r.*, u.username, u.full_name, u.created_at as joined_at
            FROM referrals r
            LEFT JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,), fetch='all')
    except Exception as e:
        print(f"Error in get_user_referrals_db: {e}")
        return []

def get_user_spins_db(user_id, limit=50):
    """الحصول على تاريخ اللفات"""
    try:
        return db_manager.execute_query("""
            SELECT * FROM spins
            WHERE user_id = ?
            ORDER BY spin_time DESC
            LIMIT ?
        """, (user_id, limit), fetch='all')
    except Exception as e:
        print(f"Error in get_user_spins_db: {e}")
        return []

def get_bot_stats():
    """إحصائيات البوت"""
    stats = {}
    
    result = db_manager.execute_query("SELECT COUNT(*) as total FROM users", fetch='one')
    stats['total_users'] = result['total'] if result else 0
    
    result = db_manager.execute_query("SELECT COUNT(*) as total FROM referrals WHERE is_valid = 1", fetch='one')
    stats['total_referrals'] = result['total'] if result else 0
    
    result = db_manager.execute_query("SELECT COUNT(*) as total FROM spins", fetch='one')
    stats['total_spins'] = result['total'] if result else 0
    
    result = db_manager.execute_query("SELECT SUM(prize_amount) as total FROM spins", fetch='one')
    stats['total_distributed'] = result['total'] if result and result['total'] else 0
    
    result = db_manager.execute_query("SELECT COUNT(*) as pending FROM withdrawals WHERE status = 'pending'", fetch='one')
    stats['pending_withdrawals'] = result['pending'] if result else 0
    
    result = db_manager.execute_query("SELECT SUM(amount) as total FROM withdrawals WHERE status = 'completed'", fetch='one')
    stats['total_withdrawn'] = result['total'] if result and result['total'] else 0
    
    return stats

# ═══════════════════════════════════════════════════════════════
# 🌐 ROUTES - Static Files
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return send_from_directory('public', 'index.html')

@app.route('/fp.html')
@app.route('/fp')
def fingerprint_page():
    """صفحة التحقق من الجهاز"""
    return send_from_directory('.', 'fp.html')

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
        
        now = datetime.now().isoformat()
        
        # التحقق من وجود المستخدم
        existing = db_manager.execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetch='one')
        
        if existing:
            # تحديث البيانات
            db_manager.execute_query("""
                UPDATE users 
                SET username = ?, full_name = ?, last_active = ?
                WHERE user_id = ?
            """, (username, full_name, now, user_id))
            print(f"✅ Updated user {user_id}: {username}, {full_name}")
        else:
            # إنشاء مستخدم جديد
            db_manager.execute_query("""
                INSERT INTO users (user_id, username, full_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, now, now))
            print(f"✅ Created user {user_id}: {username}, {full_name}")
        
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
            {'name': '0.01 TON', 'amount': 0.01, 'probability': 25},
            {'name': '0.05 TON', 'amount': 0.05, 'probability': 25},
            {'name': '0.1 TON', 'amount': 0.1, 'probability': 25},
            {'name': '0.5 TON', 'amount': 0.5, 'probability': 0},
            {'name': '1.0 TON', 'amount': 1.0, 'probability': 0},
            {'name': 'حظ أوفر', 'amount': 0.0, 'probability': 25}
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
        try:
            # Add spin record
            db_manager.execute_query("""
                INSERT INTO spins (user_id, prize_name, prize_amount, spin_time, spin_hash, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, selected_prize['name'], selected_prize['amount'], now, spin_hash, request.remote_addr))
            
            # Update user
            new_balance = user['balance'] + selected_prize['amount']
            new_spins = user['available_spins'] - 1
            new_total_spins = user['total_spins'] + 1
            
            db_manager.execute_query("""
                UPDATE users 
                SET balance = ?,
                    available_spins = ?,
                    total_spins = ?,
                    last_spin_time = ?,
                    last_active = ?
                WHERE user_id = ?
            """, (new_balance, new_spins, new_total_spins, now, now, user_id))
            
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
        rows = db_manager.execute_query("""
            SELECT id, task_type, task_name, task_description, task_link, 
                   channel_username, is_pinned
            FROM tasks 
            WHERE is_active = 1 
            ORDER BY is_pinned DESC, id DESC
        """, fetch='all')
        
        tasks = []
        for row in rows:
            tasks.append({
                'id': row[0],
                'task_type': row[1],
                'task_name': row[2],
                'task_description': row[3],
                'task_link': row[4],
                'channel_username': row[5],
                'is_pinned': row[6]
            })
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
        rows = db_manager.execute_query("""
            SELECT task_id, completed_at, verified
            FROM user_tasks
            WHERE user_id = ? AND verified = 1
        """, (user_id,), fetch='all')
        
        completed_tasks = []
        for row in rows:
            completed_tasks.append({
                'task_id': row[0],
                'completed_at': row[1],
                'verified': row[2]
            })
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
        task = db_manager.execute_query("""
            SELECT task_type, channel_username
            FROM tasks
            WHERE id = ? AND is_active = 1
        """, (task_id,), fetch='one')
        
        if not task:
            return jsonify({'success': False, 'message': 'المهمة غير موجودة'}), 404
        
        task_type = task[0]
        channel_username = task[1]
        
        # التحقق من أن المستخدم لم يكمل المهمة من قبل
        already_completed = db_manager.execute_query("""
            SELECT id FROM user_tasks
            WHERE user_id = ? AND task_id = ? AND verified = 1
        """, (user_id, task_id), fetch='one')
        
        if already_completed:
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
                    return jsonify({
                        'success': False, 
                        'message': '❌ لم يتم العثور على اشتراكك! تأكد من الاشتراك في القناة أولاً'
                    })
                    
            except Exception as e:
                print(f"Error verifying subscription: {e}")
                return jsonify({
                    'success': False,
                    'message': '❌ خطأ في التحقق من الاشتراك. حاول مرة أخرى'
                })
        
        # تسجيل إتمام المهمة
        now = datetime.now().isoformat()
        
        db_manager.execute_query("""
            INSERT OR REPLACE INTO user_tasks (user_id, task_id, completed_at, verified)
            VALUES (?, ?, ?, 1)
        """, (user_id, task_id, now))
        
        # التحقق من عدد المهام المكتملة
        completed_count_row = db_manager.execute_query("""
            SELECT COUNT(*) FROM user_tasks
            WHERE user_id = ? AND verified = 1
        """, (user_id,), fetch='one')
        
        completed_count = completed_count_row[0]
        
        # كل 5 مهمات = 1 دورة
        new_spin = 0
        if completed_count % 5 == 0:
            db_manager.execute_query("""
                UPDATE users 
                SET available_spins = available_spins + 1
                WHERE user_id = ?
            """, (user_id,))
            new_spin = 1
        
        # جلب الدورات الجديدة
        result = db_manager.execute_query("SELECT available_spins FROM users WHERE user_id = ?", (user_id,), fetch='one')
        new_spins = result[0] if result else 0
        
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
        rows = db_manager.execute_query("""
            SELECT * FROM withdrawals
            WHERE user_id = ?
            ORDER BY requested_at DESC
        """, (user_id,), fetch='all')
        withdrawals = [dict(row) for row in rows]
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
        
        # التحقق من رصيد المستخدم
        user = db_manager.execute_query('SELECT balance, username, full_name FROM users WHERE user_id = ?', (user_id,), fetch='one')
        
        if not user:
            return jsonify({'success': False, 'error': 'مستخدم غير موجود'}), 404
            
        if user['balance'] < amount:
            return jsonify({'success': False, 'error': 'رصيد غير كافٍ'}), 400
        
        # إنشاء طلب السحب
        db_manager.execute_query("""
            INSERT INTO withdrawals (user_id, amount, withdrawal_type, wallet_address, phone_number, status, requested_at)
            VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        """, (user_id, amount, withdrawal_type, wallet_address, phone_number))
        
        withdrawal_id = db_manager.get_last_row_id()
        
        # خصم المبلغ من رصيد المستخدم
        db_manager.execute_query("""
            UPDATE users 
            SET balance = balance - ?,
                last_withdrawal_time = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (amount, user_id))
        
        # الحصول على الرصيد الجديد
        new_balance_row = db_manager.execute_query('SELECT balance FROM users WHERE user_id = ?', (user_id,), fetch='one')
        new_balance = new_balance_row['balance']
        
        # التحقق من تفعيل السحب التلقائي
        auto_withdrawal_row = db_manager.execute_query("SELECT setting_value FROM bot_settings WHERE setting_key = 'auto_withdrawal_enabled'", fetch='one')
        
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
        
        # إرسال إشعار للأدمن في البوت (إلا إذا كان السحب تلقائي)
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
                auto_process=auto_withdrawal_enabled and withdrawal_type.upper() == 'TON' and wallet_address
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
        
        if status == 'all':
            rows = db_manager.execute_query("""
                SELECT 
                    w.*,
                    u.full_name as user_name,
                    u.username
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                ORDER BY w.requested_at DESC
            """, fetch='all')
        else:
            rows = db_manager.execute_query("""
                SELECT 
                    w.*,
                    u.full_name as user_name,
                    u.username
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status = ?
                ORDER BY w.requested_at DESC
            """, (status,), fetch='all')
        
        withdrawals = [dict(row) for row in rows]
        
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
        
        # تحديث حالة الطلب
        db_manager.execute_query("""
            UPDATE withdrawals 
            SET status = 'completed',
                processed_at = CURRENT_TIMESTAMP,
                processed_by = ?,
                tx_hash = ?
            WHERE id = ?
        """, (admin_id, tx_hash, withdrawal_id))
        
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
        
        # الحصول على معلومات الطلب
        withdrawal = db_manager.execute_query('SELECT user_id, amount FROM withdrawals WHERE id = ?', (withdrawal_id,), fetch='one')
        
        if not withdrawal:
            return jsonify({'success': False, 'error': 'طلب السحب غير موجود'}), 404
        
        # إرجاع المبلغ للمستخدم
        db_manager.execute_query("""
            UPDATE users 
            SET balance = balance + ?
            WHERE user_id = ?
        """, (withdrawal['amount'], withdrawal['user_id']))
        
        # تحديث حالة الطلب
        db_manager.execute_query("""
            UPDATE withdrawals 
            SET status = 'rejected',
                processed_at = CURRENT_TIMESTAMP,
                processed_by = ?,
                rejection_reason = ?
            WHERE id = ?
        """, (admin_id, reason, withdrawal_id))
        
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
        
        now = datetime.now().isoformat()
        
        try:
            # تسجيل الإحالة
            db_manager.execute_query("""
                INSERT INTO referrals (referrer_id, referred_id, is_valid, created_at, validated_at)
                VALUES (?, ?, 1, ?, ?)
            """, (referrer_id, referred_id, now, now))
            
            # تحديث عدد الإحالات للـ referrer
            db_manager.execute_query("""
                UPDATE users 
                SET total_referrals = total_referrals + 1,
                    valid_referrals = valid_referrals + 1
                WHERE user_id = ?
            """, (referrer_id,))
            
            # إضافة لفة مجانية كل 5 إحالات
            result = db_manager.execute_query("SELECT valid_referrals FROM users WHERE user_id = ?", (referrer_id,), fetch='one')
            if result and result['valid_referrals'] % 5 == 0:
                db_manager.execute_query("""
                    UPDATE users 
                    SET available_spins = available_spins + 1
                    WHERE user_id = ?
                """, (referrer_id,))
            
            return jsonify({
                'success': True,
                'message': 'Referral registered successfully'
            })
        except sqlite3.IntegrityError:
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
        
        now = datetime.now().isoformat()
        
        try:
            # التحقق من أن المهمة موجودة ونشطة
            task = db_manager.execute_query("SELECT * FROM tasks WHERE id = ? AND is_active = 1", (task_id,), fetch='one')
            
            if not task:
                return jsonify({'success': False, 'error': 'Task not found'}), 404
            
            # تسجيل إنجاز المهمة
            db_manager.execute_query("""
                INSERT INTO user_tasks (user_id, task_id, completed_at, verified)
                VALUES (?, ?, ?, 1)
            """, (user_id, task_id, now))
            
            # إضافة المكافأة للرصيد
            db_manager.execute_query("""
                UPDATE users 
                SET balance = balance + ?
                WHERE user_id = ?
            """, (task['reward_amount'], user_id))
            
            # التحقق من عدد المهام المكتملة
            tasks_count_row = db_manager.execute_query("""
                SELECT COUNT(*) as count FROM user_tasks WHERE user_id = ?
            """, (user_id,), fetch='one')
            tasks_count = tasks_count_row['count']
            
            # كل 5 مهمات = لفة إضافية
            if tasks_count % 5 == 0:
                db_manager.execute_query("""
                    UPDATE users 
                    SET available_spins = available_spins + 1
                    WHERE user_id = ?
                """, (user_id,))
            
            return jsonify({
                'success': True,
                'message': 'Task completed successfully',
                'reward': task['reward_amount']
            })
            
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Task already completed'}), 400
            
    except Exception as e:
        print(f"Error in complete_task: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/required-channels', methods=['GET'])
def get_required_channels():
    """الحصول على القنوات الإجبارية النشطة للمستخدمين"""
    try:
        rows = db_manager.execute_query("""
            SELECT id, channel_id, channel_name, channel_url
            FROM required_channels 
            WHERE is_active = 1 
            ORDER BY added_at DESC
        """, fetch='all')
        
        channels = []
        for row in rows:
            channels.append({
                'id': row[0],
                'channel_id': row[1],
                'channel_name': row[2],
                'channel_url': row[3]
            })
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
        channels = db_manager.execute_query("""
            SELECT channel_id, channel_name
            FROM required_channels 
            WHERE is_active = 1
        """, fetch='all')
        
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

# ═══════════════════════════════════════════════════════════════
# 🔐 DEVICE VERIFICATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.route('/api/fingerprint', methods=['POST'])
def submit_fingerprint():
    """استقبال وحفظ بصمة الجهاز من صفحة التحقق"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        fp_token = data.get('fp_token')
        fingerprint = data.get('fingerprint')
        meta = data.get('meta', {})
        
        if not all([user_id, fp_token, fingerprint]):
            return jsonify({
                'ok': False,
                'error': 'Missing required fields'
            }), 400
        
        # التحقق من حالة نظام التحقق
        setting = db_manager.execute_query("""
            SELECT setting_value FROM system_settings 
            WHERE setting_key = 'verification_enabled'
        """, fetch='one')
        verification_enabled = setting['setting_value'] == 'true' if setting else True
        
        # إذا كان التحقق معطلاً، نسمح مباشرة
        if not verification_enabled:
            # تسجيل المحاولة كنجاح بدون تحقق
            db_manager.execute_query("""
                INSERT INTO verification_attempts 
                (user_id, fingerprint, ip_address, attempt_time, status, reason)
                VALUES (?, ?, ?, datetime('now'), 'bypassed', 'verification_disabled')
            """, (user_id, fingerprint, request.remote_addr))
            
            db_manager.execute_query("""
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
            
            # إشعار البوت
            try:
                import requests as req
                bot_notify_url = 'http://localhost:8081/device-verified'
                req.post(bot_notify_url, json={'user_id': user_id}, timeout=3)
            except:
                pass
            
            return jsonify({
                'ok': True,
                'message': 'تم التحقق بنجاح (التحقق معطل)'
            })
        
        # استكمال التحقق العادي إذا كان مفعلاً
        # التحقق من صلاحية الـ token
        token_row = db_manager.execute_query("""
            SELECT * FROM verification_tokens 
            WHERE user_id = ? AND token = ? AND used = 0
            AND datetime(expires_at) > datetime('now')
        """, (user_id, fp_token), fetch='one')
        
        if not token_row:
            return jsonify({
                'ok': False,
                'error': 'Invalid or expired token'
            }), 403
        
        # الحصول على IP address
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0]
        else:
            ip_address = request.remote_addr
        
        # التحقق من عدم وجود جهاز آخر بنفس البصمة
        duplicate_device = db_manager.execute_query("""
            SELECT user_id FROM device_verifications 
            WHERE fingerprint = ? AND user_id != ?
        """, (fingerprint, user_id), fetch='one')
        
        if duplicate_device:
            # تسجيل المحاولة الفاشلة
            db_manager.execute_query("""
                INSERT INTO verification_attempts 
                (user_id, fingerprint, ip_address, attempt_time, status, reason)
                VALUES (?, ?, ?, datetime('now'), 'rejected', 'duplicate_device')
            """, (user_id, fingerprint, ip_address))
            
            # حظر المستخدم وحفظ السبب
            ban_reason = 'تم اكتشاف حسابات متعددة - جهاز مسجل مسبقاً'
            db_manager.execute_query("""
                UPDATE users 
                SET is_banned = 1, ban_reason = ?
                WHERE user_id = ?
            """, (ban_reason, user_id))
            
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
        ip_count_row = db_manager.execute_query("""
            SELECT COUNT(*) FROM device_verifications 
            WHERE ip_address = ? AND user_id != ?
        """, (ip_address, user_id), fetch='one')
        
        ip_count = ip_count_row[0]
        if ip_count >= 3:  # السماح بـ 3 أجهزة كحد أقصى من نفس الـ IP
            db_manager.execute_query("""
                INSERT INTO verification_attempts 
                (user_id, fingerprint, ip_address, attempt_time, status, reason)
                VALUES (?, ?, ?, datetime('now'), 'rejected', 'ip_limit_exceeded')
            """, (user_id, fingerprint, ip_address))
            
            # حظر المستخدم وحفظ السبب
            ban_reason = 'تم اكتشاف حسابات متعددة - تجاوز الحد الأقصى للأجهزة من نفس الشبكة'
            db_manager.execute_query("""
                UPDATE users 
                SET is_banned = 1, ban_reason = ?
                WHERE user_id = ?
            """, (ban_reason, user_id))
            
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
        db_manager.execute_query("""
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
        db_manager.execute_query("""
            UPDATE users 
            SET is_device_verified = 1, verification_required = 0
            WHERE user_id = ?
        """, (user_id,))
        
        # تحديث حالة الـ token
        db_manager.execute_query("""
            UPDATE verification_tokens 
            SET used = 1 
            WHERE user_id = ? AND token = ?
        """, (user_id, fp_token))
        
        # تسجيل المحاولة الناجحة
        db_manager.execute_query("""
            INSERT INTO verification_attempts 
            (user_id, fingerprint, ip_address, attempt_time, status, reason)
            VALUES (?, ?, ?, datetime('now'), 'success', 'verified')
        """, (user_id, fingerprint, ip_address))
        
        print(f"✅ Device verified for user {user_id}")
        
        # إرسال إشعار للبوت للتحقق من الإحالة إن وجدت
        try:
            import requests as req
            bot_notify_url = 'http://localhost:8081/device-verified'
            req.post(bot_notify_url, json={'user_id': user_id}, timeout=3)
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
        
        # إنشاء token عشوائي
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires_at = (now + timedelta(minutes=15)).isoformat()
        
        db_manager.execute_query("""
            INSERT INTO verification_tokens 
            (user_id, token, created_at, expires_at, used)
            VALUES (?, ?, ?, ?, 0)
        """, (user_id, token, now.isoformat(), expires_at))
        
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

@app.route('/api/verification/status/<int:user_id>', methods=['GET'])
def get_verification_status(user_id):
    """التحقق من حالة تحقق المستخدم"""
    try:
        # التحقق من وجود تحقق للمستخدم
        verification = db_manager.execute_query("""
            SELECT * FROM device_verifications 
            WHERE user_id = ?
        """, (user_id,), fetch='one')
        
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
def manage_channels():
    """إدارة القنوات الإجبارية"""
    try:
        if request.method == 'GET':
            # Get all required channels
            rows = db_manager.execute_query("""
                SELECT * FROM required_channels 
                WHERE is_active = 1 
                ORDER BY added_at DESC
            """, fetch='all')
            channels = [dict(row) for row in rows]
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
            
            now = datetime.now().isoformat()
            
            try:
                db_manager.execute_query("""
                    INSERT INTO required_channels (channel_id, channel_name, channel_url, added_by, added_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (channel_id, channel_name, channel_url, admin_id, now, is_active))
                
                return jsonify({'success': True, 'message': 'تم إضافة القناة بنجاح'})
            except sqlite3.IntegrityError:
                return jsonify({'success': False, 'message': 'القناة موجودة بالفعل'}), 400
        
        elif request.method == 'DELETE':
            # Delete channel
            channel_id = request.args.get('channel_id')
            if not channel_id:
                return jsonify({'success': False, 'message': 'معرف القناة مطلوب'}), 400
            
            db_manager.execute_query("""
                UPDATE required_channels 
                SET is_active = 0 
                WHERE channel_id = ?
            """, (channel_id,))
            
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
            rows = db_manager.execute_query("""
                SELECT id, task_type, task_name, task_description, task_link, 
                       channel_username, is_pinned, is_active, added_at
                FROM tasks
                ORDER BY is_pinned DESC, added_at DESC
            """, fetch='all')
            
            tasks = []
            for row in rows:
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
            
            now = datetime.now().isoformat()
            
            # افتراض admin_id = 1797127532 (يمكن تحديثه من Telegram WebApp)
            admin_id = 1797127532
            
            db_manager.execute_query("""
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
            
            task_id = db_manager.get_last_row_id()
            
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
            
            db_manager.execute_query("""
                UPDATE tasks 
                SET task_type = ?, task_name = ?, task_description = ?, 
                    task_link = ?, channel_username = ?, is_pinned = ?, is_active = ?
                WHERE id = ?
            """, (
                task_type, task_name, task_description, task_link,
                channel_username, is_pinned, is_active, task_id
            ))
            
            return jsonify({
                'success': True, 
                'message': 'تم تحديث المهمة بنجاح'
            })
            
        elif request.method == 'DELETE':
            # حذف مهمة
            task_id = request.args.get('task_id')
            if not task_id:
                return jsonify({'success': False, 'message': 'معرف المهمة مطلوب'}), 400
            
            # تعطيل المهمة بدلاً من حذفها
            db_manager.execute_query("""
                UPDATE tasks 
                SET is_active = 0 
                WHERE id = ?
            """, (task_id,))
            
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
            rows = db_manager.execute_query("""
                SELECT * FROM wheel_prizes 
                WHERE is_active = 1 
                ORDER BY position ASC
            """, fetch='all')
            prizes = [dict(row) for row in rows]
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
            
            now = datetime.now().isoformat()
            
            db_manager.execute_query("""
                INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (name, value, probability, color, emoji, position, now))
            
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
            
            now = datetime.now().isoformat()
            
            db_manager.execute_query("""
                UPDATE wheel_prizes 
                SET name = ?, value = ?, probability = ?, color = ?, emoji = ?, position = ?, updated_at = ?
                WHERE id = ?
            """, (name, value, probability, color, emoji, position, now, prize_id))
            
            return jsonify({'success': True, 'message': 'Prize updated successfully'})
        
        elif request.method == 'DELETE':
            # Delete prize
            prize_id = request.args.get('id')
            if not prize_id:
                return jsonify({'success': False, 'error': 'Prize ID required'}), 400
            
            db_manager.execute_query("""
                UPDATE wheel_prizes 
                SET is_active = 0 
                WHERE id = ?
            """, (prize_id,))
            
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
        
        # Find user by username
        user = db_manager.execute_query("SELECT user_id, username FROM users WHERE username = ?", (username,), fetch='one')
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user_id = user['user_id']
        
        # Add spins
        db_manager.execute_query("""
            UPDATE users 
            SET available_spins = available_spins + ?
            WHERE user_id = ?
        """, (spins_count, user_id))
        
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
        rows = db_manager.execute_query("""
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
        """, fetch='all')
        
        users = []
        for row in rows:
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
def get_advanced_stats():
    """إحصائيات متقدمة للأدمن"""
    try:
        # إجمالي المستخدمين
        total_users_row = db_manager.execute_query("SELECT COUNT(*) as total FROM users", fetch='one')
        total_users = total_users_row['total']
        
        # المستخدمين النشطين (غير محظورين)
        active_users_row = db_manager.execute_query("SELECT COUNT(*) as active FROM users WHERE is_banned = 0", fetch='one')
        active_users = active_users_row['active']
        
        # المستخدمين المحظورين
        banned_users_row = db_manager.execute_query("SELECT COUNT(*) as banned FROM users WHERE is_banned = 1", fetch='one')
        banned_users = banned_users_row['banned']
        
        # المستخدمين المتحقق منهم (بالجهاز)
        verified_users_row = db_manager.execute_query("SELECT COUNT(*) as verified FROM users WHERE is_device_verified = 1", fetch='one')
        verified_users = verified_users_row['verified']
        
        # إجمالي عمليات الحظر
        total_bans_row = db_manager.execute_query("SELECT COUNT(*) as total_bans FROM users WHERE is_banned = 1", fetch='one')
        total_bans = total_bans_row['total_bans']
        
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
def unban_user():
    """إلغاء حظر مستخدم والسماح له بالوصول بدون تحقق"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        now = datetime.now().isoformat()
        
        # إلغاء الحظر وتعيين أنه متحقق منه لتجنب التحقق مرة أخرى
        db_manager.execute_query("""
            UPDATE users 
            SET is_banned = 0,
                ban_reason = NULL,
                is_device_verified = 1,
                last_active = ?
            WHERE user_id = ?
        """, (now, user_id))
        
        # حذف سجلات التحقق القديمة
        db_manager.execute_query("DELETE FROM device_verifications WHERE user_id = ?", (user_id,))
        
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
def get_admin_user_referrals():
    """جلب إحالات مستخدم معين للأدمن"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400
        
        # جلب الإحالات
        rows = db_manager.execute_query("""
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
        """, (user_id,), fetch='all')
        
        referrals = []
        for row in rows:
            referrals.append({
                'id': row['id'],
                'username': f"@{row['username']}" if row['username'] else f"user_{row['id']}",
                'name': row['name'],
                'joined_at': row['joined_at'],
                'is_valid': row['is_valid']
            })
        
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
def verification_settings():
    """الحصول على/تحديث إعدادات التحقق من التعدد"""
    try:
        admin_id = request.args.get('admin_id') or (request.get_json() or {}).get('admin_id')
        
        # التحقق من صلاحية الأدمن
        if not admin_id or int(admin_id) not in ADMIN_IDS:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        if request.method == 'GET':
            # جلب الإعدادات الحالية
            result = db_manager.execute_query("""
                SELECT setting_value FROM system_settings 
                WHERE setting_key = 'verification_enabled'
            """, fetch='one')
            is_enabled = result['setting_value'] == 'true' if result else True
            
            return jsonify({
                'success': True,
                'verification_enabled': is_enabled
            })
        
        elif request.method == 'POST':
            # تحديث الإعدادات
            data = request.get_json()
            new_status = data.get('enabled', True)
            
            db_manager.execute_query("""
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, updated_at, updated_by)
                VALUES ('verification_enabled', ?, ?, ?)
            """, ('true' if new_status else 'false', datetime.now().isoformat(), admin_id))
            
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
        # جلب جميع الإعدادات
        settings_rows = db_manager.execute_query("SELECT setting_key, setting_value FROM bot_settings", fetch='all')
        
        settings = {}
        for row in settings_rows:
            settings[row['setting_key']] = row['setting_value']
        
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
        
        now = datetime.now().isoformat()
        
        # تحديث السحب التلقائي
        if 'auto_withdrawal_enabled' in data:
            auto_withdrawal = 'true' if data['auto_withdrawal_enabled'] else 'false'
            db_manager.execute_query("""
                INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at)
                VALUES ('auto_withdrawal_enabled', ?, ?)
            """, (auto_withdrawal, now))
        
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

