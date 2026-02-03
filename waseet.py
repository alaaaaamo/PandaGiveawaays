"""
╔════════════════════════════════════════════════════════════════╗
║         OMAR PANDA - TON ESCROW SYSTEM                         ║
║         Professional Telegram Escrow Bot                       ║
║         Version 1.0.0 - Production Ready                       ║
╚════════════════════════════════════════════════════════════════╝

نظام وساطة مالية احترافي متكامل على شبكة TON
يعمل داخل جروب تيليجرام مغلق
آمن - شفاف - أوتوماتيكي
"""

import os
import re
import json
import time
import random
import asyncio
import logging
import sqlite3
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import quote
from urllib.parse import quote

# إعداد الـ logging أولاً
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # للطباعة على الشاشة
    ]
)
logger = logging.getLogger(__name__)

# تشغيل DEBUG mode لمزيد من التفاصيل
logger.setLevel(logging.INFO)

# TON SDK imports
try:
    import requests
    from tonsdk.contract.wallet import Wallets, WalletVersionEnum
    from tonsdk.utils import bytes_to_b64str, to_nano, from_nano
    TON_SDK_AVAILABLE = True
    logger.info("✅ tonsdk imported successfully")
except ImportError as e:
    TON_SDK_AVAILABLE = False
    logger.warning(f"⚠️ tonsdk import failed: {e}")
    logger.warning("⚠️ Install with: pip install tonsdk requests")

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    Message,
    ChatMember
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode, ChatMemberStatus

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔧 CONFIGURATION - ضع بياناتك هنا مباشرة
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ═══════════════════════════════════════════════════════════════
# ⚙️ إعدادات التليجرام
# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = "8549981006:AAEQp3I1mVJugRZGhESlU0NrgTqbSZ1VDpg"  # ضع توكن البوت هنا

# ═══════════════════════════════════════════════════════════════
# 💰 إعدادات محفظة TON
# ═══════════════════════════════════════════════════════════════
TON_WALLET_ADDRESS = "UQAcdvPZiHOUw31Ng59nZQzGVYPg4TEVNgznc0d48sQSog2M"  # عنوان المحفظة

# 🔑 المفاتيح السرية للمحفظة (24 كلمة)
# ⚠️ احذر: لا تشارك هذه الكلمات مع أحد!
WALLET_MNEMONIC = [
    "right", "question", "outdoor", "congress", "extend", "attract",
    "force", "bonus", "oven", "green", "benefit", "noble",
    "split", "birth", "just", "civil", "ask", "exhaust",
    "poverty", "bag", "social", "budget", "congress", "ride"
]

# أو يمكنك وضعها كنص واحد:
WALLET_MNEMONIC_STRING = "right question outdoor congress extend attract force bonus oven green benefit noble split birth just civil ask exhaust poverty bag social budget congress ride"

# API (اختياري - للاستعلام فقط)
TON_API_KEY = "your_api_key_here"  # من toncenter.com
TON_API_URL = "https://toncenter.com/api/v2/getTransactions"
TON_API_URL_SEND = "https://toncenter.com/api/v2/sendBoc"

# ═══════════════════════════════════════════════════════════════
# ⚙️ إعدادات النظام
# ═══════════════════════════════════════════════════════════════
SYSTEM_FEE_PERCENT = 0  # 0% عمولة النظام
PAYMENT_TIMEOUT_MINUTES = 30
MIN_CONFIRMATIONS = 2
DATABASE_PATH = "escrow_system.db"

# ═══════════════════════════════════════════════════════════════
# 👥 المالكين والوسطاء
# ═══════════════════════════════════════════════════════════════
OWNER_IDS = [8394741263, 1797127532]  # المالكين - لهم كل الصلاحيات
ADMIN_IDS = []  # الوسطاء - يتم إدارتهم من المالكين

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 DATA MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DealStatus(Enum):
    """حالات الصفقة"""
    CREATED = "CREATED"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    PAID = "PAID"
    WAITING_DELIVERY = "WAITING_DELIVERY"
    DELIVERED = "DELIVERED"
    WAITING_RECEIPT = "WAITING_RECEIPT"
    READY_TO_WITHDRAW = "READY_TO_WITHDRAW"
    COMPLETED = "COMPLETED"
    DISPUTE = "DISPUTE"
    CANCELLED = "CANCELLED"

class UserRole(Enum):
    """أدوار المستخدمين"""
    BUYER = "buyer"
    SELLER = "seller"

