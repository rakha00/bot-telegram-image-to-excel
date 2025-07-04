import json
import os

from flask import Flask, abort, jsonify, send_from_directory

app = Flask(__name__)

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

@app.route('/api/json/<filename>', methods=['GET'])
def get_json_file(filename):
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
            "read": []
        }

        # Peta dari nilai 'Akun' di JSON asli ke kunci yang diinginkan di output
        # Saya telah memperbarui pemetaan ini berdasarkan contoh output yang Anda berikan
        # dan data JSON input Anda.
        account_to_output_key_map = {
            "Pendapatan bunga": "interest_income",
            "Jumlah partisipasi anggota": "member_participation", 
            "PARTISIPASI ANGGOTA": "member_participation_category", # Ini kategori, tidak ada di output expectation
            "BEBAN USAHA": "operating_expenses_category", # Ini kategori, tidak ada di output expectation
            "Beban bunga": "interest_expense",
            "Beban penyisihan": "allowance_expense",
            "Beban kepegawaian": "personnel_expense",
            "Beban administrasi dan umum": "administrative_general_expenses",
            "Beban penyusutan dan amortisasi": "depreciation_amortization_expenses",
            "Jumlah beban usaha": "business_expense", 
            "SISA HASIL USAHA BRUTO": "gross_profit", # Tidak ada di output expectation
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
            # Kunci yang tidak ada Akun langsung di JSON input, tetapi ada di output expectation
            # Mereka akan ditambahkan sebagai null jika tidak ada data yang cocok.
            # "other_business_income": "other_business_income", 
            # "other_business_expense": "other_business_expense"
        }

        # Urutan kunci yang diinginkan dalam objek di dalam array 'read'
        # Ini akan menentukan urutan output JSON Anda.
        desired_output_keys_order = [
            "interest_income",
            "other_business_income", # Akan null jika tidak ada Akun yang dipetakan
            "member_participation",
            "interest_expense",
            "allowance_expense",
            "personnel_expense",
            "administrative_general_expenses",
            "depreciation_amortization_expenses",
            "other_business_expense", # Akan null jika tidak ada Akun yang dipetakan
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
            year_data_entry = {"year": int(year)} # Inisialisasi 'year' di sini
            temp_data_storage = {} # Simpan data sementara untuk tahun ini

            for item in full_data_from_file:
                akun_value = item.get('Akun')
                if akun_value in account_to_output_key_map and year in item:
                    output_key = account_to_output_key_map[akun_value]
                    value_for_year = item.get(year) 
                    
                    temp_data_storage[output_key] = {
                        "value": clean_value_string(value_for_year),
                        "confidence": None 
                    }
            
            # Isi year_data_entry berdasarkan urutan yang diinginkan
            for key in desired_output_keys_order[1:]: # Mulai dari kunci kedua setelah 'year'
                if key in temp_data_storage:
                    year_data_entry[key] = temp_data_storage[key]
                else:
                    # Jika kunci tidak ditemukan di data asli atau pemetaan, tambahkan dengan nilai null
                    year_data_entry[key] = {"value": None, "confidence": None}
            
            response_payload["read"].append(year_data_entry)
        if not response_payload["read"]:
            response_payload["status"] = "FAILED"
            response_payload["reason"] = "No year data found in the file."

            return jsonify(response_payload), 404 # Mengembalikan 404 jika tidak ada data tahunan yang ditemukan

        return jsonify(response_payload)
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

