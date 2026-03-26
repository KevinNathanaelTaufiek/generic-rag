# PRD: Generic RAG System — MVP

## Overview

Generic RAG adalah sistem yang memungkinkan user untuk "mengajarkan" knowledge kepada sistem,
lalu melakukan tanya-jawab berbasis knowledge tersebut melalui interface chat.

**Goal MVP:**
- User dapat menambahkan knowledge (teks, PDF, file .txt/.md)
- Knowledge disimpan dan diindeks di vector store
- User dapat chat dan mendapat jawaban yang grounded pada knowledge yang telah ditambahkan

---

## Tech Stack

| Layer         | Teknologi                                            |
| ------------- | ---------------------------------------------------- |
| Backend       | Python 3.11+, FastAPI                                |
| AI Framework  | LangChain + LangGraph                                |
| LLM           | OpenAI (GPT-4o) & Google Gemini — switchable via env |
| Embeddings    | Google `models/text-embedding-004` (default)         |
| Vector Store  | ChromaDB (lokal, persistent)                         |
| Frontend      | React 18 + TypeScript + Vite + Tailwind CSS          |

---

## Features — MVP Scope

### F1: Knowledge Ingestion
- **F1.1** Input teks langsung (paste teks dari UI)
- **F1.2** Upload file PDF (backend extract teks via `pypdf`)
- **F1.3** Upload file `.txt` / `.md`
- Semua dokumen di-chunked (RecursiveCharacterTextSplitter, ~500 token, overlap 50)
- Chunks di-embed dan disimpan ke ChromaDB dengan metadata (source, filename, timestamp, doc_id)

### F2: Knowledge Management
- **F2.1** Lihat daftar dokumen/knowledge yang telah ditambahkan
- **F2.2** Hapus dokumen dari knowledge base

### F3: Chat
- **F3.1** User kirim pertanyaan via chat UI
- **F3.2** Sistem retrieve top-k chunks yang relevan dari ChromaDB
- **F3.3** LLM generate jawaban berdasarkan retrieved context + pertanyaan
- **F3.4** Respons menampilkan sumber dokumen yang digunakan (source citation)
- **F3.5** Chat history dalam satu sesi (in-memory, bukan persistent antar sesi)

### F4: Provider Switching (Anti Vendor Lock-in)
- LLM provider dipilih via `LLM_PROVIDER=openai|gemini`
- Embedding provider dipilih via `EMBEDDING_PROVIDER=google|openai` (terpisah dari LLM)
- Kedua layer (LLM + Embedding) punya factory function masing-masing
- Metadata embedding model disimpan di ChromaDB collection metadata
- Reindex via `POST /api/v1/knowledge/reindex` setelah ganti embedding provider

---

## API Endpoints

```
POST   /api/v1/knowledge/text       Ingest plain text
POST   /api/v1/knowledge/upload     Upload PDF/txt/md (multipart)
GET    /api/v1/knowledge            List semua dokumen
DELETE /api/v1/knowledge/{doc_id}   Hapus dokumen
POST   /api/v1/knowledge/reindex    Re-embed semua dokumen

POST   /api/v1/chat                 Kirim pesan, dapat respons + sources
POST   /api/v1/chat/tool-approval   Approve/reject (+ edit args) tool call yang pending

GET    /api/v1/audit                List audit records (filter: username, tool_name, date range)
GET    /api/v1/users                List predefined users
```

---

## Data Models

```python
# Knowledge
class AddTextRequest(BaseModel):
    content: str
    title: Optional[str]

class DocumentInfo(BaseModel):
    doc_id: str
    title: str
    source_type: str       # "text" | "pdf" | "file"
    created_at: str
    chunk_count: int

# Chat
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str]    # future multi-session
    history: Optional[list]      # client-side history

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]          # [{doc_id, title, excerpt}]
    session_id: str
    status: Literal["done", "pending_tool_approval"]
    pending_tool: Optional[ToolCallInfo]
    thread_id: Optional[str]
    from_general_knowledge: bool      # True jika jawaban dari training LLM, bukan knowledge base

# Audit
class ToolAuditRecord:
    username: str
    tool_name: str
    ai_suggested_args: dict
    user_edited_args: Optional[dict]  # None jika tidak diedit
    result_status: str                # "approved" | "rejected"
    session_id, thread_id, timestamp
```

---

## LangGraph RAG Chain

```
User Input
    ↓
[retrieve_node]  → query ChromaDB → top-k chunks
    ↓
[generate_node]  → LLM(system_prompt + context + history + question)
    ↓
Response + Sources
```

State: `{ question, history, context_docs, answer, sources }`

---

## Configuration (.env)

```
LLM_PROVIDER=gemini               # openai | gemini
EMBEDDING_PROVIDER=google         # google | openai
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...
CHROMA_PERSIST_DIR=./data/chroma
COLLECTION_NAME=generic_rag
TOP_K_RESULTS=5
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

---

## Extensibility (Future-Ready Design)

| Fitur Masa Depan       | Yang Sudah Disiapkan                                      |
| ---------------------- | --------------------------------------------------------- |
| Auth / multi-user      | User identity via `X-Username` header sudah ada; predefined_users config; tinggal tambah proper auth layer |
| Provider baru          | Factory pattern di `llm.py` dan `embeddings.py`           |
| Ganti embedding model  | `EMBEDDING_PROVIDER` di env + `/reindex` endpoint         |
| Input format baru      | Tambah handler di `ingestion.py`                          |
| Persistent chat history| Schema sudah siap, tinggal tambah DB                      |
| Streaming response     | FastAPI SSE mudah ditambah ke `/chat`                     |
| Re-ranking             | Inject reranker node di LangGraph antara retrieve→generate |
