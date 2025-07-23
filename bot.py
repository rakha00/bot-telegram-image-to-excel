"""
Bot Telegram untuk mengubah file PDF laporan keuangan menjadi JSON menggunakan Gemini Vision API.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import gemini_vision_extractor

# Muat environment variables dari file .env
load_dotenv()

# Konfigurasi logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ambil token dan kunci dari environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Pastikan token dan kunci ada
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan di file .env")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan di file .env")

# Pastikan direktori output dan temp ada
os.makedirs("output", exist_ok=True)
os.makedirs("temp_files", exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kirim pesan selamat datang saat perintah /start dijalankan."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Halo {user.mention_html()}! Kirimkan saya file PDF laporan keuangan, dan saya akan mengubahnya menjadi JSON menggunakan AI."
    )

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani file PDF yang dikirim oleh pengguna."""
    chat_id = update.effective_chat.id
    document = update.message.document

    # Periksa apakah file tersebut adalah PDF
    if document.mime_type != 'application/pdf':
        await update.message.reply_text("Harap kirimkan file dalam format PDF.")
        return

    logger.info(f"Menerima PDF dari chat_id: {chat_id}")
    pdf_file = await document.get_file()

    # Buat path file sementara yang unik
    temp_pdf_path = os.path.join("temp_files", f"{pdf_file.file_id}.pdf")
    await pdf_file.download_to_drive(temp_pdf_path)
    logger.info(f"PDF disimpan sementara di: {temp_pdf_path}")

    # Kirim pesan status awal
    status_message = await context.bot.send_message(
        chat_id=chat_id,
        text="✅ PDF diterima. Memulai analisis dengan AI...",
    )

    # Jalankan proses ekstraksi di latar belakang
    context.application.create_task(
        process_pdf_and_send_json(
            context,
            chat_id,
            temp_pdf_path,
            status_message.message_id,
            os.path.splitext(document.file_name)[0],  # Kirim nama file dasar
        )
    )

async def process_pdf_and_send_json(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    temp_pdf_path: str,
    message_id: int,
    base_filename: str,
) -> None:
    """Memproses PDF menggunakan Gemini, membuat file JSON, dan mengirimkannya."""
    output_json_path = None
    try:
        await context.bot.edit_message_text(
            text="⏳ AI sedang menganalisis PDF... Ini mungkin memakan waktu beberapa saat.",
            chat_id=chat_id,
            message_id=message_id,
        )

        # Panggil fungsi dari gemini_vision_extractor
        json_string = await gemini_vision_extractor.extract_json_from_pdf(temp_pdf_path)

        # Coba parse JSON untuk memvalidasi dan memeriksa error
        try:
            json_data = json.loads(json_string)
            if "error" in json_data:
                error_message = json_data.get("error", "Terjadi kesalahan yang tidak diketahui.")
                raw_response = json_data.get("raw_response")
                full_error_message = f"❌ Gagal memproses PDF: {error_message}"
                if raw_response:
                    full_error_message += f"\n\nRaw Response:\n`{raw_response}`"
                
                await context.bot.edit_message_text(
                    text=full_error_message,
                    chat_id=chat_id,
                    message_id=message_id,
                )
                logger.error(f"Gagal mengekstrak JSON dari PDF: {error_message}")
                return
        except json.JSONDecodeError:
            await context.bot.edit_message_text(
                text="❌ Gagal mem-parse JSON dari respons AI. Coba lagi.",
                chat_id=chat_id,
                message_id=message_id,
            )
            logger.error(f"Gagal mem-parse JSON. Respons mentah: {json_string}")
            return

        # Buat path file output yang unik
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        unique_id = uuid.uuid4().hex[:6]
        output_filename = f"{base_filename}_{timestamp}_{unique_id}.json"
        output_json_path = os.path.join("output", output_filename)

        # Tulis string JSON yang sudah diformat ke file
        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(json_string)
        logger.info(f"JSON berhasil ditulis ke: {output_json_path}")

        # Kirim file JSON ke pengguna
        await context.bot.edit_message_text(
            text="✅ Analisis selesai. Mengirim file JSON...",
            chat_id=chat_id,
            message_id=message_id,
        )
        with open(output_json_path, "rb") as doc:
            await context.bot.send_document(
                chat_id=chat_id,
                document=doc,
                filename=output_filename,
                caption=f"Berikut adalah data JSON yang diekstrak dari {base_filename}.pdf",
            )
        logger.info(f"File JSON berhasil dikirim ke chat_id: {chat_id}")

    except Exception as e:
        logger.error(f"Gagal memproses PDF: {e}", exc_info=True)
        await context.bot.edit_message_text(
            text=f"❌ Terjadi kesalahan tak terduga: {e}",
            chat_id=chat_id,
            message_id=message_id,
        )
    finally:
        # Hapus file sementara
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            logger.info(f"Menghapus file PDF sementara: {temp_pdf_path}")
        # Anda dapat memilih untuk menyimpan atau menghapus file output JSON
        # if output_json_path and os.path.exists(output_json_path):
        #     os.remove(output_json_path)

def main() -> None:
    """Memulai bot Telegram dan mulai polling."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Tambahkan handler untuk perintah dan dokumen
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    # Tambahkan handler untuk pesan teks biasa jika diperlukan
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    print("=" * 50)
    print("INFO: Bot berhasil dimulai dan siap menerima file PDF.")
    print("=" * 50)
    logger.info("Bot mulai polling...")

    # Jalankan bot
    application.run_polling()

if __name__ == "__main__":
    main()