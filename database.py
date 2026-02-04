"""
🗄️ Database Manager for Neon PostgreSQL

هذا الملف يدير الاتصال بقاعدة بيانات PostgreSQL من Neon
باستخدام متغير البيئة DATABASE_URL

✅ يدعم SQLite للتطوير المحلي
✅ يدعم PostgreSQL لـ Production (Neon)
✅ متوافق مع app.py و panda_giveaways_bot.py
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from contextlib import contextmanager

# تحديد نوع قاعدة البيانات بناءً على وجود DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from psycopg2 import pool
        print("✅ Using PostgreSQL (Neon)")
    except ImportError:
        print("❌ ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary")
        USE_POSTGRES = False
else:
    import sqlite3
    print("⚠️ Using SQLite (Local Development)")
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'panda_giveaways.db')


class DatabaseManager:
    """مدير قاعدة البيانات الموحد لـ SQLite و PostgreSQL"""
    
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        self.connection_pool = None
        
        if self.use_postgres:
            self._init_postgres_pool()
        else:
            self.db_path = DATABASE_PATH
        
        self.init_database()
    
    def _init_postgres_pool(self):
        """إنشاء connection pool لـ PostgreSQL"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,  # min=1, max=20 connections
                DATABASE_URL,
                cursor_factory=RealDictCursor
            )
            print("✅ PostgreSQL connection pool created")
        except Exception as e:
            print(f"❌ Failed to create PostgreSQL pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        if self.use_postgres:
            conn = self.connection_pool.getconn()
            try:
                yield conn
            finally:
                self.connection_pool.putconn(conn)
        else:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch: str = None) -> Any:
        """
        تنفيذ استعلام SQL
        
        Args:
            query: استعلام SQL
            params: معاملات الاستعلام
            fetch: 'one' | 'all' | None
        """
        # تحويل ? إلى %s لـ PostgreSQL
        if self.use_postgres:
            query = query.replace('?', '%s')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch == 'one':
                result = cursor.fetchone()
                conn.commit()
                return dict(result) if result else None
            elif fetch == 'all':
                results = cursor.fetchall()
                conn.commit()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.rowcount
    
    def init_database(self):
        """إنشاء جداول قاعدة البيانات"""
        print("🔧 Initializing database tables...")
        
        # تعريف الأنواع حسب نوع قاعدة البيانات
        if self.use_postgres:
            BIGINT = "BIGINT"
            TEXT = "TEXT"
            REAL = "DECIMAL(10,2)"
            INTEGER = "INTEGER"
            TIMESTAMP = "TIMESTAMP"
            AUTOINCREMENT = "SERIAL PRIMARY KEY"
        else:
            BIGINT = "INTEGER"
            TEXT = "TEXT"
            REAL = "REAL"
            INTEGER = "INTEGER"
            TIMESTAMP = "TEXT"
            AUTOINCREMENT = "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # جدول المستخدمين
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS users (
                    user_id {BIGINT} PRIMARY KEY,
                    username {TEXT},
                    full_name {TEXT} NOT NULL,
                    balance {REAL} DEFAULT 0.0,
                    total_spins {INTEGER} DEFAULT 0,
                    available_spins {INTEGER} DEFAULT 0,
                    total_referrals {INTEGER} DEFAULT 0,
                    valid_referrals {INTEGER} DEFAULT 0,
                    referrer_id {BIGINT},
                    created_at {TIMESTAMP} NOT NULL,
                    last_active {TIMESTAMP},
                    is_banned {INTEGER} DEFAULT 0,
                    last_spin_time {TIMESTAMP},
                    spin_count_today {INTEGER} DEFAULT 0,
                    last_withdrawal_time {TIMESTAMP},
                    ton_wallet {TEXT},
                    vodafone_number {TEXT},
                    tickets {INTEGER} DEFAULT 0,
                    is_device_verified {INTEGER} DEFAULT 0,
                    verification_required {INTEGER} DEFAULT 1,
                    ban_reason {TEXT}
                )
            """)
            
            # جدول الإحالات
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS referrals (
                    id {AUTOINCREMENT},
                    referrer_id {BIGINT} NOT NULL,
                    referred_id {BIGINT} NOT NULL,
                    is_valid {INTEGER} DEFAULT 0,
                    created_at {TIMESTAMP} NOT NULL,
                    validated_at {TIMESTAMP},
                    channels_checked {INTEGER} DEFAULT 0,
                    device_verified {INTEGER} DEFAULT 0,
                    UNIQUE(referrer_id, referred_id)
                )
            """)
            
            # جدول اللفات
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS spins (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL,
                    prize_name {TEXT} NOT NULL,
                    prize_amount {REAL} NOT NULL,
                    spin_time {TIMESTAMP} NOT NULL,
                    spin_hash {TEXT} NOT NULL UNIQUE,
                    ip_address {TEXT}
                )
            """)
            
            # جدول السحوبات
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL,
                    amount {REAL} NOT NULL,
                    withdrawal_type {TEXT} NOT NULL,
                    wallet_address {TEXT},
                    phone_number {TEXT},
                    status {TEXT} NOT NULL DEFAULT 'pending',
                    requested_at {TIMESTAMP} NOT NULL,
                    processed_at {TIMESTAMP},
                    processed_by {BIGINT},
                    tx_hash {TEXT},
                    rejection_reason {TEXT}
                )
            """)
            
            # جدول المهام
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS tasks (
                    id {AUTOINCREMENT},
                    task_type {TEXT} NOT NULL,
                    task_name {TEXT} NOT NULL,
                    task_description {TEXT},
                    task_link {TEXT},
                    channel_username {TEXT},
                    is_pinned {INTEGER} DEFAULT 0,
                    is_active {INTEGER} DEFAULT 1,
                    added_by {BIGINT} NOT NULL,
                    added_at {TIMESTAMP} NOT NULL,
                    reward_amount {REAL} DEFAULT 0
                )
            """)
            
            # جدول إنجاز المهام
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS user_tasks (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL,
                    task_id {INTEGER} NOT NULL,
                    completed_at {TIMESTAMP} NOT NULL,
                    verified {INTEGER} DEFAULT 0,
                    UNIQUE(user_id, task_id)
                )
            """)
            
            # جدول القنوات الإجبارية
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS required_channels (
                    id {AUTOINCREMENT},
                    channel_id {TEXT} NOT NULL UNIQUE,
                    channel_name {TEXT} NOT NULL,
                    channel_url {TEXT} NOT NULL,
                    is_active {INTEGER} DEFAULT 1,
                    added_by {BIGINT} NOT NULL,
                    added_at {TIMESTAMP} NOT NULL
                )
            """)
            
            # جدول التحقق من الأجهزة
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS device_verifications (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL UNIQUE,
                    fingerprint {TEXT} NOT NULL,
                    ip_address {TEXT} NOT NULL,
                    user_agent {TEXT},
                    timezone {TEXT},
                    screen_resolution {TEXT},
                    canvas_fp {TEXT},
                    audio_fp {TEXT},
                    local_id {TEXT},
                    verified_at {TIMESTAMP} NOT NULL,
                    last_seen {TIMESTAMP},
                    is_blocked {INTEGER} DEFAULT 0
                )
            """)
            
            # جدول محاولات التحقق
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS verification_attempts (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL,
                    fingerprint {TEXT} NOT NULL,
                    ip_address {TEXT} NOT NULL,
                    attempt_time {TIMESTAMP} NOT NULL,
                    status {TEXT} NOT NULL,
                    reason {TEXT}
                )
            """)
            
            # جدول tokens التحقق
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS verification_tokens (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL,
                    token {TEXT} NOT NULL UNIQUE,
                    created_at {TIMESTAMP} NOT NULL,
                    expires_at {TIMESTAMP} NOT NULL,
                    used {INTEGER} DEFAULT 0
                )
            """)
            
            # جدول إعدادات النظام
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id {AUTOINCREMENT},
                    setting_key {TEXT} NOT NULL UNIQUE,
                    setting_value {TEXT} NOT NULL,
                    updated_at {TIMESTAMP} NOT NULL,
                    updated_by {BIGINT}
                )
            """)
            
            # جدول جوائز العجلة
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS wheel_prizes (
                    id {AUTOINCREMENT},
                    name {TEXT} NOT NULL,
                    value {REAL} NOT NULL,
                    probability {REAL} NOT NULL,
                    color {TEXT} NOT NULL,
                    emoji {TEXT} NOT NULL,
                    is_active {INTEGER} DEFAULT 1,
                    position {INTEGER} DEFAULT 0,
                    added_at {TIMESTAMP} NOT NULL,
                    updated_at {TIMESTAMP}
                )
            """)
            
            # جدول السجلات
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id {AUTOINCREMENT},
                    user_id {BIGINT} NOT NULL,
                    action {TEXT} NOT NULL,
                    details {TEXT},
                    ip_address {TEXT},
                    timestamp {TIMESTAMP} NOT NULL
                )
            """)
            
            # جدول الجلسات النشطة
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS active_sessions (
                    session_id {TEXT} PRIMARY KEY,
                    user_id {BIGINT} NOT NULL,
                    created_at {TIMESTAMP} NOT NULL,
                    expires_at {TIMESTAMP} NOT NULL,
                    is_valid {INTEGER} DEFAULT 1
                )
            """)
            
            # جدول إعدادات البوت
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS bot_settings (
                    setting_key {TEXT} PRIMARY KEY,
                    setting_value {TEXT} NOT NULL,
                    updated_at {TIMESTAMP} NOT NULL,
                    updated_by {BIGINT}
                )
            """)
            
            # إنشاء indexes لتحسين الأداء (فقط PostgreSQL يدعم IF NOT EXISTS بشكل كامل)
            if self.use_postgres:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_spins_user ON spins(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_tasks ON user_tasks(user_id, task_id)")
            else:
                try:
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_spins_user ON spins(user_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawals_status ON withdrawals(status)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_tasks ON user_tasks(user_id, task_id)")
                except Exception as e:
                    print(f"⚠️ Index creation warning: {e}")
            
            # إضافة البيانات الافتراضية (القنوات والجوائز)
            self._insert_default_data(cursor)
            
            conn.commit()
        
        print("✅ Database initialized successfully")
    
    def _insert_default_data(self, cursor):
        """إضافة البيانات الافتراضية"""
        now = datetime.now().isoformat() if self.use_postgres else datetime.now().isoformat()
        
        # إعدادات النظام الافتراضية
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (setting_key) DO NOTHING
            """, ('verification_enabled', 'true', now))
            
            cursor.execute("""
                INSERT INTO bot_settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (setting_key) DO NOTHING
            """, ('auto_withdrawal_enabled', 'false', now))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO system_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
            """, ('verification_enabled', 'true', now))
            
            cursor.execute("""
                INSERT OR IGNORE INTO bot_settings (setting_key, setting_value, updated_at)
                VALUES (?, ?, ?)
            """, ('auto_withdrawal_enabled', 'false', now))
        
        # التحقق من وجود قنوات افتراضية
        cursor.execute("SELECT COUNT(*) as count FROM required_channels")
        result = cursor.fetchone()
        count = result['count'] if self.use_postgres else result[0]
        
        if count == 0:
            default_channels = [
                ('@PandaAdds', 'Panda Adds', 'https://t.me/PandaAdds', 1797127532),
                ('@CRYPTO_FLASSH', 'Crypto Flash', 'https://t.me/CRYPTO_FLASSH', 1797127532)
            ]
            
            for channel_id, name, url, admin_id in default_channels:
                if self.use_postgres:
                    cursor.execute("""
                        INSERT INTO required_channels (channel_id, channel_name, channel_url, is_active, added_by, added_at)
                        VALUES (%s, %s, %s, 1, %s, %s)
                        ON CONFLICT (channel_id) DO NOTHING
                    """, (channel_id, name, url, admin_id, now))
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO required_channels (channel_id, channel_name, channel_url, is_active, added_by, added_at)
                        VALUES (?, ?, ?, 1, ?, ?)
                    """, (channel_id, name, url, admin_id, now))
        
        # التحقق من وجود جوائز افتراضية
        cursor.execute("SELECT COUNT(*) as count FROM wheel_prizes")
        result = cursor.fetchone()
        count = result['count'] if self.use_postgres else result[0]
        
        if count == 0:
            default_prizes = [
                ('0.01 TON', 0.01, 25, '#9370db', '🪙', 0),
                ('0.05 TON', 0.05, 25, '#00bfff', '💎', 1),
                ('0.1 TON', 0.1, 25, '#ffa500', '💰', 2),
                ('0.5 TON', 0.5, 0, '#32cd32', '🏆', 3),
                ('1.0 TON', 1.0, 0, '#ff1493', '👑', 4),
                ('حظ أوفر', 0, 25, '#808080', '😔', 5)
            ]
            
            for name, value, prob, color, emoji, pos in default_prizes:
                if self.use_postgres:
                    cursor.execute("""
                        INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                    """, (name, value, prob, color, emoji, pos, now))
                else:
                    cursor.execute("""
                        INSERT INTO wheel_prizes (name, value, probability, color, emoji, position, is_active, added_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                    """, (name, value, prob, color, emoji, pos, now))
    
    def close(self):
        """إغلاق الاتصال بقاعدة البيانات"""
        if self.use_postgres and self.connection_pool:
            self.connection_pool.closeall()
            print("🔒 PostgreSQL connection pool closed")


# إنشاء instance عام من DatabaseManager
db_manager = DatabaseManager()


# دوال مساعدة للتوافق مع الكود القديم
def get_db_connection():
    """دالة للتوافق مع الكود القديم"""
    return db_manager.get_connection()


def init_database():
    """دالة للتوافق مع الكود القديم"""
    db_manager.init_database()
