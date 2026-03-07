"""
╔══════════════════════════════════════════════════════════════════╗
║                  🐼 PANDA GIVEAWAYS BOT 🐼                       ║
║           Professional Telegram Giveaway & Rewards Bot           ║
║                    Version 1.0.0 - Ultra Secure                  ║
╚══════════════════════════════════════════════════════════════════╝

بوت احترافي للأرباح والإحالات على تيليجرام
مع Mini App متكامل - عجلة الحظ - نظام الإحالات - المهام - السحوبات
أمان عالي المستوى ضد التلاعب

⚠️ ملاحظة مهمة:
هذا البوت يستخدم قاعدة البيانات المشتركة من app.py لضمان:
✅ نفس المستخدمين في البوت والموقع
✅ نفس الإحالات والإحصائيات
✅ نفس القنوات الإجبارية
✅ نفس اللفات والرصيد

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
import shutil
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
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://" + os.getenv("REPLIT_DEV_DOMAIN", "localhost:5000"))

# 👥 الأدمن (يتم قراءتهم من .env)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]

# 📢 قناة إثباتات الدفع
PAYMENT_PROOF_CHANNEL = os.getenv("PAYMENT_PROOF_CHANNEL")

# 📢 قنوات الاشتراك الإجباري (سيتم تحميلها من قاعدة البيانات)
MANDATORY_CHANNELS = []

# 🎁 إعدادات عجلة الحظ (النسب والجوائز - مطابقة لـ config.js)
WHEEL_PRIZES = [
    {"name": "0.05 TON", "amount": 0.05, "probability": 94},   # 94%
    {"name": "0.1 TON", "amount": 0.1, "probability": 5},      # 5%
    {"name": "0.15 TON", "amount": 0.15, "probability": 1},    # 1%
    {"name": "0.5 TON", "amount": 0.5, "probability": 0},      # 0%
    {"name": "1.0 TON", "amount": 1.0, "probability": 0},      # 0%
    {"name": "0.25 TON", "amount": 0.25, "probability": 0}     # 0%
]

# 💰 إعدادات الإحالات والمهام
SPINS_PER_REFERRALS = 5  # عدد الإحالات للحصول على لفة
TICKETS_PER_TASK = 1  # عدد التذاكر لكل مهمة
TICKETS_FOR_SPIN = 5  # عدد التذاكر للحصول على لفة
REFERRALS_FOR_SPIN = 5  # عدد الإحالات للحصول على لفة
MIN_WITHDRAWAL_AMOUNT = 0.1  # 0.1 TON لكل طرق السحب

# 💳 إعدادات محفظة TON (للتحقق من المعاملات فقط - لا إرسال)
# ⛔ لن يتم استخدام WALLET_MNEMONIC بتاتاً لأسباب أمنية
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "UQAcDae1BvWVAD0TkhnGgDme4b7NH9Fz8JXce-78TW6ekmvN")  # محفظة الاستقبال فقط

# 💸 محفظة الأدمن للسحوبات (المحفظة التي ترسل منها المبالغ للعملاء)
ADMIN_WITHDRAWAL_WALLET = os.getenv("ADMIN_WITHDRAWAL_WALLET", "UQAcDae1BvWVAD0TkhnGgDme4b7NH9Fz8JXce-78TW6ekmvN")  # نفس المحفظة افتراضياً

TON_API_KEY = os.getenv("TON_API_KEY", "")  # للتحقق من المعاملات

# ⛔ تم إزالة WALLET_MNEMONIC تماماً من الكود
# ❌ الدفع سيكون يدوي 100%

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
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://" + os.getenv("REPLIT_DEV_DOMAIN", "localhost:5000"))

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
    RESTORE_BACKUP,  # جديد: لاستعادة النسخة الاحتياطية
) = range(6)

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
    ban_reason: Optional[str] = None  # سبب الحظر
    
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
        
        # جدول القنوات الإجبارية (مشترك مع الموقع - required_channels)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                channel_name TEXT NOT NULL,
                channel_url TEXT,
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
        
        # جدول إعدادات البوت
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by INTEGER
            )
        """)
        
        # إضافة الإعدادات الافتراضية
        cursor.execute("""
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES ('auto_withdrawal_enabled', 'false', ?)
        """, (datetime.now().isoformat(),))
        
        cursor.execute("""
            INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES ('bot_enabled', 'true', ?)
        """, (datetime.now().isoformat(),))
        
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
            
            # ملاحظة: لا نسجل الإحالة هنا - سيتم تسجيلها في check_subscription_callback
            # بعد التحقق من الاشتراك في القنوات والتحقق من الجهاز
            if referrer_id:
                logger.info(f"📝 Referrer saved for new user: {referrer_id} -> {user_id} (pending verification)")
            
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
            # التحقق من وجود عمود ban_reason
            try:
                ban_reason_value = row['ban_reason'] if 'ban_reason' in row.keys() else None
            except (KeyError, IndexError):
                ban_reason_value = None
            
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
                ban_reason=ban_reason_value,
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
    
    def validate_referral(self, referred_id: int, channels_checked: bool = True, device_verified: bool = True) -> bool:
        """
        التحقق من صحة الإحالة (بعد الاشتراك بالقنوات والتحقق من الجهاز)
        
        Args:
            referred_id: معرف المستخدم المُحال
            channels_checked: هل تم التحقق من اشتراك المستخدم في القنوات الإجبارية
            device_verified: هل تم التحقق من جهاز المستخدم
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # التحقق من استيفاء جميع الشروط
        if not (channels_checked and device_verified):
            logger.warning(f"⚠️ Referral validation pending for user {referred_id}: channels={channels_checked}, device={device_verified}")
            
            # تحديث حالة التحقق
            cursor.execute("""
                UPDATE referrals 
                SET channels_checked = ?, device_verified = ?
                WHERE referred_id = ?
            """, (1 if channels_checked else 0, 1 if device_verified else 0, referred_id))
            
            conn.commit()
            conn.close()
            return False
        
        # تحديث حالة الإحالة كصحيحة
        cursor.execute("""
            UPDATE referrals 
            SET is_valid = 1, validated_at = ?, channels_checked = 1, device_verified = 1
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
                logger.info(f"✅ Referral validated successfully for user {referred_id}")
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
    
    async def process_auto_withdrawal(self, withdrawal_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """معالجة السحب التلقائي"""
        try:
            # الحصول على معلومات السحب
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT w.*, u.username, u.full_name
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.id = ? AND w.status = 'pending'
            """, (withdrawal_id,))
            
            withdrawal = cursor.fetchone()
            conn.close()
            
            if not withdrawal:
                logger.error(f"❌ Withdrawal {withdrawal_id} not found or not pending")
                return False
            
            withdrawal_dict = dict(withdrawal)
            
            # التحقق من نوع السحب والمحفظة
            if withdrawal_dict['withdrawal_type'] != 'ton' or not withdrawal_dict['wallet_address']:
                logger.info(f"⚠️ Withdrawal {withdrawal_id} is not TON type or missing wallet")
                return False
            
            # التحقق من توفر TON Wallet
            if not ton_wallet:
                logger.error("❌ TON Wallet not initialized")
                return False
            
            # محاولة السحب التلقائي
            logger.info(f"🚀 Starting auto withdrawal for request #{withdrawal_id}")
            
            tx_hash = await ton_wallet.send_ton(
                withdrawal_dict['wallet_address'],
                withdrawal_dict['amount'],
                f"Panda Giveaways Withdrawal #{withdrawal_id}"
            )
            
            if tx_hash:
                # الموافقة على السحب
                self.approve_withdrawal(withdrawal_id, 0, tx_hash)  # 0 = automatic
                
                # إرسال إشعار للمستخدم
                try:
                    await context.bot.send_message(
                        chat_id=withdrawal_dict['user_id'],
                        text=f"""
<tg-emoji emoji-id='5388674524583572460'>🎉</tg-emoji> <b>تم تأكيد السحب!</b>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> تم تحويل {withdrawal_dict['amount']:.4f} TON إلى محفظتك
<tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> TX Hash: <code>{tx_hash}</code>

شكراً لاستخدامك Panda Giveaways! <tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji>
""",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification: {e}")
                
                # نشر إثبات الدفع في القناة
                await send_payment_proof_to_channel(
                    context=context,
                    username=withdrawal_dict.get('username', 'مستخدم'),
                    full_name=withdrawal_dict['full_name'],
                    user_id=withdrawal_dict['user_id'],
                    amount=withdrawal_dict['amount'],
                    wallet_address=withdrawal_dict['wallet_address'],
                    tx_hash=tx_hash,
                    withdrawal_id=withdrawal_id
                )
                
                logger.info(f"✅ Auto withdrawal {withdrawal_id} completed successfully")
                return True
            else:
                logger.error(f"❌ Auto withdrawal {withdrawal_id} failed - TX Hash is None")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in auto withdrawal {withdrawal_id}: {e}")
            return False
    
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
                INSERT INTO required_channels 
                (channel_id, channel_name, channel_url, added_by, added_at)
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
        """الحصول على القنوات الإجبارية النشطة من جدول required_channels (مشترك مع الموقع)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM required_channels 
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
    # ⚙️ BOT SETTINGS OPERATIONS
    # ═══════════════════════════════════════════════════════════
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """الحصول على قيمة إعداد"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row['setting_value']
        return default
    
    def set_setting(self, key: str, value: str, admin_id: int):
        """تعيين قيمة إعداد"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO bot_settings (setting_key, setting_value, updated_at, updated_by)
            VALUES (?, ?, ?, ?)
        """, (key, value, now, admin_id))
        
        conn.commit()
        conn.close()
        logger.info(f"⚙️ Setting {key} = {value} by admin {admin_id}")
    
    def is_auto_withdrawal_enabled(self) -> bool:
        """التحقق من تفعيل السحب التلقائي"""
        value = self.get_setting('auto_withdrawal_enabled', 'false')
        return value.lower() == 'true'
    
    def is_bot_enabled(self) -> bool:
        """التحقق من تشغيل البوت"""
        value = self.get_setting('bot_enabled', 'true')
        return value.lower() == 'true'
    
    def toggle_bot_status(self, admin_id: int) -> bool:
        """تبديل حالة البوت (تشغيل/إيقاف)"""
        current_status = self.is_bot_enabled()
        new_status = 'false' if current_status else 'true'
        self.set_setting('bot_enabled', new_status, admin_id)
        return not current_status
    
    # ═══════════════════════════════════════════════════════════
    # 📊 STATISTICS & ANALYTICS
    # ═══════════════════════════════════════════════════════════
    
    def get_all_users(self) -> List[Dict]:
        """الحصول على جميع المستخدمين للبرودكاست - بدون أي فلتر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # إرسال لجميع المستخدمين بدون فلتر (حتى المحظورين)
        cursor.execute("SELECT user_id as telegram_id FROM users")
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
        logger.info("🔧 Initializing TONWalletManager...")
        logger.info(f"   Wallet Address: {wallet_address[:20]}..." if wallet_address else "   Wallet Address: MISSING")
        logger.info(f"   Mnemonic words: {len(mnemonic)} words")
        logger.info(f"   API Key: {'SET' if api_key else 'MISSING'}")
        logger.info(f"   TON_SDK_AVAILABLE: {TON_SDK_AVAILABLE}")
        
        self.wallet_address = wallet_address
        self.mnemonic = mnemonic
        self.api_key = api_key
        self.api_endpoint = "https://toncenter.com/api/v2/"
        self.api_headers = {"X-API-Key": api_key} if api_key else {}
        
        if not TON_SDK_AVAILABLE:
            logger.error("❌ TON SDK not available! Install: pip install tonsdk")
            self.wallet_obj = None
            return
            
        if not mnemonic or len(mnemonic) != 24:
            logger.error(f"❌ Invalid mnemonic! Expected 24 words, got {len(mnemonic)}")
            self.wallet_obj = None
            return
        
        logger.info("✅ Prerequisites OK, calling _init_wallet()...")
        self._init_wallet()
    
    def _init_wallet(self):
        """تهيئة المحفظة"""
        logger.info("🔑 Starting wallet initialization...")
        try:
            # جرب v4r2 أولاً (أقرب حاجة لـ v5r1 في tonsdk القديم)
            logger.info("📝 Trying wallet version v4r2...")
            try:
                mnemonics, _pub_k, _priv_k, wallet = Wallets.from_mnemonics(
                    self.mnemonic, 
                    WalletVersionEnum.v4r2, 
                    0
                )
                version_used = "v4r2"
            except AttributeError:
                logger.warning("⚠️ v4r2 not available, trying v3r2...")
                mnemonics, _pub_k, _priv_k, wallet = Wallets.from_mnemonics(
                    self.mnemonic, 
                    WalletVersionEnum.v3r2, 
                    0
                )
                version_used = "v3r2"
            
            self.wallet_obj = wallet
            
            # الحصول على العنوان الحقيقي من الـ mnemonic
            generated_address = wallet.address.to_string(True, True, True)
            
            # محاولة التحويل بين UQ و EQ (bounceable/non-bounceable)
            # كلاهما نفس المحفظة، فقط format مختلف
            configured_normalized = self.wallet_address.replace('UQ', 'EQ') if self.wallet_address.startswith('UQ') else self.wallet_address
            generated_normalized = generated_address.replace('UQ', 'EQ') if generated_address.startswith('UQ') else generated_address
            
            logger.info(f"✅ TON Wallet initialized successfully (using {version_used})")
            logger.info(f"📍 Generated Address (from mnemonic): {generated_address}")
            logger.info(f"📍 Configured Address (TON_WALLET_ADDRESS): {self.wallet_address}")
            
            # التحقق من التطابق (بعد تطبيع الـ format)
            if configured_normalized == generated_normalized:
                logger.info("✅ Address verification: PERFECT MATCH! 🎉")
                logger.info("✅ Automatic withdrawals are ENABLED")
                # استخدام العنوان المولّد للتأكد من الصحة
                self.wallet_address = generated_address
            else:
                logger.error("=" * 80)
                logger.error("⚠️⚠️⚠️ CRITICAL WARNING ⚠️⚠️⚠️")
                logger.error("=" * 80)
                logger.error("❌ MISMATCH: The mnemonic generates a DIFFERENT wallet address!")
                logger.error(f"   Mnemonic generates ({version_used}): {generated_address}")
                logger.error(f"   But you configured:  {self.wallet_address}")
                logger.error("")
                logger.error("🔧 FIX OPTIONS:")
                logger.error("   1. Update TON_WALLET_ADDRESS to match the generated address:")
                logger.error(f"      TON_WALLET_ADDRESS={generated_address}")
                logger.error("")
                logger.error("   2. OR use the correct mnemonic for your configured address")
                logger.error("")
                logger.error("   3. OR try different wallet version (v3r2, v4r1, v4r2)")
                logger.error("")
                logger.error("⚠️ AUTOMATIC WITHDRAWALS DISABLED until this is fixed!")
                logger.error("   Manual withdrawals will still work.")
                logger.error("=" * 80)
                
                # استخدام العنوان الصحيح من الـ mnemonic
                self.wallet_address = generated_address
                logger.warning(f"⚠️ Using generated address: {generated_address}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize TON wallet: {e}")
            logger.error(f"   Exception type: {type(e).__name__}")
            import traceback
            logger.error(traceback.format_exc())
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
                    
                    # محاولة الحصول على TX Hash الحقيقي من الشبكة
                    real_tx_hash = await self.get_real_transaction_hash(to_address, amount_nano, seqno)
                    if real_tx_hash:
                        logger.info(f"✅ Got real TX hash from network: {real_tx_hash}")
                        return real_tx_hash
                    
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
    
    async def get_real_transaction_hash(self, to_address: str, amount_nano: int, seqno: int, max_attempts: int = 10) -> Optional[str]:
        """الحصول على TX Hash الحقيقي من الشبكة بعد الإرسال"""
        try:
            logger.info("🔍 Waiting for transaction to appear on blockchain...")
            await asyncio.sleep(5)  # انتظار أطول لتأكيد المعاملة
            
            for attempt in range(max_attempts):
                try:
                    # استخدام endpoint مختلف - getAddressInformation مع المحفظة
                    url = f"{self.api_endpoint}getAddressInformation"
                    params = {'address': self.wallet_address}
                    
                    response = requests.get(url, params=params, headers=self.api_headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get('ok') and 'result' in data:
                            result = data['result']
                            last_tx = result.get('last_transaction_id', {})
                            
                            # الحصول على hash من آخر معاملة
                            if last_tx and 'hash' in last_tx:
                                tx_hash_b64 = last_tx['hash']
                                
                                # تحويل من base64 إلى hex
                                try:
                                    import base64
                                    hash_bytes = base64.b64decode(tx_hash_b64 + '==')
                                    hex_hash = hash_bytes.hex()
                                    logger.info(f"✅ Found transaction hash: {hex_hash}")
                                    
                                    # التحقق أن هذه هي المعاملة الصحيحة عبر جلب تفاصيلها
                                    # يمكن إضافة تحقق إضافي هنا
                                    
                                    return hex_hash
                                except Exception as e:
                                    logger.warning(f"⚠️ Error converting hash: {e}")
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
                        logger.info(f"⏳ Transaction not found yet, retrying ({attempt + 1}/{max_attempts})...")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error fetching transaction: {e}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(2)
            
            logger.warning("⚠️ Could not get real transaction hash from network")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting real transaction hash: {e}")
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

# ═══════════════════════════════════════════════════════════════
# 🔐 REFERRAL VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════

async def check_and_validate_referral(user_id: int, update: Update = None) -> bool:
    """
    التحقق الشامل من الإحالة (التحقق من الجهاز + القنوات + التحقق النهائي)
    يتم استدعاؤها بعد التحقق من الاشتراك في القنوات أو التحقق من الجهاز
    """
    try:
        import requests as req
        
        # 1. التحقق من حالة التحقق من الجهاز
        verify_status_url = f"{API_BASE_URL}/verification/status/{user_id}"
        verify_resp = req.get(verify_status_url, timeout=5)
        
        device_verified = False
        if verify_resp.ok:
            verify_data = verify_resp.json()
            device_verified = verify_data.get('verified', False)
        
        # 2. التحقق من الاشتراك في جميع القنوات الإجبارية
        channels_checked = True
        for channel_username in MANDATORY_CHANNELS:
            if update:
                if not await check_subscription(user_id, channel_username, update):
                    channels_checked = False
                    break
        
        # 3. إذا تم التحقق من كل شيء، قم بالتحقق من صحة الإحالة
        if device_verified and channels_checked:
            success = db.validate_referral(user_id, 
                                          channels_checked=True, 
                                          device_verified=True)
            
            if success:
                logger.info(f"✅ Complete referral validation for user {user_id}")
                return True
        else:
            # تحديث حالة الإحالة الجزئية
            db.validate_referral(user_id, 
                               channels_checked=channels_checked, 
                               device_verified=device_verified)
            
            logger.info(f"⏳ Partial referral validation for user {user_id}: device={device_verified}, channels={channels_checked}")
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error in check_and_validate_referral: {e}")
        return False
wheel = WheelOfFortune(WHEEL_PRIZES)

# ⛔ تم تعطيل الدفع التلقائي نهائياً لأسباب أمنية
# ❌ لن يتم استخدام WALLET_MNEMONIC بتاتاً
ton_wallet = None

# if TON_SDK_AVAILABLE and TON_WALLET_ADDRESS and WALLET_MNEMONIC:
#     ton_wallet = TONWalletManager(TON_WALLET_ADDRESS, WALLET_MNEMONIC, TON_API_KEY)

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

def check_subscription(user_id: int, channel_username: str, update: Update = None) -> bool:
    """التحقق من اشتراك المستخدم في قناة معينة"""
    try:
        # إزالة @ من اسم القناة إن وجد
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]
        
        # محاولة الحصول على عضوية المستخدم في القناة
        # ملاحظة: نحتاج لاستخدام طريقة مختلفة لأن هذه دالة sync
        # في التطبيق الفعلي، يُستدعى هذا من البوت مباشرة
        
        return False  # افتراضياً نرجع خطأ للأمان
    except Exception as e:
        logger.error(f"Error checking subscription for {channel_username}: {e}")
        return False

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
        ref_link = generate_referral_link(user_id)  # استخدام start بدلاً من startapp
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
    
    # ══════════════════════════════════════════════════════════
    # 🔴 التحقق من حالة البوت أولاً (إلا للأدمن)
    # ══════════════════════════════════════════════════════════
    if not is_admin(user_id) and not db.is_bot_enabled():
        # إرسال رسالة بأن البوت معطل
        bot_disabled_text = f"""
<tg-emoji emoji-id='5360054260508063850'>🔴</tg-emoji> <b>البوت مغلق حالياً</b>

عزيزي <b>{full_name}</b>،

البوت غير متاح في الوقت الحالي للصيانة.

<tg-emoji emoji-id='6010227837879983163'>⏰</tg-emoji> سيتم تفعيل البوت قريباً، يرجى المحاولة لاحقاً.

<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> تابعنا للحصول على آخر التحديثات!
"""
        
        await update.message.reply_text(
            bot_disabled_text,
            parse_mode=ParseMode.HTML
        )
        
        return
    
    # استخراج referrer_id إن وجد (فقط من روابط start العادية، ليس startapp)
    referrer_id = None
    is_from_mini_app = False
    
    if context.args:
        arg = context.args[0]
        if arg.startswith('ref_'):
            try:
                potential_referrer = int(arg.split('_')[1])
                # التأكد من عدم إحالة نفسه
                if potential_referrer != user_id:
                    referrer_id = potential_referrer
                    # حفظ referrer_id في context لاستخدامه لاحقاً
                    context.user_data['pending_referrer_id'] = referrer_id
            except:
                pass
    
    # إنشاء أو تحديث المستخدم
    db_user = db.get_user(user_id)
    if not db_user:
        # حفظ referrer_id في قاعدة البيانات فوراً (قبل التحقق)
        db_user = db.create_or_update_user(user_id, username, full_name, referrer_id)
    else:
        # إذا كان المستخدم موجود ولم يكن لديه referrer، نحفظه الآن
        if not db_user.referrer_id and referrer_id:
            db.create_or_update_user(user_id, username, full_name, referrer_id)
        else:
            db.create_or_update_user(user_id, username, full_name, None)
    
    # ══════════════════════════════════════════════════════════
    # 🔴 التحقق من الحظر ثانياً
    # ══════════════════════════════════════════════════════════
    db_user = db.get_user(user_id)  # إعادة جلب بيانات المستخدم
    if db_user and db_user.is_banned:
        ban_reason = db_user.ban_reason if db_user.ban_reason else 'تم حظرك من البوت'
        
        ban_message = f"""
<tg-emoji emoji-id='5463358164705489689'>⛔</tg-emoji> <b>تم حظرك من البوت</b>

عزيزي <b>{full_name}</b>،

حسابك محظور من استخدام البوت.

<b>السبب:</b> {ban_reason}
<b><tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> حالة الحساب:</b> محظور

إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.
"""
        
        await update.message.reply_text(
            ban_message,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"🔴 Banned user {user_id} tried to use /start")
        return  # إيقاف التنفيذ - لا نفتح قائمة التحقق
    
    # ══════════════════════════════════════════════════════════
    # 🔐 الخطوة 1: التحقق من الجهاز (الأساس - لا يتم شيء قبله)
    # ══════════════════════════════════════════════════════════
    
    # الأدمن لا يحتاج للتحقق
    if not is_admin(user_id):
        try:
            import requests as req
            
            # التحقق من حالة نظام التحقق
            settings_url = f"{API_BASE_URL}/admin/verification-settings?admin_id={user_id}"
            settings_resp = req.get(settings_url, timeout=5)
            
            verification_enabled = True
            if settings_resp.ok:
                settings_data = settings_resp.json()
                verification_enabled = settings_data.get('verification_enabled', True)
            
            # إذا كان التحقق مفعلاً، نتحقق من حالة المستخدم
            if verification_enabled:
                verify_status_url = f"{API_BASE_URL}/verification/status/{user_id}"
                verify_resp = req.get(verify_status_url, timeout=5)
                
                if verify_resp.ok:
                    verify_data = verify_resp.json()
                    is_verified = verify_data.get('verified', False)
                    
                    if not is_verified:
                        # المستخدم غير متحقق - إرسال رسالة التحقق
                        # إنشاء token للتحقق (يُحفظ في السيرفر فقط)
                        token_url = f"{API_BASE_URL}/verification/create-token"
                        token_resp = req.post(token_url, json={'user_id': user_id}, timeout=5)
                        
                        if token_resp.ok:
                            token_data = token_resp.json()
                            # ✅ لا نرسل fp_token في الرابط بعد الآن (أمان)
                            # التوكن سيُجلب من السيرفر باستخدام Telegram authentication
                            
                            verification_text = f"""
🔐 <b>التحقق من الجهاز</b>

عزيزي <b>{full_name}</b>، مرحباً بك! 👋

للحفاظ على نزاهة النظام ومنع التلاعب، يجب التحقق من جهازك أولاً.

<b>⚡️ هذه الخطوة تتم مرة واحدة فقط!</b>

<b>لماذا التحقق مهم؟</b>
• ضمان عدالة الإحالات
• منع الحسابات المزيفة والتلاعب

<b>✅ النظام لا يستخدم بياناتك الشخصية</b>

اضغط على الزر أدناه للبدء 👇
"""
                            
                            # محاولة إرسال رسالة مع WebApp أولاً
                            try:
                                # إنشاء رابط التحقق بدون .html (آمن)
                                verify_url = f"{MINI_APP_URL}/fp?user_id={user_id}"
                                
                                keyboard = [[InlineKeyboardButton(
                                    "🔐 تحقق من جهازك",
                                    web_app=WebAppInfo(url=verify_url)
                                )]]
                                
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                
                                await update.message.reply_text(
                                    verification_text,
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=reply_markup
                                )
                                
                                logger.info(f"✅ Verification message sent with WebApp to user {user_id}")
                                
                            except BadRequest as br:
                                # إذا فشل WebApp، نرسل رسالة بسيطة مع رابط URL
                                logger.warning(f"⚠️ WebApp failed for user {user_id}: {br}. Sending simple link.")
                                
                                simple_text = f"""
🔐 *التحقق من الجهاز*

عزيزي *{full_name}*، مرحباً بك! 👋

للحفاظ على نزاهة النظام، يجب التحقق من جهازك أولاً.

⚡️ *هذه الخطوة تتم مرة واحدة فقط!*

اضغط على الرابط للتحقق:
{MINI_APP_URL}/fp?user_id={user_id}

بعد التحقق، ارجع واكتب /start مرة أخرى.
"""
                                
                                keyboard = [[InlineKeyboardButton(
                                    "🔐 افتح صفحة التحقق",
                                    url=f"{MINI_APP_URL}/fp?user_id={user_id}"
                                )]]
                                
                                try:
                                    await update.message.reply_text(
                                        simple_text,
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=InlineKeyboardMarkup(keyboard),
                                        disable_web_page_preview=False
                                    )
                                except Exception as e2:
                                    # آخر محاولة: رسالة نص بسيط بدون أي تنسيق
                                    logger.error(f"❌ All formatting failed for user {user_id}: {e2}. Sending plain text.")
                                    await update.message.reply_text(
                                        f"🔐 التحقق من الجهاز\n\nعزيزي {full_name}، مرحباً بك!\n\nللمتابعة، افتح هذا الرابط للتحقق:\n{MINI_APP_URL}/fp?user_id={user_id}\n\nبعد التحقق، ارجع واكتب /start مرة أخرى."
                                    )
                            
                            # تسجيل النشاط
                            db.log_activity(user_id, "verification_required", f"Referrer: {referrer_id}")
                            
                            return  # إيقاف التنفيذ حتى يتم التحقق
        except BadRequest as br:
            logger.error(f"❌ BadRequest error in verification for user {user_id}: {br}")
            # في حالة BadRequest، نتخطى التحقق ونسمح بالمتابعة
        except Exception as e:
            logger.error(f"❌ Error checking verification status for user {user_id}: {e}")
            # في حالة الخطأ، السماح بالمتابعة
    
    # ══════════════════════════════════════════════════════════
    # 🎯 الخطوة 2: التحقق من الاشتراك في القنوات الإجبارية
    # ══════════════════════════════════════════════════════════
    # جلب القنوات الإجبارية (الأدمن لا يحتاج للاشتراك)
    required_channels = db.get_active_mandatory_channels()
    
    if required_channels and not is_admin(user_id):
        not_subscribed = []
        for channel in required_channels:
            channel_id = channel['channel_id']
            # إضافة @ إذا لم يكن موجوداً ولم يكن ID رقمي
            if not channel_id.startswith('@') and not channel_id.startswith('-'):
                channel_id = f"@{channel_id}"
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                    not_subscribed.append(channel)
            except Exception as e:
                logger.error(f"Error checking channel {channel_id}: {e}")
                not_subscribed.append(channel)
        
        if not_subscribed:
            # عرض أول قناة فقط
            first_channel = not_subscribed[0]
            
            subscription_text = f"""
<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> <b>اشتراك إجباري</b>

عزيزي <b>{full_name}</b>، للاستمرار في استخدام البوت، يجب الاشتراك في القناة التالية:

• <b>{first_channel['channel_name']}</b>

بعد الاشتراك، اضغط على زر "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تحققت من الاشتراك" أدناه.
"""
            
            keyboard = [
                [InlineKeyboardButton(
                    f"{first_channel['channel_name']}",
                    url=first_channel['channel_url']
                )],
                [InlineKeyboardButton(
                    "✅ تحققت من الاشتراك",
                    callback_data="check_subscription"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                subscription_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
            db.log_activity(user_id, "subscription_required", f"Channel: {first_channel['channel_name']}")
            return
    
    # ══════════════════════════════════════════════════════════
    # 🎉 الخطوة 3: المستخدم متحقق ومشترك - احتساب الإحالة
    # ══════════════════════════════════════════════════════════
    
    # احتساب الإحالة الآن فقط (بعد التحقق من الجهاز والقنوات)
    if referrer_id or context.user_data.get('pending_referrer_id'):
        final_referrer = referrer_id or context.user_data.get('pending_referrer_id')
        
        # التحقق من عدم احتساب الإحالة من روابط المينى آب (startapp)
        # فقط روابط start العادية
        if final_referrer:
            # التحقق من أن المُحيل ليس محظوراً
            referrer_user = db.get_user(final_referrer)
            if referrer_user and not referrer_user.is_banned:
                # التحقق من أن المستخدم الجديد ليس محظوراً
                new_user = db.get_user(user_id)
                if new_user and not new_user.is_banned:
                    # التحقق من عدم وجود إحالة مسجلة مسبقاً
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM referrals WHERE referred_id = ?", (user_id,))
                    existing_ref = cursor.fetchone()
                    
                    if not existing_ref:
                        # تسجيل الإحالة
                        now = datetime.now().isoformat()
                        try:
                            cursor.execute("""
                                INSERT INTO referrals (referrer_id, referred_id, created_at, channels_checked, device_verified, is_valid)
                                VALUES (?, ?, ?, 1, 1, 1)
                            """, (final_referrer, user_id, now))
                            
                            # تحديث عدد الإحالات للداعي
                            cursor.execute("""
                                UPDATE users 
                                SET total_referrals = total_referrals + 1,
                                    valid_referrals = valid_referrals + 1
                                WHERE user_id = ?
                            """, (final_referrer,))
                            
                            # التحقق من استحقاق لفة جديدة
                            cursor.execute("SELECT valid_referrals, available_spins FROM users WHERE user_id = ?", (final_referrer,))
                            ref_data = cursor.fetchone()
                            if ref_data:
                                valid_refs = ref_data['valid_referrals']
                                current_spins = ref_data['available_spins']
                                
                                # كل 5 إحالات = لفة واحدة
                                if valid_refs % SPINS_PER_REFERRALS == 0:
                                    cursor.execute("""
                                        UPDATE users 
                                        SET available_spins = available_spins + 1 
                                        WHERE user_id = ?
                                    """, (final_referrer,))
                                    
                                    # إرسال إشعار للداعي
                                    remaining_for_next = SPINS_PER_REFERRALS
                                    try:
                                        await context.bot.send_message(
                                            chat_id=final_referrer,
                                            text=f"""
<tg-emoji emoji-id='5388674524583572460'>🎉</tg-emoji> <b>تهانينا! إحالة جديدة ناجحة!</b>

<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> المستخدم <b>{full_name}</b> انضم عبر رابطك!

<tg-emoji emoji-id='5472096095280569232'>🎁</tg-emoji> <b>حصلت على لفة مجانية!</b>
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفاتك المتاحة:</b> {current_spins + 1}

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>إجمالي إحالاتك الصحيحة:</b> {valid_refs}
<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>متبقي للفة القادمة:</b> {remaining_for_next} إحالات

<b>استمر في الدعوة واربح المزيد! <tg-emoji emoji-id='5188481279963715781'>🚀</tg-emoji></b>
""",
                                            parse_mode=ParseMode.HTML
                                        )
                                    except Exception as e:
                                        logger.error(f"Failed to send referral notification: {e}")
                                else:
                                    # إرسال إشعار بدون لفة
                                    remaining_for_next = SPINS_PER_REFERRALS - (valid_refs % SPINS_PER_REFERRALS)
                                    try:
                                        await context.bot.send_message(
                                            chat_id=final_referrer,
                                            text=f"""
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>إحالة جديدة ناجحة!</b>

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> المستخدم <b>{full_name}</b> انضم عبر رابطك!

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>إجمالي إحالاتك الصحيحة:</b> {valid_refs}
<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>متبقي للفة القادمة:</b> {remaining_for_next} إحالات

<b>استمر في الدعوة! <tg-emoji emoji-id='5368724289679630642'>💪</tg-emoji></b>
""",
                                            parse_mode=ParseMode.HTML
                                        )
                                    except Exception as e:
                                        logger.error(f"Failed to send referral notification: {e}")
                            
                            conn.commit()
                            logger.info(f"✅ Referral validated and counted: {final_referrer} -> {user_id}")
                            
                        except sqlite3.IntegrityError:
                            logger.warning(f"⚠️ Referral already exists: {final_referrer} -> {user_id}")
                    
                    conn.close()
                    
                    # مسح البيانات المؤقتة
                    if 'pending_referrer_id' in context.user_data:
                        del context.user_data['pending_referrer_id']
    
    # تسجيل النشاط
    db.log_activity(user_id, "start", f"Verified and subscribed")
    
    # إنشاء رابط الدعوة للمستخدم
    user_ref_link = generate_referral_link(user_id)
    
    # رسالة الترحيب
    welcome_text = f"""
<tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji> <b>مرحباً بك في Panda Giveaways!</b> <tg-emoji emoji-id='5472096095280569232'>🎁</tg-emoji>

<b>{full_name}</b>، أهلاً بك في أفضل بوت للأرباح والهدايا! <tg-emoji emoji-id='5897920748101571572'>🌟</tg-emoji>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>رصيدك الحالي:</b> {db_user.balance:.2f} TON
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفاتك المتاحة:</b> {db_user.available_spins}
<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>إحالاتك:</b> {db_user.total_referrals}

<b><tg-emoji emoji-id='5461009483314517035'>🎯</tg-emoji> كيف تربح؟</b>
• قم بدعوة أصدقائك (كل {SPINS_PER_REFERRALS} إحالات = لفة مجانية)
• أكمل المهام اليومية
• إلعب عجلة الحظ واربح TON!
• إسحب أرباحك مباشرة إلى محفظتك

<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> <b>رابط الدعوة الخاص بك:</b>
<code>{user_ref_link}</code>

<b><tg-emoji emoji-id='5188481279963715781'>🚀</tg-emoji> ابدأ الآن واستمتع بالأرباح!</b>
"""
    
    # الأزرار
    keyboard = []
    
    # زر فتح Mini App
    keyboard.append([InlineKeyboardButton(
        "افتح Panda Giveaway 🎁",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}")
    )])
    
    # زر مشاركة رابط الدعوة (نسخ) - تغيير من startapp إلى start
    ref_link = generate_referral_link(user_id)
    ref_text = f"🎁 انضم لـ Panda Giveaways واربح TON مجاناً!\n\n{ref_link}"
    keyboard.append([InlineKeyboardButton(
        "📤 مشاركة رابط الدعوة",
        switch_inline_query=ref_text
    )])
    
    # زر إثباتات الدفع
    keyboard.append([InlineKeyboardButton(
        "💎 إثباتات الدفع",
        url="https://t.me/PandaGiveawaays"
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
<tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji> <b>مساعدة Panda Giveaways</b>

<b><tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> الأوامر المتاحة:</b>
/start - بدء البوت
/help - عرض المساعدة
/stats - إحصائياتك الشخصية
/referrals - عرض إحالاتك
/balance - عرض رصيدك

<b><tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> كيف تعمل عجلة الحظ؟</b>
• افتح Mini App من زر "افتح Panda Giveaway"
• إستخدم لفاتك المتاحة
• اربح TON فوراً!

<b><tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> نظام الإحالات:</b>
• كل {SPINS_PER_REFERRALS} إحالات صحيحة = لفة مجانية
• شارك رابطك مع الأصدقاء
• تأكد من اشتراكهم بالقنوات

<b><tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> السحوبات:</b>
• الحد الأدنى: {MIN_WITHDRAWAL_AMOUNT} TON
• ادخل من قسم السحب في Mini App
• اربط محفظة TON أو رقم فودافون كاش
• انتظر موافقة الأدمن

<b><tg-emoji emoji-id='5472201536727686043'>📞</tg-emoji> للدعم:</b>
تواصل مع @OMAR_M_SHEHATA
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
        await update.message.reply_text("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> لم يتم العثور على حسابك. استخدم /start أولاً.")
        return
    
    # حساب الإحالات المتبقية للفة القادمة
    valid_refs = user.total_referrals
    next_spin_in = SPINS_PER_REFERRALS - (valid_refs % SPINS_PER_REFERRALS)
    
    stats_text = f"""
<tg-emoji emoji-id='5422360266618707867'>📊</tg-emoji> <b>إحصائياتك الشخصية</b>

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>الاسم:</b> {user.full_name}
<tg-emoji emoji-id='5812093549042210992'>🆔</tg-emoji> <b>المعرف:</b> @{user.username}

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>الرصيد:</b> {user.balance:.4f} TON
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفات متاحة:</b> {user.available_spins}
<tg-emoji emoji-id='5226513232549664618'>🔢</tg-emoji> <b>إجمالي اللفات:</b> {user.total_spins}

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>الإحالات:</b> {user.total_referrals}
<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>متبقي للفة القادمة:</b> {next_spin_in} إحالات

<tg-emoji emoji-id='5373236586760651455'>📅</tg-emoji> <b>عضو منذ:</b> {user.created_at[:10]}
<tg-emoji emoji-id='5345905193005371012'>⚡️</tg-emoji> <b>آخر نشاط:</b> {user.last_active[:10] if user.last_active else 'N/A'}
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
    
    # حساب الإحصائيات من قاعدة البيانات مباشرة
    total_refs = len(referrals)
    valid_refs = sum(1 for r in referrals if r['is_valid'])
    
    ref_text = f"""
<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>قائمة المدعوين</b>

<tg-emoji emoji-id='5422360266618707867'>📊</tg-emoji> <b>إجمالي الإحالات:</b> {total_refs}
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>الإحالات الصحيحة:</b> {valid_refs}
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفاتك المتاحة:</b> {user.available_spins}
<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>متبقي للفة القادمة:</b> {SPINS_PER_REFERRALS - (valid_refs % SPINS_PER_REFERRALS) if valid_refs > 0 else SPINS_PER_REFERRALS}

"""
    
    if referrals:
        ref_text += "\n<b>آخر 10 مدعوين:</b>\n\n"
        for i, ref in enumerate(referrals[:10], 1):
            status = "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji>" if ref['is_valid'] else "<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji>"
            name = ref['full_name']
            username = f"@{ref['username']}" if ref['username'] else ""
            ref_text += f"{i}. {status} <b>{name}</b> {username}\n"
    else:
        ref_text += "\n<i>لم تقم بدعوة أحد بعد! شارك رابط الدعوة الآن <tg-emoji emoji-id='5188481279963715781'>🚀</tg-emoji></i>"
    
    ref_link = generate_referral_link(user_id)  # استخدام start بدلاً من startapp
    ref_text += f"\n\n<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> <b>رابط الدعوة الخاص بك:</b>\n<code>{ref_link}</code>"
    
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
<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>رصيدك</b>

<b>الرصيد الحالي:</b> {user.balance:.4f} TON
<b>الحد الأدنى للسحب:</b> {MIN_WITHDRAWAL_AMOUNT} TON

"""
    
    if user.balance >= MIN_WITHDRAWAL_AMOUNT:
        balance_text += "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> يمكنك السحب الآن من Mini App!"
    else:
        needed = MIN_WITHDRAWAL_AMOUNT - user.balance
        balance_text += f"<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> تحتاج {needed:.4f} TON إضافية للسحب"
    
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
    
    # الحصول على حالة التحقق من التعدد
    try:
        response = requests.get(f"{API_BASE_URL}/admin/verification-settings?admin_id={user_id}")
        verification_data = response.json()
        verification_enabled = verification_data.get('verification_enabled', True)
    except:
        verification_enabled = True
    
    admin_text = f"""
<tg-emoji emoji-id='5776076747866904719'>⚙️</tg-emoji> <b>لوحة المالكين - Panda Giveaways</b>

<tg-emoji emoji-id='5422360266618707867'>📊</tg-emoji> <b>الإحصائيات العامة:</b>
<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> إجمالي المستخدمين: {stats['total_users']}
<tg-emoji emoji-id='5345905193005371012'>⚡</tg-emoji> المستخدمون النشطون (7 أيام): {stats['active_users']}
<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> إجمالي الإحالات: {stats['total_referrals']}
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> إجمالي اللفات: {stats['total_spins']}

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>الإحصائيات المالية:</b>
<tg-emoji emoji-id='5472096095280569232'>🎁</tg-emoji> الأرباح الموزعة: {stats['total_distributed']:.2f} TON
<tg-emoji emoji-id='5260270009048906733'>💸</tg-emoji> السحوبات المكتملة: {stats['total_withdrawn']:.2f} TON
<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> طلبات السحب المعلقة: {stats['pending_withdrawals']}

<tg-emoji emoji-id='5776076747866904719'>⚙️</tg-emoji> <b>إعدادات السحب:</b>
<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>السحب التلقائي معطل نهائياً (أمان)</b>
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>كل الدفعات يدوية مع رابط دفع مباشر</b>

<tg-emoji emoji-id='5471981853445463256'>🤖</tg-emoji> <b>حالة البوت:</b>
{'<tg-emoji emoji-id=\'5260463209562776385\'>✅</tg-emoji> البوت مفعّل' if db.is_bot_enabled() else '<tg-emoji emoji-id=\'5273914604752216432\'>❌</tg-emoji> البوت معطّل'}

<tg-emoji emoji-id='5350619413533958825'>🔒</tg-emoji> <b>إعدادات الأمان:</b>
{'<tg-emoji emoji-id=\'5260463209562776385\'>✅</tg-emoji> التحقق من التعدد مفعّل' if verification_enabled else '<tg-emoji emoji-id=\'5273914604752216432\'>❌</tg-emoji> التحقق من التعدد معطّل'}

<b>اختر ما تريد إدارته:</b>
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{icon('wallet')} طلبات السحب", callback_data="admin_withdrawals")],
        [InlineKeyboardButton(f"{icon('broadcast')} إرسال برودكاست", callback_data="start_broadcast")],
        [InlineKeyboardButton(f"{icon('tasks')} إدارة المهام", callback_data="admin_tasks")],
        [InlineKeyboardButton(f"{icon('view')} فحص مستخدم", callback_data="admin_check_user")],
        [InlineKeyboardButton(f"{icon('chart')} إحصائيات تفصيلية", callback_data="admin_detailed_stats")],
        [
            InlineKeyboardButton("💾 نسخة احتياطية", callback_data="create_backup"),
            InlineKeyboardButton("📥 استعادة نسخة", callback_data="restore_backup_start")
        ],
        [InlineKeyboardButton(
            "⛔ السحب التلقائي (معطل نهائياً - أمان)",
            callback_data="toggle_auto_withdrawal"
        )],
        [InlineKeyboardButton(
            f"{'🔴 إيقاف' if db.is_bot_enabled() else '🟢 تشغيل'} البوت",
            callback_data="toggle_bot_status"
        )],
        [InlineKeyboardButton(
            f"{'❌ إيقاف' if verification_enabled else '✅ تفعيل'} التحقق من التعدد",
            callback_data="toggle_verification"
        )],
        [InlineKeyboardButton(f"{icon('back')} رجوع", callback_data="back_to_start")]
    ]
    
    await query.edit_message_text(
        admin_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toggle_auto_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة السحب التلقائي - معطل نهائياً"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    # ⛔ السحب التلقائي معطل نهائياً لأسباب أمنية
    await query.answer(
        "⛔ السحب التلقائي معطل نهائياً لأسباب أمنية!\n\n"
        "✅ كل الدفعات يدوية مع التحقق من المعاملات عبر TON API\n"
        "🔐 هذا يحمي محفظتك من السرقة",
        show_alert=True
    )
    
    # تحديث لوحة الأدمن
    await admin_panel_callback(update, context)

async def toggle_bot_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة البوت (تشغيل/إيقاف)"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    # تبديل الحالة
    new_state = db.toggle_bot_status(user_id)
    
    status_text = "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> مفعّل" if new_state else "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> معطّل"
    status_emoji = "<tg-emoji emoji-id='5314239906244453696'>🟢</tg-emoji>" if new_state else "<tg-emoji emoji-id='5360054260508063850'>🔴</tg-emoji>"
    
    await query.answer(
        f"{status_emoji} تم! البوت الآن {status_text}",
        show_alert=True
    )
    
    # إرسال رسالة تأكيد
    confirmation_text = f"""
{'🟢 <b>تم تشغيل البوت</b>' if new_state else '🔴 <b>تم إيقاف البوت</b>'}

{'✅ المستخدمون يمكنهم الآن استخدام البوت بشكل طبيعي.' if new_state else '⚠️ المستخدمون لن يتمكنوا من استخدام البوت حتى تقوم بتشغيله مرة أخرى.'}

🕐 التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
👤 بواسطة: {query.from_user.full_name}
"""
    
    await query.message.reply_text(
        confirmation_text,
        parse_mode=ParseMode.HTML
    )
    
    # تحديث لوحة الأدمن
    await admin_panel_callback(update, context)

async def toggle_verification_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة التحقق من التعدد"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    try:
        # الحصول على الحالة الحالية
        response = requests.get(f"{API_BASE_URL}/admin/verification-settings?admin_id={user_id}")
        current_data = response.json()
        current_state = current_data.get('verification_enabled', True)
        new_state = not current_state
        
        # تحديث الإعداد
        update_response = requests.post(
            f"{API_BASE_URL}/admin/verification-settings",
            json={'admin_id': user_id, 'enabled': new_state}
        )
        
        if update_response.json().get('success'):
            status_text = "✅ مفعّل" if new_state else "❌ معطّل"
            await query.answer(
                f"تم! التحقق من التعدد الآن {status_text}",
                show_alert=True
            )
            # تحديث لوحة الأدمن
            await admin_panel_callback(update, context)
        else:
            await query.answer("❌ حدث خطأ في تحديث الإعداد", show_alert=True)
    except Exception as e:
        print(f"❌ Error toggling verification: {e}")
        await query.answer("❌ فشل الاتصال بالخادم", show_alert=True)

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
<tg-emoji emoji-id='5422360266618707867'>📊</tg-emoji> <b>إحصائيات تفصيلية</b>

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>المستخدمون:</b>
• الإجمالي: {stats['total_users']}
• النشطون (7 أيام): {stats['active_users']}
• معدل النشاط: {(stats['active_users']/stats['total_users']*100) if stats['total_users'] > 0 else 0:.1f}%

<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> <b>الإحالات:</b>
• الإجمالي: {stats['total_referrals']}
• متوسط الإحالات/مستخدم: {(stats['total_referrals']/stats['total_users']) if stats['total_users'] > 0 else 0:.2f}

<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>اللفات:</b>
• الإجمالي: {stats['total_spins']}
• متوسط اللفات/مستخدم: {(stats['total_spins']/stats['total_users']) if stats['total_users'] > 0 else 0:.2f}

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>المالية:</b>
• الأرباح الموزعة: {stats['total_distributed']:.2f} TON
• السحوبات المكتملة: {stats['total_withdrawn']:.2f} TON
• طلبات السحب المعلقة: {stats['pending_withdrawals']}
"""
    await query.edit_message_text(
        detailed_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    )

# ═══════════════════════════════════════════════════════════════
# 💾 DATABASE BACKUP & RESTORE
# ═══════════════════════════════════════════════════════════════

async def create_backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    try:
        await query.edit_message_text(
            "<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>جاري إنشاء النسخة الاحتياطية...</b>\n\n"
            "<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> يتم نسخ قاعدة البيانات الآن، الرجاء الانتظار...",
            parse_mode=ParseMode.HTML
        )
        
        # إنشاء اسم الملف مع التاريخ والوقت
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"panda_backup_{timestamp}.db"
        backup_path = os.path.join(os.path.dirname(DATABASE_PATH), backup_filename)
        
        # نسخ قاعدة البيانات
        shutil.copy2(DATABASE_PATH, backup_path)
        
        # التحقق من حجم الملف
        file_size = os.path.getsize(backup_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # إرسال الملف للأدمن
        with open(backup_path, 'rb') as backup_file:
            await context.bot.send_document(
                chat_id=user_id,
                document=backup_file,
                filename=backup_filename,
                caption=f"""
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>تم إنشاء النسخة الاحتياطية بنجاح!</b>

<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> <b>معلومات النسخة:</b>
<tg-emoji emoji-id='5373236586760651455'>📅</tg-emoji> التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
<tg-emoji emoji-id='5422360266618707867'>📊</tg-emoji> حجم الملف: {file_size_mb:.2f} MB
<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> اسم الملف: <code>{backup_filename}</code>

<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>تعليمات مهمة:</b>
• احفظ هذا الملف في مكان آمن
• يمكنك استعادة البيانات من هذا الملف في أي وقت
• لا تشارك هذا الملف مع أحد (يحتوي على بيانات حساسة)

<tg-emoji emoji-id='5897920748101571572'>🌟</tg-emoji> لاستعادة النسخة: استخدم زر "استعادة نسخة احتياطية"
""",
                parse_mode=ParseMode.HTML
            )
        
        # حذف الملف المؤقت
        try:
            os.remove(backup_path)
        except:
            pass
        
        # العودة للوحة التحكم
        await query.edit_message_text(
            "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>تم إرسال النسخة الاحتياطية بنجاح!</b>\n\n"
            "تم إرسال الملف في رسالة منفصلة، تحقق من الرسائل أعلاه.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_panel")
            ]])
        )
        
        logger.info(f"✅ Backup created successfully by admin {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error creating backup: {e}")
        await query.edit_message_text(
            f"<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>فشل إنشاء النسخة الاحتياطية</b>\n\n"
            f"الخطأ: {str(e)}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )

async def restore_backup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية استعادة النسخة الاحتياطية"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ غير مصرح لك!", show_alert=True)
        return
    
    await query.edit_message_text(
        """
<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>استعادة نسخة احتياطية</b>

<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> <b>تعليمات مهمة:</b>
1️⃣ أرسل ملف النسخة الاحتياطية (.db)
2️⃣ سيتم استبدال قاعدة البيانات الحالية بالكامل
3️⃣ تأكد من أن الملف من نفس النظام

<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>تحذير:</b>
• سيتم حذف جميع البيانات الحالية
• تأكد من عمل نسخة احتياطية قبل الاستعادة
• هذه العملية لا يمكن التراجع عنها

<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> <b>أرسل الملف الآن أو اضغط إلغاء</b>
""",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ إلغاء", callback_data="admin_panel")
        ]])
    )
    
    return RESTORE_BACKUP

