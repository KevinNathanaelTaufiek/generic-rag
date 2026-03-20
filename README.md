# Generic RAG

A generic Retrieval-Augmented Generation (RAG) system. Add knowledge, then chat with it.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, LangChain, LangGraph |
| LLM | Google Gemini / OpenAI GPT-4o (switchable) |
| Embeddings | Google `gemini-embedding-001` |
| Vector Store | ChromaDB (local, persistent) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |

## Project Structure

```
generic-rag/
├── backend/      # FastAPI app
└── frontend/     # React app
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv

# Activate virtualenv:
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` ke `.env`:
```bash
# Windows:
copy .env.example .env
# macOS/Linux:
# cp .env.example .env
```

**`.env` minimum config:**
```
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=google
GOOGLE_API_KEY=your_key_here
```

**Run:**
```bash
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

## Features (MVP)

- **Knowledge ingestion**: paste text, upload PDF / TXT / MD
- **Knowledge management**: list and delete documents
- **Chat**: ask questions grounded on your knowledge base, with source citations
- **Provider switching**: swap LLM or embedding provider via `.env` — no code changes needed
- **Reindex**: `POST /api/v1/knowledge/reindex` to re-embed all docs after changing embedding provider

## API Endpoints

```
POST   /api/v1/knowledge/text       Add plain text
POST   /api/v1/knowledge/upload     Upload file (PDF/TXT/MD)
GET    /api/v1/knowledge            List all documents
DELETE /api/v1/knowledge/{doc_id}   Delete a document
POST   /api/v1/knowledge/reindex    Re-embed all documents

POST   /api/v1/chat                 Send a message, get answer + sources
```
