# Dokumentasi API Laporan Keuangan

API ini digunakan untuk memproses data laporan keuangan dan laba rugi dari berbagai format file (gambar, PDF, DOCX) atau input JSON langsung, dan mengubahnya menjadi format JSON yang terstruktur.

## Endpoints

### 1. Laporan Keuangan (Neraca)

Endpoint ini memproses data neraca (laporan posisi keuangan), baik untuk jenis syariah maupun konvensional. Logika pemrosesan untuk kedua endpoint ini identik.

- **URL:**
  - `/balance-sheet/ep/laporan-keuangan/syariah`
  - `/balance-sheet/ep/laporan-keuangan/konvensional`
- **Metode:** `POST`
- **Deskripsi:** Menerima file (gambar, PDF, DOCX) atau data JSON mentah dari laporan posisi keuangan dan mengembalikannya dalam format JSON yang terstruktur.

#### Permintaan (Request)

Anda dapat mengirim data dengan salah satu dari dua cara berikut:

1.  **Multipart Form Data (`multipart/form-data`)**
    - **Key:** `file`
    - **Value:** File laporan keuangan Anda.
    - **Tipe File yang Diizinkan:** `.png`, `.jpg`, `.jpeg`, `.gif`, `.pdf`, `.doc`, `.docx`

2.  **JSON Body (`application/json`)**
    - Kirimkan array JSON yang berisi data laporan. Kunci utama yang diharapkan adalah `"Akun"` dan kunci lain yang merepresentasikan tahun (misalnya, `"2022"`, `"2023"`).

    **Contoh JSON Input:**
    ```json
    [
      {
        "Akun": "Kas dan setara kas",
        "2023": "100.000",
        "2022": "95.000"
      },
      {
        "Akun": "Piutang bunga",
        "2023": "10.000",
        "2022": "8.000"
      }
    ]
    ```

#### Respon Sukses (200 OK)

- **Content-Type:** `application/json`
- **Deskripsi:** Mengembalikan objek JSON yang berisi status pemrosesan dan data yang telah diekstraksi dan distrukturkan per tahun.

**Contoh Respon:**
```json
{
    "status": "SUCCESS",
    "reason": "Data Successfully Processed",
    "read": [
        {
            "year": 2022,
            "cash_and_cash_equivalents": {
                "value": "95000",
                "confidence": null
            },
            "interest_receivable": {
                "value": "8000",
                "confidence": null
            },
            ... // bidang lain sesuai urutan
        },
        {
            "year": 2023,
            "cash_and_cash_equivalents": {
                "value": "100000",
                "confidence": null
            },
            "interest_receivable": {
                "value": "10000",
                "confidence": null
            },
            ... // bidang lain sesuai urutan
        }
    ]
}
```

---

### 2. Laporan Laba Rugi

Endpoint ini memproses data laporan laba rugi, baik untuk jenis syariah maupun konvensional. Logika pemrosesan untuk kedua endpoint ini identik.

- **URL:**
  - `/balance-sheet/ep/laba-rugi/syariah`
  - `/balance-sheet/ep/laba-rugi/konvensional`
- **Metode:** `POST`
- **Deskripsi:** Menerima file (gambar, PDF, DOCX) atau data JSON mentah dari laporan laba rugi dan mengembalikannya dalam format JSON yang terstruktur.

#### Permintaan (Request)

Sama seperti endpoint laporan keuangan, data dapat dikirim melalui `multipart/form-data` atau `application/json`.

#### Respon Sukses (200 OK)

- **Content-Type:** `application/json`
- **Deskripsi:** Mengembalikan objek JSON yang berisi status dan data laba rugi yang terstruktur.

**Contoh Respon:**
```json
{
    "status": "SUCCESS",
    "reason": "Data Successfully Processed",
    "read": [
        {
            "year": 2022,
            "interest_income": {
                "value": "500000",
                "confidence": null
            },
            ... // bidang lain sesuai urutan
        },
        {
            "year": 2023,
            "interest_income": {
                "value": "550000",
                "confidence": null
            },
            ... // bidang lain sesuai urutan
        }
    ]
}
```

---

### 3. Unduh File JSON

Endpoint ini memungkinkan pengguna untuk mengunduh file hasil pemrosesan yang telah disimpan sebelumnya (meskipun fungsionalitas penyimpanan tidak diimplementasikan secara eksplisit di endpoint POST).

- **URL:** `/api/download/<filename>`
- **Metode:** `GET`
- **Deskripsi:** Mengunduh file JSON tertentu dari direktori `output` di server.

#### Parameter URL

- `filename` (string, wajib): Nama file JSON yang akan diunduh. Contoh: `hasil_laporan.json`.

#### Respon Sukses (200 OK)

- **Content-Type:** `application/json`
- **Content-Disposition:** `attachment; filename=<filename>`
- **Deskripsi:** Mengembalikan file JSON yang diminta sebagai lampiran.

---

## Respon Kesalahan (Error Responses)

API dapat mengembalikan kode status HTTP berikut untuk kesalahan:

- **400 Bad Request:**
  - Jika tidak ada file yang dipilih (`{"error": "No selected file"}`).
  - Jika tipe file tidak diizinkan (`{"error": "File type not allowed"}`).
  - Jika data JSON yang dikirim tidak valid (`{"error": "Invalid JSON data in request body."}`).
  - Jika permintaan tidak berisi file atau data JSON (`{"error": "Request must contain either a valid file or JSON data."}`).

- **404 Not Found:**
  - Jika tidak ada data tahunan yang ditemukan dalam input (`{"status": "FAILED", "reason": "No year data found in the data."}`).
  - Jika file yang diminta untuk diunduh tidak ada.

- **415 Unsupported Media Type:**
  - Jika header `Content-Type` tidak sesuai (bukan `multipart/form-data` atau `application/json`).

- **500 Internal Server Error:**
  - Jika terjadi kesalahan tak terduga di server (`{"error": "<deskripsi kesalahan>"}`).
