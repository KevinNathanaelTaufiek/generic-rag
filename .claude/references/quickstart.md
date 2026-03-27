# Quickstart

## Menjalankan Backend

```bash
cd backend
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

Pastikan `.env` sudah di-setup (lihat `.env.example`). Virtual env aktif sebelum run.

## Menjalankan Dummy Service

```bash
cd dummy_services
uvicorn main:app --port 8001 --reload
# → http://localhost:8001/ui
```

## Menjalankan Frontend

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

## Menjalankan Keduanya Sekaligus

Buka 2 terminal terpisah, jalankan masing-masing command di atas.

## Setelah Ganti EMBEDDING_PROVIDER

Wajib reindex agar data lama ter-embed ulang:

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/reindex
```
