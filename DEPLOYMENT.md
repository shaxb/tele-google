# Deployment Guide - Tele-Google

## 📋 Prerequisites

- AWS EC2 instance running Ubuntu 20.04+ (tested on Ubuntu 24.04)
- SSH key configured: `~/.ssh/questpath-aws-key.pem`
- Access to:
  - Telegram API credentials (https://my.telegram.org/apps)
  - OpenAI API key
  - Telegram Bot Token (from @BotFather)

---

## 🚀 Initial Deployment

### Step 1: Connect to Server

```bash
ssh -i ~/.ssh/questpath-aws-key.pem ubuntu@13.60.84.34
```

### Step 2: Clone Repository

```bash
cd ~
git clone <YOUR_REPOSITORY_URL> tele-google
cd tele-google
```

### Step 3: Run Setup Script

```bash
chmod +x setup.sh
bash setup.sh
```

**The setup script will:**
1. Install system dependencies (Docker, Python 3.10, etc.)
2. Create Python virtual environment
3. Install Python packages
4. Prompt you to configure `.env` file
5. Prompt you to add channels to `channels.txt`
6. Start PostgreSQL container
7. Run database migrations
8. **Ask you to authenticate Telegram session (SMS code required)**
9. Create and start systemd services

### Step 4: Verify Deployment

**Check service status:**
```bash
sudo systemctl status tele-google-bot
sudo systemctl status tele-google-crawler
```

Both should show **active (running)** in green.

**View live logs:**
```bash
# Bot logs
sudo journalctl -u tele-google-bot -f

# Crawler logs  
sudo journalctl -u tele-google-crawler -f

# All services
sudo journalctl -u tele-google-* -f
```

**Test bot:**
1. Open Telegram
2. Search for your bot
3. Send `/start` - should get welcome message
4. Send `kvartira` - should return search results

---

## 🔄 Updating (Future Deployments)

When you make changes to the code and want to deploy updates:

### Option 1: Using Deploy Script (Recommended)

```bash
ssh -i ~/.ssh/questpath-aws-key.pem ubuntu@13.60.84.34
cd ~/tele-google
bash deploy.sh
```

The deploy script will:
1. Pull latest code from git
2. Update Python dependencies
3. Run database migrations
4. Restart services
5. Verify services are running

### Option 2: Manual Steps

```bash
ssh -i ~/.ssh/questpath-aws-key.pem ubuntu@13.60.84.34
cd ~/tele-google

# Pull latest code
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart services
sudo systemctl restart tele-google-bot
sudo systemctl restart tele-google-crawler

# Check status
sudo systemctl status tele-google-bot tele-google-crawler
```

---

## 🔧 Common Tasks

### View Logs

```bash
# Last 100 lines of bot logs
sudo journalctl -u tele-google-bot -n 100

# Last 100 lines of crawler logs
sudo journalctl -u tele-google-crawler -n 100

# Live tail (follow) bot logs
sudo journalctl -u tele-google-bot -f

# Live tail both services
sudo journalctl -u tele-google-* -f

# Logs from last hour with errors
sudo journalctl -u tele-google-bot --since "1 hour ago" | grep -i error
```

### Restart Services

```bash
# Restart both
sudo systemctl restart tele-google-bot tele-google-crawler

# Restart individually
sudo systemctl restart tele-google-bot
sudo systemctl restart tele-google-crawler

# Stop services
sudo systemctl stop tele-google-bot tele-google-crawler

# Start services
sudo systemctl start tele-google-bot tele-google-crawler
```

### Update Channels

```bash
cd ~/tele-google
nano channels.txt  # Add/remove channels

# Restart crawler to reload channels
sudo systemctl restart tele-google-crawler
```

### Database Management

```bash
# Connect to PostgreSQL
docker exec -it tele-google-postgres-1 psql -U postgres -d tele_google

# Backup database
docker exec tele-google-postgres-1 pg_dump -U postgres tele_google > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i tele-google-postgres-1 psql -U postgres -d tele_google < backup_20260212.sql

# Check database size
docker exec tele-google-postgres-1 psql -U postgres -d tele_google -c "SELECT COUNT(*) FROM listings;"
```

### Run Backfill (Index Historical Messages)

```bash
cd ~/tele-google
source venv/bin/activate

# Backfill 10 messages per channel
python backfill.py --limit 10

# Backfill specific number
python backfill.py --limit 50
```

---

## 🚨 Troubleshooting

### Bot Not Responding

```bash
# Check if service is running
sudo systemctl status tele-google-bot

# View recent logs
sudo journalctl -u tele-google-bot -n 50

# Restart service
sudo systemctl restart tele-google-bot

# Check for errors in .env
cat .env | grep BOT_TOKEN
```

### Crawler Not Monitoring Channels

```bash
# Check crawler status
sudo systemctl status tele-google-crawler

# View logs
sudo journalctl -u tele-google-crawler -n 50

# Verify session file exists
ls -lah ~/tele-google/data/sessions/

# If session missing, re-authenticate:
cd ~/tele-google
source venv/bin/activate
python run_crawler.py
# Enter SMS code, then Ctrl+C
sudo systemctl restart tele-google-crawler
```

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs tele-google-postgres-1

# Restart PostgreSQL
docker-compose restart

# Verify connection
docker exec tele-google-postgres-1 pg_isready -U postgres
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker images
docker system prune -a

# Clean old logs
sudo journalctl --vacuum-time=7d

# Check large files
du -sh ~/tele-google/*
```

### Services Keep Crashing

```bash
# View crash logs
sudo journalctl -u tele-google-bot --since "1 hour ago"
sudo journalctl -u tele-google-crawler --since "1 hour ago"

# Common issues:
# 1. Missing .env variables
# 2. Invalid API keys
# 3. Database not running
# 4. Session file deleted

# Stop auto-restart to debug
sudo systemctl stop tele-google-bot
cd ~/tele-google
source venv/bin/activate
python run_bot.py  # Run manually to see errors
```

---

## 📊 Monitoring

### Check Service Health

```bash
# All systemd services
sudo systemctl status tele-google-*

# Quick check if running
sudo systemctl is-active tele-google-bot && echo "Bot: OK" || echo "Bot: Failed"
sudo systemctl is-active tele-google-crawler && echo "Crawler: OK" || echo "Crawler: Failed"
```

### Resource Usage

```bash
# Memory usage
free -h

# Disk usage
df -h

# Check which process uses memory
ps aux --sort=-%mem | head -10

# CPU usage
top -bn1 | head -20
```

### Database Stats

```bash
# Count listings
docker exec tele-google-postgres-1 psql -U postgres -d tele_google -c "
  SELECT COUNT(*) as total_listings FROM listings;
"

# Listings by channel
docker exec tele-google-postgres-1 psql -U postgres -d tele_google -c "
  SELECT source_channel, COUNT(*) as count 
  FROM listings 
  GROUP BY source_channel 
  ORDER BY count DESC;
"

# Database size
docker exec tele-google-postgres-1 psql -U postgres -d tele_google -c "
  SELECT pg_size_pretty(pg_database_size('tele_google'));
"
```

---

## 💾 Backup & Recovery

### Create Backup

```bash
# Database
docker exec tele-google-postgres-1 pg_dump -U postgres tele_google > \
  ~/backups/db_$(date +%Y%m%d_%H%M%S).sql

# Session files
tar -czf ~/backups/sessions_$(date +%Y%m%d).tar.gz \
  ~/tele-google/data/sessions/

# Full application backup (excluding venv)
tar -czf ~/backups/tele-google_$(date +%Y%m%d).tar.gz \
  --exclude='venv' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  ~/tele-google/
```

### Restore from Backup

```bash
# Restore database
docker exec -i tele-google-postgres-1 psql -U postgres -d tele_google < \
  ~/backups/db_20260212.sql

# Restore sessions
tar -xzf ~/backups/sessions_20260212.tar.gz -C ~/

# Restart services after restore
sudo systemctl restart tele-google-bot tele-google-crawler
```

### Automated Backups (Optional)

Create backup script:
```bash
nano ~/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
mkdir -p $BACKUP_DIR

# Backup database
docker exec tele-google-postgres-1 pg_dump -U postgres tele_google > \
  "$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql"

# Backup sessions
tar -czf "$BACKUP_DIR/sessions_$(date +%Y%m%d).tar.gz" \
  /home/ubuntu/tele-google/data/sessions/

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed at $(date)"
```

Make executable and add to cron:
```bash
chmod +x ~/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line: 0 2 * * * /home/ubuntu/backup.sh >> /home/ubuntu/backup.log 2>&1
```

---

## 🔐 Security Notes

- `.env` file contains sensitive credentials - never commit to git
- Session files contain authentication - back them up securely
- PostgreSQL only accessible from localhost (127.0.0.1:5433)
- Consider setting up UFW firewall:
  ```bash
  sudo ufw allow ssh
  sudo ufw enable
  ```

---

## 📞 Support

- **Logs location:** `sudo journalctl -u tele-google-*`
- **Configuration:** `~/tele-google/.env`
- **Channels:** `~/tele-google/channels.txt`
- **Session backup:** `~/session_backup.session`

---

**Last Updated:** February 12, 2026
