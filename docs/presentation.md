# Generic RAG System — Presentation Brief

## Slide 1: Apa Itu Generic RAG?

**Tagline:** "Ajarkan AI pengetahuan Anda, lalu tanya-jawab langsung."

Generic RAG (Retrieval-Augmented Generation) adalah sistem yang memungkinkan siapa saja untuk:
- Memasukkan dokumen/knowledge ke dalam sistem
- Lalu bertanya kepada AI yang jawabannya **berdasarkan dokumen tersebut** — bukan hanya dari training data umum

**Analogi:** Seperti memberi karyawan baru sebuah manual/SOP, lalu ia bisa menjawab pertanyaan berdasarkan manual itu — bukan menebak-nebak.

---

## Slide 2: Masalah yang Dipecahkan

| Masalah | Solusi Generic RAG |
|---|---|
| LLM menjawab berdasarkan data lama / hallucinate | Jawaban di-ground ke dokumen yang Anda upload |
| Tidak tahu apakah jawaban dari dokumen atau tebakan | Badge "⚠ Jawaban dari general knowledge" muncul jika tidak ada sumber |
| Tidak bisa kontrol AI melakukan aksi berbahaya | Human-in-the-loop: setiap aksi perlu approval + bisa edit argumen |
| Tidak ada jejak siapa melakukan apa | Audit trail lengkap per user |

---

## Slide 3: Tech Stack

| Layer | Teknologi |
|---|---|
| Backend | Python 3.11 + FastAPI |
| AI Framework | LangChain + LangGraph |
| LLM | OpenAI GPT-4o **atau** Google Gemini — bisa switch via config |
| Embeddings | Google text-embedding-004 (default) atau OpenAI |
| Vector Store | ChromaDB (lokal, persistent) |
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Database | SQLite (audit trail) |

**Catatan desain:** LLM dan Embedding bisa diganti bebas via environment variable — tidak ada vendor lock-in.

---

## Slide 4: Arsitektur Sistem

```
User
 │
 ├── Upload Dokumen (PDF / TXT / MD / plain text)
 │       ↓
 │   [Chunking] → [Embedding] → ChromaDB
 │
 └── Chat / Tanya Jawab
         ↓
     [LangGraph Agent]
         ├── search_knowledge → ChromaDB (semantic search)
         ├── search_web       → Tavily Web Search
         └── manage_task      → Dummy microservice (contoh integrasi)
         ↓
     [LLM Generate Jawaban + Sumber]
         ↓
     Response + Sources + Thinking Process (streaming)
```

**LangGraph** digunakan karena memudahkan penambahan node baru (reranker, guardrails, routing) tanpa ubah logika lama.

---

## Slide 5: Fitur Utama — Knowledge Management

### Upload & Simpan Knowledge
- **Plain text** — paste langsung dari UI
- **PDF** — extract teks otomatis via pypdf
- **File .txt / .md** — upload langsung
- Dokumen dipotong (chunked) ~500 token, di-embed, disimpan ke ChromaDB

### Manajemen Dokumen
- Lihat daftar semua dokumen yang telah dimasukkan (dengan jumlah chunk)
- Hapus dokumen kapan saja — semua chunk terkait ikut terhapus
- Re-index seluruh knowledge base jika ganti embedding provider

---

## Slide 6: Fitur Utama — Chat & RAG

### Chat Berbasis Knowledge
- Pertanyaan → sistem cari chunk paling relevan di ChromaDB (similarity search)
- LLM generate jawaban berdasarkan chunk tersebut + riwayat percakapan
- **Source citation:** setiap jawaban menampilkan dokumen mana yang jadi sumber

### Transparency Features
- **"⚠ Jawaban dari general knowledge"** — muncul jika LLM menjawab dari training data, bukan dokumen Anda
- **Thinking process** — tampilkan proses berpikir LLM (collapsible, khusus Gemini 2.5)
- **Streaming** — jawaban muncul token-by-token, tidak perlu tunggu response penuh

### Strict Mode
- Aktifkan untuk memastikan LLM hanya menjawab dari knowledge base — jika tidak ditemukan, ia menolak menjawab

---

## Slide 7: Fitur Utama — Agent & Tool Calling

### ReAct Agent
Selain RAG sederhana, sistem menggunakan ReAct agent yang bisa memilih tools:
- `search_knowledge` — cari di knowledge base
- `search_web` — cari di internet (via Tavily)
- `manage_task` — contoh integrasi ke microservice eksternal (CRUD task)

### Human-in-the-Loop Approval
Ketika agent ingin menjalankan aksi (misal: buat task, edit data):
1. Sistem **pause** dan tampilkan approval card ke user
2. User bisa **approve**, **reject**, atau **edit argumen** sebelum dijalankan
3. Semua ini dicatat di audit trail

**Contoh use case:** Agent ingin membuat task "Follow up dengan client A" → user bisa ubah nama client sebelum approve.

---

## Slide 8: Fitur Utama — Multi-User & Audit Trail

### Multi-User (tanpa auth kompleks)
- User dipilih dari daftar predefined (alice, bob, charlie)
- Setiap user punya **riwayat chat terpisah** (Zustand store per-user)
- Identity dikirim via header `X-Username` — cukup untuk demo/presentasi

