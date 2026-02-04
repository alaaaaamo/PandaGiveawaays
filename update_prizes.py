#!/usr/bin/env python3
"""
تحديث نسب جوائز العجلة في قاعدة البيانات
Update wheel prize probabilities to: 25% each for 0.01, 0.05, 0.1, حظ أوفر
"""
import os
import sys
from datetime import datetime

# استيراد مدير قاعدة البيانات الجديد (يدعم PostgreSQL & SQLite)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import db_manager

def update_prizes():
    print(f"📂 Using database: {'PostgreSQL (Neon)' if db_manager.use_postgres else 'SQLite (Local)'}")
    
    # طباعة النسب الحالية
    print("\n📊 النسب الحالية:")
    current_prizes = db_manager.execute_query(
        "SELECT name, value, probability FROM wheel_prizes WHERE is_active = 1 ORDER BY position",
        fetch='all'
    )
    
    if not current_prizes:
        print("❌ لا توجد جوائز في قاعدة البيانات")
        return
    
    for prize in current_prizes:
        print(f"  {prize['name']}: {prize['probability']}%")
    
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
            db_manager.execute_query("""
                UPDATE wheel_prizes 
                SET probability = ?, updated_at = ?
                WHERE value = ? AND name LIKE '%حظ%' AND is_active = 1
            """, (new_prob, now, value))
        else:
            db_manager.execute_query("""
                UPDATE wheel_prizes 
                SET probability = ?, updated_at = ?
                WHERE value = ? AND is_active = 1
            """, (new_prob, now, value))
        
        updated_count += 1
    
    # طباعة النسب الجديدة
    print("\n✅ النسب الجديدة:")
    updated_prizes = db_manager.execute_query(
        "SELECT name, value, probability FROM wheel_prizes WHERE is_active = 1 ORDER BY position",
        fetch='all'
    )
    
    for prize in updated_prizes:
        print(f"  {prize['name']}: {prize['probability']}%")
    
    total_prob = sum(prize['probability'] for prize in updated_prizes)
    print(f"\n📌 المجموع الكلي: {total_prob}%")
    
    if total_prob == 100:
        print("✅ النسب صحيحة!")
    else:
        print(f"⚠️ تحذير: المجموع = {total_prob}% (يجب أن يكون 100%)")
    
    print(f"\n✅ تم تحديث {updated_count} جائزة")

if __name__ == '__main__':
    try:
        update_prizes()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
