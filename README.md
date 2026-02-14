# Tele-Google

**Telegram Marketplace Search Engine**

A real-time search engine that indexes public Telegram marketplace channels and makes their content searchable through a Telegram bot. Built for the Uzbekistan marketplace ecosystem.

## 🎯 Key Features

- 🔍 **Natural Language Search** - Search in Uzbek/Russian with typo tolerance
- 🤖 **AI-Powered Extraction** - Smart categorization and data extraction using GPT-4o-mini
- ⚡ **Real-time Indexing** - Instant indexing of new marketplace messages
- 🎨 **Rich Results** - Get results with images, prices, and direct channel links
- 📊 **Multi-Category Support** - Electronics, Real Estate, Vehicles, Jobs, and more

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker Desktop
- Telegram account
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/shaxb/tele-google.git
   cd tele-google
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or
   source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.template .env
   # Edit .env with your credentials
   ```

5. **Start Docker services**
   ```bash
   docker-compose up -d
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Add channels to monitor**
   ```bash
   # Edit channels.txt and add channel usernames (one per line)
   # Example:
   # @MalikaBozor
   # @ToshkentMarket
   ```

8. **Run the application**
   ```bash
   # Terminal 1: Start crawler
   python run_crawler.py

   # Terminal 2: Start bot  
   python run_bot.py
   ```

## 📖 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Server deployment guide

## 🏗️ Architecture

```
Telegram Channels → Telethon Crawler → AI Pipeline → PostgreSQL (pgvector) → Bot → Users
                                        ├─ GPT-4o-mini (Listing Detection)
                                        ├─ Embeddings (Semantic Search)
                                        └─ AI Reranking (Result Quality)
```

**AI-Powered Search Pipeline:**
1. **Listing Detection** - AI classifies marketplace messages
2. **Semantic Embeddings** - Converts text to 1536-dim vectors
3. **Vector Search** - pgvector finds similar listings
4. **AI Reranking** - Reorders results by relevance

## 🛠️ Tech Stack

- **Crawler**: Telethon (User client for channel monitoring)
- **AI**: OpenAI GPT-4o-mini + text-embedding-3-small
- **Database**: PostgreSQL + pgvector extension
- **Bot**: Aiogram 3.x
- **Language**: Python 3.10+

## 📝 Configuration

Key environment variables (see [.env.template](.env.template)):

```env
# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+998901234567

# OpenAI
OPENAI_API_KEY=sk-...

# Bot
BOT_TOKEN=your_bot_token
BOT_ADMIN_USER_IDS=[your_user_id]
```

## 📦 Project Structure

```
tele-google/
├── src/
│   ├── ai_parser.py          # AI listing detection & reranking
│   ├── embeddings.py         # OpenAI embedding generation
│   ├── crawler.py            # Telethon message listener
│   ├── search_engine.py      # pgvector search pipeline
│   ├── bot.py                # Aiogram bot interface
│   ├── config.py             # Pydantic settings loader
│   ├── prompts.py            # AI prompt templates
│   ├── i18n.py               # Multi-language support
│   ├── database/
│   │   ├── connection.py     # Async SQLAlchemy engine
│   │   ├── models.py         # ORM models (Listing, Channel, etc.)
│   │   └── repository.py     # Data-access layer
│   ├── bot_utils/
│   │   ├── admin.py          # Admin bot commands
│   │   ├── formatters.py     # Result & UI formatting
│   │   └── language.py       # Per-user language prefs
│   ├── utils/
│   │   ├── channels.py       # Channel-file management
│   │   └── logger.py         # Loguru setup
│   └── locales/              # en/ru/uz translation JSONs
├── migrations/               # Alembic database migrations
├── data/sessions/            # Telegram session files (gitignored)
├── logs/                     # Application logs (gitignored)
├── channels.txt              # Monitored channels list
├── backfill.py               # Historical message indexing
├── clear_data.py             # Database cleanup utility
├── run_bot.py                # Bot entry point
├── run_crawler.py            # Crawler entry point
└── docker-compose.yml        # PostgreSQL + pgvector service
```

## 🎯 Roadmap

- [x] Architecture design
- [x] Database schema (PostgreSQL + pgvector)
- [x] AI pipeline implementation (Listing detection + Reranking)
- [x] Crawler development (Telethon multi-channel monitoring)
- [x] Search engine (Semantic search with embeddings)
- [x] Bot interface (Aiogram with multi-language support)
- [x] Admin commands (Channel management via bot)
- [ ] Production deployment
- [ ] Performance optimization
- [ ] Analytics dashboard

See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for detailed implementation roadmap.

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome!

## 📄 License

MIT License - feel free to use this project as inspiration for your own marketplace search solutions.

## 🔗 Links

- [Get Telegram API Credentials](https://my.telegram.org/apps)
- [OpenAI Platform](https://platform.openai.com/)
- [pgvector Extension](https://github.com/pgvector/pgvector)
- [Telethon Docs](https://docs.telethon.dev/)
- [Aiogram Docs](https://docs.aiogram.dev/)

## 📧 Contact

For questions or suggestions, open an issue on GitHub.

---

**Status**: ✅ Ready for Deployment (MVP Complete)



sudo journalctl -u tele-google-bot -f       # live bot logs
sudo journalctl -u tele-google-crawler -f    # live crawler logs
sudo systemctl restart tele-google-bot       # restart bot
sudo systemctl restart tele-google-crawler   # restart crawler