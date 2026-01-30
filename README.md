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

6. **Initialize database**
   ```bash
   python scripts/init_db.py
   ```

7. **Run the application**
   ```bash
   # Terminal 1: Start crawler
   python src/crawler.py

   # Terminal 2: Start bot
   python src/bot.py
   ```

## 📖 Documentation

- [PROJECT_GUIDE.md](PROJECT_GUIDE.md) - Complete architecture and development guide
- [scatch-idea.md](scatch-idea.md) - Original project concept

## 🏗️ Architecture

```
Telegram Channels → Telethon Crawler → AI Pipeline → Meilisearch → Bot → Users
                                        ├─ Router AI
                                        └─ Specialist AI
```

**Two-Stage AI Pipeline:**
1. **Router AI** - Classifies messages into categories
2. **Specialist AI** - Extracts structured data with category-specific prompts

## 🛠️ Tech Stack

- **Crawler**: Telethon (Multi-session support)
- **AI**: OpenAI GPT-4o-mini
- **Search**: Meilisearch (Typo-tolerant, fast filtering)
- **Database**: PostgreSQL
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

# Channels to monitor
CHANNELS=@MalikaBozor,@ToshkentMarket
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

## 📦 Project Structure

```
tele-google/
├── src/
│   ├── ai_parser.py      # Two-stage AI pipeline
│   ├── crawler.py        # Telethon message listener
│   ├── search.py         # Meilisearch wrapper
│   ├── bot.py            # Aiogram bot interface
│   ├── config.py         # Configuration loader
│   ├── schemas.py        # Category schemas
│   └── prompts.py        # AI prompt templates
├── scripts/              # Utility scripts
├── tests/                # Test files
├── data/                 # Persistent data (gitignored)
└── docker-compose.yml    # Docker services
```

## 🎯 Roadmap

- [x] Architecture design
- [x] Project setup
- [ ] AI pipeline implementation
- [ ] Crawler development
- [ ] Search engine integration
- [ ] Bot interface
- [ ] Testing & optimization
- [ ] Deployment

See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for detailed implementation roadmap.

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome!

## 📄 License

MIT License - feel free to use this project as inspiration for your own marketplace search solutions.

## 🔗 Links

- [Get Telegram API Credentials](https://my.telegram.org/apps)
- [OpenAI Platform](https://platform.openai.com/)
- [Meilisearch Docs](https://www.meilisearch.com/docs)
- [Telethon Docs](https://docs.telethon.dev/)
- [Aiogram Docs](https://docs.aiogram.dev/)

## 📧 Contact

For questions or suggestions, open an issue on GitHub.

---

**Status**: 🚧 In Development (Phase 1 Complete)
