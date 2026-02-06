#!/bin/bash
# Render Start Script - Backend API Server only (Frontend on Vercel)

echo "🐼 Starting Panda Giveaways Backend Services..."

# Start Flask web server (البوت هيشتغل تلقائياً من app.py)
echo "🌐 Starting Flask API Server on port $PORT..."
echo "📱 Frontend running on: https://panda-giveawaays.vercel.app"
exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
