# Pengenalan RAG (Retrieval-Augmented Generation)

## Apa itu RAG?

RAG adalah singkatan dari **Retrieval-Augmented Generation**, sebuah teknik dalam kecerdasan buatan yang menggabungkan dua komponen utama:

1. **Retrieval (Pengambilan)** — sistem mencari informasi relevan dari knowledge base
2. **Generation (Pembuatan)** — LLM menggunakan informasi yang ditemukan untuk menghasilkan jawaban

## Mengapa RAG Penting?

LLM (Large Language Model) memiliki keterbatasan:
- Pengetahuan terbatas pada data training (knowledge cutoff)
- Tidak bisa mengakses informasi privat atau spesifik perusahaan
- Rentan terhadap hallucination (mengarang fakta)

RAG mengatasi keterbatasan ini dengan memberi LLM akses ke dokumen eksternal secara real-time.

## Cara Kerja RAG

1. User mengajukan pertanyaan
2. Sistem mengkonversi pertanyaan menjadi vector (embedding)
3. Vector digunakan untuk mencari dokumen paling relevan di database
4. Dokumen relevan dikirim sebagai konteks ke LLM
5. LLM menghasilkan jawaban berdasarkan konteks tersebut

## Komponen Utama RAG

| Komponen | Fungsi |
|---|---|
| Embedding Model | Mengkonversi teks ke representasi vector |
| Vector Store | Menyimpan dan mencari dokumen berdasarkan kesamaan vector |
| LLM | Menghasilkan jawaban natural dari konteks yang ditemukan |
| Chunking | Memecah dokumen panjang menjadi potongan kecil |

## Keunggulan RAG

- Jawaban selalu up-to-date sesuai knowledge base
- Bisa menggunakan dokumen privat dan internal
- Mengurangi hallucination karena berbasis sumber nyata
- Mudah diperbarui tanpa perlu melatih ulang model
