import io
import json
import os
from collections import OrderedDict

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request

# --- Import untuk Google Gemini ---
try:
    import pathlib

    from google import genai
    from google.genai import types
except ImportError:
    print("Peringatan: pustaka google-generativeai tidak ditemukan.")
    print("Integrasi Gemini tidak akan berfungsi.")
    print("Instal dengan: pip install google-generativeai")
    genai = None  

load_dotenv()

app = Flask(__name__)

# --- Konfigurasi API Key Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and genai: 
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        print("Gemini client berhasil diinisialisasi.")
    except Exception as e:
        print(f"Error saat menginisialisasi Gemini client: {e}")
        print("Pastikan API key valid.")
else:
    print("Error: GEMINI_API_KEY tidak diatur atau pustaka Gemini tidak dimuat.")

# Direktori untuk menyimpan file yang diunggah sementara
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/balance-sheet/ep/konvensional/posisi-keuangan', methods=['POST'])
def konvensional_keuangan():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Tidak ada bagian 'pdf_file' dalam permintaan"}), 400

    pdf_file = request.files['pdf_file']

    if pdf_file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        filepath = ""
        uploaded_file = None
        try:
            filepath = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
            pdf_file.save(filepath)
            print(f"File PDF disimpan sementara di: {filepath}")

            if not gemini_client:
                return jsonify({"error": "API Gemini tidak dikonfigurasi. Periksa API key atau inisialisasi model."}), 500

            print("Mengunggah file PDF ke Gemini File API...")
            uploaded_file = gemini_client.files.upload(
                file=filepath
            )

            print(f"File berhasil diunggah ke Gemini: {uploaded_file.uri}")

            # Prompt untuk Gemini
            prompt_text = """
            You are an expert assistant in analyzing financial reports, specifically balance sheets.
            Extract balance sheet information from the provided PDF document. Ensure you identify main categories (Assets, Liabilities, Equity),
            sub-categories like 'Current Assets', 'Short-Term Liabilities', 'Cooperative Capital', and items within them (e.g., 'Cash and cash equivalents', 'Principal savings').
            Provide values for the years 2023 and 2022.
            Present the output in a clean, structured JSON format. Monetary values should be strings without thousand separators.
            If an item does not have data for a specific year, use null.
            All keys and values in the JSON should be in English.

            The JSON output should have a top-level structure with 'status', 'reason', and 'read' fields.
            The 'read' field should be an array containing two objects, one for each year (2022 and 2023).
            Each financial item should be represented as an object with 'value' and 'confidence' (set to null) keys.

            Expected JSON output structure:
              "reason": "File Successfully read",
              "status": "Success",
              "read": [
                {{
                  "year": "2022",
                  "Cash_and_cash_equivalents": {{ "value": "value", "confidence": null }}
                  "Cash": {{ "value": "value", "confidence": null }}
                  "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
                }},
                {{
                  "year": "2022",
                  "Cash_and_cash_equivalents": {{ "value": "value", "confidence": null }}
                  "Cash": {{ "value": "value", "confidence": null }}
                  "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
                }},
            }}
            """

            # Model instance untuk generasi konten
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt_text])
            print("Respons dari Gemini diterima.")

            # Extract JSON from response
            raw_json_string = response.text.strip()
            if raw_json_string.startswith("```json"):
                raw_json_string = raw_json_string[7:-3].strip()
            elif raw_json_string.startswith("json"):
                raw_json_string = raw_json_string[4:].strip()

            try:
                parsed_json_data = json.loads(raw_json_string)
                ordered = OrderedDict()
                ordered["reason"] = parsed_json_data.get("reason", "File Successfully read")
                ordered["status"] = parsed_json_data.get("status", "Success")
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
            # --- CORRECTED CODE: Using the client instance to delete the file ---
            if uploaded_file:
                try:
                    gemini_client.files.delete(uploaded_file.name)
                    print(f"File Gemini sementara dihapus: {uploaded_file.name}")
                except Exception as e:
                    print(f"Error saat menghapus file Gemini: {e}")

            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"File sementara dihapus secara lokal: {filepath}")
    else:
        return jsonify({"error": "Tipe file tidak valid. Harap unggah file PDF."}), 400
