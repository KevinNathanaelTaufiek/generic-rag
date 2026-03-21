# Session Summary — Generic RAG Build Journey

Rangkuman perjalanan development sesi ini. Cocok untuk referensi presentasi vibe coding.

---

## 1. Debugging Tool Approval

Masalah pertama: setiap pertanyaan memunculkan tool approval dialog — termasuk `search_knowledge` yang seharusnya otomatis. LLM memanggil `web_search` padahal KB sudah punya jawabannya.

**Fix:** `search_knowledge` dikecualikan dari flow approval — eksekusi otomatis tanpa konfirmasi user.

---

## 2. Refactor Tools Architecture

Sebelumnya semua tools selalu aktif. Diubah menjadi sistem toggle:

- Frontend kirim `enabled_tools[]` per request
- Backend filter tools yang aktif via `get_tools(enabled_tools)`
- **Knowledge Base selalu diprioritaskan** — jika aktif, selalu dipanggil pertama sebelum tools lain

---

## 3. Strict Mode

Dua mode jawaban:

| Mode | Behavior |
|---|---|
| **Strict ON** | Jawab HANYA dari KB. Jika tidak ada → "tidak tahu" |
| **Strict OFF** | Prioritize KB, boleh fallback ke general knowledge LLM |

Saat strict ON → tools lain otomatis di-disable di UI dan tidak bisa di-toggle.

---

## 4. Knowledge-First dengan General Knowledge Fallback

Problem: strict OFF tapi LLM tetap menolak jawab dari general knowledge meski diperintah via prompt (Gemini conservative).

**Solusi dua lapis:**
- **Score threshold 0.5** di ChromaDB — hasil di bawah 0.5 dianggap tidak relevan
- **Rebind LLM tanpa tools** jika KB tidak relevan → paksa jawab dari general knowledge dengan disclaimer

---

## 5. Investigasi Latency

Ditemukan response ~6.6s per pertanyaan. Pasang **verbose logging** dengan `time.perf_counter()` di setiap step:

```
LLM call #1 (decision)   → 1.87s
search_knowledge          → 1.40s  (embed query ke Google API)
LLM call #2 (answer)     → 1.67s
LangGraph overhead        → ~1.67s
─────────────────────────────────
Total                     → 6.61s
```

Kesimpulan: tidak ada single bottleneck — semua step berkontribusi merata. Bottleneck utama adalah **3x network round-trip ke Google** (2x Gemini + 1x embedding API).

---

## 6. Fast Path Optimization

Insight: kalau hanya KB yang aktif, LLM #1 pasti akan memanggil `search_knowledge` anyway — tidak perlu tanya dulu.

**Implementasi fast path:**
```
Sebelum:  LLM #1 decide → search_knowledge → LLM #2 answer  (~6.6s)
Sesudah:  search_knowledge → LLM #1 answer                   (~3.5s)
```

Kondisi fast path aktif:
- Hanya `search_knowledge` yang di-enable, ATAU
- Strict mode ON + `search_knowledge` aktif

**Hasil: ~50% lebih cepat** (6.6s → 3.2–3.8s)

---

## 7. Refactor Tools ke Module Terpisah

`backend/app/core/tools.py` (satu file besar) dipecah jadi package `backend/app/core/tools/`:

| File | Isi |
|---|---|
| `base.py` | Base class & helper shared |
| `search_knowledge.py` | Tool pencarian KB (ChromaDB) |
| `search_web.py` | Tool pencarian web (Tavily) |
| `microservice.py` | Tool untuk microservice eksternal |
| `__init__.py` | Export semua tool |

Keuntungan: setiap tool terisolasi, mudah ditambah tool baru tanpa edit file yang sama.

---

## 8. Microservice Tool System

Tools untuk microservice eksternal kini **data-driven** — tidak perlu tulis kode Python untuk tambah tool baru. Cukup daftarkan endpoint di `backend/microservices.json`:

```json
{
  "name": "send_notification",
  "description": "...",
  "endpoint": "http://localhost:8001/notify",
  "method": "POST",
  "args_schema": { ... },
  "response_schema": { ... }
}
```

Microservices yang sudah terdaftar: `send_notification`, `get_random_number`, `crud_data`.

