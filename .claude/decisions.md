# Architectural Decision Records (ADR)

Dokumen ini mencatat keputusan arsitektur beserta alasannya.

---

## ADR-001: LangGraph untuk RAG Chain

**Status:** Accepted
**Date:** 2026-03-20

**Context:** Perlu memilih antara LangChain Expression Language (LCEL) atau LangGraph untuk mendefinisikan RAG pipeline.

**Decision:** Pakai LangGraph.

**Reason:**
- LangGraph lebih eksplisit dan mudah di-debug (state machine vs chain)
- Lebih mudah menambahkan node baru (reranker, guardrails, routing, dll) di masa depan
- LCEL lebih concise untuk pipeline sederhana, tapi kurang fleksibel untuk extension

---

## ADR-002: Embedding Provider Terpisah dari LLM Provider

**Status:** Accepted
**Date:** 2026-03-20

**Context:** Awalnya dipertimbangkan untuk membuat embedding provider mengikuti LLM provider secara otomatis.

**Decision:** `EMBEDDING_PROVIDER` dikonfigurasi secara independen dari `LLM_PROVIDER`.

**Reason:**
- Embedding harus konsisten — sekali data diindex dengan provider A, tidak bisa langsung ganti ke provider B tanpa reindex
- User mungkin ingin pakai Gemini LLM tapi OpenAI embeddings (atau sebaliknya)
- Memisahkan concern membuat sistem lebih fleksibel dan tidak mengejutkan user

**Consequence:** Ada `/reindex` endpoint untuk migrasi antar embedding provider.

---

## ADR-003: ChromaDB sebagai Vector Store

**Status:** Accepted
**Date:** 2026-03-20

**Context:** Pilihan: ChromaDB, FAISS, Pinecone.

**Decision:** ChromaDB.

**Reason:**
- Local + persistent (tidak butuh service eksternal)
- Mendukung metadata filtering (penting untuk delete per doc_id)
- Mudah diganti ke Pinecone/Weaviate di masa depan karena abstraksi di `vectorstore.py`

---

## ADR-004: Metadata `doc_id` di Setiap Chunk

**Status:** Accepted
**Date:** 2026-03-20

**Context:** ChromaDB menyimpan chunks, bukan dokumen utuh. Perlu cara untuk delete semua chunks milik satu dokumen.

**Decision:** Setiap chunk diberi metadata `doc_id` (UUID) yang sama untuk semua chunks dari dokumen yang sama.

**Reason:**
- Memungkinkan `DELETE /knowledge/{doc_id}` menghapus semua chunk terkait
- Memungkinkan list documents dengan `chunk_count` per dokumen
- `doc_id` juga dipakai sebagai referensi di chat sources
