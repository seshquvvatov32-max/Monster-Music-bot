import asyncio
import os
import re
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import FSInputFile, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp

# ===================== SOZLAMALAR =====================
TOKEN = "8559222643:AAHxfSaQ2bHO50IvpqTCjJu8FDgSVCSa0PU"                  
ADMIN_ID = 8213102743  # O'zingizning Telegram IDingiz
SHAZAM_BOT = "https://t.me/SaveOpenBot"

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

URL_REGEXP = re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_for_ad = State()

# ===================== YORDAMCHI FUNKSIYALAR =====================

def get_admin_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Statistika")
    builder.button(text="📢 Reklama Tarqatish")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def clean_title(title: str) -> str:
    patterns = [r'#\w+', r'@\w+', r'http\S+', r'Shorts', r'Reels', r'TikTok', r'\s*\|\s*.*', r'\(.*?\)', r'\[.*?\]']
    for pat in patterns:
        title = re.sub(pat, '', title, flags=re.IGNORECASE)
    return title.strip() or "Musiqa"

def get_ydl_opts(mode="video"):
    if mode == "video":
        return {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(DOWNLOAD_DIR / 'v_%(id)s.%(ext)s'),
            'noplaylist': True, 'quiet': True, 'geo_bypass': True,
        }
    else:
        return {
            'format': 'bestaudio/best',
            'outtmpl': str(DOWNLOAD_DIR / 'a_%(id)s.%(ext)s'),
            'noplaylist': True, 'quiet': True, 'geo_bypass': True,
        }

# ===================== ASOSIY LOGIKA =====================

async def download_all(message: Message, url: str):
    status = await message.answer("🚀 Yuklash boshlandi (HD Sifat)...")
    v_file, a_file = None, None
    try:
        loop = asyncio.get_event_loop()
        
        # 1. Video
        def dl_v():
            with yt_dlp.YoutubeDL(get_ydl_opts("video")) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'video')
        
        v_file, title = await loop.run_in_executor(None, dl_v)
        clean_name = clean_title(title)
        
        await message.answer_video(
            FSInputFile(v_file), 
            caption=f"🎬 <b>{clean_name}</b>\n\nℹ️ <i>Musiqani topish:</i> <a href='{SHAZAM_BOT}'>Shazam Bot</a>", 
            parse_mode="HTML"
        )

        # 2. Audio
        def dl_a():
            with yt_dlp.YoutubeDL(get_ydl_opts("audio")) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        a_file = await loop.run_in_executor(None, dl_a)
        await message.answer_audio(FSInputFile(a_file), title=clean_name, performer="VK Music")
        await status.delete()

    except Exception as e:
        logger.error(e)
        await status.edit_text("❌ Xatolik: Video juda katta yoki havola noto'g'ri.")
    finally:
        for f in [v_file, a_file]:
            if f and os.path.exists(f): os.remove(f)

# ===================== ADMIN VA STATISTIKA =====================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    if not os.path.exists("users.txt"): open("users.txt", "w").close()
    with open("users.txt", "r+") as f:
        users = f.read().splitlines()
        if user_id not in users: f.write(f"{user_id}\n")

    kb = get_admin_kb() if message.from_user.id == ADMIN_ID else None
    await message.answer(
    "👋 <b>Monster Music botga xush kelibsiz!</b>\n\n"
    "Musiqa yuklab olish uchun:\n"
    "1️⃣ Qo'shiq nomi yoki ijrochi nomini yozing (masalan: <i>Konsta Puli</i>)\n"
    "2️⃣ Yoki YouTube/Instagram havolasini (link) yuboring.\n\n"
    "🔍 Men sizga eng yaxshi variantlarni topib beraman!", 
    reply_markup=kb, 
    parse_mode="HTML"
)

@dp.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def cmd_stats(message: Message):
    count = len(open("users.txt").read().splitlines()) if os.path.exists("users.txt") else 0
    await message.answer(f"👥 <b>Jami foydalanuvchilar:</b> {count}", parse_mode="HTML")

@dp.message(F.text == "📢 Reklama Tarqatish", F.from_user.id == ADMIN_ID)
async def ad_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_ad)
    await message.answer("Forward qilish uchun har qanday xabarni yuboring (Rasm, Video, Matn)...")

@dp.message(AdminStates.waiting_for_ad, F.from_user.id == ADMIN_ID)
async def ad_send(message: Message, state: FSMContext):
    await state.clear()
    users = open("users.txt").read().splitlines()
    success, fail = 0, 0
    await message.answer("🚀 Tarqatish boshlandi...")
    
    for uid in users:
        try:
            await message.copy_to(int(uid))
            success += 1
            await asyncio.sleep(0.05)
        except: fail += 1
    
    await message.answer(f"✅ Tayyor!\n<b>Yuborildi:</b> {success}\n<b>Xato:</b> {fail}", parse_mode="HTML", reply_markup=get_admin_kb())

# ===================== QIDIRUV VA YUKLASH =====================

@dp.message(F.text)
async def handle_msg(message: Message):
    if message.from_user.id == ADMIN_ID and message.text in ["📊 Statistika", "📢 Reklama Tarqatish"]: return
    
    url_match = URL_REGEXP.search(message.text)
    if url_match:
        await download_all(message, url_match.group())
    else:
        status = await message.answer(f"🔎 <b>{message.text}</b> qidirilmoqda...")
        loop = asyncio.get_event_loop()
        def search():
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                return ydl.extract_info(f"ytsearch10:{message.text}", download=False).get('entries', [])

        entries = await loop.run_in_executor(None, search)
        if not entries:
            return await status.edit_text("😔 Topilmadi.")

        builder = InlineKeyboardBuilder()
        text = "🔍 <b>Natijalar:</b>\n\n"
        for i, entry in enumerate(entries[:10], 1):
            dur = f"[{int(entry['duration']//60)}:{int(entry['duration']%60):02d}]" if entry.get('duration') else ""
            text += f"{i}. {entry['title'][:50]} {dur}\n"
            builder.button(text=f"🎵 {i}", callback_data=f"audio_{entry['id']}")
        
        builder.adjust(5)
        await status.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("audio_"))
async def callback_audio(call: types.CallbackQuery):
    vid = call.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={vid}"
    status = await call.message.answer("📥 Yuklanmoqda...")
    await call.answer()
    
    filename = None
    try:
        loop = asyncio.get_event_loop()
        def dl():
            with yt_dlp.YoutubeDL(get_ydl_opts("audio")) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), info.get('title', 'audio'), info.get('uploader', 'Artist')
        
        filename, title, artist = await loop.run_in_executor(None, dl)
        await call.message.answer_audio(FSInputFile(filename), title=clean_title(title), performer=artist)
        await status.delete()
    except:
        await status.edit_text("❌ Xato.")
    finally:
        if filename and os.path.exists(filename): os.remove(filename)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

