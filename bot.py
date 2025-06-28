"""
Modul utama untuk Bot Telegram Konversi Gambar ke Excel.
Arsitektur ini menggunakan AI untuk ekstraksi JSON, dan Python untuk pembuatan Excel.
"""
import logging
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

import excel_generator
import ollama_vision_extractor # Menggunakan ekstraktor berbasis Ollama

# Muat environment variables dari .env file
load_dotenv()

# Konfigurasi logging dasar
logging.basicConfig(
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ambil token dari environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN tidak ditemukan di file .env")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan ketika perintah /start dijalankan."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Halo {user.mention_html()}! Kirimkan gambar tabel. Saya akan menggunakan AI (LLaVA) untuk mengekstrak data dan membuat file Excel.",
    )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani pesan gambar, memberikan umpan balik instan, dan memulai proses di latar belakang."""
    os.makedirs("temp_images", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    chat_id = update.effective_chat.id
    photo_file = await update.message.photo[-1].get_file()
    temp_image_path = os.path.join("temp_images", f"{photo_file.file_id}.jpg")
    await photo_file.download_to_drive(temp_image_path)
    logger.info(f"Gambar disimpan di: {temp_image_path}")

    # Kirim pesan konfirmasi instan yang akan kita edit nanti
    status_message = await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Gambar diterima. Memulai analisis..."
    )

    # Jalankan proses yang berat di thread terpisah untuk tidak memblokir bot
    context.application.create_task(
        process_image_in_background(context, chat_id, temp_image_path, status_message.message_id)
    )

async def update_status_indicator(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Mengedit pesan untuk menunjukkan bahwa bot sedang bekerja."""
    indicators = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
    i = 0
    while True:
        try:
            await context.bot.edit_message_text(
                text=f"Analisis sedang berlangsung... {indicators[i % len(indicators)]}",
                chat_id=chat_id,
                message_id=message_id
            )
            i += 1
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Tidak dapat mengedit pesan status: {e}")
            break

async def process_image_in_background(context: ContextTypes.DEFAULT_TYPE, chat_id: int, temp_image_path: str, message_id: int):
    """Fungsi yang berjalan di latar belakang untuk memproses gambar dengan indikator status."""
    output_excel_path = None  # Tetap ada untuk logika pembersihan
    indicator_task = context.application.create_task(
        update_status_indicator(context, chat_id, message_id)
    )

    try:
        logger.info(f"Memulai pemrosesan latar belakang untuk: {temp_image_path}")
        
        # Menggunakan model qwen2.5vl:latest secara eksplisit
        results = await ollama_vision_extractor.extract_tables_with_ollama(temp_image_path, model_name='qwen2.5vl:latest')

        indicator_task.cancel()
        await asyncio.sleep(0.1)  # Beri waktu untuk pembatalan

        if not results:
            await context.bot.edit_message_text(
                text="Analisis selesai. Maaf, tidak ada tabel yang dapat diekstrak.",
                chat_id=chat_id,
                message_id=message_id
            )
            return

        logger.info(f"Berhasil mengekstrak {len(results)} tabel. Membuat file Excel...")
        await context.bot.edit_message_text(
            text=f"✅ Analisis selesai! Ditemukan {len(results)} tabel. Membuat file Excel...",
            chat_id=chat_id,
            message_id=message_id,
        )

        # Pisahkan dataframes
        dataframes = [res[0] for res in results]

        # Buat file Excel
        file_id = os.path.basename(temp_image_path).split('.')[0]
        output_excel_path = os.path.join("output", f"{file_id}_hasil.xlsx")
        
        excel_generator.create_excel_file(dataframes, output_excel_path)
        logger.info(f"File Excel dibuat di: {output_excel_path}")

        # Kirim file Excel
        await context.bot.send_document(
            chat_id=chat_id,
            document=open(output_excel_path, 'rb'),
            filename=os.path.basename(output_excel_path),
            caption="Berikut adalah file Excel dengan data yang diekstrak."
        )

    except Exception as e:
        indicator_task.cancel()
        await asyncio.sleep(0.1)
        logger.error(f"Terjadi kesalahan besar dalam alur kerja latar belakang: {e}", exc_info=True)
        await context.bot.edit_message_text(
            text=f"❌ Maaf, terjadi kesalahan saat memproses gambar: {e}",
            chat_id=chat_id,
            message_id=message_id
        )
    finally:
        if not indicator_task.done():
            indicator_task.cancel()
        
        # Hapus file gambar dan excel sementara
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            logger.info(f"File gambar sementara dihapus: {temp_image_path}")
        if output_excel_path and os.path.exists(output_excel_path):
            os.remove(output_excel_path)
            logger.info(f"File Excel sementara dihapus: {output_excel_path}")


def main() -> None:
    """Memulai dan menjalankan bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    print("="*50)
    print("INFO: Bot berhasil dimulai dan siap menerima gambar.")
    print("="*50)
    logger.info("Bot starting polling...")
    application.run_polling()

if __name__ == "__main__":
    main()