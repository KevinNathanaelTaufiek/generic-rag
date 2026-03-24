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

## [2026-03-24] Multi-User, Audit Trail, Tool Args Editing, General Knowledge Flag

**Request:**
> Rangkum semua perubahan, update docs / .claude

**Perubahan yang dilakukan:**

### Backend
- **User identity**: `X-Username` header di `/chat` dan `/chat/tool-approval` — audit per user tanpa auth
- **Audit trail**: SQLite (`data/audit.db`) via SQLAlchemy — catat setiap tool approval/rejection dengan `ai_suggested_args` vs `user_edited_args`
- **`GET /api/v1/audit`**: query audit log dengan filter username, tool_name, date range, pagination
- **`GET /api/v1/users`**: return `predefined_users` dari config
- **`modified_args` di tool approval**: user bisa edit args sebelum approve; `resume_agent()` pass ke `interrupt()` return value sebagai dict
- **`get_pending_info()`**: helper untuk ambil interrupt payload sebelum resume (dibutuhkan untuk audit)
- **`from_general_knowledge` flag**: backend detect `[GENERAL_KNOWLEDGE]` marker di LLM response; strip marker sebelum dikirim ke client
- **`[GENERAL_KNOWLEDGE]` token di system prompt**: semua prompt variant instruksikan LLM untuk tambah token ini jika jawab dari training knowledge
- **Strict mode improvement**: langsung refuse jika LLM skip tool call tanpa search_knowledge
- **Multi-topic search**: system prompt update — instruksikan LLM call `search_knowledge` per topik, jawab bagian yang ditemukan
- **`_build_description()`**: generalized menjadi `tool_name(args_str)` format instead of hardcoded per tool
- **`AgentState`**: tambah field `from_general_knowledge: bool`
- `config.py`: tambah `predefined_users: list[str]` setting

### Frontend
- **UserContext + UserSwitcher**: user picker popover di navbar — pilih dari predefined users, simpan ke localStorage
- **Zustand store (`chatStore.ts`)**: migrasi chat state dari `useState`/props-drilling ke Zustand; per-user message history (`userMessages: Record<string, DisplayMessage[]>`)
- **`ChatPage`**: tidak lagi terima props — semua state dari store; `setMessagesForUser()` untuk update per-user
- **`AuditPage`**: tabel audit dengan filter username/tool/date, expand args diff (AI suggested vs user edited)
- **`ArgEditor` component**: edit tool args di approval card sebelum approve — type-aware (string/number/boolean/object/array)
- **`ToolApprovalCard`**: tampilkan editable args; `onApprove` sekarang pass `modifiedArgs`
- **Message timestamp + actor label**: setiap bubble chat tampilkan "You · 12:34" / "Assistant · 12:34"
- **`from_general_knowledge` warning badge**: warning ⚠ di bawah assistant message jika jawaban bukan dari knowledge base
- **axios interceptor**: inject `X-Username` header dari localStorage di setiap request
- **Routing**: tambah `/audit` route di `App.tsx`; chat state tidak lagi di-lift ke `App` (dipegang Zustand)

**File baru:**
- `backend/app/api/v1/audit.py`
- `backend/app/api/v1/users.py`
- `backend/app/db.py`
- `backend/app/services/audit.py`
- `frontend/src/api/audit.ts`
- `frontend/src/api/users.ts`
- `frontend/src/components/UserSwitcher.tsx`
- `frontend/src/context/UserContext.tsx`
- `frontend/src/pages/AuditPage.tsx`
- `frontend/src/store/chatStore.ts`

**File yang diubah:**
- `backend/app/api/v1/chat.py` — X-Username header, audit logging, modified_args, from_general_knowledge
- `backend/app/api/v1/router.py` — daftarkan audit + users router
- `backend/app/config.py` — predefined_users setting
- `backend/app/core/react_agent.py` — modified_args support, general_knowledge flag, strict mode, multi-topic prompt
- `backend/app/main.py` — startup event: create_db()
- `backend/app/schemas/chat.py` — from_general_knowledge field, modified_args field
- `frontend/src/App.tsx` — UserProvider, UserSwitcher, /audit route, state tidak di-lift
- `frontend/src/api/chat.ts` — from_general_knowledge, modified_args types
- `frontend/src/api/client.ts` — X-Username interceptor
- `frontend/src/components/ChatWindow.tsx` — ArgEditor, timestamp, actor label, general_knowledge badge
- `frontend/src/pages/ChatPage.tsx` — Zustand store, setMessagesForUser, modifiedArgs di handleApprove
- `.claude/decisions.md` — ADR-010 sampai ADR-014

**ADR baru:** ADR-010 (SQLite audit), ADR-011 (X-Username header), ADR-012 (Zustand), ADR-013 (editable tool args), ADR-014 ([GENERAL_KNOWLEDGE] marker)

---

## [2026-03-24] Audit Trail Fix, manage_task Tool, Dynamic Tool Registry

**Request:**
> - Fix badge "edited" di audit trail yang muncul meski user tidak edit args
> - Buat tool `manage_task` sebagai pengganti `crud_data` untuk testing multiple args, nested array, nested object
> - Tool list di frontend diambil dari backend (dynamic), bukan hardcode
> - Fix Gemini error: array field harus punya `items`

**Perubahan yang dilakukan:**

### Bug Fix — Audit "edited" badge
- `services/audit.py`: `log_tool_approval()` hanya set `changes` jika `user_edited_args != ai_suggested_args`. Sebelumnya selalu di-set meskipun identik.

### manage_task Tool
- `dummy_services/routes/tasks.py`: route baru `POST /tasks/manage` (create/update/delete/list) + `GET /tasks` untuk UI polling. Menggantikan `data.py`.
- `dummy_services/main.py`: swap `data` → `tasks`, tambah serve static (`/ui`, `/static`)
- `dummy_services/static/index.html`: Task Manager UI standalone — auto-refresh tiap 2s dengan toggle Pause/Resume
- `dummy_services/requirements.txt`: tambah `aiofiles`
- `backend/microservices.json`: ganti `crud_data` → `manage_task` dengan 5 args (`action`, `task_id`, `title`, `tags: array`, `metadata: object`)

### Dynamic Tool Registry
- `backend/app/api/v1/chat.py`: tambah `GET /api/v1/chat/tools` — return semua tool dari registry (search_knowledge + search_web + microservices)
- `frontend/src/api/chat.ts`: tambah `fetchTools()` + `ToolInfo` interface
- `frontend/src/store/chatStore.ts`: `ALL_TOOLS` tidak lagi hardcode — diisi runtime via `setAllTools()`
- `frontend/src/pages/ChatPage.tsx`: hapus `TOOL_LABELS`/`TOOL_DESCRIPTIONS` hardcode; fetch dari backend on mount; label auto-format via `toLabel()`

### Fix Gemini Array Schema
- `backend/app/core/tools/microservice.py`:
  - `_json_schema_to_pydantic()`: array field kini pakai `list[<item_type>]` typed — LangChain generate schema dengan `items` field (required by Gemini)
  - `_ensure_array_items()`: safety net — auto-inject `items: {type: string}` ke config jika missing
- `backend/microservices.json`: tambah `"items": {"type": "string"}` di field `tags`

**File baru:**
- `dummy_services/routes/tasks.py`
- `dummy_services/static/index.html`

**ADR baru:** ADR-015 (dynamic tool registry), ADR-016 (manage_task dummy service)

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
