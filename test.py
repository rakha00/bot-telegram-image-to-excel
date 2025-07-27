import io
import json
import os
from collections import OrderedDict

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request

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

load_dotenv()

app = Flask(__name__)

# --- Konfigurasi API Key Gemini ---
# PENTING: Jangan hardcode API key di kode produksi. Gunakan variabel lingkungan!
# Contoh: os.getenv("GEMINI_API_KEY")
# Untuk tujuan demonstrasi, ini akan disisipkan di sini.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

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

@app.route('/balance-sheet/ep/konvensional/posisi-keuangan', methods=['POST'])
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
            You are an expert assistant in analyzing financial reports, specifically balance sheets.
            Extract balance sheet information from the following text. Ensure you identify main categories (Assets, Liabilities, Equity),
            sub-categories like 'Current Assets', 'Short-Term Liabilities', 'Cooperative Capital', and items within them (e.g., 'Cash and cash equivalents', 'Principal savings').
            Provide values for the years 2023 and 2022.
            Present the output in a clean, structured JSON format. Monetary values should be strings without thousand separators.
            If an item does not have data for a specific year, use null.
            All keys and values in the JSON should be in English.

            The JSON output should have a top-level structure with 'status', 'reason', and 'read' fields.
            The 'read' field should be an array containing two objects, one for each year (2022 and 2023).
            Each financial item should be represented as an object with 'value' and 'confidence' (set to null) keys.

            Expected JSON output structure:
            {{
            "header": {{
                    "title": "COOPERATIVE NAME",
                    "report_type": "BALANCE SHEET",
                    "period": "For the Year Ended December 31, CURRENT_YEAR",
                    "comparison_period": "With Comparative Figures PREVIOUS_YEAR",
                    "currency": "Presented in Rupiah, unless otherwise stated"
                  }},
              "reason": "File Successfully read",
              "status": "Success",
              "read": [
                {{
                  "year": "2022",
                  "ASSETS": {{
                    "Current_Assets": {{
                      "Cash_and_cash_equivalents": {{ "value": "value", "confidence": null }},
                      "Financing_to_members": {{ "value": "value", "confidence": null }}
                      // ... other items
                    }},
                    "Total_Current_Assets": {{ "value": "value", "confidence": null }},
                    "Non-Current_Assets": {{
                      "Investments": {{ "value": "value", "confidence": null }}
                      // ... other items
                    }},
                    "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
                  }},
                  "LIABILITIES_AND_EQUITY": {{
                    "LIABILITIES": {{
                      "Short-Term_Liabilities": {{
                        "Member_deposits": {{ "value": "value", "confidence": null }}
                        // ... other items
                      }},
                      "Total_Short-Term_Liabilities": {{ "value": "value", "confidence": null }},
                      "Long-Term_Liabilities": {{
                        "Debt_to_members": {{ "value": "value", "confidence": null }}
                        // ... other items
                      }},
                      "Total_Long-Term_Liabilities": {{ "value": "value", "confidence": null }}
                    }},
                    "TOTAL_LIABILITIES": {{ "value": "value", "confidence": null }},
                    "EQUITY": {{
                      "Cooperative_Capital": {{
                        "Principal_savings": {{ "value": "value", "confidence": null }}
                        // ... other items
                      }},
                      "Total_Cooperative_Capital": {{ "value": "value", "confidence": null }}
                    }},
                    "TOTAL_LIABILITIES_AND_EQUITY": {{ "value": "value", "confidence": null }}
                  }}
                }},
                {{
                  "year": "2023",
                  "header": {{
                    "title": "COOPERATIVE NAME",
                    "report_type": "BALANCE SHEET",
                    "period": "For the Year Ended December 31, CURRENT_YEAR",
                    "comparison_period": "With Comparative Figures PREVIOUS_YEAR",
                    "currency": "Presented in Rupiah, unless otherwise stated"
                  }},
                  "ASSETS": {{
                    "Current_Assets": {{
                      "Cash_and_cash_equivalents": {{ "value": "value", "confidence": null }},
                      "Financing_to_members": {{ "value": "value", "confidence": null }}
                      // ... other items
                    }},
                    "Total_Current_Assets": {{ "value": "value", "confidence": null }},
                    "Non-Current_Assets": {{
                      "Investments": {{ "value": "value", "confidence": null }}
                      // ... other items
                    }},
                    "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
                  }},
                  "LIABILITIES_AND_EQUITY": {{
                    "LIABILITIES": {{
                      "Short-Term_Liabilities": {{
                        "Member_deposits": {{ "value": "value", "confidence": null }}
                        // ... other items
                      }},
                      "Total_Short-Term_Liabilities": {{ "value": "value", "confidence": null }},
                      "Long-Term_Liabilities": {{
                        "Debt_to_members": {{ "value": "value", "confidence": null }}
                        // ... other items
                      }},
                      "Total_Long-Term_Liabilities": {{ "value": "value", "confidence": null }}
                    }},
                    "TOTAL_LIABILITIES": {{ "value": "value", "confidence": null }},
                    "EQUITY": {{
                      "Cooperative_Capital": {{
                        "Principal_savings": {{ "value": "value", "confidence": null }}
                        // ... other items
                      }},
                      "Total_Cooperative_Capital": {{ "value": "value", "confidence": null }}
                    }},
                    "TOTAL_LIABILITIES_AND_EQUITY": {{ "value": "value", "confidence": null }}
                  }}
                }}
              ]
            }}

            Balance Sheet Text:
            {extracted_text}
            """
            
            print("Mengirim permintaan ke Gemini API...")
            response = gemini_model.generate_content(prompt)
            print("Respons dari Gemini diterima.")
            
            # Ekstrak teks JSON dari respons Gemini
            raw_json_string = response.text.strip()
            if raw_json_string.startswith("```json") and raw_json_string.endswith("```"):
                raw_json_string = raw_json_string[7:-3].strip()
            if raw_json_string.startswith("json\n"):
                raw_json_string = raw_json_string[len("json\n"):].strip()

            try:
                parsed_json_data = json.loads(raw_json_string)
                ordered = OrderedDict()
                ordered["header"] = parsed_json_data.get("header", {})
                ordered["reason"] = parsed_json_data.get("reason", "")
                ordered["status"] = parsed_json_data.get("status", "")
                ordered["read"] = parsed_json_data.get("read", [])
                json_string = json.dumps(ordered, ensure_ascii=False, indent=2)
                return Response(json_string, mimetype='application/json')
            except json.JSONDecodeError as e:
                print(f"Error JSONDecodeError: {e}")
                print(f"Respons mentah Gemini: {raw_json_string}")
                return jsonify({"error": f"Gagal mengurai JSON dari respons Gemini: {str(e)}", "gemini_raw_response": raw_json_string}), 500

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

@app.route('/balance-sheet/ep/syariah/posisi-keuangan', methods=['POST'])
def syariah_keuangan():
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
            You are an expert assistant in analyzing financial reports, specifically balance sheets.
Extract balance sheet information from the following Indonesian financial report text. Your job is to identify key sections such as 'ASSETS', 'LIABILITIES', and 'EQUITY'. Within those, identify subcategories like 'Current Assets', 'Non-Current Assets', 'Short-Term Liabilities', 'Long-Term Liabilities', and components of 'Equity' (e.g., Member Savings, Retained Earnings).

Here are the items you should specifically extract (case-insensitive match, English only):
- Cash (Kas)
- Placement in Other Banks (Penempatan pada Bank Lain)
- Receivables and Financing (Piutang dan Pembiayaan)
- Deferred Margin Revenue (Pendapatan Margin Ditangguhkan)
- Allowance for Impairment Losses (Penyisihan Piutang)

- Long-Term Investments (Investasi Jangka Panjang)
- Fixed Assets and Inventory (Asset Tetap dan Inventaris)
- Accumulated Depreciation (Akumulasi Penyusutan)
- Other Assets (Asset Lain - Lain)

- Member Deposits (Simpanan)
- Profit-Sharing Payables (Dana Pembagian SHU)
- Tax Payables (Hutang Pajak)
- Employee Benefits Liabilities (Kewajiban Imbalan Kerja)
- Other Liabilities (Kewajiban Lain - Lain)
- Long-Term Liabilities (Kewajiban Jangka Panjang)

- Member Savings (Simpanan Anggota)
- Donation Capital (Modal Donasi)
- Reserves (Cadangan-Cadangan)
- Current Year SHU (SHU Tahun Berjalan)

Output the result in structured JSON format with:
- Top-level fields: `status`, `reason`, `header`, and `read`.
- `header` should include:
  - `title`: "KSPPS BMT ASSYAFI'IYAH BERKAH NASIONAL"
  - `report_type`: "BALANCE SHEET"
  - `period`: "For the Year Ended December 31, 2023"
  - `comparison_period`: "With Comparative Figures 2022"
  - `currency`: "Presented in Rupiah, unless otherwise stated"

Each year (2023 and 2022) must be represented under the `read` array.
Each item should be represented using this structure: `{{ "value": "value", "confidence": null }}`.
If an item is missing, still include it with `"value": null`.

This is the expected output structure:
{{
  "status": "Success",
  "reason": "File Successfully read",
  "header": {{
    "title": "KSPPS BMT ASSYAFI'IYAH BERKAH NASIONAL",
    "report_type": "BALANCE SHEET",
    "period": "For the Year Ended December 31, 2023",
    "comparison_period": "With Comparative Figures 2022",
    "currency": "Presented in Rupiah, unless otherwise stated"
  }},
  "read": [
    {{
      "year": "2022",
      "ASSETS": {{
          "Cash": {{ "value": "value", "confidence": null }},
          "Placement_in_Other_Banks": {{ "value": "value", "confidence": null }},
          "Total_Current_Assets": {{ "value": "value", "confidence": null }},
          "Receivables_and_Financing": {{ "value": "value", "confidence": null }},
          "Deferred_Margin_Revenue": {{ "value": "value", "confidence": null }},
          "Allowance_for_Impairment_Losses": {{ "value": "value", "confidence": null }},
          "Total_Current_Assets2": {{ "value": "value", "confidence": null }},
          "Long_Term_Investments": {{ "value": "value", "confidence": null }},
          "Fixed_Assets_and_Inventory": {{ "value": "value", "confidence": null }},
          "Accumulated_Depreciation": {{ "value": "value", "confidence": null }},
          "Total_Current_Assets3": {{ "value": "value", "confidence": null }},
          "Other_Assets": {{ "value": "value", "confidence": null }}
        "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
      }},
        "LIABILITIES": {{
            "Member_Deposits": {{ "value": "value", "confidence": null }},
            "Profit_Sharing_Payables": {{ "value": "value", "confidence": null }},
            "Tax_Payables": {{ "value": "value", "confidence": null }},
            "Employee_Benefits_Liabilities": {{ "value": "value", "confidence": null }},
            "Other_Liabilities": {{ "value": "value", "confidence": null }}
          }},
          "Total_Term_Liabilities": {{ "value": "value", "confidence": null }},
          "Long_Term_Liabilities": {{ "value": "value", "confidence": null }}
        "EQUITY": {{
          "Member_Savings": {{ "value": "value", "confidence": null }},
          "Donation_Capital": {{ "value": "value", "confidence": null }},
          "Total_Modal": {{ "value": "value", "confidence": null }},
        }},
        "BALANCE_SHU"{{
          "reserves": {{ "value": "value", "confidence": null }},
          "Running_Year_SHU": {{ "value": "value", "confidence": null }},
          "Total_Balance_SHU": {{ "value": "value", "confidence": null }},
        }},
        "TOTAL_EQUITY": {{ "value": "value", "confidence": null }}
        "TOTAL_LIABILITIES_AND_EQUITY": {{ "value": "value", "confidence": null }}
    }},
    {{
      "year": "2023",
      "ASSETS": {{
          "Cash": {{ "value": "value", "confidence": null }},
          "Placement_in_Other_Banks": {{ "value": "value", "confidence": null }},
          "Total_Current_Assets": {{ "value": "value", "confidence": null }}
          "Receivables_and_Financing": {{ "value": "value", "confidence": null }},
          "Deferred_Margin_Revenue": {{ "value": "value", "confidence": null }},
          "Allowance_for_Impairment_Losses": {{ "value": "value", "confidence": null }},
          "Long_Term_Investments": {{ "value": "value", "confidence": null }},
          "Fixed_Assets_and_Inventory": {{ "value": "value", "confidence": null }},
          "Accumulated_Depreciation": {{ "value": "value", "confidence": null }},
          "Other_Assets": {{ "value": "value", "confidence": null }} 
        "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
      }},
      "LIABILITIES_AND_EQUITY": {{
        "LIABILITIES": {{
          "Short_Term_Liabilities": {{
            "Member_Deposits": {{ "value": "value", "confidence": null }},
            "Profit_Sharing_Payables": {{ "value": "value", "confidence": null }},
            "Tax_Payables": {{ "value": "value", "confidence": null }},
            "Employee_Benefits_Liabilities": {{ "value": "value", "confidence": null }},
            "Other_Liabilities": {{ "value": "value", "confidence": null }}
          }},
          "Total_Short_Term_Liabilities": {{ "value": "value", "confidence": null }},
          "Long_Term_Liabilities": {{
            "Long_Term_Liabilities": {{ "value": "value", "confidence": null }}
          }}
        }},
        "TOTAL_LIABILITIES": {{ "value": "value", "confidence": null }},
        "EQUITY": {{
          "Member_Savings": {{ "value": "value", "confidence": null }},
          "Donation_Capital": {{ "value": "value", "confidence": null }},
          "Reserves": {{ "value": "value", "confidence": null }},
          "Current_Year_SHU": {{ "value": "value", "confidence": null }},
          "TOTAL_EQUITY": {{ "value": "value", "confidence": null }}
        }},
        "TOTAL_LIABILITIES_AND_EQUITY": {{ "value": "value", "confidence": null }}
      }}
    }}
  ]
}}


            Balance Sheet Text:
            {extracted_text}
            """
            
            print("Mengirim permintaan ke Gemini API...")
            response = gemini_model.generate_content(prompt)
            print("Respons dari Gemini diterima.")
            
            # Ekstrak teks JSON dari respons Gemini
            raw_json_string = response.text.strip()
            if raw_json_string.startswith("```json") and raw_json_string.endswith("```"):
                raw_json_string = raw_json_string[7:-3].strip()
            if raw_json_string.startswith("json\n"):
                raw_json_string = raw_json_string[len("json\n"):].strip()

            try:
                parsed_json_data = json.loads(raw_json_string)
                ordered = OrderedDict()
                ordered["header"] = parsed_json_data.get("header", {})
                ordered["reason"] = parsed_json_data.get("reason", "")
                ordered["status"] = parsed_json_data.get("status", "")
                ordered["read"] = parsed_json_data.get("read", [])
                json_string = json.dumps(ordered, ensure_ascii=False, indent=2)
                return Response(json_string, mimetype='application/json')
            except json.JSONDecodeError as e:
                print(f"Error JSONDecodeError: {e}")
                print(f"Respons mentah Gemini: {raw_json_string}")
                return jsonify({"error": f"Gagal mengurai JSON dari respons Gemini: {str(e)}", "gemini_raw_response": raw_json_string}), 500

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
