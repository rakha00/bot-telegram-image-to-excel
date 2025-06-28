"""
Modul untuk mengekstrak tabel dari gambar menggunakan model vision lokal
yang dijalankan melalui Ollama (misalnya, LLaVA).
"""
import ollama
import pandas as pd
import json
import base64
import os
import asyncio

def get_image_base64(image_path: str) -> str:
    """Mengonversi file gambar menjadi string base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_ollama_prompt():
    """Membangun prompt instruksi untuk menghasilkan skrip Python mentah."""
    return """
    **PERINTAH TEGAS: MISI UTAMA ANDA ADALAH MEREPLIKASI STRUKTUR TABEL SECARA SEMPURNA.**

    Tugas Anda adalah mengubah gambar tabel menjadi **skrip Python** yang menghasilkan file Excel. Akurasi adalah segalanya. Skrip yang Anda hasilkan harus menciptakan kembali tabel **persis** seperti di gambar.

    **ATURAN WAJIB**:
    1.  **Output HANYA Kode**: Respons Anda HARUS hanya berisi kode Python mentah. Jangan sertakan penjelasan, komentar, atau format markdown seperti ```python ... ```.
    2.  **Replikasi 1:1**: Skrip harus menggunakan `pandas` dan `openpyxl` untuk membuat file Excel yang merupakan cerminan sempurna dari gambar.
    3.  **Aturan Penggabungan Ketat**: HANYA gabungkan sel jika ada bukti visual yang jelas.
    4.  **Fungsi Wajib**: Skrip HARUS berisi fungsi `create_excel(output_path: str)`.

    **Contoh Output Sempurna (Hanya Teks Ini)**:
    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import Font, Alignment

    def create_excel(output_path: str):
        data = [
            ['ASET', None, '2007', 'KEWAJIBAN DAN EKUITAS', None, '2007'],
            ['ASET LANCAR', None, None, 'EKUITAS', None, None],
            ['Kas dan Bank', '37.021.114', None, 'Modal Saham 800 saham, Disetor dan Dibayar Penuh 100 saham', None, '100.000.000'],
            ['Piutang Lain-lain', '72.500.000', None, 'Nilai Nominal Rp. 1.000.000,- per saham', None, None],
            ['Persediaan', '51.600.000', None, 'Laba ditahan', None, '6.582.427.859'],
            ['Jumlah Aset Lancar', '161.121.114', None, 'Laba (Rugi) Tahun Berjalan', None, '2.030.943.255'],
            [None, None, None, 'Total Ekuitas', None, '8.713.371.114'],
            ['ASET TETAP', None, None, None, None, None],
            ['Tanah', '4.200.000.000', None, None, None, None],
            ['Mesin dan Instalasi', '4.115.000.000', None, None, None, None],
            ['Bangunan Pabrik', '4.185.000.000', None, None, None, None],
            ['Total', '12.500.000.000', None, None, None, None],
            ['Akumulasi penyusutan', '(3.947.750.000)', None, None, None, None],
            ['Nilai Buku Aset Tetap', '8.552.250.000', None, None, None, None],
            ['TOTAL ASET', '8.713.371.114', None, 'TOTAL KEWAJIBAN DAN EKUITAS', None, '8.713.371.114']
        ]
        df = pd.DataFrame(data)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Neraca', index=False, header=False)
            # ... (sisa logika penggabungan sel dan gaya)
    """

async def stream_excel_script(image_path: str, model_name: str = 'qwen2.5vl:latest'):
    """
    Menghasilkan skrip Python secara streaming untuk membuat file Excel dari gambar.

    Args:
        image_path: Path ke file gambar.
        model_name: Nama model Ollama yang akan digunakan.

    Yields:
        Potongan (chunk) dari skrip Python yang dihasilkan.
    """
    try:
        client = ollama.AsyncClient()
        image_b64 = get_image_base64(image_path)
        prompt_text = generate_ollama_prompt()

        options = {
            'num_predict': 4096
        }

        stream = await client.generate(
            model=model_name,
            prompt=prompt_text,
            images=[image_b64],
            options=options,
            stream=True
        )
        async for chunk in stream:
            if 'response' in chunk:
                yield chunk['response']

    except asyncio.TimeoutError:
        print("Error: Waktu pemrosesan Ollama habis (timeout).")
        yield ""
    except Exception as e:
        print(f"Error saat streaming dari Ollama: {e}")
        yield ""