async def restore_backup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج استعادة النسخة الاحتياطية"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> غير مصرح لك!")
        return ConversationHandler.END
    
    if not update.message.document:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>خطأ: لم يتم إرسال ملف</b>\n\n"
            "الرجاء إرسال ملف قاعدة البيانات (.db)",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
        return RESTORE_BACKUP
    
    document = update.message.document
    
    # التحقق من امتداد الملف
    if not document.file_name.endswith('.db'):
        await update.message.reply_text(
            "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>خطأ: نوع ملف غير صحيح</b>\n\n"
            "الرجاء إرسال ملف قاعدة بيانات بامتداد .db",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
        return RESTORE_BACKUP
    
    try:
        # إرسال رسالة الانتظار
        wait_msg = await update.message.reply_text(
            "<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>جاري استعادة النسخة الاحتياطية...</b>\n\n"
            "<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> يتم معالجة الملف، الرجاء الانتظار...",
            parse_mode=ParseMode.HTML
        )
        
        # تحميل الملف
        file = await context.bot.get_file(document.file_id)
        temp_backup_path = os.path.join(os.path.dirname(DATABASE_PATH), f"temp_restore_{user_id}.db")
        await file.download_to_drive(temp_backup_path)
        
        # التحقق من صحة الملف
        try:
            conn = sqlite3.connect(temp_backup_path)
            cursor = conn.cursor()
            # التحقق من وجود الجداول الأساسية
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            required_tables = ['users', 'referrals', 'spins', 'withdrawals']
            if not all(table in tables for table in required_tables):
                raise Exception("ملف قاعدة البيانات غير صحيح أو تالف")
                
        except Exception as validation_error:
            os.remove(temp_backup_path)
            await wait_msg.edit_text(
                f"❌ <b>فشل التحقق من الملف</b>\n\n"
                f"الخطأ: {str(validation_error)}\n\n"
                f"تأكد من أن الملف نسخة احتياطية صحيحة من نفس النظام.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
                ]])
            )
            return ConversationHandler.END
        
        # إنشاء نسخة احتياطية من قاعدة البيانات الحالية قبل الاستبدال
        current_backup = f"{DATABASE_PATH}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(DATABASE_PATH, current_backup)
        
        # استبدال قاعدة البيانات
        shutil.copy2(temp_backup_path, DATABASE_PATH)
        
        # حذف الملف المؤقت
        os.remove(temp_backup_path)
        
        await wait_msg.edit_text(
            f"""
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>تم استعادة النسخة الاحتياطية بنجاح!</b>

<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> <b>معلومات العملية:</b>
<tg-emoji emoji-id='5373236586760651455'>📅</tg-emoji> التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> بواسطة: {update.effective_user.full_name}
<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> اسم الملف: {document.file_name}

<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>تم بنجاح:</b>
• استعادة قاعدة البيانات
• حفظ نسخة من البيانات القديمة
• تحديث النظام

<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>ملاحظة:</b>
تم حفظ نسخة من البيانات القديمة في:
<code>{os.path.basename(current_backup)}</code>

<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> يُنصح بإعادة تشغيل البوت لتطبيق التغييرات بشكل كامل.
""",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع للوحة التحكم", callback_data="admin_panel")
            ]])
        )
        
        logger.info(f"✅ Database restored successfully by admin {user_id} from file {document.file_name}")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"❌ Error restoring backup: {e}")
        
        # حذف الملف المؤقت في حالة الخطأ
        try:
            if os.path.exists(temp_backup_path):
                os.remove(temp_backup_path)
        except:
            pass
        
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>فشلت استعادة النسخة الاحتياطية</b>\n\n"
            f"الخطأ: {str(e)}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
        
        return ConversationHandler.END

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
<tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji> <b>مرحباً بك في Panda Giveaways!</b> <tg-emoji emoji-id='5472096095280569232'>🎁</tg-emoji>

