"""
Modul untuk mengekstrak tabel dari gambar menggunakan model vision lokal
yang dijalankan melalui Ollama (misalnya, LLaVA).
"""
import ollama
import base64
import os
import asyncio

def get_image_base64(image_path: str) -> str:
    """Mengonversi file gambar menjadi string base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def generate_ollama_prompt():
    """Builds a very strict prompt to generate a Python script."""
    return """
    **YOUR MISSION: CONVERT THE IMAGE INTO A PYTHON SCRIPT THAT PERFECTLY REPLICATES THE EXCEL GRID.**

    **PRIMARY DIRECTIVES**:
    - **PYTHON CODE ONLY.** Your entire response must be only raw, executable Python code. Do not add any other words, explanations, or markdown formatting.
    - **FOCUS ON GRID STRUCTURE.** Your absolute top priority is placing the data in the correct cells.
    - Use `pandas` for the data and `openpyxl` for `merge_cells`.

    **CRITICAL RULES - DO NOT DO THIS**:
    - **DO NOT** merge cells unless you see a single cell clearly spanning multiple rows or columns in the image.
    - **DO NOT** invent data or rows that are not in the image. If a cell is empty, use `None`.
    - **DO NOT** use `openpyxl.styles` or attempt to replicate any visual styling (bold, alignment, etc.).

    **SIMPLE EXAMPLE**:
    import pandas as pd
    from openpyxl import load_workbook

    def create_excel(output_path: str):
        # The data must mirror the grid. Use None for empty cells.
        data = [
            ['Header 1', 'Header 2', 'Header 3'],
            ['Data A1', 'Data B1', 'Data C1'],
            ['Data A2', None, 'Data C2'] # Cell B3 is empty
        ]
        df = pd.DataFrame(data)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False, header=False)
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            # Example of merging ONLY if it is visually present in the image
            # worksheet.merge_cells('A1:C1')
            workbook.save(output_path)
    """

async def stream_excel_script(image_path: str, model_name: str = 'granite3.2-vision:latest'):
    """
    Menghasilkan skrip Python secara streaming untuk membuat file Excel dari gambar.
    """
    try:
        client = ollama.AsyncClient()
        image_b64 = get_image_base64(image_path)
        prompt_text = generate_ollama_prompt()

        messages = [
            {
                'role': 'user',
                'content': prompt_text,
                'images': [image_b64]
            }
        ]
        
        options = {
            'num_predict': 4096
        }

        async for chunk in await client.chat(model=model_name, messages=messages, options=options, stream=True):
            if content := chunk['message']['content']:
                print(content, end='', flush=True)
                yield content

    except asyncio.TimeoutError:
        print("Error: Waktu pemrosesan Ollama habis (timeout).")
        yield ""
    except Exception as e:
        print(f"Error saat streaming dari Ollama: {e}")
        yield ""