Backend baca file JSON saat startup → generate LangChain tools otomatis.
`dummy_services/routes/search.py` dihapus karena sudah tidak dipakai.

---

## 9. Web Search Tool (Tavily)

Ditambahkan tool `search_web` menggunakan **Tavily API**:
- Tambah `TAVILY_API_KEY` di `.env.example` dan `config.py`
- Tambah `tavily-python==0.5.0` di `requirements.txt`
- Tool tersedia di toggle list di frontend

---

## 10. Dark Mode

Seluruh UI frontend mendukung dark mode dengan toggle di navbar:

- `ThemeContext` (`frontend/src/context/ThemeContext.tsx`) — context + localStorage persistence
- `App.tsx` dibungkus `ThemeProvider`, ada tombol toggle ☀️/🌙 di header
- Semua komponen (`ChatWindow`, `ChatPage`, `ChatInput`, `KnowledgeList`, `KnowledgeUpload`) sudah pakai Tailwind `dark:` variants
- `index.css` menambah `dark` class support

---

## 11. Fix Retrieval Service

`backend/app/services/retrieval.py` direfactor untuk akses ChromaDB secara langsung (`chromadb.PersistentClient`) menggantikan `get_vectorstore()` — lebih stabil dan tidak bergantung pada LangChain wrapper.

---

## Tech Stack

- **Backend:** FastAPI + LangGraph (ReAct agent) + ChromaDB + Gemini 2.5 Flash
- **Embedding:** gemini-embedding-001
- **Frontend:** React + Tailwind v4
- **Pattern:** RAG klasik (fast path) + ReAct agent (multi-tool)
- **Web Search:** Tavily API

---

## 12. Web Search Sources di Response

`search_web` tool diubah untuk mengembalikan output dalam dua format sekaligus:
- **Human-readable** untuk LLM (untuk dijadikan jawaban)
- **JSON block** `[web_sources_json]...[/web_sources_json]` untuk ekstraksi di `react_agent.py`

`react_agent.py` menambahkan fungsi `_extract_sources_from_web_result()` yang parse JSON block ini dan populate `sources` di response. Schema `Source` ditambah field `url` optional — web sources tampil sebagai link yang bisa diklik (↗) di frontend.

---

## 13. Score Threshold Dinaikkan 0.5 → 0.6

Threshold relevance ChromaDB dinaikkan dari 0.5 ke 0.6 di dua tempat:
- `rag_chain.py` (fast path)
- `tools/search_knowledge.py` (ReAct agent path)

Alasan: reduce false positives — lebih baik bilang "tidak tahu" daripada jawab dengan dokumen yang tidak relevan.

---

## 14. React Router Migration

Navigasi frontend dimigrasi dari tab state (`useState<Tab>`) ke `react-router-dom`:
- `App.tsx` sekarang pakai `<Routes>` + `<Route>` + `<NavLink>`
- `ChatPage` menerima `messages`, `setMessages`, `sessionId`, `setSessionId` sebagai props (state di-lift ke `AppInner`)
- Memungkinkan deep linking dan browser back/forward navigation

---

## 15. Agent Steps Log di Frontend

`ChatWindow.tsx` ditambah komponen `AgentStepsLog` untuk menampilkan progress tool calls secara real-time:
- Types baru: `StepStatus`, `AgentStep`, `DisplayMessage` (diekspor)
- Status: `tool_requested` → `tool_approved/cancelled` → `tool_executing` → `tool_done`
- AbortSignal support di `chat.ts` untuk cancel request yang sedang berjalan

---

## Key Learnings

1. **ReAct agent itu mahal** — setiap tool call = +1 LLM round-trip
2. **Prompt saja tidak cukup** — Gemini tetap conservative meski diperintah via system prompt, butuh logic di backend
3. **Score threshold penting** — tanpa threshold, ChromaDB selalu return hasil meski tidak relevan
4. **Fast path > flexibility** untuk use case sederhana — skip LLM decision step kalau toolnya sudah pasti
5. **Data-driven tools** — daftar microservice di JSON jauh lebih scalable daripada hardcode per tool
6. **ThemeContext + localStorage** — pola standar untuk dark mode di React tanpa library tambahan
