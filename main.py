import json
import os

from flask import Flask, Response, abort, jsonify, send_from_directory

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Konfigurasi path ke direktori 'output' tempat file JSON disimpan
OUTPUT_FOLDER = 'output'
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

@app.route('/')
def home():
    return "Selamat datang di API OCR Tabel! Gunakan /api/files untuk melihat daftar file JSON."

@app.route('/api/files', methods=['GET'])
def list_json_files():
    """
    Mengembalikan daftar semua file JSON yang tersedia di direktori output.
    """
    try:
        json_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) if f.endswith('.json')]
        return jsonify({"files": json_files})
    except FileNotFoundError:
        return jsonify({"error": "Direktori output tidak ditemukan."}, 404)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)


# ====tools====
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


# ============  SYARIAH LABARUGI ============
@app.route('/balance-sheet/ep/syariah/laba-rugi/<filename>', methods=['GET'])
def get_json_file_syariah_laba_rugi(filename):
    """
    Mengembalikan laporan JSON lengkap dengan data untuk semua tahun yang ditemukan,
    difomrat sesuai permintaan.
    """
    if not filename.endswith('.json'):
        return jsonify({"error": "Nama file harus berakhiran .json"}, 400)

    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File tidak ditemukan."}, 404)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_data_from_file = json.load(f)
        
        # Struktur respons sesuai permintaan
        response_payload = {
            "status" : "SUCCESS",
            "reason" : "File Successfully Read",
            "read": []
        }

        # Peta dari nilai 'Akun' di JSON asli ke kunci yang diinginkan di output
        # Saya telah memperbarui pemetaan ini berdasarkan contoh output yang Anda berikan
        # dan data JSON input Anda.
        account_to_output_key_map = {
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
        }

        # Urutan kunci yang diinginkan dalam objek di dalam array 'read'
        # Ini akan menentukan urutan output JSON Anda.
        desired_output_keys_order = [
            "interest_income",
            "other_business_income",
            "member_participation",
            "member_participation_category",
            "operating_expenses_category",
            "interest_expense",
            "allowance_expense",
            "personnel_expense",
            "administrative_general_expenses",
            "depreciation_amortization_expenses",
            "other_business_expense",
            "business_expense",
            "investment_result",
            "cooperative_expense",
            "other_income",
            "other_expense",
            "remaining_profit_before_tax",
            "income_tax_expense",
            "remaining_profit",
            "other_comprehensive_income",
            "comprehensive_income"
        ]

        # Temukan semua tahun yang tersedia di data
        available_years = set()
        for item in full_data_from_file:
            for key in item:
                if key.isdigit() and len(key) == 4: # Asumsi tahun adalah 4 digit angka
                    available_years.add(key)
        
        # Urutkan tahun secara ascending
        sorted_years = sorted(list(available_years))

        # Proses data untuk setiap tahun yang ditemukan
        for year in sorted_years:
            year_data_entry = {} # Inisialisasi dictionary kosong
            temp_data_storage = {} # Simpan data sementara untuk tahun ini

            # Pertama, kumpulkan semua data untuk tahun saat ini
            for item in full_data_from_file:
                akun_value = item.get('Akun')
                if akun_value in account_to_output_key_map and year in item:
                    output_key = account_to_output_key_map[akun_value]
                    value_for_year = item.get(year)
                    
                    temp_data_storage[output_key] = {
                        "value": clean_value_string(value_for_year),
                        "conUidence": None
                    }
            
            # Kedua, bangun entri data tahunan dengan urutan yang benar
            for key in desired_output_keys_order:
                if key == "year":
                    year_data_entry['year'] = int(year)
                elif key in temp_data_storage:
                    year_data_entry[key] = temp_data_storage[key]
                else:
                    # Jika kunci tidak ditemukan, tambahkan dengan nilai null
                    year_data_entry[key] = {"value": None, "conUidence": None}
            
            response_payload["read"].append(year_data_entry)
            
        if not response_payload["read"]:
            response_payload["status"] = "FAILED"
            response_payload["reason"] = "No year data found in the file."

            return Response(json.dumps(response_payload, sort_keys=False), mimetype='application/json', status=404)

        # Explicitly create the final dictionary to ensure key order.
        # This is the most reliable way to control the output structure.
        final_response = {
            "status": response_payload["status"],
            "reason": response_payload["reason"],
            "read": response_payload["read"]
        }
        # Use json.dumps with sort_keys=False and return a raw Response object
        # to have full control over the output format and prevent any reordering by jsonify.
        return Response(json.dumps(final_response, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "File bukan JSON yang valid."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)


# ============ KONVESIONAL LABARUGI ============
@app.route('/balance-sheet/ep/konvesional/laba-rugi/<filename>', methods=['GET'])
def get_json_file_konvensional_laba_rugi(filename):
    """
    Mengembalikan laporan JSON lengkap dengan data untuk semua tahun yang ditemukan,
    difomrat sesuai permintaan.
    """
    if not filename.endswith('.json'):
        return jsonify({"error": "Nama file harus berakhiran .json"}, 400)

    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File tidak ditemukan."}, 404)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_data_from_file = json.load(f)
        
        # Struktur respons sesuai permintaan
        response_payload = {
            "status" : "SUCCESS",
            "reason" : "File Successfully Read",
            "read": []
        }

        # Peta dari nilai 'Akun' di JSON asli ke kunci yang diinginkan di output
        # Saya telah memperbarui pemetaan ini berdasarkan contoh output yang Anda berikan
        # dan data JSON input Anda.
        account_to_output_key_map = {
            "PARTISIPASI ANGGOTA": "member_participation_category", # Ini kategori, tidak ada di output expectation
            "Pendapatan bunga": "interest_income",
            "Jumlah partisipasi anggota": "member_participation",
            "BEBAN USAHA": "operating_expenses_category", # Ini kategori, tidak ada di output expectation
            "Beban bunga": "interest_expense",
            "Beban penyisihan": "allowance_expense",
            "Beban kepegawaian": "personnel_expense",
            "Beban administrasi dan umum": "administrative_general_expenses",
            "Beban penyusutan dan amortisasi": "depreciation_amortization_expenses",
            "Beban usaha lainnya": "other_business_expense",
            "Jumlah beban usaha": "business_expense",
            "SISA HASIL USAHA BRUTO": "remaining_profit_bruto", # Tidak ada di output expectation
            "Hasil investasi": "investment_result",
            "Beban perkoperasian": "cooperative_expense",
            "PENDAPATAN & BEBAN LAIN": "other_income_expense_category", # Ini kategori, tidak ada di output expectation
            "Pendapatan lain": "other_income",
            "Beban lain": "other_expense",
            "Sisa hasil usaha sebelum pajak": "remaining_profit_before_tax",
            "Beban pajak penghasilan": "income_tax_expense",
            "SISA HASIL USAHA": "remaining_profit",
            "Penghasilan komprehensif lain": "other_comprehensive_income",
            "PENGHASILAN KOMPREHENSIF": "comprehensive_income",
        }

        # Urutan kunci yang diinginkan dalam objek di dalam array 'read'
        # Ini akan menentukan urutan output JSON Anda.
        desired_output_keys_order = [
            "year",
            "member_participation",
            "interest_income",
            "interest_expense",
            "allowance_expense",
            "personnel_expense",
            "administrative_general_expenses",
            "depreciation_amortization_expenses",
            "other_business_expense",
            "business_expense",
            "remaining_profit_bruto", 
            "investment_result",
            "cooperative_expense",
            "other_income_expense_category",
            "other_income",
            "other_expense",
            "remaining_profit_before_tax",
            "income_tax_expense",
            "remaining_profit",
            "other_comprehensive_income",
            "comprehensive_income"
        ]

        # Temukan semua tahun yang tersedia di data
        available_years = set()
        for item in full_data_from_file:
            for key in item:
                if key.isdigit() and len(key) == 4: # Asumsi tahun adalah 4 digit angka
                    available_years.add(key)
        
        # Urutkan tahun secara ascending
        sorted_years = sorted(list(available_years))

        # Proses data untuk setiap tahun yang ditemukan
        for year in sorted_years:
            year_data_entry = {} # Inisialisasi dictionary kosong
            temp_data_storage = {} # Simpan data sementara untuk tahun ini

            # Pertama, kumpulkan semua data untuk tahun saat ini
            for item in full_data_from_file:
                akun_value = item.get('Akun')
                if akun_value in account_to_output_key_map and year in item:
                    output_key = account_to_output_key_map[akun_value]
                    value_for_year = item.get(year)
                    
                    temp_data_storage[output_key] = {
                        "value": clean_value_string(value_for_year),
                        "conUidence": None
                    }
            
            # Kedua, bangun entri data tahunan dengan urutan yang benar
            for key in desired_output_keys_order:
                if key == "year":
                    year_data_entry['year'] = int(year)
                elif key in temp_data_storage:
                    year_data_entry[key] = temp_data_storage[key]
                else:
                    # Jika kunci tidak ditemukan, tambahkan dengan nilai null
                    year_data_entry[key] = {"value": None, "conUidence": None}
            
            response_payload["read"].append(year_data_entry)
            
        if not response_payload["read"]:
            response_payload["status"] = "FAILED"
            response_payload["reason"] = "No year data found in the file."

            return Response(json.dumps(response_payload, sort_keys=False), mimetype='application/json', status=404)

        # Explicitly create the final dictionary to ensure key order.
        # This is the most reliable way to control the output structure.
        final_response = {
            "status": response_payload["status"],
            "reason": response_payload["reason"],
            "read": response_payload["read"]
        }
        # Use json.dumps with sort_keys=False and return a raw Response object
        # to have full control over the output format and prevent any reordering by jsonify.
        return Response(json.dumps(final_response, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "File bukan JSON yang valid."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)

# =========== Syariah Laporan Keuangan ============
@app.route('/balance-sheet/ep/syariah/laporan-keuangan/<filename>', methods=['GET'])
def get_json_file_syariah_keuangan(filename):
    """
    Mengembalikan laporan JSON lengkap dengan data untuk semua tahun yang ditemukan,
    difomrat sesuai permintaan.
    """
    if not filename.endswith('.json'):
        return jsonify({"error": "Nama file harus berakhiran .json"}, 400)

    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File tidak ditemukan."}, 404)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_data_from_file = json.load(f)
        
        # Struktur respons sesuai permintaan
        response_payload = {
            "status" : "SUCCESS",
            "reason" : "File Successfully Read",
            "read": []
        }

        # Peta dari nilai 'Akun' di JSON asli ke kunci yang diinginkan di output
        # Saya telah memperbarui pemetaan ini berdasarkan contoh output yang Anda berikan
        # dan data JSON input Anda.
        account_to_output_key_map = {
            "Kas dan setara kas": "cash_and_cash_equivalents",
            "Piutang bunga": "interest_receivable",
            "Pinjaman anggota": "member_loans",
            "Penyisihan pinjaman": "loan_loss_provision",
            "Pinjaman koperasi lain": "loans_to_other_cooperatives",
            "Aset tetap": "fixed_assets",
            "Akumulasi penyusutan": "accumulated_depreciation",
            "Aset takberwujud": "intangible_assets",
            "Akumulasi amortisasi": "accumulated_amortization",
            "Aset lain": "other_assets",
            "Total aset": "total_assets",
            "Utang bunga": "interest_payable",
            "Simpanan anggota": "member_deposits",
            "Simpanan koperasi lain": "other_cooperative_deposits",
            "Utang pinjaman": "loan_payable",
            "Liabilitas imbalan kerja": "employee_benefit_liabilities",
            "Liabilitas lain": "other_liabilities",
            "Total liabilitas": "total_liabilities",
            "Simpanan Pokok": "principal_savings",
            "Simpanan Wajib": "mandatory_savings",
            "Cadangan umum": "general_reserve",
            "Sisa hasil usaha": "retained_earnings",
            "Ekuitas lain": "other_equity",
            "Total ekuitas": "total_equity",
            "Total liabilitas dan ekuitas": "total_liabilities_and_equity",
        }

        # Urutan kunci yang diinginkan dalam objek di dalam array 'read'
        # Ini akan menentukan urutan output JSON Anda.
        desired_output_keys_order = [
        "year",
        "cash_and_cash_equivalents",
        "interest_receivable",
        "member_loans",
        "loan_loss_provision",
        "loans_to_other_cooperatives",
        "fixed_assets",
        "accumulated_depreciation",
        "intangible_assets",
        "accumulated_amortization",
        "other_assets",
        "total_assets",
        "interest_payable",
        "member_deposits",
        "other_cooperative_deposits",
        "loan_payable",
        "employee_benefit_liabilities",
        "other_liabilities",
        "total_liabilities",
        "principal_savings",
        "mandatory_savings",
        "general_reserve",
        "retained_earnings",
        "other_equity",
        "total_equity",
        "total_liabilities_and_equity"
        ]

        # Temukan semua tahun yang tersedia di data
        available_years = set()
        for item in full_data_from_file:
            for key in item:
                if key.isdigit() and len(key) == 4: # Asumsi tahun adalah 4 digit angka
                    available_years.add(key)
        
        # Urutkan tahun secara ascending
        sorted_years = sorted(list(available_years))

        # Proses data untuk setiap tahun yang ditemukan
        for year in sorted_years:
            year_data_entry = {} # Inisialisasi dictionary kosong
            temp_data_storage = {} # Simpan data sementara untuk tahun ini

            # Pertama, kumpulkan semua data untuk tahun saat ini
            for item in full_data_from_file:
                akun_value = item.get('Akun')
                if akun_value in account_to_output_key_map and year in item:
                    output_key = account_to_output_key_map[akun_value]
                    value_for_year = item.get(year)
                    
                    temp_data_storage[output_key] = {
                        "value": clean_value_string(value_for_year),
                        "conUidence": None
                    }
            
            # Kedua, bangun entri data tahunan dengan urutan yang benar
            for key in desired_output_keys_order:
                if key == "year":
                    year_data_entry['year'] = int(year)
                elif key in temp_data_storage:
                    year_data_entry[key] = temp_data_storage[key]
                else:
                    # Jika kunci tidak ditemukan, tambahkan dengan nilai null
                    year_data_entry[key] = {"value": None, "conUidence": None}
            
            response_payload["read"].append(year_data_entry)
            
        if not response_payload["read"]:
            response_payload["status"] = "FAILED"
            response_payload["reason"] = "No year data found in the file."

            return Response(json.dumps(response_payload, sort_keys=False), mimetype='application/json', status=404)

        # Explicitly create the final dictionary to ensure key order.
        # This is the most reliable way to control the output structure.
        final_response = {
            "status": response_payload["status"],
            "reason": response_payload["reason"],
            "read": response_payload["read"]
        }
        # Use json.dumps with sort_keys=False and return a raw Response object
        # to have full control over the output format and prevent any reordering by jsonify.
        return Response(json.dumps(final_response, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "File bukan JSON yang valid."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)


# =========== KONVESIONAL Laporan Keuangan ============
@app.route('/balance-sheet/ep/konvesional/laporan-keuangan/<filename>', methods=['GET'])
def get_json_file_konvesional_keuangan(filename):
    """
    Mengembalikan laporan JSON lengkap dengan data untuk semua tahun yang ditemukan,
    difomrat sesuai permintaan.
    """
    if not filename.endswith('.json'):
        return jsonify({"error": "Nama file harus berakhiran .json"}, 400)

    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File tidak ditemukan."}, 404)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_data_from_file = json.load(f)
        
        # Struktur respons sesuai permintaan
        response_payload = {
            "status" : "SUCCESS",
            "reason" : "File Successfully Read",
            "read": []
        }

        # Peta dari nilai 'Akun' di JSON asli ke kunci yang diinginkan di output
        # Saya telah memperbarui pemetaan ini berdasarkan contoh output yang Anda berikan
        # dan data JSON input Anda.
        account_to_output_key_map = {
            "Kas dan setara kas": "cash_and_cash_equivalents",
            "Piutang bunga": "interest_receivable",
            "Pinjaman anggota": "member_loans",
            "Penyisihan pinjaman": "loan_loss_provision",
            "Pinjaman koperasi lain": "loans_to_other_cooperatives",
            "Aset tetap": "fixed_assets",
            "Akumulasi penyusutan": "accumulated_depreciation",
            "Aset takberwujud": "intangible_assets",
            "Akumulasi amortisasi": "accumulated_amortization",
            "Aset lain": "other_assets",
            "Total aset": "total_assets",
            "Utang bunga": "interest_payable",
            "Simpanan anggota": "member_deposits",
            "Simpanan koperasi lain": "other_cooperative_deposits",
            "Utang pinjaman": "loan_payable",
            "Liabilitas imbalan kerja": "employee_benefit_liabilities",
            "Liabilitas lain": "other_liabilities",
            "Total liabilitas": "total_liabilities",
            "Simpanan Pokok": "principal_savings",
            "Simpanan Wajib": "mandatory_savings",
            "Cadangan umum": "general_reserve",
            "Sisa hasil usaha": "retained_earnings",
            "Ekuitas lain": "other_equity",
            "Total ekuitas": "total_equity",
            "Total liabilitas dan ekuitas": "total_liabilities_and_equity",
        }

        # Urutan kunci yang diinginkan dalam objek di dalam array 'read'
        # Ini akan menentukan urutan output JSON Anda.
        desired_output_keys_order = [
        "year",
        "cash_and_cash_equivalents",
        "interest_receivable",
        "member_loans",
        "loan_loss_provision",
        "loans_to_other_cooperatives",
        "fixed_assets",
        "accumulated_depreciation",
        "intangible_assets",
        "accumulated_amortization",
        "other_assets",
        "total_assets",
        "interest_payable",
        "member_deposits",
        "other_cooperative_deposits",
        "loan_payable",
        "employee_benefit_liabilities",
        "other_liabilities",
        "total_liabilities",
        "principal_savings",
        "mandatory_savings",
        "general_reserve",
        "retained_earnings",
        "other_equity",
        "total_equity",
        "total_liabilities_and_equity"
        ]

        # Temukan semua tahun yang tersedia di data
        available_years = set()
        for item in full_data_from_file:
            for key in item:
                if key.isdigit() and len(key) == 4: # Asumsi tahun adalah 4 digit angka
                    available_years.add(key)
        
        # Urutkan tahun secara ascending
        sorted_years = sorted(list(available_years))

        # Proses data untuk setiap tahun yang ditemukan
        for year in sorted_years:
            year_data_entry = {} # Inisialisasi dictionary kosong
            temp_data_storage = {} # Simpan data sementara untuk tahun ini

            # Pertama, kumpulkan semua data untuk tahun saat ini
            for item in full_data_from_file:
                akun_value = item.get('Akun')
                if akun_value in account_to_output_key_map and year in item:
                    output_key = account_to_output_key_map[akun_value]
                    value_for_year = item.get(year)
                    
                    temp_data_storage[output_key] = {
                        "value": clean_value_string(value_for_year),
                        "conUidence": None
                    }
            
            # Kedua, bangun entri data tahunan dengan urutan yang benar
            for key in desired_output_keys_order:
                if key == "year":
                    year_data_entry['year'] = int(year)
                elif key in temp_data_storage:
                    year_data_entry[key] = temp_data_storage[key]
                else:
                    # Jika kunci tidak ditemukan, tambahkan dengan nilai null
                    year_data_entry[key] = {"value": None, "conUidence": None}
            
            response_payload["read"].append(year_data_entry)
            
        if not response_payload["read"]:
            response_payload["status"] = "FAILED"
            response_payload["reason"] = "No year data found in the file."

            return Response(json.dumps(response_payload, sort_keys=False), mimetype='application/json', status=404)

        # Explicitly create the final dictionary to ensure key order.
        # This is the most reliable way to control the output structure.
        final_response = {
            "status": response_payload["status"],
            "reason": response_payload["reason"],
            "read": response_payload["read"]
        }
        # Use json.dumps with sort_keys=False and return a raw Response object
        # to have full control over the output format and prevent any reordering by jsonify.
        return Response(json.dumps(final_response, sort_keys=False), mimetype='application/json')
    except json.JSONDecodeError:
        return jsonify({"error": "File bukan JSON yang valid."}, 400)
    except Exception as e:
        return jsonify({"error": str(e)}, 500)


@app.route('/api/download/<filename>', methods=['GET'])
def download_json_file(filename):
    """
    Mengizinkan pengguna mengunduh file JSON tertentu.
    """
    if not filename.endswith('.json'):
        return jsonify({"error": "Nama file harus berakhiran .json"}, 400)
    
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(file_path):
        abort(404) 
    
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    # Pastikan direktori 'output' ada
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)

