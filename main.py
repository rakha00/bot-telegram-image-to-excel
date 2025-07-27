import asyncio
import json
import os
import uuid
from datetime import datetime

import docx
import pdfplumber
from flask import (Flask, Response, abort, jsonify, render_template, request,
                   send_from_directory)
from werkzeug.utils import secure_filename

from gemini_vision_extractor import get_json_output

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

def to_snake_case(name):
    import re
    name = re.sub(r'[^a-zA-Z0-9_ ]', '', name) # Remove special characters except underscore and space
    name = name.strip().replace(' ', '_')
    return name.lower()

# Konfigurasi path ke direktori 'output' tempat file JSON disimpan
OUTPUT_FOLDER = 'output'
TEMP_FILES_FOLDER = 'temp_files' # Folder sementara untuk file yang diunggah
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['TEMP_FILES_FOLDER'] = TEMP_FILES_FOLDER

@app.route('/')
def home():
    return render_template('index.html')


def clean_value_string(value):
    """
    Membersihkan string nilai dari karakter non-numerik seperti 'Rp', '.', ',', '(', ')'.
    Menangani nilai negatif dalam kurung.
    """
    if value is None:
        return None
    
    s_value = str(value).strip()
    is_negative = False

    if s_value.startswith('(') and s_value.endswith(')'):
        is_negative = True
        s_value = s_value[1:-1] # Hapus tanda kurung

    # Hapus 'Rp', spasi, titik (ribuan), dan koma (desimal atau ribuan)
    cleaned_value = s_value.replace('Rp', '').replace('.', '').replace(',', '').replace(' ', '').strip()

    if is_negative:
        return f"-{cleaned_value}"
    return cleaned_value


def pdf_to_json(pdf_path):
    """
    Ekstrak tabel dari PDF dan konversi ke JSON array of objects.
    Hanya mengambil tabel pertama di halaman pertama.
    Membersihkan header dan memastikan kolom pertama bernama 'Akun'.
    """
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        tables = first_page.extract_tables()
        if not tables:
            return []
        table = tables[0]
        
        # Clean and prepare headers
        raw_headers = table[0]
        cleaned_headers = [h.strip() if h else '' for h in raw_headers]
        
        # Ensure the first column is named 'Akun' for consistency in mapping
        # This assumes the first column in the PDF table is always the account description
        if cleaned_headers:
            # If the first header is empty or a general category (like "ASET"), rename it to "Akun"
            # This is a heuristic based on the PDF structure for balance sheets.
            if not cleaned_headers[0] or cleaned_headers[0].upper() in ["ASET", "LIABILITAS DAN EKUITAS", "LIABILITAS", "EKUITAS"]:
                cleaned_headers[0] = "Akun"
            # Otherwise, use its existing cleaned name.
        
        data = []
        for row in table[1:]: # Start from the second row (skip original headers)
            obj = {}
            for i, cell in enumerate(row):
                key = to_snake_case(cleaned_headers[i]) if i < len(cleaned_headers) else f"col_{i+1}"
                obj[key] = cell if cell not in [None, ""] else None
            data.append(obj)
        return data

def docx_to_json(docx_path):
    """
    Ekstrak tabel dari DOCX dan konversi ke JSON array of objects.
    Hanya mengambil tabel pertama.
    """
    doc = docx.Document(docx_path)
    if not doc.tables:
        return []
    table = doc.tables[0]
    rows = list(table.rows)
    headers = [cell.text.strip() for cell in rows[0].cells]
    data = []
    for row in rows[1:]:
        obj = {}
        for i, cell in enumerate(row.cells):
            key = to_snake_case(headers[i]) if i < len(headers) else f"col_{i+1}"
            value = cell.text.strip()
            obj[key] = value if value else None
        data.append(obj)
    return data

