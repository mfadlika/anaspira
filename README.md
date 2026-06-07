# Sistem Analisis Aspirasi Warga

Aplikasi full-stack berbasis Python untuk mengolah aspirasi, keluhan, serta masukan warga desa dari Google Form, Google Sheets, formulir digital, atau media sosial menjadi insight yang terstruktur.

## Fitur

- Import data dari CSV atau Excel.
- Import data langsung dari Google Sheets atau response sheet Google Form yang sudah dipublikasikan sebagai CSV.
- Preprocessing teks Bahasa Indonesia.
- Klasifikasi topik berbasis model semantik ringan + kata kunci.
- Analisis sentimen berbasis leksikon dengan penanganan negasi.
- Ekstraksi kata kunci dengan TF-IDF.
- Penilaian urgensi untuk membantu prioritas kebijakan.
- Dashboard interaktif untuk melihat tren dan detail aspirasi.
- API FastAPI untuk ingest, query, summary, dan prioritas.
- Database SQLite lokal untuk menyimpan hasil analisis.

## Struktur Data yang Disarankan

Kolom minimal:

- `tanggal`
- `sumber`
- `nama`
- `teks`

Kolom lain akan tetap dipertahankan jika ada.

## Menjalankan Aplikasi

1. Buat environment Python.
2. Install dependensi:

```bash
pip install -r requirements.txt
```

3. Jalankan backend API:

```bash
python run_backend.py
```

```bash
python run_all.py
```

4. Jalankan dashboard:

```bash
streamlit run app.py
```

Dashboard akan berjalan di `http://localhost:8501`, sedangkan API tersedia di `http://localhost:3000`.

Jika Anda sedang berada di folder `backend/`, jalankan API dengan:

```bash
uvicorn main:app --reload
```

## Integrasi Google Form / Google Sheets

Google Form biasanya menyimpan respons ke Google Sheets. Di dashboard, pilih mode `Google Sheets / Form responses` lalu tempel URL spreadsheet yang sudah dipublikasikan sebagai CSV. Jika Anda memakai endpoint API, gunakan `POST /ingest/google-sheets` with payload JSON berikut:

```json
{
  "url": "https://docs.google.com/spreadsheets/d/ID_SPREADSHEET/edit#gid=0",
  "replace_existing": true
}
```

URL akan dikonversi otomatis ke format ekspor CSV jika spreadsheet dapat diakses publik.

## Endpoint API

- `GET /health`
- `POST /ingest/sample`
- `POST /ingest/file`
- `POST /ingest/google-sheets`
- `POST /ingest/records`
- `GET /records`
- `GET /summary`
- `GET /priorities`
- `DELETE /records`

## Catatan Implementasi

Pendekatan NLP di proyek ini memakai model semantik ringan berbasis TF-IDF char n-gram untuk topik, ditambah leksikon sentimen dengan negasi agar lebih stabil untuk bahasa warga sehari-hari. Struktur ini tetap ringan dan bisa dikembangkan ke model transformer Bahasa Indonesia jika nanti dibutuhkan.

