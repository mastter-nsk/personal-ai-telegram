# Personal AI Assistant for Telegram — v0.1

Current milestone:

- private owner-only Telegram bot
- PostgreSQL persistence
- OpenAI Responses API text chat
- conversation history
- `/new` starts a fresh conversation
- automatic database schema initialization

## Required environment variables

- `TELEGRAM_BOT_TOKEN`
- `OWNER_TELEGRAM_ID`
- `OPENAI_API_KEY`
- `DATABASE_URL`

## Optional variables

- `BOT_NAME`
- `OWNER_NAME`
- `PERSONALITY`
- `INTERESTS`
- `TIMEZONE`
- `OPENAI_MODEL` (default: `gpt-5.6-luna`)
- `CONTEXT_MESSAGES` (default: `20`)

## Railway

Set:

`DATABASE_URL=${{Postgres.DATABASE_URL}}`

Telegram long polling is used, so no public domain or webhook is required.
