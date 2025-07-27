"""
Modul untuk mengekstrak tabel dari gambar menggunakan Google Gemini Vision API,
dan mengubahnya menjadi JSON mentah.
"""
import asyncio
import json
import os

import fitz  # PyMuPDF untuk membuka PDF
import google.generativeai as genai
import PIL.Image


async def extract_json_from_pdf(pdf_path: str, model_name: str = 'gemini-1.5-flash') -> str:
    try:
        configure_gemini()
        model = genai.GenerativeModel(model_name)
        prompt = generate_gemini_prompt()
        
        doc = fitz.open(pdf_path)
        all_json_responses = []

        for page_num in range(doc.page_count):
            page = doc[page_num]
            pix = page.get_pixmap()
            img = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            response_stream = await model.generate_content_async([prompt, img], stream=True)
            
            full_chunk_response = []
            async for chunk in response_stream:
                if chunk.text:
                    full_chunk_response.append(chunk.text)
            
            page_json_string = "".join(full_chunk_response)
            
            # --- TAMBAHKAN BARIS INI UNTUK DEBUGGING ---
            print(f"\n--- Raw Gemini Response (Page {page_num+1}) ---")
            print(page_json_string)
            print("-------------------------------------------\n")
            # ---------------------------------------------

            try:
                page_data = json.loads(page_json_string)
                all_json_responses.append(page_data)
            except json.JSONDecodeError as e:
                print(f"Peringatan: Halaman {page_num+1} gagal mem-parse JSON. Error: {e}. Respons: {page_json_string}")
                # Kirimkan pesan error yang lebih informatif ke pemanggil
                all_json_responses.append({
                    "page": page_num + 1,
                    "error": "Gagal mem-parse JSON dari respons Gemini.",
                    "raw_gemini_response": page_json_string,
                    "parse_error_details": str(e)
                })
            except Exception as page_e:
                print(f"Error memproses JSON halaman {page_num+1}: {page_e}")
                all_json_responses.append({"page": page_num + 1, "error": str(page_e)})

        doc.close()
        return json.dumps(all_json_responses, indent=2)

    except Exception as e:
        print(f"Error saat mengekstrak JSON dari PDF: {e}")
        return json.dumps({"error": f"Kesalahan internal di extractor: {e}"})
    
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

async def get_json_output(image_path: str) -> str:
    """
    Processes an image and returns the full JSON output as a single string.
    This is a helper for calling the streaming function from a synchronous context.
    """
    full_response = []
    async for chunk in stream_json_output(image_path):
        full_response.append(chunk)
    return "".join(full_response)