import io
import json
import os

from flask import Flask, jsonify, request

# --- Import untuk PDF dan OCR (Perlu instalasi manual di lingkungan Anda) ---
# Jika PDF Anda berisi teks yang dapat dipilih, PyPDF2 cukup.
# Jika PDF Anda hasil scan (gambar), Anda memerlukan Tesseract dan pytesseract.
try:
    from PyPDF2 import PdfReader

    # from PIL import Image # Untuk OCR gambar PDF (perlu Pillow)
    # import pytesseract # Untuk OCR gambar PDF (perlu Tesseract OCR Engine)
    # from pdf2image import convert_from_path # Untuk mengubah PDF ke gambar (perlu poppler-utils)
except ImportError:
    print("Peringatan: PyPDF2, Pillow, pytesseract, atau pdf2image tidak ditemukan.")
    print("Pemrosesan PDF mungkin terbatas, terutama untuk dokumen hasil scan.")
    print("Instal dengan: pip install PyPDF2 Pillow pytesseract pdf2image")

# --- Import untuk Google Gemini ---
try:
    import google.generativeai as genai
except ImportError:
    print("Peringatan: pustaka google-generativeai tidak ditemukan.")
    print("Integrasi Gemini tidak akan berfungsi.")
    print("Instal dengan: pip install google-generativeai")

app = Flask(__name__)

# --- Konfigurasi API Key Gemini ---
# PENTING: Jangan hardcode API key di kode produksi. Gunakan variabel lingkungan!
# Contoh: os.getenv("GEMINI_API_KEY")
# Untuk tujuan demonstrasi, ini akan disisipkan di sini.
GEMINI_API_KEY = "AIzaSyCfz8_6eLVOig7ILRgbXwMlG0toY-_--ng" 

gemini_model = None
if GEMINI_API_KEY and 'genai' in globals(): # Pastikan pustaka genai berhasil diimpor
    try:
        # Gunakan model yang sering tersedia dan cocok untuk generateContent
        # Ganti 'gemini-1.5-flash-latest' jika 'check_models.py' menunjukkan nama lain
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("Model Gemini berhasil diinisialisasi: gemini-1.5-flash-latest")
    except Exception as e:
        print(f"Error saat menginisialisasi model Gemini: {e}")
        print("Pastikan nama model benar dan API key valid.")
else:
    print("Error: GEMINI_API_KEY tidak diatur atau pustaka Gemini tidak dimuat.")

