# Feedback Loop & Learning System

Panduan untuk Claude dalam belajar dari interaksi dengan user di project ini.

---

## Kapan Menyimpan Memory

Simpan ke memory system (`~/.claude/projects/.../memory/`) ketika:

- User mengoreksi pendekatan kamu ("jangan begitu", "salah", "harusnya X")
- User mengkonfirmasi pendekatan non-obvious ("ya tepat", "bagus pertahankan itu")
- User menyebutkan preferensi eksplisit tentang cara kerja
- User memberikan konteks bisnis yang tidak ada di kode

Jangan simpan ke memory:
- Info yang bisa di-derive dari kode (struktur, pola, API)
- State sementara atau in-progress work
- Detail yang sudah ada di CLAUDE.md

---

## Format Memory yang Baik

Untuk feedback/koreksi:
```
Rule: [aturan yang harus diikuti]
Why: [alasan user memberikan koreksi ini]
How to apply: [kapan/di mana rule ini berlaku]
```

---

## Aturan Pengambilan Keputusan

### Keputusan Teknis (implementasi)
1. Cari referensi valid di internet jika tidak yakin
2. Baca decisions.md untuk constraint yang sudah ada
3. Hanya implementasi jika sudah yakin 100%

### Keputusan Bisnis/Arsitektur
1. JANGAN langsung implementasi
2. Tanya user dengan format:
   - Jelaskan konteks masalah
   - Berikan 2-3 opsi konkret
   - Untuk setiap opsi: plus dan minus
   - Rekomendasikan salah satu dengan alasan

### Template Pertanyaan ke User

```
Untuk [fitur/keputusan ini], ada beberapa pendekatan:

**Opsi A: [nama]**
+ [kelebihan 1]
+ [kelebihan 2]
- [kekurangan 1]

**Opsi B: [nama]**
+ [kelebihan 1]
- [kekurangan 1]
- [kekurangan 2]

Saya rekomendasikan **Opsi A** karena [alasan singkat]. Kamu pilih mana?
```

---

## After Each Session Checklist

Setelah sesi selesai, tanya diri sendiri:
- [ ] Ada koreksi dari user? → Simpan ke memory (type: feedback)
- [ ] Ada keputusan arsitektur baru? → Update `.claude/decisions.md`
- [ ] Ada request fitur baru yang diimplementasi? → Update `.claude/requests.md`
- [ ] Ada info project yang berubah? → Update memory (type: project)
