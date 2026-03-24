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

---

## ADR-010 — SQLite untuk Audit Trail (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** Audit log tool approvals disimpan ke SQLite (`data/audit.db`) via SQLAlchemy, bukan in-memory atau file log biasa.

**Reasoning:**
- Perlu query/filter per user, tool name, dan date range — lebih mudah dengan SQL
- SQLite tidak butuh service eksternal (sesuai prinsip MVP lokal)
- Schema sederhana: satu tabel `tool_audit` dengan kolom username, tool_name, ai_suggested_args, user_edited_args, result_status, session_id, thread_id, timestamp
- Mudah migrasi ke PostgreSQL di masa depan jika perlu (tinggal ganti `DATABASE_URL`)

**Consequence:** Backend butuh folder `data/` saat startup. `create_db()` dipanggil di `@app.on_event("startup")`.

---

## ADR-011 — User Identity via X-Username Header (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** Identity user dikirim sebagai HTTP header `X-Username` dari frontend, bukan via auth token/session.

**Reasoning:**
- MVP tidak ada auth — tidak perlu JWT/OAuth
- User dipilih dari `predefined_users` list di config (alice, bob, charlie)
- Frontend simpan pilihan di `localStorage` dan inject via axios interceptor
- Cukup untuk audit trail per user tanpa kerumitan auth

**Trade-off:** Tidak ada enkripsi/validasi identity — user bisa kirim username apapun. Acceptable di MVP/demo. Untuk production, ganti dengan proper auth.

---

## ADR-012 — Zustand untuk Chat State (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** State chat (messages, sessionId, loading, tools, strictMode) dipindah dari `useState` di `ChatPage` ke Zustand store (`chatStore.ts`).

**Reasoning:**
- Multi-user switching perlu state per-user yang persist saat user switch
- State sebelumnya di-lift ke `App.tsx` (props drilling) — tidak scalable
- Zustand lebih ringan dari Redux, tidak butuh Provider wrapper
- `userMessages: Record<string, DisplayMessage[]>` memungkinkan setiap user punya history chat terpisah

**Consequence:** `ChatPage` tidak lagi menerima props — semua state dari store.

---

## ADR-013 — Tool Args Editable di Approval Card (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** Saat LLM request tool call, user bisa edit args sebelum approve — bukan hanya approve/reject binary.

**Reasoning:**
- Memberikan user kontrol lebih: bisa koreksi parameter yang salah tanpa reject dan kirim ulang pesan
- Audit trail menyimpan `ai_suggested_args` vs `user_edited_args` untuk visibility gap antara AI intent dan user action

**Implementation:** `ArgEditor` component di `ChatWindow.tsx` render input sesuai tipe data (string/number/boolean/object). `modified_args` dikirim ke `/chat/tool-approval`. Backend di `resume_agent()` build `resume_value` sebagai dict `{approved, modified_args}` jika ada edit.

---

## ADR-015 — Dynamic Tool Registry via API (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** Frontend fetch daftar tool dari `GET /api/v1/chat/tools` saat mount, bukan hardcode di `chatStore.ts` dan `ChatPage.tsx`.

**Reasoning:**
- Sebelumnya ada 3 tempat yang harus diupdate manual saat tambah/hapus tool di `microservices.json`: `ALL_TOOLS` di store, `TOOL_LABELS`, dan `TOOL_DESCRIPTIONS` di ChatPage
- Dengan dynamic registry, tambah tool di `microservices.json` → otomatis muncul di dropdown tanpa sentuh frontend
- Label auto-format dari tool name (`manage_task` → `Manage Task`); override manual hanya untuk static tools via `STATIC_LABELS`

**Consequence:** Frontend butuh backend running untuk populate tool list. Jika backend unreachable saat mount, dropdown kosong tapi tidak crash.

---

## ADR-016 — manage_task sebagai Dummy Service untuk Testing (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** Ganti `crud_data` dengan `manage_task` — tool dengan 5 args termasuk nested array (`tags`) dan nested object (`metadata`), lengkap dengan UI standalone.

**Reasoning:**
- `crud_data` terlalu generic, tidak cover kasus nested array/object yang perlu ditest untuk approval card
- `manage_task` sengaja dirancang untuk cover semua edge case: multiple args, `list[str]`, nested dict, dan CRUD operations
- UI (`/ui`) di dummy service memudahkan demo presentasi — real-time update saat agent create/update/delete task

**Implementation:**
- `dummy_services/routes/tasks.py`: in-memory `_tasks: dict[str, dict]`
- `dummy_services/static/index.html`: polling `GET /tasks` tiap 2s, toggle pause/resume
- Gemini mensyaratkan array field harus punya `items` — di-handle di `microservice.py` via typed `list[str]` Pydantic field

---

## ADR-014 — [GENERAL_KNOWLEDGE] Marker di LLM Response (2026-03-24)

**Status:** Accepted
**Date:** 2026-03-24

**Decision:** LLM diminta menambahkan token `[GENERAL_KNOWLEDGE]` di awal response jika jawaban berasal dari training knowledge (bukan tool result). Backend strip token ini dan set `from_general_knowledge: true` di response.

**Reasoning:**
- User perlu tahu apakah jawaban grounded di knowledge base atau hanya dari LLM training data
- Frontend tampilkan warning badge "⚠ Jawaban dari general knowledge LLM" saat flag ini true
- Lebih reliable daripada inferring dari sources list (sources bisa kosong karena berbagai alasan)

**Trade-off:** LLM mungkin tidak selalu comply dengan instruksi marker. Fallback heuristic di `resume_agent()`: jika `sources == []` dan answer ada dan tidak dimulai "Maaf," → set `from_general_knowledge = True`.
