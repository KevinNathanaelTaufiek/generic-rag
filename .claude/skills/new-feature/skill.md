# Skill: new-feature

Digunakan ketika user meminta fitur baru, endpoint baru, atau perubahan arsitektur pada project generic-rag.

**Trigger:** Gunakan skill ini ketika user menyebut kata kunci seperti:
- "tambah fitur", "buat fitur", "implement fitur"
- "endpoint baru", "API baru"
- "tambah support X", "integrate X"
- "buat halaman baru", "tambah komponen"

---

## Langkah-langkah

### 1. Baca Context
Sebelum apapun, baca file-file ini untuk memahami constraint dan pola yang sudah ada:
- `.claude/prd.md` — scope MVP dan fitur yang sudah ada
- `.claude/decisions.md` — keputusan arsitektur yang tidak boleh dilanggar
- `.claude/requests.md` — log request sebelumnya (hindari duplikasi)

### 2. Analisis Request
Tentukan:
- Termasuk kategori fitur apa? (lihat tabel extensibility di CLAUDE.md)
- Apakah ada keputusan bisnis/arsitektur yang perlu dikonfirmasi?
- Apakah ada ambiguitas yang perlu ditanya ke user?

### 3. Jika Ada Keputusan yang Perlu Dikonfirmasi
Gunakan format dari `.claude/feedback_loop.md`:
- Presentasikan 2-3 opsi dengan plus/minus
- Rekomendasikan satu opsi
- Tunggu konfirmasi sebelum implementasi

### 4. Update requests.md
Tambahkan entry baru ke `.claude/requests.md` dengan format:

```
## [Tanggal] — [Nama Fitur]
**Request:** [deskripsi singkat]
**Keputusan:** [pendekatan yang dipilih]
**File yang diubah:** [list file]
```

### 5. Implementasi
Ikuti pola extensibility sesuai tabel di CLAUDE.md. Jangan rombak arsitektur yang sudah ada kecuali ada alasan kuat dan sudah dikonfirmasi user.

### 6. Update decisions.md (jika ada keputusan baru)
Jika implementasi ini membuat keputusan arsitektur baru, tambahkan ADR baru ke `.claude/decisions.md`.
