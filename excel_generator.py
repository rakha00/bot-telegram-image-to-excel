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
    output_path: str
) -> str:
    """
    Membuat file Excel dari daftar DataFrame.

    Args:
        dataframes: Daftar Pandas DataFrame, masing-masing berisi satu tabel.
        output_path: Path untuk menyimpan file .xlsx.

    Returns:
        Path ke file Excel yang telah dibuat.
    """
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Tulis setiap DataFrame tabel ke sheet terpisah
            if not dataframes:
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