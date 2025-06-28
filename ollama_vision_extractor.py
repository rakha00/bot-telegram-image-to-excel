"""
Modul untuk mengekstrak tabel dari gambar menggunakan model vision lokal
yang dijalankan melalui Ollama (misalnya, LLaVA).
"""
import ollama
import pandas as pd
import json
import base64
import os

def get_image_base64(image_path: str) -> str:
    """Mengonversi file gambar menjadi string base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_ollama_prompt():
    """Membangun prompt instruksi untuk ekstraksi dan analisis tabel."""
    return """
    Analisis gambar yang diberikan dengan saksama. Fokus utama Anda adalah pada **ekstraksi tabel yang akurat dan lengkap**, terutama untuk dokumen keuangan yang kompleks seperti neraca atau laporan laba rugi.

    Tugas Anda adalah:
    1.  **Deteksi dan Ekstrak SEMUA Tabel**: Identifikasi setiap tabel dalam gambar.
    2.  **Tangani Struktur Kompleks**: Berikan perhatian khusus pada:
        *   **Header Multi-Level**: Kenali jika sebuah kolom memiliki beberapa tingkat header (misalnya, 'Neraca Saldo' yang memiliki sub-kolom 'Debit' dan 'Kredit').
        *   **Baris Hirarkis**: Pahami baris yang merupakan kategori utama (misalnya, 'ASET LANCAR') dan sub-barisnya (misalnya, 'Kas', 'Piutang'). Pertahankan struktur ini.
        *   **Sel yang Digabung (Merged Cells)**: Interpretasikan sel yang digabung dengan benar, baik secara horizontal maupun vertikal.
        *   **Baris Total dan Subtotal**: Identifikasi baris yang berisi total atau subtotal dan pastikan mereka ditempatkan dengan benar dalam struktur data.
    3.  **Berikan Analisis**: Untuk setiap tabel, berikan analisis singkat yang merangkum tujuan dan poin-poin penting dari tabel tersebut.

    **Format Output JSON yang Diperlukan**:
    - Sebuah list utama. Setiap elemen dalam list adalah objek yang mewakili satu tabel.
    - Setiap objek tabel HARUS memiliki dua kunci: `analysis` dan `data`.
    - `analysis`: Sebuah string teks yang berisi ringkasan atau wawasan dari data tabel.
    - `data`: Sebuah list dari list, di mana setiap list dalam merepresentasikan satu baris dalam tabel.
        - **PENTING**: Baris pertama (atau beberapa baris pertama) HARUS mewakili header tabel secara lengkap, termasuk header multi-level jika ada.
        - Pertahankan baris kosong jika itu adalah bagian dari struktur tabel untuk memisahkan bagian-bagian.
        - Jangan menghilangkan baris total atau subtotal.

    **Contoh untuk Tabel Keuangan Kompleks**:
    [
      {
        "analysis": "Tabel ini adalah neraca saldo yang menunjukkan saldo debit dan kredit untuk setiap akun, beserta jurnal penyesuaian dan saldo setelah penyesuaian.",
        "data": [
          ["No", "Nama Akun", "Neraca Saldo", "", "Jurnal Penyesuaian", "", "Neraca Saldo Setelah Disesuaikan", ""],
          ["", "", "Debit", "Kredit", "Debit", "Kredit", "Debit", "Kredit"],
          ["101", "Kas", "61,700,000", "", "1,600,000", "", "63,300,000", ""],
          ["102", "Piutang Usaha", "20,500,000", "", "", "", "20,500,000", ""],
          ["", "Jumlah", "154,860,000", "154,860,000", "29,900,000", "29,900,000", "169,260,000", "169,260,000"]
        ]
      }
    ]

    Jika tidak ada tabel yang ditemukan, kembalikan list JSON kosong: `[]`.
    Hanya kembalikan output dalam format JSON mentah tanpa penjelasan atau format tambahan seperti ```json ... ```.
    """

async def extract_tables_with_ollama(image_path: str, model_name: str = 'qwen2.5vl:latest') -> list[tuple[pd.DataFrame, str]]:
    """
    Mengekstrak dan menganalisis tabel dari gambar menggunakan model vision lokal via Ollama.

    Args:
        image_path: Path ke file gambar.
        model_name: Nama model Ollama yang akan digunakan.

    Returns:
        Daftar tuple, di mana setiap tuple berisi (DataFrame, analysis_string).
    """
    try:
        client = ollama.AsyncClient()
        image_b64 = get_image_base64(image_path)
        prompt_text = generate_ollama_prompt()

        response = await client.generate(
            model=model_name,
            prompt=prompt_text,
            images=[image_b64],
            format='json'
        )
        
        json_string = response.get('response', '{}')
        
        if not json_string.strip():
            return []

        tables_data = json.loads(json_string)
        
        if isinstance(tables_data, dict):
            tables_data = [tables_data]

        if not isinstance(tables_data, list):
            return []

        results = []
        for table_obj in tables_data:
            if isinstance(table_obj, dict) and "data" in table_obj and "analysis" in table_obj:
                data = table_obj.get("data")
                analysis = table_obj.get("analysis", "Tidak ada analisis yang diberikan.")
                
                if data and len(data) > 1:
                    header = data[0]
                    table_data = data[1:]
                    df = pd.DataFrame(table_data, columns=header)
                    results.append((df, analysis))
        
        return results

    except ollama.ResponseError as e:
        print(f"Error dari server Ollama: {e.error}")
        if "model not found" in e.error:
            print(f"Pastikan model '{model_name}' sudah di-pull dengan 'ollama run {model_name}'")
        return []
    except Exception as e:
        print(f"Error saat berkomunikasi dengan Ollama: {e}")
        return []