@app.route('/balance-sheet/ep/syariah/posisi-keuangan', methods=['POST'])
def syariah_keuangan():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Tidak ada bagian 'pdf_file' dalam permintaan"}), 400

    pdf_file = request.files['pdf_file']

    if pdf_file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        filepath = ""
        uploaded_file = None
        try:
            filepath = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
            pdf_file.save(filepath)
            print(f"File PDF disimpan sementara di: {filepath}")

            if not gemini_client:
                return jsonify({"error": "API Gemini tidak dikonfigurasi. Periksa API key atau inisialisasi model."}), 500

            print("Mengunggah file PDF ke Gemini File API...")
            uploaded_file = gemini_client.files.upload(
                file=filepath
            )

            print(f"File berhasil diunggah ke Gemini: {uploaded_file.uri}")

            # Prompt untuk Gemini
            prompt_text = """
            You are an expert assistant in analyzing financial reports, specifically balance sheets.
            Extract balance sheet information from the provided PDF document. Ensure you identify main categories (Assets, Liabilities, Equity),
            sub-categories like 'Current Assets', 'Short-Term Liabilities', 'Cooperative Capital', and items within them (e.g., 'Cash and cash equivalents', 'Principal savings').
            Provide values for the years 2023 and 2022.
            Present the output in a clean, structured JSON format. Monetary values should be strings without thousand separators.
            If an item does not have data for a specific year, use null.
            All keys and values in the JSON should be in English.

            The JSON output should have a top-level structure with 'status', 'reason', and 'read' fields.
            The 'read' field should be an array containing two objects, one for each year (2022 and 2023).
            Each financial item should be represented as an object with 'value' and 'confidence' (set to null) keys.

            Expected JSON output structure:
              "reason": "File Successfully read",
              "status": "Success",
              "read": [
                {{
                  "year": "2022",
                  "Cash_and_cash_equivalents": {{ "value": "value", "confidence": null }}
                  "Cash": {{ "value": "value", "confidence": null }}
                  "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
                }},
                {{
                  "year": "2023",
                  "Cash_and_cash_equivalents": {{ "value": "value", "confidence": null }}
                  "Cash": {{ "value": "value", "confidence": null }}
                  "TOTAL_ASSETS": {{ "value": "value", "confidence": null }}
                }},
            }}
            """

            # Model instance untuk generasi konten
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt_text])
            print("Respons dari Gemini diterima.")

            raw_json_string = response.text.strip()
            if raw_json_string.startswith("```json"):
                raw_json_string = raw_json_string[7:-3].strip()
            elif raw_json_string.startswith("json"):
                raw_json_string = raw_json_string[4:].strip()

            try:
                parsed_json_data = json.loads(raw_json_string)
                ordered = OrderedDict()
                ordered["reason"] = parsed_json_data.get("reason", "File Successfully read")
                ordered["status"] = parsed_json_data.get("status", "Success")
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
            # --- CORRECTED CODE: Using the client instance to delete the file ---
            if uploaded_file:
                try:
                    gemini_client.files.delete(uploaded_file.name)
                    print(f"File Gemini sementara dihapus: {uploaded_file.name}")
                except Exception as e:
                    print(f"Error saat menghapus file Gemini: {e}")

            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"File sementara dihapus secara lokal: {filepath}")
    else:
        return jsonify({"error": "Tipe file tidak valid. Harap unggah file PDF."}), 400
