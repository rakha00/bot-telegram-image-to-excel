"""
Modul untuk Membuat File Excel.

File ini akan berisi fungsi untuk:
- Mengambil daftar DataFrame (untuk tabel) dan teks (untuk catatan).
- Membuat file Excel baru menggunakan Pandas.
- Menulis setiap DataFrame ke sheet terpisah.
- Menulis teks catatan ke sheet pertama.
- Menyimpan file Excel ke direktori output dan mengembalikan path-nya.
"""

import pandas as pd
from typing import List

def create_excel_file(
    dataframes: List[pd.DataFrame],
    summary_text: str,
    output_path: str
) -> str:
    """
    Membuat file Excel dari daftar DataFrame dan teks ringkasan.

    Args:
        dataframes: Daftar Pandas DataFrame, masing-masing berisi satu tabel.
        summary_text: Teks untuk ditulis di sheet 'Catatan'.
        output_path: Path untuk menyimpan file .xlsx.

    Returns:
        Path ke file Excel yang telah dibuat.
    """
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Tulis sheet Catatan/Summary
            if summary_text and summary_text.strip():
                summary_df = pd.DataFrame({'Catatan': [summary_text]})
                summary_df.to_excel(writer, sheet_name='Catatan', index=False, header=False)

            # Tulis setiap DataFrame tabel ke sheet terpisah
            if not dataframes:
                 # Jika tidak ada tabel, pastikan sheet Catatan tetap dibuat jika ada teks
                if not (summary_text and summary_text.strip()):
                    # Buat file kosong jika tidak ada apa-apa untuk ditulis
                    pd.DataFrame().to_excel(writer, sheet_name='Sheet1')
            else:
                for i, df in enumerate(dataframes):
                    sheet_name = f'Tabel {i+1}'
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return output_path
    except Exception as e:
        print(f"Error saat membuat file Excel: {e}")
        return ""