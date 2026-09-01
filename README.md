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
- built-in OpenAI web search when current information is needed
- Telegram voice messages → OpenAI transcription → AI reply
- Telegram photo analysis with vision
- document analysis
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
- `OPENAI_MODEL`
- `TRANSCRIPTION_MODEL`
- `CONTEXT_MESSAGES`

## Railway

Use:

`DATABASE_URL=${{Postgres.DATABASE_URL}}`

Telegram long polling is used, so no public domain or webhook is required.

## Supported Telegram input

- text messages
- voice messages
- photos with or without a caption
- PDF
- TXT / Markdown / JSON / HTML / XML
- DOC / DOCX / RTF / ODT
- PPT / PPTX
- CSV / TSV
- XLS / XLSX

Documents are passed directly to the OpenAI Responses API as file inputs.
No local document parser or additional database is required.

## Memory commands

- `/memory` — list stored memories
- `/remember I prefer concise answers` — save manually
- `/forget 3` — remove memory with ID 3

`/new` clears current conversation context but keeps long-term memory.
