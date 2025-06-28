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
    Analisis gambar yang diberikan dengan saksama.
    Tugas Anda adalah mendeteksi SEMUA tabel yang ada di dalam gambar, mengekstrak datanya, DAN memberikan analisis singkat untuk setiap tabel.

    Format output Anda HARUS berupa JSON dengan struktur berikut:
    - Sebuah list utama yang berisi semua tabel yang ditemukan.
    - Setiap elemen dalam list adalah sebuah objek yang mewakili satu tabel.
    - Setiap objek tabel memiliki DUA kunci: "analysis" dan "data".
    - Nilai dari "analysis" adalah sebuah string teks yang berisi ringkasan atau wawasan dari data tabel.
    - Nilai dari "data" adalah sebuah list dari list, di mana setiap list dalam merepresentasikan satu baris dalam tabel. Baris pertama HARUS menjadi header.

    Contoh:
    [
      {
        "analysis": "Tabel ini menunjukkan penjualan produk berdasarkan wilayah, dengan penjualan tertinggi di wilayah Utara.",
        "data": [
          ["Produk", "Wilayah", "Penjualan"],
          ["A", "Utara", 150],
          ["B", "Selatan", 120]
        ]
      }
    ]

    Jika tidak ada tabel yang ditemukan, kembalikan list JSON kosong: [].
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