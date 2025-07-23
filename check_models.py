import os

import google.generativeai as genai

# PENTING: Ganti dengan API key Gemini Anda yang sebenarnya.
# Disarankan untuk menggunakan variabel lingkungan di produksi: os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY = "AIzaSyCfz8_6eLVOig7ILRgbXwMlG0toY-_--ng" 

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY tidak diatur. Harap atur API key Anda.")
    exit()

genai.configure(api_key=GEMINI_API_KEY)

print("Mencantumkan model Gemini yang tersedia:")
try:
    for m in genai.list_models():
        # Periksa apakah model mendukung generateContent dan menerima input teks
        if 'generateContent' in m.supported_generation_methods and \
           m.input_token_limit_protos and \
           m.input_token_limit_protos[0].token_limit:
            print(f"  Nama: {m.name}")
            print(f"  Deskripsi: {m.description}")
            print(f"  Metode yang didukung: {m.supported_generation_methods}")
            print(f"  Token input maksimum: {m.input_token_limit_protos[0].token_limit}")
            print("-" * 30)
except Exception as e:
    print(f"Terjadi kesalahan saat mencantumkan model: {e}")
    print("Pastikan API key Anda benar dan memiliki izin yang sesuai.")

