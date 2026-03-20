# Tool Use (ReAct System) — Design Spec
**Date:** 2026-03-20
**Status:** Approved

---

## Context

Saat ini Generic RAG hanya bisa menjawab pertanyaan berbasis knowledge base (retrieve → generate). Tidak ada kemampuan untuk melakukan aksi nyata seperti mencari di web, mengirim notifikasi, atau memanipulasi data.

Fitur ini menambahkan **ReAct agent loop** sehingga sistem bisa:
1. Mendeteksi intent user yang membutuhkan aksi (tool call)
2. Meminta persetujuan user sebelum mengeksekusi tool (human-in-the-loop)
3. Mengeksekusi tool via REST call ke microservices
4. Melanjutkan reasoning berdasarkan hasil tool

Dummy microservices disediakan sebagai standalone app terpisah, mensimulasikan microservices asli yang belum bisa diakses.

---

## Architecture

### Flow Utama

```
User message
     ↓
backend generate thread_id (UUID, per approval transaction)
     ↓
graph.invoke(input, config={"configurable": {"thread_id": thread_id}})
     ↓
[agent_node]  ← LLM + tool definitions
     ↓ jika LLM pilih tool → raise NodeInterrupt
[INTERRUPT] ← graph pause, MemorySaver simpan state
     ↓ backend kembalikan status=pending_tool_approval + thread_id + pending_tool
     ↓ frontend: render approval card, disable ChatInput
[User: Approve / Cancel]
     ↓ POST /chat/tool-approval {thread_id, approved}
     ↓ backend: graph.update_state(config, {"tool_approved": approved})
     ↓ backend: graph.invoke(None, config) → resume dari interrupt
     ↓ Approve → [tool_executor_node] → HTTP call → result → agent_node → loop/END
     ↓ Cancel  → agent_node dengan context "user cancelled" → minta klarifikasi → END
     ↓ backend kembalikan ToolApprovalResponse (blocking, tunggu agent selesai)
```

**Multi-step tool calls:** Setiap tool call menghasilkan interrupt baru dengan `thread_id` baru. Frontend menangani approval card secara sequential — satu per satu.

**Jika Cancel:** Graph di-resume dengan injected message: `"User cancelled tool execution. Ask the user what went wrong or how it should be done differently."` LLM reply minta klarifikasi, hasilnya dikembalikan ke frontend sebagai response normal.

**Jika Tool Error:** `tool_executor_node` tangkap exception, set `tool_error` di state. LLM diberi context error dan decide: inform user, retry suggestion, atau fallback.

**Jika `thread_id` tidak ditemukan di `MemorySaver`** (stale atau duplikat): endpoint `/chat/tool-approval` kembalikan HTTP 400 dengan pesan error. Frontend tampilkan pesan bahwa approval sudah kadaluarsa.

### Error Types (Tool Execution)

| Error | Handling |
|---|---|
| HTTP 4xx | LLM inform user bahwa input tidak valid |
| HTTP 5xx | LLM suggest retry |
| Timeout (>10s) | LLM inform user koneksi gagal |
| Exception lain | Generic error message ke user |

---

## File Structure

### New Files

```
generic-rag/
├── backend/app/
│   ├── core/
│   │   ├── react_agent.py     ← LangGraph ReAct agent
│   │   └── tools.py           ← Tool registry & executors
│   ├── api/v1/
│   │   └── chat.py            ← UPDATE: tambah /tool-approval endpoint
│   └── schemas/
│       └── chat.py            ← UPDATE: tambah ToolCallInfo, ToolApprovalRequest/Response
│
└── dummy_services/             ← NEW: standalone microservice simulator (port 8001)
    ├── main.py
    ├── routes/
    │   ├── search.py          ← POST /search
    │   ├── notify.py          ← POST /notify
    │   └── data.py            ← POST /data (in-memory CRUD)
    └── requirements.txt       ← fastapi, uvicorn, pydantic
```

### Modified Files (Backend)

- `backend/app/config.py` — tambah `dummy_services_base_url: str = "http://localhost:8001"`
- `backend/app/api/v1/chat.py` — tambah endpoint `/chat/tool-approval`, update `/chat` untuk gunakan `react_agent`
- `backend/app/schemas/chat.py` — update `ChatResponse`, tambah `ToolApprovalRequest`, `ToolApprovalResponse`
- `backend/app/core/rag_chain.py` — tetap ada dan tidak diubah (untuk referensi)

