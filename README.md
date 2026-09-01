# Personal AI Assistant for Telegram — v0.1 core

Current milestone: secure Telegram owner whitelist + PostgreSQL initialization.
OpenAI handlers are intentionally not wired yet.

## Required environment variables

- `TELEGRAM_BOT_TOKEN`
- `OWNER_TELEGRAM_ID`
- `OPENAI_API_KEY`
- `DATABASE_URL`

## Local run

1. Copy `.env.example` to `.env`
2. Fill the required values
3. Create a PostgreSQL database and put its connection URL in `DATABASE_URL`
4. Install dependencies:
   `pip install -r requirements.txt`
5. Run:
   `python main.py`

At startup the application automatically creates its PostgreSQL tables.

## Current behavior

- `/start` from the owner creates/updates the owner record and confirms DB connectivity.
- Updates from any other Telegram account are silently rejected by an update-level outer middleware.
- No OpenAI call exists yet, so this milestone can be tested without spending API credits.
