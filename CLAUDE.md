# CLAUDE.md — Generic RAG

Context engineering file untuk Claude Code. Dibaca otomatis di setiap sesi.

---

## Tentang Project

Generic RAG system: user bisa tambah knowledge (teks/PDF/file), lalu tanya-jawab via chat.
Dirancang extensible — setiap fitur baru harus mudah ditambahkan tanpa rombak besar.

Detail lengkap: `.claude/prd.md`
Keputusan arsitektur: `.claude/decisions.md`
Log request user: `.claude/requests.md`

Pastikan untuk setiap perubahan terkait project dan decision yang user lakukan update file pada .claude

---

## Struktur Project

```
generic-rag/
├── backend/               # Python FastAPI
│   ├── app/
│   │   ├── main.py        # Entry point
│   │   ├── config.py      # Settings dari .env
│   │   ├── api/v1/        # Endpoints (knowledge.py, chat.py, router.py)
│   │   ├── core/          # LLM, embeddings, vectorstore, rag_chain
│   │   ├── services/      # ingestion.py, retrieval.py
│   │   └── schemas/       # Pydantic models
│   ├── requirements.txt
│   └── .env.example
├── frontend/              # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── api/           # API client (knowledge.ts, chat.ts)
│       ├── components/    # ChatWindow, ChatInput, KnowledgeUpload, KnowledgeList
│       └── pages/         # ChatPage, KnowledgePage
├── CLAUDE.md              # (file ini)
└── .claude/               # Context tambahan (gitignored)
```

---

## Cara Menjalankan

```bash
# Backend
cd backend && uvicorn app.main:app --reload
# → http://localhost:8000/docs

# Frontend
cd frontend && npm run dev
# → http://localhost:5173
```

---

## Tech Stack

| Layer        | Teknologi                                    |
| ------------ | -------------------------------------------- |
| Backend      | Python 3.11+, FastAPI, LangChain, LangGraph  |
| LLM          | Gemini 2.0 Flash / GPT-4o (via `LLM_PROVIDER`) |
| Embeddings   | Google gemini-embedding-001 (via `EMBEDDING_PROVIDER`) |
| Vector Store | ChromaDB (local persistent, `./data/chroma`) |
| Frontend     | React 18 + TypeScript + Vite + Tailwind v4   |

---

## Konvensi Koding

### Backend
- Semua settings dari `.env` via `app/config.py` (`Settings` class pydantic-settings)
- LLM dan Embeddings dibuat via factory function (`get_llm()`, `get_embeddings()`) — tidak diinstansiasi langsung di tempat lain
- Tambah provider baru: edit `core/llm.py` atau `core/embeddings.py`, tambah `elif` baru
- Tambah input format baru: tambah fungsi di `services/ingestion.py`
- Tambah endpoint baru: buat file baru di `api/v1/`, daftarkan di `api/v1/router.py`
- Semua dokumen di ChromaDB punya metadata: `doc_id`, `title`, `source_type`, `created_at`, `chunk_index`

### Frontend
- API calls hanya dari `src/api/` — komponen tidak import axios langsung
- Tailwind v4 (pakai `@import "tailwindcss"` di CSS, bukan config file)
- Komponen di `src/components/`, halaman di `src/pages/`

---

## Pola Extensibility

Saat user minta fitur baru, ikuti pola ini:

| Jenis Fitur          | Di Mana                                  |
| -------------------- | ---------------------------------------- |
| LLM provider baru    | `core/llm.py` — tambah `elif`            |
| Embedding provider   | `core/embeddings.py` — tambah `elif`     |
| Input format baru    | `services/ingestion.py` — fungsi baru    |
| Endpoint baru        | `api/v1/` — file baru + daftar di router |
| Node baru di RAG     | `core/rag_chain.py` — tambah node        |

---

## Environment Variables

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

## Catatan Penting

- Ganti `EMBEDDING_PROVIDER` → harus panggil `POST /api/v1/knowledge/reindex` agar data lama ter-embed ulang
- `LLM_PROVIDER` bisa diganti bebas tanpa reindex
- Tidak ada auth di MVP — semua user share satu knowledge base
- Chat history: in-memory per sesi (dikirim dari client di setiap request), tidak persistent ke DB