### Modified Files (Frontend)

- `frontend/src/api/chat.ts` — tambah `approveToolCall(threadId, approved): Promise<ToolApprovalResponse>`
- `frontend/src/pages/ChatPage.tsx` — handle `pending_tool_approval` state, disable input saat pending
- `frontend/src/components/ChatWindow.tsx` — render tool approval card inline

---

## Schema

### `schemas/chat.py` (additions)

```python
class ToolCallInfo(BaseModel):
    tool_name: str
    tool_args: dict
    description: str  # human-readable: "Searching web for: 'Jakarta cuaca'"

class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]  # empty list saat status=pending_tool_approval
    session_id: str
    status: Literal["done", "pending_tool_approval"]  # NEW
    pending_tool: ToolCallInfo | None = None           # set saat pending
    thread_id: str | None = None                       # set saat pending, untuk resume

class ToolApprovalRequest(BaseModel):
    thread_id: str
    session_id: str
    approved: bool

class ToolApprovalResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    session_id: str                                    # sama dengan request session_id, untuk konsistensi dengan ChatResponse
    status: Literal["done", "pending_tool_approval"]  # bisa ada loop tool berikutnya
    pending_tool: ToolCallInfo | None = None
    thread_id: str | None = None
```

**`/chat/tool-approval` adalah blocking endpoint** — ia tidak return sampai agent selesai atau interrupt lagi untuk tool berikutnya. Frontend menampilkan spinner, kemudian render response final atau approval card berikutnya.

**`sources`** dalam response: hanya diisi dari RAG retrieval. Pada agent path yang tidak melakukan RAG, `sources` adalah empty list.

---

## LangGraph Agent State

```python
class AgentState(TypedDict):
    # LangChain messages — source of truth untuk LLM context
    # Diinisialisasi dari client `history` saat graph pertama kali di-invoke
    messages: Annotated[list, add_messages]

    # Tool approval state — diisi saat interrupt/resume
    pending_tool_call: dict | None    # info tool yang di-interrupt
    tool_approved: bool | None        # diset via graph.update_state() sebelum resume

    # RAG sources (opsional, hanya ada jika agent melakukan retrieval)
    sources: list[dict]
```

**`session_id` vs `thread_id`:**
- `session_id` — identitas sesi chat user (persistent across turns, dari client)
- `thread_id` — identitas satu approval transaction (UUID baru per interrupt, dibuang setelah resolved)

**Checkpoint:** `MemorySaver` (in-memory). Cukup untuk MVP karena thread hanya hidup selama satu approval cycle (beberapa detik). Jika backend restart, pending approval hilang → frontend perlu handle HTTP 400 dari `/tool-approval` dan inform user untuk kirim ulang.

**Resume pseudocode:**
```python
# Saat interrupt (di /chat endpoint):
from langgraph.types import interrupt
thread_id = str(uuid4())
config = {"configurable": {"thread_id": thread_id}}
result = await graph.ainvoke(input, config)
# Cek graph.get_state(config).next → ada interrupt → kembalikan pending_tool_approval ke frontend
# Di dalam agent_node: approved = interrupt(pending_info)  ← pauses here, returns resume value

# Saat approval (di /chat/tool-approval endpoint):
from langgraph.types import Command
config = {"configurable": {"thread_id": request.thread_id}}
# resume: Command(resume=approved) menjadi return value dari interrupt() di agent_node
result = await graph.ainvoke(Command(resume=request.approved), config)
# Cek graph.get_state(config).next lagi → ada interrupt baru (loop) atau selesai
```

**Catatan:** Gunakan `Command(resume=value)`, bukan `aupdate_state + ainvoke(None)`. Pattern `aupdate_state + ainvoke(None)` hanya untuk `interrupt_before=[...]` compile-time breakpoints, bukan untuk `interrupt()` dinamis di dalam node.

---

## Tool Definitions

### `core/tools.py`

