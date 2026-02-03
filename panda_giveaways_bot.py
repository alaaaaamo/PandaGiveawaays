"""
╔══════════════════════════════════════════════════════════════════╗
║                  🐼 PANDA GIVEAWAYS BOT 🐼                       ║
║           Professional Telegram Giveaway & Rewards Bot           ║
║                    Version 1.0.0 - Ultra Secure                  ║
╚══════════════════════════════════════════════════════════════════╝

بوت احترافي للأرباح والإحالات على تيليجرام
مع Mini App متكامل - عجلة الحظ - نظام الإحالات - المهام - السحوبات
أمان عالي المستوى ضد التلاعب

Created by: Omar Panda
"""

import os
import json
import logging
import asyncio
import hashlib
import random
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
from dataclasses import dataclass
from enum import Enum
import sqlite3

# ═══════════════════════════════════════════════════════════════
# 📦 IMPORTS
# ═══════════════════════════════════════════════════════════════
try:
    import requests
    from tonsdk.contract.wallet import Wallets, WalletVersionEnum
    from tonsdk.utils import bytes_to_b64str, to_nano, from_nano
    TON_SDK_AVAILABLE = True
except ImportError:
    TON_SDK_AVAILABLE = False
    print("⚠️ tonsdk not available - install: pip install tonsdk requests")

from flask import Flask, request, jsonify
import threading

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    WebAppInfo,
    ChatMember,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    InlineQueryHandler
)
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TimedOut, NetworkError, Forbidden, BadRequest
import re

# استيراد نظام الأيقونات المودرن
try:
    from bot_icons import icon, button_text, title, QUICK
except ImportError:
    # Fallback إذا الملف مش موجود
    def icon(name, fallback='•'): return fallback
    def button_text(i, t): return t
    def title(i, t): return t
    QUICK = {}

# ═══════════════════════════════════════════════════════════════
# 🔧 CONFIGURATION - من ملف .env
# ═══════════════════════════════════════════════════════════════

# تحميل المتغيرات من .env
from dotenv import load_dotenv
load_dotenv()

# 🤖 معلومات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "PandaGiveawaysBot")
MINI_APP_URL = os.getenv("MINI_APP_URL")

# 👥 الأدمن (يتم قراءتهم من .env)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]

# 📢 قناة إثباتات الدفع
PAYMENT_PROOF_CHANNEL = os.getenv("PAYMENT_PROOF_CHANNEL")

# 📢 قنوات الاشتراك الإجباري (سيتم تحميلها من قاعدة البيانات)
MANDATORY_CHANNELS = []

# 🎁 إعدادات عجلة الحظ (النسب والجوائز)
WHEEL_PRIZES = [
    {"name": "0.01 TON", "amount": 0.01, "probability": 40},   # 40%
    {"name": "0.05 TON", "amount": 0.05, "probability": 25},   # 25%
    {"name": "0.1 TON", "amount": 0.1, "probability": 15},     # 15%
    {"name": "0.5 TON", "amount": 0.5, "probability": 10},     # 10%
    {"name": "1.0 TON", "amount": 1.0, "probability": 5},      # 5%
    {"name": "حظ أوفر المرة القادمة", "amount": 0, "probability": 5}  # 5%
]

# 💰 إعدادات الإحالات والمهام
SPINS_PER_REFERRALS = 5  # عدد الإحالات للحصول على لفة
TICKETS_PER_TASK = 1  # عدد التذاكر لكل مهمة
TICKETS_FOR_SPIN = 5  # عدد التذاكر للحصول على لفة
REFERRALS_FOR_SPIN = 5  # عدد الإحالات للحصول على لفة
MIN_WITHDRAWAL_AMOUNT = 0.1  # 0.1 TON لكل طرق السحب

# 💳 إعدادات محفظة TON (للسحوبات الأوتوماتيكية)
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "")
WALLET_MNEMONIC_STR = os.getenv("WALLET_MNEMONIC", "")
WALLET_MNEMONIC = WALLET_MNEMONIC_STR.split() if WALLET_MNEMONIC_STR else []
TON_API_KEY = os.getenv("TON_API_KEY", "")

# 🔐 مفتاح الأمان
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

# 📊 إعدادات قاعدة البيانات
DATABASE_URL = os.getenv("DATABASE_URL", "")  # PostgreSQL
# Use absolute path on Render to ensure consistency with Flask app
if os.environ.get('RENDER'):
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/opt/render/project/src/panda_giveaways.db")
else:
    DATABASE_PATH = os.getenv("DATABASE_PATH", "panda_giveaways.db")

print(f"📂 Bot using database at: {DATABASE_PATH}")

# 🌐 API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000/api")

# � إعدادات البرودكاست
BROADCAST_CONCURRENCY = 25  # عدد الرسائل المتزامنة
BROADCAST_BATCH_SIZE = 100  # حجم الدفعة
BROADCAST_BATCH_DELAY = 1.0  # تأخير بين الدفعات (ثانية)
BROADCAST_PRUNE_BLOCKED = True  # حذف المستخدمين المحظورين تلقائياً

# 📊 States للـ ConversationHandler
(
    ADMIN_MENU, 
    BROADCAST_MESSAGE, 
    BROADCAST_BUTTON_NAME, 
    BROADCAST_BUTTON_URL,
    ADD_CHANNEL_LINK,  # جديد: لإضافة قناة
) = range(5)

