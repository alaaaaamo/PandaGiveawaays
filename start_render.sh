#!/bin/bash
# Render Start Script - تشغيل السيرفر (البوت يشتغل من app.py)

echo "🐼 Starting Panda Giveaways Services..."

# Start Flask web server (البوت هيشتغل تلقائياً من app.py)
echo "🌐 Starting Flask Server on port $PORT..."
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