@app.route('/balance-sheet/ep/konvensional/laba-rugi', methods=['POST'])
def konvensional_labarugi():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Tidak ada bagian 'pdf_file' dalam permintaan"}), 400

    pdf_file = request.files['pdf_file']

    if pdf_file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        filepath = ""
        uploaded_file = None
        try:
            filepath = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
            pdf_file.save(filepath)
            print(f"File PDF disimpan sementara di: {filepath}")

            if not gemini_client:
                return jsonify({"error": "API Gemini tidak dikonfigurasi. Periksa API key atau inisialisasi model."}), 500

            # --- CORRECTED CODE: Using the client instance to upload the file ---
            print("Mengunggah file PDF ke Gemini File API...")
            uploaded_file = gemini_client.files.upload(
                file=filepath
            )

            print(f"File berhasil diunggah ke Gemini: {uploaded_file.uri}")

            # Prompt untuk Gemini
            prompt_text = """
You are an expert assistant in analyzing cooperative financial reports, especially balance sheets, income statements, and equity reports.

Your task is to extract structured financial data from the uploaded PDF. Specifically:

📌 Focus on extracting key components related to:
- Net Revenue (Pendapatan)
- Cost of Revenue (Beban Pokok Pendapatan)
- Gross Profit (Sisa Hasil Usaha Kotor)
- General & Admin Expenses (Beban Umum dan Administrasi)
- Other Income (Pendapatan Lain-lain)
- Other Expenses (Beban lain-lain)
- Income Before Tax (Sisa Hasil Usaha Sebelum Pajak)
- Income Tax Expense (Beban pajak kini)
- Net Income / SHU (Sisa Hasil Usaha Tahun Berjalan)

📌 Also extract changes in equity:
- Principal Savings (Simpanan Pokok)
- Mandatory Savings (Simpanan Wajib)
- Special Savings (Simpanan Khusus)
- Reserve Funds (Cadangan)
- Undistributed SHU (SHU belum dibagikan)
- Total Equity (Jumlah / Total Ekuitas)

✅ The result should be returned in the following **clean JSON format**:
{
  "status": "SUCCESS",
  "reason": "File Successfully Read",
  "read": [
    {
      "year": 2022,
      "net_revenue": { "value": ..., "confidence": null },
      "cost_of_revenue": { "value": ..., "confidence": null },
      "gross_profit": { "value": ..., "confidence": null },
      "general_admin_expenses": { "value": ..., "confidence": null },
      "other_income": { "value": ..., "confidence": null },
      "other_expenses": { "value": ..., "confidence": null },
      "income_before_tax": { "value": ..., "confidence": null },
      "income_tax_expense": { "value": ..., "confidence": null },
      "net_income": { "value": ..., "confidence": null },
      "principal_savings": { "value": ..., "confidence": null },
      "mandatory_savings": { "value": ..., "confidence": null },
      "special_savings": { "value": ..., "confidence": null },
      "reserves": { "value": ..., "confidence": null },
      "undistributed_shu": { "value": ..., "confidence": null },
      "total_equity": { "value": ..., "confidence": null }
    },
    {
      "year": 2023,
      ...
    }
  ]
}

📌 RULES:
- All keys must use lowercase snake_case format (e.g., `net_income`)
- Monetary values must be numbers only, no commas or separators.
- If a value is missing, set `"value": null`
- Always set `"confidence": null`
- Do NOT include any explanation or formatting outside the JSON structure.

Begin processing and return the JSON output only.
"""
            # Model instance untuk generasi konten
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt_text])
            print("Respons dari Gemini diterima.")

            raw_json_string = response.text.strip()
            if raw_json_string.startswith("```json"):
                raw_json_string = raw_json_string[7:-3].strip()
            elif raw_json_string.startswith("json"):
                raw_json_string = raw_json_string[4:].strip()

            try:
                parsed_json_data = json.loads(raw_json_string)
                ordered = OrderedDict()
                ordered["reason"] = parsed_json_data.get("reason", "File Successfully read")
                ordered["status"] = parsed_json_data.get("status", "Success")
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
            # --- CORRECTED CODE: Using the client instance to delete the file ---
            if uploaded_file:
                try:
                    gemini_client.files.delete(uploaded_file.name)
                    print(f"File Gemini sementara dihapus: {uploaded_file.name}")
                except Exception as e:
                    print(f"Error saat menghapus file Gemini: {e}")

            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"File sementara dihapus secara lokal: {filepath}")
    else:
        return jsonify({"error": "Tipe file tidak valid. Harap unggah file PDF."}), 400
