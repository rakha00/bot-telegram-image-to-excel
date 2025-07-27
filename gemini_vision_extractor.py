"""
Modul untuk mengekstrak tabel keuangan dari file PDF menggunakan Google Gemini Vision API
dan mengubahnya menjadi JSON terstruktur.
"""
import os
import json
import google.generativeai as genai
import fitz  # PyMuPDF
import PIL.Image

def configure_gemini():
    """Konfigurasi Gemini API dengan kunci dari environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY tidak ditemukan di environment variables.")
    genai.configure(api_key=api_key)

def generate_financial_statement_prompt():
    """Menghasilkan prompt yang disesuaikan untuk mengekstrak neraca keuangan."""
    return """
    Anda adalah seorang analis keuangan ahli. Tugas Anda adalah mengekstrak data keuangan dari gambar neraca ("NERACA") yang disediakan.
    Ubah tabel menjadi objek JSON yang terstruktur.

    Objek JSON harus memiliki dua kunci utama: "2023" dan "2022", yang mewakili tahun-tahun tersebut.
    Nilai setiap tahun harus berupa objek yang berisi kategori-kategori keuangan.

    Ikuti struktur ini:
    - Kunci tingkat atas harus merupakan bagian utama seperti "aset_lancar", "aset_tidak_lancar", "liabilitas_jangka_pendek", "liabilitas_jangka_panjang", dan "ekuitas". Gunakan snake_case untuk semua kunci.
    - Setiap bagian harus berisi objek di mana kunci adalah item baris (misalnya, "kas_dan_setara_kas", "investasi") dan nilai adalah angka yang sesuai. Gunakan snake_case untuk semua kunci.
    - Sajikan angka sebagai integer atau float, hapus semua titik yang digunakan sebagai pemisah ribuan.
    - Jika nilai tidak ada untuk suatu tahun (misalnya, tanda hubung '-'), sajikan sebagai `null`.
    - Gabungkan semua bagian neraca menjadi satu objek JSON untuk halaman tersebut.
    - Hanya kembalikan objek JSON akhir, tanpa penjelasan, markdown, atau teks tambahan.
    - Pastikan format JSON benar dan dapat di-parse.
    """

def clean_gemini_response(text: str) -> str:
    """Membersihkan respons teks dari Gemini untuk memastikan itu adalah JSON yang valid."""
    # Hapus markdown code block
    if '```json' in text:
        text = text.split('```json')[1]
    if '```' in text:
        text = text.split('```')[0]
    
    # Hapus karakter non-printable dan strip whitespace
    return ''.join(char for char in text if char.isprintable()).strip()

async def extract_json_from_pdf(pdf_path: str, model_name: str = 'gemini-1.5-flash') -> str:
    """
    Mengekstrak tabel keuangan dari halaman pertama PDF dan mengembalikan string JSON.
    """
    try:
        configure_gemini()

        # Buka PDF dan ubah halaman pertama menjadi gambar menggunakan PyMuPDF
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)  # 0 adalah indeks untuk halaman pertama
        pix = page.get_pixmap(dpi=300)  # Tingkatkan DPI untuk kualitas gambar yang lebih baik
        doc.close()

        # Buat objek gambar PIL dari data piksel
        image = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        if not image:
            return json.dumps({"error": "Gagal mengonversi PDF ke gambar."})
        
        model = genai.GenerativeModel(model_name)
        prompt = generate_financial_statement_prompt()

        # Hasilkan konten dari model
        response = await model.generate_content_async([prompt, image])
        
        # Bersihkan dan parse respons
        cleaned_text = clean_gemini_response(response.text)
        
        try:
            # Validasi dengan memuatnya sebagai JSON
            parsed_json = json.loads(cleaned_text)
            # Kembalikan sebagai string JSON yang diformat dengan baik
            return json.dumps(parsed_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            return json.dumps({
                "error": "Gagal mem-parse JSON dari respons Gemini.",
                "raw_response": cleaned_text
            })

    except Exception as e:
        print(f"Terjadi kesalahan di extract_json_from_pdf: {e}")
        return json.dumps({"error": f"Gagal memproses PDF: {e}"})