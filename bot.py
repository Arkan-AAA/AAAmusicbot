from dotenv import load_dotenv
load_dotenv()

import os
import logging
import tempfile
import asyncio
import time
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from downloader import MusicDownloader
from shazam_client import ShazamClient

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]

downloader = MusicDownloader()
shazam = ShazamClient()

# Rate limiting
user_requests = defaultdict(list)
MAX_REQUESTS = 5
TIME_WINDOW = 60
REQUEST_TIMEOUT = 120

# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────

def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    user_requests[user_id] = [t for t in user_requests[user_id] if now - t < TIME_WINDOW]
    if len(user_requests[user_id]) >= MAX_REQUESTS:
        return False
    user_requests[user_id].append(now)
    return True

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *Музыкальный бот*\n\n"
        "Отправь мне:\n"
        "• 🔗 Ссылку — YouTube, TikTok, Instagram, VK, SoundCloud, Spotify и др.\n"
        "• 🔍 Название песни или исполнителя (на любом языке)\n\n"
        "Для ссылок TikTok/Instagram я распознаю трек через Shazam "
        "и найду полную версию 🎧",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏱ Слишком много запросов. Подожди минуту.")
        return
    
    text = update.message.text.strip()
    is_url = text.startswith("http://") or text.startswith("https://")

    msg = await update.message.reply_text("⏳ Обрабатываю...")

    try:
        if is_url:
            await asyncio.wait_for(_handle_url(update, context, text, msg), timeout=REQUEST_TIMEOUT)
        else:
            await asyncio.wait_for(_handle_search(update, context, text, msg), timeout=REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        await msg.edit_text("⏱ Превышено время ожидания. Попробуй позже.")
    except Exception as e:
        logger.exception("handle_message error")
        await msg.edit_text(f"❌ Ошибка: {e}")


# ─────────────────────────────────────────────
# URL FLOW
# ─────────────────────────────────────────────

async def _handle_url(update, context, url: str, msg):
    platform = downloader.detect_platform(url)
    logger.info(f"Platform detected: {platform} | {url}")

    with tempfile.TemporaryDirectory() as tmp:

        if platform in ("TikTok", "Instagram", "Twitter/X", "Facebook"):
            await msg.edit_text(f"🎵 Определяю трек через Shazam ({platform})...")

            raw_audio = await downloader.download_raw_audio(url, tmp)
            if not raw_audio:
                await msg.edit_text("❌ Не удалось скачать видео.")
                return

            track = await shazam.recognize(raw_audio)

            if track:
                artist, title = track["artist"], track["title"]
                await msg.edit_text(
                    f"✅ Распознан: *{artist} — {title}*\n🔍 Ищу полную версию...",
                    parse_mode="Markdown"
                )
                results = await downloader.search_track(f"{artist} {title}", limit=6)
                if results:
                    _store_results(context, update.effective_user.id, results)
                    await msg.delete()
                    await _send_results_keyboard(update, results, f"{artist} — {title}")
                    return
                else:
                    await msg.edit_text("⚠️ Полная версия не найдена. Отправляю оригинал...")

            else:
                await msg.edit_text("⚠️ Не удалось распознать трек. Отправляю оригинал...")

            # fallback — send original
            mp3 = await downloader.extract_audio(url, tmp)
            if mp3:
                await msg.delete()
                await _send_audio(update, mp3)
            else:
                await msg.edit_text("❌ Не удалось извлечь аудио.")

        else:
            # YouTube, SoundCloud, VK, Deezer, etc.
            await msg.edit_text(f"📥 Скачиваю аудио ({platform})...")
            mp3 = await downloader.extract_audio(url, tmp)
            if mp3:
                meta = await downloader.get_meta(url)
                await msg.delete()
                await _send_audio(update, mp3,
                                  title=meta.get("title"),
                                  artist=meta.get("artist"))
            else:
                await msg.edit_text("❌ Не удалось скачать аудио с этой ссылки.")


# ─────────────────────────────────────────────
# SEARCH FLOW
# ─────────────────────────────────────────────

async def _handle_search(update, context, query: str, msg):
    await msg.edit_text(f"🔍 Ищу: *{query}*...", parse_mode="Markdown")

    results = await downloader.search_track(query, limit=8)
    if not results:
        await msg.edit_text("😔 Ничего не найдено. Попробуй уточнить запрос.")
        return

    _store_results(context, update.effective_user.id, results)
    await msg.delete()
    await _send_results_keyboard(update, results, query)


# ─────────────────────────────────────────────
# CALLBACK — download chosen track
# ─────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    logger.info(f"Callback received: {query.data}")
    await query.answer()

    if query.data == "cancel":
        await query.message.delete()
        return

    if not query.data.startswith("dl:"):
        return

    track_id = query.data[3:]
    user_id  = update.effective_user.id
    data = context.bot_data.get(f"res_{user_id}", {})
    
    if not data or time.time() > data.get("expires", 0):
        await query.edit_message_text("❌ Результаты устарели. Попробуй снова.")
        context.bot_data.pop(f"res_{user_id}", None)
        return
    
    tracks = data.get("tracks", {})
    logger.info(f"Track ID: {track_id}, User: {user_id}, Tracks: {list(tracks.keys())}")
    track = tracks.get(track_id)

    if not track:
        await query.edit_message_text("❌ Трек не найден, попробуй снова.")
        return

    await query.edit_message_text(
        f"📥 Скачиваю: *{track['artist']} — {track['title']}*...",
        parse_mode="Markdown"
    )

    try:
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = await asyncio.wait_for(downloader.download_by_id(track, tmp), timeout=REQUEST_TIMEOUT)
            logger.info(f"Downloaded file: {mp3}")
            
            if mp3 and os.path.exists(mp3):
                file_size = os.path.getsize(mp3)
                if file_size > 50 * 1024 * 1024:
                    await query.edit_message_text("❌ Файл слишком большой (>50 МБ). Попробуй другой.")
                    return
                
                chat_id = update.effective_chat.id
                
                with open(mp3, "rb") as f:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=f,
                        title=track["title"],
                        performer=track["artist"]
                    )
                await query.message.delete()
            else:
                await query.edit_message_text("❌ Не удалось скачать. Попробуй другой вариант.")
    except asyncio.TimeoutError:
        await query.edit_message_text("⏱ Превышено время ожидания. Попробуй другой трек.")
    except Exception as e:
        logger.exception("Callback error")
        await query.edit_message_text(f"❌ Ошибка: {e}")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _store_results(context, user_id: int, results: list):
    key = f"res_{user_id}"
    context.bot_data[key] = {
        "tracks": {t["id"]: t for t in results},
        "expires": time.time() + 600
    }


async def _send_results_keyboard(update: Update, results: list, query: str):
    keyboard = []

    for i, t in enumerate(results, 1):
        label = f"{i}. {t['artist'][:18]} — {t['title'][:22]}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"dl:{t['id']}")])

    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])

    await update.effective_message.reply_text(
        f"🎵 Выбери трек:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _send_audio(update: Update, path: str,
                      title: str = None, artist: str = None):
    chat_id = update.effective_chat.id
    bot = update.get_bot()
    
    # Sanitize path to prevent path traversal
    safe_path = os.path.abspath(path)
    if not os.path.exists(safe_path) or not os.path.isfile(safe_path):
        raise ValueError("Invalid file path")
    
    with open(safe_path, "rb") as f:
        await bot.send_audio(
            chat_id=chat_id,
            audio=f,
            title=title,
            performer=artist,
        )


# ─────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────

async def cleanup_expired(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    expired = [k for k, v in context.bot_data.items() 
               if k.startswith("res_") and isinstance(v, dict) and now > v.get("expires", 0)]
    for key in expired:
        context.bot_data.pop(key, None)
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired results")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    if app.job_queue:
        app.job_queue.run_repeating(cleanup_expired, interval=300, first=300)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