# ═══════════════════════════════════════════════════════════════
# 🔧 LOGGING
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('panda_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 📊 DATA MODELS
# ═══════════════════════════════════════════════════════════════

class WithdrawalStatus(Enum):
    """حالات طلبات السحب"""
    PENDING = "pending"      # في انتظار الموافقة
    APPROVED = "approved"    # تم الموافقة
    COMPLETED = "completed"  # تم التحويل
    REJECTED = "rejected"    # تم الرفض

class TaskType(Enum):
    """أنواع المهام"""
    JOIN_CHANNEL = "join_channel"
    VISIT_LINK = "visit_link"
    SHARE_BOT = "share_bot"

@dataclass
class User:
    """نموذج المستخدم"""
    user_id: int
    username: str
    full_name: str
    balance: float = 0.0
    total_spins: int = 0
    available_spins: int = 0
    tickets: int = 0  # التذاكر من المهام والإحالات
    total_referrals: int = 0
    referrer_id: Optional[int] = None
    created_at: str = None
    last_active: str = None
    is_banned: bool = False
    
    # للأمان
    last_spin_time: Optional[str] = None
    spin_count_today: int = 0
    last_withdrawal_time: Optional[str] = None

# ═══════════════════════════════════════════════════════════════
# 🗄️ DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════

class DatabaseManager:
    """إدارة قاعدة البيانات بشكل آمن"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        logger.info("🗄️ Initializing Panda Giveaways Database...")
        self.init_database()
        logger.info("✅ Database initialized successfully")
    
    def get_connection(self):
        """إنشاء اتصال آمن بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = self.get_connection()
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
                tickets INTEGER DEFAULT 0,
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
                vodafone_number TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id)
            )
        """)
        
        # إضافة عمود tickets للمستخدمين القدامى
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN tickets INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # العمود موجود بالفعل
        
        # جدول الإحالات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                is_valid INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                validated_at TEXT,
                FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                FOREIGN KEY (referred_id) REFERENCES users(user_id),
                UNIQUE(referrer_id, referred_id)
            )
        """)
        
        # جدول لفات العجلة
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prize_name TEXT NOT NULL,
                prize_amount REAL NOT NULL,
                spin_time TEXT NOT NULL,
                spin_hash TEXT NOT NULL UNIQUE,
                ip_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # جدول طلبات السحب
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
                rejection_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (processed_by) REFERENCES users(user_id)
            )
        """)
        
        # جدول القنوات الإجبارية
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                channel_name TEXT NOT NULL,
                channel_username TEXT,
                is_active INTEGER DEFAULT 1,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                FOREIGN KEY (added_by) REFERENCES users(user_id)
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
                added_at TEXT NOT NULL,
                FOREIGN KEY (added_by) REFERENCES users(user_id)
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
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                UNIQUE(user_id, task_id)
            )
        """)
        
        # جدول السجلات (للأمان والمراقبة)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # جدول الجلسات النشطة (منع التلاعب)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_valid INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # إنشاء indexes لتحسين الأداء
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spins_user ON spins(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_tasks ON user_tasks(user_id, task_id)")
        
        conn.commit()
        conn.close()
        logger.info("✅ All database tables created successfully")
    
    # ═══════════════════════════════════════════════════════════
    # 👤 USER OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def create_or_update_user(self, user_id: int, username: str, full_name: str, 
                            referrer_id: Optional[int] = None) -> User:
        """إنشاء أو تحديث مستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # التحقق من وجود المستخدم
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # تحديث المستخدم الموجود
            cursor.execute("""
                UPDATE users 
                SET username = ?, full_name = ?, last_active = ?
                WHERE user_id = ?
            """, (username, full_name, now, user_id))
            conn.commit()
            
            user = User(
                user_id=existing['user_id'],
                username=username,
                full_name=full_name,
                balance=existing['balance'],
                total_spins=existing['total_spins'],
                available_spins=existing['available_spins'],
                total_referrals=existing['total_referrals'],
                referrer_id=existing['referrer_id'],
                created_at=existing['created_at'],
                last_active=now,
                is_banned=bool(existing['is_banned'])
            )
        else:
            # إنشاء مستخدم جديد
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, referrer_id, created_at, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, full_name, referrer_id, now, now))
            conn.commit()
            
            # إذا كان هناك referrer، نسجل الإحالة
            if referrer_id:
                try:
                    cursor.execute("""
                        INSERT INTO referrals (referrer_id, referred_id, created_at)
                        VALUES (?, ?, ?)
                    """, (referrer_id, user_id, now))
                    conn.commit()
                    logger.info(f"✅ Referral registered: {referrer_id} -> {user_id}")
                except sqlite3.IntegrityError:
                    logger.warning(f"⚠️ Referral already exists: {referrer_id} -> {user_id}")
            
            user = User(
                user_id=user_id,
                username=username,
                full_name=full_name,
                referrer_id=referrer_id,
                created_at=now,
                last_active=now
            )
        
        conn.close()
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """الحصول على بيانات مستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row['user_id'],
                username=row['username'],
                full_name=row['full_name'],
                balance=row['balance'],
                total_spins=row['total_spins'],
                available_spins=row['available_spins'],
                total_referrals=row['total_referrals'],
                referrer_id=row['referrer_id'],
                created_at=row['created_at'],
                last_active=row['last_active'],
                is_banned=bool(row['is_banned']),
                last_spin_time=row['last_spin_time'],
                spin_count_today=row['spin_count_today']
            )
        return None
    
    def update_user_balance(self, user_id: int, amount: float, add: bool = True):
        """تحديث رصيد المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if add:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                         (amount, user_id))
        else:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", 
                         (amount, user_id))
        
        conn.commit()
        conn.close()
        logger.info(f"💰 Balance updated for user {user_id}: {'+'if add else '-'}{amount}")
    
    def add_spins(self, user_id: int, spins: int):
        """إضافة لفات للمستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET available_spins = available_spins + ? 
            WHERE user_id = ?
        """, (spins, user_id))
        
        conn.commit()
        conn.close()
        logger.info(f"🎰 Added {spins} spin(s) to user {user_id}")
    
    def use_spin(self, user_id: int) -> bool:
        """استخدام لفة واحدة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود لفات متاحة
        cursor.execute("SELECT available_spins FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result['available_spins'] > 0:
            cursor.execute("""
                UPDATE users 
                SET available_spins = available_spins - 1,
                    total_spins = total_spins + 1,
                    spin_count_today = spin_count_today + 1,
                    last_spin_time = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    # ═══════════════════════════════════════════════════════════
    # 🎁 SPIN OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def record_spin(self, user_id: int, prize_name: str, prize_amount: float, 
                   ip_address: Optional[str] = None) -> str:
        """تسجيل لفة في قاعدة البيانات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # توليد hash فريد للتأكد من عدم التكرار
        spin_hash = hashlib.sha256(
            f"{user_id}{now}{prize_name}{random.random()}{SECRET_KEY}".encode()
        ).hexdigest()
        
        cursor.execute("""
            INSERT INTO spins (user_id, prize_name, prize_amount, spin_time, spin_hash, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, prize_name, prize_amount, now, spin_hash, ip_address))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🎰 Spin recorded: User {user_id} won {prize_name}")
        return spin_hash
    
    def get_user_spins_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """الحصول على سجل اللفات"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT prize_name, prize_amount, spin_time 
            FROM spins 
            WHERE user_id = ? 
            ORDER BY spin_time DESC 
            LIMIT ?
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════
    # 👥 REFERRAL OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def validate_referral(self, referred_id: int) -> bool:
        """التحقق من صحة الإحالة (بعد الاشتراك بالقنوات)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # تحديث حالة الإحالة
        cursor.execute("""
            UPDATE referrals 
            SET is_valid = 1, validated_at = ? 
            WHERE referred_id = ? AND is_valid = 0
        """, (now, referred_id))
        
        if cursor.rowcount > 0:
            # الحصول على الـ referrer
            cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (referred_id,))
            row = cursor.fetchone()
            
            if row:
                referrer_id = row['referrer_id']
                
                # تحديث عدد الإحالات الصحيحة
                cursor.execute("""
                    UPDATE users 
                    SET total_referrals = total_referrals + 1,
                        valid_referrals = valid_referrals + 1
                    WHERE user_id = ?
                """, (referrer_id,))
                
                # التحقق من استحقاق لفة جديدة
                cursor.execute("SELECT valid_referrals FROM users WHERE user_id = ?", (referrer_id,))
                valid_refs = cursor.fetchone()['valid_referrals']
                
                # كل 5 إحالات = لفة واحدة
                if valid_refs % SPINS_PER_REFERRALS == 0:
                    cursor.execute("""
                        UPDATE users 
                        SET available_spins = available_spins + 1 
                        WHERE user_id = ?
                    """, (referrer_id,))
                    logger.info(f"🎁 User {referrer_id} earned a spin from referrals!")
                
                conn.commit()
                conn.close()
                return True
        
        conn.close()
        return False
    
    def get_user_referrals(self, user_id: int) -> List[Dict]:
        """الحصول على قائمة المدعوين"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username, u.full_name, r.created_at, r.is_valid
            FROM referrals r
            JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════
    # 💸 WITHDRAWAL OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def create_withdrawal_request(self, user_id: int, amount: float, 
                                 withdrawal_type: str, wallet_address: Optional[str] = None,
                                 phone_number: Optional[str] = None) -> int:
        """إنشاء طلب سحب جديد"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO withdrawals 
            (user_id, amount, withdrawal_type, wallet_address, phone_number, status, requested_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (user_id, amount, withdrawal_type, wallet_address, phone_number, now))
        
        withdrawal_id = cursor.lastrowid
        
        # خصم المبلغ من رصيد المستخدم مؤقتاً
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", 
                      (amount, user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💸 Withdrawal request created: ID {withdrawal_id}, User {user_id}, Amount {amount}")
        return withdrawal_id
    
    def get_pending_withdrawals(self) -> List[Dict]:
        """الحصول على طلبات السحب المعلقة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT w.*, u.username, u.full_name
            FROM withdrawals w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.status = 'pending'
            ORDER BY w.requested_at ASC
        """, ())
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def approve_withdrawal(self, withdrawal_id: int, admin_id: int, tx_hash: Optional[str] = None):
        """الموافقة على طلب سحب"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE withdrawals 
            SET status = 'completed', processed_at = ?, processed_by = ?, tx_hash = ?
            WHERE id = ?
        """, (now, admin_id, tx_hash, withdrawal_id))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Withdrawal {withdrawal_id} approved by admin {admin_id}")
    
    def reject_withdrawal(self, withdrawal_id: int, admin_id: int, reason: str):
        """رفض طلب سحب وإعادة المبلغ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # الحصول على معلومات الطلب
        cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id = ?", (withdrawal_id,))
        row = cursor.fetchone()
        
        if row:
            user_id = row['user_id']
            amount = row['amount']
            
            # رفض الطلب
            cursor.execute("""
                UPDATE withdrawals 
                SET status = 'rejected', processed_at = ?, processed_by = ?, rejection_reason = ?
                WHERE id = ?
            """, (now, admin_id, reason, withdrawal_id))
            
            # إعادة المبلغ للمستخدم
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                          (amount, user_id))
            
            conn.commit()
            conn.close()
            logger.info(f"❌ Withdrawal {withdrawal_id} rejected by admin {admin_id}. Amount returned.")
    
    def complete_withdrawal(self, withdrawal_id: int, tx_hash: str):
        """تأكيد اكتمال السحب"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE withdrawals 
            SET status = 'completed', tx_hash = ?
            WHERE id = ?
        """, (tx_hash, withdrawal_id))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Withdrawal {withdrawal_id} completed with tx_hash: {tx_hash}")
    
    def get_user_withdrawals(self, user_id: int) -> List[Dict]:
        """الحصول على سجل سحوبات المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM withdrawals 
            WHERE user_id = ? 
            ORDER BY requested_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════
    # 📢 CHANNEL & TASK OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def add_mandatory_channel(self, channel_id: str, channel_name: str, 
                            channel_username: str, added_by: int):
        """إضافة قناة إجبارية"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO mandatory_channels 
                (channel_id, channel_name, channel_username, added_by, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (channel_id, channel_name, channel_username, added_by, now))
            
            conn.commit()
            conn.close()
            logger.info(f"📢 Added mandatory channel: {channel_name}")
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_active_mandatory_channels(self) -> List[Dict]:
        """الحصول على القنوات الإجبارية النشطة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM mandatory_channels 
            WHERE is_active = 1 
            ORDER BY added_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_task(self, task_type: str, task_name: str, task_description: str,
                channel_id: Optional[str] = None, link_url: Optional[str] = None,
                reward_amount: float = 0, added_by: int = 0):
        """إضافة مهمة جديدة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO tasks 
            (task_type, task_name, task_description, channel_id, link_url, reward_amount, added_by, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_type, task_name, task_description, channel_id, link_url, reward_amount, added_by, now))
        
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"✅ Task added: {task_name} (ID: {task_id})")
        return task_id
    
    def get_active_tasks(self) -> List[Dict]:
        """الحصول على المهام النشطة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE is_active = 1 ORDER BY added_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def mark_task_completed(self, user_id: int, task_id: int):
        """تسجيل إكمال مهمة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO user_tasks (user_id, task_id, completed_at, verified)
                VALUES (?, ?, ?, 1)
            """, (user_id, task_id, now))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Task {task_id} completed by user {user_id}")
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_user_completed_tasks(self, user_id: int) -> List[int]:
        """الحصول على المهام المكتملة للمستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [row['task_id'] for row in rows]
    
    # ═══════════════════════════════════════════════════════════
    # 📊 STATISTICS & ANALYTICS
    # ═══════════════════════════════════════════════════════════
    
    def get_all_users(self) -> List[Dict]:
        """الحصول على جميع المستخدمين للبرودكاست"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id as telegram_id FROM users WHERE is_banned = 0")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def delete_user(self, user_id: int):
        """حذف مستخدم (للمحظورين)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    
    def get_bot_statistics(self) -> Dict:
        """إحصائيات البوت الكاملة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # عدد المستخدمين
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        # عدد المستخدمين النشطين (آخر 7 أيام)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) as active FROM users WHERE last_active > ?", (week_ago,))
        active_users = cursor.fetchone()['active']
        
        # إجمالي الإحالات
        cursor.execute("SELECT COUNT(*) as total FROM referrals WHERE is_valid = 1")
        total_referrals = cursor.fetchone()['total']
        
        # إجمالي اللفات
        cursor.execute("SELECT COUNT(*) as total FROM spins")
        total_spins = cursor.fetchone()['total']
        
        # إجمالي المبالغ الموزعة
        cursor.execute("SELECT SUM(prize_amount) as total FROM spins")
        total_distributed = cursor.fetchone()['total'] or 0
        
        # طلبات السحب المعلقة
        cursor.execute("SELECT COUNT(*) as pending FROM withdrawals WHERE status = 'pending'")
        pending_withdrawals = cursor.fetchone()['pending']
        
        # إجمالي السحوبات المكتملة
        cursor.execute("SELECT SUM(amount) as total FROM withdrawals WHERE status = 'completed'")
        total_withdrawn = cursor.fetchone()['total'] or 0
        
        conn.close()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_referrals': total_referrals,
            'total_spins': total_spins,
            'total_distributed': total_distributed,
            'pending_withdrawals': pending_withdrawals,
            'total_withdrawn': total_withdrawn
        }
    
    def log_activity(self, user_id: int, action: str, details: Optional[str] = None,
                    ip_address: Optional[str] = None):
        """تسجيل نشاط المستخدم (للأمان)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO activity_logs (user_id, action, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, action, details, ip_address, now))
        
        conn.commit()
        conn.close()