@app.route('/balance-sheet/ep/syariah/laba-rugi', methods=['POST'])
def syariah_labarugi():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "Tidak ada bagian 'pdf_file' dalam permintaan"}), 400

    pdf_file = request.files['pdf_file']

    if pdf_file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih"}), 400

    if pdf_file and pdf_file.filename.endswith('.pdf'):
        filepath = ""
        uploaded_file = None
        try:
            filename = pdf_file.filename.lower()
            filepath = os.path.join(UPLOAD_FOLDER, pdf_file.filename)
            pdf_file.save(filepath)
            print(f"File PDF disimpan sementara di: {filepath}")

            if not gemini_client:
                return jsonify({"error": "API Gemini tidak dikonfigurasi. Periksa API key atau inisialisasi model."}), 500
            
            PROMPT_ASSAFIIYAH = """
You are an expert assistant in analyzing SHU (Sisa Hasil Usaha / Net Income) reports from cooperative financial statements.

From the uploaded PDF document, extract key financial components for years 2023 and 2022. These include:

- contractual_margin (Margin Kontraktual)
- provisions_and_administration (Provisi dan Administrasi)
- total_profit_sharing_income (Jumlah Pendapatan Bagi Hasil)
- profit_sharing_expense (Beban Bagi Hasil)
- net_profit_sharing_income (Pendapatan Bagi Hasil Neto)
- other_operational_income (Pendapatan Operasional Lainnya)
- total_operational_income (Jumlah Pendapatan Operasional)
- impairment_/_depreciation_expense (Beban Penyisihan Kerugian / Penyusutan)
- marketing_expenses (Beban Pemasaran)
- administrative_and_general_expenses (Beban Administrasi dan Umum)
- other_operational_expenses (Beban Operasional Lainnya)
- total_operational_expenses (Jumlah Beban Operasional)
- operating_profit_(loss) (Laba (Rugi) Operasional)
- non_operating_income (Pendapatan Non Operasional)
- non_operating_expenses (Beban Non Operasional)
- total_non_operating_expenses (Jumlah Beban Non Operasional)
- net_income_before_tax (SHU Sebelum Pajak)
- estimated_income_tax (Taksiran Pajak Penghasilan)
- net_income_after_tax (SHU SETELAH PAJAK)

✅ FORMAT RULES:
- All values must be in JSON with the following structure:
{
  "status": "Success",
  "reason": "File Successfully read",
  "read": [
    {
      "year": "2022",
      "contractual_margin": { "value": "value", "confidence": null },
      ...
    },
    {
      "year": "2023",
      ...
    }
  ]
}
- All monetary values must be strings **without thousand separators**
- All keys must be in PascalCase with underscores
- All values are objects with "value" and "confidence" (confidence always null)
- If a field is missing, include it with "value": null

DO NOT include any explanation or additional text. Return JSON only.
"""
            PROMPT_BERINGHARJO = """
You are a financial report assistant. Your job is to extract SHU (Net Income) information from a cooperative's annual report PDF.
If the document contains SHU or income statement data (Pendapatan, Beban, SHU), extract for both 2022 and 2023.
Look for the following values if available:

- main_operational_income (pendapatan_operasional_utama)
- members_profit_sharing_rights_on_savings (hak bagi hasil anggota penyimpanan)
- gross_operating_result (sisa_hasil_usaha_kotor)
- general_and_administrative_expenses (beban_umum_dan_administrasi)
- cooperative_expenses (beban_perkoperasian)
- total_operating_expenses (jumlah_beban_operasional)
- operating_result (sisa_hasil_usaha_operasional)
- non_operating_income (pendapatan_non_operasional)
- non_operating_expenses (beban_non_operasional)
- total_non_operating_income_and_expenses (jumlah_pendapatan_dan_beban_non_operasional)
- profit_sharing_expenses_on_received_financing (beban_bagi_hasil_pembiayaan_yang_diterima)
- net_income_before_ZIS_and_tax (shu_sebelum_ZIS_dan_pajak)
- zakat_infaq_shodaqoh (zakat_infaq_shodaqoh)
- net_income_before_tax (shu_sebelum_pajak)
- estimated_income_tax (taksiran_pajak_penghasilan)
- net_income (shu_bersih)

✅ RETURN STRUCTURE:
{
  "status": "Success",
  "reason": "File Successfully read",
  "read": [
    {
      "year": "2022",
      "main_operational_income": { "value": "value", "confidence": null },
      "members_profit_sharing_rights_on_savings": { "value": "value", "confidence": null },
      ...
    },
    {
      "year": "2023",
      ...
    }
  ]
}

RULES:
- All values must be strings (numbers only), no formatting
"""
            PROMPT_DEFAULT_SHU = """ """
            # 🧠 Tentukan prompt berdasarkan nama file
            if "assafiiyah" in filename:
                prompt_text = PROMPT_ASSAFIIYAH
            elif "beringharjo" in filename:
                prompt_text = PROMPT_BERINGHARJO
            else:
                prompt_text = PROMPT_DEFAULT_SHU  # fallback

            # --- Upload file ke Gemini File API ---
            print("Mengunggah file PDF ke Gemini File API...")
            uploaded_file = gemini_client.files.upload(file=filepath)
            print(f"File berhasil diunggah ke Gemini: {uploaded_file.uri}")

            # 🔍 Kirim prompt dan file ke model Gemini
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, prompt_text]
            )
            print("Respons dari Gemini diterima.")
            
            # 🧹 Bersihkan dan parsing hasil JSON
            raw_json_string = response.text.strip()
            if raw_json_string.startswith("```json"):
                raw_json_string = raw_json_string[7:-3].strip()
            elif raw_json_string.startswith("json"):
                raw_json_string = raw_json_string[4:].strip()

            try:
                parsed_json_data = json.loads(raw_json_string)
                ordered = OrderedDict()
                ordered["reason"] = parsed_json_data.get("reason", "File Successfully read")
                ordered["status"] = parsed_json_data.get("status", "Success")
                ordered["read"] = parsed_json_data.get("read", [])
                json_string = json.dumps(ordered, ensure_ascii=False, indent=2)
                return Response(json_string, mimetype='application/json')
            except json.JSONDecodeError as e:
                print(f"Error JSONDecodeError: {e}")
                print(f"Respons mentah Gemini: {raw_json_string}")
                return jsonify({
                    "error": f"Gagal mengurai JSON dari respons Gemini: {str(e)}",
                    "gemini_raw_response": raw_json_string
                }), 500

        except Exception as e:
            print(f"Terjadi kesalahan umum: {e}")
            return jsonify({
                "error": f"Terjadi kesalahan selama pemrosesan PDF atau interaksi Gemini: {str(e)}"
            }), 500
        finally:
            # 🧹 Hapus file dari Gemini & lokal
            if uploaded_file:
                try:
                    gemini_client.files.delete(uploaded_file.name)
                    print(f"File Gemini sementara dihapus: {uploaded_file.name}")
                except Exception as e:
                    print(f"Error saat menghapus file Gemini: {e}")

            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"File sementara dihapus secara lokal: {filepath}")
    else:
        return jsonify({"error": "Tipe file tidak valid. Harap unggah file PDF."}), 400



if __name__ == '__main__':
    print("Memulai server Flask...")
    app.run(debug=True, host='127.0.0.1', port=5000)
