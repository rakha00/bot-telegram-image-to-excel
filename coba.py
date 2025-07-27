# python_api_example.py (File baru untuk API RESTful)

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

import gemini_vision_extractor  # Asumsi modul ini sudah ada

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan di file .env")

os.makedirs("output", exist_ok=True)
os.makedirs("temp_files", exist_ok=True)

app = FastAPI()

# Fungsi inti yang memproses PDF, sama seperti process_pdf_and_send_json tanpa bagian Telegram
async def process_pdf_file_for_api(temp_pdf_path: str, base_filename: str) -> dict:
    try:
        json_string = await gemini_vision_extractor.extract_json_from_pdf(temp_pdf_path)

        try:
            json_data = json.loads(json_string)
            if "error" in json_data:
                logger.error(f"Gagal mengekstrak JSON dari PDF: {json_data.get('error')}")
                return {"status": "error", "message": json_data.get("error", "Terjadi kesalahan AI.")}
        except json.JSONDecodeError:
            logger.error(f"Gagal mem-parse JSON. Respons mentah: {json_string}")
            return {"status": "error", "message": "Gagal mem-parse JSON dari respons AI."}

        # Simpan file JSON (opsional, tergantung kebutuhan API)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        unique_id = uuid.uuid4().hex[:6]
        output_filename = f"{base_filename}_{timestamp}_{unique_id}.json"
        output_json_path = os.path.join("output", output_filename)

        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(json_string)
        logger.info(f"JSON berhasil ditulis ke: {output_json_path}")

        return {"status": "success", "data": json_data, "output_filename": output_filename}

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat memproses PDF: {e}", exc_info=True)
        return {"status": "error", "message": f"Terjadi kesalahan server: {e}"}
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            logger.info(f"Menghapus file PDF sementara: {temp_pdf_path}")

@app.post("/process_financial_pdf/")
async def upload_pdf_for_processing(pdf_file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if pdf_file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="Hanya file PDF yang diizinkan.")

    logger.info(f"Menerima PDF melalui API: {pdf_file.filename}")

    temp_pdf_path = os.path.join("temp_files", f"{uuid.uuid4().hex}_{pdf_file.filename}")
    try:
        with open(temp_pdf_path, "wb") as buffer:
            while True:
                chunk = await pdf_file.read(1024) # Baca dalam chunk
                if not chunk:
                    break
                buffer.write(chunk)
        logger.info(f"PDF API disimpan sementara di: {temp_pdf_path}")

        # Langsung proses dan kembalikan hasil. Untuk proses yang sangat panjang,
        # pertimbangkan antrean tugas (task queue) seperti Celery.
        result = await process_pdf_file_for_api(temp_pdf_path, os.path.splitext(pdf_file.filename)[0])

        if result["status"] == "success":
            return JSONResponse(content=result["data"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except Exception as e:
        logger.error(f"Gagal menerima atau menyimpan file PDF API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan internal server: {e}")