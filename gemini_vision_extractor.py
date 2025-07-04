"""
Modul untuk mengekstrak tabel dari gambar menggunakan Google Gemini Vision API,
dan mengubahnya menjadi JSON mentah.
"""
import os
import google.generativeai as genai
import PIL.Image
import asyncio

def configure_gemini():
    """Konfigurasi Gemini API dengan kunci dari environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY tidak ditemukan di file .env")
    genai.configure(api_key=api_key)

def generate_gemini_prompt():
    return """
    UBAH GAMBAR TABEL INI MENJADI JSON ARRAY OF OBJECTS (ARRAY BERISI DICTIONARY).
    - Baris pertama tabel adalah header/kolom, gunakan sebagai key di setiap object.
    - Setiap baris berikutnya adalah data, gunakan header sebagai key dan isi sel sebagai value.
    - Jika sel kosong, isi dengan null.
    - Hanya kembalikan JSON array of objects, tanpa penjelasan, tanpa markdown, tanpa teks tambahan.
    - Contoh:
    [
      {"Header1": "Data1", "Header2": null},
      {"Header1": "Data2", "Header2": "Data3"}
    ]
    """

async def stream_json_output(image_path: str, model_name: str = 'gemini-1.5-flash'):
    """
    Menghasilkan hasil JSON secara streaming dari gambar tabel menggunakan Gemini Vision.
    """
    try:
        configure_gemini()
        model = genai.GenerativeModel(model_name)
        prompt = generate_gemini_prompt()
        image = PIL.Image.open(image_path)

        response_stream = await model.generate_content_async([prompt, image], stream=True)
        
        async for chunk in response_stream:
            if chunk.text:
                print(chunk.text, end='', flush=True)
                yield chunk.text

    except Exception as e:
        print(f"Error saat streaming dari Gemini: {e}")
        yield ""