# ═══════════════════════════════════════════════════════════════
# 🎰 WHEEL OF FORTUNE LOGIC
# ═══════════════════════════════════════════════════════════════

class WheelOfFortune:
    """منطق عجلة الحظ بنسب عادلة"""
    
    def __init__(self, prizes: List[Dict]):
        self.prizes = prizes
        self._validate_probabilities()
    
    def _validate_probabilities(self):
        """التحقق من صحة النسب"""
        total_prob = sum(p['probability'] for p in self.prizes)
        if abs(total_prob - 100) > 0.01:
            raise ValueError(f"Total probability must be 100%, got {total_prob}%")
    
    def spin(self) -> Dict:
        """تدوير العجلة والحصول على جائزة"""
        # توليد رقم عشوائي آمن
        rand = random.uniform(0, 100)
        
        cumulative = 0
        for prize in self.prizes:
            cumulative += prize['probability']
            if rand <= cumulative:
                return prize
        
        # fallback (لن يحدث نظرياً)
        return self.prizes[-1]

# ═══════════════════════════════════════════════════════════════
# 💰 TON WALLET MANAGER (للسحوبات الأوتوماتيكية)
# ═══════════════════════════════════════════════════════════════

class TONWalletManager:
    """إدارة محفظة TON للسحوبات"""
    
    def __init__(self, wallet_address: str, mnemonic: List[str], api_key: str):
        self.wallet_address = wallet_address
        self.mnemonic = mnemonic
        self.api_key = api_key
        self.api_endpoint = "https://toncenter.com/api/v2/"
        self.api_headers = {"X-API-Key": api_key}
        
        if TON_SDK_AVAILABLE and mnemonic:
            self._init_wallet()
        else:
            logger.warning("⚠️ TON SDK not available or mnemonic not provided")
            self.wallet_obj = None
    
    def _init_wallet(self):
        """تهيئة المحفظة"""
        try:
            mnemonics, _pub_k, _priv_k, wallet = Wallets.from_mnemonics(
                self.mnemonic, 
                WalletVersionEnum.v3r2, 
                0
            )
            self.wallet_obj = wallet
            logger.info("✅ TON Wallet initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize TON wallet: {e}")
            self.wallet_obj = None
    
    async def send_ton(self, to_address: str, amount: float, memo: Optional[str] = None) -> Optional[str]:
        """إرسال TON - نفس آلية waseet.py"""
        if not self.wallet_obj:
            logger.error("❌ Wallet not initialized - Cannot send TON")
            logger.error("❌ Manual transfer required")
            return None
        
        try:
            logger.info(f"💸 Sending {amount} TON to {to_address}...")
            logger.info("🚀 Initiating REAL TON transfer...")
            
            # الحصول على seqno من API مع retry
            seqno = None
            max_seqno_retries = 3
            
            for seqno_attempt in range(max_seqno_retries):
                try:
                    url = f"{self.api_endpoint}getWalletInformation"
                    params = {'address': self.wallet_address}
                    
                    logger.info(f"🔍 Fetching seqno (attempt {seqno_attempt + 1}/{max_seqno_retries})...")
                    
                    response = requests.get(url, params=params, headers=self.api_headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"📊 API Response: {str(data)[:400]}...")
                        
                        if data.get('ok') and 'result' in data:
                            result = data['result']
                            seqno = result.get('seqno')
                            
                            if seqno is not None:
                                logger.info(f"✅ Got seqno: {seqno}")
                                break
                            else:
                                # محاولة من wallet_id
                                wallet_id = result.get('wallet_id')
                                if wallet_id is not None:
                                    logger.info(f"⚠️ Using wallet_id as seqno: {wallet_id}")
                                    seqno = 0  # للمحفظة الجديدة
                                    break
                                logger.warning(f"⚠️ Could not find seqno in response")
                        else:
                            error_msg = data.get('error', 'Unknown error')
                            logger.warning(f"⚠️ API failed: {error_msg}")
                            
                            # إذا فشل، المحفظة غير مهيأة
                            if 'not found' in error_msg.lower() or 'contract is not initialized' in error_msg.lower():
                                logger.info("⚠️ Wallet not initialized - using seqno=0")
                                seqno = 0
                                break
                    else:
                        logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                    
                    if seqno_attempt < max_seqno_retries - 1:
                        wait_time = (seqno_attempt + 1) * 2
                        logger.info(f"⏳ Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        
                except Exception as e:
                    logger.error(f"❌ Error getting seqno: {e}")
                    if seqno_attempt < max_seqno_retries - 1:
                        await asyncio.sleep(2)
            
            # إذا فشل الحصول على seqno بعد كل المحاولات
            if seqno is None:
                logger.error("❌ Failed to get seqno after all retries")
                logger.error("⚠️ Cannot proceed without valid seqno - wallet might be uninitialized")
                raise Exception("Failed to get wallet seqno. Please ensure wallet is initialized and has sufficient balance.")
            
            logger.info(f"📝 Creating transfer message...")
            logger.info(f"   From: {self.wallet_address}")
            logger.info(f"   To: {to_address}")
            logger.info(f"   Amount: {amount} TON")
            logger.info(f"   Memo: {memo}")
            logger.info(f"   Seqno: {seqno}")
            
            # تحويل المبلغ إلى nanoTON
            amount_nano = to_nano(amount, 'ton')
            
            # إنشاء الـ query للتحويل
            query = self.wallet_obj.create_transfer_message(
                to_addr=to_address,
                amount=amount_nano,
                seqno=seqno,
                payload=memo
            )
            
            # إرسال المعاملة
            boc = bytes_to_b64str(query['message'].to_boc(False))
            
            send_url = f"{self.api_endpoint}sendBoc"
            send_params = {'boc': boc}
            
            # محاولة الإرسال مع retry في حالة 429
            max_retries = 3
            for attempt in range(max_retries):
                send_response = requests.post(send_url, json=send_params, headers=self.api_headers, timeout=10)
                
                if send_response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                        logger.warning(f"⚠️ Rate limited (429), waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error("❌ Failed after retries due to rate limiting")
                        return None
                
                break  # نجحت العملية
            
            if send_response.status_code == 200:
                result = send_response.json()
                
                if result.get('ok'):
                    # محاولة الحصول على TX hash من الـ response
                    result_data = result.get('result', {})
                    tx_hash = result_data.get('hash')
                    
                    # إذا لم يكن موجود في result، نحاول من مكان آخر
                    if not tx_hash:
                        tx_hash = result_data.get('message_hash') or result_data.get('@extra')
                    
                    # إذا لم نحصل على hash حقيقي، نولد واحد من BOC
                    if not tx_hash or tx_hash == 'transaction_sent':
                        try:
                            cell_hash = query['message'].hash
                            tx_hash = bytes_to_b64str(cell_hash)
                            logger.warning(f"⚠️ No hash in response, generated from BOC cell: {tx_hash[:16]}...")
                        except Exception as hash_error:
                            # fallback: استخدام sha256
                            import base64
                            hash_bytes = hashlib.sha256(boc.encode()).digest()
                            tx_hash = base64.b64encode(hash_bytes).decode().replace('+', '-').replace('/', '_').rstrip('=')
                            logger.warning(f"⚠️ Using fallback hash generation: {tx_hash[:16]}...")
                    
                    logger.info(f"✅ REAL Transfer successful!")
                    logger.info(f"   🔗 TX Hash: {tx_hash[:32] if isinstance(tx_hash, str) else tx_hash}...")
                    logger.info(f"   💰 Amount: {amount} TON")
                    logger.info(f"   📤 To: {to_address}")
                    
                    return str(tx_hash)
                else:
                    logger.error(f"❌ Send failed: {result.get('error', 'Unknown')}")
                    return None
            else:
                logger.error(f"❌ HTTP Error {send_response.status_code}")
                if send_response.status_code == 429:
                    logger.error("Rate limit exceeded. Please add API key or wait.")
                elif send_response.status_code == 500:
                    logger.error("❌ Server error (500) from TON API")
                    try:
                        error_data = send_response.json()
                        logger.error(f"Error details: {error_data}")
                    except:
                        logger.error(f"Response text: {send_response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error sending TON: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("⚠️ Transfer failed, please check wallet and network")
            return None
    
    async def get_balance(self) -> float:
        """الحصول على رصيد المحفظة"""
        try:
            url = f"{self.api_endpoint}getAddressBalance"
            params = {'address': self.wallet_address}
            response = requests.get(url, params=params, headers=self.api_headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    balance_nano = int(data['result'])
                    balance_ton = from_nano(balance_nano, 'ton')
                    return float(balance_ton)
            
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            return 0.0

# ═══════════════════════════════════════════════════════════════
# 🤖 BOT HANDLERS
# ═══════════════════════════════════════════════════════════════

# Initialize global objects
db = DatabaseManager()
wheel = WheelOfFortune(WHEEL_PRIZES)
ton_wallet = None

if TON_SDK_AVAILABLE and TON_WALLET_ADDRESS and WALLET_MNEMONIC:
    ton_wallet = TONWalletManager(TON_WALLET_ADDRESS, WALLET_MNEMONIC, TON_API_KEY)

# ═══════════════════════════════════════════════════════════════
# 🔐 SECURITY & HELPERS
# ═══════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    """التحقق من كون المستخدم أدمن"""
    return user_id in ADMIN_IDS

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من اشتراك المستخدم في جميع القنوات الإجبارية"""
    channels = db.get_active_mandatory_channels()
    
    for channel in channels:
        channel_id = channel['channel_id']
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                return False
        except Exception as e:
            logger.error(f"Error checking membership for channel {channel_id}: {e}")
            return False
    
    return True

def generate_referral_link(user_id: int) -> str:
    """توليد رابط الإحالة"""
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

def generate_mini_app_link(user_id: int) -> str:
    """توليد رابط المينى آب مع الإحالة"""
    return f"https://t.me/{BOT_USERNAME}?startapp=ref_{user_id}"

# ═══════════════════════════════════════════════════════════════
# � INLINE QUERY HANDLER
# ═══════════════════════════════════════════════════════════════

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج Inline Query لمشاركة رابط الدعوة"""
    query = update.inline_query.query
    user_id = update.inline_query.from_user.id
    
    # إذا كان النص فارغاً، استخدم النص الافتراضي
    if not query:
        ref_link = generate_mini_app_link(user_id)
        query = f"🎁 انضم لـ Panda Giveaways واربح TON مجاناً!\n\n{ref_link}"
    
    results = [
        InlineQueryResultArticle(
            id="1",
            title="🎁 شارك رابط الدعوة",
            description="انقر لمشاركة رابط الدعوة مع أصدقائك",
            input_message_content=InputTextMessageContent(
                message_text=query
            )
        )
    ]
    
    await update.inline_query.answer(results, cache_time=0)

# ═══════════════════════════════════════════════════════════════
# �📱 COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    full_name = user.full_name or username
    
    # استخراج referrer_id إن وجد
    referrer_id = None
    if context.args:
        arg = context.args[0]
        if arg.startswith('ref_'):
            try:
                referrer_id = int(arg.split('_')[1])
                # التأكد من عدم إحالة نفسه
                if referrer_id == user_id:
                    referrer_id = None
            except:
                referrer_id = None
    
    # إنشاء أو تحديث المستخدم
    db_user = db.create_or_update_user(user_id, username, full_name, referrer_id)
    
    # تسجيل النشاط
    db.log_activity(user_id, "start", f"Referrer: {referrer_id}")
    
    # رسالة الترحيب
    welcome_text = f"""
🐼 <b>مرحباً بك في Panda Giveaways!</b> 🎁

<b>{full_name}</b>، أهلاً بك في أفضل بوت للأرباح والهدايا! 🌟

💰 <b>رصيدك الحالي:</b> {db_user.balance:.2f} TON
🎰 <b>لفاتك المتاحة:</b> {db_user.available_spins}
👥 <b>إحالاتك:</b> {db_user.total_referrals}

<b>🎯 كيف تربح؟</b>
• قم بدعوة أصدقائك (كل {SPINS_PER_REFERRALS} إحالات = لفة مجانية)
• أكمل المهام اليومية
• إلعب عجلة الحظ واربح TON!
• إسحب أرباحك مباشرة إلى محفظتك

<b>🚀 ابدأ الآن واستمتع بالأرباح!</b>
"""
    
    # الأزرار
    keyboard = []
    
    # زر فتح Mini App
    keyboard.append([InlineKeyboardButton(
        "🎰 افتح Panda Giveaway",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}")
    )])
    
    # زر مشاركة رابط الدعوة (نسخ)
    ref_link = generate_mini_app_link(user_id)
    ref_text = f"🎁 انضم لـ Panda Giveaways واربح TON مجاناً!\n\n{ref_link}"
    keyboard.append([InlineKeyboardButton(
        "📤 مشاركة رابط الدعوة",
        switch_inline_query=ref_text
    )])
    
    # زر إثباتات الدفع
    keyboard.append([InlineKeyboardButton(
        "💎 إثباتات الدفع",
        url=PAYMENT_PROOF_CHANNEL
    )])
    
    # زر لوحة الأدمن (للأدمن فقط)
    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("⚙️ لوحة المالكين", callback_data="admin_panel"),
            InlineKeyboardButton("🖥️ لوحة الأدمن", web_app=WebAppInfo(url=f"{MINI_APP_URL}/admin?user_id={user_id}"))
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help"""
    help_text = """
🐼 <b>مساعدة Panda Giveaways</b>

<b>📋 الأوامر المتاحة:</b>
/start - بدء البوت
/help - عرض المساعدة
/stats - إحصائياتك الشخصية
/referrals - عرض إحالاتك
/balance - عرض رصيدك

<b>🎰 كيف تعمل عجلة الحظ؟</b>
• افتح Mini App من زر "افتح Panda Giveaway"
• إستخدم لفاتك المتاحة
• اربح TON فوراً!

<b>👥 نظام الإحالات:</b>
• كل {SPINS_PER_REFERRALS} إحالات صحيحة = لفة مجانية
• شارك رابطك مع الأصدقاء
• تأكد من اشتراكهم بالقنوات

<b>💰 السحوبات:</b>
• الحد الأدنى: {MIN_WITHDRAWAL_AMOUNT} TON
• ادخل من قسم السحب في Mini App
• اربط محفظة TON أو رقم فودافون كاش
• انتظر موافقة الأدمن

<b>📞 للدعم:</b>
تواصل مع @YourSupportBot
"""
    
    await update.message.reply_text(help_text.format(
        SPINS_PER_REFERRALS=SPINS_PER_REFERRALS,
        MIN_WITHDRAWAL_AMOUNT=MIN_WITHDRAWAL_AMOUNT
    ), parse_mode=ParseMode.HTML)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ لم يتم العثور على حسابك. استخدم /start أولاً.")
        return
    
    # حساب الإحالات المتبقية للفة القادمة
    valid_refs = user.total_referrals
    next_spin_in = SPINS_PER_REFERRALS - (valid_refs % SPINS_PER_REFERRALS)
    
    stats_text = f"""
📊 <b>إحصائياتك الشخصية</b>

👤 <b>الاسم:</b> {user.full_name}
🆔 <b>المعرف:</b> @{user.username}

💰 <b>الرصيد:</b> {user.balance:.4f} TON
🎰 <b>لفات متاحة:</b> {user.available_spins}
🔢 <b>إجمالي اللفات:</b> {user.total_spins}

👥 <b>الإحالات:</b> {user.total_referrals}
⏳ <b>متبقي للفة القادمة:</b> {next_spin_in} إحالات

📅 <b>عضو منذ:</b> {user.created_at[:10]}
⚡ <b>آخر نشاط:</b> {user.last_active[:10] if user.last_active else 'N/A'}
"""
    
    keyboard = [[
        InlineKeyboardButton("🎰 افتح Mini App", web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}")),
        InlineKeyboardButton("🔗 رابط الدعوة", callback_data="get_ref_link")
    ]]
    
    await update.message.reply_text(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def referrals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الإحالات"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ استخدم /start أولاً")
        return
    
    referrals = db.get_user_referrals(user_id)
    
    ref_text = f"""
👥 <b>قائمة المدعوين</b>

📊 <b>إجمالي الإحالات:</b> {len(referrals)}
✅ <b>الإحالات الصحيحة:</b> {sum(1 for r in referrals if r['is_valid'])}

"""
    
    if referrals:
        ref_text += "\n<b>آخر 10 مدعوين:</b>\n\n"
        for i, ref in enumerate(referrals[:10], 1):
            status = "✅" if ref['is_valid'] else "⏳"
            name = ref['full_name']
            username = f"@{ref['username']}" if ref['username'] else ""
            ref_text += f"{i}. {status} <b>{name}</b> {username}\n"
    else:
        ref_text += "\n<i>لم تقم بدعوة أحد بعد! شارك رابط الدعوة الآن 🚀</i>"
    
    ref_link = generate_mini_app_link(user_id)
    ref_text += f"\n\n🔗 <b>رابط الدعوة الخاص بك:</b>\n<code>{ref_link}</code>"
    
    keyboard = [[
        InlineKeyboardButton("📤 مشاركة الرابط", url=f"https://t.me/share/url?url={ref_link}&text=انضم%20معي%20في%20Panda%20Giveaways%20واربح%20TON!")
    ]]
    
    await update.message.reply_text(
        ref_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الرصيد"""
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ استخدم /start أولاً")
        return
    
    balance_text = f"""
💰 <b>رصيدك</b>

<b>الرصيد الحالي:</b> {user.balance:.4f} TON
<b>الحد الأدنى للسحب:</b> {MIN_WITHDRAWAL_AMOUNT} TON

"""
    
    if user.balance >= MIN_WITHDRAWAL_AMOUNT:
        balance_text += "✅ يمكنك السحب الآن من Mini App!"
    else:
        needed = MIN_WITHDRAWAL_AMOUNT - user.balance
        balance_text += f"⏳ تحتاج {needed:.4f} TON إضافية للسحب"
    
    keyboard = [[
        InlineKeyboardButton("💸 اسحب الآن", web_app=WebAppInfo(url=f"{MINI_APP_URL}/withdraw?user_id={user_id}")),
        InlineKeyboardButton("🎰 العب واربح", web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}"))
    ]]
    
    await update.message.reply_text(
        balance_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ═══════════════════════════════════════════════════════════════
# ⚙️ ADMIN PANEL HANDLERS
# ═══════════════════════════════════════════════════════════════

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الأدمن"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    # الحصول على إحصائيات البوت
    stats = db.get_bot_statistics()
    
    admin_text = f"""
⚙️ <b>لوحة المالكين - Panda Giveaways</b>

📊 <b>الإحصائيات العامة:</b>
👥 إجمالي المستخدمين: {stats['total_users']}
⚡ المستخدمون النشطون (7 أيام): {stats['active_users']}
🔗 إجمالي الإحالات: {stats['total_referrals']}
🎰 إجمالي اللفات: {stats['total_spins']}

💰 <b>الإحصائيات المالية:</b>
🎁 الأرباح الموزعة: {stats['total_distributed']:.2f} TON
💸 السحوبات المكتملة: {stats['total_withdrawn']:.2f} TON
⏳ طلبات السحب المعلقة: {stats['pending_withdrawals']}

<b>اختر ما تريد إدارته:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{icon('wallet')} طلبات السحب", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(f"{icon('broadcast')} إرسال برودكاست", callback_data="start_broadcast")],
        [InlineKeyboardButton(f"{icon('tasks')} إدارة المهام", callback_data="admin_tasks")],
        [InlineKeyboardButton(f"{icon('view')} فحص مستخدم", callback_data="admin_check_user")],
        [InlineKeyboardButton(f"{icon('chart')} إحصائيات تفصيلية", callback_data="admin_detailed_stats")],
        [InlineKeyboardButton(f"{icon('back')} رجوع", callback_data="back_to_start")]
    ]
    
    await query.edit_message_text(
        admin_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة المهام والقنوات"""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.answer(f"{icon('error')} غير مصرح لك!", show_alert=True)
        return
    
    # جلب القنوات والمهام من API
    try:
        response = requests.get(f"{MINI_APP_URL}/api/admin/channels")
        channels_data = response.json()
        channels = channels_data.get('data', [])
    except:
        channels = []
    
    tasks_text = f"""
{icon('tasks')} <b>إدارة المهام والقنوات</b>

{icon('info')} القنوات المضافة: {len(channels)}

{icon('bullet')} اضغط على إضافة قناة لإضافة قناة جديدة
{icon('bullet')} سيتم التحقق تلقائياً من أن البوت أدمن في القناة
{icon('bullet')} كل قناة = {TICKETS_PER_TASK} تذكرة للمستخدم
{icon('bullet')} {TICKETS_FOR_SPIN} تذاكر = 1 لفة
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{icon('add')} إضافة قناة جديدة", callback_data="add_channel_start")],
        [InlineKeyboardButton(f"{icon('view')} عرض جميع القنوات", callback_data="view_all_channels")],
        [InlineKeyboardButton(f"{icon('back')} رجوع", callback_data="admin_panel")]
    ]
    
    await query.edit_message_text(
        tasks_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_check_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص مستخدم"""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    await query.edit_message_text(
        "🚧 قريباً: فحص المستخدمين",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    )

async def admin_detailed_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إحصائيات تفصيلية"""
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    stats = db.get_bot_statistics()
    detailed_text = f"""
📊 <b>إحصائيات تفصيلية</b>

👥 <b>المستخدمون:</b>
• الإجمالي: {stats['total_users']}
• النشطون (7 أيام): {stats['active_users']}
• معدل النشاط: {(stats['active_users']/stats['total_users']*100) if stats['total_users'] > 0 else 0:.1f}%

🔗 <b>الإحالات:</b>
• الإجمالي: {stats['total_referrals']}
• متوسط الإحالات/مستخدم: {(stats['total_referrals']/stats['total_users']) if stats['total_users'] > 0 else 0:.2f}

🎰 <b>اللفات:</b>
• الإجمالي: {stats['total_spins']}
• متوسط اللفات/مستخدم: {(stats['total_spins']/stats['total_users']) if stats['total_users'] > 0 else 0:.2f}

💰 <b>المالية:</b>
• الأرباح الموزعة: {stats['total_distributed']:.2f} TON
• السحوبات المكتملة: {stats['total_withdrawn']:.2f} TON
• طلبات السحب المعلقة: {stats['pending_withdrawals']}
"""
    await query.edit_message_text(
        detailed_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    )

async def back_to_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للبداية"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    full_name = user.full_name or username
    
    db_user = db.get_user(user_id)
    if not db_user:
        db_user = db.create_or_update_user(user_id, username, full_name)
    
    welcome_text = f"""
🐼 <b>مرحباً بك في Panda Giveaways!</b> 🎁

<b>{full_name}</b>، أهلاً بك في أفضل بوت للأرباح والهدايا! 🌟

💰 <b>رصيدك الحالي:</b> {db_user.balance:.2f} TON
🎰 <b>لفاتك المتاحة:</b> {db_user.available_spins}
👥 <b>إحالاتك:</b> {db_user.total_referrals}

<b>🎯 كيف تربح؟</b>
• قم بدعوة أصدقائك (كل {SPINS_PER_REFERRALS} إحالات = لفة مجانية)
• أكمل المهام اليومية
• إلعب عجلة الحظ واربح TON!
• إسحب أرباحك مباشرة إلى محفظتك

<b>🚀 ابدأ الآن واستمتع بالأرباح!</b>
"""
    
    keyboard = []
    keyboard.append([InlineKeyboardButton(
        "🎰 افتح Panda Giveaway",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}")
    )])
    
    ref_link = generate_mini_app_link(user_id)
    ref_text = f"🎁 انضم لـ Panda Giveaways واربح TON مجاناً!\n\n{ref_link}"
    keyboard.append([InlineKeyboardButton(
        "📤 مشاركة رابط الدعوة",
        switch_inline_query=ref_text
    )])
    
    keyboard.append([InlineKeyboardButton(
        "💎 إثباتات الدفع",
        url=PAYMENT_PROOF_CHANNEL
    )])
    
    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("⚙️ لوحة المالكين", callback_data="admin_panel"),
            InlineKeyboardButton("🖥️ لوحة الأدمن", web_app=WebAppInfo(url=f"{MINI_APP_URL}/admin?user_id={user_id}"))
        ])
    
    await query.edit_message_text(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض طلبات السحب المعلقة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    pending = db.get_pending_withdrawals()
    
    if not pending:
        await query.edit_message_text(
            "✅ لا توجد طلبات سحب معلقة حالياً!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
        return
    
    withdrawal_text = f"""
💸 <b>طلبات السحب المعلقة ({len(pending)})</b>

"""
    
    keyboard = []
    
    for w in pending[:5]:  # أول 5 طلبات
        user_info = f"{w['full_name']} (@{w['username']})" if w['username'] else w['full_name']
        w_type = "TON" if w['withdrawal_type'] == 'ton' else "Vodafone Cash"
        
        withdrawal_text += f"""
━━━━━━━━━━━━━━━━━━
🆔 <b>ID:</b> {w['id']}
👤 <b>المستخدم:</b> {user_info}
💰 <b>المبلغ:</b> {w['amount']:.4f} TON
📱 <b>النوع:</b> {w_type}
"""
        
        if w['wallet_address']:
            withdrawal_text += f"🔐 <b>المحفظة:</b> <code>{w['wallet_address']}</code>\n"
        if w['phone_number']:
            withdrawal_text += f"📞 <b>الرقم:</b> <code>{w['phone_number']}</code>\n"
        
        withdrawal_text += f"📅 <b>التاريخ:</b> {w['requested_at'][:16]}\n"
        
        # أزرار الموافقة/الرفض
        keyboard.append([
            InlineKeyboardButton(f"✅ موافقة #{w['id']}", callback_data=f"approve_withdrawal_{w['id']}"),
            InlineKeyboardButton(f"❌ رفض #{w['id']}", callback_data=f"reject_withdrawal_{w['id']}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    
    await query.edit_message_text(
        withdrawal_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def approve_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على طلب سحب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    withdrawal_id = int(query.data.split('_')[2])
    
    # الحصول على معلومات الطلب
    pending = db.get_pending_withdrawals()
    withdrawal = next((w for w in pending if w['id'] == withdrawal_id), None)
    
    if not withdrawal:
        await query.answer("❌ الطلب غير موجود!", show_alert=True)
        return
    
    # محاولة السحب الأوتوماتيكي
    tx_hash = None
    
    if withdrawal['withdrawal_type'] == 'ton' and ton_wallet and withdrawal['wallet_address']:
        await query.edit_message_text("⏳ جاري معالجة السحب الأوتوماتيكي...")
        
        try:
            tx_hash = await ton_wallet.send_ton(
                withdrawal['wallet_address'],
                withdrawal['amount'],
                f"Panda Giveaways Withdrawal #{withdrawal_id}"
            )
            
            if tx_hash:
                db.approve_withdrawal(withdrawal_id, user_id, tx_hash)
                success_msg = f"""
✅ <b>تم السحب بنجاح!</b>

💸 المبلغ: {withdrawal['amount']:.4f} TON
👤 المستخدم: {withdrawal['full_name']}
🔐 TX Hash: <code>{tx_hash}</code>

تم إرسال الإشعار للمستخدم ✅
"""
                
                # إرسال إشعار للمستخدم
                try:
                    await context.bot.send_message(
                        chat_id=withdrawal['user_id'],
                        text=f"""
🎉 <b>تم تأكيد السحب!</b>

💰 تم تحويل {withdrawal['amount']:.4f} TON إلى محفظتك
🔐 TX Hash: <code>{tx_hash}</code>

شكراً لاستخدامك Panda Giveaways! 🐼
""",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
                
                await query.edit_message_text(success_msg, parse_mode=ParseMode.HTML)
                return
        except Exception as e:
            logger.error(f"Automatic withdrawal failed: {e}")
    
    # إذا فشل الأوتوماتيكي أو كان vodafone cash
    db.approve_withdrawal(withdrawal_id, user_id, tx_hash)
    
    approval_msg = f"""
✅ <b>تم الموافقة على الطلب #{withdrawal_id}</b>

💰 المبلغ: {withdrawal['amount']:.4f} TON
👤 المستخدم: {withdrawal['full_name']}
"""
    
    if withdrawal['withdrawal_type'] == 'vodafone':
        approval_msg += f"\n📞 <b>الرقم:</b> <code>{withdrawal['phone_number']}</code>\n\n⚠️ يرجى إرسال المبلغ يدوياً إلى الرقم أعلاه"
    else:
        approval_msg += f"\n🔐 <b>المحفظة:</b> <code>{withdrawal['wallet_address']}</code>\n\n⚠️ يرجى إرسال المبلغ يدوياً إلى المحفظة أعلاه"
    
    # إرسال إشعار للمستخدم
    try:
        await context.bot.send_message(
            chat_id=withdrawal['user_id'],
            text=f"""
✅ <b>تمت الموافقة على طلب السحب!</b>

💰 المبلغ: {withdrawal['amount']:.4f} TON
📅 سيتم التحويل خلال 24 ساعة

شكراً لصبرك! 🐼
""",
            parse_mode=ParseMode.HTML
        )
    except:
        pass
    
    await query.edit_message_text(
        approval_msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 رجوع لطلبات السحب", callback_data="admin_withdrawals")
        ]])
    )

# ═══════════════════════════════════════════════════════════════
# 📢 BROADCAST SYSTEM
# ═══════════════════════════════════════════════════════════════

async def safe_answer_query(query):
    """معالجة آمنة لـ callback_query"""
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Failed to answer query: {e}")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """بدء البرودكاست"""
    query = update.callback_query
    await safe_answer_query(query)
    await query.edit_message_text(
        text="أرسل الرسالة التي تريد إرسالها لجميع المستخدمين (يمكنك إرسال نص، صورة، ملصق، أو رسالة محوّلة):",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("رجوع", callback_data="admin_panel")]]
        ),
    )
    # مسح بيانات البرودكاست السابقة
    context.user_data.pop("broadcast_type", None)
    context.user_data.pop("broadcast_content", None)
    context.user_data.pop("broadcast_entities", None)
    context.user_data.pop("broadcast_photo", None)
    context.user_data.pop("broadcast_caption", None)
    context.user_data.pop("broadcast_caption_entities", None)
    context.user_data.pop("broadcast_sticker", None)
    context.user_data.pop("broadcast_button", None)
    context.user_data.pop("broadcast_button_url", None)
    context.user_data.pop("broadcast_from_chat_id", None)
    context.user_data.pop("broadcast_message_id", None)
    return BROADCAST_MESSAGE

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال رسالة البرودكاست"""
    message = update.message
    context.user_data["broadcast_type"] = None
    context.user_data["broadcast_button"] = None
    context.user_data["broadcast_button_url"] = None

    add_button_keyboard = [
        [InlineKeyboardButton("➕ إضافة زر رابط", callback_data="add_broadcast_button")],
        [InlineKeyboardButton("نعم، أرسل الآن", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("لا، إلغاء", callback_data="cancel_broadcast")],
    ]

    # تحقق من رسالة محوّلة
    is_forward = False
    try:
        if (getattr(message, "forward_origin", None) or getattr(message, "forward_date", None) 
            or getattr(message, "forward_from", None) or getattr(message, "forward_from_chat", None)):
            is_forward = True
    except Exception:
        is_forward = False

    if is_forward:
        context.user_data["broadcast_type"] = "forward"
        context.user_data["broadcast_from_chat_id"] = message.chat_id
        context.user_data["broadcast_message_id"] = message.message_id
        confirm_keyboard = [
            [InlineKeyboardButton("نعم، أرسل الآن", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("لا، إلغاء", callback_data="cancel_broadcast")],
        ]
        await message.reply_text(
            "تم استقبال رسالة محوّلة. هل تريد تحويل هذه الرسالة كما هي لجميع المستخدمين؟",
            reply_markup=InlineKeyboardMarkup(confirm_keyboard),
        )
        return BROADCAST_MESSAGE

    if message.text:
        context.user_data["broadcast_type"] = "text"
        context.user_data["broadcast_content"] = message.text
        context.user_data["broadcast_entities"] = message.entities
        await message.reply_text(
            "⚠️ هل أنت متأكد من إرسال هذه الرسالة لجميع المستخدمين؟",
            reply_markup=InlineKeyboardMarkup(add_button_keyboard),
        )
        return BROADCAST_MESSAGE
    elif message.photo:
        context.user_data["broadcast_type"] = "photo"
        context.user_data["broadcast_photo"] = message.photo[-1].file_id
        context.user_data["broadcast_caption"] = message.caption or ""
        context.user_data["broadcast_caption_entities"] = message.caption_entities
        await message.reply_photo(
            photo=message.photo[-1].file_id,
            caption=message.caption or "",
            caption_entities=message.caption_entities,
            reply_markup=InlineKeyboardMarkup(add_button_keyboard),
        )
        return BROADCAST_MESSAGE
    elif message.sticker:
        context.user_data["broadcast_type"] = "sticker"
        context.user_data["broadcast_sticker"] = message.sticker.file_id
        await message.reply_sticker(
            sticker=message.sticker.file_id,
            reply_markup=InlineKeyboardMarkup(add_button_keyboard),
        )
        return BROADCAST_MESSAGE
    else:
        await message.reply_text("❌ نوع الرسالة غير مدعوم. أرسل نص أو صورة أو ملصق فقط.")
        return BROADCAST_MESSAGE

async def add_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إضافة زر رابط للبرودكاست"""
    query = update.callback_query
    await safe_answer_query(query)
    try:
        await query.edit_message_text(
            "أرسل اسم الزر الذي تريد إضافته (مثال: اضغط هنا):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="admin_panel")]]),
        )
    except Exception as e:
        logger.warning(f"edit_message_text failed: {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text="أرسل اسم الزر الذي تريد إضافته (مثال: اضغط هنا):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="admin_panel")]]),
        )
    return BROADCAST_BUTTON_NAME

async def set_broadcast_button_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تعيين اسم الزر"""
    button_name = update.message.text.strip()
    context.user_data["broadcast_button"] = button_name
    await update.message.reply_text(
        "الآن أرسل رابط الزر (يجب أن يبدأ بـ http:// أو https://):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="admin_panel")]]),
    )
    return BROADCAST_BUTTON_URL

async def set_broadcast_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تعيين رابط الزر"""
    url = update.message.text.strip()
    if not re.match(r"^https?://", url):
        await update.message.reply_text("❌ الرابط غير صحيح. يجب أن يبدأ بـ http:// أو https://")
        return BROADCAST_BUTTON_URL
    context.user_data["broadcast_button_url"] = url

    b_type = context.user_data.get("broadcast_type")
    add_button = [[InlineKeyboardButton(context.user_data["broadcast_button"], url=context.user_data["broadcast_button_url"])]]
    confirm_keyboard = [
        [InlineKeyboardButton("نعم، أرسل الآن", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("لا، إلغاء", callback_data="cancel_broadcast")],
    ]
    reply_markup = InlineKeyboardMarkup(add_button + confirm_keyboard)

    if b_type == "text":
        await update.message.reply_text(
            context.user_data["broadcast_content"],
            entities=context.user_data.get("broadcast_entities"),
            reply_markup=reply_markup,
        )
    elif b_type == "photo":
        await update.message.reply_photo(
            photo=context.user_data["broadcast_photo"],
            caption=context.user_data.get("broadcast_caption", ""),
            caption_entities=context.user_data.get("broadcast_caption_entities"),
            reply_markup=reply_markup,
        )
    elif b_type == "sticker":
        await update.message.reply_sticker(
            sticker=context.user_data["broadcast_sticker"], 
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ نوع الرسالة غير مدعوم.")
    return BROADCAST_MESSAGE

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تأكيد وإرسال البرودكاست"""
    query = update.callback_query
    await safe_answer_query(query)
    
    if query.data == "cancel_broadcast":
        if query.message and query.message.text:
            await query.edit_message_text("تم إلغاء البرودكاست.")
        else:
            await context.bot.send_message(chat_id=query.from_user.id, text="تم إلغاء البرودكاست.")
        return ConversationHandler.END

    # منع تشغيل أكثر من برودكاست لنفس الأدمن
    try:
        running = context.bot_data.setdefault("broadcast_tasks", {})
        uid = query.from_user.id
        if uid in running:
            tinfo = running.get(uid)
            task = tinfo.get("task") if isinstance(tinfo, dict) else None
            if task and not task.done():
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="يوجد برودكاست قيد التنفيذ بالفعل. يمكنك إلغاؤه من رسالة الحالة."
                )
                return BROADCAST_MESSAGE
    except Exception:
        pass

    # رسالة الحالة
    control_kb_running = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏸️ إيقاف مؤقت", callback_data="pause_broadcast_run")],
        [InlineKeyboardButton("⛔ إلغاء البرودكاست", callback_data="cancel_broadcast_run")],
    ])
    control_kb_paused = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ استئناف", callback_data="resume_broadcast_run")],
        [InlineKeyboardButton("⛔ إلغاء البرودكاست", callback_data="cancel_broadcast_run")],
    ])
    
    status_msg = None
    try:
        status_msg = await context.bot.send_message(
            chat_id=query.from_user.id,
            text="بدء إرسال البرودكاست في الخلفية...",
            reply_markup=control_kb_running,
        )
    except Exception as e:
        logger.warning(f"Failed to send status message: {e}")

    # جلب المستخدمين
    users = db.get_all_users()
    success = 0
    failed = 0
    total = len(users)

    b_type = context.user_data.get("broadcast_type")
    button = context.user_data.get("broadcast_button")
    button_url = context.user_data.get("broadcast_button_url")
    reply_markup = None
    if button and button_url:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(button, url=button_url)]])

    # دالة الإرسال
    async def _send_one(uid: int) -> bool:
        max_retries = 5
        delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                if b_type == "text":
                    await context.bot.send_message(
                        chat_id=uid,
                        text=context.user_data["broadcast_content"],
                        entities=context.user_data.get("broadcast_entities"),
                        reply_markup=reply_markup,
                        parse_mode=None,
                    )
                elif b_type == "photo":
                    await context.bot.send_photo(
                        chat_id=uid,
                        photo=context.user_data["broadcast_photo"],
                        caption=context.user_data.get("broadcast_caption", ""),
                        caption_entities=context.user_data.get("broadcast_caption_entities"),
                        reply_markup=reply_markup,
                    )
                elif b_type == "sticker":
                    await context.bot.send_sticker(
                        chat_id=uid,
                        sticker=context.user_data["broadcast_sticker"],
                        reply_markup=reply_markup,
                    )
                elif b_type == "forward":
                    from_chat_id = context.user_data.get("broadcast_from_chat_id")
                    msg_id = context.user_data.get("broadcast_message_id")
                    await context.bot.forward_message(
                        chat_id=uid, from_chat_id=from_chat_id, message_id=msg_id
                    )
                else:
                    return False
                return True
            except RetryAfter as e:
                wait_for = int(getattr(e, "retry_after", 1)) + 1
                logger.warning(f"Rate limited. Sleeping {wait_for}s (uid={uid})")
                await asyncio.sleep(wait_for)
                continue
            except (TimedOut, NetworkError) as e:
                logger.warning(f"Network issue for {uid}: {e}. Retry in {delay}s")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 10)
                continue
            except Forbidden:
                if BROADCAST_PRUNE_BLOCKED:
                    db.delete_user(uid)
                logger.info(f"User {uid} blocked bot")
                return False
            except BadRequest as e:
                logger.info(f"BadRequest for {uid}: {e}")
                return False
            except Exception as e:
                logger.error(f"Failed to send to {uid}: {e}")
                return False
        return False

    sem = asyncio.Semaphore(BROADCAST_CONCURRENCY)

    async def _worker(uid: int):
        nonlocal success, failed
        async with sem:
            ok = await _send_one(uid)
            if ok:
                success += 1
            else:
                failed += 1

    pause_event = asyncio.Event()
    pause_event.set()

    async def _run_background():
        nonlocal success, failed
        try:
            for i in range(0, total, BROADCAST_BATCH_SIZE):
                await pause_event.wait()
                batch = users[i:i + BROADCAST_BATCH_SIZE]
                tasks = [asyncio.create_task(_worker(u["telegram_id"])) for u in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                try:
                    if status_msg:
                        await context.bot.edit_message_text(
                            chat_id=status_msg.chat.id,
                            message_id=status_msg.message_id,
                            text=f"جاري الإرسال... {success} ناجح / {failed} فاشل من {total}",
                            reply_markup=control_kb_running if pause_event.is_set() else control_kb_paused,
                        )
                except Exception:
                    pass
                await asyncio.sleep(BROADCAST_BATCH_DELAY)

            report = (
                f"✅ تم إرسال البرودكاست بنجاح!\n\n"
                f"📊 الإحصائيات:\n"
                f"✔ تم الإرسال بنجاح: {success}\n"
                f"✖ فشل الإرسال: {failed}"
            )
            try:
                if status_msg:
                    await context.bot.edit_message_text(
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id,
                        text=report,
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="admin_panel")]]),
                    )
            except Exception as e:
                logger.warning(f"Failed to update final report: {e}")
        except asyncio.CancelledError:
            try:
                if status_msg:
                    await context.bot.edit_message_text(
                        chat_id=status_msg.chat.id,
                        message_id=status_msg.message_id,
                        text=f"⛔ تم إلغاء البرودكاست.\n\n✔ نجح: {success}\n✖ فشل: {failed}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="admin_panel")]]),
                    )
            except Exception:
                pass
            raise
        finally:
            running = context.bot_data.setdefault("broadcast_tasks", {})
            running.pop(query.from_user.id, None)

    try:
        task = asyncio.create_task(_run_background())
        running = context.bot_data.setdefault("broadcast_tasks", {})
        running[query.from_user.id] = {
            "task": task,
            "status_chat_id": status_msg.chat.id if status_msg else None,
            "status_message_id": status_msg.message_id if status_msg else None,
            "pause_event": pause_event,
        }
    except Exception as e:
        logger.error(f"Failed to schedule broadcast: {e}")

    try:
        if query and query.message:
            await query.edit_message_text("تم بدء إرسال البرودكاست في الخلفية.")
    except Exception:
        pass

    return ConversationHandler.END

