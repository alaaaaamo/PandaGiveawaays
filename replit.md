# Panda Giveaways Bot

## Overview
Telegram Mini App with Python/Flask backend, SQLite database, and static HTML/CSS/JS frontend. Originally built for Vercel/Render, now fully migrated to Replit.

## Architecture
- **Backend**: Flask (Python) served via gunicorn on port 5000
- **Frontend**: Static HTML/CSS/JS in `public/` directory, served by Flask
- **Database**: SQLite (`panda_giveaways.db`)
- **Bot**: `panda_giveaways_bot.py` runs as a subprocess from Flask

## Key Files
- `app.py` - Flask backend with all API endpoints
- `panda_giveaways_bot.py` - Telegram bot logic
- `public/index.html` - Main Mini App UI
- `public/admin.html` - Admin dashboard
- `public/referral-program.html` - Referral program page
- `public/fp.html` - Fingerprint verification page
- `public/js/config.js` - Frontend config (API_BASE_URL, TelegramApp, UserState, etc.)
- `public/js/app.js` - Main app logic
- `public/js/debug.js` - Debug/error handling utilities
- `public/js/wheel.js` - Spin wheel canvas logic
- `public/js/api.js` - API client
- `public/js/tasks.js` - Tasks page logic
- `public/js/channels.js` - Channel verification logic
- `public/js/channels-check.js` - Channel subscription checking
- `public/css/styles.css` - Main stylesheet
- `public/css/tasks.css` - Tasks page styles
- `public/css/channels-check.css` - Channel modal styles
- `public/css/admin.css` - Admin dashboard styles

## Design Theme
Modern olive/earthy color scheme:
- Primary bg: `#1a1f16` (dark olive)
- Secondary bg: `#232b1e`
- Card bg: `#2d3627`
- Text: `#f0ece4` / `#a0997e`
- Accent: `#b5a642` (olive gold)
- Success: `#6b8e23` (olive green)
- Error: `#c44536`
- Border: `#3d4a33`

Uses inline SVG icons throughout for minimal JS overhead. Lottie player dependency removed from main index.html.

## Configuration
- `BOT_TOKEN` - Required secret for Telegram bot
- API endpoints use relative `/api` paths (same-origin)
- CORS configured for all origins
- Flask serves static files from `public/` directory

## Workflow
- `Start application`: `gunicorn app:app --bind 0.0.0.0:5000 --workers 1 --threads 2 --timeout 120`