<b>{full_name}</b>، أهلاً بك في أفضل بوت للأرباح والهدايا! <tg-emoji emoji-id='5897920748101571572'>🌟</tg-emoji>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>رصيدك الحالي:</b> {db_user.balance:.2f} TON
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفاتك المتاحة:</b> {db_user.available_spins}
<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>إحالاتك:</b> {db_user.total_referrals}

<b><tg-emoji emoji-id='5461009483314517035'>🎯</tg-emoji> كيف تربح؟</b>
• قم بدعوة أصدقائك (كل {SPINS_PER_REFERRALS} إحالات = لفة مجانية)
• أكمل المهام اليومية
• إلعب عجلة الحظ واربح TON!
• إسحب أرباحك مباشرة إلى محفظتك

<b><tg-emoji emoji-id='5188481279963715781'>🚀</tg-emoji> ابدأ الآن واستمتع بالأرباح!</b>
"""
    
    keyboard = []
    keyboard.append([InlineKeyboardButton(
        "🎰 افتح Panda Giveaway",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}")
    )])
    
    ref_link = generate_referral_link(user_id)  # استخدام start بدلاً من startapp
    ref_text = f"🎁 انضم لـ Panda Giveaways واربح TON مجاناً!\n\n{ref_link}"
    keyboard.append([InlineKeyboardButton(
        "📤 مشاركة رابط الدعوة",
        switch_inline_query=ref_text
    )])
    
    keyboard.append([InlineKeyboardButton(
        "💎 إثباتات الدفع",
        url="https://t.me/PandaGiveawaays"
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

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من اشتراك المستخدم في القنوات الإجبارية"""
    query = update.callback_query
    await query.answer("جارٍ التحقق من الاشتراك...")
    
    user = query.from_user
    user_id = user.id
    username = user.username or f"user_{user_id}"
    full_name = user.full_name or username
    
    # جلب القنوات الإجبارية من قاعدة البيانات
    required_channels = db.get_active_mandatory_channels()
    
    if required_channels:
        not_subscribed = []
        for channel in required_channels:
            channel_id = channel['channel_id']
            # إضافة @ إذا لم يكن موجوداً ولم يكن ID رقمي
            if not channel_id.startswith('@') and not channel_id.startswith('-'):
                channel_id = f"@{channel_id}"
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                    not_subscribed.append(channel)
            except Exception as e:
                logger.error(f"Error checking channel {channel_id}: {e}")
                not_subscribed.append(channel)
        
        if not_subscribed:
            # عرض أول قناة غير مشترك فيها
            first_channel = not_subscribed[0]
            
            await query.answer("⚠️ يجب الاشتراك في القناة أولاً!", show_alert=True)
            
            subscription_text = f"""
<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> <b>اشتراك إجباري</b>

عزيزي <b>{full_name}</b>، يجب الاشتراك في القناة التالية:

• <b>{first_channel['channel_name']}</b>

بعد الاشتراك، اضغط على زر "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تحققت من الاشتراك" مرة أخرى.
"""
            
            keyboard = [
                [InlineKeyboardButton(
                    f"<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> {first_channel['channel_name']}",
                    url=first_channel['channel_url']
                )],
                [InlineKeyboardButton(
                    "✅ تحققت من الاشتراك",
                    callback_data="check_subscription"
                )]
            ]
            
            await query.edit_message_text(
                subscription_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return
    
    # المستخدم مشترك في جميع القنوات - عرض الرسالة الرئيسية
    await query.answer("✅ تم التحقق من الاشتراك بنجاح!", show_alert=True)
    
    # ═══════════════════════════════════════════════════════════
    # 🎯 احتساب الإحالة بعد اكتمال جميع الخطوات
    # ═══════════════════════════════════════════════════════════
    # الحصول على referrer_id من context أو من قاعدة البيانات
    referrer_id = context.user_data.get('pending_referrer_id')
    logger.info(f"🔍 Checking referral for user {user_id}, context referrer: {referrer_id}")
    
    # إذا لم يكن موجود في context، نحاول الحصول عليه من قاعدة البيانات
    if not referrer_id:
        current_user = db.get_user(user_id)
        if current_user and current_user.referrer_id:
            referrer_id = current_user.referrer_id
            logger.info(f"📎 Retrieved referrer_id from database: {referrer_id} for user {user_id}")
    
    if referrer_id:
        logger.info(f"🎯 Processing referral: {referrer_id} -> {user_id}")
        # التحقق من أن المُحيل ليس محظوراً
        referrer_user = db.get_user(referrer_id)
        if referrer_user and not referrer_user.is_banned:
            # التحقق من أن المستخدم الجديد ليس محظوراً
            new_user = db.get_user(user_id)
            if new_user and not new_user.is_banned:
                # التحقق من عدم وجود إحالة مسجلة مسبقاً
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM referrals WHERE referred_id = ?", (user_id,))
                existing_ref = cursor.fetchone()
                
                if existing_ref:
                    logger.warning(f"⚠️ Referral already exists for user {user_id}, skipping")
                    conn.close()
                else:
                    logger.info(f"✨ Creating new referral record: {referrer_id} -> {user_id}")
                    # تسجيل الإحالة
                    now = datetime.now().isoformat()
                    try:
                        cursor.execute("""
                            INSERT INTO referrals (referrer_id, referred_id, created_at, channels_checked, device_verified, is_valid)
                            VALUES (?, ?, ?, 1, 1, 1)
                        """, (referrer_id, user_id, now))
                        
                        # تحديث عدد الإحالات للداعي
                        cursor.execute("""
                            UPDATE users 
                            SET total_referrals = total_referrals + 1,
                                valid_referrals = valid_referrals + 1
                            WHERE user_id = ?
                        """, (referrer_id,))
                        
                        # التحقق من استحقاق لفة جديدة
                        cursor.execute("SELECT valid_referrals, available_spins FROM users WHERE user_id = ?", (referrer_id,))
                        ref_data = cursor.fetchone()
                        if ref_data:
                            valid_refs = ref_data['valid_referrals']
                            current_spins = ref_data['available_spins']
                            
                            logger.info(f"📊 Referrer stats: {valid_refs} referrals, {current_spins} spins")
                            
                            # كل 5 إحالات = لفة واحدة
                            if valid_refs % SPINS_PER_REFERRALS == 0:
                                cursor.execute("""
                                    UPDATE users 
                                    SET available_spins = available_spins + 1 
                                    WHERE user_id = ?
                                """, (referrer_id,))
                                
                                logger.info(f"🎁 Awarding spin to referrer {referrer_id}")
                                
                                # إرسال إشعار للداعي
                                remaining_for_next = SPINS_PER_REFERRALS
                                try:
                                    await context.bot.send_message(
                                        chat_id=referrer_id,
                                        text=f"""
<tg-emoji emoji-id='5388674524583572460'>🎉</tg-emoji> <b>تهانينا! إحالة جديدة ناجحة!</b>

<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> المستخدم <b>{full_name}</b> انضم عبر رابطك وأكمل جميع الخطوات!

<tg-emoji emoji-id='5472096095280569232'>🎁</tg-emoji> <b>حصلت على لفة مجانية!</b>
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفاتك المتاحة:</b> {current_spins + 1}

<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>إجمالي إحالاتك الصحيحة:</b> {valid_refs}
<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> <b>متبقي للفة القادمة:</b> {remaining_for_next} إحالات

<b>استمر في الدعوة واربح المزيد! <tg-emoji emoji-id='5188481279963715781'>🚀</tg-emoji></b>
""",
                                        parse_mode=ParseMode.HTML
                                    )
                                    logger.info(f"✅ Spin notification sent to {referrer_id}")
                                except Exception as e:
                                    logger.error(f"Failed to send referral notification: {e}")
                            else:
                                # إرسال إشعار بدون لفة
                                remaining_for_next = SPINS_PER_REFERRALS - (valid_refs % SPINS_PER_REFERRALS)
                                try:
                                    await context.bot.send_message(
                                        chat_id=referrer_id,
                                        text=f"""
✅ <b>إحالة جديدة ناجحة!</b>

👤 المستخدم <b>{full_name}</b> انضم عبر رابطك وأكمل جميع الخطوات!

👥 <b>إجمالي إحالاتك الصحيحة:</b> {valid_refs}
⏳ <b>متبقي للفة القادمة:</b> {remaining_for_next} إحالات

<b>استمر في الدعوة! 💪</b>
""",
                                        parse_mode=ParseMode.HTML
                                    )
                                    logger.info(f"✅ Referral notification sent to {referrer_id}")
                                except Exception as e:
                                    logger.error(f"Failed to send referral notification: {e}")
                        
                        conn.commit()
                        logger.info(f"✅ Referral validated and counted after subscription check: {referrer_id} -> {user_id}")
                        
                    except sqlite3.IntegrityError:
                        logger.warning(f"⚠️ Referral already exists: {referrer_id} -> {user_id}")
                    
                    conn.close()
            else:
                logger.warning(f"⚠️ New user {user_id} is banned, referral not counted")
        else:
            logger.warning(f"⚠️ Referrer {referrer_id} is banned or not found, referral not counted")
                
        # مسح البيانات المؤقتة
        if 'pending_referrer_id' in context.user_data:
            del context.user_data['pending_referrer_id']
    else:
        logger.info(f"ℹ️ No referrer_id found for user {user_id}, skipping referral count")
    
    # الحصول على بيانات المستخدم المحدثة
    db_user = db.get_user(user_id)
    if not db_user:
        db_user = db.create_or_update_user(user_id, username, full_name, None)
    
    # رسالة الترحيب
    welcome_text = f"""
<tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji> <b>مرحباً بك في Panda Giveaways!</b> <tg-emoji emoji-id='5472096095280569232'>🎁</tg-emoji>

<b>{full_name}</b>، أهلاً بك في أفضل بوت للأرباح والهدايا! <tg-emoji emoji-id='5897920748101571572'>🌟</tg-emoji>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>رصيدك الحالي:</b> {db_user.balance:.2f} TON
<tg-emoji emoji-id='5778315894706937436'>🎰</tg-emoji> <b>لفاتك المتاحة:</b> {db_user.available_spins}
<tg-emoji emoji-id='5453957997418004470'>👥</tg-emoji> <b>إحالاتك:</b> {db_user.total_referrals}

<b><tg-emoji emoji-id='5461009483314517035'>🎯</tg-emoji> كيف تربح؟</b>
• قم بدعوة أصدقائك (كل {SPINS_PER_REFERRALS} إحالات = لفة مجانية)
• أكمل المهام اليومية
• إلعب عجلة الحظ واربح TON!
• إسحب أرباحك مباشرة إلى محفظتك

<b><tg-emoji emoji-id='5188481279963715781'>🚀</tg-emoji> ابدأ الآن واستمتع بالأرباح!</b>
"""
    
    # الأزرار
    keyboard = []
    
    # زر فتح Mini App
    keyboard.append([InlineKeyboardButton(
        "🎰 افتح Panda Giveaway",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?user_id={user_id}")
    )])
    
    # زر مشاركة رابط الدعوة
    ref_link = generate_referral_link(user_id)
    ref_text = f"🎁 انضم لـ Panda Giveaways واربح TON مجاناً!\n\n{ref_link}"
    keyboard.append([InlineKeyboardButton(
        "📤 مشاركة رابط الدعوة",
        switch_inline_query=ref_text
    )])
    
    # زر إثباتات الدفع
    keyboard.append([InlineKeyboardButton(
        "💎 إثباتات الدفع",
        url="https://t.me/PandaGiveawaays"
    )])
    
    # زر لوحة الأدمن (للأدمن فقط)
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
        await query.answer("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> غير مصرح لك!", show_alert=True)
        return
    
    pending = db.get_pending_withdrawals()
    
    if not pending:
        await query.edit_message_text(
            "<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> لا توجد طلبات سحب معلقة حالياً!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
            ]])
        )
        return
    
    withdrawal_text = f"""
<tg-emoji emoji-id='5260270009048906733'>💸</tg-emoji> <b>طلبات السحب المعلقة ({len(pending)})</b>

"""
    
    keyboard = []
    
    for w in pending[:5]:  # أول 5 طلبات
        user_info = f"{w['full_name']} (@{w['username']})" if w['username'] else w['full_name']
        w_type = "TON" if w['withdrawal_type'] == 'ton' else "Vodafone Cash"
        
        withdrawal_text += f"""
━━━━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5197269100878907942'>🆔</tg-emoji> <b>ID:</b> {w['id']}
<tg-emoji emoji-id='5453957997418004470'>👤</tg-emoji> <b>المستخدم:</b> {user_info}
<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>المبلغ:</b> {w['amount']:.4f} TON
<tg-emoji emoji-id='5472201536727686043'>📱</tg-emoji> <b>النوع:</b> {w_type}
"""
        
        if w['wallet_address']:
            withdrawal_text += f"<tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> <b>المحفظة:</b> <code>{w['wallet_address']}</code>\n"
        if w['phone_number']:
            withdrawal_text += f"<tg-emoji emoji-id='5472201536727686043'>📞</tg-emoji> <b>الرقم:</b> <code>{w['phone_number']}</code>\n"
        
        withdrawal_text += f"<tg-emoji emoji-id='5373236586760651455'>📅</tg-emoji> <b>التاريخ:</b> {w['requested_at'][:16]}\n"
        
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