# The fix_empty_key function is no longer strictly needed if pdf_to_json handles 'Akun' directly,
# but keeping it for robustness in case other file types or extraction methods produce empty keys.
def fix_empty_key(json_data, new_key="Akun"):
    if not json_data:
        return json_data
    old_key = "" 
    if isinstance(json_data, list) and len(json_data) > 0:
        if old_key in json_data[0]:
            for obj in json_data:
                if isinstance(obj, dict) and old_key in obj:
                    if new_key not in obj:
                        obj[new_key] = obj.pop(old_key)
    return json_data


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Konfigurasi Pemetaan untuk Setiap Jenis Laporan (Disederhanakan) ---
REPORT_CONFIGS = {
    'laporan_keuangan': { # Satu entri untuk kedua jenis laporan keuangan (syariah & konvensional)
        'account_to_output_key_map': {
            # ASSET
            "kas_dan_setara_kas": "cash_and_cash_equivalents",
            "pembiayaan_kepada_anggota": "financing_to_members",
            "persediaan": "inventory",
            "biaya_dibayar_dimuka_dan_uang_muka": "prepaid_expenses_and_advances",
            "jumlah_aset_lancar": "total_current_assets",
            "investasi": "investments",
            "aset_tetap_bersih": "net_fixed_assets",
            "aset_tidak_berwujud_bersih": "net_intangible_assets",
            "jumlah_aset_tidak_lancar": "total_non_current_assets",
            "jumlah_aset": "total_assets",

            # LIABILITIES AND EQUITY
            "liabilitas": "liabilities_header",
            "liabilitas_jangka_pendek": "short_term_liabilities_header", # Added for clarity
            "simpanan_anggota": "member_deposits",
            "biaya_yang_masih_harus_dibayar": "accrued_expenses",
            "utang_lain_lain": "other_payables",
            "bagian_jatuh_tempo_satu_tahun_utang_jangka_panjang": "current_portion_long_term_debt",
            "utang_bank": "bank_loans",
            "utang_pembiayaan": "financing_payables",
            "utang_pajak": "tax_payables",
            
            "liabilitas_jangka_panjang": "long_term_liabilities_header",
            "utang_kepada_anggota": "payables_to_members",
            "utang_jangka_panjang_setelah_dikurangi_bagian_jatuh_tempo_satu_tahun": "long_term_debt_net_current_portion",
            "liabilitas_imbalan_kerja": "employee_benefit_liabilities",
            "jumlah_liabilitas_jangka_panjang": "total_long_term_liabilities",
            "jumlah_liabilitas": "total_liabilities",
            
            # EKUITAS
            "ekuitas": "equity_header",
            "modal_koperasi": "cooperative_capital_header", # Added for clarity
            "simpanan_pokok": "principal_savings",
            "simpanan_wajib": "mandatory_savings",
            "simpanan_khusus": "special_savings",
            "dana_cadangan": "reserve_fund",
            "shu_yang_belum_dibagi": "undistributed_shu", # SHU: Sisa Hasil Usaha (Retained Earnings)
            "jumlah": "total_equity", # This "Jumlah" refers to total equity
            "jumlah_liabilitas_dan_ekuitas": "total_liabilities_and_equity"
        },
        'desired_output_keys_order': [
            "year", 
            # ASSET
            "cash_and_cash_equivalents",
            "financing_to_members",
            "inventory",
            "prepaid_expenses_and_advances",
            "total_current_assets",
            "investments",
            "net_fixed_assets",
            "net_intangible_assets",
            "total_non_current_assets",
            "total_assets",
            
            # LIABILITIES AND EQUITY
            "liabilities_header",
            "short_term_liabilities_header",
            "member_deposits",
            "accrued_expenses",
            "other_payables",
            "current_portion_long_term_debt",
            "bank_loans",
            "financing_payables",
            "tax_payables",
            "long_term_liabilities_header",
            "payables_to_members",
            "long_term_debt_net_current_portion",
            "employee_benefit_liabilities",
            "total_long_term_liabilities",
            "total_liabilities",
            
            "equity_header",
            "cooperative_capital_header",
            "principal_savings",
            "mandatory_savings",
            "special_savings",
            "reserve_fund",
            "undistributed_shu",
            "total_equity",
            "total_liabilities_and_equity"
        ]
    },
    'laba_rugi': { # Satu entri untuk kedua jenis laba rugi (syariah & konvensional)
        'account_to_output_key_map': {
            "Pendapatan bunga": "interest_income",
            "Jumlah partisipasi anggota": "member_participation",
            "PARTISIPASI ANGGOTA": "member_participation_category",
            "BEBAN USAHA": "operating_expenses_category",
            "Beban penyisihan": "allowance_expense",
            "Beban kepegawaian": "personnel_expense",
            "Beban administrasi dan umum": "administrative_general_expenses",
            "Beban penyusutan dan amortisasi": "depreciation_amortization_expenses",
            "Jumlah beban usaha": "business_expense",
            "SISA HASIL USAHA BRUTO": "remaining_profit_bruto",
            "Hasil investasi": "investment_result",
            "Beban perkoperasian": "cooperative_expense",
            "PENDAPATAN & BEBAN LAIN": "other_income_expense_category",
            "Pendapatan lain": "other_income",
            "Beban lain": "other_expense",
            "Sisa hasil usaha sebelum pajak": "remaining_profit_before_tax",
            "Beban pajak penghasilan": "income_tax_expense",
            "SISA HASIL USAHA": "remaining_profit",
            "Penghasilan komprehensif lain": "other_comprehensive_income",
            "PENGHASILAN KOMPREHENSIF": "comprehensive_income",
        },
        'desired_output_keys_order': [
            "year", "member_participation_category", "interest_income", "member_participation",
            "operating_expenses_category", "allowance_expense", "personnel_expense",
            "administrative_general_expenses", "depreciation_amortization_expenses",
            "business_expense", "remaining_profit_bruto", "investment_result",
            "cooperative_expense", "other_income_expense_category", "other_income",
            "other_expense", "remaining_profit_before_tax", "income_tax_expense",
            "remaining_profit", "other_comprehensive_income", "comprehensive_income"
        ]
    }
}