async def cancel_broadcast_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء البرودكاست الجاري"""
    query = update.callback_query
    await safe_answer_query(query)
    uid = query.from_user.id
    running = context.bot_data.setdefault("broadcast_tasks", {})
    info = running.get(uid)
    task = info.get("task") if isinstance(info, dict) else None
    if not task or task.done():
        await context.bot.send_message(chat_id=uid, text="لا توجد عملية برودكاست قيد التشغيل.")
        running.pop(uid, None)
        return
    try:
        task.cancel()
        await context.bot.send_message(chat_id=uid, text="جاري إلغاء البرودكاست...")
    except Exception:
        pass

async def pause_broadcast_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف مؤقت للبث"""
    query = update.callback_query
    await safe_answer_query(query)
    uid = query.from_user.id
    running = context.bot_data.setdefault("broadcast_tasks", {})
    info = running.get(uid)
    if not info:
        await context.bot.send_message(chat_id=uid, text="لا توجد عملية برودكاست قيد التشغيل.")
        return
    pause_event = info.get("pause_event")
    status_chat_id = info.get("status_chat_id")
    status_message_id = info.get("status_message_id")
    try:
        if pause_event:
            pause_event.clear()
        if status_chat_id and status_message_id:
            await context.bot.edit_message_reply_markup(
                chat_id=status_chat_id,
                message_id=status_message_id,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ استئناف", callback_data="resume_broadcast_run")],
                    [InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_broadcast_run")],
                ]),
            )
    except Exception:
        pass

