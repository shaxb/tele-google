# Deployment Checklist

**Project:** Tele-Google (Telegram Marketplace Search Engine)  
**Status:** ✅ Ready for Deployment  
**Date:** February 10, 2026

## Pre-Deployment Verification

### ✅ Code Quality
- [x] Removed unused code and dependencies
- [x] Cleaned up helper functions (kept only used ones)
- [x] Removed temporary files (check_sessions.py, nul, test sessions)
- [x] No hardcoded credentials in source code
- [x] All imports are necessary and used
- [x] No TODO/FIXME markers in production code

### ✅ Configuration
- [x] `.env.template` up-to-date and documented
- [x] Removed Meilisearch references from config
- [x] `.gitignore` protects sensitive files (.env, sessions, logs)
- [x] `BOT_ADMIN_USER_IDS` uses correct JSON array format
- [x] Database configuration ready (PostgreSQL + pgvector)

### ✅ Documentation
- [x] README.md updated with correct architecture
- [x] Installation steps verified
- [x] Project structure reflects actual codebase
- [x] Roadmap updated to show MVP complete status
- [x] Removed outdated Meilisearch references from main docs

### ✅ Entry Points
- [x] `run_bot.py` - No errors, ready to run
- [x] `run_crawler.py` - No errors, ready to run
- [x] `backfill.py` - Working utility script
- [x] `clear_data.py` - Working utility script

### ✅ Database
- [x] Alembic migrations configured
- [x] PostgreSQL with pgvector in docker-compose.yml
- [x] Session management handled correctly
- [x] Foreign key constraints properly set

### ✅ Features Implemented
- [x] Multi-channel monitoring
- [x] AI-powered listing detection (GPT-4o-mini)
- [x] Semantic search with embeddings (text-embedding-3-small)
- [x] pgvector similarity search
- [x] AI result reranking
- [x] Multi-language bot interface (Uzbek/Russian/English)
- [x] Admin commands (/addchannel, /removechannel, /listchannels, /backfill)
- [x] Automatic backfill when adding channels
- [x] Channel hot-reload (no restart needed)

### ✅ Security
- [x] No credentials in git repository
- [x] `.env` file gitignored
- [x] Session files gitignored
- [x] Admin commands restricted by user ID
- [x] Database credentials not hardcoded
- [x] API keys loaded from environment

## Deployment Steps

### 1. Server Setup (AWS EC2)
```bash
# Connect to server
ssh -i ~/.ssh/questpath-aws-key.pem ubuntu@13.60.84.34

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Install Python 3.10+
sudo apt install python3.10 python3.10-venv python3-pip -y
```

### 2. Project Deployment
```bash
# Clone repository
git clone <repository-url> tele-google
cd tele-google

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.template .env
nano .env  # Fill in actual credentials

# Setup channels
nano channels.txt  # Add channel usernames

# Start database
docker-compose up -d

# Wait for database to be ready
sleep 10

# Run migrations
alembic upgrade head

# Create systemd services (see below)
```

### 3. Systemd Service Files

**Bot Service:** `/etc/systemd/system/tele-google-bot.service`
```ini
[Unit]
Description=Tele-Google Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tele-google
Environment=PATH=/home/ubuntu/tele-google/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/tele-google/venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Crawler Service:** `/etc/systemd/system/tele-google-crawler.service`
```ini
[Unit]
Description=Tele-Google Crawler
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tele-google
Environment=PATH=/home/ubuntu/tele-google/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/tele-google/venv/bin/python run_crawler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4. Start Services
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable tele-google-bot
sudo systemctl enable tele-google-crawler

# Start services
sudo systemctl start tele-google-bot
sudo systemctl start tele-google-crawler

# Check status
sudo systemctl status tele-google-bot
sudo systemctl status tele-google-crawler

# View logs
sudo journalctl -u tele-google-bot -f
sudo journalctl -u tele-google-crawler -f
```

### 5. Telegram Authentication
```bash
# First time: authenticate crawler
sudo systemctl stop tele-google-crawler
cd /home/ubuntu/tele-google
source venv/bin/activate
python run_crawler.py
# Enter phone number and SMS code when prompted
# After successful auth, session is saved
# Ctrl+C to stop

# Restart crawler service
sudo systemctl start tele-google-crawler
```

## Post-Deployment Verification

### Check Services
```bash
# Services running
sudo systemctl status tele-google-bot
sudo systemctl status tele-google-crawler

# Database running
docker ps | grep postgres

# View logs
tail -f logs/app.log
```

### Test Bot Commands
1. Start bot: `/start`
2. Search: Send any query (e.g., "iPhone 15")
3. Admin: `/listchannels` (if configured as admin)
4. Language: `/language`

### Monitor Performance
```bash
# CPU/Memory usage
htop

# Docker stats
docker stats

# Disk usage
df -h

# Database size
docker exec -it tele-google-postgres psql -U postgres -d tele_google -c "SELECT pg_size_pretty(pg_database_size('tele_google'));"
```

## Maintenance Commands

```bash
# Restart services
sudo systemctl restart tele-google-bot
sudo systemctl restart tele-google-crawler

# View logs
sudo journalctl -u tele-google-bot --since "1 hour ago"
sudo journalctl -u tele-google-crawler --since "1 hour ago"

# Backfill new channel
cd /home/ubuntu/tele-google
source venv/bin/activate
python backfill.py --channel @NewChannel --limit 100

# Clear database (careful!)
python clear_data.py

# Database backup
docker exec tele-google-postgres pg_dump -U postgres tele_google > backup_$(date +%Y%m%d).sql

# Database restore
docker exec -i tele-google-postgres psql -U postgres tele_google < backup_20260210.sql
```

## Environment Variables Required

```env
TELEGRAM_API_ID=         # From my.telegram.org
TELEGRAM_API_HASH=       # From my.telegram.org
TELEGRAM_PHONE=          # +998... format
OPENAI_API_KEY=          # OpenAI API key
OPENAI_MODEL=gpt-4o-mini
BOT_TOKEN=               # From @BotFather
BOT_ADMIN_USER_IDS=[...]  # JSON array of admin user IDs
DB_HOST=localhost
DB_PORT=5433
DB_NAME=tele_google
DB_USER=postgres
DB_PASSWORD=postgres
LOG_LEVEL=INFO
```

## Known Issues & Solutions

### Issue: Crawler not authenticating
**Solution:** Run crawler manually first time to enter SMS code, then restart service

### Issue: Database locked error
**Solution:** Each backfill creates temporary session, should not happen in current version

### Issue: Search returns no results
**Solution:** 
1. Check if crawler is running: `sudo systemctl status tele-google-crawler`
2. Check database has listings: `docker exec -it tele-google-postgres psql -U postgres -d tele_google -c "SELECT COUNT(*) FROM listings;"`
3. Run backfill: `python backfill.py --limit 50`

### Issue: Bot not responding
**Solution:**
1. Check bot service: `sudo systemctl status tele-google-bot`
2. Check logs: `sudo journalctl -u tele-google-bot -n 50`
3. Verify BOT_TOKEN in .env
4. Restart: `sudo systemctl restart tele-google-bot`

## Success Criteria

- ✅ Bot responds to `/start` command
- ✅ Search returns relevant results
- ✅ Crawler indexes new messages in real-time
- ✅ Admin commands work for authorized users
- ✅ No errors in logs
- ✅ Database growing with new listings
- ✅ Services auto-restart on failure

---

**Ready for Production:** ✅ YES

All checks passed. System is clean, documented, and ready for deployment.
