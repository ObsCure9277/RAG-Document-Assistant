# RAG Document Assistant

A personal Retrieval-Augmented Generation (RAG) workspace for uploading documents, indexing them asynchronously, and asking grounded questions with source citations.

The application supports PDF, DOCX, TXT, and Markdown files. Documents are persisted in PostgreSQL with pgvector, indexed through Inngest, and queried through hybrid vector plus full-text retrieval.

## Features

| Feature | Details |
|---|---|
| Multi-format upload | PDF, DOCX, TXT, and Markdown |
| Document library | Upload, list, re-index, retry, and remove documents |
| Durable indexing | Inngest-powered asynchronous ingestion |
| LlamaIndex chunking | LlamaIndex SentenceSplitter and TextNode metadata |
| Embeddings | OpenAI-compatible embeddings through OpenRouter or OpenAI |
| Persistent vector store | PostgreSQL with the pgvector extension |
| Hybrid retrieval | Vector similarity plus PostgreSQL full-text search |
| Grounded chat | Streaming answers constrained to retrieved evidence |
| Citations | Document name, page, heading, excerpt, and relevance scores |
| Structured observability | Indexing, retrieval, embedding, and answer timing logs |
| Responsive frontend | Single-column dark workspace for desktop and mobile |

## Architecture

```mermaid
flowchart TD
    UI[React frontend] --> API[FastAPI]
    API --> DB[(PostgreSQL + pgvector)]
    API --> ING[Inngest event]
    ING --> WORK[ingest-file]
    WORK --> LOAD[Load and extract]
    LOAD --> CHUNK[LlamaIndex SentenceSplitter]
    CHUNK --> EMBED[OpenRouter embeddings]
    EMBED --> UPSERT[Persist document chunks]
    UPSERT --> DB
    API --> RETRIEVE[Hybrid retrieval]
    RETRIEVE --> DB
    RETRIEVE --> LLM[OpenRouter chat model]
    LLM --> SSE[Streaming answer + citations]
    SSE --> UI
```

## RAG pipeline

1. Upload a supported document.
2. Store the original file and create a document version.
3. Publish a `document/ingestion.requested` event.
4. Inngest invokes the `ingest-file` function.
5. Extract text and split it into LlamaIndex nodes/chunks.
6. Generate embeddings and upsert chunks into PostgreSQL/pgvector.
7. Embed the user question.
8. Retrieve candidates using vector similarity and PostgreSQL full-text search.
9. Build a numbered evidence context.
10. Stream the grounded answer with citation metadata.

Internal chunk UUIDs are retained for database deduplication but are not shown in the user-facing citation output.

## Technology

- Python 3.11+
- FastAPI
- SQLAlchemy async
- PostgreSQL 16 with pgvector
- Inngest
- LlamaIndex Core
- OpenAI-compatible embeddings and chat models
- React, TypeScript, and Vite
- Docker Compose

## Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- Docker Desktop
- An OpenRouter or OpenAI API key for embeddings and chat

## Configuration

Copy the example configuration:

```powershell
Copy-Item .env.example .env
```

For OpenRouter, configure:

```env
POSTGRES_PORT=55432
DATABASE_URL=postgresql+asyncpg://rag_assistant:change-me@127.0.0.1:55432/rag_assistant

OPENAI_API_KEY=sk-or-v1-your-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
ANSWER_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small
```

Never commit `.env` or expose the API key in logs, screenshots, or issue reports.

Set `API_AUTH_TOKEN` to a long random secret. The frontend uses the same value through `VITE_API_TOKEN` and sends it as `Authorization: Bearer <token>`. All application API routes require this token; only `/health` and the signed Inngest handler are unauthenticated at the application middleware.

## Run locally