# Direktori untuk menyimpan file yang diunggah sementara
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload-and-process-pdf', methods=['POST'])
def upload_and_process_pdf():
    # Periksa apakah ada bagian 'pdf_file' dalam permintaan
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Tidak ada bagian 'pdf_file' dalam permintaan"}), 400

    pdf_file = request.files['pdf_file']

    # Periksa apakah nama file kosong
    if pdf_file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    # Pastikan file adalah PDF
    if pdf_file and pdf_file.filename.endswith('.pdf'):
        filepath = "" # Inisialisasi filepath
        try:
            # Simpan file yang diunggah sementara
            filepath = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
            pdf_file.save(filepath)
            print(f"File PDF disimpan sementara di: {filepath}")

            extracted_text = ""
            # --- Langkah 1: Ekstraksi Teks dari PDF ---
            # Jika PDF adalah teks, PyPDF2 akan bekerja.
            # Jika PDF adalah gambar (hasil scan), Anda perlu melakukan OCR gambar.
            if 'PdfReader' in globals(): # Pastikan PyPDF2 berhasil diimpor
                reader = PdfReader(filepath)
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                    else:
                        print(f"Peringatan: Halaman {page_num + 1} sepertinya adalah gambar atau tidak ada teks yang dapat diekstrak.")
                        print("Anda perlu mengimplementasikan OCR gambar di sini (misalnya, dengan pytesseract dan Pillow).")

            else:
                return jsonify({"error": "Pustaka PyPDF2 tidak ditemukan. Tidak dapat membaca PDF."}), 500

            if not extracted_text.strip():
                return jsonify({"error": "Tidak dapat mengekstrak teks apa pun dari PDF. Apakah itu dokumen hasil scan tanpa pengaturan OCR yang tepat?"}), 400

            print("Teks berhasil diekstrak dari PDF. Melanjutkan ke pemrosesan Gemini...")

            # --- Langkah 2: Gunakan Gemini untuk Mem-parsing Teks ---
            if not gemini_model:
                return jsonify({"error": "API Gemini tidak dikonfigurasi. Periksa API key atau inisialisasi model."}), 500

            prompt = f"""
            Anda adalah asisten yang ahli dalam menganalisis laporan keuangan, khususnya neraca.
            Ekstrak informasi neraca dari teks berikut. Pastikan Anda mengidentifikasi kategori utama (Aset, Liabilitas, Ekuitas),
            sub-kategori seperti 'Aset Lancar', 'Liabilitas Jangka Pendek', 'Modal Koperasi', dan item-item di dalamnya (misalnya, 'Kas dan setara kas', 'Simpanan pokok').
            Berikan nilai untuk tahun 2023 dan 2022.
            Sajikan output dalam format JSON yang bersih dan terstruktur. Nilai uang harus dalam string dan tanpa pemisah ribuan.
            Jika suatu item tidak memiliki data untuk tahun tertentu, gunakan null.

            Contoh struktur output JSON yang diharapkan:
            {{
              "header": {{
                "title": "NAMA KOPERASI",
                "report_type": "NERACA",
                "period": "Untuk Tahun Yang Berakhir 31 Desember TAHUN_SEKARANG",
                "comparison_period": "Dengan Angka Perbandingan TAHUN_SEBELUMNYA",
                "currency": "Disajikan dalam Rupiah, kecuali dinyatakan lain"
              }},
              "ASET": {{
                "Aset Lancar": {{
                  "Kas dan setara kas": {{ "2023": "nilai", "2022": "nilai" }},
                  "Pembiayaan kepada anggota": {{ "2023": "nilai", "2022": "nilai" }}
                  // ... item lainnya
                }},
                "Jumlah Aset Lancar": {{ "2023": "nilai", "2022": "nilai" }},
                "Aset Tidak Lancar": {{
                  "Investasi": {{ "2023": "nilai", "2022": "nilai" }}
                  // ... item lainnya
                }},
                "JUMLAH ASET": {{ "2023": "nilai", "2022": "nilai" }}
              }},
              "LIABILITAS DAN EKUITAS": {{
                "LIABILITAS": {{
                  "Liabilitas Jangka Pendek": {{
                    "Simpanan anggota": {{ "2023": "nilai", "2022": "nilai" }}
                    // ... item lainnya
                  }},
                  "Jumlah Liabilitas Jangka Pendek": {{ "2023": "nilai", "2022": "nilai" }},
                  "Liabilitas Jangka Panjang": {{
                    "Utang kepada anggota": {{ "2023": "nilai", "2022": "nilai" }}
                    // ... item lainnya
                  }},
                  "Jumlah Liabilitas Jangka Panjang": {{ "2023": "nilai", "2022": "nilai" }}
                }},
                "JUMLAH LIABILITAS": {{ "2023": "nilai", "2022": "nilai" }},
                "EKUITAS": {{
                  "Modal Koperasi": {{
                    "Simpanan pokok": {{ "2023": "nilai", "2022": "nilai" }}
                    // ... item lainnya
                  }},
                  "Jumlah Modal Koperasi": {{ "2023": "nilai", "2022": "nilai" }}
                }},
                "JUMLAH LIABILITAS DAN EKUITAS": {{ "2023": "nilai", "2022": "nilai" }}
              }}
            }}

            Teks Neraca:
            {extracted_text}
            """
            
            print("Mengirim permintaan ke Gemini API...")
            response = gemini_model.generate_content(prompt)
            print("Respons dari Gemini diterima.")
            
            # Ekstrak teks JSON dari respons Gemini
            raw_json_string = response.text
            
            # Bersihkan respons dari markdown (```json) dan prefix 'json\n'
            cleaned_json_string = raw_json_string.strip()
            if cleaned_json_string.startswith("```json") and cleaned_json_string.endswith("```"):
                cleaned_json_string = cleaned_json_string[7:-3].strip()
            
            # Tambahan: Tangani kasus di mana respons dimulai dengan "json\n"
            if cleaned_json_string.startswith("json\n"):
                cleaned_json_string = cleaned_json_string[len("json\n"):].strip()

            try:
                parsed_json_data = json.loads(cleaned_json_string)
                return jsonify(parsed_json_data), 200
            except json.JSONDecodeError as e:
                print(f"Error JSONDecodeError: {e}")
                print(f"Respons mentah Gemini: {cleaned_json_string}")
                return jsonify({"error": f"Gagal mengurai JSON dari respons Gemini: {str(e)}", "gemini_raw_response": cleaned_json_string}), 500

        except Exception as e:
            print(f"Terjadi kesalahan umum: {e}")
            return jsonify({"error": f"Terjadi kesalahan selama pemrosesan PDF atau interaksi Gemini: {str(e)}"}), 500
        finally:
            # Pastikan untuk membersihkan file yang diunggah meskipun ada kesalahan
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"File sementara dihapus: {filepath}")
    else:
        return jsonify({"error": "Tipe file tidak valid. Harap unggah file PDF."}), 400

if __name__ == '__main__':
    # Untuk menjalankan aplikasi Flask di lingkungan lokal Anda
    # host='0.0.0.0' akan membuat server dapat diakses dari luar localhost
    print("Memulai server Flask...")
    app.run(debug=True, host='127.0.0.1', port=5000)