async def resume_broadcast_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استئناف البث"""
    query = update.callback_query
    await safe_answer_query(query)
    uid = query.from_user.id
    running = context.bot_data.setdefault("broadcast_tasks", {})
    info = running.get(uid)
    if not info:
        await context.bot.send_message(chat_id=uid, text="لا توجد عملية برودكاست قيد التشغيل.")
        return
    pause_event = info.get("pause_event")
    status_chat_id = info.get("status_chat_id")
    status_message_id = info.get("status_message_id")
    try:
        if pause_event:
            pause_event.set()
        if status_chat_id and status_message_id:
            await context.bot.edit_message_reply_markup(
                chat_id=status_chat_id,
                message_id=status_message_id,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⏸️ إيقاف مؤقت", callback_data="pause_broadcast_run")],
                    [InlineKeyboardButton("⛔ إلغاء", callback_data="cancel_broadcast_run")],
                ]),
            )
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# ADMIN WITHDRAWAL HANDLERS
# ═══════════════════════════════════════════════════════════════

async def reject_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض طلب سحب"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    withdrawal_id = int(query.data.split('_')[2])
    
    # رفض الطلب وإعادة المبلغ
    db.reject_withdrawal(withdrawal_id, user_id, "تم الرفض من قبل الأدمن")
    
    # الحصول على معلومات الطلب
    pending = db.get_pending_withdrawals()
    withdrawal = next((w for w in pending if w['id'] == withdrawal_id), None)
    
    # إرسال إشعار للمستخدم
    if withdrawal:
        try:
            await context.bot.send_message(
                chat_id=withdrawal['user_id'],
                text=f"""