### 1. Install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
```

### 2. Start PostgreSQL

The default Docker port is 5432. If another PostgreSQL instance already uses that port, use 55432:

```powershell
docker compose up -d postgres
```

Set the matching `POSTGRES_PORT` and `DATABASE_URL` values in `.env`.

Apply migrations:

```powershell
alembic upgrade head
```

### 3. Start Inngest

In a separate terminal:

```powershell
npx inngest-cli@latest dev --no-discovery -u http://127.0.0.1:8001/api/inngest
```

Open the Inngest dashboard at http://127.0.0.1:8288.

### 4. Start FastAPI

In another terminal:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

FastAPI runs at http://127.0.0.1:8001. API documentation is available at http://127.0.0.1:8001/docs.

### 5. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the workspace at http://127.0.0.1:5173.

The Vite development server proxies `/api` requests to FastAPI on port 8001.

## API examples

Upload a document:

```powershell
curl.exe -X POST http://127.0.0.1:8001/api/documents `
  -F "file=@.scratch\rag-document-assistant\issues\01-dockerized-persistence-foundation.md"
```

List documents:

```powershell
curl.exe http://127.0.0.1:8001/api/documents
```

Search indexed documents:

```powershell
curl.exe "http://127.0.0.1:8001/api/search?query=database%20persistence"
```

Create a conversation:

```powershell
curl.exe -X POST http://127.0.0.1:8001/api/conversations
```

Send a streaming chat message:

```powershell
curl.exe -N -X POST http://127.0.0.1:8001/api/conversations/{conversation_id}/messages `
  -H "Content-Type: application/json" `
  -d '{"content":"What does the document say about persistence?"}'
```

## Citation format

The model receives evidence using numbered references:

```text
[1] 01-dockerized-persistence-foundation.md
Relevant source excerpt...
```

The frontend displays citations as:

```text
[1] 01-dockerized-persistence-foundation.md
Relevant source excerpt...
```

The internal database chunk identifier is never intended for user-facing output.

## Inngest observability

The `ingest-file` function emits structured logs for:

```text
index_started
load_and_chunk_started
load_and_chunk_completed
embed_and_upsert_started
embeddings_completed
embed_and_upsert_completed
index_completed
index_failed
```

Chat observability includes:

```text
embed_and_search_started
embed_and_search_completed
llm_answer_started
llm_answer_completed
chat_completed
chat_failed
```

Timing fields include `duration_ms`; indexing logs also include chunk counts and chunks-per-second.

## Testing

Run the backend tests:

```powershell
pytest
```

Build the frontend:

```powershell
cd frontend
npm run build
```

Tests cover chunking, grounded prompt construction, SSE serialization, evaluation metrics, lifecycle behaviour, and event publishing.

## Project structure

```text
app/
  main.py             FastAPI routes and streaming chat
  models.py           SQLAlchemy domain models
  indexing.py         Extraction and LlamaIndex chunking
  worker.py           Document indexing workflow
  inngest_worker.py   Inngest function adapter
  retrieval.py        Hybrid vector and lexical retrieval
  embeddings.py       OpenAI-compatible embedding adapter
  chat_models.py      OpenAI-compatible chat adapter
  chat.py             Grounded prompt and SSE helpers
  lifecycle.py        Document version lifecycle
  evaluation.py       Retrieval evaluation metrics
  storage.py           Original file storage

frontend/
  src/App.tsx         Document library and upload workspace
  src/Chat.tsx        Streaming chat interface
  src/index.css       Responsive dark theme
```

## Current limitations

- Single-user application.
- OCR is not included for image-only PDFs.
- OpenRouter/OpenAI credentials are required for embeddings and generated answers.
- The local Inngest development server is intended for development, not production deployment.
- Existing PostgreSQL data must be retained when changing embedding dimensions or embedding models.

## Security notes

- Keep `.env` outside version control.
- Rotate any key that appears in terminal output, screenshots, logs, or chat transcripts.
- Use a disposable PostgreSQL database for integration tests.
- Do not expose the Inngest development server or FastAPI instance publicly without authentication.

## License

This project is intended for personal development and experimentation.