# --- Fungsi Utilitas Umum untuk Memproses Laporan ---
async def _process_financial_report(report_category):
    full_data_from_file = None
    file_uploaded = False

    try:
        config = REPORT_CONFIGS[report_category]
        account_to_output_key_map = config['account_to_output_key_map']
        desired_output_keys_order = config['desired_output_keys_order']
    except KeyError:
        error_msg = f"Kategori laporan '{report_category}' tidak valid atau tidak ditemukan."
        return {"error": error_msg}, 400

    if 'file' in request.files:
        file_uploaded = True
        file = request.files['file']
        if file.filename == '':
            return {"error": "No selected file"}, 400
        
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['TEMP_FILES_FOLDER'], exist_ok=True)
            file_path = os.path.join(app.config['TEMP_FILES_FOLDER'], filename)
            file.save(file_path)
            
            ext = filename.rsplit('.', 1)[1].lower()
            if ext == 'pdf':
                full_data_from_file = pdf_to_json(file_path) # <<< PASTIKAN HANYA BARIS INI
            elif ext in {'doc', 'docx'}:
                full_data_from_file = docx_to_json(file_path)
            else: # For image files, use Gemini Vision Extractor
                json_output = await get_json_output(file_path)
                full_data_from_file = json.loads(json_output)
            
            os.remove(file_path) # Hapus file sementara setelah diproses
        else:
            return {"error": "File type not allowed"}, 400

    elif request.is_json and not file_uploaded: # Only process JSON body if no file was uploaded
        full_data_from_file = request.get_json()
    else:
        return {
            "error": "Unsupported Media Type. Please upload a file using 'form-data' with a 'file' key, or provide a JSON body with 'Content-Type: application/json'."
        }, 415

    if not full_data_from_file:
        return {"error": "Request must contain either a valid file or JSON data."}, 400

    elif request.is_json and not file_uploaded: # Only process JSON body if no file was uploaded
        full_data_from_file = request.get_json()
    else:
        return {
            "error": "Unsupported Media Type. Please upload a file using 'form-data' with a 'file' key, or provide a JSON body with 'Content-Type: application/json'."
        }, 415

    if not full_data_from_file:
        return {"error": "Request must contain either a valid file or JSON data."}, 400
    
    response_payload = {
        "status" : "SUCCESS",
        "reason" : "Data Successfully Processed",
        "read": []
    }

    available_years = set()
    for item in full_data_from_file:
        for key in item:
            # Ensure key is a string and clean it before checking for year format
            if isinstance(key, str):
                cleaned_key = key.strip()
                if cleaned_key.isdigit() and len(cleaned_key) == 4: # Asumsi tahun adalah 4 digit angka
                    available_years.add(cleaned_key)
    
    sorted_years = sorted(list(available_years))

    if not sorted_years: # If no years are found after cleaning
        response_payload["status"] = "FAILED"
        response_payload["reason"] = "No year data found in the data after cleaning headers."
        return response_payload, 404

    for year in sorted_years:
        year_data_entry = {}
        temp_data_storage = {}

        for item in full_data_from_file:
            akun_value = item.get('Akun')
            # Ensure akun_value is a string and strip it for consistent matching
            if isinstance(akun_value, str):
                akun_value = akun_value.strip()

            if akun_value in account_to_output_key_map and year in item:
                output_key = account_to_output_key_map[akun_value]
                value_for_year = item.get(year)
                
                temp_data_storage[output_key] = {
                    "value": clean_value_string(value_for_year),
                    "confidence": None
                }
            # Handle cases where 'Akun' might be null or not found for headers that are part of the map
            # This is less likely with the new pdf_to_json, but good for robustness
            elif akun_value is None: 
                for mapped_akun, output_key_from_map in account_to_output_key_map.items():
                    # If the value in the year column itself matches a mapped account name (e.g., "LIABILITAS")
                    if item.get(year) and item.get(year).strip() == mapped_akun:
                        temp_data_storage[output_key_from_map] = {
                            "value": None, # Headers usually don't have numerical values
                            "confidence": None
                        }


        for key in desired_output_keys_order:
            if key == "year":
                year_data_entry['year'] = int(year)
            elif key in temp_data_storage:
                year_data_entry[key] = temp_data_storage[key]
            else:
                year_data_entry[key] = {"value": None, "confidence": None}
        
        response_payload["read"].append(year_data_entry)
        
    if not response_payload["read"]:
        response_payload["status"] = "FAILED"
        response_payload["reason"] = "No data could be processed for the identified years."
        return response_payload, 404

    final_response = {
        "status": response_payload["status"],
        "reason": response_payload["reason"],
        "read": response_payload["read"]
    }
    return final_response, 200 # Mengembalikan payload dan status HTTP

