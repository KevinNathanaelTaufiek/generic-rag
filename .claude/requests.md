# User Requests Log

Dokumen ini mencatat request-request user beserta konteks dan keputusan yang diambil.
Berguna sebagai memori kontekstual untuk sesi-sesi Claude berikutnya.

---

## [2026-03-20] MVP Setup — Generic RAG

**Request:**
> "saya ingin membuat generic rag dimana kita akan pakai python untuk membuat sistem RAG,
> MVP dari sistem RAG yang saya mau adalah user bisa kasih knowledge ke sistem RAG,
> lalu sistem RAG bisa simpan knowledge tersebut, dari knowledge yang telah dimiliki user
> bisa tanya-tanya via chat. Kedepannya saya akan minta berbagai tambahan fitur, jadi
> pastikan kalo kode & PRD siap untuk penambahan / perubahan fitur."

**Stack yang dipilih:**
- Backend: Python + FastAPI + LangChain + LangGraph
- LLM: Google Gemini + OpenAI (switchable via `LLM_PROVIDER` env)
- Embeddings: Google `text-embedding-004` (default) — dipilih karena free tier, tidak ada vendor lock-in
- Vector Store: ChromaDB (local, persistent)
- Frontend: React + TypeScript + Vite + Tailwind CSS (folder terpisah dari backend)

**Keputusan penting:**
- Embedding provider dipisahkan dari LLM provider (`EMBEDDING_PROVIDER` env sendiri)
- Ada endpoint `/reindex` untuk re-embed semua data saat ganti embedding provider
- Tidak ada auth di MVP (single user)
- Input: plain text, PDF, TXT, MD (URL scraping ditunda ke post-MVP)
- Chat history: in-memory per sesi (bukan persistent antar sesi di MVP)

---

## [2026-03-22] Web Sources, Score Threshold, React Router, Agent Steps Log

**Request:**
> Rangkum semua perubahan, update knowledge, commit.

**Perubahan yang dilakukan:**
- Score threshold ChromaDB: 0.5 → 0.6 (lebih strict, kurangi false positives)
- `search_web` output: dual-format (human-readable + JSON block) untuk source extraction
- `react_agent.py`: ekstraksi web sources ke `sources[]` di response; strict mode guard lebih awal
- `Source` schema: tambah field `url` optional
- Frontend: migrasi navigasi ke React Router (`react-router-dom`)
- Frontend: `AgentStepsLog` component untuk real-time tool call progress
- Frontend: web sources tampil sebagai clickable link (↗)
- Frontend: AbortSignal support di `sendMessage()`

**File yang diubah:**
- `backend/app/core/rag_chain.py` — threshold 0.6
- `backend/app/core/react_agent.py` — web sources extraction, strict mode guard
- `backend/app/core/tools/search_knowledge.py` — threshold 0.6
- `backend/app/core/tools/search_web.py` — dual-format output
- `backend/app/schemas/chat.py` — `url` field di `Source`
- `frontend/src/App.tsx` — React Router migration
- `frontend/src/components/ChatWindow.tsx` — AgentStepsLog, clickable sources
- `frontend/src/api/chat.ts` — AbortSignal support
- `.claude/decisions.md` — ADR-007, ADR-008, ADR-009
- `.claude/session-summary.md` — item 12–15

---

## Template untuk Request Berikutnya

Saat menambahkan fitur baru, tambahkan entry di sini:

```
## [YYYY-MM-DD] Nama Fitur

**Request:**
> "..."

**Keputusan:**
- ...

**File yang diubah:**
- ...
```
