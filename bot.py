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
import importlib.util
import sys
import time
import ollama_vision_extractor # Menggunakan ekstraktor berbasis Ollama
from helpers import ensure_safe_html_for_pre

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

async def stream_and_update_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, image_path: str):
    """Memperbarui pesan secara real-time dengan skrip yang di-stream dari AI."""
    full_script = ""
    last_sent_text = ""
    last_update_time = time.time()
    update_interval = 1.0  # Detik

    initial_text = "⏳ AI sedang membuat skrip...\n\n<pre></pre>"
    await context.bot.edit_message_text(text=initial_text, chat_id=chat_id, message_id=message_id, parse_mode=ParseMode.HTML)
    last_sent_text = initial_text

    async for chunk in ollama_vision_extractor.stream_excel_script(image_path):
        full_script += chunk
        current_time = time.time()
        if current_time - last_update_time > update_interval:
            try:
                safe_content = ensure_safe_html_for_pre(full_script)
                new_text = f"⏳ AI sedang membuat skrip...\n\n<pre>{safe_content}</pre>"
                
                if new_text != last_sent_text:
                    await context.bot.edit_message_text(text=new_text, chat_id=chat_id, message_id=message_id, parse_mode=ParseMode.HTML)
                    last_sent_text = new_text
                last_update_time = current_time
            except Exception as e:
                if "Message is not modified" not in str(e):
                    logger.warning(f"Gagal memperbarui pesan streaming: {e}")
    
    # Pembaruan final untuk memastikan skrip yang lengkap dan bersih ditampilkan
    safe_final_script = ensure_safe_html_for_pre(full_script)
    final_text = f"⏳ AI sedang membuat skrip...\n\n<pre>{safe_final_script}</pre>"
    if final_text != last_sent_text:
        await context.bot.edit_message_text(text=final_text, chat_id=chat_id, message_id=message_id, parse_mode=ParseMode.HTML)
    
    return full_script

async def process_image_in_background(context: ContextTypes.DEFAULT_TYPE, chat_id: int, temp_image_path: str, message_id: int):
    """Fungsi yang berjalan di latar belakang untuk memproses gambar dengan pembaruan status real-time."""
    output_excel_path = None
    temp_script_path = None

    try:
        script_code = await stream_and_update_message(context, chat_id, message_id, temp_image_path)

        if not script_code:
            await context.bot.edit_message_text(
                text="⚠️ Analisis selesai. Maaf, AI tidak dapat menghasilkan skrip untuk gambar ini.",
                chat_id=chat_id,
                message_id=message_id
            )
            return

        await context.bot.edit_message_text(
            text="⚙️ Skrip diterima. Mengeksekusi kode untuk membuat file Excel...",
            chat_id=chat_id,
            message_id=message_id,
        )

        # Membersihkan skrip dari markdown fences sebelum menyimpan
        if script_code.strip().startswith("```python"):
            script_code = script_code.strip()[9:]
        if script_code.strip().endswith("```"):
            script_code = script_code.strip()[:-3]

        file_id = os.path.basename(temp_image_path).split('.')[0]
        output_excel_path = os.path.join("output", f"{file_id}_hasil.xlsx")
        temp_script_path = os.path.join("output", f"{file_id}_script.py")

        with open(temp_script_path, "w", encoding="utf-8") as f:
            f.write(script_code.strip())

        try:
            spec = importlib.util.spec_from_file_location("generated_script", temp_script_path)
            generated_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(generated_module)
            generated_module.create_excel(output_excel_path)
            logger.info(f"Skrip berhasil dieksekusi. File Excel dibuat di: {output_excel_path}")

            await context.bot.edit_message_text(
                text="✅ Eksekusi berhasil. Mengirim file Excel...",
                chat_id=chat_id,
                message_id=message_id,
            )
            await context.bot.send_document(
                chat_id=chat_id,
                document=open(output_excel_path, 'rb'),
                filename=os.path.basename(output_excel_path),
                caption="Berikut adalah file Excel yang dibuat oleh AI."
            )
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

        except Exception as e:
            logger.error(f"Gagal mengeksekusi skrip yang dihasilkan AI: {e}", exc_info=True)
            await context.bot.edit_message_text(
                text=f"❌ Maaf, terjadi kesalahan saat mengeksekusi skrip.\n\n<b>Error:</b>\n<pre>{e}</pre>",
                chat_id=chat_id,
                message_id=message_id,
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.error(f"Terjadi kesalahan besar dalam alur kerja latar belakang: {e}", exc_info=True)
        await context.bot.edit_message_text(
            text=f"❌ Maaf, terjadi kesalahan tak terduga saat memproses gambar.",
            chat_id=chat_id,
            message_id=message_id
        )
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        if temp_script_path and os.path.exists(temp_script_path):
            os.remove(temp_script_path)
        if output_excel_path and os.path.exists(output_excel_path):
            os.remove(output_excel_path)


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