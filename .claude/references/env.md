# Environment Variables

Semua variabel ini ada di `backend/.env` (copy dari `backend/.env.example`).

## Provider

| Variabel | Default | Opsi | Catatan |
|---|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai` | Bisa diganti bebas tanpa reindex |
| `EMBEDDING_PROVIDER` | `google` | `google`, `openai` | Ganti → wajib `/reindex` |

## API Keys

| Variabel | Kapan Dibutuhkan |
|---|---|
| `GOOGLE_API_KEY` | Jika `LLM_PROVIDER=gemini` atau `EMBEDDING_PROVIDER=google` |
| `OPENAI_API_KEY` | Jika `LLM_PROVIDER=openai` atau `EMBEDDING_PROVIDER=openai` |

## ChromaDB

| Variabel | Default | Keterangan |
|---|---|---|
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Path penyimpanan vector store |
| `COLLECTION_NAME` | `generic_rag` | Nama koleksi di ChromaDB |

## RAG Parameters

| Variabel | Default | Keterangan |
|---|---|---|
| `TOP_K_RESULTS` | `5` | Jumlah chunk yang diambil saat retrieval |
| `CHUNK_SIZE` | `500` | Ukuran chunk dalam token |
| `CHUNK_OVERLAP` | `50` | Overlap antar chunk untuk kontinuitas konteks |
