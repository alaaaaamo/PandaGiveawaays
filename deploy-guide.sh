#!/bin/bash
# Quick Deploy Script

echo "🐼 Panda Giveaways - Quick Deploy Guide"
echo "======================================"
echo ""

echo "📋 Pre-deployment Checklist:"
echo "✅ Repository uploaded to GitHub"
echo "✅ Environment variables ready"  
echo "✅ Bot token obtained"
echo "✅ Database configured"
echo ""

echo "🌐 STEP 1: Deploy Frontend to Vercel"
echo "1. Go to vercel.com and login"
echo "2. Click 'New Project'"
echo "3. Import your GitHub repository"
echo "4. Vercel will auto-detect vercel.json"
echo "5. Click Deploy"
echo "6. Your site will be: https://panda-giveawaays.vercel.app"
echo ""

echo "🖥️ STEP 2: Deploy Backend to Render"  
echo "1. Go to render.com and login"
echo "2. Click 'New Web Service'"
echo "3. Connect your GitHub repository"
echo "4. Render will auto-detect render.yaml"
echo "5. Add environment variables:"
echo "   - BOT_TOKEN=your_bot_token"
echo "   - DATABASE_URL=your_database_url"
echo "   - MINI_APP_URL=https://panda-giveawaays.vercel.app"
echo "   - ADMIN_IDS=1797127532,6603009212"
echo "6. Click Deploy"
echo ""

echo "🔗 STEP 3: Configure Bot"
echo "1. Open @BotFather in Telegram"
echo "2. Set Mini App URL: https://panda-giveawaays.vercel.app"
echo "3. Test bot commands"
echo ""

echo "✅ Deployment Complete!"
echo "Frontend: https://panda-giveawaays.vercel.app"
echo "Backend:  https://pandagiveawaays.onrender.com"
echo ""

echo "📞 Support: Check README-DEPLOYMENT.md for troubleshooting"