# === Endpoint Baru (4 API) ===

@app.route('/balance-sheet/ep/laporan-keuangan/syariah', methods=['POST'])
async def get_json_file_laporan_keuangan_syariah():
    try:
        response_data, status_code = await _process_financial_report('laporan_keuangan')
        if status_code != 200:
            return jsonify(response_data), status_code
        return Response(json.dumps(response_data, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data in request body."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)

@app.route('/balance-sheet/ep/laporan-keuangan/konvensional', methods=['POST'])
async def get_json_file_laporan_keuangan_konvensional():
    try:
        response_data, status_code = await _process_financial_report('laporan_keuangan')
        if status_code != 200:
            return jsonify(response_data), status_code
        return Response(json.dumps(response_data, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data in request body."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)

@app.route('/balance-sheet/ep/laba-rugi/syariah', methods=['POST'])
async def get_json_file_laba_rugi_syariah():
    try:
        response_data, status_code = await _process_financial_report('laba_rugi')
        if status_code != 200:
            return jsonify(response_data), status_code
        return Response(json.dumps(response_data, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data in request body."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)

@app.route('/balance-sheet/ep/laba-rugi/konvensional', methods=['POST'])
async def get_json_file_laba_rugi_konvensional():
    try:
        response_data, status_code = await _process_financial_report('laba_rugi')
        if status_code != 200:
            return jsonify(response_data), status_code
        return Response(json.dumps(response_data, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data in request body."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)


@app.route('/neraca', methods=['POST'])
async def post_neraca_json():
    try:
        response_data, status_code = await _process_financial_report('laporan_keuangan')
        if status_code != 200:
            return jsonify(response_data), status_code
        return Response(json.dumps(response_data, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON data in request body."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}, 500)


if __name__ == '__main__':
    # Pastikan direktori 'output' dan 'temp_files' ada saat aplikasi dimulai
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FILES_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
