#!/bin/bash
set -e

echo "🎯 Tele-Google Initial Setup"
echo "===================================="
echo ""

# Check if running as ubuntu user
if [ "$USER" != "ubuntu" ]; then
    echo "⚠️  This script should be run as 'ubuntu' user"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "🔧 Installing required packages..."

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo "✅ Docker already installed"
    sudo apt install -y git python3 python3-venv python3-pip
else
    echo "Installing Docker and dependencies..."
    sudo apt install -y git python3 python3-venv python3-pip docker.io docker-compose
fi

# Setup Docker permissions
echo "🐳 Configuring Docker..."
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl start docker

echo "⚠️  IMPORTANT: You need to logout and login again for Docker group to take effect!"
echo "    After re-login, run: docker ps (should work without sudo)"
echo ""
read -p "Press Enter to continue with Python setup..."

# Check if repository exists
if [ ! -d "/home/ubuntu/tele-google" ]; then
    echo ""
    echo "📥 Repository not found. Please clone it first:"
    echo "    git clone <YOUR_REPO_URL> /home/ubuntu/tele-google"
    exit 1
fi

cd /home/ubuntu/tele-google

# Setup Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup .env
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.template .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file with your configuration:"
    echo "    nano .env"
    echo ""
    echo "    Required values:"
    echo "    - TELEGRAM_API_ID (from https://my.telegram.org/apps)"
    echo "    - TELEGRAM_API_HASH (from https://my.telegram.org/apps)"
    echo "    - TELEGRAM_PHONE (+998901234567)"
    echo "    - OPENAI_API_KEY (sk-...)"
    echo "    - BOT_TOKEN (from @BotFather)"
    echo "    - BOT_ADMIN_USER_IDS ([123456789])"
    echo ""
    read -p "Press Enter after you've configured .env..."
else
    echo "✅ .env file already exists"
fi

# Setup channels.txt
if [ ! -f "channels.txt" ]; then
    echo "📋 Creating channels.txt..."
    touch channels.txt
    echo ""
    echo "⚠️  Add channels to monitor (one per line):"
    echo "    nano channels.txt"
    echo ""
    echo "    Example:"
    echo "    @channel1"
    echo "    @channel2"
    echo "    channel3"
    echo ""
    read -p "Press Enter after you've added channels..."
else
    echo "✅ channels.txt already exists"
fi

# Start PostgreSQL
echo "🗄️  Starting PostgreSQL container..."
docker-compose up -d

echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Run migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Create session directory
mkdir -p data/sessions

# Authenticate Telegram
echo ""
echo "🔐 Telegram Session Authentication"
echo "===================================="
echo "⚠️  You need to authenticate the Telegram crawler session."
echo "    This will send an SMS code to your phone."
echo ""
read -p "Press Enter to start authentication..."

python run_crawler.py &
CRAWLER_PID=$!

echo ""
echo "⚠️  After entering the SMS code and seeing '✅ Session authenticated', press Ctrl+C"
echo ""

wait $CRAWLER_PID || true

# Verify session file
if [ -f "data/sessions/test_session.session" ]; then
    echo "✅ Session file created successfully"
    
    # Backup session
    echo "💾 Creating backup of session file..."
    cp data/sessions/test_session.session ~/session_backup.session
    echo "✅ Session backed up to: ~/session_backup.session"
else
    echo "❌ Session file not found. Authentication may have failed."
    echo "   Please run: python run_crawler.py and enter SMS code"
    exit 1
fi

# Create systemd services
echo ""
echo "🔧 Creating systemd services..."

# Bot service
sudo tee /etc/systemd/system/tele-google-bot.service > /dev/null <<EOF
[Unit]
Description=Tele-Google Telegram Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tele-google
Environment="PATH=/home/ubuntu/tele-google/venv/bin:/usr/bin"
ExecStart=/home/ubuntu/tele-google/venv/bin/python run_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Crawler service
sudo tee /etc/systemd/system/tele-google-crawler.service > /dev/null <<EOF
[Unit]
Description=Tele-Google Channel Crawler
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tele-google
Environment="PATH=/home/ubuntu/tele-google/venv/bin:/usr/bin"
ExecStart=/home/ubuntu/tele-google/venv/bin/python run_crawler.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable tele-google-bot
sudo systemctl enable tele-google-crawler
sudo systemctl start tele-google-bot
sudo systemctl start tele-google-crawler

# Wait for services to start
sleep 5

# Check status
echo ""
echo "✅ Checking service status..."
echo "===================================="
sudo systemctl status tele-google-bot --no-pager -l
echo ""
sudo systemctl status tele-google-crawler --no-pager -l

echo ""
echo "✨ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Test bot in Telegram: Send /start to your bot"
echo "   2. View logs: sudo journalctl -u tele-google-bot -f"
echo "   3. View logs: sudo journalctl -u tele-google-crawler -f"
echo ""
echo "🔧 Useful commands:"
echo "   Restart bot:     sudo systemctl restart tele-google-bot"
echo "   Restart crawler: sudo systemctl restart tele-google-crawler"
echo "   View status:     sudo systemctl status tele-google-bot tele-google-crawler"
echo "   View bot logs:   sudo journalctl -u tele-google-bot -f"
echo "   View all logs:   sudo journalctl -u tele-google-* -f"
echo ""
echo "🚀 For future deployments, use: bash deploy.sh"
