# Microservices Tool Tutorial

Panduan lengkap untuk menambah, mengubah, atau menghapus tool microservice di Generic RAG.

---

## Cara Kerja

Tools microservice dikonfigurasi sepenuhnya via satu file JSON:

```
backend/microservices.json
```

Setiap entry di file ini otomatis menjadi tool yang bisa dipakai LLM — **tanpa perlu ubah kode Python**.

Saat backend start, `tools/__init__.py` membaca file ini dan membangun tool secara dinamis via `MicroserviceTool`.

---

## Struktur Satu Entry

```json
{
  "name": "nama_tool",
  "description": "Deskripsi untuk LLM — jelaskan apa yang dilakukan tool ini.",
  "endpoint": "http://host:port/path",
  "method": "POST",
  "args_schema": { ... },
  "response_schema": { ... },
  "args_example": { ... },
  "response_example": { ... }
}
```

### Field Wajib

| Field | Tipe | Keterangan |
|---|---|---|
| `name` | string | Identifier unik. Dipakai LLM dan frontend. Gunakan `snake_case`. |
| `description` | string | Deskripsi tool untuk LLM. Makin jelas, makin akurat LLM memanggilnya. |
| `endpoint` | string (URL) | Full URL endpoint. Contoh: `http://localhost:8001/notify` |
| `method` | string | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `args_schema` | JSON Schema object | Schema input tool. Lihat bagian [Args Schema](#args-schema). |
| `response_schema` | JSON Schema object | Schema response yang diharapkan. Dipakai untuk validasi runtime. |
| `args_example` | object | Contoh args valid. Harus lolos validasi terhadap `args_schema`. |
| `response_example` | object | Contoh response valid. Harus lolos validasi terhadap `response_schema`. |

---

## Args Schema

Mengikuti standar [JSON Schema Draft-07](https://json-schema.org/draft-07/json-schema-validation.html) dengan satu extension: **`x-param-style`**.

### Struktur Dasar

```json
"args_schema": {
  "type": "object",
  "properties": {
    "field_name": {
      "type": "string",
      "description": "Penjelasan field untuk LLM",
      "x-param-style": "body"
    }
  },
  "required": ["field_name"]
}
```

### Tipe Data yang Didukung

| JSON Schema type | Python type | Contoh nilai |
|---|---|---|
| `"string"` | `str` | `"hello"` |
| `"integer"` | `int` | `42` |
| `"number"` | `float` | `3.14` |
| `"boolean"` | `bool` | `true` |
| `"object"` | `dict` | `{"key": "value"}` |
| `"array"` | `list` | `["a", "b", "c"]` |

Untuk enum (pilihan terbatas), gunakan keyword `"enum"`:
```json
"action": {
  "type": "string",
  "enum": ["create", "read", "update", "delete"],
  "description": "Operation to perform",
  "x-param-style": "body"
}
```

### `x-param-style` — Wajib di Setiap Field

Menentukan bagaimana field dikirim ke endpoint:

| Nilai | Dikirim sebagai | Contoh |
|---|---|---|
| `"body"` | JSON request body | `POST /notify` dengan `{"to": "...", "message": "..."}` |
| `"path"` | Path variable di URL | `GET /users/{user_id}` → `GET /users/123` |
| `"query"` | Query string | `GET /search?q=foo&limit=5` |

**Wajib explicit di setiap field** — tidak ada default.

#### Contoh `path` variable

Endpoint harus mengandung `{field_name}` sebagai template:

```json
{
  "endpoint": "http://localhost:8001/users/{user_id}",
  "method": "GET",
  "args_schema": {
    "type": "object",
    "properties": {
      "user_id": {
        "type": "string",
        "description": "User ID to retrieve",
        "x-param-style": "path"
      }
    },
    "required": ["user_id"]
  }
}
```

#### Contoh `query` param

```json
{
  "endpoint": "http://localhost:8001/search",
  "method": "GET",
  "args_schema": {
    "type": "object",
    "properties": {
      "q": {
        "type": "string",
        "description": "Search query",
        "x-param-style": "query"
      },
      "limit": {
        "type": "integer",
        "description": "Max results to return. Default: 10",
        "default": 10,
        "x-param-style": "query"
      }
    },
    "required": ["q"]
  }
}
```

### Optional Fields

Field yang **tidak** ada di array `required` dianggap optional.

- Jika field punya `"default"`, nilai default itu yang dipakai jika LLM tidak mengisi.
- Jika tidak ada `"default"`, field bernilai `null` jika tidak diisi dan tidak dikirim ke body.

```json
"properties": {
  "message": {
    "type": "string",
    "description": "Optional message. Default: empty string",
    "default": "",
    "x-param-style": "body"
  }
},
"required": []
```

---

## Response Schema

Sama dengan JSON Schema standar, tanpa `x-param-style`. Dipakai untuk **validasi runtime**.

```json
"response_schema": {
  "type": "object",
  "properties": {
    "success":   { "type": "boolean" },
    "message":   { "type": "string" },
    "data":      { "type": "object" }
  },
  "required": ["success"]
}
```

Jika response dari microservice tidak sesuai schema, LLM menerima:
```
Error: <tool_name> returned an unexpected response format — <detail>.
Raw response: <json string>
```

---

## Menambah Tool Baru

1. Tambah entry baru di `microservices.json`
2. Validate schema (lihat [Validasi](#validasi))
3. Restart backend — tool otomatis tersedia

Contoh tool baru `get_weather`:

```json
{
  "name": "get_weather",
  "description": "Get current weather for a city.",
  "endpoint": "http://localhost:8002/weather",
  "method": "GET",
  "args_schema": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "City name to get weather for",
        "x-param-style": "query"
      }
    },
    "required": ["city"]
  },
  "response_schema": {
    "type": "object",
    "properties": {
      "city":        { "type": "string" },
      "temperature": { "type": "number" },
      "condition":   { "type": "string" }
    },
    "required": ["city", "temperature", "condition"]
  },
  "args_example": { "city": "Jakarta" },
  "response_example": { "city": "Jakarta", "temperature": 30.5, "condition": "Sunny" }
}
```

---

## Validasi

Setiap kali mengubah `microservices.json`, jalankan validasi:

```bash
cd backend
python -c "
import json, jsonschema

with open('microservices.json') as f:
    services = json.load(f)

for svc in services:
    jsonschema.validate(svc['args_example'], svc['args_schema'])
    jsonschema.validate(svc['response_example'], svc['response_schema'])
    print(f'  OK: {svc[\"name\"]}')

print('All valid.')
"
```

---

## `args_example` dan LLM

`args_example` otomatis di-inject ke dalam deskripsi tool yang dilihat LLM **hanya jika** schema mengandung field bertipe `object` atau `array`.

Untuk schema sederhana (semua field string/integer), example tidak di-inject karena LLM sudah cukup mengerti dari `description` masing-masing field.
