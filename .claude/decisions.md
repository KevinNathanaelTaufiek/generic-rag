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

---

## ADR-005 — MemorySaver untuk interrupt state (2026-03-20)

**Decision:** Gunakan `MemorySaver` (in-memory) dari LangGraph untuk menyimpan graph state saat interrupt.

**Reasoning:** `thread_id` hanya hidup selama satu approval cycle (beberapa detik antara `/chat` dan `/chat/tool-approval`). Tidak perlu database persisten untuk ini di MVP.

**Trade-off:** Pending approval hilang jika backend restart. Frontend handle HTTP 400 dan inform user untuk kirim ulang. Jika persistence diperlukan di masa depan, ganti `MemorySaver` dengan `SqliteSaver` atau `PostgresSaver` — tidak ada perubahan logika lain.

## ADR-006 — Dummy microservices sebagai app terpisah (2026-03-20)

**Decision:** Dummy services di-deploy sebagai FastAPI app terpisah di `dummy_services/` (port 8001), bukan endpoint di backend utama.

**Reasoning:** Mensimulasikan deployment separation yang nyata. Saat microservices asli bisa diakses, cukup ganti `DUMMY_SERVICES_BASE_URL` di `backend/.env`.

**Migration:** `DUMMY_SERVICES_BASE_URL=https://real-service.internal` di `backend/.env`.

---

## ADR-007 — Dual-format output untuk search_web (2026-03-22)

**Decision:** `search_web` tool mengembalikan dua format sekaligus: human-readable text untuk LLM + JSON block `[web_sources_json]` untuk source extraction di agent.

**Reasoning:** LLM butuh teks natural untuk dijadikan jawaban; backend butuh structured data untuk populate `sources` di response API. Menggabungkan keduanya dalam satu string menghindari perubahan interface tool (LangChain tools hanya return string).

**Trade-off:** Sedikit lebih verbose dalam output tool. Alternatif (return JSON murni) membuat LLM kesulitan membaca hasilnya.

---

## ADR-008 — Score threshold 0.6 untuk ChromaDB (2026-03-22)

**Decision:** Threshold relevance dinaikkan dari 0.5 ke 0.6 di semua path (fast path + ReAct agent).

**Reasoning:** Threshold 0.5 terlalu permissive — ChromaDB mengembalikan dokumen yang tidak relevan, menyebabkan LLM menjawab dengan informasi salah. Lebih baik "tidak tahu" daripada hallucinate.

**Consequence:** Recall sedikit lebih rendah, precision lebih tinggi. Bisa diturunkan lagi jika KB kecil dan recall rendah.

---

## ADR-009 — React Router untuk navigasi frontend (2026-03-22)

**Decision:** Migrasi dari tab state (`useState`) ke `react-router-dom` `<Routes>`.

**Reasoning:** Mendukung deep linking, browser history navigation, dan persiapan untuk penambahan halaman baru di masa depan. State chat di-lift ke `AppInner` agar persist saat navigasi antar halaman.