@dataclass
class Deal:
    """نموذج الصفقة"""
    deal_id: str
    group_id: int
    buyer_id: int
    seller_id: int
    amount: float
    description: str
    status: str
    created_at: str
    comment: str
    payment_tx_hash: Optional[str] = None
    withdraw_tx_hash: Optional[str] = None
    withdraw_address: Optional[str] = None
    withdraw_memo: Optional[str] = None
    buyer_screenshot: Optional[str] = None
    seller_screenshot: Optional[str] = None
    pinned_message_id: Optional[int] = None
    mediator_id: Optional[int] = None
    updated_at: Optional[str] = None
    buyer_address: Optional[str] = None  # عنوان المشتري لإرجاع المبلغ

    def to_dict(self) -> dict:
        return asdict(self)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🗄️ DATABASE MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        logger.info("🗄️ Initializing database...")
        self.init_database()
        logger.info("✅ Database initialized successfully")
    
    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)  # timeout أطول 30 ثانية
        conn.execute("PRAGMA journal_mode=WAL")  # استخدام WAL mode لتحسين الأداء
        return conn
    
    def init_database(self):
        """إنشاء الجداول"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # جدول الصفقات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                group_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                comment TEXT UNIQUE NOT NULL,
                payment_tx_hash TEXT,
                withdraw_tx_hash TEXT,
                withdraw_address TEXT,
                withdraw_memo TEXT,
                buyer_screenshot TEXT,
                seller_screenshot TEXT,
                pinned_message_id INTEGER,
                mediator_id INTEGER,
                buyer_address TEXT
            )
        """)
        
        # إضافة عمود buyer_address إذا لم يكن موجوداً (للجداول القديمة)
        try:
            cursor.execute("ALTER TABLE deals ADD COLUMN buyer_address TEXT")
            logger.info("✅ Added buyer_address column to deals table")
        except sqlite3.OperationalError:
            # العمود موجود بالفعل
            pass
        
        # جدول السجلات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id INTEGER,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (deal_id) REFERENCES deals(deal_id)
            )
        """)
        
        # جدول الوسطاء
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mediators (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # جدول المعاملات المالية (إيداع/سحب)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_type TEXT NOT NULL,
                amount REAL NOT NULL,
                tx_hash TEXT,
                user_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                note TEXT
            )
        """)
        
        # جدول المجموعات المصرح بها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # جدول رسائل الصفقات (لحفظ جميع الرسائل أثناء الصفقة)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deal_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                message_type TEXT NOT NULL,
                message_text TEXT,
                file_id TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (deal_id) REFERENCES deals(deal_id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # تنظيف البيانات الخاطئة في pinned_message_id
        self.cleanup_invalid_pinned_messages()
    
    def cleanup_invalid_pinned_messages(self):
        """تنظيف القيم الخاطئة في pinned_message_id (file_id بدلاً من message_id)"""
        try:
            logger.info("🧹 Checking for invalid pinned_message_id entries...")
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # البحث عن القيم غير الصحيحة (file_id طويل بدلاً من integer)
            cursor.execute("""
                SELECT deal_id, pinned_message_id FROM deals 
                WHERE pinned_message_id IS NOT NULL 
                AND LENGTH(CAST(pinned_message_id AS TEXT)) > 20
            """)
            
            invalid_rows = cursor.fetchall()
            
            if invalid_rows:
                logger.warning(f"🧹 Found {len(invalid_rows)} deals with invalid pinned_message_id")
                for deal_id, pinned_id in invalid_rows[:3]:  # عرض أول 3 فقط
                    logger.warning(f"   - Deal {deal_id}: {str(pinned_id)[:50]}...")
                
                # تعيين NULL للقيم الخاطئة
                cursor.execute("""
                    UPDATE deals 
                    SET pinned_message_id = NULL 
                    WHERE LENGTH(CAST(pinned_message_id AS TEXT)) > 20
                """)
                
                conn.commit()
                logger.info(f"✅ Cleaned up {len(invalid_rows)} invalid pinned_message_id entries")
            else:
                logger.info("✅ No invalid pinned_message_id entries found")
            
            conn.close()
        except Exception as e:
            logger.error(f"❌ Error cleaning up pinned_message_id: {e}")
    
    def create_deal(self, deal: Deal) -> bool:
        """إنشاء صفقة جديدة"""
        try:
            conn = self.get_connection()
            with conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO deals VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    deal.deal_id, deal.group_id, deal.buyer_id, deal.seller_id,
                    deal.amount, deal.description, deal.status, deal.created_at,
                    deal.updated_at, deal.comment, deal.payment_tx_hash,
                    deal.withdraw_tx_hash, deal.withdraw_address, deal.withdraw_memo,
                    deal.buyer_screenshot, deal.seller_screenshot, 
                    deal.pinned_message_id, deal.mediator_id, deal.buyer_address
                ))
            
            conn.close()
            
            # تسجيل العملية بعد إغلاق الاتصال
            self.log_action(deal.deal_id, "CREATED", None, f"Amount: {deal.amount} TON")
            
            return True
        except Exception as e:
            logger.error(f"Error creating deal: {e}")
            return False
    
    def update_deal(self, deal_id: str, **kwargs) -> bool:
        """تحديث صفقة"""
        try:
            conn = self.get_connection()
            
            kwargs['updated_at'] = datetime.now().isoformat()
            
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [deal_id]
            
            with conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    UPDATE deals SET {set_clause} WHERE deal_id = ?
                """, values)
            
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating deal: {e}")
            return False
    
    def get_deal(self, deal_id: str) -> Optional[Deal]:
        """استرجاع صفقة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Deal(*row)
        return None
    
    def get_deal_by_comment(self, comment: str) -> Optional[Deal]:
        """استرجاع صفقة عبر الكومنت"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM deals WHERE comment = ?", (comment,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Deal(*row)
        return None
    
    def get_active_deals(self, group_id: int) -> List[Deal]:
        """استرجاع الصفقات النشطة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM deals 
            WHERE group_id = ? AND status NOT IN ('COMPLETED', 'CANCELLED')
            ORDER BY created_at DESC
        """, (group_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [Deal(*row) for row in rows]
    
    def log_action(self, deal_id: str, action: str, user_id: Optional[int], details: str = ""):
        """تسجيل إجراء"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self.get_connection()
                with conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO deal_logs (deal_id, action, user_id, timestamp, details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (deal_id, action, user_id, datetime.now().isoformat(), details))
                    
                conn.close()
                return  # نجحت العملية
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    import time
                    time.sleep(0.1 * (attempt + 1))  # انتظر قليلاً ثم حاول مرة أخرى
                    continue
                logger.error(f"Error logging action (attempt {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                logger.error(f"Error logging action: {e}")
                break
    
    def save_deal_message(self, deal_id: str, user_id: int, username: str, 
                         message_type: str, message_text: str = None, file_id: str = None) -> bool:
        """حفظ رسالة من الصفقة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO deal_messages 
                (deal_id, user_id, username, message_type, message_text, file_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (deal_id, user_id, username, message_type, message_text, file_id, 
                  datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving deal message: {e}")
            return False
    
    def get_deal_messages(self, deal_id: str) -> list:
        """جلب جميع رسائل الصفقة"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, username, message_type, message_text, file_id, timestamp
                FROM deal_messages
                WHERE deal_id = ?
                ORDER BY timestamp ASC
            """, (deal_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'user_id': row[0],
                    'username': row[1],
                    'message_type': row[2],
                    'message_text': row[3],
                    'file_id': row[4],
                    'timestamp': row[5]
                })
            
            conn.close()
            return messages
        except Exception as e:
            logger.error(f"Error getting deal messages: {e}")
            return []
    
    def delete_deal_messages(self, deal_id: str) -> bool:
        """حذف جميع رسائل الصفقة (للتنظيف)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM deal_messages WHERE deal_id = ?", (deal_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting deal messages: {e}")
            return False
    
    def add_authorized_group(self, group_id: int, group_name: str, added_by: int) -> bool:
        """إضافة مجموعة مصرح بها"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO authorized_groups 
                (group_id, group_name, added_by, added_at, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (group_id, group_name, added_by, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding authorized group: {e}")
            return False
    
    def remove_authorized_group(self, group_id: int) -> bool:
        """إزالة مجموعة من القائمة المصرح بها"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM authorized_groups WHERE group_id = ?", (group_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error removing authorized group: {e}")
            return False
    
    def is_group_authorized(self, group_id: int) -> bool:
        """التحقق من أن المجموعة مصرح بها"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM authorized_groups 
            WHERE group_id = ? AND is_active = 1
        """, (group_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def get_authorized_groups(self) -> List[Tuple]:
        """الحصول على قائمة المجموعات المصرح بها"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT group_id, group_name, added_at 
            FROM authorized_groups 
            WHERE is_active = 1
            ORDER BY added_at DESC
        """)
        
        groups = cursor.fetchall()
        conn.close()
        
        return groups
    
    def get_deal_logs(self, deal_id: str) -> List[Dict]:
        """استرجاع سجلات الصفقة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT action, user_id, timestamp, details 
            FROM deal_logs WHERE deal_id = ?
            ORDER BY timestamp ASC
        """, (deal_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"action": r[0], "user_id": r[1], "timestamp": r[2], "details": r[3]}
            for r in rows
        ]
    
    def add_mediator(self, user_id: int, username: str, added_by: int) -> bool:
        """إضافة وسيط جديد"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO mediators (user_id, username, added_by, added_at, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (user_id, username, added_by, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Mediator {user_id} added by {added_by}")
            return True
        except Exception as e:
            logger.error(f"Error adding mediator: {e}")
            return False
    
    def remove_mediator(self, user_id: int) -> bool:
        """إزالة وسيط"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE mediators SET is_active = 0 WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Mediator {user_id} removed")
            return True
        except Exception as e:
            logger.error(f"Error removing mediator: {e}")
            return False
    
    def get_active_mediators(self) -> List[Dict]:
        """الحصول على قائمة الوسطاء النشطين"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username FROM mediators 
            WHERE is_active = 1
            ORDER BY added_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"user_id": r[0], "username": r[1]} for r in rows]
    
    def log_wallet_transaction(self, tx_type: str, amount: float, user_id: int, 
                               tx_hash: str = None, note: str = ""):
        """تسجيل معاملة محفظة (إيداع/سحب)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO wallet_transactions (tx_type, amount, tx_hash, user_id, timestamp, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tx_type, amount, tx_hash, user_id, datetime.now().isoformat(), note))
            
            conn.commit()
            conn.close()
            logger.info(f"💰 Wallet {tx_type}: {amount} TON by user {user_id}")
        except Exception as e:
            logger.error(f"Error logging wallet transaction: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔗 TON BLOCKCHAIN INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TONManager:
    """مدير التفاعل مع شبكة TON - يعمل محلياً بدون API"""
    
    def __init__(self, wallet_address: str, api_key: str = None, mnemonic: List[str] = None):
        self.wallet_address = wallet_address
        self.api_key = api_key  # اختياري
        self.mnemonic = mnemonic or WALLET_MNEMONIC
        self.last_check_lt = 0
        self.last_check_hash = None
        self.wallet = None
        self.transactions_cache = []  # كاش للمعاملات
        self._init_wallet()
    
    def _init_wallet(self):
        """تهيئة المحفظة من المفاتيح باستخدام tonsdk"""
        try:
            if not TON_SDK_AVAILABLE:
                logger.error("❌ tonsdk not installed. Install with: pip install tonsdk")
                logger.error("❌ Cannot proceed without tonsdk. Install it: pip install tonsdk requests")
                self.wallet = {
                    'address': self.wallet_address,
                    'mnemonic': self.mnemonic,
                    'balance': 0.0,
                    'ready': False
                }
                return
            
            logger.info("🔄 Initializing TON wallet with tonsdk...")
            logger.info(f"📍 Wallet address: {self.wallet_address}")
            logger.info(f"🔑 Mnemonic: {'✓ Loaded (' + str(len(self.mnemonic)) + ' words)' if self.mnemonic else '✗ Not Set'}")
            
            # إنشاء المحفظة من المفاتيح
            mnemonics_list = self.mnemonic
            _mnemonics, _pub_k, _priv_k, wallet_obj = Wallets.from_mnemonics(
                mnemonics=mnemonics_list,
                version=WalletVersionEnum.v4r2,
                workchain=0
            )
            self.wallet_obj = wallet_obj
            
            # إعداد API endpoint
            self.api_endpoint = 'https://toncenter.com/api/v2/'
            self.api_headers = {}
            if self.api_key and self.api_key != 'your_api_key_here':
                self.api_headers['X-API-Key'] = self.api_key
            
            # تهيئة المحفظة
            self.wallet = {
                'address': self.wallet_address,
                'mnemonic': self.mnemonic,
                'balance': 0.0,
                'ready': True
            }
            
            logger.info("✅ Wallet initialized successfully with REAL TON SDK (tonsdk)")
            logger.info("💡 Using tonsdk + TON API for blockchain interaction")
            
        except Exception as e:
            logger.error(f"❌ Error initializing wallet: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("❌ Wallet initialization failed - Manual operations required")
            self.wallet = {
                'address': self.wallet_address,
                'mnemonic': self.mnemonic,
                'balance': 0.0,
                'ready': False
            }
    
    async def get_balance(self) -> float:
        """الحصول على رصيد المحفظة الحقيقي من blockchain"""
        try:
            if not self.wallet or not self.wallet.get('ready'):
                logger.error("❌ Wallet not ready - cannot check balance")
                return 0.0
                logger.warning(f"⚠️ SIMULATION MODE - Balance: {balance} TON")
                return balance
            
            # استخدام TON API للحصول على الرصيد الحقيقي
            logger.info("🔍 Fetching real balance from TON blockchain...")
            
            try:
                # الحصول على معلومات الحساب عبر API
                url = f"{self.api_endpoint}getAddressInformation"
                params = {'address': self.wallet_address}
                
                response = requests.get(url, params=params, headers=self.api_headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('ok') and 'result' in data:
                        result = data['result']
                        balance_nano = int(result.get('balance', 0))
                        balance = balance_nano / 1e9
                        
                        logger.info(f"✅ Real balance fetched: {balance} TON")
                        self.wallet['balance'] = balance
                        
                        return balance
                    else:
                        logger.warning(f"⚠️ API returned error: {data.get('error', 'Unknown')}")
                        return 0.0
                else:
                    logger.error(f"❌ HTTP Error {response.status_code}")
                    return self.wallet.get('balance', 0.0)
                    
            except Exception as api_error:
                logger.error(f"❌ API Error: {api_error}")
                logger.warning("⚠️ Falling back to cached balance")
                return self.wallet.get('balance', 0.0)
                
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0.0
    
    async def check_payment(self, deal_id: str, amount: float, comment: str) -> Optional[Dict]:
        """
        التحقق من وصول الدفع - يستخدم pytonlib للتحقق الحقيقي من المعاملات
        Returns: معلومات المعاملة أو Dict مع 'insufficient' إذا كان المبلغ ناقص
        """
        try:
            if not self.wallet:
                return None
            
            # متغير لتتبع المعاملات الناقصة
            insufficient_payments = []
            
            # استخدام TON API للتحقق من blockchain فقط
            logger.info(f"🔍 Checking real blockchain transactions for deal {deal_id}...")
            
            try:
                # الحصول على المعاملات الأخيرة عبر API
                url = f"{self.api_endpoint}getTransactions"
                params = {
                    'address': self.wallet_address,
                    'limit': 100
                }
                
                response = requests.get(url, params=params, headers=self.api_headers, timeout=15)
                
                if response.status_code != 200:
                    logger.error(f"❌ HTTP Error {response.status_code}")
                    return None
                
                data = response.json()
                
                if not data.get('ok'):
                    logger.error(f"❌ API Error: {data.get('error', 'Unknown')}")
                    return None
                
                transactions = data.get('result', [])
                logger.info(f"📊 Found {len(transactions)} recent transactions")
                
                # طباعة تفاصيل المعاملات للتشخيص
                logger.info(f"🔍 Searching for deal_id: '{deal_id}'")
                
                current_time = int(time.time())
                amount_tolerance = 0.01  # هامش 0.01 TON
                
                for tx in transactions:
                    try:
                        # التحقق من أن المعاملة واردة (in_msg)
                        in_msg = tx.get('in_msg')
                        if not in_msg:
                            continue
                        
                        # الحصول على المبلغ (من nanoton)
                        tx_value = int(in_msg.get('value', 0)) / 1e9
                        
                        # تخطي المعاملات الصفرية
                        if tx_value == 0:
                            continue
                        
                        # الحصول على رسالة المعاملة
                        msg_data = in_msg.get('message', '')
                        if isinstance(msg_data, dict):
                            msg_data = str(msg_data)
                        
                        # طباعة تفاصيل كل معاملة واردة
                        if tx_value > 0:
                            logger.info(f"  📨 TX #{transactions.index(tx)}: {tx_value} TON, msg='{msg_data[:100] if msg_data else '(empty)'}'")
                        
                        # logging للتشخيص
                        logger.debug(f"🔍 Checking TX: amount={tx_value}, msg='{msg_data[:50]}...', looking_for='{deal_id}'")
                        
                        # التحقق من التوقيت (آخر 24 ساعة)
                        tx_time = int(tx.get('utime', 0))
                        time_diff = current_time - tx_time
                        
                        if time_diff > 86400:  # أكثر من 24 ساعة
                            logger.debug(f"  ⏰ TX too old: {time_diff}s > 86400s")
                            continue
                        
                        # التحقق من أن deal_id موجود في الرسالة
                        if deal_id not in msg_data:
                            logger.debug(f"  📝 Deal ID not in message")
                            continue
                        
                        logger.info(f"✅ Found transaction with deal_id! Amount: {tx_value} TON")
                        
                        # التحقق من المبلغ
                        if tx_value < (amount - amount_tolerance):
                            logger.warning(f"⚠️ Transaction amount too small: {tx_value} < {amount}")
                            # حفظ المعاملة الناقصة
                            insufficient_payments.append({
                                'amount': tx_value,
                                'required': amount,
                                'tx_hash': tx.get('transaction_id', {}).get('hash', tx.get('hash', '')),
                                'timestamp': tx_time
                            })
                            continue
                        
                        # التحقق من أن المعاملة لم تستخدم من قبل
                        tx_hash = tx.get('transaction_id', {}).get('hash', '')
                        if not tx_hash:
                            tx_hash = tx.get('hash', '')
                        
                        # تحقق من الكاش
                        if tx_hash in self.transactions_cache:
                            continue
                        
                        # معاملة صالحة!
                        self.transactions_cache.append(tx_hash)
                        
                        # استخراج عنوان المرسل (المشتري)
                        source_address = None
                        try:
                            # محاولة الحصول على عنوان المرسل من in_msg
                            source_address = in_msg.get('source', '')
                            if not source_address:
                                # محاولة بديلة
                                source_address = in_msg.get('from', '')
                            logger.info(f"   📍 Source Address: {source_address}")
                        except Exception as addr_error:
                            logger.warning(f"⚠️ Could not extract source address: {addr_error}")
                        
                        logger.info(f"✅ Real payment found!")
                        logger.info(f"   💰 Amount: {tx_value} TON")
                        logger.info(f"   🆔 Deal: {deal_id}")
                        logger.info(f"   🔗 TX Hash: {tx_hash[:16]}...")
                        
                        return {
                            'tx_hash': tx_hash,
                            'amount': tx_value,
                            'timestamp': tx_time,
                            'deal_id': deal_id,
                            'comment': msg_data,
                            'source_address': source_address,  # عنوان المشتري
                            'used': False
                        }
                        
                    except Exception as tx_error:
                        logger.error(f"Error processing transaction: {tx_error}")
                        continue
                
                # إذا وجدنا معاملات ناقصة، نرجعها
                if insufficient_payments:
                    logger.warning(f"⚠️ Found {len(insufficient_payments)} insufficient payment(s)")
                    return {
                        'insufficient': True,
                        'payments': insufficient_payments
                    }
                
                logger.info(f"ℹ️ No matching payment found for deal {deal_id}")
                return None
                
            except Exception as api_error:
                logger.error(f"❌ API Error: {api_error}")
                import traceback
                logger.error(traceback.format_exc())
                return None
            
        except Exception as e:
            logger.error(f"Error checking payment: {e}")
            return None
    
    async def send_ton(self, to_address: str, amount: float, memo: Optional[str] = None) -> Optional[str]:
        """
        إرسال TON باستخدام المحفظة المدمجة مع tonsdk
        """
        try:
            if not self.wallet or not self.wallet.get('ready'):
                logger.error("❌ Wallet not initialized")
                return None
            
            logger.info(f"💸 Sending {amount} TON to {to_address}...")
            
            # إرسال TON باستخدام tonsdk فقط - لا محاكاة
            logger.info("🚀 Initiating REAL TON transfer...")
            
            try:
                # الحصول على كائن المحفظة
                if not hasattr(self, 'wallet_obj') or not self.wallet_obj:
                    logger.error("❌ Wallet object not initialized - Cannot send TON")
                    logger.error("❌ Manual transfer required")
                    return None
                
                # الحصول على seqno من API مع retry
                seqno = None
                max_seqno_retries = 3
                
                for seqno_attempt in range(max_seqno_retries):
                    try:
                        # استخدام getWalletInformation للحصول على seqno مباشرة
                        url = f"{self.api_endpoint}getWalletInformation"
                        params = {
                            'address': self.wallet_address
                        }
                        
                        logger.info(f"🔍 Fetching seqno via getWalletInformation (attempt {seqno_attempt + 1}/{max_seqno_retries})...")
                        
                        response = requests.get(url, params=params, headers=self.api_headers, timeout=15)
                        
                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"📊 getWalletInformation Response: {str(data)[:400]}...")
                            
                            if data.get('ok') and 'result' in data:
                                result = data['result']
                                
                                # الحصول على seqno مباشرة
                                seqno = result.get('seqno')
                                
                                if seqno is not None:
                                    logger.info(f"✅ Got seqno from getWalletInformation: {seqno}")
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
                                logger.warning(f"⚠️ getWalletInformation failed: {error_msg}")
                                
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
                            # البحث في @extra أو message_hash
                            tx_hash = result_data.get('message_hash') or result_data.get('@extra')
                        
                        # إذا لم نحصل على hash حقيقي، نولد واحد من BOC
                        if not tx_hash or tx_hash == 'transaction_sent':
                            # توليد hash من BOC data باستخدام cell hash (base64)
                            try:
                                cell_hash = query['message'].hash
                                tx_hash = bytes_to_b64str(cell_hash)
                                logger.warning(f"⚠️ No hash in response, generated from BOC cell: {tx_hash[:16]}...")
                            except Exception as hash_error:
                                # fallback: استخدام sha256 من boc ثم تحويله لـ base64
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
            
            except Exception as send_error:
                logger.error(f"❌ Send error: {send_error}")
                import traceback
                logger.error(traceback.format_exc())
                logger.warning("⚠️ Transfer failed, please check wallet and network")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error sending TON: {e}")
            return None
    
    def validate_address(self, address: str) -> bool:
        """التحقق من صحة عنوان TON"""
        # عنوان TON يبدأ بـ EQ أو UQ ويكون 48 حرف
        pattern = r'^(EQ|UQ)[A-Za-z0-9_-]{46}$'
        is_valid = bool(re.match(pattern, address))
        logger.info(f"🔍 Validating address: {address[:20]}... | Valid: {is_valid} | Length: {len(address)}")
        return is_valid
    


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 💸 PAYMENT HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_quick_payment_button(wallet_address: str, amount: float, comment: str) -> Optional[InlineKeyboardButton]:
    """
    إنشاء زر دفع فوري يفتح محفظة تليجرام مع البيانات جاهزة
    
    Args:
        wallet_address: عنوان محفظة TON
        amount: المبلغ بالـ TON
        comment: الكومنت المطلوب
    
    Returns:
        InlineKeyboardButton أو None في حالة الخطأ
    """
    try:
        if not wallet_address or not isinstance(wallet_address, str):
            return None
        
        amt = max(0.0, float(f"{amount:.8f}"))
        if amt <= 0:
            return None
        
        # تشفير البيانات للـ URL
        addr_encoded = quote(wallet_address)
        comment_encoded = quote(comment)
        
        # تحويل المبلغ إلى nanoTON (1 TON = 1,000,000,000 nanoTON)
        nanoton = int(round(amt * 1_000_000_000))
        
        # إنشاء رابط محفظة تليجرام
        payment_url = f"ton://transfer/{addr_encoded}?amount={nanoton}&text={comment_encoded}"
        
        return InlineKeyboardButton("💸 دفع فوري", url=payment_url)
    except Exception as e:
        logger.error(f"Error creating quick payment button: {e}")
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 AI OPERATIONAL SUPPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AISupport:
    """نظام الذكاء التشغيلي"""
    
    # الكلمات الحساسة (تحويل فوري لبشري)
    SENSITIVE_KEYWORDS = [
        "نصب", "فلوسي", "احتيال", "سرقة", "مش وصل", "بلغ",
        "scam", "fraud", "steal", "stolen", "cheat"
    ]
    
    @staticmethod
    def detect_intent(message: str) -> str:
        """تحديد نية المستخدم"""
        message = message.lower()
        
        # التحقق من الكلمات الحساسة أولاً
        if any(keyword in message for keyword in AISupport.SENSITIVE_KEYWORDS):
            return "EMERGENCY_SUPPORT"
        
        if any(word in message for word in ["حالة", "status", "فين", "where", "وصل"]):
            return "STATUS_CHECK"
        
        if any(word in message for word in ["دفع", "فلوس", "payment", "paid"]):
            return "PAYMENT_CONFIRMATION"
        
        if any(word in message for word in ["تأخير", "delay", "متأخر", "slow"]):
            return "DELAY_COMPLAINT"
        
        if any(word in message for word in ["كومنت", "comment", "نسيت", "forgot"]):
            return "COMMENT_MISSING"
        
        return "GENERAL_INQUIRY"
    
    @staticmethod
    def get_response(status: str, intent: str = "STATUS_CHECK") -> str:
        """الحصول على رد مناسب"""
        
        if intent == "EMERGENCY_SUPPORT":
            return (
                "🚨 <b>تم تحويل طلبك لدعم بشري لمراجعة الحالة فورًا</b>\n\n"
                "سيتم التواصل معك في أقرب وقت."
            )
        
        responses = {
            DealStatus.CREATED.value: (
                "تم إنشاء الصفقة بنجاح ✅\n"
                "في انتظار إضافة التفاصيل."
            ),
            DealStatus.WAITING_PAYMENT.value: (
                "لم يتم استلام المبلغ حتى الآن.\n"
                "يرجى التأكد من إرسال المبلغ مع الكومنت الصحيح الخاص بالصفقة."
            ),
            DealStatus.PAID.value: (
                "تم استلام المبلغ بنجاح ✅\n"
                "الصفقة الآن في انتظار تسليم الطرف الآخر.\n"
                "في حال وجود تأخير يمكنك طلب دعم مباشر."
            ),
            DealStatus.WAITING_DELIVERY.value: (
                "الصفقة في مرحلة التسليم.\n"
                "في انتظار تأكيد البائع."
            ),
            DealStatus.DELIVERED.value: (
                "تم إعلان التسليم من البائع.\n"
                "في انتظار تأكيد الاستلام من المشتري."
            ),
            DealStatus.READY_TO_WITHDRAW.value: (
                "الصفقة جاهزة للسحب."
            ),
            DealStatus.COMPLETED.value: (
                "تمت الصفقة بنجاح ✅\n"
                "شكراً لاستخدام نظام الوساطة."
            ),
            DealStatus.DISPUTE.value: (
                "تم تسجيل نزاع على الصفقة.\n"
                "دعم بشري سيقوم بمراجعة التفاصيل والتواصل مع الطرفين."
            )
        }
        
        return responses.get(status, "حالة غير معروفة.")
    
    @staticmethod
    def format_deal_info(deal: Deal, user_id: int) -> str:
        """تنسيق معلومات الصفقة"""
        role = "مشتري 🛒" if deal.buyer_id == user_id else "بائع 📦"
        
        info = f"📋 <b>معلومات الصفقة</b>\n\n"
        info += f"🆔 رقم الصفقة: <code>{deal.deal_id}</code>\n"
        info += f"👤 دورك: {role}\n"
        info += f"💰 المبلغ: {deal.amount} TON\n"
        info += f"📊 الحالة: {AISupport._translate_status(deal.status)}\n"
        info += f"🕐 آخر تحديث: {AISupport._format_time(deal.updated_at or deal.created_at)}\n"
        
        return info
    
    @staticmethod
    def _translate_status(status: str) -> str:
        """ترجمة الحالة"""
        translations = {
            "CREATED": "تم الإنشاء",
            "WAITING_PAYMENT": "في انتظار الدفع",
            "PAID": "تم الدفع",
            "WAITING_DELIVERY": "في انتظار التسليم",
            "DELIVERED": "تم التسليم",
            "WAITING_RECEIPT": "في انتظار تأكيد الاستلام",
            "READY_TO_WITHDRAW": "جاهز للسحب",
            "COMPLETED": "مكتمل",
            "DISPUTE": "نزاع",
            "CANCELLED": "ملغي"
        }
        return translations.get(status, status)
    
    @staticmethod
    def _format_time(iso_time: str) -> str:
        """تنسيق الوقت"""
        try:
            dt = datetime.fromisoformat(iso_time)
            now = datetime.now()
            diff = now - dt
            
            if diff.seconds < 60:
                return "الآن"
            elif diff.seconds < 3600:
                return f"منذ {diff.seconds // 60} دقيقة"
            elif diff.seconds < 86400:
                return f"منذ {diff.seconds // 3600} ساعة"
            else:
                return f"منذ {diff.days} يوم"
        except:
            return "غير محدد"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎮 ESCROW BOT CORE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EscrowBot:
    """النواة الأساسية لبوت الوساطة"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # تهيئة مدير TON مع المحفظة الكاملة
        mnemonic = WALLET_MNEMONIC if isinstance(WALLET_MNEMONIC, list) else WALLET_MNEMONIC_STRING.split()
        self.ton = TONManager(TON_WALLET_ADDRESS, TON_API_KEY, mnemonic)
        
        self.ai = AISupport()
        
        # عرض معلومات المحفظة
        logger.info("╔════════════════════════════════════════╗")
        logger.info("║     🔐 WALLET INITIALIZED             ║")
        logger.info("╚════════════════════════════════════════╝")
        logger.info(f"📍 Address: {TON_WALLET_ADDRESS[:16]}...")
        logger.info(f"🔑 Mnemonic: {'✓ Loaded' if mnemonic else '✗ Missing'}")
        logger.info("")
    
    # ──────────────────────────────────────────────────────────
    # 🔒 Security & Validation
    # ──────────────────────────────────────────────────────────
    
    async def is_group_admin(self, update: Update, user_id: int) -> bool:
        """التحقق من صلاحيات الإدارة"""
        if user_id in OWNER_IDS or user_id in ADMIN_IDS:
            return True
        
        try:
            chat = update.effective_chat
            member = await chat.get_member(user_id)
            return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
        except:
            return False
    
    def is_group_chat(self, update: Update) -> bool:
        """التحقق من أن المحادثة في جروب (عام أو خاص)"""
        # دعم جميع أنواع الجروبات: group, supergroup, channel
        return update.effective_chat.type in ["group", "supergroup", "channel"]
    
    async def is_authorized_in_deal(self, user_id: int, update: Update) -> bool:
        """التحقق من أن المستخدم مصرح له بالتفاعل (بائع/مشتري/مالك/وسيط)"""
        # التحقق من المالكين
        if user_id in OWNER_IDS:
            return True
        
        # التحقق من الوسطاء
        if user_id in ADMIN_IDS:
            return True
        
        # التحقق من أنه مشرف في الجروب
        if await self.is_group_admin(update, user_id):
            return True
        
        # التحقق من الصفقات النشطة
        active_deals = self.db.get_active_deals(update.effective_chat.id)
        for deal in active_deals:
            # إذا كان البائع أو المشتري
            if user_id in [deal.buyer_id, deal.seller_id]:
                return True
            # إذا كان وسيط في نزاع
            if deal.status == DealStatus.DISPUTE.value and deal.mediator_id == user_id:
                return True
        
        return False
    
    def check_group_authorization(self, update: Update) -> bool:
        """التحقق من أن المجموعة مصرح بها"""
        # السماح للرسائل في الخاص
        if not self.is_group_chat(update):
            return True
        
        # السماح للمالكين في كل المجموعات
        user_id = update.effective_user.id if update.effective_user else 0
        if user_id in OWNER_IDS:
            return True
        
        # التحقق من المجموعة
        group_id = update.effective_chat.id
        return self.db.is_group_authorized(group_id)
    
    async def get_user_name_mention(self, user_id: int, context, default_name: str = "المستخدم") -> str:
        """الحصول على اسم المستخدم مع رابط الملف الشخصي"""
        try:
            user = await context.bot.get_chat(user_id)
            # محاولة الحصول على الاسم الأول أو اسم المستخدم
            if user.first_name:
                name = user.first_name
                if user.last_name:
                    name += f" {user.last_name}"
            elif user.username:
                name = f"@{user.username}"
            else:
                name = default_name
            
            return f'<a href="tg://user?id={user_id}">{name}</a>'
        except:
            return f'<a href="tg://user?id={user_id}">{default_name}</a>'
    
    def safe_message_id(self, message_id) -> Optional[int]:
        """تحويل message_id بشكل آمن إلى int"""
        if message_id is None:
            return None
        if isinstance(message_id, int):
            return message_id
        try:
            return int(message_id)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Cannot convert message_id to int: {message_id}")
            return None
    
    def generate_deal_id(self) -> str:
        """توليد معرف صفقة فريد"""
        timestamp = int(time.time() * 1000)
        random_part = hashlib.md5(str(timestamp).encode()).hexdigest()[:6].upper()
        return f"DEAL-{random_part}"
    
    async def cleanup_deal_messages(self, update: Update, deal: Deal, final_message_id: int):
        """حذف جميع رسائل الصفقة ما عدا الرسالة النهائية"""
        try:
            logger.info(f"🧹 Cleaning up messages for deal {deal.deal_id}")
            
            chat_id = deal.group_id
            bot = update.get_bot() if hasattr(update, 'get_bot') else update.message.bot if hasattr(update, 'message') else None
            
            if not bot:
                logger.warning("⚠️ Cannot get bot instance for cleanup")
                return
            
            # التحقق من وجود pinned_message_id وتحويله لـ int
            pinned_msg_id = None
            if deal.pinned_message_id:
                try:
                    pinned_msg_id = int(deal.pinned_message_id)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Invalid pinned_message_id: {deal.pinned_message_id}")
                    pinned_msg_id = None
            
            # حذف الرسالة المثبتة أولاً
            if pinned_msg_id and pinned_msg_id != final_message_id:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=pinned_msg_id)
                    logger.info(f"✅ Deleted pinned message {pinned_msg_id}")
                    
                    # فك التثبيت
                    try:
                        await bot.unpin_chat_message(chat_id=chat_id, message_id=pinned_msg_id)
                    except:
                        pass
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete pinned message: {e}")
            
            # محاولة حذف رسائل البوت المتعلقة بالصفقة
            # نبحث في نطاق 50 رسالة قبل وبعد الرسالة المثبتة
            if pinned_msg_id:
                try:
                    for msg_id in range(pinned_msg_id - 50, pinned_msg_id + 50):
                        if msg_id == final_message_id:  # لا نحذف الرسالة النهائية
                            continue
                        if msg_id <= 0:  # message IDs يجب أن تكون موجبة
                            continue
                        
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            await asyncio.sleep(0.1)  # تجنب rate limiting
                        except Exception:
                            # تجاهل الأخطاء (رسالة غير موجودة أو ليست للبوت)
                            pass
                    
                    logger.info(f"✅ Cleanup completed for deal {deal.deal_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error during message cleanup: {e}")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup deal messages: {e}")
    
    # ──────────────────────────────────────────────────────────
    # 📱 Command Handlers
    # ──────────────────────────────────────────────────────────
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user_id = update.effective_user.id
        is_owner = user_id in OWNER_IDS
        is_admin = user_id in ADMIN_IDS
        
        # السماح للمالكين والوسطاء بالتحدث في الخاص
        if not self.is_group_chat(update):
            if not is_owner and not is_admin:
                await update.message.reply_text(
                    "⚠️ هذا البوت يعمل فقط داخل الجروبات المخصصة للوساطة.\n\n"
                    "💡 للمالكين والوسطاء: يمكنكم استخدام الأوامر الإدارية هنا."
                )
                return
            else:
                # رسالة خاصة للمالكين والوسطاء - عرض أزرار
                welcome_text = "╔══════════════════════╗\n"
                welcome_text += "║  🔐 Waset Panda  & First ai         ║\n"
                welcome_text += "╚══════════════════════╝\n\n"
                
                if is_owner:
                    welcome_text += "👑 <b>مرحباً بك في لوحة تحكم المالك</b>\n\n"
                    welcome_text += "اختر من الأزرار أدناه:"
                    
                    keyboard = [
                        [InlineKeyboardButton("📊 إدارة الوسطاء", callback_data="admin_mediators")],
                        [InlineKeyboardButton("إدارة شاتات الوساطة", callback_data="admin_groups")],
                        [InlineKeyboardButton("💰 إدارة المحفظة", callback_data="admin_wallet")],
                        [InlineKeyboardButton("🔧 أدوات الوساطة", callback_data="admin_tools")]
                    ]
                else:
                    welcome_text += "🔧 <b>مرحباً بك في لوحة الوسيط</b>\n\n"
                    welcome_text += "اختر من الأدوات أدناه:"
                    
                    keyboard = [
                        [InlineKeyboardButton("🔧 أدوات الوساطة", callback_data="admin_tools")]
                    ]
                
                await update.message.reply_text(
                    welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
        
        # التحقق من تفويض المجموعة
        if not self.check_group_authorization(update):
            group_name = update.effective_chat.title
            await update.message.reply_text(
                f"⚠️ <b>هذه المجموعة غير مصرح بها</b>\n\n"
                f"📌 المجموعة: {group_name}\n"
                f"🆔 ID: <code>{update.effective_chat.id}</code>\n\n"
                f"❌ البوت لا يعمل في هذه المجموعة\n"
                f"💡 تواصل مع المالك لإضافتها",
                parse_mode=ParseMode.HTML
            )
            return
        
        welcome_text = (
             "╔═══════════════════╗\n"
             "║       Waset Panda & First Ai       ║\n"
             "╚═══════════════════╝\n\n"
            "🤝 <b>مرحباً في نظام الوساطة المالية</b>\n\n"
            "✅ وسيط آمن للمعاملات\n"
            "✅ عملة مدعومة: TON فقط\n"
            "✅ تحقق تلقائي من الدفع\n"
            "✅ سحب تلقائي بعد التأكيد\n"
            "✅ يدعم الجروبات العامة والخاصة\n\n"
            "⚠️ <b>تحذير هام:</b>\n"
            "❌ أي معاملة خارج الجروب على مسؤوليتك\n"
            "❌ ممنوع التحويل المباشر بين الأطراف\n"
            "❌ ممنوع الاتفاق الخاص\n\n"
            "📌 <b>استخدم الأزرار أدناه:</b>\n\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ بدء صفقة جديدة", callback_data="new_deal")],
            [InlineKeyboardButton("📊 الصفقات النشطة", callback_data="active_deals")],
            [InlineKeyboardButton("ℹ️ كيف يعمل النظام؟", callback_data="how_it_works")],
            [InlineKeyboardButton("🤖 تعليمات الذكاء الاصطناعي", callback_data="ai_instructions")],
            [InlineKeyboardButton("🚨 الدعم", callback_data="support")]
        ]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأزرار"""
        query = update.callback_query
        
        user_id = update.effective_user.id
        data = query.data
        
        # التحقق من تفويض المجموعة (إلا للأزرار الإدارية)
        admin_callbacks = ['admin_mediators', 'admin_groups', 'admin_wallet', 'admin_tools', 
                          'admin_back', 'add_mediator_start', 'remove_mediator_start',
                          'add_group_start', 'remove_group_start', 'list_groups',
                          'wallet_show_deposit', 'wallet_withdraw_start']
        
        if not any(data.startswith(cb) or data == cb for cb in admin_callbacks):
            if not self.check_group_authorization(update):
                await query.answer("⚠️ هذه المجموعة غير مصرح بها. تواصل مع المالك لإضافتها.", show_alert=True)
                return
        
        # Admin Panel callbacks
        if data == "admin_mediators":
            await query.answer()
            await self.show_admin_mediators_panel(update, context)
        elif data == "admin_groups":
            await query.answer()
            await self.show_admin_groups_panel(update, context)
        elif data == "admin_wallet":
            await query.answer()
            await self.show_admin_wallet_panel(update, context)
        elif data == "admin_tools":
            await query.answer()
            await self.show_admin_tools_panel(update, context)
        elif data == "admin_back":
            await query.answer()
            await self.admin_back_button(update, context)
        elif data == "add_mediator_start":
            await query.answer()
            await self.start_add_mediator(update, context)
        elif data == "remove_mediator_start":
            await query.answer()
            await self.start_remove_mediator(update, context)
        elif data == "add_group_start":
            await query.answer()
            await self.start_add_group(update, context)
        elif data == "remove_group_start":
            await query.answer()
            await self.start_remove_group(update, context)
        elif data == "list_groups":
            await query.answer()
            await self.show_authorized_groups_list(update, context)
        elif data == "wallet_show_deposit":
            await query.answer()
            await self.show_wallet_deposit(update, context)
        elif data == "wallet_withdraw_start":
            await query.answer()
            await self.start_wallet_withdraw(update, context)
        
        # Original callbacks
        elif data == "new_deal":
            await query.answer()
            await self.start_new_deal(update, context)
        elif data == "active_deals":
            await query.answer()
            await self.show_active_deals(update, context)
        elif data == "how_it_works":
            await query.answer()
            await self.show_how_it_works(update, context)
        elif data == "ai_instructions":
            await query.answer()
            await self.show_ai_instructions(update, context)
        elif data == "support":
            await query.answer()
            await self.show_support_info(update, context)
        elif data.startswith("role_"):
            await query.answer()
            await self.select_role(update, context)
        elif data.startswith("confirm_role_"):
            await query.answer()
            await self.confirm_other_party(update, context)
        elif data.startswith("deliver_"):
            await self.mark_delivered(update, context)
        elif data.startswith("confirm_deliver_"):
            await query.answer()
            await self.confirm_delivery_action(update, context)
        elif data.startswith("cancel_deliver_"):
            await query.answer()
            await self.cancel_delivery_action(update, context)
        elif data.startswith("confirm_receipt_"):
            # التحقق من أن المستخدم هو المشتري فقط
            deal_id = data.split("_")[2]
            deal = self.db.get_deal(deal_id)
            if deal and user_id != deal.buyer_id:
                await query.answer("❌ هذا الزر للمشتري فقط", show_alert=True)
                return
            await query.answer()
            await self.confirm_receipt(update, context)
        elif data.startswith("reject_receipt_"):
            # التحقق من أن المستخدم هو المشتري فقط
            deal_id = data.split("_")[2]
            deal = self.db.get_deal(deal_id)
            if deal and user_id != deal.buyer_id:
                await query.answer("❌ هذا الزر للمشتري فقط", show_alert=True)
                return
            await query.answer()
            await self.reject_receipt(update, context)
        elif data.startswith("dispute_"):
            # التحقق من أن المستخدم هو البائع أو المشتري
            deal_id = data.split("_")[1]
            deal = self.db.get_deal(deal_id)
            
            if not deal:
                await query.answer("❌ الصفقة غير موجودة", show_alert=True)
                return
            
            # التحقق من حالة الصفقة - منع فتح نزاع على صفقة منتهية
            if deal.status in [DealStatus.COMPLETED.value, DealStatus.CANCELLED.value]:
                await query.answer("⚠️ هذه الصفقة منتهية. لا يمكن فتح نزاع.", show_alert=True)
                return
            
            if user_id not in [deal.buyer_id, deal.seller_id]:
                await query.answer("❌ هذا الزر للبائع والمشتري فقط", show_alert=True)
                return
            await self.open_dispute(update, context)
        elif data.startswith("take_dispute_"):
            # التحقق من أن المستخدم من الوسطاء أو المالكين
            if user_id not in OWNER_IDS and user_id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر للوسطاء والمالكين فقط", show_alert=True)
                return
            await query.answer()
            await self.take_dispute(update, context)
        elif data.startswith("show_messages_"):
            # التحقق من أن المستخدم من الوسطاء أو المالكين
            if user_id not in OWNER_IDS and user_id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر للوسطاء والمالكين فقط", show_alert=True)
                return
            await query.answer()
            await self.show_deal_messages(update, context)
        elif data.startswith("recheck_payment_"):
            await query.answer()
            await self.recheck_payment_button(update, context)
        elif data.startswith("confirm_cancel_"):
            await query.answer()
            await self.confirm_cancel_deal(update, context)
        elif data.startswith("abort_cancel_"):
            await query.answer()
            await self.abort_cancel_deal(update, context)
        elif data.startswith("close_deal_"):
            # التحقق من أن المستخدم من الوسطاء أو المالكين
            if user_id not in OWNER_IDS and user_id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر للوسطاء والمالكين فقط", show_alert=True)
                return
            await query.answer()
            await self.close_deal_request(update, context)
        elif data.startswith("confirm_close_deal_"):
            # التحقق من أن المستخدم من الوسطاء أو المالكين
            if user_id not in OWNER_IDS and user_id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر للوسطاء والمالكين فقط", show_alert=True)
                return
            await query.answer()
            await self.confirm_close_deal(update, context)
        elif data.startswith("abort_close_deal_"):
            # التحقق من أن المستخدم من الوسطاء أو المالكين
            if user_id not in OWNER_IDS and user_id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر للوسطاء والمالكين فقط", show_alert=True)
                return
            await query.answer()
            await self.abort_close_deal(update, context)
        elif data.startswith("retry_withdraw_"):
            await query.answer()
            await self.retry_withdrawal(update, context)
    
    # ──────────────────────────────────────────────────────────
    # 📦 Deal Creation Flow
    # ──────────────────────────────────────────────────────────
    
    async def start_new_deal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء صفقة جديدة"""
        query = update.callback_query
        
        text = (
            "📋 <b>إنشاء صفقة جديدة</b>\n\n"
            "اختر دورك في هذه الصفقة:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 مشتري", callback_data="role_buyer")],
            [InlineKeyboardButton("📦 بائع", callback_data="role_seller")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # إعادة تعيين بيانات المستخدم
        context.user_data.clear()
    
    async def select_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اختيار الدور"""
        query = update.callback_query
        role = query.data.split("_")[1]  # buyer or seller
        user_id = update.effective_user.id
        
        # التحقق من أن الرسالة في الجروب
        if not self.is_group_chat(update):
            await query.answer("⚠️ يجب استخدام البوت داخل الجروب فقط", show_alert=True)
            return
        
        message_id = query.message.message_id
        
        # حفظ الدور في bot_data باستخدام message_id كمفتاح
        deal_key = f"pending_deal_{message_id}"
        context.application.bot_data[deal_key] = {
            'creator_id': user_id,
            'creator_role': role,
            'creator_name': update.effective_user.mention_html(),
            'chat_id': update.effective_chat.id
        }
        
        if role == "buyer":
            # المشتري تم تحديده، ننتظر البائع
            text = (
                f"✅ <b>تم تحديد المشتري</b>\n\n"
                f"👤 المشتري: {update.effective_user.mention_html()}\n\n"
                f"📌 الآن على البائع الضغط على الزر أدناه:"
            )
            keyboard = [
                [InlineKeyboardButton("📦 أنا البائع", callback_data=f"confirm_role_seller_{message_id}")]
            ]
        else:
            # البائع تم تحديده، ننتظر المشتري
            text = (
                f"✅ <b>تم تحديد البائع</b>\n\n"
                f"👤 البائع: {update.effective_user.mention_html()}\n\n"
                f"📌 الآن على المشتري الضغط على الزر أدناه:"
            )
            keyboard = [
                [InlineKeyboardButton("🛒 أنا المشتري", callback_data=f"confirm_role_buyer_{message_id}")]
            ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def confirm_other_party(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد الطرف الآخر"""
        query = update.callback_query
        data_parts = query.data.split("_")
        other_role = data_parts[2]  # buyer or seller
        message_id = int(data_parts[3])
        user_id = update.effective_user.id
        
        # الحصول على بيانات مُنشئ الصفقة من bot_data
        deal_key = f"pending_deal_{message_id}"
        pending_deal = context.application.bot_data.get(deal_key)
        
        if not pending_deal:
            await query.answer("❌ الصفقة منتهية الصلاحية. ابدأ صفقة جديدة.", show_alert=True)
            return
        
        creator_id = pending_deal['creator_id']
        creator_role = pending_deal['creator_role']
        creator_name = pending_deal['creator_name']
        
        # التحقق من أن المستخدم ليس نفس الشخص
        if user_id == creator_id:
            await query.answer("❌ لا يمكنك أن تكون الطرفين في نفس الصفقة!", show_alert=True)
            return
        
        # تحديد من هو البائع ومن المشتري
        if creator_role == "buyer":
            # المُنشئ مشتري، الطرف الثاني بائع
            buyer_id = creator_id
            seller_id = user_id
            buyer_name = creator_name
            seller_name = update.effective_user.mention_html()
        else:
            # المُنشئ بائع، الطرف الثاني مشتري
            buyer_id = user_id
            seller_id = creator_id
            buyer_name = update.effective_user.mention_html()
            seller_name = creator_name
        
        # تحديد من سيكتب المبلغ (البائع دائماً)
        seller_will_enter = (user_id == seller_id)
        
        # حفظ البيانات في user_data للبائع فقط
        if seller_will_enter:
            # البائع هو من ضغط الزر، سيكتب المبلغ
            context.user_data['buyer_id'] = buyer_id
            context.user_data['seller_id'] = seller_id
            context.user_data['buyer_name'] = buyer_name
            context.user_data['seller_name'] = seller_name
            context.user_data['waiting_amount_from_seller'] = True
            
            await query.edit_message_text(
                f"✅ <b>تم تحديد الطرفين</b>\n\n"
                f"👤 المشتري: {buyer_name}\n"
                f"👤 البائع: {seller_name}\n\n"
                f"⏳ في انتظار البائع لإدخال المبلغ المطلوب...\n\n"
                ,
                parse_mode=ParseMode.HTML
            )
        else:
            # المشتري ضغط، لكن البائع هو المُنشئ، نحتاج إنشاء إشعار للبائع
            # نحفظ البيانات في bot_data مع معرّف البائع
            seller_key = f"seller_needs_amount_{seller_id}_{message_id}"
            context.application.bot_data[seller_key] = {
                'buyer_id': buyer_id,
                'seller_id': seller_id,
                'buyer_name': buyer_name,
                'seller_name': seller_name,
                'chat_id': update.effective_chat.id
            }
            
            await query.edit_message_text(
                f"✅ <b>تم تحديد الطرفين</b>\n\n"
                f"👤 المشتري: {buyer_name}\n"
                f"👤 البائع: {seller_name}\n\n"
                f"⏳ في انتظار البائع لإدخال المبلغ المطلوب...",
                parse_mode=ParseMode.HTML
            )
            
            # إرسال رسالة خاصة للبائع
            try:
                seller_text = (
                    f"✅ <b>تم تحديد المشتري للصفقة</b>\n\n"
                    f"👤 المشتري: {buyer_name}\n"
                    f"👤 البائع: {seller_name}\n\n"
                    f"💰 <b>أرسل المبلغ المطلوب بالـ TON</b>\n\n"
                    f"<b>مثال:</b>\n"
                    f"<code>10.5</code>\n\n"
                    f"📝 أرسل المبلغ هنا أو في المجموعة"
                )
                await context.bot.send_message(
                    chat_id=seller_id,
                    text=seller_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send message to seller {seller_id}: {e}")
        
        # حذف البيانات المؤقتة من bot_data
        del context.application.bot_data[deal_key]
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية"""
        user_id = update.effective_user.id
        message = update.message
        
        # معالجة إدخالات لوحة التحكم (للمالكين في الخاص)
        if not self.is_group_chat(update):
            # إضافة وسيط
            if context.user_data.get('waiting_mediator_add'):
                text = message.text.strip()
                if text == 'إلغاء':
                    del context.user_data['waiting_mediator_add']
                    await message.reply_text("❌ تم إلغاء العملية")
                    return
                
                try:
                    mediator_id = int(text)
                except:
                    await message.reply_text("❌ User ID غير صحيح. أرسل رقم صحيح أو 'إلغاء'")
                    return
                
                try:
                    user = await context.bot.get_chat(mediator_id)
                    username = user.username or user.first_name or f"User{mediator_id}"
                except:
                    username = f"User{mediator_id}"
                
                if self.db.add_mediator(mediator_id, username, user_id):
                    if mediator_id not in ADMIN_IDS:
                        ADMIN_IDS.append(mediator_id)
                    
                    await message.reply_text(
                        f"✅ <b>تم إضافة الوسيط بنجاح</b>\n\n"
                        f"🆔 ID: <code>{mediator_id}</code>\n"
                        f"👤 الاسم: {username}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.reply_text("❌ حدث خطأ أثناء الإضافة")
                
                del context.user_data['waiting_mediator_add']
                return
            
            # إزالة وسيط
            if context.user_data.get('waiting_mediator_remove'):
                text = message.text.strip()
                if text == 'إلغاء':
                    del context.user_data['waiting_mediator_remove']
                    await message.reply_text("❌ تم إلغاء العملية")
                    return
                
                try:
                    mediator_id = int(text)
                except:
                    await message.reply_text("❌ User ID غير صحيح. أرسل رقم صحيح أو 'إلغاء'")
                    return
                
                if self.db.remove_mediator(mediator_id):
                    if mediator_id in ADMIN_IDS:
                        ADMIN_IDS.remove(mediator_id)
                    
                    await message.reply_text(
                        f"✅ <b>تم إزالة الوسيط بنجاح</b>\n\n"
                        f"🆔 ID: <code>{mediator_id}</code>",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.reply_text("❌ حدث خطأ أثناء الإزالة أو الوسيط غير موجود")
                
                del context.user_data['waiting_mediator_remove']
                return
            
            # إضافة مجموعة
            if context.user_data.get('waiting_group_add'):
                text = message.text.strip()
                if text == 'إلغاء':
                    del context.user_data['waiting_group_add']
                    await message.reply_text("❌ تم إلغاء العملية")
                    return
                
                try:
                    group_id = int(text)
                    if group_id > 0:
                        group_id = -group_id  # Telegram group IDs are negative
                except:
                    await message.reply_text("❌ Group ID غير صحيح. أرسل رقم صحيح أو 'إلغاء'")
                    return
                
                try:
                    chat = await context.bot.get_chat(group_id)
                    group_name = chat.title or f"Group{group_id}"
                except:
                    group_name = f"Group{group_id}"
                
                if self.db.add_authorized_group(group_id, group_name, user_id):
                    await message.reply_text(
                        f"✅ <b>تم إضافة المجموعة بنجاح</b>\n\n"
                        f"🆔 ID: <code>{group_id}</code>\n"
                        f"📌 الاسم: {group_name}\n\n"
                        f"✅ البوت الآن يعمل في هذه المجموعة",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.reply_text("❌ حدث خطأ أثناء الإضافة")
                
                del context.user_data['waiting_group_add']
                return
            
            # إزالة مجموعة
            if context.user_data.get('waiting_group_remove'):
                text = message.text.strip()
                if text == 'إلغاء':
                    del context.user_data['waiting_group_remove']
                    await message.reply_text("❌ تم إلغاء العملية")
                    return
                
                try:
                    group_id = int(text)
                    if group_id > 0:
                        group_id = -group_id  # Telegram group IDs are negative
                except:
                    await message.reply_text("❌ Group ID غير صحيح. أرسل رقم صحيح أو 'إلغاء'")
                    return
                
                if self.db.remove_authorized_group(group_id):
                    await message.reply_text(
                        f"✅ <b>تم إزالة المجموعة بنجاح</b>\n\n"
                        f"🆔 ID: <code>{group_id}</code>\n\n"
                        f"⚠️ البوت لن يعمل في هذه المجموعة بعد الآن",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.reply_text("❌ حدث خطأ أثناء الإزالة أو المجموعة غير موجودة")
                
                del context.user_data['waiting_group_remove']
                return
            
            # سحب من المحفظة
            if context.user_data.get('waiting_wallet_withdraw'):
                text = message.text.strip()
                if text == 'إلغاء':
                    del context.user_data['waiting_wallet_withdraw']
                    await message.reply_text("❌ تم إلغاء العملية")
                    return
                
                parts = text.split()
                if len(parts) != 2:
                    await message.reply_text(
                        "❌ صيغة غير صحيحة\n\n"
                        "<b>الصيغة الصحيحة:</b>\n"
                        "<code>المبلغ العنوان</code>\n\n"
                        "<b>مثال:</b>\n"
                        "<code>10 EQCabc123...</code>",
                        parse_mode=ParseMode.HTML
                    )
                    return
                
                try:
                    amount = float(parts[0])
                    address = parts[1]
                except:
                    await message.reply_text("❌ المبلغ غير صحيح")
                    return
                
                balance = await self.ton.get_balance()
                if amount > balance:
                    await message.reply_text(
                        f"❌ <b>رصيد غير كافٍ</b>\n\n"
                        f"الرصيد الحالي: {balance} TON\n"
                        f"المبلغ المطلوب: {amount} TON",
                        parse_mode=ParseMode.HTML
                    )
                    del context.user_data['waiting_wallet_withdraw']
                    return
                
                tx_hash = await self.ton.send_ton(address, amount)
                
                if tx_hash:
                    self.db.log_wallet_transaction("WITHDRAW", amount, user_id, tx_hash, 
                                                  f"Owner withdrawal to {address[:16]}...")
                    
                    await message.reply_text(
                        f"✅ <b>تم السحب بنجاح</b>\n\n"
                        f"💰 المبلغ: {amount} TON\n"
                        f"📤 إلى: <code>{address}</code>\n"
                        f"🔗 TX: <code>{tx_hash}</code>",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await message.reply_text("❌ فشل السحب")
                
                del context.user_data['waiting_wallet_withdraw']
                return
            
            # معالجة عنوان المشتري لإرجاع المبلغ عند إغلاق الصفقة
            if context.user_data.get('waiting_for') == 'buyer_refund_address':
                address = message.text.strip()
                deal_id = context.user_data.get('pending_close_deal')
                admin_id = context.user_data.get('pending_close_by')
                
                if not deal_id or not admin_id:
                    await message.reply_text("❌ خطأ في البيانات")
                    return
                
                # الحصول على بيانات الصفقة
                deal = self.db.get_deal(deal_id)
                if not deal:
                    await message.reply_text("❌ الصفقة غير موجودة")
                    return
                
                # التحقق من أن المرسل هو المشتري فعلاً
                if user_id != deal.buyer_id:
                    await message.reply_text(
                        "❌ <b>غير مصرح</b>\n\n"
                        "⚠️ يجب أن يرسل المشتري عنوان محفظته بنفسه\n"
                        f"👤 المشتري: {await self.get_user_name_mention(deal.buyer_id, context)}",
                        parse_mode=ParseMode.HTML
                    )
                    return
                
                # التحقق من صحة العنوان
                if not self.ton.validate_address(address):
                    await message.reply_text(
                        "❌ <b>عنوان محفظة غير صحيح</b>\n\n"
                        "يرجى إرسال عنوان محفظة TON صحيح",
                        parse_mode=ParseMode.HTML
                    )
                    return
                
                self.db.update_deal(deal_id, buyer_address=address)
                
                # محاولة إرجاع المبلغ
                await message.reply_text(
                    f"✅ <b>تم استلام العنوان</b>\n\n"
                    f"⏳ جاري إرجاع المبلغ...",
                    parse_mode=ParseMode.HTML
                )
                
                try:
                    network_fee = 0.02
                    refund_amount = deal.amount - network_fee
                    
                    refund_tx = await self.ton.send_ton(
                        to_address=address,
                        amount=refund_amount,
                        memo=f"REFUND-{deal_id}"
                    )
                    
                    if refund_tx:
                        self.db.log_action(deal_id, "REFUND_SENT", admin_id, 
                                         f"Refund: {refund_amount} TON, TX: {refund_tx}")
                        
                        self.db.update_deal(deal_id, status=DealStatus.CANCELLED.value)
                        self.db.log_action(deal_id, "DEAL_CLOSED_BY_MEDIATOR", admin_id, 
                                          f"Closed with refund by {admin_id}")
                        
                        # تنظيف رسائل الصفقة من قاعدة البيانات
                        self.db.delete_deal_messages(deal_id)
                        logger.info(f"🧹 Cleaned up messages for cancelled deal {deal_id}")
                        
                        tx_link = f"https://tonscan.org/tx/{refund_tx}"
                        await message.reply_text(
                            f"✅ <b>تم إغلاق الصفقة وإرجاع المبلغ</b>\n\n"
                            f"🆔 الصفقة: <code>{deal_id}</code>\n"
                            f"💰 المبلغ المرجع: {refund_amount} TON\n"
                            f"💳 رسوم الشبكة: {network_fee} TON\n"
                            f"📤 إلى: <code>{address}</code>\n"
                            f"<a href='{tx_link}'>رابط المعاملة</a>\n\n"
                            f"✅ تم إغلاق الصفقة بنجاح",
                            parse_mode=ParseMode.HTML
                        )
                        
                        # إشعار في الجروب
                        try:
                            buyer_mention = await self.get_user_name_mention(deal.buyer_id, context)
                            seller_mention = await self.get_user_name_mention(deal.seller_id, context)
                            
                            await context.bot.send_message(
                                chat_id=deal.group_id,
                                text=(
                                    f"🔔 <b>إشعار إغلاق الصفقة</b>\n\n"
                                    f"{buyer_mention} / {seller_mention}\n\n"
                                    f"🚫 تم إغلاق الصفقة <code>{deal_id}</code> من قبل الإدارة\n"
                                    f"💸 تم إرجاع {refund_amount} TON للمشتري\n"
                                    f"🔗 <a href='{tx_link}'>رابط المعاملة</a>"
                                ),
                                parse_mode=ParseMode.HTML,
                                reply_to_message_id=deal.pinned_message_id if deal.pinned_message_id else None
                            )
                        except Exception as e:
                            logger.error(f"Error sending group notification: {e}")
                        
                    else:
                        raise Exception("Transaction failed")
                        
                except Exception as e:
                    logger.error(f"Refund error: {e}")
                    await message.reply_text(
                        f"❌ <b>خطأ في إرجاع المبلغ</b>\n\n"
                        f"⚠️ {str(e)}\n\n"
                        f"يرجى إرجاع المبلغ يدوياً",
                        parse_mode=ParseMode.HTML
                    )
                
                # تنظيف البيانات
                del context.user_data['waiting_for']
                del context.user_data['pending_close_deal']
                del context.user_data['pending_close_by']
                return
            
            # إذا كان في الخاص وليس من المعالجات أعلاه، لا تفعل شيء
            return
        
        # معالجة رسائل الجروب فقط من هنا
        # التحقق من الصلاحيات: البائع، المشتري، الأدمن، أو الوسطاء فقط
        if not await self.is_authorized_in_deal(user_id, update):
            # حذف الرسالة إذا كانت من شخص غير مصرح
            try:
                await message.delete()
            except:
                pass
            return
        
        # حفظ الرسالة في قاعدة البيانات (للصفقات النشطة)
        await self.save_message_to_active_deals(update, context)
        
        # معالجة الصور (الاسكرينات)
        if message.photo:
            await self.handle_screenshot(update, context)
            return
        
        # معالجة النصوص
        if not message.text:
            return
        
        message_text = message.text.strip()
        
        # التحقق من رد المشتري على سؤال الاستلام (نعم/لا)
        buyer_receipt_deal = None
        for key, buyer_id in list(context.application.bot_data.items()):
            if key.startswith('waiting_buyer_receipt_') and buyer_id == user_id:
                buyer_receipt_deal = key.replace('waiting_buyer_receipt_', '')
                break
        
        if buyer_receipt_deal:
            await self.process_buyer_receipt_response(update, context, buyer_receipt_deal, message_text)
            return
        
        # التحقق من إدخال المبلغ من البائع
        if context.user_data.get('waiting_amount_from_seller'):
            await self.process_amount_input(update, context)
            return
        
        # التحقق من البائع الذي يحتاج لإدخال المبلغ (من bot_data)
        seller_pending = None
        for key, data in list(context.application.bot_data.items()):
            if key.startswith(f'seller_needs_amount_{user_id}_'):
                seller_pending = data
                # نقل البيانات إلى user_data
                context.user_data['buyer_id'] = data['buyer_id']
                context.user_data['seller_id'] = data['seller_id']
                context.user_data['buyer_name'] = data['buyer_name']
                context.user_data['seller_name'] = data['seller_name']
                context.user_data['waiting_amount_from_seller'] = True
                # حذف من bot_data
                del context.application.bot_data[key]
                # معالجة المبلغ
                await self.process_amount_input(update, context)
                return
        
        # التحقق من إدخال الوصف
        if context.user_data.get('waiting_description'):
            await self.process_description_input(update, context)
            return
        
        # التحقق من إدخال عنوان السحب
        # البحث في bot_data عن عنوان سحب منتظر للمستخدم الحالي
        waiting_for_withdraw = False
        withdraw_deal_id = None
        for key, expected_seller_id in list(context.application.bot_data.items()):
            if key.startswith('waiting_withdraw_address_'):
                # التحقق من أن المستخدم الحالي هو البائع المتوقع
                if expected_seller_id == user_id:
                    waiting_for_withdraw = True
                    withdraw_deal_id = key.replace('waiting_withdraw_address_', '')
                    logger.info(f"📤 User {user_id} is processing withdrawal for deal {withdraw_deal_id}")
                    break
        
        if waiting_for_withdraw:
            await self.process_withdraw_address(update, context)
            return
        
        # تجاهل الرسائل التي تبدأ أو تنتهي بنقطة (.)
        if message_text.startswith('.') or message_text.endswith('.'):
            return
        
        # الرد التلقائي (AI)
        await self.handle_ai_response(update, context)
    
    async def save_message_to_active_deals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """حفظ الرسالة لجميع الصفقات النشطة التي يشارك فيها المستخدم"""
        user_id = update.effective_user.id
        message = update.message
        
        # الحصول على اسم المستخدم
        username = update.effective_user.first_name or ""
        if update.effective_user.last_name:
            username += f" {update.effective_user.last_name}"
        if not username and update.effective_user.username:
            username = f"@{update.effective_user.username}"
        if not username:
            username = f"User{user_id}"
        
        # البحث عن الصفقات النشطة
        active_deals = self.db.get_active_deals(update.effective_chat.id)
        user_deals = [d for d in active_deals if d.buyer_id == user_id or d.seller_id == user_id]
        
        for deal in user_deals:
            # تحديد نوع الرسالة ومحتواها
            if message.photo:
                message_type = "photo"
                file_id = message.photo[-1].file_id
                message_text = message.caption if message.caption else None
                self.db.save_deal_message(deal.deal_id, user_id, username, message_type, message_text, file_id)
            elif message.document:
                message_type = "document"
                file_id = message.document.file_id
                message_text = message.caption if message.caption else f"File: {message.document.file_name}"
                self.db.save_deal_message(deal.deal_id, user_id, username, message_type, message_text, file_id)
            elif message.video:
                message_type = "video"
                file_id = message.video.file_id
                message_text = message.caption if message.caption else None
                self.db.save_deal_message(deal.deal_id, user_id, username, message_type, message_text, file_id)
            elif message.text:
                message_type = "text"
                message_text = message.text
                self.db.save_deal_message(deal.deal_id, user_id, username, message_type, message_text, None)
    
    async def handle_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الصور (الاسكرينات)"""
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # أعلى جودة
        
        # البحث عن صفقات نشطة للمستخدم
        active_deals = self.db.get_active_deals(update.effective_chat.id)
        user_deals = [
            d for d in active_deals 
            if (d.buyer_id == user_id or d.seller_id == user_id)
            and d.status in [DealStatus.WAITING_PAYMENT.value, DealStatus.PAID.value, DealStatus.WAITING_DELIVERY.value]
        ]
        
        if not user_deals:
            await update.message.reply_text(
                "📸 <b>تم استلام الاسكرين</b>\n\n"
                "⚠️ ملاحظة: الاسكرين للمرجعية فقط ولا يعتمد عليه تلقائياً.",
                parse_mode=ParseMode.HTML
            )
            return
        
        deal = user_deals[0]  # أحدث صفقة
        
        # إعادة قراءة الصفقة من قاعدة البيانات للحصول على أحدث حالة
        deal = self.db.get_deal(deal.deal_id)
        if not deal:
            await update.message.reply_text("❌ لم يتم العثور على الصفقة")
            return
        
        # تحديد نوع الاسكرين
        if user_id == deal.buyer_id and deal.status == DealStatus.WAITING_PAYMENT.value:
            # اسكرين الدفع من المشتري
            self.db.update_deal(deal.deal_id, buyer_screenshot=photo.file_id)
            
            # رسالة انتظار
            checking_msg = await update.message.reply_text(
                f"✅ <b>تم استلام اسكرين الدفع</b>\n\n"
                f"🆔 الصفقة: <code>{deal.deal_id}</code>\n\n"
                f"⏳ <b>جاري التحقق من الدفع تلقائياً...</b>",
                parse_mode=ParseMode.HTML
            )
            
            # التحقق التلقائي من الدفع
            await asyncio.sleep(2)  # انتظار قصير
            payment_info = await self.ton.check_payment(deal.deal_id, deal.amount, deal.comment)
            
            if payment_info:
                # تم العثور على الدفع
                await checking_msg.edit_text(
                    f"✅ <b>تم العثور على الدفع!</b>\n\n"
                    f"🆔 الصفقة: <code>{deal.deal_id}</code>\n"
                    f"💰 المبلغ: {payment_info['amount']} TON\n"
                    f"🔗 TX: <code>{payment_info['hash'][:16]}...</code>\n\n"
                    f"📊 جاري معالجة الصفقة...",
                    parse_mode=ParseMode.HTML
                )
                
                # معالجة تأكيد الدفع
                await self.process_payment_confirmation(context.application, deal.deal_id, payment_info)
            else:
                # لم يتم العثور على الدفع
                keyboard = [
                    [InlineKeyboardButton("🔄 إعادة التحقق", callback_data=f"recheck_payment_{deal.deal_id}")]
                ]
                
                await checking_msg.edit_text(
                    f"⚠️ <b>لم يتم العثور على الدفع بعد</b>\n\n"
                    f"🆔 الصفقة: <code>{deal.deal_id}</code>\n"
                    f"💰 المبلغ المطلوب: {deal.amount} TON\n\n"
                    f"📌 تأكد من:\n"
                    f"  • إرسال المبلغ الصحيح\n"
                    f"  • كتابة الكومنت: <code>{deal.comment}</code>\n"
                    f"  • الإرسال لـ: <code>{TON_WALLET_ADDRESS[:16]}...</code>\n\n"
                    f"يمكنك الضغط على الزر أدناه للتحقق مرة أخرى،\n"
                    f"أو استخدام: <code>/check_payment {deal.deal_id}</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        elif user_id == deal.buyer_id and deal.status in [DealStatus.PAID.value, DealStatus.WAITING_DELIVERY.value]:
            # المشتري يحاول إرسال اسكرين بعد الدفع - غير مطلوب
            await update.message.reply_text(
                f"✅ <b>تم استلام الاسكرين</b>\n\n"
                f"🆔 الصفقة: <code>{deal.deal_id}</code>\n\n"
                f"⚠️ <b>ملاحظة:</b> الاسكرين للمرجعية فقط.\n\n"
                f"📦 في انتظار تسليم المنتج/الخدمة من البائع.",
                parse_mode=ParseMode.HTML
            )
            
        elif user_id == deal.seller_id and deal.status in [DealStatus.PAID.value, DealStatus.WAITING_DELIVERY.value]:
            # اسكرين التسليم من البائع
            self.db.update_deal(deal.deal_id, seller_screenshot=photo.file_id)
            
            # إظهار زر "تم التسليم" للبائع
            keyboard = [
                [InlineKeyboardButton("📦 تم التسليم", callback_data=f"deliver_{deal.deal_id}")]
            ]
            
            # إرسال رسالة تأكيد للبائع
            await update.message.reply_text(
                f"✅ <b>تم استلام اسكرين التسليم</b>\n\n"
                f"🆔 الصفقة: <code>{deal.deal_id}</code>\n\n"
                f"📌 اضغط الزر أدناه لإخطار المشتري بالتسليم\n\n"
                f"⚠️ الاسكرين للمرجعية فقط.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # إرسال إشعار للمشتري أن البائع أرسل اسكرين
            try:
                buyer_mention = await self.get_user_name_mention(deal.buyer_id, context.application)
                await context.bot.send_message(
                    chat_id=deal.group_id,
                    text=(
                        f"🔔 <b>تنبيه للمشتري</b> {buyer_mention}\n\n"
                        f"📸 البائع قام بإرسال اسكرين التسليم.\n\n"
                        f"🔍 يرجى مراجعة الصورة والتأكد من التسليم.\n"
                        f"📦 سيتم إخطارك عندما يؤكد البائع التسليم رسمياً."
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=deal.pinned_message_id
                )
            except Exception as e:
                logger.error(f"Error notifying buyer: {e}")
        
        elif user_id == deal.seller_id and deal.status == DealStatus.WAITING_PAYMENT.value:
            # البائع يحاول إرسال اسكرين في مرحلة الدفع - غير مسموح
            await update.message.reply_text(
                f"✅ <b>تم استلام الاسكرين</b>\n\n"
                f"🆔 الصفقة: <code>{deal.deal_id}</code>\n\n"
                f"⚠️ <b>ملاحظة:</b> الاسكرين للمرجعية فقط.\n\n"
                f"⏳ في انتظار دفع المشتري أولاً...\n"
                f"📦 بعد تأكيد الدفع، ستُطلب منك إرسال اسكرين التسليم.",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "📸 <b>تم استلام الاسكرين</b>\n\n"
                "⚠️ ملاحظة: الاسكرين للمرجعية فقط.",
                parse_mode=ParseMode.HTML
            )
    
    async def process_amount_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال المبلغ من البائع"""
        message = update.message
        text = message.text.strip()
        
        # محاولة تحويل إلى رقم
        try:
            amount = float(text)
            if amount <= 0:
                await message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
                return
        except ValueError:
            await message.reply_text(
                "❌ صيغة غير صحيحة\n\n"
                "أرسل المبلغ بالأرقام فقط\n"
                "مثال: <code>10.5</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        # حفظ المبلغ
        context.user_data['deal_amount'] = amount
        context.user_data['waiting_amount_from_seller'] = False
        context.user_data['waiting_description'] = True
        
        await message.reply_text(
            f"✅ <b>المبلغ: {amount} TON</b>\n\n"
            f"الآن، أرسل وصف مختصر للصفقة\n\n"
            f"<b>مثال:</b>\n"
            f"تصميم لوجو احترافي",
            parse_mode=ParseMode.HTML
        )
    
    async def process_description_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إدخال الوصف"""
        message = update.message
        description = message.text.strip()
        
        if len(description) < 3:
            await message.reply_text("❌ الوصف قصير جداً")
            return
        
        # الآن ننشئ الصفقة
        await self.create_deal_from_data(update, context, description)
    
    async def create_deal_from_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
        """إنشاء الصفقة من البيانات المحفوظة"""
        buyer_id = context.user_data.get('buyer_id')
        seller_id = context.user_data.get('seller_id')
        amount = context.user_data.get('deal_amount')
        
        if not all([buyer_id, seller_id, amount]):
            await update.message.reply_text("❌ حدث خطأ في البيانات")
            context.user_data.clear()
            return
        
        # إنشاء معرف الصفقة
        deal_id = self.generate_deal_id()
        comment = deal_id
        
        # إنشاء كائن الصفقة
        deal = Deal(
            deal_id=deal_id,
            group_id=update.effective_chat.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=amount,
            description=description,
            status=DealStatus.WAITING_PAYMENT.value,
            created_at=datetime.now().isoformat(),
            comment=comment
        )
        
        # حفظ في قاعدة البيانات
        if self.db.create_deal(deal):
            # إنشاء رسالة الصفقة
            deal_message = await self.create_deal_message_new(update, deal)
            
            # تثبيت الرسالة
            try:
                await deal_message.pin()
                # التأكد من أن message_id هو int
                if isinstance(deal_message.message_id, int):
                    self.db.update_deal(deal_id, pinned_message_id=deal_message.message_id)
                    logger.info(f"📌 Pinned message with ID: {deal_message.message_id}")
                else:
                    logger.warning(f"⚠️ Invalid message_id type: {type(deal_message.message_id)}")
            except Exception as e:
                logger.warning(f"⚠️ Could not pin message: {e}")
            
            # مسح بيانات الجلسة
            context.user_data.clear()
        else:
            await update.message.reply_text("❌ حدث خطأ في إنشاء الصفقة")
            context.user_data.clear()
    
    async def process_deal_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة بيانات إنشاء الصفقة"""
        message = update.message
        text = message.text
        
        # تحليل الرسالة: @username amount description
        pattern = r'@(\w+)\s+([\d.]+)\s+(.+)'
        match = re.match(pattern, text)
        
        if not match:
            await message.reply_text(
                "❌ صيغة غير صحيحة\n\n"
                "الصيغة الصحيحة:\n"
                "<code>@username 10.5 وصف الخدمة</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        other_username = match.group(1)
        amount = float(match.group(2))
        description = match.group(3)
        
        # التحقق من المبلغ
        if amount <= 0:
            await message.reply_text("❌ المبلغ يجب أن يكون أكبر من صفر")
            return
        
        # إنشاء الصفقة
        role = context.user_data.get('deal_role')
        deal_id = self.generate_deal_id()
        comment = deal_id
        
        user_id = update.effective_user.id
        
        # تحديد البائع والمشتري
        if role == "buyer":
            buyer_id = user_id
            seller_id = 0  # سيتم تحديثه لاحقاً
        else:
            seller_id = user_id
            buyer_id = 0
        
        # إنشاء كائن الصفقة
        deal = Deal(
            deal_id=deal_id,
            group_id=update.effective_chat.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            amount=amount,
            description=description,
            status=DealStatus.WAITING_PAYMENT.value,
            created_at=datetime.now().isoformat(),
            comment=comment
        )
        
        # حفظ في قاعدة البيانات
        if self.db.create_deal(deal):
            # إنشاء رسالة الصفقة
            deal_message = await self.create_deal_message(update, deal, other_username)
            
            # تثبيت الرسالة
            try:
                await deal_message.pin()
                # التأكد من أن message_id هو int
                if isinstance(deal_message.message_id, int):
                    self.db.update_deal(deal_id, pinned_message_id=deal_message.message_id)
                    logger.info(f"📌 Pinned message with ID: {deal_message.message_id}")
                else:
                    logger.warning(f"⚠️ Invalid message_id type: {type(deal_message.message_id)}")
            except Exception as e:
                logger.warning(f"⚠️ Could not pin message: {e}")
            
            # مسح حالة الإنشاء
            context.user_data.clear()
            
        else:
            await message.reply_text("❌ حدث خطأ في إنشاء الصفقة")
    
    async def create_deal_message_new(self, update: Update, deal: Deal) -> Message:
        """إنشاء رسالة الصفقة الرسمية (نسخة جديدة)"""
        # الحصول على أسماء المستخدمين مع روابط الملفات الشخصية
        bot = update.message.bot if hasattr(update, 'message') and hasattr(update.message, 'bot') else update.get_bot() if hasattr(update, 'get_bot') else None
        
        # الحصول على اسم المشتري الحقيقي
        try:
            buyer_chat = await bot.get_chat(deal.buyer_id)
            buyer_name = buyer_chat.first_name or ""
            if buyer_chat.last_name:
                buyer_name += f" {buyer_chat.last_name}"
            if not buyer_name and buyer_chat.username:
                buyer_name = f"@{buyer_chat.username}"
            if not buyer_name:
                buyer_name = f"User{deal.buyer_id}"
            buyer_mention = f'<a href="tg://user?id={deal.buyer_id}">{buyer_name}</a>'
        except:
            buyer_mention = f'<a href="tg://user?id={deal.buyer_id}">User{deal.buyer_id}</a>'
        
        # الحصول على اسم البائع الحقيقي
        try:
            seller_chat = await bot.get_chat(deal.seller_id)
            seller_name = seller_chat.first_name or ""
            if seller_chat.last_name:
                seller_name += f" {seller_chat.last_name}"
            if not seller_name and seller_chat.username:
                seller_name = f"@{seller_chat.username}"
            if not seller_name:
                seller_name = f"User{deal.seller_id}"
            seller_mention = f'<a href="tg://user?id={deal.seller_id}">{seller_name}</a>'
        except:
            seller_mention = f'<a href="tg://user?id={deal.seller_id}">User{deal.seller_id}</a>'
        
        text = (
            "╔═══════════════╗\n"
            "                            📄 صفقة جديدة \n"
            "╚═══════════════╝\n\n"
            f"🆔 <b>Deal ID:</b> <code>{deal.deal_id}</code>\n\n"
            f"👤 المشتري: {buyer_mention}\n"
            f"👤 البائع: {seller_mention}\n"
            f"💰 <b>المبلغ:</b> {deal.amount} TON\n"
            f"📝 <b>الوصف:</b> {deal.description}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 <b>معلومات الدفع للمشتري:</b>\n"
            f"📤 العنوان:\n<code>{TON_WALLET_ADDRESS}</code>\n\n"
            f"✍️ <b>Comment (إجباري):</b>\n<code>{deal.comment}</code>\n\n"
            "⚠️ <b>تنبيه:</b> أي دفع بدون الكومنت قد يؤدي لتأخير التحقق\n\n"
            f"📊 <b>الحالة:</b> ⏳ في انتظار الدفع من المشتري"
        )
        
        # إنشاء الأزرار
        keyboard = []
        
        # زر الدفع الفوري (فوق زر الدعم)
        quick_pay_btn = build_quick_payment_button(
            wallet_address=TON_WALLET_ADDRESS,
            amount=deal.amount,
            comment=deal.comment
        )
        if quick_pay_btn:
            keyboard.append([quick_pay_btn])
        
        # زر الدعم
        keyboard.append([InlineKeyboardButton("🚨 أحتاج دعم", callback_data=f"dispute_{deal.deal_id}")])
        
        return await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def create_deal_message(self, update: Update, deal: Deal, other_username: str) -> Message:
        """إنشاء رسالة الصفقة الرسمية"""
        role = "المشتري" if deal.buyer_id == update.effective_user.id else "البائع"
        
        text = (
            "╔═══════════════╗\n"
            " 📄 صفقة جديدة \n"
            "╚═══════════════╝\n\n"
            f"🆔 <b>Deal ID:</b> <code>{deal.deal_id}</code>\n\n"
            f"👤 {role}: {update.effective_user.mention_html()}\n"
            f"👤 الطرف الآخر: @{other_username}\n"
            f"💰 <b>المبلغ:</b> {deal.amount} TON\n"
            f"📝 <b>الوصف:</b> {deal.description}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔐 <b>معلومات الدفع:</b>\n"
            f"📤 العنوان:\n<code>{TON_WALLET_ADDRESS}</code>\n\n"
            f"✍️ <b>Comment (إجباري):</b>\n<code>{deal.comment}</code>\n\n"
            "⚠️ <b>تنبيه:</b> أي دفع بدون الكومنت قد يؤدي لتأخير التحقق\n\n"
            f"📊 <b>الحالة:</b> ⏳ في انتظار الدفع"
        )
        
        keyboard = [
            [InlineKeyboardButton("🚨 أحتاج دعم", callback_data=f"dispute_{deal.deal_id}")]
        ]
        
        return await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # ──────────────────────────────────────────────────────────
    # 💰 Payment Verification (Background Task)
    # ──────────────────────────────────────────────────────────
    
    async def payment_monitor_job(self, context: ContextTypes.DEFAULT_TYPE):
        """مراقبة الدفعات - تُستدعى دورياً كل 30 ثانية"""
        try:
            logger.info("🔄 ════════════════════════════════════════")
            logger.info("🔄 Payment Monitor: Starting check cycle...")
            
            # الحصول على جميع الصفقات في انتظار الدفع
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT deal_id, amount, comment, created_at FROM deals 
                WHERE status = 'WAITING_PAYMENT'
            """)
            
            pending_deals = cursor.fetchall()
            conn.close()
            
            if not pending_deals:
                logger.info("ℹ️  No pending payments to check.")
                logger.info("🔄 ════════════════════════════════════════")
                return
            
            logger.info(f"💰 Found {len(pending_deals)} pending payment(s)!")
            
            for deal_id, amount, comment, created_at in pending_deals:
                try:
                    logger.info(f"🔍 Checking Deal ID: {deal_id}")
                    logger.info(f"   💵 Expected Amount: {amount} TON")
                    logger.info(f"   📝 Comment: {comment}")
                    
                    # التحقق من الدفع
                    payment_info = await self.ton.check_payment(deal_id, amount, comment)
                    
                    if payment_info:
                        # تم العثور على الدفع
                        logger.info(f"✅✅✅ PAYMENT FOUND for deal {deal_id}!")
                        logger.info(f"   💰 Received: {payment_info.get('amount', 'N/A')} TON")
                        logger.info(f"   🔗 TX Hash: {payment_info.get('tx_hash', 'N/A')[:16]}...")
                        
                        await self.process_payment_confirmation(
                            context.application, deal_id, payment_info
                        )
                        
                        logger.info(f"✅ Payment processed successfully!")
                    else:
                        # لم يتم العثور على الدفع بعد
                        logger.info(f"⏳ No payment detected yet for deal {deal_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Error checking payment for {deal_id}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            logger.info("🔄 Payment Monitor: Check cycle completed.")
            logger.info("🔄 ════════════════════════════════════════")
            
        except Exception as e:
            logger.error(f"❌ Critical error in payment monitor job: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def payment_monitor_loop(self, application: Application):
        """حلقة مراقبة الدفعات (خلفية) - DEPRECATED"""
        # هذه الدالة القديمة - تم استبدالها بـ payment_monitor_job
        pass
    
    async def process_payment_confirmation(self, application: Application, 
                                          deal_id: str, payment_info: Dict):
        """معالجة تأكيد الدفع"""
        deal = self.db.get_deal(deal_id)
        if not deal:
            return
        
        # محاولة استخراج عنوان المشتري من المعاملة إن أمكن
        buyer_addr = None
        try:
            # يمكن محاولة الحصول على العنوان من source_address في المعاملة
            if 'source_address' in payment_info:
                buyer_addr = payment_info['source_address']
                logger.info(f"✅ Buyer address extracted from payment: {buyer_addr[:20]}...")
            else:
                logger.warning(f"⚠️ No source_address found in payment_info. Keys: {list(payment_info.keys())}")
        except Exception as e:
            logger.error(f"❌ Error extracting buyer address: {e}")
        
        # تحديث حالة الصفقة مع حفظ عنوان المشتري
        self.db.update_deal(
            deal_id,
            status=DealStatus.PAID.value,
            payment_tx_hash=payment_info['tx_hash'],
            buyer_address=buyer_addr  # حفظ عنوان المشتري
        )
        
        if buyer_addr:
            logger.info(f"💾 Saved buyer address to database: {buyer_addr[:20]}...")
        else:
            logger.warning(f"⚠️ No buyer address saved - will need to request manually if refund needed")
        
        self.db.log_action(deal_id, "PAYMENT_VERIFIED", None, 
                          f"TX: {payment_info['tx_hash']}")
        
        # إنشاء رابط المعاملة على TON blockchain explorer
        tx_hash = payment_info['tx_hash']
        tx_link = f"https://tonscan.org/tx/{tx_hash}"
        
        # إرسال إشعار للطرفين
        notification_text = (
            f"✅ <b>تم استلام المبلغ بنجاح</b>\n\n"
            f"🆔 الصفقة: <code>{deal_id}</code>\n"
            f"💰 المبلغ المطلوب: {deal.amount} TON\n"
            f"💵 المبلغ المستلم: {payment_info['amount']} TON\n"
            f"<a href='{tx_link}'>عرض المعاملة على TON</a>\n\n"
            "📦 الصفقة الآن في انتظار التسليم من البائع.\n\n"
            "👇 <b>للبائع:</b> اضغط زر 'تم التسليم' عند إتمام التسليم"
        )
        
        keyboard = [
            [InlineKeyboardButton("📦 تم التسليم", callback_data=f"deliver_{deal_id}")],
            [InlineKeyboardButton("🚨 أحتاج دعم", callback_data=f"dispute_{deal_id}")]
        ]
        
        # تحديث رسالة الصفقة
        try:
            if deal.pinned_message_id:
                pinned_id = self.safe_message_id(deal.pinned_message_id)
                if pinned_id:
                    await application.bot.edit_message_text(
                        chat_id=deal.group_id,
                        message_id=pinned_id,
                        text=notification_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
        except Exception as e:
            logger.error(f"Error updating deal message: {e}")
        
        # إبلاغ البائع مع منشن
        try:
            seller_mention = await self.get_user_name_mention(deal.seller_id, application)
            tx_link = f"https://tonscan.org/tx/{payment_info['tx_hash']}"
            
            await application.bot.send_message(
                chat_id=deal.group_id,
                text=(
                    f"🔔 <b>تنبيه للبائع</b> {seller_mention}\n\n"
                    f"✅ تم استلام الدفع من المشتري!\n"
                    f"💰 المبلغ المستلم: {payment_info['amount']} TON\n"
                    f"<a href='{tx_link}'>عرض المعاملة على TON Blockchain</a>\n\n"
                    f"📦 <b>المطلوب الآن:</b>\n"
                    f"قم بتسليم المنتج/الخدمة للمشتري\n"
                    f"ثم اضغط زر '📦 تم التسليم' في رسالة الصفقة"
                ),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=deal.pinned_message_id
            )
        except Exception as e:
            logger.error(f"Error notifying seller: {e}")
        
        # طلب الاسكرين من البائع
        try:
            seller_mention = await self.get_user_name_mention(deal.seller_id, application)
            await application.bot.send_message(
                chat_id=deal.group_id,
                text=(
                    f"📸 <b>مطلوب من البائع</b> {seller_mention}\n\n"
                    f"يرجى إرسال اسكرين يوضح عملية التسليم (صورة المنتج/الخدمة المقدمة).\n\n"
                    f"⚠️ <b>ملاحظة:</b> الاسكرين للمرجعية فقط ولا يُعتمد عليه تلقائيًا."
                ),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=deal.pinned_message_id
            )
        except:
            pass
    
    # ──────────────────────────────────────────────────────────
    # 📦 Delivery & Receipt Confirmation
    # ──────────────────────────────────────────────────────────
    
    async def mark_delivered(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد التسليم من البائع"""
        query = update.callback_query
        deal_id = query.data.split("_")[1]
        user_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # التحقق من أن المستخدم هو البائع
        if deal.seller_id != user_id:
            await query.answer("❌ فقط البائع يمكنه تأكيد التسليم", show_alert=True)
            return
        
        # تحديث الحالة إلى تم التسليم
        self.db.update_deal(deal_id, status=DealStatus.DELIVERED.value)
        self.db.log_action(deal_id, "DELIVERY_CONFIRMED", user_id, "Seller confirmed delivery")
        
        await query.answer("✅ تم تسجيل التسليم")
        
        # تحديث الرسالة
        try:
            await query.edit_message_text(
                f"📦 <b>تم إعلان التسليم من البائع</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"👤 البائع أكد التسليم\n\n"
                "⏳ في انتظار تأكيد المشتري...",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        # إرسال رسالة للمشتري مع منشن وأزرار
        buyer_mention = await self.get_user_name_mention(deal.buyer_id, context)
        
        # أزرار تأكيد/رفض الاستلام للمشتري
        buyer_keyboard = [
            [
                InlineKeyboardButton("✅ نعم، استلمت", callback_data=f"confirm_receipt_{deal_id}"),
                InlineKeyboardButton("❌ لم أستلم", callback_data=f"reject_receipt_{deal_id}")
            ]
        ]
        
        try:
            await query.message.reply_text(
                f"🔔 <b>تنبيه للمشتري</b> {buyer_mention}\n\n"
                f"📦 البائع أكد تسليم المنتج/الخدمة\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n\n"
                f"❓ <b>هل استلمت البضاعة من البائع؟</b>\n\n"
                f"✅ اضغط 'نعم، استلمت' إذا وصلك كل شيء بشكل صحيح\n"
                f"❌ اضغط 'لم أستلم' إذا لم تستلم شيئاً بعد\n\n"
                f"💡 <b>يمكنك أيضاً الرد بكلمة:</b>\n"
                f"  • <b>نعم</b> - للتأكيد\n"
                f"  • <b>لا</b> - للرفض",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(buyer_keyboard)
            )
        except Exception as e:
            logger.error(f"Error sending buyer notification: {e}")
        
        # حفظ حالة انتظار رد المشتري
        context.application.bot_data[f'waiting_buyer_receipt_{deal_id}'] = deal.buyer_id
    
    async def confirm_delivery_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد التسليم من البائع بعد السؤال"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        user_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal or deal.seller_id != user_id:
            await query.answer("❌ غير مصرح", show_alert=True)
            return
        
        # تحديث الحالة
        self.db.update_deal(deal_id, status=DealStatus.DELIVERED.value)
        self.db.log_action(deal_id, "DELIVERY_CONFIRMED", user_id, "Seller confirmed delivery")
        
        await query.answer("✅ تم تسجيل التسليم")
        
        # حذف رسالة التأكيد
        try:
            await query.message.delete()
        except:
            pass
        
        # تحديث رسالة الصفقة الرئيسية
        try:
            if deal.pinned_message_id:
                pinned_id = self.safe_message_id(deal.pinned_message_id)
                if pinned_id:
                    text = (
                        f"📦 <b>تم إعلان التسليم من البائع</b>\n\n"
                        f"🆔 الصفقة: <code>{deal_id}</code>\n"
                        f"👤 البائع أكد التسليم\n\n"
                        "⏳ في انتظار تأكيد المشتري..."
                    )
                    
                    await context.bot.edit_message_text(
                        chat_id=deal.group_id,
                        message_id=pinned_id,
                        text=text,
                        parse_mode=ParseMode.HTML
                    )
        except:
            pass
        
        # إرسال رسالة للمشتري مع منشن
        buyer_mention = await self.get_user_name_mention(deal.buyer_id, context)
        
        try:
            await context.bot.send_message(
                chat_id=deal.group_id,
                text=(
                    f"🔔 <b>تنبيه للمشتري</b> {buyer_mention}\n\n"
                    f"📦 البائع أكد تسليم المنتج/الخدمة\n\n"
                    f"❓ <b>هل استلمت البضاعة من البائع؟</b>\n\n"
                    f"✅ للتأكيد: أرسل <b>نعم</b>\n"
                    f"❌ للرفض: أرسل <b>لا</b>\n\n"
                    f"⚠️ يرجى الرد بكلمة 'نعم' أو 'لا' فقط"
                ),
                parse_mode=ParseMode.HTML,
                reply_to_message_id=deal.pinned_message_id
            )
        except:
            pass
        
        # حفظ حالة انتظار رد المشتري
        context.application.bot_data[f'waiting_buyer_receipt_{deal_id}'] = deal.buyer_id
    
    async def cancel_delivery_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء عملية التسليم - البائع لم يسلم بعد"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        
        await query.answer("✅ تم الإلغاء")
        
        try:
            await query.message.edit_text(
                f"❌ <b>تم إلغاء التسليم</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n\n"
                f"قم بالتسليم أولاً ثم اضغط الزر مرة أخرى.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
    
    async def process_buyer_receipt_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                             deal_id: str, response: str):
        """معالجة رد المشتري على سؤال الاستلام"""
        user_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            return
        
        # التحقق من أن المستخدم هو المشتري
        if deal.buyer_id != user_id:
            return
        
        response_lower = response.lower().strip()
        
        # الرد بنعم
        if response_lower in ['نعم', 'yes', 'نعم استلمت', 'استلمت']:
            # حذف حالة الانتظار
            if f'waiting_buyer_receipt_{deal_id}' in context.application.bot_data:
                del context.application.bot_data[f'waiting_buyer_receipt_{deal_id}']
            
            # تحديث الحالة
            self.db.update_deal(deal_id, status=DealStatus.READY_TO_WITHDRAW.value)
            self.db.log_action(deal_id, "RECEIPT_CONFIRMED", user_id, "Buyer confirmed receipt")
            
            await update.message.reply_text(
                f"✅ <b>تم تأكيد الاستلام بنجاح</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n\n"
                f"شكراً لتأكيدك!",
                parse_mode=ParseMode.HTML
            )
            
            # إخطار البائع مع منشن
            seller_mention = await self.get_user_name_mention(deal.seller_id, context)
            
            try:
                await update.message.reply_text(
                    f"🔔 <b>تنبيه للبائع</b> {seller_mention}\n\n"
                    f"✅ المشتري أكد استلام البضاعة بنجاح!\n\n"
                    f"💸 <b>يرجى إرسال عنوان محفظة TON لاستلام المبلغ</b>\n\n"
                    f"<b>الصيغة المقبولة:</b>\n"
                    f"• <code>ADDRESS</code>\n"
                    f"• أو: <code>ADDRESS / MEMO</code>\n\n"
                    f"<b>مثال:</b>\n"
                    f"<code>EQCabc123... / order-7282</code>",
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=deal.pinned_message_id
                )
            except:
                pass
            
            # حفظ حالة انتظار العنوان
            # استخدام bot_data بدلاً من user_data للوصول من أي مكان
            context.application.bot_data[f'waiting_withdraw_address_{deal_id}'] = deal.seller_id
        
        # الرد بلا
        elif response_lower in ['لا', 'no', 'لا لم استلم', 'لم استلم']:
            # حذف حالة الانتظار
            del context.application.bot_data[f'waiting_buyer_receipt_{deal_id}']
            
            await update.message.reply_text(
                f"⚠️ <b>تم رفض الاستلام</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n\n"
                f"سيتم فتح نزاع لمراجعة الحالة...",
                parse_mode=ParseMode.HTML
            )
            
            # فتح نزاع تلقائياً
            self.db.update_deal(deal_id, status=DealStatus.DISPUTE.value)
            self.db.log_action(deal_id, "DISPUTE_OPENED", user_id, "Buyer rejected receipt")
            
            # إشعار الطرفين والإدارة
            dispute_text = (
                f"🚨 <b>تم فتح نزاع</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"📝 السبب: المشتري لم يستلم البضاعة\n\n"
                f"⏳ في انتظار وسيط لمراجعة الحالة"
            )
            
            await update.message.reply_text(dispute_text, parse_mode=ParseMode.HTML)
        
        else:
            # رد غير مفهوم
            await update.message.reply_text(
                f"❓ <b>رد غير واضح</b>\n\n"
                f"يرجى الرد بـ:\n"
                f"✅ <b>نعم</b> - إذا استلمت البضاعة\n"
                f"❌ <b>لا</b> - إذا لم تستلم البضاعة",
                parse_mode=ParseMode.HTML
            )
    
    async def confirm_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد الاستلام من المشتري"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        user_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # التحقق من أن المستخدم هو المشتري
        if deal.buyer_id != user_id:
            await query.answer("❌ فقط المشتري يمكنه تأكيد الاستلام", show_alert=True)
            return
        
        # حذف حالة الانتظار
        if f'waiting_buyer_receipt_{deal_id}' in context.application.bot_data:
            del context.application.bot_data[f'waiting_buyer_receipt_{deal_id}']
        
        # تحديث الحالة إلى جاهز للسحب
        self.db.update_deal(deal_id, status=DealStatus.READY_TO_WITHDRAW.value)
        self.db.log_action(deal_id, "RECEIPT_CONFIRMED", user_id, "Buyer confirmed receipt")
        
        await query.answer("✅ تم تأكيد الاستلام")
        
        # تحديث الرسالة
        await query.edit_message_text(
            f"✅ <b>تم تأكيد الاستلام من المشتري</b>\n\n"
            f"🆔 الصفقة: <code>{deal_id}</code>\n"
            f"💰 المبلغ: {deal.amount} TON\n\n"
            f"🎉 <b>الصفقة اكتملت بنجاح!</b>",
            parse_mode=ParseMode.HTML
        )
        
        # إرسال رسالة للبائع لطلب عنوان السحب
        seller_mention = await self.get_user_name_mention(deal.seller_id, context)
        
        await query.message.reply_text(
            f"🔔 <b>تنبيه للبائع</b> {seller_mention}\n\n"
            f"🎉 تم تأكيد استلام المنتج من المشتري بنجاح!\n\n"
            f"💰 يمكنك الآن سحب {deal.amount} TON\n\n"
            f"📤 <b>لسحب المبلغ، أرسل:</b>\n"
            f"• عنوان محفظتك\n"
            f"• الميمو (اختياري)\n\n"
            f"<b>مثال:</b>\n"
            f"<code>EQAabc...xyz</code>\n"
            f"أو\n"
            f"<code>EQAabc...xyz / memo123</code>\n\n"
            f"⚠️ تأكد من صحة العنوان!",
            parse_mode=ParseMode.HTML
        )
        
        # حفظ حالة انتظار عنوان السحب
        context.application.bot_data[f'waiting_withdraw_address_{deal_id}'] = deal.seller_id
    
    async def reject_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """رفض الاستلام - فتح نزاع"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        
        await self.open_dispute(update, context, auto_trigger=True)
    
    # ──────────────────────────────────────────────────────────
    # 💸 Withdrawal Processing
    # ──────────────────────────────────────────────────────────
    
    async def process_withdraw_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة عنوان السحب"""
        user_id = update.effective_user.id
        logger.info(f"🔍 Processing withdrawal address from user {user_id}")
        
        # البحث عن deal_id من bot_data
        deal_id = None
        for key, expected_user in list(context.application.bot_data.items()):
            if key.startswith('waiting_withdraw_address_') and expected_user == user_id:
                deal_id = key.replace('waiting_withdraw_address_', '')
                logger.info(f"✅ Found deal_id: {deal_id} for user {user_id}")
                break
        
        if not deal_id:
            logger.warning(f"❌ No deal_id found for user {user_id}")
            return
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            logger.error(f"❌ Deal {deal_id} not found in database")
            return
        
        logger.info(f"📋 Deal info: seller_id={deal.seller_id}, buyer_id={deal.buyer_id}, status={deal.status}")
        
        # التحقق من أن المستخدم هو البائع
        if user_id != deal.seller_id:
            logger.warning(f"⚠️ User {user_id} is not the seller (seller_id={deal.seller_id})")
            # تجاهل الرسالة تماماً إذا كانت من المشتري أو أي شخص آخر
            # حذف الرسالة إن أمكن
            try:
                await update.message.delete()
                logger.info(f"🗑️ Deleted message from non-seller user {user_id}")
            except:
                logger.warning(f"⚠️ Could not delete message from user {user_id}")
            return
        
        message_text = update.message.text.strip()
        logger.info(f"📝 Received message: {message_text[:50]}...")
        
        # تحليل العنوان والميمو
        parts = message_text.split("/")
        address = parts[0].strip()
        memo = parts[1].strip() if len(parts) > 1 else None
        
        logger.info(f"📍 Parsed address: {address}")
        logger.info(f"📝 Parsed memo: {memo}")
        
        # التحقق من العنوان
        is_valid = self.ton.validate_address(address)
        logger.info(f"🔍 Address validation result: {is_valid}")
        
        if not is_valid:
            logger.error(f"❌ Invalid address: {address}")
            await update.message.reply_text(
                "❌ <b>عنوان غير صحيح</b>\n\n"
                f"العنوان المرسل: <code>{address}</code>\n\n"
                "✅ تأكد من أن العنوان يبدأ بـ EQ أو UQ ويتكون من 48 حرف\n\n"
                "<b>مثال صحيح:</b>\n"
                "<code>UQAcDae1BvWVAD0TkhnGgDme4b7NH9Fz8JXce-78TW6ekmvN</code>",
                parse_mode=ParseMode.HTML
            )
            return
        
        # التحقق من أنه ليس عنوان النظام
        if address == TON_WALLET_ADDRESS:
            logger.warning(f"⚠️ User tried to use system address")
            await update.message.reply_text(
                "❌ لا يمكن استخدام عنوان النظام"
            )
            return
        
        logger.info(f"✅ Address is valid and not system address")
        
        # حفظ العنوان
        logger.info(f"💾 Saving withdrawal address to database...")
        self.db.update_deal(
            deal_id,
            withdraw_address=address,
            withdraw_memo=memo
        )
        
        self.db.log_action(deal_id, "WITHDRAW_ADDRESS_PROVIDED", 
                          update.effective_user.id, f"Address: {address[:16]}...")
        
        logger.info(f"✅ Address saved successfully")
        
        # تنفيذ السحب
        logger.info(f"🚀 Starting withdrawal execution for deal {deal_id}")
        await self.execute_withdrawal(update, context, deal_id, address, memo)
        
        logger.info(f"✅ Withdrawal execution completed")
        
        # مسح الحالة
        if f'waiting_withdraw_address_{deal_id}' in context.application.bot_data:
            del context.application.bot_data[f'waiting_withdraw_address_{deal_id}']
            logger.info(f"🧹 Cleaned up bot_data for deal {deal_id}")
    
    async def retry_withdrawal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إعادة محاولة السحب بعد فشل سابق"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        user_id = update.effective_user.id
        
        logger.info(f"🔄 Retry withdrawal requested for deal {deal_id} by user {user_id}")
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # التحقق من أن المستخدم هو البائع
        if deal.seller_id != user_id:
            await query.answer("❌ فقط البائع يمكنه إعادة محاولة السحب", show_alert=True)
            return
        
        # التحقق من أن الصفقة في حالة READY_TO_WITHDRAW
        if deal.status != DealStatus.READY_TO_WITHDRAW.value:
            await query.answer("❌ الصفقة ليست جاهزة للسحب", show_alert=True)
            return
        
        # التحقق من وجود عنوان السحب المحفوظ
        if not deal.withdraw_address:
            logger.warning(f"⚠️ No withdraw address found for deal {deal_id}, requesting from seller...")
            
            # حفظ حالة انتظار عنوان السحب
            context.application.bot_data[f'waiting_withdraw_address_{deal_id}'] = deal.seller_id
            
            await query.answer("⚠️ يرجى إرسال عنوان محفظتك مرة أخرى")
            
            # حذف رسالة الخطأ القديمة
            try:
                await query.message.delete()
            except:
                pass
            
            # إرسال رسالة طلب العنوان مباشرة للشات (بدون reply)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=(
                    f"📤 <b>يرجى إرسال عنوان محفظتك للسحب</b>\n\n"
                    f"🆔 الصفقة: <code>{deal_id}</code>\n"
                    f"💰 المبلغ: {deal.amount} TON\n\n"
                    f"📝 <b>أرسل:</b>\n"
                    f"• عنوان محفظتك\n"
                    f"• الميمو (اختياري)\n\n"
                    f"<b>مثال:</b>\n"
                    f"<code>EQAabc...xyz</code>\n"
                    f"أو\n"
                    f"<code>EQAabc...xyz / memo123</code>\n\n"
                    f"⚠️ تأكد من صحة العنوان!"
                ),
                parse_mode=ParseMode.HTML
            )
            return
        
        await query.answer("🔄 جاري إعادة محاولة السحب...")
        
        logger.info(f"✅ Retrying withdrawal with saved address: {deal.withdraw_address}")
        
        # حذف رسالة الخطأ القديمة
        try:
            await query.message.delete()
        except:
            pass
        
        # إنشاء update وهمي للرسالة
        # نحتاج هذا لأن execute_withdrawal يتوقع update من نوع message
        class FakeMessage:
            def __init__(self, bot, chat_id):
                self.bot = bot
                self.chat_id = chat_id
                
            async def reply_text(self, text, **kwargs):
                return await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    **kwargs
                )
        
        class FakeUpdate:
            def __init__(self, message):
                self.message = message
                self.effective_user = query.from_user
                self.effective_chat = query.message.chat
        
        fake_message = FakeMessage(query.message.bot, query.message.chat_id)
        fake_update = FakeUpdate(fake_message)
        
        # إعادة محاولة السحب
        await self.execute_withdrawal(
            fake_update,
            context,
            deal_id,
            deal.withdraw_address,
            deal.withdraw_memo
        )
    
    async def execute_withdrawal(self, update: Update, context: ContextTypes.DEFAULT_TYPE, deal_id: str, withdraw_address: str, withdraw_memo: Optional[str] = None):
        """تنفيذ عملية السحب"""
        logger.info(f"💸 execute_withdrawal called for deal {deal_id}")
        logger.info(f"📤 Withdrawal to: {withdraw_address}")
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            logger.error(f"❌ Deal {deal_id} not found in execute_withdrawal")
            return
        
        logger.info(f"📊 Deal details: amount={deal.amount}")
        
        # حساب المبلغ بعد العمولة ورسوم المعاملة
        fee = deal.amount * (SYSTEM_FEE_PERCENT / 100)
        network_fee = 0.01  # رسوم المعاملة على شبكة TON
        final_amount = deal.amount - fee - network_fee
        
        logger.info(f"💰 Calculated amounts: fee={fee}, network_fee={network_fee}, final={final_amount}")
        
        # التحقق من أن المبلغ النهائي موجب
        if final_amount <= 0:
            logger.error(f"❌ Invalid final amount: {final_amount}")
            await update.message.reply_text(
                "❌ <b>خطأ في حساب المبلغ</b>\n\n"
                "المبلغ بعد خصم الرسوم غير كافٍ.",
                parse_mode=ParseMode.HTML
            )
            return
        
        logger.info(f"⏳ Sending waiting message to user...")
        
        # إرسال رسالة انتظار
        waiting_msg = await update.message.reply_text(
            f"⏳ <b>جاري تنفيذ عملية التحويل...</b>\n\n"
            f"💰 المبلغ الإجمالي: {deal.amount} TON\n"
            f"💸 العمولة ({SYSTEM_FEE_PERCENT}%): {fee:.2f} TON\n"
            f"⛓️ رسوم الشبكة: {network_fee:.2f} TON\n"
            f"💵 المبلغ النهائي: {final_amount:.2f} TON\n\n"
            f"📤 إلى: <code>{withdraw_address}</code>\n\n"
            f"⏳ يرجى الانتظار...",
            parse_mode=ParseMode.HTML
        )
        
        try:
            logger.info(f"🚀 Starting withdrawal for deal {deal_id}")
            logger.info(f"   Amount: {final_amount} TON")
            logger.info(f"   To: {withdraw_address}")
            logger.info(f"   Memo: {withdraw_memo}")
            
            # إرسال TON
            tx_hash = await self.ton.send_ton(
                to_address=withdraw_address,
                amount=final_amount,
                memo=withdraw_memo
            )
            
            logger.info(f"✅ Transfer completed: {tx_hash}")
            
            # حذف رسالة الانتظار
            try:
                await waiting_msg.delete()
            except:
                pass
        except Exception as send_error:
            # حذف رسالة الانتظار في حالة الخطأ
            try:
                await waiting_msg.delete()
            except:
                pass
            
            logger.error(f"❌ Withdrawal failed: {send_error}")
            
            # تحليل نوع الخطأ
            error_message = str(send_error)
            is_seqno_error = "seqno" in error_message.lower() or "exitcode=33" in error_message
            is_balance_error = "insufficient" in error_message.lower() or "not enough" in error_message.lower()
            is_network_error = "connection" in error_message.lower() or "timeout" in error_message.lower()
            
            # إنشاء زر لإعادة المحاولة
            keyboard = [
                [InlineKeyboardButton("🔄 حاول السحب مرة أخرى", callback_data=f"retry_withdraw_{deal_id}")]
            ]
            
            # رسالة مخصصة حسب نوع الخطأ
            if is_seqno_error:
                error_text = (
                    "❌ <b>خطأ في معلومات المحفظة</b>\n\n"
                    "⚠️ المشكلة: لم نتمكن من الحصول على حالة المحفظة الصحيحة.\n\n"
                    "💡 <b>الأسباب المحتملة:</b>\n"
                    "  • المحفظة غير مُفعّلة على الشبكة\n"
                    "  • رصيد المحفظة صفر (يجب أن يكون > 0)\n"
                    "  • مشكلة مؤقتة في TON API\n\n"
                    "🔧 <b>الحل:</b>\n"
                    "  • تأكد من أن المحفظة لديها رصيد\n"
                    "  • انتظر دقيقة ثم حاول مرة أخرى\n\n"
                    "👇 اضغط الزر أدناه لإعادة المحاولة:"
                )
            elif is_balance_error:
                error_text = (
                    "❌ <b>رصيد غير كافٍ</b>\n\n"
                    "⚠️ المشكلة: رصيد محفظة النظام غير كافٍ.\n\n"
                    "💡 يرجى الاتصال بالدعم.\n\n"
                    "👇 أو حاول مرة أخرى:"
                )
            elif is_network_error:
                error_text = (
                    "❌ <b>مشكلة في الاتصال</b>\n\n"
                    "⚠️ المشكلة: فشل الاتصال بشبكة TON.\n\n"
                    "💡 <b>الحل:</b>\n"
                    "  • تحقق من اتصال الإنترنت\n"
                    "  • حاول مرة أخرى بعد قليل\n\n"
                    "👇 اضغط الزر أدناه لإعادة المحاولة:"
                )
            else:
                error_text = (
                    "❌ <b>حدث خطأ في عملية التحويل</b>\n\n"
                    f"⚠️ الخطأ: {error_message[:150]}...\n\n"
                    "💡 <b>الأسباب المحتملة:</b>\n"
                    "  • مشكلة في الاتصال بشبكة TON\n"
                    "  • رصيد المحفظة غير كافٍ\n"
                    "  • خطأ مؤقت في API\n\n"
                    "👇 اضغط الزر أدناه لإعادة المحاولة:"
                )
            
            await update.message.reply_text(
                error_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # عدم تحويل الصفقة لنزاع - فقط الاحتفاظ بحالة READY_TO_WITHDRAW
            # بحيث يمكن إعادة المحاولة
            return
        
        if not tx_hash:
            # فشل التحويل بدون exception
            try:
                await waiting_msg.delete()
            except:
                pass
            
            logger.error(f"❌ Transfer returned None - failed")
            
            # إنشاء زر لإعادة المحاولة
            keyboard = [
                [InlineKeyboardButton("🔄 حاول السحب مرة أخرى", callback_data=f"retry_withdraw_{deal_id}")]
            ]
            
            await update.message.reply_text(
                "❌ <b>فشل التحويل</b>\n\n"
                "⚠️ لم يتم إرسال المعاملة بنجاح.\n\n"
                "💡 <b>الأسباب المحتملة:</b>\n"
                "  • مشكلة في الاتصال بشبكة TON\n"
                "  • رصيد المحفظة غير كافٍ\n"
                "  • Rate limit من API\n\n"
                "👇 اضغط الزر أدناه لإعادة المحاولة:",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        if tx_hash:
            # تحديث الصفقة
            self.db.update_deal(
                deal_id,
                status=DealStatus.COMPLETED.value,
                withdraw_tx_hash=tx_hash
            )
            
            self.db.log_action(deal_id, "WITHDRAWAL_COMPLETED", None, 
                              f"TX: {tx_hash}, Amount: {final_amount} TON")
            
            # تنظيف رسائل الصفقة من قاعدة البيانات
            self.db.delete_deal_messages(deal_id)
            logger.info(f"🧹 Cleaned up messages for completed deal {deal_id}")
            
            # إرسال تأكيد
            completion_text = (

                "✅ تم تنفيذ التحويل \n\n"
                f"🆔 <b>الصفقة:</b> <code>{deal_id}</code>\n"
                f"💰 <b>المبلغ المرسل:</b> {final_amount:.2f} TON\n"
                f"💸 <b>عمولة النظام:</b> {fee:.2f} TON\n"
                f"⛓️ <b>رسوم المعاملة:</b> {network_fee:.2f} TON\n"
                f"📤 <b>إلى:</b> <code>{withdraw_address}</code>\n"
            )
        
            if withdraw_memo:
                completion_text += f"📝 <b>Memo:</b> <code>{withdraw_memo}</code>\n"
            
            # إضافة رابط TONScan
            tx_link = f"https://tonscan.org/tx/{tx_hash}"
            completion_text += (
                f"<a href='{tx_link}'>عرض المعاملة على TON Blockchain</a>\n\n"
                "شكراً لاستخدام نظام\n🔐 Panda & First Ai  للوساطة 🤝"
            )
            
            try:
                # تحديث الرسالة المثبتة بإزالة الأزرار وتحديث الحالة
                if deal.pinned_message_id:
                    try:
                        # تحويل إلى int
                        pinned_msg_id = int(deal.pinned_message_id) if deal.pinned_message_id else None
                        
                        if pinned_msg_id:
                            buyer_mention = await self.get_user_name_mention(deal.buyer_id, context)
                            seller_mention = await self.get_user_name_mention(deal.seller_id, context)
                            
                            await context.bot.edit_message_text(
                                chat_id=deal.group_id,
                                message_id=pinned_msg_id,
                                text=(
                                    f"✅ <b>صفقة ناجحة</b>\n\n"
                                    f"🆔 الصفقة: <code>{deal_id}</code>\n"
                                    f"👤 المشتري: {buyer_mention}\n"
                                    f"👤 البائع: {seller_mention}\n"
                                    f"💰 المبلغ: {deal.amount} TON\n"
                                    f"📝 الوصف: {deal.description}\n\n"
                                    f"💸 المبلغ المحول: {final_amount:.2f} TON\n"
                                    f"📤 إلى: <code>{withdraw_address}</code>\n\n"
                                    f"✅ <b>تمت الصفقة بنجاح</b>\n"
                                    f"<a href='{tx_link}'>عرض المعاملة</a>"
                                ),
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True
                            )
                            # فك التثبيت
                            await context.bot.unpin_chat_message(
                                chat_id=deal.group_id,
                                message_id=pinned_msg_id
                            )
                    except (ValueError, TypeError) as convert_error:
                        logger.warning(f"⚠️ Invalid pinned_message_id format: {deal.pinned_message_id}")
                    except Exception as pin_error:
                        logger.warning(f"⚠️ Could not update/unpin message: {pin_error}")
                
                # إرسال رسالة الإتمام
                final_msg = await update.message.reply_text(
                    completion_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                
                # حذف جميع رسائل الصفقة ما عدا الرسالة النهائية
                try:
                    await self.cleanup_deal_messages(update, deal, final_msg.message_id)
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Cleanup failed (non-critical): {cleanup_error}")
                    
            except Exception as e:
                logger.error(f"Error sending completion message: {e}")
        
        else:
            await update.message.reply_text(
                "❌ <b>حدث خطأ في عملية التحويل</b>\n\n"
                "تم تحويل الصفقة لمراجعة يدوية.",
                parse_mode=ParseMode.HTML
            )
            
            self.db.update_deal(deal_id, status=DealStatus.DISPUTE.value)
    
    # ──────────────────────────────────────────────────────────
    # ⚠️ Dispute Management
    # ──────────────────────────────────────────────────────────
    
    async def open_dispute(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          auto_trigger: bool = False):
        """فتح نزاع"""
        if auto_trigger:
            query = update.callback_query
            deal_id = query.data.split("_")[2]
        else:
            query = update.callback_query
            deal_id = query.data.split("_")[1]
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # منع فتح نزاع للصفقات المكتملة
        if deal.status == DealStatus.COMPLETED.value:
            await query.answer("❌ لا يمكن فتح نزاع لصفقة مكتملة", show_alert=True)
            return
        
        # تحديث الحالة
        self.db.update_deal(deal_id, status=DealStatus.DISPUTE.value)
        self.db.log_action(deal_id, "DISPUTE_OPENED", 
                          update.effective_user.id, "User requested support")
        
        await query.answer("✅ تم فتح النزاع")
        
        # الحصول على قائمة الوسطاء النشطين من قاعدة البيانات
        active_mediators = self.db.get_active_mediators()
        mediator_ids = [m['user_id'] for m in active_mediators]
        
        # إضافة المالكين دائماً
        all_mediators = list(set(OWNER_IDS + mediator_ids))
        
        # الحصول على أسماء الأطراف
        buyer_name = await self.get_user_name_mention(deal.buyer_id, context)
        seller_name = await self.get_user_name_mention(deal.seller_id, context)
        
        # إنشاء رابط للرسالة المثبتة
        message_link = "#"
        if deal.pinned_message_id:
            try:
                # تحويل group_id إلى الصيغة الصحيحة للرابط
                group_id_str = str(deal.group_id)
                if group_id_str.startswith('-100'):
                    clean_id = group_id_str[4:]  # إزالة -100
                else:
                    clean_id = group_id_str.replace('-', '')
                message_link = f"https://t.me/c/{clean_id}/{deal.pinned_message_id}"
            except Exception:
                message_link = "#"
        
        # ترجمة التايم لاين
        logs = self.db.get_deal_logs(deal_id)
        timeline_ar = []
        action_translations = {
            "CREATED": "تم إنشاء الصفقة",
            "PAYMENT_VERIFIED": "تم التحقق من الدفع",
            "DELIVERY_CONFIRMED": "تم تأكيد التسليم",
            "RECEIPT_CONFIRMED": "تم تأكيد الاستلام",
            "WITHDRAW_ADDRESS_PROVIDED": "تم إدخال عنوان السحب",
            "WITHDRAWAL_COMPLETED": "تم إتمام السحب",
            "DISPUTE_OPENED": "تم فتح نزاع"
        }
        
        for log in logs:
            action_ar = action_translations.get(log['action'], log['action'])
            time_ar = self.ai._format_time(log['timestamp'])
            timeline_ar.append(f"• {action_ar} - {time_ar}")
        
        timeline_text = "\n".join(timeline_ar)
        
        # إنشاء منشن لجميع الوسطاء
        mediators_mentions = []
        for med_id in all_mediators:
            try:
                mediator_chat = await context.bot.get_chat(med_id)
                mediator_name = mediator_chat.first_name or ""
                if mediator_chat.last_name:
                    mediator_name += f" {mediator_chat.last_name}"
                if not mediator_name and mediator_chat.username:
                    mediator_name = f"@{mediator_chat.username}"
                if not mediator_name:
                    mediator_name = f"User{med_id}"
                mention = f'<a href="tg://user?id={med_id}">{mediator_name}</a>'
                mediators_mentions.append(mention)
            except:
                mediators_mentions.append(f'<a href="tg://user?id={med_id}">Mediator</a>')
        
        mediators_text = " ".join(mediators_mentions) if mediators_mentions else "الوسطاء"
        
        # إرسال رسالة مفصلة في الجروب فقط
        try:
            keyboard = [
                [InlineKeyboardButton("🧑‍⚖️ سأتولى هذا النزاع", 
                                   callback_data=f"take_dispute_{deal_id}")],
                [InlineKeyboardButton("📋 عرض جميع الرسائل", 
                                   callback_data=f"show_messages_{deal_id}")]
            ]
            
            await context.bot.send_message(
                chat_id=deal.group_id,
                text=(
                    f"🚨 <b>نزاع جديد - يحتاج مراجعة</b>\n\n"
                    f"📢 <b>تنبيه الوسطاء:</b> {mediators_text}\n\n"
                    f"🆔 <b>الصفقة:</b> <code>{deal_id}</code>\n"
                    f"👤 <b>المشتري:</b> {buyer_name}\n"
                    f"👤 <b>البائع:</b> {seller_name}\n"
                    f"💰 <b>المبلغ:</b> {deal.amount} TON\n"
                    f"📝 <b>الوصف:</b> {deal.description}\n"
                    f"📊 <b>الحالة السابقة:</b> {self.ai._translate_status(deal.status)}\n\n"
                    f"⏱ <b>Timeline:</b>\n{timeline_text}\n\n"
                    f"👇 <b>أول وسيط يضغط الزر يتولى القضية</b>"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard),
                reply_to_message_id=deal.pinned_message_id if deal.pinned_message_id else None
            )
        except Exception as e:
            logger.error(f"Error sending dispute message: {e}")
    
    async def take_dispute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تولي نزاع من قبل وسيط"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        mediator_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # المالكين لهم كل الحقوق دائماً
        is_owner = mediator_id in OWNER_IDS
        is_mediator = mediator_id in ADMIN_IDS
        
        # التحقق من الصلاحيات
        if not is_owner and not is_mediator:
            await query.answer("❌ غير مصرح لك", show_alert=True)
            return
        
        # التحقق من عدم تولي وسيط آخر (إلا إذا كان مالك)
        if deal.mediator_id and deal.mediator_id != mediator_id and not is_owner:
            mediator_name = await self.get_user_name_mention(deal.mediator_id, context)
            await query.answer(f"❌ تم تولي القضية من قبل {mediator_name}", show_alert=True)
            return
        
        # تحديث الوسيط
        self.db.update_deal(deal_id, mediator_id=mediator_id)
        self.db.log_action(deal_id, "MEDIATOR_ASSIGNED", mediator_id, 
                          f"Mediator {mediator_id} took the dispute")
        
        mediator_mention = await self.get_user_name_mention(mediator_id, context)
        
        # تحديث رسالة النزاع - إزالة الزر
        try:
            await query.edit_message_text(
                query.message.text + f"\n\n✅ <b>تم التولي بواسطة:</b> {mediator_mention}",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        # جلب معلومات الصفقة الكاملة
        buyer_name = await self.get_user_name_mention(deal.buyer_id, context)
        seller_name = await self.get_user_name_mention(deal.seller_id, context)
        logs = self.db.get_deal_logs(deal_id)
        
        # إنشاء Timeline
        timeline_lines = []
        for log in logs:
            timestamp = datetime.fromisoformat(log['timestamp']).strftime("%H:%M")
            action_translations = {
                'DEAL_CREATED': '✅ تم إنشاء الصفقة',
                'BUYER_CONFIRMED': '✔️ المشتري أكد',
                'SELLER_CONFIRMED': '✔️ البائع أكد',
                'PAYMENT_VERIFIED': '💰 تم التحقق من الدفع',
                'DISPUTE_RAISED': '⚠️ تم رفع نزاع',
                'MEDIATOR_ASSIGNED': '🧑‍⚖️ تم تعيين وسيط',
                'DISPUTE_TAKEN': '🧑‍⚖️ تم تولي النزاع',
                'DEAL_CLOSED': '🚫 تم إغلاق الصفقة',
                'DEAL_COMPLETED': '✅ تم إتمام الصفقة',
            }
            action_ar = action_translations.get(log['action'], log['action'])
            timeline_lines.append(f"• {action_ar} - {timestamp}")
        
        timeline_text = "\n".join(timeline_lines)
        
        # إرسال رسالة جديدة بمعلومات الصفقة والأزرار
        keyboard = [
            [InlineKeyboardButton("📜 عرض جميع الرسائل", callback_data=f"show_messages_{deal_id}")],
            [InlineKeyboardButton("🚫 إغلاق الصفقة", callback_data=f"close_deal_{deal_id}")]
        ]
        
        info_message = (
            f"📋 <b>تفاصيل الصفقة</b> <code>{deal_id}</code>\n\n"
            f"🧑‍⚖️ <b>الوسيط:</b> {mediator_mention}\n"
            f"👤 <b>المشتري:</b> {buyer_name}\n"
            f"👤 <b>البائع:</b> {seller_name}\n"
            f"💰 <b>المبلغ:</b> {deal.amount} TON\n"
            f"📝 <b>الوصف:</b> {deal.description}\n\n"
            f"⏱ <b>Timeline:</b>\n{timeline_text}\n\n"
        )
        
        if deal.payment_tx_hash:
            info_message += f"🔗 <b>TX Hash:</b> <code>{deal.payment_tx_hash[:32]}...</code>\n"
        if deal.buyer_screenshot:
            info_message += f"📸 اسكرين المشتري: متوفر\n"
        if deal.seller_screenshot:
            info_message += f"📸 اسكرين البائع: متوفر\n"
        
        info_message += f"\n✅ <b>تم تولي القضية بنجاح</b>\nيرجى مراجعة التفاصيل واتخاذ القرار المناسب."
        
        await context.bot.send_message(
            chat_id=deal.group_id,
            text=info_message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await query.answer("✅ تم تولي القضية")
    
    async def show_deal_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض جميع رسائل الصفقة للوسطاء والمالكين"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        user_id = update.effective_user.id
        
        # التحقق من الصلاحيات
        if user_id not in OWNER_IDS and user_id not in ADMIN_IDS:
            await query.answer("❌ غير مصرح لك", show_alert=True)
            return
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # جلب جميع الرسائل
        messages = self.db.get_deal_messages(deal_id)
        
        if not messages:
            await query.answer("📭 لا توجد رسائل محفوظة لهذه الصفقة", show_alert=True)
            return
        
        # إرسال رسالة تمهيدية
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"📋 <b>جميع رسائل الصفقة</b> <code>{deal_id}</code>\n\n"
                f"💰 المبلغ: {deal.amount} TON\n"
                f"📊 الحالة: {self.ai._translate_status(deal.status)}\n\n"
                f"📨 عدد الرسائل: {len(messages)}\n"
                f"⏬ جاري إرسال الرسائل بالترتيب...\n"
            ),
            parse_mode=ParseMode.HTML
        )
        
        # إرسال كل رسالة بالترتيب
        for i, msg in enumerate(messages, 1):
            try:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%Y-%m-%d %H:%M")
                header = f"📨 <b>رسالة {i}/{len(messages)}</b>\n👤 <b>المرسل:</b> {msg['username']}\n🕐 <b>الوقت:</b> {timestamp}\n\n"
                
                if msg['message_type'] == 'text':
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=header + f"💬 <b>النص:</b>\n{msg['message_text']}",
                        parse_mode=ParseMode.HTML
                    )
                elif msg['message_type'] == 'photo':
                    caption = header
                    if msg['message_text']:
                        caption += f"📝 <b>الوصف:</b> {msg['message_text']}"
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=msg['file_id'],
                        caption=caption,
                        parse_mode=ParseMode.HTML
                    )
                elif msg['message_type'] == 'document':
                    caption = header + f"📄 <b>ملف:</b> {msg['message_text']}"
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=msg['file_id'],
                        caption=caption,
                        parse_mode=ParseMode.HTML
                    )
                elif msg['message_type'] == 'video':
                    caption = header
                    if msg['message_text']:
                        caption += f"📝 <b>الوصف:</b> {msg['message_text']}"
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=msg['file_id'],
                        caption=caption,
                        parse_mode=ParseMode.HTML
                    )
                
                # انتظار قصير بين الرسائل لتجنب الحظر
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error sending message {i}: {e}")
                continue
        
        # رسالة نهائية
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"✅ <b>تم عرض جميع الرسائل ({len(messages)})</b>",
            parse_mode=ParseMode.HTML
        )
        
        await query.answer("✅ تم إرسال جميع الرسائل")
    
    async def handle_ai_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الاستفسارات بالذكاء الاصطناعي"""
        message_text = update.message.text
        user_id = update.effective_user.id
        
        # اكتشاف النية
        intent = self.ai.detect_intent(message_text)
        
        # التحقق من الكلمات الحساسة
        if intent == "EMERGENCY_SUPPORT":
            response = self.ai.get_response("", intent)
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.HTML
            )
            
            # إرسال إشعار للوسطاء
            alert = (
                f"🚨 <b>تنبيه عاجل</b>\n\n"
                f"👤 المستخدم: {update.effective_user.mention_html()}\n"
                f"💬 الرسالة: {message_text}\n\n"
                f"يرجى التدخل فوراً."
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(admin_id, alert, parse_mode=ParseMode.HTML)
                except:
                    pass
            return
        
        # البحث عن صفقات المستخدم النشطة
        active_deals = self.db.get_active_deals(update.effective_chat.id)
        user_deals = [d for d in active_deals if d.buyer_id == user_id or d.seller_id == user_id]
        
        if user_deals:
            deal = user_deals[0]  # أحدث صفقة
            response = self.ai.get_response(deal.status, intent)
            info = self.ai.format_deal_info(deal, user_id)
            
            await update.message.reply_text(
                f"{response}\n\n{info}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "لا توجد صفقات نشطة حالياً.\n"
                "للمساعدة العامة، اضغط /start",
                parse_mode=ParseMode.HTML
            )
    
    async def recheck_payment_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إعادة التحقق من الدفع عبر الزر"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        if deal.status != DealStatus.WAITING_PAYMENT.value:
            await query.answer("⚠️ الصفقة لم تعد في انتظار الدفع", show_alert=True)
            return
        
        # تحديث الرسالة
        await query.edit_message_text(
            f"⏳ <b>جاري إعادة التحقق من الدفع...</b>\n\n"
            f"🆔 الصفقة: <code>{deal_id}</code>\n"
            f"💰 المبلغ: {deal.amount} TON",
            parse_mode=ParseMode.HTML
        )
        
        # التحقق من الدفع
        payment_info = await self.ton.check_payment(deal_id, deal.amount, deal.comment)
        
        if payment_info:
            # التحقق من وجود معاملات ناقصة
            if payment_info.get('insufficient'):
                insufficient_list = payment_info.get('payments', [])
                payments_text = ""
                for idx, p in enumerate(insufficient_list, 1):
                    payments_text += f"\n  {idx}. دفع {p['amount']} TON (ناقص {p['required'] - p['amount']:.2f} TON)"
                
                keyboard = [
                    [InlineKeyboardButton("🔄 إعادة التحقق", callback_data=f"recheck_payment_{deal_id}")]
                ]
                
                await query.edit_message_text(
                    f"⚠️ <b>تم العثور على دفعات لكن المبلغ ناقص!</b>\n\n"
                    f"🆔 الصفقة: <code>{deal_id}</code>\n"
                    f"💰 المبلغ المطلوب: {deal.amount} TON\n\n"
                    f"📊 الدفعات المستلمة:{payments_text}\n\n"
                    f"❗️ <b>يجب دفع المبلغ كاملاً ({deal.amount} TON)</b>\n\n"
                    f"📌 تأكد من:\n"
                    f"  • إرسال المبلغ الكامل: {deal.amount} TON\n"
                    f"  • كتابة الكومنت: <code>{deal.comment}</code>\n"
                    f"  • الإرسال لـ: <code>{TON_WALLET_ADDRESS[:16]}...</code>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # إنشاء رابط المعاملة على TON blockchain
            tx_hash = payment_info['tx_hash']
            tx_link = f"https://tonscan.org/tx/{tx_hash}"
            
            # تم العثور على الدفع
            await query.edit_message_text(
                f"✅ <b>تم العثور على الدفع!</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"💰 المبلغ المطلوب: {deal.amount} TON\n"
                f"💵 المبلغ المستلم: {payment_info['amount']} TON\n"
                f"<a href='{tx_link}'>عرض المعاملة على TON</a>\n\n"
                f"📊 جاري معالجة الصفقة...",
                parse_mode=ParseMode.HTML
            )
            
            # معالجة تأكيد الدفع
            await self.process_payment_confirmation(context.application, deal_id, payment_info)
        else:
            # لم يتم العثور
            keyboard = [
                [InlineKeyboardButton("🔄 إعادة التحقق", callback_data=f"recheck_payment_{deal_id}")]
            ]
            
            await query.edit_message_text(
                f"❌ <b>لم يتم العثور على الدفع</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"💰 المبلغ المطلوب: {deal.amount} TON\n\n"
                f"📌 تأكد من:\n"
                f"  • إرسال المبلغ الصحيح\n"
                f"  • كتابة الكومنت: <code>{deal.comment}</code>\n"
                f"  • الإرسال لـ: <code>{TON_WALLET_ADDRESS[:16]}...</code>\n\n"
                f"يمكنك المحاولة مرة أخرى أو استخدام:\n"
                f"<code>/check_payment {deal_id}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    # ──────────────────────────────────────────────────────────
    # 🤖 AI Response Handler
    # ──────────────────────────────────────────────────────────
    
    async def handle_ai_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الاستفسارات بالذكاء الاصطناعي"""
        message_text = update.message.text
        user_id = update.effective_user.id
        
        # اكتشاف النية
        intent = self.ai.detect_intent(message_text)
        
        # التحقق من الكلمات الحساسة
        if intent == "EMERGENCY_SUPPORT":
            response = self.ai.get_response("", intent)
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.HTML
            )
            
            # إرسال إشعار للوسطاء
            alert = (
                f"🚨 <b>تنبيه عاجل</b>\n\n"
                f"👤 المستخدم: {update.effective_user.mention_html()}\n"
                f"💬 الرسالة: {message_text}\n\n"
                f"يرجى التدخل فوراً."
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(admin_id, alert, parse_mode=ParseMode.HTML)
                except:
                    pass
            return
        
        # البحث عن صفقات المستخدم النشطة
        active_deals = self.db.get_active_deals(update.effective_chat.id)
        user_deals = [d for d in active_deals if d.buyer_id == user_id or d.seller_id == user_id]
        
        if user_deals:
            deal = user_deals[0]  # أحدث صفقة
            response = self.ai.get_response(deal.status, intent)
            info = self.ai.format_deal_info(deal, user_id)
            
            await update.message.reply_text(
                f"{response}\n\n{info}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "لا توجد صفقات نشطة حالياً.\n"
                "يمكنك بدء صفقة جديدة باستخدام /start"
            )
    
    # ──────────────────────────────────────────────────────────
    # ℹ️ Info Commands
    # ──────────────────────────────────────────────────────────
    
    async def show_active_deals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الصفقات النشطة"""
        query = update.callback_query
        
        active_deals = self.db.get_active_deals(update.effective_chat.id)
        
        if not active_deals:
            await query.edit_message_text(
                "لا توجد صفقات نشطة حالياً."
            )
            return
        
        text = "📊 <b>الصفقات النشطة:</b>\n\n"
        
        for deal in active_deals[:10]:  # أحدث 10 صفقات
            text += (
                f"🆔 <code>{deal.deal_id}</code>\n"
                f"💰 {deal.amount} TON\n"
                f"📊 {self.ai._translate_status(deal.status)}\n"
                f"━━━━━━━━━━━━━━━━\n"
            )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML
        )
    
    async def show_how_it_works(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شرح آلية العمل"""
        query = update.callback_query
        
        text = (
            "📖 <b>كيف يعمل النظام؟</b>\n\n"
            "1️⃣ <b>إنشاء الصفقة</b>\n"
            "   • تحديد الدور (مشتري/بائع)\n"
            "   • إدخال التفاصيل\n\n"
            "2️⃣ <b>الدفع</b>\n"
            "   • المشتري يدفع للمحفظة المحددة\n"
            "   • مع كتابة الكومنت الإجباري\n"
            "   • التحقق تلقائي خلال دقائق\n\n"
            "3️⃣ <b>التسليم</b>\n"
            "   • البائع يؤكد التسليم\n"
            "   • المشتري يقكد الاستلام\n\n"
            "4️⃣ <b>السحب</b>\n"
            "   • البائع يرسل عنوان محفظته\n"
            "   • التحويل تلقائي بعد خصم العمولة\n\n"
            "🔒 <b>الأمان:</b>\n"
            "✅ الأموال محفوظة حتى رضا الطرفين\n"
            "✅ وسيط بشري عند النزاع\n"
            "✅ شفافية كاملة\n\n"
            "🤖 <b>الذكاء الاصطناعي:</b>\n"
            "• البوت يرد على استفساراتك تلقائياً\n"
            "• لتجاهل رد البوت: ضع نقطة (.) قبل أو بعد رسالتك\n"
            "• للمزيد: اضغط على '🤖 تعليمات الذكاء الاصطناعي'\n"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML
        )
    
    async def show_ai_instructions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تعليمات استخدام الذكاء الاصطناعي"""
        query = update.callback_query
        
        text = (
            "🤖 <b>تعليمات الذكاء الاصطناعي (AI)</b>\n\n"
            "💬 <b>كيف يعمل الذكاء الاصطناعي؟</b>\n"
            "البوت يحتوي على مساعد ذكي يرد على استفساراتك في الجروب تلقائياً\n\n"
            "✅ <b>ما يمكن للـ AI مساعدتك فيه:</b>\n"
            "• شرح حالة صفقتك الحالية\n"
            "• الإجابة عن أسئلتك حول الصفقات\n"
            "• توضيح الخطوات التالية\n"
            "• شرح كيفية عمل النظام\n"
            "• مساعدتك في فهم عملية الوساطة\n\n"
            "🕐 <b>متى يرد الـ AI؟</b>\n"
            "البوت يرد تلقائياً على أي رسالة في الجروب من الأطراف المصرح لهم (البائع/المشتري/الوسطاء)\n\n"
            "🚫 <b>كيف تتجاهل رد الـ AI؟</b>\n"
            "لو عايز تبعت رسالة عادية في الجروب والبوت ميردش عليها:\n\n"
            "• ضع نقطة (.) في <b>بداية</b> الرسالة\n"
            "• أو ضع نقطة (.) في <b>نهاية</b> الرسالة\n\n"
            "📝 <b>أمثلة:</b>\n"
            "• <code>.مرحبا كيف الحال</code> → لن يرد البوت\n"
            "• <code>شكرا لك.</code> → لن يرد البوت\n"
            "• <code>متى الدفع؟</code> → سيرد البوت تلقائياً\n\n"
            "💡 <b>نصيحة:</b>\n"
            "استخدم الـ AI للأسئلة المتعلقة بالصفقات فقط. للمحادثات العادية، استخدم النقطة لتجنب الرد التلقائي.\n"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML
        )
    
    async def show_support_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معلومات الدعم"""
        query = update.callback_query
        
        text = (
            "🚨 <b>الدعم والمساعدة</b>\n\n"
            "إذا واجهت أي مشكلة:\n\n"
            "1️⃣ اضغط زر \"أحتاج دعم\" في رسالة الصفقة\n"
            "2️⃣ سيتم إشعار الوسطاء فوراً\n"
            "3️⃣ سيتم مراجعة حالتك خلال 24 ساعة\n\n"
            "⚠️ <b>تذكر:</b>\n"
            "• احتفظ بالاسكرينات\n"
            "• لا تتفاوض خارج الجروب\n"
            "• اكتب الكومنت بدقة\n\n"
            "📞 للتواصل المباشر:\n"
            "@OMAR_M_SHEHATA\n"
            "@m_n_c"
        )
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML
        )
    
    async def abort_cancel_deal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء عملية إلغاء الصفقة"""
        query = update.callback_query
        await query.answer("✅ تم التراجع")
        
        try:
            await query.message.edit_text(
                f"❌ <b>تم إلغاء العملية</b>\n\n"
                f"الصفقة لم يتم إغلاقها.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
    
    async def confirm_cancel_deal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد إلغاء الصفقة"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        user_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # تحديث حالة الصفقة
        self.db.update_deal(deal_id, status=DealStatus.CANCELLED.value)
        self.db.log_action(deal_id, "DEAL_CANCELLED", user_id, "Deal cancelled by user")
        
        await query.answer("✅ تم إلغاء الصفقة")
        
        # تحديث الرسالة
        try:
            await query.message.edit_text(
                f"❌ <b>تم إلغاء الصفقة</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"💰 المبلغ: {deal.amount} TON\n"
                f"👤 بواسطة: {await self.get_user_name_mention(user_id, context)}\n\n"
                f"✅ تم إغلاق الصفقة بنجاح.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        
        # تحديث الرسالة المثبتة إن وجدت
        try:
            if deal.pinned_message_id:
                await context.bot.edit_message_text(
                    chat_id=deal.group_id,
                    message_id=deal.pinned_message_id,
                    text=(
                        f"❌ <b>صفقة ملغاة</b>\n\n"
                        f"🆔 الصفقة: <code>{deal_id}</code>\n"
                        f"💰 المبلغ: {deal.amount} TON\n\n"
                        f"✅ تم إغلاق الصفقة"
                    ),
                    parse_mode=ParseMode.HTML
                )
                # فك التثبيت
                await context.bot.unpin_chat_message(
                    chat_id=deal.group_id,
                    message_id=deal.pinned_message_id
                )
        except Exception as e:
            logger.error(f"Error updating pinned message: {e}")
        
        # إشعار الأطراف
        try:
            buyer_mention = await self.get_user_name_mention(deal.buyer_id, context)
            seller_mention = await self.get_user_name_mention(deal.seller_id, context)
            
            await context.bot.send_message(
                chat_id=deal.group_id,
                text=(
                    f"🔔 <b>إشعار إلغاء</b>\n\n"
                    f"{buyer_mention} / {seller_mention}\n\n"
                    f"❌ تم إلغاء الصفقة <code>{deal_id}</code>\n\n"
                    f"⚠️ إذا كنت قد دفعت بالفعل، يرجى التواصل مع الدعم."
                ),
                parse_mode=ParseMode.HTML
            )
        except:
            pass
    
    # ──────────────────────────────────────────────────────────
    # 🚫 Close Deal with Refund (للمالكين والوسطاء)
    # ──────────────────────────────────────────────────────────
    
    async def close_deal_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """طلب إغلاق الصفقة من الوسيط"""
        query = update.callback_query
        deal_id = query.data.split("_")[2]
        user_id = update.effective_user.id
        
        # التحقق من الصلاحيات
        is_owner = user_id in OWNER_IDS
        is_admin = user_id in ADMIN_IDS
        
        if not is_owner and not is_admin:
            await query.answer("❌ غير مصرح لك", show_alert=True)
            return
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # التحقق من حالة الصفقة
        if deal.status in [DealStatus.COMPLETED.value, DealStatus.CANCELLED.value]:
            await query.answer("⚠️ الصفقة مغلقة بالفعل", show_alert=True)
            return
        
        # تحديد ما إذا كان هناك دفع
        has_payment = deal.payment_tx_hash is not None
        
        # رسالة التأكيد
        confirm_text = (
            f"⚠️ <b>تأكيد إغلاق الصفقة</b>\n\n"
            f"🆔 الصفقة: <code>{deal_id}</code>\n"
            f"💰 المبلغ: {deal.amount} TON\n"
            f"📊 الحالة: {self.ai._translate_status(deal.status)}\n\n"
        )
        
        if has_payment:
            confirm_text += (
                f"💳 <b>تم الدفع:</b> نعم\n"
                f"🔗 TX: <code>{deal.payment_tx_hash[:16]}...</code>\n\n"
                f"✅ سيتم إرجاع المبلغ للمشتري تلقائياً\n\n"
            )
        else:
            confirm_text += f"💳 <b>تم الدفع:</b> لا\n\n"
        
        confirm_text += f"❓ <b>هل أنت متأكد من إغلاق هذه الصفقة؟</b>"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، إغلاق", callback_data=f"confirm_close_deal_{deal_id}"),
                InlineKeyboardButton("❌ لا، تراجع", callback_data=f"abort_close_deal_{deal_id}")
            ]
        ]
        
        await query.message.reply_text(
            confirm_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        await query.answer()
    
    async def abort_close_deal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء عملية إغلاق الصفقة"""
        query = update.callback_query
        await query.answer("✅ تم التراجع")
        
        try:
            await query.message.edit_text(
                f"❌ <b>تم إلغاء العملية</b>\n\n"
                f"لم يتم إغلاق الصفقة.",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
    
    async def confirm_close_deal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد إغلاق الصفقة مع إرجاع المبلغ إن وجد"""
        query = update.callback_query
        deal_id = query.data.split("_")[3]
        user_id = update.effective_user.id
        
        deal = self.db.get_deal(deal_id)
        if not deal:
            await query.answer("❌ الصفقة غير موجودة", show_alert=True)
            return
        
        # التحقق من الصلاحيات
        is_owner = user_id in OWNER_IDS
        is_admin = user_id in ADMIN_IDS
        
        if not is_owner and not is_admin:
            await query.answer("❌ غير مصرح لك", show_alert=True)
            return
        
        # التحقق من وجود دفع
        has_payment = deal.payment_tx_hash is not None
        
        if has_payment:
            # محاولة إرجاع المبلغ
            await query.message.edit_text(
                f"⏳ <b>جاري معالجة إغلاق الصفقة...</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"💰 المبلغ: {deal.amount} TON\n\n"
                f"🔍 جاري محاولة إرجاع المبلغ للمشتري...",
                parse_mode=ParseMode.HTML
            )
            
            # التحقق من وجود عنوان محفوظ
            buyer_wallet = deal.buyer_address
            
            if not buyer_wallet:
                # طلب عنوان المشتري
                context.user_data['pending_close_deal'] = deal_id
                context.user_data['pending_close_by'] = user_id
                context.user_data['waiting_for'] = 'buyer_refund_address'
                
                await query.message.edit_text(
                    f"💼 <b>طلب عنوان المشتري للإرجاع</b>\n\n"
                    f"🆔 الصفقة: <code>{deal_id}</code>\n"
                    f"💰 المبلغ: {deal.amount} TON\n\n"
                    f"⚠️ لم يتم العثور على عنوان محفظة المشتري.\n\n"
                    f"💬 يرجى إرسال عنوان محفظة TON للمشتري لإرجاع المبلغ:",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # محاولة إرجاع المبلغ
            try:
                network_fee = 0.02
                refund_amount = deal.amount - network_fee
                
                refund_tx = await self.ton.send_ton(
                    to_address=buyer_wallet,
                    amount=refund_amount,
                    memo=f"REFUND-{deal_id}"
                )
                
                if refund_tx:
                    self.db.log_action(deal_id, "REFUND_SENT", user_id, 
                                     f"Refund: {refund_amount} TON, TX: {refund_tx}")
                    
                    # تحديث الحالة
                    self.db.update_deal(deal_id, status=DealStatus.CANCELLED.value)
                    self.db.log_action(deal_id, "DEAL_CLOSED_BY_MEDIATOR", user_id, 
                                      f"Closed with refund by {user_id}")
                    
                    # تنظيف رسائل الصفقة من قاعدة البيانات
                    self.db.delete_deal_messages(deal_id)
                    logger.info(f"🧹 Cleaned up messages for cancelled deal {deal_id}")
                    
                    # رسالة النجاح
                    tx_link = f"https://tonscan.org/tx/{refund_tx}"
                    await query.message.edit_text(
                        f"✅ <b>تم إغلاق الصفقة وإرجاع المبلغ</b>\n\n"
                        f"🆔 الصفقة: <code>{deal_id}</code>\n"
                        f"💰 المبلغ المرجع: {refund_amount} TON\n"
                        f"💳 رسوم الشبكة: {network_fee} TON\n"
                        f"📤 إلى: <code>{buyer_wallet}</code>\n"
                        f"<a href='{tx_link}'>رابط المعاملة</a>\n\n"
                        f"✅ تم إغلاق الصفقة بنجاح",
                        parse_mode=ParseMode.HTML
                    )
                    
                    # إشعار في الجروب
                    try:
                        buyer_mention = await self.get_user_name_mention(deal.buyer_id, context)
                        seller_mention = await self.get_user_name_mention(deal.seller_id, context)
                        
                        await context.bot.send_message(
                            chat_id=deal.group_id,
                            text=(
                                f"🔔 <b>إشعار إغلاق الصفقة</b>\n\n"
                                f"{buyer_mention} / {seller_mention}\n\n"
                                f"🚫 تم إغلاق الصفقة <code>{deal_id}</code> من قبل الإدارة\n"
                                f"💸 تم إرجاع {refund_amount} TON للمشتري\n"
                                f"<a href='{tx_link}'>رابط المعاملة</a>"
                            ),
                            parse_mode=ParseMode.HTML,
                            reply_to_message_id=int(deal.pinned_message_id) if deal.pinned_message_id else None
                        )
                        
                        # تحديث الرسالة المثبتة - إزالة الأزرار
                        if deal.pinned_message_id:
                            try:
                                pinned_msg_id = int(deal.pinned_message_id)
                                buyer_mention_close = await self.get_user_name_mention(deal.buyer_id, context)
                                seller_mention_close = await self.get_user_name_mention(deal.seller_id, context)
                                
                                await context.bot.edit_message_text(
                                    chat_id=deal.group_id,
                                    message_id=pinned_msg_id,
                                    text=(
                                        f"🚫 <b>صفقة مغلقة</b>\n\n"
                                        f"🆔 الصفقة: <code>{deal_id}</code>\n"
                                        f"👤 المشتري: {buyer_mention_close}\n"
                                        f"👤 البائع: {seller_mention_close}\n"
                                        f"💰 المبلغ: {deal.amount} TON\n"
                                        f"📝 الوصف: {deal.description}\n\n"
                                        f"💸 تم إرجاع {refund_amount} TON للمشتري\n"
                                        f"<a href='{tx_link}'>عرض المعاملة</a>\n\n"
                                        f"🚫 تم إغلاق الصفقة من قبل الإدارة"
                                    ),
                                    parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True
                                )
                                await context.bot.unpin_chat_message(
                                    chat_id=deal.group_id,
                                    message_id=pinned_msg_id
                                )
                            except (ValueError, TypeError) as convert_error:
                                logger.warning(f"⚠️ Invalid pinned_message_id format: {deal.pinned_message_id}")
                            except Exception as e:
                                logger.error(f"Error updating pinned message: {e}")
                    except Exception as e:
                        logger.error(f"Error sending group notification: {e}")
                    
                else:
                    raise Exception("Transaction failed")
                    
            except Exception as e:
                logger.error(f"Refund error: {e}")
                await query.message.edit_text(
                    f"❌ <b>خطأ في إرجاع المبلغ</b>\n\n"
                    f"🆔 الصفقة: <code>{deal_id}</code>\n"
                    f"⚠️ {str(e)}\n\n"
                    f"يرجى إرجاع المبلغ يدوياً",
                    parse_mode=ParseMode.HTML
                )
        else:
            # لا يوجد دفع - إغلاق مباشر
            self.db.update_deal(deal_id, status=DealStatus.CANCELLED.value)
            self.db.log_action(deal_id, "DEAL_CLOSED_BY_MEDIATOR", user_id, 
                              f"Closed without refund by {user_id}")
            
            # تنظيف رسائل الصفقة من قاعدة البيانات
            self.db.delete_deal_messages(deal_id)
            logger.info(f"🧹 Cleaned up messages for cancelled deal {deal_id}")
            
            await query.message.edit_text(
                f"✅ <b>تم إغلاق الصفقة</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"📊 الحالة: مغلقة\n\n"
                f"✅ لم يتم الدفع - تم الإغلاق بنجاح",
                parse_mode=ParseMode.HTML
            )
            
            # إشعار في الجروب
            try:
                buyer_mention_no_pay = await self.get_user_name_mention(deal.buyer_id, context)
                seller_mention_no_pay = await self.get_user_name_mention(deal.seller_id, context)
                
                await context.bot.send_message(
                    chat_id=deal.group_id,
                    text=(
                        f"🔔 <b>إشعار</b>\n\n"
                        f"🚫 تم إغلاق الصفقة <code>{deal_id}</code> من قبل الإدارة"
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=int(deal.pinned_message_id) if deal.pinned_message_id else None
                )
                
                # تحديث الرسالة المثبتة - إزالة الأزرار
                if deal.pinned_message_id:
                    try:
                        pinned_msg_id = int(deal.pinned_message_id)
                        await context.bot.edit_message_text(
                            chat_id=deal.group_id,
                            message_id=pinned_msg_id,
                            text=(
                                f"🚫 <b>صفقة مغلقة</b>\n\n"
                                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                                f"👤 المشتري: {buyer_mention_no_pay}\n"
                                f"👤 البائع: {seller_mention_no_pay}\n"
                                f"💰 المبلغ: {deal.amount} TON\n"
                                f"📝 الوصف: {deal.description}\n\n"
                                f"🚫 تم الإغلاق من قبل الإدارة"
                            ),
                            parse_mode=ParseMode.HTML
                        )
                        await context.bot.unpin_chat_message(
                            chat_id=deal.group_id,
                            message_id=pinned_msg_id
                        )
                    except (ValueError, TypeError) as convert_error:
                        logger.warning(f"⚠️ Invalid pinned_message_id format: {deal.pinned_message_id}")
                    except Exception as e:
                        logger.error(f"Error updating pinned message: {e}")
            except Exception as e:
                logger.error(f"Error sending group notification: {e}")
            logger.error(f"Error sending notification: {e}")
    
    # ──────────────────────────────────────────────────────────
    # � Admin Commands (للاختبار)
    # ──────────────────────────────────────────────────────────
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض رصيد المحفظة (للمشرفين)"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_IDS and user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمشرفين والمالكين فقط")
            return
        
        balance = await self.ton.get_balance()
        
        await update.message.reply_text(
            f"💰 <b>رصيد المحفظة</b>\n\n"
            f"📍 العنوان:\n<code>{self.ton.wallet_address[:16]}...</code>\n\n"
            f"💵 الرصيد: {balance} TON",
            parse_mode=ParseMode.HTML
        )
    
    async def add_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إضافة المجموعة الحالية للقائمة المصرح بها (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        if not self.is_group_chat(update):
            await update.message.reply_text("❌ هذا الأمر يعمل فقط في المجموعات")
            return
        
        group_id = update.effective_chat.id
        group_name = update.effective_chat.title
        
        if self.db.add_authorized_group(group_id, group_name, user_id):
            await update.message.reply_text(
                f"✅ <b>تم إضافة هذه المجموعة بنجاح</b>\n\n"
                f"📌 الاسم: {group_name}\n"
                f"🆔 ID: <code>{group_id}</code>\n\n"
                f"✅ البوت الآن يعمل في هذه المجموعة",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء الإضافة")
    
    async def remove_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إزالة المجموعة الحالية من القائمة المصرح بها (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        if not self.is_group_chat(update):
            await update.message.reply_text("❌ هذا الأمر يعمل فقط في المجموعات")
            return
        
        group_id = update.effective_chat.id
        group_name = update.effective_chat.title
        
        if self.db.remove_authorized_group(group_id):
            await update.message.reply_text(
                f"✅ <b>تم إزالة هذه المجموعة بنجاح</b>\n\n"
                f"📌 الاسم: {group_name}\n"
                f"🆔 ID: <code>{group_id}</code>\n\n"
                f"⚠️ البوت لن يعمل في هذه المجموعة بعد الآن",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء الإزالة")
    
    async def check_payment_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """التحقق من وصول الدفع (للجميع)"""
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "📋 <b>الاستخدام:</b>\n"
                "<code>/check_payment DEAL-XXXXX</code>\n\n"
                "سيقوم بالتحقق يدوياً من وصول الدفع لهذه الصفقة",
                parse_mode=ParseMode.HTML
            )
            return
        
        deal_id = context.args[0]
        deal = self.db.get_deal(deal_id)
        
        if not deal:
            await update.message.reply_text(f"❌ الصفقة <code>{deal_id}</code> غير موجودة", parse_mode=ParseMode.HTML)
            return
        
        if deal.status != DealStatus.WAITING_PAYMENT.value:
            await update.message.reply_text(
                f"⚠️ الصفقة ليست في حالة انتظار الدفع\n"
                f"الحالة الحالية: {self.ai._translate_status(deal.status)}"
            )
            return
        
        checking_msg = await update.message.reply_text(
            f"⏳ <b>جاري التحقق من الدفع...</b>\n\n"
            f"🆔 الصفقة: <code>{deal_id}</code>\n"
            f"💰 المبلغ: {deal.amount} TON",
            parse_mode=ParseMode.HTML
        )
        
        payment_info = await self.ton.check_payment(deal_id, deal.amount, deal.comment)
        
        if payment_info:
            # التحقق من وجود معاملات ناقصة
            if payment_info.get('insufficient'):
                insufficient_list = payment_info.get('payments', [])
                payments_text = ""
                for idx, p in enumerate(insufficient_list, 1):
                    payments_text += f"\n  {idx}. دفع {p['amount']} TON (ناقص {p['required'] - p['amount']} TON)"
                
                await checking_msg.edit_text(
                    f"⚠️ <b>تم العثور على دفعات لكن المبلغ ناقص!</b>\n\n"
                    f"🆔 الصفقة: <code>{deal_id}</code>\n"
                    f"💰 المبلغ المطلوب: {deal.amount} TON\n\n"
                    f"📊 الدفعات المستلمة:{payments_text}\n\n"
                    f"❗️ <b>يجب دفع المبلغ كاملاً ({deal.amount} TON)</b>\n\n"
                    f"📌 تأكد من:\n"
                    f"  • إرسال المبلغ الكامل: {deal.amount} TON\n"
                    f"  • كتابة الكومنت: <code>{deal.comment}</code>\n"
                    f"  • الإرسال لـ: <code>{TON_WALLET_ADDRESS[:16]}...</code>",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # إنشاء رابط المعاملة على TON blockchain
            tx_hash = payment_info['tx_hash']
            tx_link = f"https://tonscan.org/tx/{tx_hash}"
            
            await checking_msg.edit_text(
                f"✅ <b>تم العثور على الدفع!</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"💰 المبلغ المطلوب: {deal.amount} TON\n"
                f"💵 المبلغ المستلم: {payment_info['amount']} TON\n"
                f"<a href='{tx_link}'>عرض المعاملة على TON</a>\n\n"
                f"📊 جاري معالجة الصفقة...",
                parse_mode=ParseMode.HTML
            )
            await self.process_payment_confirmation(context.application, deal_id, payment_info)
        else:
            await checking_msg.edit_text(
                f"❌ <b>لم يتم العثور على الدفع</b>\n\n"
                f"🆔 الصفقة: <code>{deal_id}</code>\n"
                f"💰 المبلغ المطلوب: {deal.amount} TON\n\n"
                f"📌 تأكد من:\n"
                f"  • إرسال المبلغ الصحيح\n"
                f"  • كتابة الكومنت: <code>{deal.comment}</code>\n"
                f"  • الإرسال لـ: <code>{TON_WALLET_ADDRESS[:16]}...</code>\n\n"
                f"⏳ يمكنك محاولة التحقق مرة أخرى بعد قليل.",
                parse_mode=ParseMode.HTML
            )
    
    async def cancel_deal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء/إغلاق صفقة"""
        user_id = update.effective_user.id
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "📋 <b>الاستخدام:</b>\n"
                "<code>/cancel DEAL-XXXXX</code>\n\n"
                "لإلغاء وإغلاق الصفقة\n\n"
                "⚠️ <b>ملاحظة:</b>\n"
                "• الأدمن: يمكنه إلغاء أي صفقة\n"
                "• البائع/المشتري: فقط قبل الدفع",
                parse_mode=ParseMode.HTML
            )
            return
        
        deal_id = context.args[0]
        deal = self.db.get_deal(deal_id)
        
        if not deal:
            await update.message.reply_text(f"❌ الصفقة <code>{deal_id}</code> غير موجودة", parse_mode=ParseMode.HTML)
            return
        
        # التحقق من الصلاحيات
        is_owner = user_id in OWNER_IDS
        is_admin = user_id in ADMIN_IDS
        is_party = user_id in [deal.buyer_id, deal.seller_id]
        
        if not is_owner and not is_admin and not is_party:
            await update.message.reply_text(
                "❌ <b>غير مصرح</b>\n\n"
                "فقط المالك أو الأدمن أو أطراف الصفقة يمكنهم إلغاء الصفقة.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # المالك والأدمن يمكنهم إلغاء أي صفقة
        # البائع/المشتري فقط قبل الدفع
        if not is_owner and not is_admin:
            if deal.status != DealStatus.WAITING_PAYMENT.value:
                await update.message.reply_text(
                    f"❌ <b>لا يمكن إلغاء الصفقة</b>\n\n"
                    f"يمكنك فقط إلغاء الصفقة قبل الدفع.\n"
                    f"الحالة الحالية: {self.ai._translate_status(deal.status)}\n\n"
                    f"⚠️ إذا كانت هناك مشكلة، استخدم زر '🚨 أحتاج دعم'",
                    parse_mode=ParseMode.HTML
                )
                return
        
        # التحقق من أن الصفقة لم يتم إغلاقها مسبقاً
        if deal.status in [DealStatus.COMPLETED.value, DealStatus.CANCELLED.value]:
            await update.message.reply_text(
                f"⚠️ <b>الصفقة مغلقة بالفعل</b>\n\n"
                f"الحالة: {self.ai._translate_status(deal.status)}",
                parse_mode=ParseMode.HTML
            )
            return
        
        # تأكيد الإلغاء
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، إلغاء الصفقة", callback_data=f"confirm_cancel_{deal_id}"),
                InlineKeyboardButton("❌ لا، تراجع", callback_data=f"abort_cancel_{deal_id}")
            ]
        ]
        
        await update.message.reply_text(
            f"⚠️ <b>تأكيد إلغاء الصفقة</b>\n\n"
            f"🆔 الصفقة: <code>{deal_id}</code>\n"
            f"💰 المبلغ: {deal.amount} TON\n"
            f"📋 الحالة: {self.ai._translate_status(deal.status)}\n\n"
            f"❓ <b>هل أنت متأكد من إلغاء هذه الصفقة؟</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    
    def run(self):
        """تشغيل البوت"""
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Command Handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("check_payment", self.check_payment_command))
        application.add_handler(CommandHandler("cancel", self.cancel_deal_command))
        
        # Owner Commands
        application.add_handler(CommandHandler("add_mediator", self.add_mediator_command))
        application.add_handler(CommandHandler("remove_mediator", self.remove_mediator_command))
        application.add_handler(CommandHandler("list_mediators", self.list_mediators_command))
        application.add_handler(CommandHandler("add_group", self.add_group_command))
        application.add_handler(CommandHandler("remove_group", self.remove_group_command))
        application.add_handler(CommandHandler("wallet_deposit", self.wallet_deposit_command))
        application.add_handler(CommandHandler("withdraw_wallet", self.wallet_withdraw_command))
        
        # Callback Handlers
        application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        # Message Handlers
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.message_handler
        ))
        
        # Photo Handler (للاسكرينات)
        application.add_handler(MessageHandler(
            filters.PHOTO,
            self.message_handler
        ))
        
        # بدء مراقبة الدفعات في الخلفية - كل 30 ثانية
        application.job_queue.run_repeating(
            self.payment_monitor_job,
            interval=30,  # كل 30 ثانية
            first=5  # يبدأ بعد 5 ثوان من تشغيل البوت
        )
        
        # Start the bot
        logger.info("🚀 OMAR PANDA Escrow Bot Started")
        logger.info("✅ Payment monitor will start in 5 seconds...")
        logger.info("🔄 Auto-verification will check every 30 seconds for pending payments")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # ──────────────────────────────────────────────────────────
    # 👑 Owner Admin Panel (لوحة تحكم المالكين)
    # ──────────────────────────────────────────────────────────
    
    async def show_admin_mediators_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة إدارة الوسطاء"""
        query = update.callback_query
        await query.answer()
        
        mediators = self.db.get_active_mediators()
        
        text = "╔══════════════════╗\n"
        text += "║ 📊 إدارة الوسطاء ║\n"
        text += "╚══════════════════╝\n\n"
        
        if mediators:
            text += "👥 <b>الوسطاء النشطين:</b>\n\n"
            for med in mediators:
                text += f"• <code>{med['user_id']}</code> - {med['username']}\n"
            text += "\n━━━━━━━━━━━━━━━━━━━━━━━\n"
        else:
            text += "📋 لا يوجد وسطاء حالياً\n\n"
        
        text += "اختر عملية:"
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة وسيط", callback_data="add_mediator_start")],
            [InlineKeyboardButton("➖ إزالة وسيط", callback_data="remove_mediator_start")],
            [InlineKeyboardButton("🔄 تحديث القائمة", callback_data="admin_mediators")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ]
        
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            # تجاهل خطأ "Message is not modified"
            if "Message is not modified" not in str(e):
                raise
    
    async def show_admin_wallet_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة إدارة المحفظة"""
        query = update.callback_query
        await query.answer()
        
        balance = await self.ton.get_balance()
        
        text = "╔══════════════════╗\n"
        text += "║ 💰 إدارة المحفظة ║\n"
        text += "╚══════════════════╝\n\n"
        text += f"💵 <b>الرصيد الحالي:</b> {balance} TON\n\n"
        text += f"📍 <b>عنوان المحفظة:</b>\n<code>{TON_WALLET_ADDRESS[:30]}...</code>\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "اختر عملية:"
        
        keyboard = [
            [InlineKeyboardButton("📥 عنوان الإيداع", callback_data="wallet_show_deposit")],
            [InlineKeyboardButton("📤 سحب من المحفظة", callback_data="wallet_withdraw_start")],
            [InlineKeyboardButton("🔄 تحديث الرصيد", callback_data="admin_wallet")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ]
        
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            # تجاهل خطأ "Message is not modified"
            if "Message is not modified" not in str(e):
                raise
    
    async def show_admin_tools_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة أدوات الوساطة"""
        query = update.callback_query
        await query.answer()
        
        text = "╔══════════════════╗\n"
        text += "║ 🔧 أدوات الوساطة ║\n"
        text += "╚══════════════════╝\n\n"
        text += "<b>الأوامر المتاحة:</b>\n\n"
        text += "<code>/check_payment DEAL-ID</code>\n"
        text += "التحقق من وصول الدفع\n\n"
        text += "<code>/cancel DEAL-ID</code>\n"
        text += "إلغاء صفقة\n\n"
        text += "<code>/balance</code>\n"
        text += "عرض رصيد المحفظة\n\n"
        
        if update.effective_user.id in OWNER_IDS:
            text += "<code>/simulate_payment DEAL-ID</code>\n"
            text += "محاكاة دفع (للاختبار)\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def admin_back_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """زر الرجوع للوحة الرئيسية"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        is_owner = user_id in OWNER_IDS
        
        welcome_text = "╔══════════════════════╗\n"
        welcome_text += "║  🔐 Waset Panda  & First ai         ║\n"
        welcome_text += "╚══════════════════════╝\n\n"
        
        if is_owner:
            welcome_text += "👑 <b>لوحة تحكم المالك</b>\n\n"
            welcome_text += "اختر من الأزرار أدناه:"
            
            keyboard = [
                [InlineKeyboardButton("📊 إدارة الوسطاء", callback_data="admin_mediators")],
                [InlineKeyboardButton("� إدارة شاتات الوساطة", callback_data="admin_groups")],
                [InlineKeyboardButton("�💰 إدارة المحفظة", callback_data="admin_wallet")],
                [InlineKeyboardButton("🔧 أدوات الوساطة", callback_data="admin_tools")]
            ]
        else:
            welcome_text += "🔧 <b>لوحة الوسيط</b>\n\n"
            welcome_text += "اختر من الأدوات أدناه:"
            
            keyboard = [
                [InlineKeyboardButton("🔧 أدوات الوساطة", callback_data="admin_tools")]
            ]
        
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def start_add_mediator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إضافة وسيط"""
        query = update.callback_query
        await query.answer()
        
        text = "➕ <b>إضافة وسيط جديد</b>\n\n"
        text += "أرسل User ID للوسيط الجديد:\n\n"
        text += "<b>مثال:</b>\n<code>123456789</code>\n\n"
        text += "⚠️ للإلغاء، أرسل: <code>إلغاء</code>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_mediators")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # حفظ حالة انتظار إدخال User ID
        context.user_data['waiting_mediator_add'] = True
    
    async def start_remove_mediator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إزالة وسيط"""
        query = update.callback_query
        await query.answer()
        
        mediators = self.db.get_active_mediators()
        
        if not mediators:
            await query.answer("❌ لا يوجد وسطاء لإزالتهم", show_alert=True)
            return
        
        text = "➖ *إزالة وسيط*\n\n"
        text += "أرسل User ID للوسيط المراد إزالته:\n\n"
        text += "<b>الوسطاء الحاليين:</b>\n"
        for med in mediators:
            text += f"• <code>{med['user_id']}</code> - {med['username']}\n"
        text += "\n⚠️ للإلغاء، أرسل: <code>إلغاء</code>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_mediators")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # حفظ حالة انتظار إدخال User ID
        context.user_data['waiting_mediator_remove'] = True
    
    async def show_admin_groups_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة إدارة شاتات الوساطة"""
        query = update.callback_query
        await query.answer()
        
        groups = self.db.get_authorized_groups()
        
        text = "╔════════════════════════╗\n"
        text += "║ 💬 شاتات الوساطة المصرح بها ║\n"
        text += "╚════════════════════════╝\n\n"
        
        if groups:
            text += "✅ <b>المجموعات المصرح بها:</b>\n\n"
            for group in groups:
                group_id, group_name, added_at = group
                text += f"• <code>{group_id}</code>\n"
                if group_name:
                    text += f"  📌 {group_name}\n"
                text += "\n"
            text += "━━━━━━━━━━━━━━━━━━━━━━━\n"
        else:
            text += "📋 لا توجد مجموعات مصرح بها\n"
            text += "⚠️ البوت لن يعمل في أي مجموعة!\n\n"
        
        text += "اختر عملية:"
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة مجموعة", callback_data="add_group_start")],
            [InlineKeyboardButton("➖ إزالة مجموعة", callback_data="remove_group_start")],
            [InlineKeyboardButton("📋 عرض القائمة", callback_data="list_groups")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ]
        
        try:
            await query.edit_message_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            # تجاهل خطأ "Message is not modified"
            if "Message is not modified" not in str(e):
                raise
    
    async def start_add_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إضافة مجموعة"""
        query = update.callback_query
        await query.answer()
        
        text = "➕ <b>إضافة شات وساطة</b>\n\n"
        text += "📝 <b>الطريقة:</b>\n"
        text += "1. أرسل Group ID للمجموعة\n"
        text += "2. أو ارسل <code>/add_group</code> في المجموعة المراد إضافتها\n\n"
        text += "💡 <b>للحصول على Group ID:</b>\n"
        text += "• أضف البوت للمجموعة\n"
        text += "• أرسل أي رسالة في المجموعة\n"
        text += "• سيرسل البوت الـ ID\n\n"
        text += "⚠️ للإلغاء، أرسل: <code>إلغاء</code>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_groups")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # حفظ حالة انتظار إدخال Group ID
        context.user_data['waiting_group_add'] = True
    
    async def start_remove_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إزالة مجموعة"""
        query = update.callback_query
        await query.answer()
        
        groups = self.db.get_authorized_groups()
        
        if not groups:
            await query.answer("❌ لا توجد مجموعات لإزالتها", show_alert=True)
            return
        
        text = "➖ <b>إزالة شات وساطة</b>\n\n"
        text += "أرسل Group ID للمجموعة المراد إزالتها:\n\n"
        text += "<b>المجموعات الحالية:</b>\n"
        for group in groups:
            group_id, group_name, added_at = group
            text += f"• <code>{group_id}</code>"
            if group_name:
                text += f" - {group_name}"
            text += "\n"
        text += "\n⚠️ للإلغاء، أرسل: <code>إلغاء</code>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_groups")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # حفظ حالة انتظار إدخال Group ID
        context.user_data['waiting_group_remove'] = True
    
    async def show_authorized_groups_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة المجموعات المصرح بها"""
        query = update.callback_query
        await query.answer()
        
        groups = self.db.get_authorized_groups()
        
        text = "╔════════════════════════╗\n"
        text += "║ 📋 قائمة شاتات الوساطة ║\n"
        text += "╚════════════════════════╝\n\n"
        
        if groups:
            text += f"✅ <b>عدد المجموعات: {len(groups)}</b>\n\n"
            for i, group in enumerate(groups, 1):
                group_id, group_name, added_at = group
                text += f"{i}. Group ID: <code>{group_id}</code>\n"
                if group_name:
                    text += f"   📌 {group_name}\n"
                text += f"   📅 تم الإضافة: {added_at[:10]}\n\n"
        else:
            text += "⚠️ لا توجد مجموعات مصرح بها!\n"
            text += "البوت لن يعمل في أي شات.\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_groups")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_wallet_deposit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض عنوان الإيداع"""
        query = update.callback_query
        await query.answer()
        
        text = " ╔═════════════════╗\n"
        text += " 📥 عنوان الإيداع \n"
        text += " ╚═════════════════╝\n\n"
        text += f"📍 <b>العنوان الكامل:</b>\n<code>{TON_WALLET_ADDRESS}</code>\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "⚠️ <b>تعليمات:</b>\n"
        text += "• أرسل TON إلى هذا العنوان\n"
        text += "• سيظهر في رصيد البوت تلقائياً\n"
        text += "• لا تحتاج Comment للإيداع\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_wallet")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def start_wallet_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية سحب من المحفظة"""
        query = update.callback_query
        await query.answer()
        
        balance = await self.ton.get_balance()
        
        text =" ╔═════════════════╗\n"
        text +="📤 سحب من المحفظة \n"
        text +="╚═════════════════╝\n\n"
        text += f"💵 <b>الرصيد المتاح:</b> {balance} TON\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "أرسل المعلومات بالصيغة التالية:\n\n"
        text += "<code>المبلغ العنوان</code>\n\n"
        text += "<b>مثال:</b>\n"
        text += "<code>10 EQCabc123def456...</code>\n\n"
        text += "⚠️ للإلغاء، أرسل: <code>إلغاء</code>"
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_wallet")]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # حفظ حالة انتظار إدخال بيانات السحب
        context.user_data['waiting_wallet_withdraw'] = True
    
    # ──────────────────────────────────────────────────────────
    # 👑 Owner Commands (للمالكين فقط)
    # ──────────────────────────────────────────────────────────
    
    async def add_mediator_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إضافة وسيط (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "📋 <b>الاستخدام:</b>\n"
                "<code>/add_mediator USER_ID</code>\n\n"
                "<b>مثال:</b>\n"
                "<code>/add_mediator 123456789</code>\n\n"
                "لإضافة وسيط جديد للنظام",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            mediator_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ User ID غير صحيح")
            return
        
        # محاولة الحصول على معلومات المستخدم
        try:
            user = await context.bot.get_chat(mediator_id)
            username = user.username or user.first_name or f"User{mediator_id}"
        except:
            username = f"User{mediator_id}"
        
        # إضافة الوسيط
        if self.db.add_mediator(mediator_id, username, user_id):
            # تحديث قائمة ADMIN_IDS
            if mediator_id not in ADMIN_IDS:
                ADMIN_IDS.append(mediator_id)
            
            await update.message.reply_text(
                f"✅ <b>تم إضافة الوسيط بنجاح</b>\n\n"
                f"🆔 ID: <code>{mediator_id}</code>\n"
                f"👤 الاسم: {username}",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء الإضافة")
    
    async def remove_mediator_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إزالة وسيط (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "📋 <b>الاستخدام:</b>\n"
                "<code>/remove_mediator USER_ID</code>\n\n"
                "لإزالة وسيط من النظام",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            mediator_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ User ID غير صحيح")
            return
        
        if self.db.remove_mediator(mediator_id):
            # إزالة من قائمة ADMIN_IDS
            if mediator_id in ADMIN_IDS:
                ADMIN_IDS.remove(mediator_id)
            
            await update.message.reply_text(
                f"✅ <b>تم إزالة الوسيط بنجاح</b>\n\n"
                f"🆔 ID: <code>{mediator_id}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ حدث خطأ أثناء الإزالة")
    
    async def list_mediators_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة الوسطاء (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        mediators = self.db.get_active_mediators()
        
        if not mediators:
            await update.message.reply_text("📋 لا يوجد وسطاء حالياً")
            return
        
        text = "👥 <b>قائمة الوسطاء النشطين:</b>\n\n"
        for med in mediators:
            text += f"• <code>{med['user_id']}</code> - {med['username']}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    async def wallet_deposit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض عنوان الإيداع (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        await update.message.reply_text(
            f"💰 <b>عنوان الإيداع</b>\n\n"
            f"📍 العنوان:\n<code>{TON_WALLET_ADDRESS}</code>\n\n"
            f"⚠️ أرسل TON إلى هذا العنوان لإيداعها في محفظة البوت",
            parse_mode=ParseMode.HTML
        )
    
    async def wallet_withdraw_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """سحب من المحفظة (للمالكين فقط)"""
        user_id = update.effective_user.id
        
        if user_id not in OWNER_IDS:
            await update.message.reply_text("❌ هذا الأمر للمالكين فقط")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "📋 <b>الاستخدام:</b>\n"
                "<code>/withdraw_wallet AMOUNT ADDRESS</code>\n\n"
                "<b>مثال:</b>\n"
                "<code>/withdraw_wallet 10 EQCabc123...</code>\n\n"
                "لسحب TON من محفظة البوت",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            amount = float(context.args[0])
            address = context.args[1]
        except:
            await update.message.reply_text("❌ صيغة غير صحيحة")
            return
        
        # التحقق من الرصيد
        balance = await self.ton.get_balance()
        if amount > balance:
            await update.message.reply_text(
                f"❌ <b>رصيد غير كافٍ</b>\n\n"
                f"الرصيد الحالي: {balance} TON\n"
                f"المبلغ المطلوب: {amount} TON",
                parse_mode=ParseMode.HTML
            )
            return
        
        # تنفيذ السحب
        tx_hash = await self.ton.send_ton(address, amount)
        
        if tx_hash:
            # تسجيل المعاملة
            self.db.log_wallet_transaction("WITHDRAW", amount, user_id, tx_hash, 
                                         f"Owner withdrawal to {address[:16]}...")
            
            await update.message.reply_text(
                f"✅ <b>تم السحب بنجاح</b>\n\n"
                f"💰 المبلغ: {amount} TON\n"
                f"📤 إلى: <code>{address}</code>\n"
                f"🔗 TX: <code>{tx_hash}</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text("❌ فشل السحب")
    
    def _translate_role(self, role: str) -> str:
        """ترجمة الدور"""
        return "مشتري 🛒" if role == "buyer" else "بائع 📦"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🎯 MAIN ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    """نقطة البداية"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🔐 OMAR PANDA - TON ESCROW SYSTEM 🔐                ║
║                                                                ║
║              Professional Telegram Escrow Bot                  ║
║                    Version 1.0.1 - Auto Payment Check         ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

[✓] Database initialized
[✓] TON Wallet ready (Local Simulation Mode)
[✓] AI support loaded
[✓] Security protocols active
[✓] Auto payment verification: ENABLED (every 30 seconds)

⚙️  SIMULATION MODE ACTIVE
   - Payments are simulated locally
   - Use /simulate_payment DEAL-ID to test
   - For production: integrate real TON SDK

🔄 AUTO VERIFICATION FEATURES:
   ✓ Automatic payment detection every 30 seconds
   ✓ Real-time notifications when payment received
   ✓ Auto-update deal status on payment confirmation
   ✓ Detailed logs for debugging

Starting bot...
    """)
    
    # التحقق من المتغيرات
    if not TELEGRAM_BOT_TOKEN or "your_bot_token" in TELEGRAM_BOT_TOKEN.lower():
        print("❌ ERROR: Please set TELEGRAM_BOT_TOKEN in the code")
        print("   Edit line 52 and add your bot token")
        return
    
    if not TON_WALLET_ADDRESS or "your_wallet" in TON_WALLET_ADDRESS.lower():
        print("❌ ERROR: Please set TON_WALLET_ADDRESS in the code")
        print("   Edit line 58 and add your wallet address")
        return
    
    if not WALLET_MNEMONIC or WALLET_MNEMONIC[0] == "word1":
        print("⚠️  WARNING: Wallet mnemonic not configured!")
        print("   Edit lines 62-67 and add your 24 seed words")
        print("   Without this, automatic withdrawals will NOT work!")
        print("")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    if not ADMIN_IDS or ADMIN_IDS[0] == 7657546816:
        print("⚠️  WARNING: Default admin IDs detected.")
        print("   Edit line 85 and add your Telegram User IDs")
    
    print("\n" + "="*64)
    print("🚀 Bot Configuration:")
    print(f"   📱 Bot Token: {'✓ Set' if TELEGRAM_BOT_TOKEN else '✗ Missing'}")
    print(f"   💰 Wallet: {TON_WALLET_ADDRESS[:16]}...")
    print(f"   🔑 Mnemonic: {'✓ Set' if WALLET_MNEMONIC and WALLET_MNEMONIC[0] != 'word1' else '✗ Missing'}")
    print(f"   👥 Admins: {len(ADMIN_IDS)} configured")
    print(f"   🔧 Mode: SIMULATION (Local)")
    print(f"   🔄 Auto Check: ENABLED (every 30 sec)")
    print("\n   💡 Admin Commands:")
    print("      /simulate_payment DEAL-ID  - Simulate payment")
    print("      /balance                    - Check wallet balance")
    print("      /check_payment DEAL-ID      - Manual payment check")
    print("="*64 + "\n")
    
    # تشغيل البوت
    bot = EscrowBot()
    bot.run()

if __name__ == "__main__":
    main()