# ═══════════════════════════════════════════════════════════════
# 📢 PAYMENT PROOF CHANNEL
# ═══════════════════════════════════════════════════════════════

async def send_payment_proof_to_channel(context: ContextTypes.DEFAULT_TYPE, 
                                       username: str, 
                                       full_name: str,
                                       user_id: int,
                                       amount: float, 
                                       wallet_address: str,
                                       tx_hash: str,
                                       withdrawal_id: int):
    """نشر إثبات الدفع في قناة الإثباتات"""
    if not PAYMENT_PROOF_CHANNEL:
        logger.warning("⚠️ PAYMENT_PROOF_CHANNEL not configured")
        return False
    
    try:
        # رابط المستخدم
        user_link = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>{full_name}</a>"
        
        # رابط المعاملة على TON Explorer
        ton_explorer_url = f"https://tonscan.org/tx/{tx_hash}"
        
        # تنسيق عنوان المحفظة (الأحرف الأولى والأخيرة فقط)
        wallet_short = f"{wallet_address[:6]}...{wallet_address[-6:]}"
        
        # رسالة الإثبات
        proof_message = f"""
<tg-emoji emoji-id='5388674524583572460'>🎉</tg-emoji> <b>تم تنفيذ سحب جديد!</b>

<tg-emoji emoji-id='5453957997418004470'>👤</tg-emoji> <b>المستخدم:</b> {user_link}
<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> <b>المبلغ:</b> {amount:.4f} TON
<tg-emoji emoji-id='6005943221455165890'>💳</tg-emoji> <b>المحفظة:</b> <code>{wallet_short}</code>
<tg-emoji emoji-id='5197269100878907942'>📋</tg-emoji> <b>رقم الطلب:</b> #{withdrawal_id}

<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> <b>تفاصيل المعاملة:</b>
<a href="{ton_explorer_url}">عرض على TON Explorer</a>

<tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> <b>TX Hash:</b>
<code>{tx_hash}</code>

━━━━━━━━━━━━━━━
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تم التحويل بنجاح عبر البوت الآلي
<tg-emoji emoji-id='6010227837879983163'>⏰</tg-emoji> التوقيت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━

<tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji> @{BOT_USERNAME}
"""
        
        # إرسال الرسالة للقناة
        await context.bot.send_message(
            chat_id=PAYMENT_PROOF_CHANNEL,
            text=proof_message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        
        logger.info(f"✅ Payment proof sent to channel {PAYMENT_PROOF_CHANNEL} for withdrawal #{withdrawal_id}")
        return True
        
    except Forbidden as e:
        logger.error(f"❌ Bot is not admin or can't post in channel {PAYMENT_PROOF_CHANNEL}: {e}")
        return False
    except BadRequest as e:
        logger.error(f"❌ Bad request when posting to channel {PAYMENT_PROOF_CHANNEL}: {e}")
        logger.error(f"   Hint: Make sure PAYMENT_PROOF_CHANNEL is set to @channelname (not URL) and bot is admin")
        return False

# ═══════════════════════════════════════════════════════════════
# 🔍 TON TRANSACTION CHECKER (للدفع اليدوي)
# ═══════════════════════════════════════════════════════════════

async def check_pending_withdrawals_transactions(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    فحص المعاملات للسحوبات المعلقة عبر محافظ العملاء
    يبحث في المعاملات الواردة لكل محفظة عميل عن Comment محدد
    Comment format: W{withdrawal_id}-{user_id}
    """
    try:
        if not TON_API_KEY:
            logger.warning("⚠️ TON_API_KEY not configured")
            return {'success': False, 'error': 'Configuration missing'}
        
        # الحصول على السحوبات المعلقة
        pending_withdrawals = db.get_pending_withdrawals()
        
        if not pending_withdrawals:
            logger.info("✅ No pending withdrawals to check")
            return {'success': True, 'checked': 0, 'found': 0}
        
        logger.info(f"🔍 Checking {len(pending_withdrawals)} pending withdrawals...")
        logger.info(f"   Method: Check incoming transactions to USER wallets")
        
        # استخدام TON API
        api_endpoint = "https://toncenter.com/api/v2/"
        headers = {"X-API-Key": TON_API_KEY} if TON_API_KEY else {}
        
        checked_count = 0
        found_count = 0
        
        # فحص كل سحب معلق
        for withdrawal in pending_withdrawals:
            if withdrawal['withdrawal_type'].upper() != 'TON':
                continue  # فقط TON withdrawals
            
            withdrawal_id = withdrawal['id']
            user_id = withdrawal['user_id']
            amount = withdrawal['amount']
            wallet_address = withdrawal['wallet_address']
            
            # Comment المتوقع
            expected_comment = f"W{withdrawal_id}-{user_id}"
            
            try:
                logger.info(f"   Checking withdrawal #{withdrawal_id}: {expected_comment}")
                logger.info(f"      User wallet: {wallet_address[:15]}...")
                
                # فحص معاملات محفظة العميل (المستلم)
                url = f"{api_endpoint}getTransactions"
                params = {
                    'address': wallet_address,  # محفظة العميل
                    'limit': 20  # آخر 20 معاملة
                }
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    logger.warning(f"      ⚠️ API error for wallet {wallet_address[:10]}...")
                    continue
                
                data = response.json()
                
                if not data.get('ok') or 'result' not in data:
                    logger.warning(f"      ⚠️ Invalid API response")
                    continue
                
                transactions = data['result']
                logger.debug(f"      Found {len(transactions)} transactions")
                
                # البحث في المعاملات الواردة
                for tx in transactions:
                    try:
                        # فحص المعاملة الواردة (in_msg)
                        in_msg = tx.get('in_msg', {})
                        
                        if not in_msg:
                            continue
                        
                        # استخراج الكومنت من message
                        msg_data = in_msg.get('message', '')
                        
                        # تحويل dict إلى string إذا لزم الأمر
                        if isinstance(msg_data, dict):
                            msg_data = str(msg_data)
                        
                        comment = str(msg_data) if msg_data else ''
                        
                        # التحقق من الكومنت فقط (بدون المبلغ)
                        if expected_comment in comment:
                            # وجدنا المعاملة عبر الكومنت!
                            value = int(in_msg.get('value', '0'))
                            value_ton = value / 1_000_000_000
                            
                            # استخراج tx_hash بشكل صحيح
                            tx_hash = ''
                            tx_id = tx.get('transaction_id', {})
                            if isinstance(tx_id, dict):
                                tx_hash = tx_id.get('hash', '')
                                if not tx_hash:
                                    tx_lt = tx_id.get('lt', '')
                                    if tx_lt:
                                        tx_hash = f"lt:{tx_lt}"
                            
                            # fallback: استخدام hash مباشر
                            if not tx_hash:
                                tx_hash = tx.get('hash', 'unknown')
                            
                            logger.info(f"      ✅ Found matching transaction!")
                            logger.info(f"         Comment: {comment}")
                            logger.info(f"         Amount: {value_ton} TON")
                            logger.info(f"         TX Hash: {tx_hash}")
                            
                            # الموافقة تلقائياً
                            db.approve_withdrawal(withdrawal_id, 0, tx_hash)  # 0 = auto
                            
                            # إرسال إشعار للمستخدم
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id,
                                    text=f"""
🎉 <b>تم تأكيد السحب!</b>

💰 المبلغ: {value_ton:.4f} TON
🔐 TX Hash: <code>{tx_hash[:16]}...</code>

شكراً لاستخدامك Panda Giveaways! 🐼
""",
                                    parse_mode=ParseMode.HTML
                                )
                            except Exception as notify_error:
                                logger.error(f"Failed to notify user: {notify_error}")
                            
                            # نشر إثبات الدفع
                            try:
                                await send_payment_proof_to_channel(
                                    context=context,
                                    username=withdrawal.get('username', ''),
                                    full_name=withdrawal['full_name'],
                                    user_id=user_id,
                                    amount=value_ton,  # المبلغ الفعلي المرسل
                                    wallet_address=wallet_address,
                                    tx_hash=tx_hash,
                                    withdrawal_id=withdrawal_id
                                )
                            except Exception as proof_error:
                                logger.error(f"Failed to post proof: {proof_error}")
                            
                            found_count += 1
                            break  # وجدنا المعاملة، انتقل للسحب التالي
                    
                    except Exception as tx_error:
                        logger.debug(f"Error processing transaction: {tx_error}")
                        continue
                
                checked_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error checking withdrawal #{withdrawal_id}: {e}")
        
        result = {
            'success': True,
            'checked': checked_count,
            'found': found_count,
            'total_pending': len(pending_withdrawals)
        }
        
        logger.info(f"✅ Transaction check complete: {found_count}/{checked_count} found")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in check_pending_withdrawals_transactions: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════
# 🔍 VERIFY WITHDRAWAL TRANSACTION - التحقق من معاملة محددة
# ═══════════════════════════════════════════════════════════════

async def verify_withdrawal_transaction(withdrawal_id: int, wallet_address: str, amount: float, context: ContextTypes.DEFAULT_TYPE, user_id: int = None) -> dict:
    """
    التحقق من وصول معاملة السحب إلى محفظة المستخدم (العميل)
    يفحص المعاملات الواردة لمحفظة العميل عبر الكومنت فقط
    Comment format: W{withdrawal_id}-{user_id}
    """
    try:
        if not TON_API_KEY:
            logger.warning("⚠️ TON_API_KEY not configured")
            return {'success': False, 'error': 'Configuration missing'}
        
        # الكومنت المتوقع
        expected_comment = f"W{withdrawal_id}-{user_id}" if user_id else f"W{withdrawal_id}"
        
        logger.info(f"🔍 Verifying withdrawal #{withdrawal_id} with comment: {expected_comment}")
        logger.info(f"   Checking USER wallet (recipient): {wallet_address[:10]}...")
        
        # استخدام TON Center API
        api_endpoint = "https://toncenter.com/api/v2/"
        headers = {"X-API-Key": TON_API_KEY} if TON_API_KEY else {}
        
        # فحص المعاملات الواردة لمحفظة العميل (المستلم)
        url = f"{api_endpoint}getTransactions"
        params = {
            'address': wallet_address,  # محفظة العميل (المستلم)
            'limit': 50  # آخر 50 معاملة
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"❌ API returned status {response.status_code}")
            return {'success': False, 'error': f'API returned {response.status_code}'}
        
        data = response.json()
        
        if not data.get('ok') or 'result' not in data:
            logger.error(f"❌ Invalid API response: {data}")
            return {'success': False, 'error': 'Invalid API response'}
        
        transactions = data['result']
        logger.info(f"📊 Checking {len(transactions)} incoming transactions to user wallet...")
        
        # البحث عن المعاملة المطابقة عبر الكومنت فقط
        for idx, tx in enumerate(transactions):
            try:
                # فحص المعاملات الواردة (in_msg)
                in_msg = tx.get('in_msg', {})
                
                if not in_msg:
                    continue
                
                # استخراج الكومنت من message (نفس طريقة waseet.py)
                msg_data = in_msg.get('message', '')
                
                # تحويل dict إلى string إذا لزم الأمر
                if isinstance(msg_data, dict):
                    msg_data = str(msg_data)
                
                # الكومنت قد يكون في msg_data مباشرة كـ string
                comment = str(msg_data) if msg_data else ''
                
                # تخطي المعاملات الفارغة
                if not comment:
                    continue
                
                # طباعة للتشخيص
                logger.debug(f"   TX #{idx}: Message='{comment[:100]}'")
                
                # التحقق من الكومنت
                if expected_comment in comment:
                    # وجدنا المعاملة الصحيحة عبر الكومنت!
                    value = int(in_msg.get('value', '0'))
                    value_ton = value / 1_000_000_000
                    
                    # استخراج tx_hash بشكل صحيح
                    tx_hash = ''
                    tx_id = tx.get('transaction_id', {})
                    if isinstance(tx_id, dict):
                        tx_hash = tx_id.get('hash', '')
                        if not tx_hash:
                            tx_lt = tx_id.get('lt', '')
                            if tx_lt:
                                tx_hash = f"lt:{tx_lt}"
                    
                    # fallback: استخدام hash مباشر
                    if not tx_hash:
                        tx_hash = tx.get('hash', 'unknown')
                    
                    # استخراج عنوان المرسل (الأدمن)
                    source_address = in_msg.get('source', '')
                    
                    logger.info(f"✅ Found matching transaction via comment!")
                    logger.info(f"   Comment: {comment}")
                    logger.info(f"   Amount: {value_ton} TON")
                    logger.info(f"   From: {source_address[:10] if source_address else 'unknown'}...")
                    logger.info(f"   TX Hash: {tx_hash}")
                    
                    return {
                        'success': True,
                        'found': True,
                        'tx_hash': tx_hash,
                        'amount': value_ton,
                        'destination': wallet_address,
                        'source': source_address,
                        'comment': comment
                    }
            
            except Exception as tx_error:
                logger.debug(f"Error processing transaction: {tx_error}")
                continue
        
        # لم نجد المعاملة
        logger.warning(f"⚠️ No matching transaction found for withdrawal #{withdrawal_id}")
        logger.warning(f"   Expected comment: {expected_comment}")
        logger.warning(f"   Checked {len(transactions)} transactions")
        return {
            'success': True,
            'found': False,
            'error': 'No matching transaction found'
        }
        
    except Exception as e:
        logger.error(f"❌ Error in verify_withdrawal_transaction: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

async def approve_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على طلب سحب - مع التحقق التلقائي"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> غير مصرح لك!", show_alert=True)
        return
    
    withdrawal_id = int(query.data.split('_')[2])
    
    # الحصول على معلومات الطلب
    pending = db.get_pending_withdrawals()
    withdrawal = next((w for w in pending if w['id'] == withdrawal_id), None)
    
    if not withdrawal:
        await query.answer("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> الطلب غير موجود!", show_alert=True)
        return
    
    # 🔍 التحقق التلقائي من المعاملة
    if withdrawal['withdrawal_type'] == 'ton' and withdrawal['wallet_address']:
        try:
            await query.edit_message_text(
                "🔍 <b>جاري التحقق من المعاملة...</b>\n\n"
                "يرجى الانتظار...",
                parse_mode=ParseMode.HTML
            )
        except Exception as edit_error:
            # إذا فشل التحديث، نرسل رسالة جديدة
            logger.warning(f"Could not edit message: {edit_error}")
            await query.answer("🔍 جاري التحقق من المعاملة...")
        
        try:
            # فحص المعاملة على الشبكة
            verification = await verify_withdrawal_transaction(
                withdrawal_id=withdrawal_id,
                wallet_address=withdrawal['wallet_address'],
                amount=withdrawal['amount'],
                context=context,
                user_id=withdrawal['user_id']  # ✅ إضافة user_id للفحص عبر الكومنت
            )
            
            if verification['success'] and verification['found']:
                # ✅ وجدنا المعاملة!
                tx_hash = verification['tx_hash']
                
                # الموافقة على السحب
                db.approve_withdrawal(withdrawal_id, user_id, tx_hash)
                
                logger.info(f"✅ Withdrawal #{withdrawal_id} auto-verified and approved")
                
                success_msg = f"""
<tg-emoji emoji-id='5388674524583572460'>🎉</tg-emoji> <b>تم التحقق والموافقة بنجاح!</b>

<tg-emoji emoji-id='5260270009048906733'>💸</tg-emoji> المبلغ: {withdrawal['amount']:.4f} TON
<tg-emoji emoji-id='5453957997418004470'>👤</tg-emoji> المستخدم: {withdrawal['full_name']}
<tg-emoji emoji-id='6005943221455165890'>💳</tg-emoji> المحفظة: <code>{withdrawal['wallet_address'][:10]}...</code>
<tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> TX Hash: <code>{tx_hash[:20]}...</code>

<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تم التحقق من وصول المبلغ تلقائياً
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تم إرسال الإشعار للمستخدم
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تم نشر إثبات الدفع في القناة
"""
                
                # إرسال إشعار للمستخدم
                try:
                    await context.bot.send_message(
                        chat_id=withdrawal['user_id'],
                        text=f"""
<tg-emoji emoji-id='5388674524583572460'>🎉</tg-emoji> <b>تم تأكيد السحب!</b>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> تم استلام {withdrawal['amount']:.4f} TON في محفظتك بنجاح!
<tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> TX Hash: <code>{tx_hash[:16]}...</code>

<tg-emoji emoji-id='5271604874419647061'>🔗</tg-emoji> <a href="https://tonscan.org/tx/{tx_hash}">عرض على TON Explorer</a>

شكراً لاستخدامك Panda Giveaways! <tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji>
""",
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=False
                    )
                except Exception as notify_error:
                    logger.warning(f"Failed to notify user: {notify_error}")
                
                # نشر إثبات الدفع في القناة
                await send_payment_proof_to_channel(
                    context=context,
                    username=withdrawal.get('username', 'مستخدم'),
                    full_name=withdrawal['full_name'],
                    user_id=withdrawal['user_id'],
                    amount=withdrawal['amount'],
                    wallet_address=withdrawal['wallet_address'],
                    tx_hash=tx_hash,
                    withdrawal_id=withdrawal_id
                )
                
                await query.edit_message_text(success_msg, parse_mode=ParseMode.HTML)
                return
            
            elif verification['success'] and not verification['found']:
                # لم نجد المعاملة بعد
                await query.edit_message_text(
                    f"""
<tg-emoji emoji-id='5206617715358217098'>⚠️</tg-emoji> <b>لم يتم العثور على المعاملة</b>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> المبلغ المطلوب: {withdrawal['amount']:.4f} TON
<tg-emoji emoji-id='6005943221455165890'>💳</tg-emoji> المحفظة: <code>{withdrawal['wallet_address']}</code>

<tg-emoji emoji-id='5210943116096681636'>💡</tg-emoji> <b>الأسباب المحتملة:</b>
• لم يتم إرسال المبلغ بعد
• المعاملة لم تصل للشبكة بعد (انتظر 1-2 دقيقة)
• المبلغ المرسل غير مطابق ({withdrawal['amount']:.4f} TON)

<tg-emoji emoji-id='5217697679030637222'>⏳</tg-emoji> يمكنك المحاولة مرة أخرى بعد إرسال المبلغ
""",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 إعادة التحقق", callback_data=f"approve_withdrawal_{withdrawal_id}")],
                        [InlineKeyboardButton("✅ موافقة يدوية", callback_data=f"manual_approve_{withdrawal_id}")],
                        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_withdrawals")]
                    ])
                )
                return
            
            else:
                # خطأ في التحقق
                await query.edit_message_text(
                    f"""
<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>خطأ في التحقق</b>

الخطأ: {verification.get('error', 'Unknown')}

<tg-emoji emoji-id='5210943116096681636'>💡</tg-emoji> يمكنك المحاولة مرة أخرى أو الموافقة يدوياً
""",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"approve_withdrawal_{withdrawal_id}")],
                        [InlineKeyboardButton("✅ موافقة يدوية", callback_data=f"manual_approve_{withdrawal_id}")],
                        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_withdrawals")]
                    ])
                )
                return
                
        except Exception as e:
            logger.error(f"Error in auto-verification: {e}")
            await query.edit_message_text(
                f"""
<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>خطأ في التحقق</b>

حدث خطأ أثناء التحقق من المعاملة.

<tg-emoji emoji-id='5210943116096681636'>💡</tg-emoji> يمكنك المحاولة مرة أخرى أو الموافقة يدوياً
""",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 إعادة المحاولة", callback_data=f"approve_withdrawal_{withdrawal_id}")],
                    [InlineKeyboardButton("✅ موافقة يدوية", callback_data=f"manual_approve_{withdrawal_id}")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="admin_withdrawals")]
                ])
            )
            return
    
    # Vodafone cash أو fallback للموافقة اليدوية
    db.approve_withdrawal(withdrawal_id, user_id, None)
    
    approval_msg = f"""
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>تم الموافقة على الطلب #{withdrawal_id}</b>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> المبلغ: {withdrawal['amount']:.4f} TON
<tg-emoji emoji-id='5453957997418004470'>👤</tg-emoji> المستخدم: {withdrawal['full_name']}
"""
    
    if withdrawal['withdrawal_type'] == 'vodafone':
        approval_msg += f"\n<tg-emoji emoji-id='5472201536727686043'>📞</tg-emoji> <b>الرقم:</b> <code>{withdrawal['phone_number']}</code>\n\n<tg-emoji emoji-id='5206617715358217098'>⚠️</tg-emoji> يرجى إرسال المبلغ يدوياً إلى الرقم أعلاه"
    else:
        approval_msg += f"\n<tg-emoji emoji-id='5350619413533958825'>🔐</tg-emoji> <b>المحفظة:</b> <code>{withdrawal['wallet_address']}</code>\n\n<tg-emoji emoji-id='5206617715358217098'>⚠️</tg-emoji> يرجى إرسال المبلغ يدوياً إلى المحفظة أعلاه"
        approval_msg += f"\n\n<tg-emoji emoji-id='5210943116096681636'>💡</tg-emoji> <b>ملاحظة:</b> بعد إرسال المبلغ، استخدم /add_tx_hash_{withdrawal_id} لإضافة tx_hash ونشره في قناة الإثباتات"
    
    # إرسال إشعار للمستخدم
    try:
        await context.bot.send_message(
            chat_id=withdrawal['user_id'],
            text=f"""
<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> <b>تمت الموافقة على طلب السحب!</b>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> المبلغ: {withdrawal['amount']:.4f} TON
<tg-emoji emoji-id='5373236586760651455'>📅</tg-emoji> سيتم التحويل خلال 24 ساعة

شكراً لصبرك! <tg-emoji emoji-id='6008183145684277336'>🐼</tg-emoji>
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

async def manual_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة اليدوية على طلب سحب بدون تحقق تلقائي"""
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
    
    # الموافقة يدوياً بدون tx_hash
    db.approve_withdrawal(withdrawal_id, user_id, None)
    
    approval_msg = f"""
✅ <b>تمت الموافقة اليدوية على الطلب #{withdrawal_id}</b>

💰 المبلغ: {withdrawal['amount']:.4f} TON
👤 المستخدم: {withdrawal['full_name']}
"""
    
    if withdrawal['withdrawal_type'] == 'vodafone':
        approval_msg += f"\n📞 <b>الرقم:</b> <code>{withdrawal['phone_number']}</code>\n\n⚠️ يرجى إرسال المبلغ يدوياً"
    else:
        approval_msg += f"\n🔐 <b>المحفظة:</b> <code>{withdrawal['wallet_address']}</code>\n\n⚠️ بعد الإرسال، استخدم /add_tx_hash {withdrawal_id} <tx_hash>"
    
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

async def check_transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فحص المعاملات المعلقة - للأدمن فقط"""
    user_id = update.effective_user.id    
    if not is_admin(user_id):
        await update.message.reply_text("❌ هذا الأمر للإدمن فقط!")
        return
    status_msg = await update.message.reply_text("🔍 <b>جاري فحص المعاملات...</b>\n\nيرجى الانتظار...", parse_mode=ParseMode.HTML)
    try:
        result = await check_pending_withdrawals_transactions(context)
        if result['success']:
            if result['found'] > 0:
                await status_msg.edit_text(f"🎉 <b>تم العثور على معاملات!</b>\n\n✅ تم تأكيد: {result['found']} سحب\n🔍 تم فحص: {result['checked']} سحب\n⏳ إجمالي معلق: {result['total_pending']}\n\n💡 تم نشر الإثباتات في قناة السحوبات!", parse_mode=ParseMode.HTML)
            else:
                await status_msg.edit_text(f"💡 <b>لا توجد معاملات جديدة</b>\n\n🔍 تم فحص: {result['checked']} سحب\n⏳ إجمالي معلق: {result['total_pending']}\n\n💡 لم يتم العثور على معاملات مطابقة حتى الآن.", parse_mode=ParseMode.HTML)
        else:
            await status_msg.edit_text(f"❌ <b>خطأ في الفحص</b>\n\nالخطأ: {result.get('error', 'Unknown')}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in check_transactions_command: {e}")
        await status_msg.edit_text(f"❌ <b>خطأ</b>\n\n{str(e)}", parse_mode=ParseMode.HTML)

# ═══════════════════════════════════════════════════════════════
# � ADD TX HASH FOR MANUAL WITHDRAWALS
# ═══════════════════════════════════════════════════════════════

async def add_tx_hash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة tx_hash لسحب تمت الموافقة عليه يدوياً"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> هذا الأمر للإدمن فقط!")
        return
    
    # التحقق من صيغة الأمر
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> صيغة خاطئة!\n\n"
            "الاستخدام الصحيح:\n"
            "/add_tx_hash <withdrawal_id> <tx_hash>\n\n"
            "مثال:\n"
            "/add_tx_hash 123 64-utInJYG0mrpAy77spv_QyRqAIlqOb...",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        withdrawal_id = int(context.args[0])
        tx_hash = context.args[1]
        
        # الحصول على معلومات السحب
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT w.*, u.username, u.full_name
            FROM withdrawals w
            JOIN users u ON w.user_id = u.user_id
            WHERE w.id = ? AND w.status = 'completed'
        """, (withdrawal_id,))
        
        withdrawal = cursor.fetchone()
        
        if not withdrawal:
            await update.message.reply_text(f"<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> لم يتم العثور على سحب مكتمل برقم #{withdrawal_id}")
            conn.close()
            return
        
        withdrawal_dict = dict(withdrawal)
        
        # تحديث tx_hash في قاعدة البيانات
        cursor.execute("""
            UPDATE withdrawals 
            SET tx_hash = ?
            WHERE id = ?
        """, (tx_hash, withdrawal_id))
        
        conn.commit()
        conn.close()
        
        # نشر إثبات الدفع في القناة
        await send_payment_proof_to_channel(
            context=context,
            username=withdrawal_dict.get('username', 'مستخدم'),
            full_name=withdrawal_dict['full_name'],
            user_id=withdrawal_dict['user_id'],
            amount=withdrawal_dict['amount'],
            wallet_address=withdrawal_dict['wallet_address'],
            tx_hash=tx_hash,
            withdrawal_id=withdrawal_id
        )
        
        await update.message.reply_text(
            f"<tg-emoji emoji-id='5260463209562776385'>✅</tg-emoji> تم تحديث TX Hash للسحب #{withdrawal_id}\n"
            f"<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> تم نشر الإثبات في قناة الإثباتات",
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"✅ TX Hash added for withdrawal #{withdrawal_id} by admin {user_id}")
        
    except ValueError:
        await update.message.reply_text(
            "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> رقم السحب يجب أن يكون رقماً صحيحاً!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error adding tx_hash: {e}")
        await update.message.reply_text(f"<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> حدث خطأ: {str(e)}")

# ═══════════════════════════════════════════════════════════════
# �📢 BROADCAST SYSTEM
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
        await message.reply_text("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> نوع الرسالة غير مدعوم. أرسل نص أو صورة أو ملصق فقط.")
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
        await update.message.reply_text("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> الرابط غير صحيح. يجب أن يبدأ بـ http:// أو https://")
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
        await update.message.reply_text("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> نوع الرسالة غير مدعوم.")
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
        await query.answer("<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> غير مصرح لك!", show_alert=True)
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
<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> <b>تم رفض طلب السحب</b>

<tg-emoji emoji-id='5278467510604160626'>💰</tg-emoji> المبلغ: {withdrawal['amount']:.4f} TON
<tg-emoji emoji-id='5197269100878907942'>📝</tg-emoji> السبب: تم الرفض من قبل الإدارة

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

@verification_app.route('/', methods=['GET'])
def health_check():
    """فحص صحة الخادم"""
    return jsonify({
        'status': 'ok',
        'service': 'Panda Giveaways Verification Server',
        'timestamp': datetime.now().isoformat(),
        'endpoints': ['/verify-subscription', '/check-bot-admin', '/device-verified']
    })

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
        
        # استخدام Telegram Bot API مباشرة مع المعالجة المحسنة
        try:
            import requests as req
            api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/getChatMember'
            
            # محاولتين مع timeout مناسب
            for attempt in range(2):
                try:
                    response = req.post(api_url, json={
                        'chat_id': f'@{channel_username}',
                        'user_id': user_id
                    }, timeout=15)  # زيادة timeout
                    
                    if response.status_code == 200:
                        break
                        
                except (req.exceptions.RequestException, req.exceptions.Timeout) as e:
                    if attempt == 0:  # محاولة أولى
                        logger.warning(f"⚠️ Timeout on attempt {attempt + 1} for channel {channel_username}: {e}")
                        continue
                    else:  # محاولة أخيرة
                        logger.error(f"❌ Failed after 2 attempts for channel {channel_username}: {e}")
                        return jsonify({
                            'success': False,
                            'is_subscribed': False,
                            'error': f'Connection timeout after multiple attempts: {str(e)}'
                        }), 503
            
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
            
            # محاولتين مع timeout محسن
            for attempt in range(2):
                try:
                    response = req.post(api_url, json={
                        'chat_id': f'@{channel_username}',
                        'user_id': bot_id
                    }, timeout=15)  # زيادة timeout
                    
                    if response.status_code == 200:
                        break
                        
                except (req.exceptions.RequestException, req.exceptions.Timeout) as e:
                    if attempt == 0:
                        logger.warning(f"⚠️ Admin check timeout on attempt {attempt + 1} for channel {channel_username}: {e}")
                        continue
                    else:
                        logger.error(f"❌ Admin check failed after 2 attempts for channel {channel_username}: {e}")
                        return jsonify({
                            'success': False,
                            'is_admin': False,
                            'error': f'Connection timeout: {str(e)}'
                        }), 503
            
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

@verification_app.route('/device-verified', methods=['POST'])
def handle_device_verified():
    """استقبال إشعار عند التحقق من جهاز المستخدم"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
        logger.info(f"🔔 Device verified notification for user {user_id}")
        
        # إرسال رسالة تأكيد للمستخدم عبر البوت
        try:
            import requests as req
            
            # الحصول على بيانات المستخدم
            user = db.get_user(user_id)
            full_name = user.full_name if user else "المستخدم"
            
            # التحقق من وجود referrer_id في قاعدة البيانات
            referrer_id = user.referrer_id if user else None
            
            # إذا فشل الحصول على referrer_id، استخدم الرابط الافتراضي
            if not referrer_id:
                # محاولة الحصول على referrer_id من البيانات المرسلة (fallback)
                referrer_id = data.get('referrer_id')
            
            success_text = f"""
✅ تم التحقق من جهازك بنجاح!

عزيزي {full_name} تم التحقق من جهازك بنجاح! 🎉

🎯 يمكنك الآن استخدام البوت بحرية!
"""
            
            # إنشاء رابط البوت (مع الإحالة إذا وجدت)
            if referrer_id:
                bot_link = f"https://t.me/{BOT_USERNAME}?start=ref_{referrer_id}"
                button_text = "🚀 متابعة للبوت"
            else:
                # إذا فشل كل شيء، استخدم الرابط المرسل من المستخدم كـ fallback
                fallback_link = data.get('fallback_link', f"https://t.me/{BOT_USERNAME}")
                bot_link = fallback_link
                button_text = "🚀 فتح البوت"
            
            # إرسال الرسالة مع زر عبر Bot API
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": user_id,
                "text": success_text,
                "parse_mode": "HTML",
                "reply_markup": {
                    "inline_keyboard": [[
                        {
                            "text": button_text,
                            "url": bot_link
                        }
                    ]]
                }
            }
            resp = req.post(url, json=payload, timeout=10)
            
            if resp.ok:
                logger.info(f"✅ Verification success message sent to user {user_id}")
            else:
                logger.error(f"❌ Failed to send message: {resp.text}")
            
            return jsonify({'success': True, 'message': 'Notification sent'})
            
        except Exception as bot_error:
            logger.error(f"❌ Error sending message to user {user_id}: {bot_error}")
            return jsonify({'success': False, 'error': 'Failed to send message'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error in handle_device_verified: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@verification_app.route('/user-banned', methods=['POST'])
def handle_user_banned():
    """استقبال إشعار عند حظر مستخدم بسبب التعدد"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        reason = data.get('reason', 'unknown')
        ban_reason = data.get('ban_reason', 'تم اكتشاف حسابات متعددة')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
        logger.info(f"🔴 User banned notification for user {user_id}, reason: {reason}")
        
        # إرسال رسالة للمستخدم المحظور
        try:
            import requests as req
            
            # الحصول على بيانات المستخدم
            user = db.get_user(user_id)
            full_name = user.full_name if user else "المستخدم"
            
            # تحديد نص الرسالة حسب سبب الحظر
            if reason == 'duplicate_device':
                ban_text = f"""
⛔ <b>تم حظرك من البوت</b>

عزيزي <b>{full_name}</b>،

تم اكتشاف استخدام هذا الجهاز لحساب آخر مسبقاً.

<b>السبب:</b> جهاز مسجل مسبقاً لمستخدم آخر
<b>📌 ملاحظة:</b> كل جهاز يمكن استخدامه لحساب واحد فقط

<b>🔒 حالة الحساب:</b> محظور

إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.
"""
            elif reason == 'ip_limit_exceeded':
                ban_text = f"""
⛔ <b>تم حظرك من البوت</b>

عزيزي <b>{full_name}</b>،

تم تجاوز الحد الأقصى للحسابات من نفس الشبكة.

<b>السبب:</b> تجاوز الحد الأقصى (3 حسابات لكل شبكة)
<b>📌 ملاحظة:</b> هذا الإجراء لضمان نزاهة النظام

<b>🔒 حالة الحساب:</b> محظور

إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.
"""
            else:
                ban_text = f"""
⛔ <b>تم حظرك من البوت</b>

عزيزي <b>{full_name}</b>،

تم حظر حسابك من البوت.

<b>السبب:</b> {ban_reason}
<b>🔒 حالة الحساب:</b> محظور

إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.
"""
            
            # إرسال الرسالة عبر Bot API
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": user_id,
                "text": ban_text,
                "parse_mode": "HTML"
            }
            resp = req.post(url, json=payload, timeout=10)
            
            if resp.ok:
                logger.info(f"✅ Ban notification sent to user {user_id}")
            else:
                logger.error(f"❌ Failed to send ban notification: {resp.text}")
            
            return jsonify({'success': True, 'message': 'Ban notification sent'})
            
        except Exception as bot_error:
            logger.error(f"❌ Error sending ban notification to user {user_id}: {bot_error}")
            return jsonify({'success': False, 'error': 'Failed to send message'}), 500
            
    except Exception as e:
        logger.error(f"❌ Error in handle_user_banned: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    """تشغيل Flask server في thread منفصل مع معالجة أفضل للأخطاء"""
    try:
        logger.info("🌐 Starting Flask verification server on port 8081...")
        
        # إعداد أفضل للخادم
        verification_app.config['DEBUG'] = False
        verification_app.config['TESTING'] = False
        
        # تشغيل الخادم مع إعدادات محسنة
        from werkzeug.serving import WSGIRequestHandler
        WSGIRequestHandler.timeout = 30  # زيادة timeout للطلبات
        
        verification_app.run(
            host='0.0.0.0', 
            port=8081, 
            debug=False, 
            use_reloader=False,
            threaded=True  # تمكين threading
        )
    except Exception as e:
        logger.error(f"❌ Failed to start Flask server: {e}")
        logger.info("⚠️ Bot will continue without verification server")

# ═══════════════════════════════════════════════════════════════
# � WEB APP DATA HANDLER
# ═══════════════════════════════════════════════════════════════

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج استقبال البيانات من Mini App (صفحة التحقق)
    """
    try:
        logger.info("🔔 handle_web_app_data called!")
        
        user = update.effective_user
        user_id = user.id
        username = user.username or f"user_{user_id}"
        full_name = user.full_name or username
        
        logger.info(f"👤 User: {user_id} - {full_name}")
        
        # التحقق من وجود web_app_data
        if not update.effective_message or not update.effective_message.web_app_data:
            logger.error("❌ No web_app_data found in update")
            return
        
        # استخراج البيانات المرسلة من Mini App
        web_app_data = update.effective_message.web_app_data.data
        
        logger.info(f"📱 Received web app data from user {user_id}: {web_app_data[:100]}...")
        
        # تحليل البيانات JSON
        import json
        data = json.loads(web_app_data)
        
        logger.info(f"📊 Parsed data: fingerprint={data.get('fingerprint', 'N/A')[:20]}...")
        
        fingerprint = data.get('fingerprint')
        meta = data.get('meta', {})
        
        if not fingerprint:
            logger.error("❌ No fingerprint in data")
            await update.message.reply_text(
                "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> حدث خطأ في استقبال البيانات. حاول مرة أخرى.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # إرسال البيانات لـ API للحفظ في قاعدة البيانات
        try:
            import requests as req
            
            # الحصول على IP address (محاولة من metadata)
            ip_address = meta.get('ip', 'Unknown')
            
            # حفظ البيانات في قاعدة البيانات مباشرة
            api_url = f"{API_BASE_URL}/fingerprint"
            
            # إنشاء token مؤقت للتحقق
            token_url = f"{API_BASE_URL}/verification/create-token"
            token_resp = req.post(token_url, json={'user_id': user_id}, timeout=5)
            
            fp_token = None
            if token_resp.ok:
                token_data = token_resp.json()
                fp_token = token_data.get('token')
            
            # إرسال البيانات للحفظ
            payload = {
                'user_id': user_id,
                'fingerprint': fingerprint,
                'fp_token': fp_token,
                'meta': meta
            }
            
            api_resp = req.post(api_url, json=payload, timeout=10)
            
            if api_resp.ok:
                result = api_resp.json()
                
                if result.get('ok'):
                    # نجح التحقق - إرسال رسالة تأكيد
                    success_text = f"""
✅ <b>تم التحقق من جهازك بنجاح!</b>

عزيزي <b>{full_name}</b>، تم التحقق من جهازك بنجاح! 🎉

<b>📊 معلومات التحقق:</b>
🔐 بصمة الجهاز: <code>{fingerprint[:16]}...</code>
🌐 عنوان IP: <code>{meta.get('ip', 'N/A')}</code>
📱 الدقة: {meta.get('rez', 'N/A')}
🕐 التوقيت: {meta.get('tz', 'N/A')}

<b>🎯 يمكنك الآن استخدام البوت بحرية!</b>

استخدم /start لرؤية القائمة الرئيسية
"""
                    
                    keyboard = [[InlineKeyboardButton(
                        "🏠 العودة للقائمة الرئيسية",
                        callback_data="back_to_start"
                    )]]
                    
                    await update.message.reply_text(
                        success_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    
                    # ═══════════════════════════════════════════════════════
                    # 🎯 التحقق التلقائي من القنوات بعد التحقق من الجهاز
                    # ═══════════════════════════════════════════════════════
                    
                    # التحقق من وجود إحالة معلقة
                    has_pending_referrer = context.user_data.get('pending_referrer_id') is not None
                    
                    # التحقق من الاشتراك في القنوات تلقائياً
                    required_channels = db.get_active_mandatory_channels()
                    
                    if required_channels:
                        not_subscribed = []
                        for channel in required_channels:
                            channel_id = channel['channel_id']
                            try:
                                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                                if member.status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                                    not_subscribed.append(channel)
                            except Exception as e:
                                logger.error(f"Error checking channel {channel_id}: {e}")
                                not_subscribed.append(channel)
                        
                        if not_subscribed:
                            # المستخدم غير مشترك - إرسال رسالة اشتراك إجباري
                            first_channel = not_subscribed[0]
                            
                            subscription_text = f"""
<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> <b>خطوة أخيرة!</b>

عزيزي <b>{full_name}</b>، تم التحقق من جهازك بنجاح! ✅

الآن، يجب الاشتراك في القناة التالية للمتابعة:

• <b>{first_channel['channel_name']}</b>

بعد الاشتراك، اضغط على زر "✅ تحققت من الاشتراك" أدناه.
"""
                            
                            keyboard = [
                                [InlineKeyboardButton(
                                    f"<tg-emoji emoji-id='5370599459661045441'>🤍</tg-emoji> {first_channel['channel_name']}",
                                    url=first_channel['channel_url']
                                )],
                                [InlineKeyboardButton(
                                    "✅ تحققت من الاشتراك",
                                    callback_data="check_subscription"
                                )]
                            ]
                            
                            await update.message.reply_text(
                                subscription_text,
                                parse_mode=ParseMode.HTML,
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                            
                            return
                    
                    # المستخدم مشترك في جميع القنوات - احتساب الإحالة
                    referrer_id = context.user_data.get('pending_referrer_id')
                    if referrer_id:
                        # التحقق من أن المُحيل ليس محظوراً
                        referrer_user = db.get_user(referrer_id)
                        if referrer_user and not referrer_user.is_banned:
                            # التحقق من أن المستخدم الجديد ليس محظوراً
                            new_user = db.get_user(user_id)
                            if new_user and not new_user.is_banned:
                                # التحقق من عدم وجود إحالة مسجلة مسبقاً
                                conn = db.get_connection()
                                cursor = conn.cursor()
                                cursor.execute("SELECT * FROM referrals WHERE referred_id = ?", (user_id,))
                                existing_ref = cursor.fetchone()
                                
                                if not existing_ref:
                                    # تسجيل الإحالة
                                    now = datetime.now().isoformat()
                                    try:
                                        cursor.execute("""
                                            INSERT INTO referrals (referrer_id, referred_id, created_at, channels_checked, device_verified, is_valid)
                                            VALUES (?, ?, ?, 1, 1, 1)
                                        """, (referrer_id, user_id, now))
                                        
                                        # تحديث عدد الإحالات للداعي
                                        cursor.execute("""
                                            UPDATE users 
                                            SET total_referrals = total_referrals + 1,
                                                valid_referrals = valid_referrals + 1
                                            WHERE user_id = ?
                                        """, (referrer_id,))
                                        
                                        # التحقق من استحقاق لفة جديدة
                                        cursor.execute("SELECT valid_referrals, available_spins FROM users WHERE user_id = ?", (referrer_id,))
                                        ref_data = cursor.fetchone()
                                        if ref_data:
                                            valid_refs = ref_data['valid_referrals']
                                            current_spins = ref_data['available_spins']
                                            
                                            # كل 5 إحالات = لفة واحدة
                                            if valid_refs % SPINS_PER_REFERRALS == 0:
                                                cursor.execute("""
                                                    UPDATE users 
                                                    SET available_spins = available_spins + 1 
                                                    WHERE user_id = ?
                                                """, (referrer_id,))
                                                
                                                # إرسال إشعار للداعي
                                                remaining_for_next = SPINS_PER_REFERRALS
                                                try:
                                                    await context.bot.send_message(
                                                        chat_id=referrer_id,
                                                        text=f"""
🎉 <b>تهانينا! إحالة جديدة ناجحة!</b>

✅ المستخدم <b>{full_name}</b> انضم عبر رابطك وأكمل جميع الخطوات!

🎁 <b>حصلت على لفة مجانية!</b>
🎰 <b>لفاتك المتاحة:</b> {current_spins + 1}

👥 <b>إجمالي إحالاتك الصحيحة:</b> {valid_refs}
⏳ <b>متبقي للفة القادمة:</b> {remaining_for_next} إحالات

<b>استمر في الدعوة واربح المزيد! 🚀</b>
""",
                                                        parse_mode=ParseMode.HTML
                                                    )
                                                except Exception as e:
                                                    logger.error(f"Failed to send referral notification: {e}")
                                            else:
                                                # إرسال إشعار بدون لفة
                                                remaining_for_next = SPINS_PER_REFERRALS - (valid_refs % SPINS_PER_REFERRALS)
                                                try:
                                                    await context.bot.send_message(
                                                        chat_id=referrer_id,
                                                        text=f"""
✅ <b>إحالة جديدة ناجحة!</b>

👤 المستخدم <b>{full_name}</b> انضم عبر رابطك وأكمل جميع الخطوات!

👥 <b>إجمالي إحالاتك الصحيحة:</b> {valid_refs}
⏳ <b>متبقي للفة القادمة:</b> {remaining_for_next} إحالات

<b>استمر في الدعوة! 💪</b>
""",
                                                        parse_mode=ParseMode.HTML
                                                    )
                                                except Exception as e:
                                                    logger.error(f"Failed to send referral notification: {e}")
                                        
                                        conn.commit()
                                        logger.info(f"✅ Referral validated and counted after device verification: {referrer_id} -> {user_id}")
                                        
                                    except sqlite3.IntegrityError:
                                        logger.warning(f"⚠️ Referral already exists: {referrer_id} -> {user_id}")
                                
                                conn.close()
                                
                                # مسح البيانات المؤقتة
                                if 'pending_referrer_id' in context.user_data:
                                    del context.user_data['pending_referrer_id']
                    
                    logger.info(f"✅ Device verified successfully for user {user_id}")
                else:
                    # فشل التحقق
                    error_reason = result.get('error', 'خطأ غير معروف')
                    
                    if 'duplicate' in error_reason.lower():
                        error_text = f"""
⚠️ <b>جهاز مسجل مسبقاً</b>

عزيزي <b>{full_name}</b>، هذا الجهاز مسجل بالفعل لمستخدم آخر.

<b>📌 ملاحظة:</b>
• كل جهاز يمكن استخدامه لحساب واحد فقط
• هذا الإجراء لضمان نزاهة النظام

إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.
"""
                    elif 'ip_limit' in error_reason.lower():
                        error_text = f"""
⚠️ <b>تجاوز الحد الأقصى</b>

عزيزي <b>{full_name}</b>، تم تجاوز الحد الأقصى للحسابات من هذه الشبكة.

<b>📌 الحد الأقصى:</b> 3 حسابات لكل شبكة

إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.
"""
                    else:
                        error_text = f"""
❌ <b>فشل التحقق</b>

عزيزي <b>{full_name}</b>، حدث خطأ أثناء التحقق من جهازك.

<b>السبب:</b> {error_reason}

حاول مرة أخرى أو تواصل مع الدعم.
"""
                    
                    await update.message.reply_text(
                        error_text,
                        parse_mode=ParseMode.HTML
                    )
                    
                    logger.warning(f"⚠️ Device verification failed for user {user_id}: {error_reason}")
            else:
                # فشل الاتصال بـ API
                await update.message.reply_text(
                    "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> حدث خطأ في الاتصال بالخادم. حاول مرة أخرى لاحقاً.",
                    parse_mode=ParseMode.HTML
                )
                logger.error(f"❌ API request failed: {api_resp.status_code}")
                
        except Exception as api_error:
            logger.error(f"❌ Error sending data to API: {api_error}")
            await update.message.reply_text(
                "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> حدث خطأ في معالجة البيانات. حاول مرة أخرى.",
                parse_mode=ParseMode.HTML
            )
    
    except Exception as e:
        logger.error(f"❌ Error in handle_web_app_data: {e}")
        import traceback
        traceback.print_exc()
        
        await update.message.reply_text(
            "<tg-emoji emoji-id='5273914604752216432'>❌</tg-emoji> حدث خطأ غير متوقع. حاول مرة أخرى لاحقاً.",
            parse_mode=ParseMode.HTML
        )

# ═══════════════════════════════════════════════════════════════
# �🚀 MAIN FUNCTION
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
    
    # تشغيل Flask server في thread منفصل مع فحص إضافي
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # انتظار قصير للتأكد من تشغيل الخادم
    import time
    time.sleep(2)
    
    # فحص بسيط لحالة الخادم
    try:
        import requests as req
        test_response = req.get('http://localhost:8081/', timeout=5)
        logger.info("✅ Flask verification server started successfully on port 8081")
    except Exception as server_check_error:
        logger.warning(f"⚠️ Flask server health check failed: {server_check_error}")
        logger.info("🔄 Server will continue to attempt startup...")
    
    # اختبار الاتصال بـ Telegram
    try:
        import requests as req
        bot_test = req.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getMe', timeout=10)
        if bot_test.ok:
            bot_info = bot_test.json()
            logger.info(f"✅ Telegram Bot API connection successful: @{bot_info['result']['username']}")
        else:
            logger.error(f"❌ Telegram Bot API test failed: {bot_test.status_code}")
    except Exception as telegram_error:
        logger.error(f"❌ Could not test Telegram connection: {telegram_error}")
    
    logger.info("🚀 Bot initialization completed")
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("referrals", referrals_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("add_tx_hash", add_tx_hash_command))
    application.add_handler(CommandHandler("check_transactions", check_transactions_command))  # ✅ فحص المعاملات يدوياً
    
    # معالج استقبال بيانات التحقق من Mini App (يجب أن يكون في البداية!)
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    logger.info("✅ Web App Data handler registered")
    
    # معالج Inline Query
    application.add_handler(InlineQueryHandler(inline_query_handler))
    
    # معالجات Callback
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_withdrawals_callback, pattern="^admin_withdrawals$"))
    application.add_handler(CallbackQueryHandler(admin_tasks_callback, pattern="^admin_tasks$"))
    application.add_handler(CallbackQueryHandler(admin_check_user_callback, pattern="^admin_check_user$"))
    application.add_handler(CallbackQueryHandler(admin_detailed_stats_callback, pattern="^admin_detailed_stats$"))
    application.add_handler(CallbackQueryHandler(toggle_auto_withdrawal_callback, pattern="^toggle_auto_withdrawal$"))
    application.add_handler(CallbackQueryHandler(toggle_bot_status_callback, pattern="^toggle_bot_status$"))
    application.add_handler(CallbackQueryHandler(toggle_verification_callback, pattern="^toggle_verification$"))
    application.add_handler(CallbackQueryHandler(back_to_start_callback, pattern="^back_to_start$"))
    
    # معالجات النسخ الاحتياطي
    application.add_handler(CallbackQueryHandler(create_backup_callback, pattern="^create_backup$"))
    
    # ConversationHandler لاستعادة النسخة الاحتياطية
    restore_backup_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(restore_backup_start, pattern="^restore_backup_start$")],
        states={
            RESTORE_BACKUP: [MessageHandler(filters.Document.ALL, restore_backup_handler)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    application.add_handler(restore_backup_conv_handler)
    application.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))
    application.add_handler(CallbackQueryHandler(approve_withdrawal_callback, pattern="^approve_withdrawal_"))
    application.add_handler(CallbackQueryHandler(manual_approve_callback, pattern="^manual_approve_"))  # ✅ موافقة يدوية
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
    
    # ⛔ معالج السحب التلقائي معطل نهائياً لأسباب أمنية
    # ❌ لن يتم معالجة AUTO_PROCESS_WITHDRAWAL تلقائياً بعد الآن
    # ✅ كل الدفعات يدوية مع التحقق من المعاملات عبر TON API
    
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
    
    # معالج عام لرصد جميع الرسائل (للتشخيص)
    async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج لرصد جميع التحديثات"""
        logger.info(f"🔍 Update received: {update}")
        if update.effective_message:
            logger.info(f"📨 Message type: {type(update.effective_message)}")
            if hasattr(update.effective_message, 'web_app_data'):
                logger.info(f"🌐 Has web_app_data: {update.effective_message.web_app_data}")
    
    # لا تضيف هذا في الإنتاج - فقط للتشخيص
    # application.add_handler(MessageHandler(filters.ALL, log_all_updates), group=999)
    
    # تشغيل البوت
    logger.info("✅ All handlers registered successfully!")
    logger.info("📱 Bot is ready to receive messages and web app data...")
    logger.info("🔄 Starting polling...")
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
