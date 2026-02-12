#!/bin/bash
set -e

echo "🚀 Deploying Tele-Google..."
echo "===================================="

# Navigate to project directory
cd /home/ubuntu/tele-google

# Pull latest code
echo "📥 Pulling latest code from git..."
git pull origin main

# Activate virtual environment
echo "🐍 Activating Python virtual environment..."
source venv/bin/activate

# Update dependencies
echo "📦 Installing/updating Python dependencies..."
pip install -r requirements.txt --quiet

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart tele-google-bot
sudo systemctl restart tele-google-crawler

# Wait for services to initialize
sleep 5

# Health check
echo ""
echo "✅ Checking service status..."
echo "-----------------------------------"

if sudo systemctl is-active --quiet tele-google-bot; then
    echo "✅ Bot: Running"
else
    echo "❌ Bot: Failed"
    sudo systemctl status tele-google-bot --no-pager -l
fi

if sudo systemctl is-active --quiet tele-google-crawler; then
    echo "✅ Crawler: Running"
else
    echo "❌ Crawler: Failed"
    sudo systemctl status tele-google-crawler --no-pager -l
fi

echo ""
echo "✨ Deployment complete!"
echo ""
echo "💡 Useful commands:"
echo "   View bot logs:     sudo journalctl -u tele-google-bot -f"
echo "   View crawler logs: sudo journalctl -u tele-google-crawler -f"
echo "   Check status:      sudo systemctl status tele-google-bot tele-google-crawler"