### Audit Trail
- Setiap tool approval/rejection dicatat ke SQLite
- Tersimpan: username, tool name, **argumen yang AI sarankan** vs **argumen yang user edit**
- Filter berdasarkan user, nama tool, dan rentang tanggal
- Halaman `/audit` di frontend untuk melihat log

---

## Slide 9: Demo Flow (Skenario Presentasi)

**Skenario:** "AI Assistant untuk tim support internal"

1. **Upload SOP perusahaan** (PDF) → sistem index otomatis
2. **Tanya:** "Apa prosedur untuk refund lebih dari 30 hari?" → AI jawab berdasarkan SOP + tampilkan sumber
3. **Tanya sesuatu yang tidak ada di SOP** → muncul badge "⚠ General Knowledge"
4. **Aktifkan Strict Mode** → AI tolak menjawab jika tidak ada di knowledge base
5. **Agent buat task follow-up** → approval card muncul → user edit task title → approve → task muncul di Task Manager UI

---

## Slide 10: Keputusan Arsitektur Penting

| Keputusan | Alasan |
|---|---|
| LangGraph (bukan LCEL) | State machine lebih mudah di-debug, mudah tambah node baru |
| Embedding provider terpisah dari LLM | Konsistensi index — ganti embedding = harus reindex |
| ChromaDB (bukan FAISS/Pinecone) | Lokal + persistent + support delete per doc_id |
| doc_id di setiap chunk | Memungkinkan delete semua chunk satu dokumen sekaligus |
| SQLite untuk audit | Tidak butuh service eksternal, mudah query/filter |
| X-Username header (bukan JWT) | Cukup untuk MVP/demo tanpa kerumitan auth |
| Dynamic tool registry | Tambah tool baru di config → otomatis muncul di UI |
| Streaming via SSE | Perceived latency jauh lebih rendah |

---

## Slide 11: Arah Pengembangan Selanjutnya

### Short-term (siap diimplementasi, fondasi sudah ada)
- **Authentication proper** — tinggal ganti `X-Username` header dengan JWT/OAuth; semua infrastructure audit trail sudah ada
- **Persistent chat history** — schema sudah siap, tinggal tambah DB (PostgreSQL / SQLite)
- **Re-ranking** — inject reranker node di LangGraph antara retrieve → generate (Cohere Rerank, dll)
- **Input format baru** — URL scraping, DOCX, Excel; tinggal tambah handler di `ingestion.py`
- **LLM/Embedding provider baru** — tambah `elif` di factory function; arsitektur sudah siap

### Medium-term
- **Evaluasi kualitas RAG** — integrasikan RAGAS (faithfulness, answer relevance, context recall)
- **Hybrid search** — kombinasi semantic search (vector) + keyword search (BM25) untuk recall lebih baik
- **Per-collection knowledge base** — setiap user/tim punya knowledge base terisolasi
- **Webhook / event notifications** — notify saat agent selesai menjalankan task panjang

### Long-term / Enterprise-ready
- **Multi-tenant** — tiap organisasi punya isolated knowledge base + user management
- **Role-based access control** — admin vs viewer vs editor per knowledge base
- **Deployment to cloud** — ganti ChromaDB lokal ke Pinecone/Weaviate; ganti SQLite ke PostgreSQL
- **Observability** — integrasikan LangSmith atau Langfuse untuk trace setiap LLM call
- **Fine-tuning pipeline** — gunakan audit trail (approved tool calls) sebagai training data untuk fine-tune model
- **Knowledge versioning** — track perubahan knowledge base seperti git

---

## Slide 12: Kenapa Arsitektur Ini Scalable?

```
Tambah LLM provider baru    → 1 elif di core/llm.py
Tambah embedding provider   → 1 elif di core/embeddings.py
Tambah input format baru    → 1 fungsi di services/ingestion.py
Tambah endpoint baru        → 1 file di api/v1/ + daftar di router
Tambah node di RAG pipeline → 1 node di core/rag_chain.py
Tambah tool baru            → 1 entry di microservices.json
```

**Prinsip:** Setiap ekstensi terisolasi, tidak rombak kode yang sudah ada.

---

## Slide 13: Summary

**Generic RAG = Platform RAG yang extensible**

✓ Upload knowledge → tanya jawab grounded
✓ Transparent: tahu persis jawaban dari mana
✓ Agent + human approval untuk aksi nyata
✓ Multi-user dengan audit trail
✓ Streaming UX — tidak ada loading tanpa feedback
✓ Anti vendor lock-in — switch LLM/embedding via config
✓ Arsitektur siap scale — dari MVP ke enterprise

**Stack:** Python + FastAPI + LangGraph + ChromaDB + React + TypeScript

---

## Appendix: API Endpoints

```
POST   /api/v1/knowledge/text       Upload plain text
POST   /api/v1/knowledge/upload     Upload PDF/txt/md
GET    /api/v1/knowledge            List semua dokumen
DELETE /api/v1/knowledge/{doc_id}   Hapus dokumen
POST   /api/v1/knowledge/reindex    Re-embed semua dokumen

POST   /api/v1/chat                 Chat (streaming SSE)
POST   /api/v1/chat/tool-approval   Approve/reject/edit tool call

GET    /api/v1/audit                Audit log (filter: user, tool, date)
GET    /api/v1/users                List predefined users
GET    /api/v1/chat/tools           Dynamic tool registry
```
