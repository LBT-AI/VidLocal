# VidLocal Monorepo

VidLocal automates video localization: download from Facebook/TikTok → transcribe → translate → TTS → render → upload to YouTube.

## Structure

```
├── backend/               # FastAPI + Celery + Telegram bot
│   ├── app/               # Python application code
│   ├── alembic/           # Database migrations
│   └── requirements.txt
├── apps/
│   └── telegram-mini/     # Telegram Mini App (Vite + React)
├── frontend/
│   └── web-admin/         # Web admin panel (Next.js)
├── docs/                  # Documentation
├── docker-compose.yml     # All services
└── .env.example           # Environment template
```

## Quick Start

### Backend (Docker)
```bash
docker compose up -d
```

### Telegram Mini App
```bash
cd apps/telegram-mini
npm install
npm run dev
```

### Web Admin
```bash
cd frontend/web-admin
npm install
npm run dev
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI backend |
| Worker | - | Celery async tasks |
| Bot | - | Telegram bot |
| Frontend | 3002 | Web admin panel |
| Mini App | 3000 | Telegram Mini App |
| PostgreSQL | 5432 | Database |
| Redis | 6380 | Message broker |