❌ <b>تم رفض طلب السحب</b>

💰 المبلغ: {withdrawal['amount']:.4f} TON
📝 السبب: تم الرفض من قبل الإدارة

تم إعادة المبلغ إلى رصيدك. يمكنك المحاولة مرة أخرى.
""",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
    
    await query.edit_message_text(
        f"{icon('cross')} تم رفض الطلب #{withdrawal_id} وإعادة المبلغ",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{icon('back')} رجوع لطلبات السحب", callback_data="admin_withdrawals")
        ]])
    )

# ═══════════════════════════════════════════════════════════════
# 📢 إضافة قناة/مهمة - نظام مبسط
# ═══════════════════════════════════════════════════════════════

async def add_channel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء إضافة قناة جديدة"""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.answer(f"{icon('error')} غير مصرح لك!", show_alert=True)
        return
    
    # طلب رابط القناة فقط
    await query.edit_message_text(
        f"""
{icon('channel')} <b>إضافة قناة/مهمة جديدة</b>

{icon('info')} <b>نوع المهمة:</b> channel/link

{icon('edit')} <b>أرسل رابط القناة:</b>
<code>https://t.me/YourChannel</code>
أو
<code>@YourChannel</code>

{icon('bullet')} سيتم التحقق تلقائياً من أن البوت أدمن في القناة
{icon('bullet')} المكافأة: {TICKETS_PER_TASK} تذكرة لكل قناة
""",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{icon('cross')} إلغاء", callback_data="admin_tasks")
        ]])
    )
    
    return ADD_CHANNEL_LINK