```python
TOOLS = [
    StructuredTool(
        name="search_web",
        description="Search the web for information about a topic or recent events. Use when the user asks about something not in the knowledge base.",
        args_schema=SearchWebInput,        # {"query": str}
        func=search_web_executor,
    ),
    StructuredTool(
        name="send_notification",
        description="Send a notification or message to a recipient.",
        args_schema=SendNotificationInput, # {"to": str, "message": str}
        func=send_notification_executor,
    ),
    StructuredTool(
        name="crud_data",
        description="Create, read, update, or delete data in an external system. Action must be one of: create, read, update, delete.",
        args_schema=CRUDDataInput,         # {"action": Literal["create","read","update","delete"], "resource": str, "data": dict}
        func=crud_data_executor,
    ),
]
```

Setiap executor panggil `dummy_services_base_url` via `httpx.AsyncClient(timeout=10.0)`.

**Note tentang `strict_mode`:** Dalam ReAct agent mode, `strict_mode` tidak diterapkan — parameter tersebut hanya relevan untuk RAG generation node. Agent bebas menggunakan tool dan general knowledge LLM.

---

## Dummy Microservices

**App:** `dummy_services/main.py`, port 8001. Dependencies: `fastapi`, `uvicorn`, `pydantic`.

| Endpoint | Method | Input | Response |
|---|---|---|---|
| `/search` | POST | `{"query": str}` | `{"results": [{"title": str, "snippet": str, "url": str}]}` (3 fake results) |
| `/notify` | POST | `{"to": str, "message": str}` | `{"sent": true, "to": str, "timestamp": str}` |
| `/data` | POST | `{"action": str, "resource": str, "data": dict}` | `{"success": true, "action": str, "resource": str, "data": dict \| list}` |

`/data` action enum: `create`, `read`, `update`, `delete`. Simpan di Python dict in-memory per resource name.

**Ganti ke microservices asli:** Update `DUMMY_SERVICES_BASE_URL` di `backend/.env`. Tidak ada perubahan kode.

---

## Frontend UI

### Tool Approval Card (`ChatWindow.tsx`)

Ketika `message.status === "pending_tool_approval"`, tampilkan card:

```
┌─────────────────────────────────────────────┐
│ 🔧 System ingin menjalankan tool:            │
│                                              │
│   search_web                                │
│   → Searching web for: "cuaca Jakarta"      │
│                                              │
│   [✓ Approve]          [✗ Cancel]           │
└─────────────────────────────────────────────┘
```

Setelah user respond, card diganti dengan status text ("Executed" / "Cancelled").

### ChatInput State

`ChatInput` **harus disabled** ketika `status === "pending_tool_approval"` (sama seperti `loading`). Ini mencegah race condition dari user mengirim pesan baru saat graph sedang di-pause.

---

## Architecture Decisions (untuk `.claude/decisions.md`)

**ADR-005 — MemorySaver untuk interrupt state**
- Pilih `MemorySaver` (in-memory) bukan persistent storage
- Alasan: thread_id hanya hidup selama approval cycle (detik), tidak perlu persistence
- Trade-off: pending approval hilang jika backend restart

**ADR-006 — Dummy microservices sebagai app terpisah**
- Pilih folder `dummy_services/` di root, bukan endpoint di backend
- Alasan: mensimulasikan deployment separation yang nyata, mudah di-replace dengan URL asli
- Migration: ganti `DUMMY_SERVICES_BASE_URL` di `.env`

---

## Verification

1. **Start dummy services:** `cd dummy_services && uvicorn main:app --port 8001`
2. **Start backend:** `cd backend && uvicorn app.main:app --port 8000`
3. **Start frontend:** `cd frontend && npm run dev`

**Test cases:**
- Pesan "Cari info terbaru tentang AI" → approval card muncul, ChatInput disabled → approve → search results tampil di chat
- Pesan "Kirim notifikasi ke admin tentang laporan" → approval card muncul → cancel → LLM tanya klarifikasi
- Pesan "Simpan data user baru: nama Kevin" → approval card muncul → approve → confirmation tampil
- Pesan pertanyaan normal ("Apa itu RAG?") → RAG path, tidak ada approval card, sources tampil
- Dummy service di-stop → tool executor gagal → error message informatif di chat
- Submit approval dua kali (atau `thread_id` stale) → HTTP 400, frontend tampilkan pesan expired
