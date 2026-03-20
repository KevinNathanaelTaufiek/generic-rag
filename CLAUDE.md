# CLAUDE.md — Generic RAG

Context engineering file untuk Claude Code. Dibaca otomatis di setiap sesi.

---

## Tentang Project

Generic RAG system: user bisa tambah knowledge (teks/PDF/file), lalu tanya-jawab via chat.
Dirancang extensible — setiap fitur baru harus mudah ditambahkan tanpa rombak besar.

**Context files:**
- Detail fitur & API: `.claude/prd.md`
- Keputusan arsitektur: `.claude/decisions.md`
- Log request user: `.claude/requests.md`
- Cara menjalankan: `.claude/references/quickstart.md`
- Environment variables: `.claude/references/env.md`
- Learning loop: `.claude/feedback_loop.md`

> Setiap perubahan terkait arsitektur atau keputusan → update `.claude/decisions.md` dan `.claude/requests.md`

---

## Konvensi Koding

### Backend
- Settings via `app/config.py` (`Settings` class pydantic-settings) — tidak hardcode di tempat lain
- LLM dan Embeddings via factory function (`get_llm()`, `get_embeddings()`) — tidak diinstansiasi langsung
- Semua dokumen di ChromaDB punya metadata: `doc_id`, `title`, `source_type`, `created_at`, `chunk_index`

### Frontend
- API calls hanya dari `src/api/` — komponen tidak import axios langsung
- Tailwind v4 (pakai `@import "tailwindcss"` di CSS, bukan config file)

---

## Pola Extensibility

| Jenis Fitur          | Di Mana                                  |
| -------------------- | ---------------------------------------- |
| LLM provider baru    | `core/llm.py` — tambah `elif`            |
| Embedding provider   | `core/embeddings.py` — tambah `elif`     |
| Input format baru    | `services/ingestion.py` — fungsi baru    |
| Endpoint baru        | `api/v1/` — file baru + daftar di router |
| Node baru di RAG     | `core/rag_chain.py` — tambah node        |

---

## Catatan Penting

- Ganti `EMBEDDING_PROVIDER` → harus panggil `POST /api/v1/knowledge/reindex`
- `LLM_PROVIDER` bisa diganti bebas tanpa reindex
- Tidak ada auth di MVP — semua user share satu knowledge base
- Chat history: in-memory per sesi (dikirim dari client di setiap request)

---

## Learning Loop

- Jika tidak yakin tentang implementasi teknis → cari referensi valid di internet terlebih dahulu
- Untuk keputusan bisnis/arsitektur → tanya user dengan beberapa opsi beserta plus/minus tiap opsi
- Hanya implementasi hal yang sudah yakin 100%
- Setiap feedback atau koreksi dari user → simpan ke memory system (`~/.claude/projects/.../memory/`)
- Panduan lengkap: `.claude/feedback_loop.md`