async def add_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال رابط القناة والتحقق منه"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        return ConversationHandler.END
    
    channel_link = update.message.text.strip()
    
    # استخراج username القناة
    if 't.me/' in channel_link:
        channel_username = '@' + channel_link.split('t.me/')[1].strip('/')
    elif channel_link.startswith('@'):
        channel_username = channel_link
    else:
        await update.message.reply_text(
            f"{icon('error')} رابط غير صحيح! أرسل الرابط بالشكل الصحيح.",
            parse_mode=ParseMode.HTML
        )
        return ADD_CHANNEL_LINK
    
    # التحقق من أن البوت أدمن في القناة
    try:
        chat = await context.bot.get_chat(channel_username)
        bot_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if bot_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                f"""
{icon('error')} <b>البوت ليس أدمن في القناة!</b>

{icon('info')} يرجى:
1. إضافة البوت كأدمن في القناة
2. إعطاء صلاحية "Invite Users" على الأقل
3. المحاولة مرة أخرى
""",
                parse_mode=ParseMode.HTML
            )
            return ADD_CHANNEL_LINK
        
        # إضافة القناة إلى API
        try:
            response = requests.post(
                f"{MINI_APP_URL}/api/admin/channels",
                json={
                    'chat_id': chat.id,
                    'username': channel_username.replace('@', ''),
                    'name': chat.title,
                    'mandatory': True,
                    'admin_id': user_id
                }
            )
            result = response.json()
            
            if result.get('success'):
                await update.message.reply_text(
                    f"""
{icon('success')} <b>تم إضافة القناة بنجاح!</b>

{icon('channel')} <b>القناة:</b> {chat.title}
{icon('link')} <b>الرابط:</b> {channel_username}
{icon('ticket')} <b>المكافأة:</b> {TICKETS_PER_TASK} تذكرة

{icon('check')} البوت أدمن في القناة
{icon('check')} القناة نشطة الآن
""",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"{icon('tasks')} إدارة المهام", callback_data="admin_tasks"),
                        InlineKeyboardButton(f"{icon('add')} إضافة أخرى", callback_data="add_channel_start")
                    ]])
                )
            else:
                await update.message.reply_text(
                    f"{icon('error')} خطأ في حفظ القناة: {result.get('error')}",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Error saving channel: {e}")
            await update.message.reply_text(
                f"{icon('error')} خطأ في الاتصال بالخادم",
                parse_mode=ParseMode.HTML
            )
        
    except Forbidden:
        await update.message.reply_text(
            f"{icon('error')} البوت محظور أو غير موجود في القناة!",
            parse_mode=ParseMode.HTML
        )
        return ADD_CHANNEL_LINK
    except BadRequest:
        await update.message.reply_text(
            f"{icon('error')} رابط القناة غير صحيح!",
            parse_mode=ParseMode.HTML
        )
        return ADD_CHANNEL_LINK
    except Exception as e:
        logger.error(f"Error checking channel: {e}")
        await update.message.reply_text(
            f"{icon('error')} خطأ في التحقق من القناة",
            parse_mode=ParseMode.HTML
        )
        return ADD_CHANNEL_LINK
    
    return ConversationHandler.END

async def cancel_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء إضافة قناة"""
    await admin_tasks_callback(update, context)
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# 🌐 FLASK SERVER FOR VERIFICATION
# ═══════════════════════════════════════════════════════════════

verification_app = Flask(__name__)

@verification_app.route('/verify-subscription', methods=['POST'])
def verify_subscription():
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        channel_username = data.get('channel_username')
        
        if not user_id or not channel_username:
            return jsonify({'success': False, 'is_subscribed': False, 'error': 'Missing parameters'}), 400
        
        # إزالة @ إذا كان موجود
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]
        
        # استخدام Telegram Bot API مباشرة
        try:
            import requests as req
            api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getChatMember'
            response = req.post(api_url, json={
                'chat_id': f'@{channel_username}',
                'user_id': user_id
            }, timeout=10)
            
            result = response.json()
            
            if result.get('ok'):
                member = result.get('result', {})
                status = member.get('status', 'left')
                is_subscribed = status in ['member', 'administrator', 'creator']
                
                return jsonify({
                    'success': True,
                    'is_subscribed': is_subscribed,
                    'status': status
                })
            else:
                return jsonify({
                    'success': False,
                    'is_subscribed': False,
                    'error': result.get('description', 'Unknown error')
                }), 500
            
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return jsonify({
                'success': False,
                'is_subscribed': False,
                'error': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error in verify_subscription: {e}")
        return jsonify({'success': False, 'is_subscribed': False, 'error': str(e)}), 500

@verification_app.route('/check-bot-admin', methods=['POST'])
def check_bot_admin():
    """التحقق من أن البوت مشرف في القناة"""
    try:
        data = request.get_json()
        channel_username = data.get('channel_username')
        
        if not channel_username:
            return jsonify({'success': False, 'is_admin': False, 'error': 'Missing channel_username'}), 400
        
        # إزالة @ إذا كان موجود
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]
        
        # استخدام Telegram Bot API مباشرة
        try:
            import requests as req
            
            # الحصول على bot_id أولاً
            me_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getMe'
            me_response = req.get(me_url, timeout=10)
            me_result = me_response.json()
            
            if not me_result.get('ok'):
                return jsonify({
                    'success': False,
                    'is_admin': False,
                    'error': 'Failed to get bot info'
                }), 500
            
            bot_id = me_result['result']['id']
            
            # التحقق من أن البوت مشرف
            api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getChatMember'
            response = req.post(api_url, json={
                'chat_id': f'@{channel_username}',
                'user_id': bot_id
            }, timeout=10)
            
            result = response.json()
            
            if result.get('ok'):
                member = result.get('result', {})
                status = member.get('status', 'left')
                is_admin = status in ['administrator', 'creator']
                
                return jsonify({
                    'success': True,
                    'is_admin': is_admin,
                    'status': status
                })
            else:
                return jsonify({
                    'success': False,
                    'is_admin': False,
                    'error': result.get('description', 'Unknown error')
                }), 500
            
        except Exception as e:
            logger.error(f"Error checking bot admin: {e}")
            return jsonify({
                'success': False,
                'is_admin': False,
                'error': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error in check_bot_admin: {e}")
        return jsonify({'success': False, 'is_admin': False, 'error': str(e)}), 500

@verification_app.route('/send-welcome', methods=['POST'])
def send_welcome_message():
    """إرسال رسالة ترحيبية للمستخدم عند فتح المينى آب"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        username = data.get('username', '')
        full_name = data.get('full_name', 'مستخدم')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
        # استخدام Telegram Bot API مباشرة
        try:
            import requests as req
            
            welcome_text = f"""
🎉 <b>مرحباً بك في Panda Giveaways!</b>

<b>{full_name}</b>، سعداء بانضمامك! 🎁

💰 استمتع بالأرباح اليومية
🎰 العب عجلة الحظ
👥 ادعُ أصدقاءك واربح المزيد
💎 اسحب أرباحك مباشرة

🚀 <b>ابدأ الآن وحقق أرباحك!</b>
"""
            
            api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
            response = req.post(api_url, json={
                'chat_id': user_id,
                'text': welcome_text,
                'parse_mode': 'HTML'
            }, timeout=10)
            
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"✅ Welcome message sent to user {user_id}")
                
                # تسجيل المستخدم في قاعدة البيانات
                if username:
                    db.create_or_update_user(user_id, username, full_name, None)
                
                return jsonify({
                    'success': True,
                    'message': 'Welcome message sent'
                })
            else:
                error_desc = result.get('description', 'Unknown error')
                logger.warning(f"⚠️ Failed to send welcome to {user_id}: {error_desc}")
                return jsonify({
                    'success': False,
                    'error': error_desc,
                    'need_start': 'bot was blocked' in error_desc.lower() or 'user is deactivated' in error_desc.lower()
                })
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error in send_welcome_message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def run_flask_server():
    """تشغيل Flask server في thread منفصل"""
    try:
        logger.info("🌐 Starting Flask verification server on port 8081...")
        verification_app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")

# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

def main():
    """تشغيل البوت"""
    
    # التحقق من التوكن
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set your BOT_TOKEN!")
        return
    
    logger.info("🐼 Starting Panda Giveaways Bot...")
    logger.info(f"🤖 Bot Username: @{BOT_USERNAME}")
    logger.info(f"🌐 Mini App URL: {MINI_APP_URL}")
    logger.info(f"👥 Admins: {ADMIN_IDS}")
    
    # تشغيل Flask server في thread منفصل
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask verification server started on port 8081")
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("referrals", referrals_command))
    application.add_handler(CommandHandler("balance", balance_command))
    
    # معالج Inline Query
    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    # معالجات Callback
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_withdrawals_callback, pattern="^admin_withdrawals$"))
    application.add_handler(CallbackQueryHandler(admin_tasks_callback, pattern="^admin_tasks$"))
    application.add_handler(CallbackQueryHandler(admin_check_user_callback, pattern="^admin_check_user$"))
    application.add_handler(CallbackQueryHandler(admin_detailed_stats_callback, pattern="^admin_detailed_stats$"))
    application.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    application.add_handler(CallbackQueryHandler(approve_withdrawal_callback, pattern="^approve_withdrawal_"))
    application.add_handler(CallbackQueryHandler(reject_withdrawal_callback, pattern="^reject_withdrawal_"))
    
    # ConversationHandler لإضافة القنوات
    add_channel_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_channel_start, pattern="^add_channel_start$")],
        states={
            ADD_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_channel_link)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_channel, pattern="^admin_tasks$"),
            CommandHandler("cancel", cancel_add_channel)
        ],
        allow_reentry=True
    )
    application.add_handler(add_channel_handler)
    
    # معالجات البرودكاست
    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern="^start_broadcast$")],
        states={
            BROADCAST_MESSAGE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, send_broadcast),
                CallbackQueryHandler(confirm_broadcast, pattern="^(confirm_broadcast|cancel_broadcast)$"),
                CallbackQueryHandler(add_broadcast_button, pattern="^add_broadcast_button$"),
            ],
            BROADCAST_BUTTON_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_broadcast_button_name)],
            BROADCAST_BUTTON_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_broadcast_button_url)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        ],
    )
    application.add_handler(broadcast_handler)
    
    # معالجات التحكم بالبرودكاست (pause/resume/cancel)
    application.add_handler(CallbackQueryHandler(cancel_broadcast_run, pattern="^cancel_broadcast_run$"))
    application.add_handler(CallbackQueryHandler(pause_broadcast_run, pattern="^pause_broadcast_run$"))
    application.add_handler(CallbackQueryHandler(resume_broadcast_run, pattern="^resume_broadcast_run$"))
    
    # تشغيل البوت
    logger.info("✅ Bot is running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
