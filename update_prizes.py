#!/usr/bin/env python3
"""
تحديث نسب جوائز العجلة في قاعدة البيانات
Update wheel prize probabilities to: 25% each for 0.01, 0.05, 0.1, حظ أوفر
"""
import sqlite3
import os
from datetime import datetime

def update_prizes():
    db_path = 'panda_giveaways.db'
    
    if not os.path.exists(db_path):
        print("❌ قاعدة البيانات غير موجودة. سيتم إنشاؤها عند تشغيل البوت أول مرة.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # التحقق من وجود الجدول
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wheel_prizes'")
    if not cursor.fetchone():
        print("❌ جدول wheel_prizes غير موجود")
        conn.close()
        return
    
    # طباعة النسب الحالية
    print("\n📊 النسب الحالية:")
    cursor.execute("SELECT name, value, probability FROM wheel_prizes WHERE is_active = 1 ORDER BY position")
    current_prizes = cursor.fetchall()
    for name, value, prob in current_prizes:
        print(f"  {name}: {prob}%")
    
    # النسب الجديدة
    new_probabilities = {
        0.01: 25,    # 0.01 TON
        0.05: 25,    # 0.05 TON
        0.1: 25,     # 0.1 TON
        0.5: 0,      # 0.5 TON
        1.0: 0,      # 1.0 TON
        0: 25        # حظ أوفر (value = 0)
    }
    
    # تحديث النسب
    now = datetime.now().isoformat()
    updated_count = 0
    
    for value, new_prob in new_probabilities.items():
        if value == 0:
            # حالة خاصة لـ "حظ أوفر"
            cursor.execute("""
                UPDATE wheel_prizes 
                SET probability = ?, updated_at = ?
                WHERE value = ? AND name LIKE '%حظ%' AND is_active = 1
            """, (new_prob, now, value))
        else:
            cursor.execute("""
                UPDATE wheel_prizes 
                SET probability = ?, updated_at = ?
                WHERE value = ? AND is_active = 1
            """, (new_prob, now, value))
        
        updated_count += cursor.rowcount
    
    conn.commit()
    
    # طباعة النسب الجديدة
    print("\n✅ النسب الجديدة:")
    cursor.execute("SELECT name, value, probability FROM wheel_prizes WHERE is_active = 1 ORDER BY position")
    updated_prizes = cursor.fetchall()
    for name, value, prob in updated_prizes:
        print(f"  {name}: {prob}%")
    
    total_prob = sum(prob for _, _, prob in updated_prizes)
    print(f"\n📌 المجموع الكلي: {total_prob}%")
    
    if total_prob == 100:
        print("✅ النسب صحيحة!")
    else:
        print(f"⚠️ تحذير: المجموع = {total_prob}% (يجب أن يكون 100%)")
    
    print(f"\n✅ تم تحديث {updated_count} جائزة")
    conn.close()

if __name__ == '__main__':
    try:
        update_prizes()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
