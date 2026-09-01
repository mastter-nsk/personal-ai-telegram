# Personal AI Assistant for Telegram — v0.1

Current milestone:

- owner-only Telegram bot
- PostgreSQL persistence
- OpenAI Responses API text chat
- conversation history
- `/new` starts a fresh conversation
- persistent long-term memory
- `/memory`
- `/remember`
- `/forget`
- automatic memory through an OpenAI function tool
- automatic database schema initialization

## Required environment variables

- `TELEGRAM_BOT_TOKEN`
- `OWNER_TELEGRAM_ID`
- `OPENAI_API_KEY`
- `DATABASE_URL`

## Railway

Use:

`DATABASE_URL=${{Postgres.DATABASE_URL}}`

Telegram long polling is used, so no public domain or webhook is required.

## Memory commands

- `/memory` — list stored memories
- `/remember I prefer concise answers` — save manually
- `/forget 3` — remove memory with ID 3

`/new` clears the current conversation context but does not delete long-term memory.
