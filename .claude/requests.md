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
