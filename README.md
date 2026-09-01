# Personal AI Assistant for Telegram

Your own private AI assistant in Telegram with persistent memory, web search,
voice transcription, vision, and document understanding.

Designed to deploy on Railway with a Python service + PostgreSQL.

## v0.1 features

- private access restricted to `OWNER_TELEGRAM_ID`
- OpenAI text chat
- PostgreSQL conversation history
- persistent long-term memory
- automatic memory for useful durable facts
- `/new`, `/memory`, `/remember`, `/forget`, `/help`
- built-in web search for current information
- Telegram voice message transcription
- photo / image understanding
- document analysis
- automatic PostgreSQL schema initialization
- Telegram long polling: no public domain or webhook required

Supported document types include:

- PDF
- TXT / Markdown / JSON / HTML / XML
- DOC / DOCX / RTF / ODT
- PPT / PPTX
- CSV / TSV
- XLS / XLSX

## Railway deployment

The intended Railway Template contains two services:

1. this Python application
2. PostgreSQL

The user should only need to enter three values:

```env
TELEGRAM_BOT_TOKEN=
OWNER_TELEGRAM_ID=
OPENAI_API_KEY=
```

The application service should receive the database connection automatically
from the PostgreSQL service:

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

Optional variables:

```env
BOT_NAME=Personal AI
OWNER_NAME=
PERSONALITY=You are a helpful, natural and personal AI assistant.
INTERESTS=
TIMEZONE=UTC
OPENAI_MODEL=gpt-5.6-luna
TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
CONTEXT_MESSAGES=20
```

## Security model

`OWNER_TELEGRAM_ID` is enforced in an aiogram outer middleware before the
application's message handlers run. Unauthorized Telegram users therefore do
not reach OpenAI calls, media downloads, or normal handler database writes.

API keys must be stored only in Railway Variables (or a local `.env` file).
Never commit real keys to GitHub. `.env` is excluded by `.gitignore`.

OpenAI Responses requests use `store=False`. Conversation history and
long-term memory are stored in the user's PostgreSQL service.

## First-run test

After deployment:

1. send `/start`
2. send a normal text message
3. send `/remember I like concise answers`
4. send `/new`
5. ask what preference the assistant remembers
6. send a voice message
7. send a photo
8. send a small PDF or DOCX
9. ask a question that requires current web information

If all nine tests work, the clean deployment is ready to be turned into a
Railway Template.

## Local development

Copy `.env.example` to `.env`, fill the required values and provide a
PostgreSQL connection string.

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

## Architecture

```text
Telegram
   |
Owner-only middleware
   |
Handlers (text / voice / image / document / commands)
   |
OpenAI Responses API + transcription
   |
PostgreSQL (conversations + long-term memory)
```

No n8n, Redis, FastAPI, Flask, or separate vector database is required for v0.1.

## License

MIT
