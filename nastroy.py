import sqlite3
import logging
import re
import random, string
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from os import getenv
from dotenv import load_dotenv

# Loggingni sozlash
logging.basicConfig(level=logging.INFO)
load_dotenv()

ADMIN_CODE = getenv("ADMIN_CODE")
TOKEN = getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= MA'LUMOTLAR BAZASI TIZIMI =================
def init_db():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali (referal_code va referred_by qo'shildi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_seen TEXT,
        referral_code TEXT UNIQUE,
        referred_by TEXT
    )""")
    
    # Arizalar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        username TEXT,
        first_name TEXT,
        fullname TEXT,
        birth_year TEXT,
        phone TEXT,
        subject TEXT,
        created_at TEXT
    )""")
    
    # O'quv markaziga kelgan talabalar jadvali (Yangi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        phone TEXT,
        brought_by_code TEXT,
        arrived_at TEXT
    )""")
    conn.commit()
    conn.close()

# ================= FSM HOLATLARI (STATES) =================
class BotStates(StatesGroup):
    MAIN_MENU = State()
    COURSES_MENU = State()
    
    # Ariza qoldirish holatlari
    APP_NAME = State()
    APP_YEAR = State()
    APP_PHONE = State()
    APP_SUBJECT = State()
    
    # Admin holatlari
    ADMIN_PANEL = State()
    ADMIN_BROADCAST = State()
    
    # Yangi o'quvchi qo'shish holatlari (Admin uchun)
    STUDENTS_PANEL = State()
    ADD_STUDENT_NAME = State()
    ADD_STUDENT_PHONE = State()
    ADD_STUDENT_REF = State()

# ================= YORDAMCHI FUNKSIYALAR =================
def generate_ref_code():
    """Foydalanuvchilar uchun noyob 6 xonali kod yaratadi"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def make_row_keyboard(buttons_matrix: list) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=btn) for btn in row] for row in buttons_matrix]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def update_user_activity(message: Message):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_id = message.from_user.id
    
    username = message.from_user.username if message.from_user.username else ""
    first_name = message.from_user.first_name if message.from_user.first_name else "Foydalanuvchi"

    # Avval foydalanuvchi mavjudligini tekshiramiz (kod o'zgarmasligi uchun)
    cursor.execute("SELECT referral_code FROM users WHERE chat_id = ?", (chat_id,))
    user_data = cursor.fetchone()
    
    if user_data:
        cursor.execute("""
        UPDATE users SET username = ?, first_name = ?, last_seen = ? WHERE chat_id = ?
        """, (username, first_name, now_str, chat_id))
    else:
        new_code = generate_ref_code()
        cursor.execute("""
        INSERT INTO users (chat_id, username, first_name, last_seen, referral_code, referred_by) 
        VALUES (?, ?, ?, ?, ?, ?)
        """, (chat_id, username, first_name, now_str, new_code, None))
        
    conn.commit()
    conn.close()

def build_profile_link_html(chat_id, username, first_name):
    safe_name = first_name.replace("<", "&lt;").replace(">", "&gt;") if first_name else "Foydalanuvchi"
    if username:
        return f'<a href="https://t.me/{username}">{safe_name}</a>'
    return f'<a href="tg://user?id={chat_id}">{safe_name}</a>'

# Global menyular
MAIN_MENU_KBOARD = [
    ["📚 Kurslar haqida ma'lumot", "✈️ Chet elda o'qish"],
    ["📝 Ariza qoldirish", "📍 Manzilimiz"],
    ["📞 Aloqaga chiqish", "💰 Pul ishlash"]
]

COURSES_KBOARD = [
    ["IT", "Robototexnika", "English for kids"],
    ["IELTS", "CEFR", "Rus tili"],
    ["⬅️ Ortga"]
]

ADMIN_MENU_KBOARD = [
    ["📋 Arizalar", "❌ Arizalarni tozalash"], 
    ["📢 Xabar yuborish", "🕒 Oxirgi 48 soat"], 
    ["🧑‍🎓 O'quvchilar paneli", "⬅️ Chiqish"]
]

STUDENTS_MENU_KBOARD = [
    ["➕ Yangi o'quvchi qo'shish", "📊 Kelganlar ro'yxati"],
    ["⬅️ Admin panelga qaytish"]
]

# ================= KO'P FUNKSIYALI ADMIN TEKSHIRUVCHISI =================
@dp.message(F.text == ADMIN_CODE)
async def check_global_admin(message: Message, state: FSMContext):
    update_user_activity(message)
    await state.clear()
    kb = make_row_keyboard(ADMIN_MENU_KBOARD)
    await message.answer("👑 <b>XUSH KELIBSIZ ADMIN PANEL!</b>", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BotStates.ADMIN_PANEL)

# ================= BOT BOSHLANISHI =================
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    update_user_activity(message)
    
    menu_text = "✨ <b>UNIWAY Consulting</b> botiga xush kelibsiz!\nAsosiy menyudan o'zingizga kerakli bo'limni tanlang 👇"
    kb = make_row_keyboard(MAIN_MENU_KBOARD)
    await message.answer(menu_text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(BotStates.MAIN_MENU)

# ================= ASOSIY MENYU LOGIKASI =================
@dp.message(BotStates.MAIN_MENU)
async def process_main_menu(message: Message, state: FSMContext):
    text = message.text
    update_user_activity(message)

    if "Kurslar haqida ma'lumot" in text:
        kb = make_row_keyboard(COURSES_KBOARD)
        await message.answer("📚 Bizning mavjud kurslarimiz. Batafsil ma'lumot uchun fanni tanlang:", reply_markup=kb)
        await state.set_state(BotStates.COURSES_MENU)

    elif "Chet elda o'qish" in text:
        # Chet el matni o'zgarishsiz qoldi...
        chet_el_matni = "✈️ <b>UNIWAY Consulting bilan Xorijda Ta'lim oling!</b>\n\nBatafsil maslahat uchun adminimiz: @bekk_owner"
        await message.answer(chet_el_matni, parse_mode="HTML")

    elif "Manzilimiz" in text:
        latitude = 38.97539774265464   
        longitude = 66.69552288927127  
        await message.answer_location(latitude=latitude, longitude=longitude)
        manzil_matni = "📍 <b>Bizning manzilimiz:</b>\nYakkabog' tumani, Amir Temur ko'chasi.\nMo'ljal: Agrobank ro'parasidagi bino 2-qavatida"
        await message.answer(manzil_matni, parse_mode="HTML")

    elif "Aloqaga chiqish" in text:
        await message.answer("📞 <b>Biz bilan aloqa:</b>\n\nAdmin: @bekk_owner\nTelefon: +998770869988", parse_mode="HTML")

    elif "Ariza qoldirish" in text:
        await message.answer("👤 Ism va familiyangizni kiriting (Faqat harflar bilan):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(BotStates.APP_NAME)
        
    elif "Pul ishlash" in text:
        conn = sqlite3.connect("school.db")
        cursor = conn.cursor()
        cursor.execute("SELECT referral_code FROM users WHERE chat_id = ?", (message.from_user.id,))
        row = cursor.fetchone()
        conn.close()
        
        ref_code = row[0] if row else "Xatolik"
        user_link = build_profile_link_html(message.from_user.id, message.from_user.username, message.from_user.first_name)
        
        pul_matni = (
            "💰 <b>UNIWAY hamkorlik dasturi!</b>\n\n"
            "Do'stlaringizni o'quv markazimizga taklif qiling va pul ishlang! "
            "Quyidagi maxsus xabarni do'stlaringizga yoki guruhlarga tarqating. "
            "Ular markazimizga kelib ushbu kodni ko'rsatishganda sizga bonus yoziladi!\n\n"
            "👇 <b>Do'stlar uchun yuboriladigan xabar:</b>\n"
            "-----------------------------------------\n"
            f"Salam! Men UNIWAY o'quv markazida o'qiyapman. Senga ham tavsiya qilaman! "
            f"Ro'yxatdan o'tishda mening maxsus kodimni taqdim etsang, chegirmaga ega bo'lasan!\n\n"
            f"🔑 <b>Mening maxsus kodim:</b> <code>{ref_code}</code>\n"
            f"👤 <b>Taklif qiluvchi profili:</b> {user_link}\n"
            "-----------------------------------------\n"
            "<i>Eslatma: Kodni nusalab oling va do'stingizga yuboring!</i>"
        )
        await message.answer(pul_matni, parse_mode="HTML", disable_web_page_preview=True)

# ================= KURSLAR MENYUSI LOGIKASI =================
@dp.message(BotStates.COURSES_MENU)
async def process_courses_menu(message: Message, state: FSMContext):
    text = message.text
    update_user_activity(message)

    if text == "⬅️ Ortga":
        kb = make_row_keyboard(MAIN_MENU_KBOARD)
        await message.answer("Asosiy menyu:", reply_markup=kb)
        await state.set_state(BotStates.MAIN_MENU)
        return

    courses_data = {
        "IT": "💻 <b>🚀 IT-KURSLARI</b>\n\nPython, C++, CSS, PostgreSQL, JavaScript.",
        "Robototexnika": "🤖 <b>✨ ROBOTOTEXNIKA</b>\n\nScratch va Arduino platformasi.",
        "English for kids": "👶 <b>🇬🇧 ENGLISH FOR KIDS</b>\n\nBolalar uchun qiziqarli ingliz tili.",
        "IELTS": "📈 <b>🏆 IELTS INTENSIVE</b>\n\nYuqori ball kafolati.",
        "CEFR": "⚠️ Biz CEFR o'qitishdan voz kechdik! Va to'liq IELTS tayyorlovga o'tdik.",
        "Rus tili": "🇷🇺 <b>🗣 RUS TILI (SAYRASH)</b>\n\nErkin va ravon gapirishni o'rganing!"
    }

    if text in courses_data:
        await message.answer(courses_data[text], parse_mode="HTML")
    else:
        await message.answer("⚠️ Iltimos, menyudagi tugmalardan birini tanlang.")

# ================= ARIZA QOLDIRISH LOGIKASI =================
@dp.message(BotStates.APP_NAME)
async def app_name(message: Message, state: FSMContext):
    update_user_activity(message)
    name_text = message.text
    if name_text == ADMIN_CODE: return 
    if re.search(r'\d', name_text):
        await message.answer("❌ Ism va familiyada raqam qatnashishi mumkin emas! Qayta kiriting:")
        return
    await state.update_data(fullname=name_text)
    await message.answer("📅 Tug'ilgan yilingizni kiriting (Masalan: 2005):")
    await state.set_state(BotStates.APP_YEAR)

@dp.message(BotStates.APP_YEAR)
async def app_year(message: Message, state: FSMContext):
    update_user_activity(message)
    year_text = message.text
    if year_text == ADMIN_CODE: return
    if not year_text.isdigit() or len(year_text) != 4:
        await message.answer("❌ Iltimos, yilni to'g'ri formatda kiriting (Masalan: 2004):")
        return
    await state.update_data(birth_year=year_text)
    await message.answer("📞 Telefon raqamingizni kiriting:\nFormati: <code>+998XXXXXXXXX</code>", parse_mode="HTML")
    await state.set_state(BotStates.APP_PHONE)

@dp.message(BotStates.APP_PHONE)
async def app_phone(message: Message, state: FSMContext):
    update_user_activity(message)
    phone_text = message.text.strip()
    if phone_text == ADMIN_CODE: return
    if not re.match(r'^\+998\d{9}$', phone_text):
        await message.answer("❌ Noto'g'ri raqam formati! Qayta kiriting:", parse_mode="HTML")
        return
    await state.update_data(phone=phone_text)
    subject_kb = make_row_keyboard([["IT", "Robototexnika"], ["English for kids", "IELTS"], ["CEFR", "Rus tili"]])
    await message.answer("📚 Qaysi fanni o'qimoqchisiz?", reply_markup=subject_kb)
    await state.set_state(BotStates.APP_SUBJECT)

@dp.message(BotStates.APP_SUBJECT)
async def app_subject(message: Message, state: FSMContext):
    update_user_activity(message)
    if message.text == ADMIN_CODE: return
    
    data = await state.get_data()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_username = message.from_user.username if message.from_user.username else ""
    user_first_name = message.from_user.first_name if message.from_user.first_name else "Foydalanuvchi"

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO applications (chat_id, username, first_name, fullname, birth_year, phone, subject, created_at) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (message.from_user.id, user_username, user_first_name, data['fullname'], data['birth_year'], data['phone'], message.text, now_str))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Arizangiz muvaffaqiyatli qabul qilindi!")
    kb = make_row_keyboard(MAIN_MENU_KBOARD)
    await message.answer("Asosiy menyu:", reply_markup=kb)
    await state.set_state(BotStates.MAIN_MENU)

# ================= ADMIN PANEL LOGIKASI =================
@dp.message(BotStates.ADMIN_PANEL)
async def process_admin_panel(message: Message, state: FSMContext):
    text = message.text
    update_user_activity(message)
    
    if text == "⬅️ Chiqish":
        await state.clear()
        await cmd_start(message, state)
        return

    if text == "🧑‍🎓 O'quvchilar paneli":
        kb = make_row_keyboard(STUDENTS_MENU_KBOARD)
        await message.answer("🧑‍🎓 <b>O'QUVCHILAR BILAN ISHLAH BO'LIMI:</b>", reply_markup=kb, parse_mode="HTML")
        await state.set_state(BotStates.STUDENTS_PANEL)
        return

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()

    if text == "📋 Arizalar":
        cursor.execute("SELECT chat_id, username, first_name, fullname, birth_year, phone, subject, created_at FROM applications ORDER BY id DESC")
        apps = cursor.fetchall()
        if not apps:
            await message.answer("Mavjud arizalar yo'q.")
        else:
            res = "📋 <b>Kelib tushgan arizalar:</b>\n\n"
            for idx, item in enumerate(apps, 1):
                c_id, u_name, f_name, f_fullname, b_year, p_phone, s_sub, c_at = item
                p_link = build_profile_link_html(c_id, u_name, f_name)
                res += f"{idx}. 👤 <b>{f_fullname}</b> ({p_link})\n📅 Yil: {b_year} | 📞 Raqam: {p_phone}\n📚 Fan: {s_sub} | 🕒 {c_at}\n\n"
            await message.answer(res, parse_mode="HTML", disable_web_page_preview=True)

    elif text == "❌ Arizalarni tozalash":
        cursor.execute("DELETE FROM applications")
        conn.commit()
        await message.answer("🗑 Barcha arizalar muvaffaqiyatli o'chirildi va tozalandi!")

    elif text == "📢 Xabar yuborish":
        await message.answer("📝 Xabarni kiriting (Rasm, matn yoki video yuborishingiz mumkin):", reply_markup=make_row_keyboard([["⬅️ Orqaga"]]))
        await state.set_state(BotStates.ADMIN_BROADCAST)

    elif text == "🕒 Oxirgi 48 soat":
        time_threshold = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT chat_id, username, first_name, last_seen FROM users WHERE last_seen >= ? ORDER BY last_seen DESC", (time_threshold,))
        active_users = cursor.fetchall()
        
        if not active_users:
            await message.answer("Yaqin 48 soat ichida hech kim botga kirmadi.")
        else:
            res = f"🕒 <b>Yaqin 48 soat ichida botga kirganlar ({len(active_users)} ta user):</b>\n\n"
            for idx, user in enumerate(active_users, 1):
                c_id, u_name, f_name, l_seen = user
                user_link = build_profile_link_html(c_id, u_name, f_name)
                res += f"{idx}. 👤 {user_link} | 🆔 <code>{c_id}</code> | 🕒 {l_seen}\n"
            await message.answer(res, parse_mode="HTML", disable_web_page_preview=True)
        
    conn.close()

# Admin Reklama tarqatish qismi
@dp.message(BotStates.ADMIN_BROADCAST)
async def admin_broadcast(message: Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        kb = make_row_keyboard(ADMIN_MENU_KBOARD)
        await message.answer("Admin bosh paneli:", reply_markup=kb)
        await state.set_state(BotStates.ADMIN_PANEL)
        return

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM users")
    all_users = cursor.fetchall()
    conn.close()

    success, fail = 0, 0
    await message.answer("📢 Xabar tarqatish boshlandi, biroz kuting...")
    
    for user in all_users:
        try:
            await message.copy_to(chat_id=user[0])
            success += 1
        except Exception:
            fail += 1

    await message.answer(f"✅ Xabar tarqatish tugadi!\n\n🚀 Yetkazildi: {success} ta userga\n❌ Yo'qotildi: {fail} ta user")
    kb = make_row_keyboard(ADMIN_MENU_KBOARD)
    await message.answer("Admin bosh paneli:", reply_markup=kb)
    await state.set_state(BotStates.ADMIN_PANEL)

# ================= O'QUVCHILAR (KELGANLAR) PANELI LOGIKASI =================
@dp.message(BotStates.STUDENTS_PANEL)
async def process_students_panel(message: Message, state: FSMContext):
    text = message.text
    
    if text == "⬅️ Admin panelga qaytish":
        kb = make_row_keyboard(ADMIN_MENU_KBOARD)
        await message.answer("Admin bosh paneli:", reply_markup=kb)
        await state.set_state(BotStates.ADMIN_PANEL)
        return

    if text == "➕ Yangi o'quvchi qo'shish":
        await message.answer("🧑‍🎓 Yangi o'quvchining Ismi va Familiyasini kiriting:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(BotStates.ADD_STUDENT_NAME)
        
    elif text == "📊 Kelganlar ro'yxati":
        conn = sqlite3.connect("school.db")
        cursor = conn.cursor()
        
        # Talabalarni olamiz va ularni olib kelgan foydalanuvchilar ma'lumotlarini JOIN qilamiz
        cursor.execute("""
            SELECT s.fullname, s.phone, s.arrived_at, s.brought_by_code, u.chat_id, u.username, u.first_name 
            FROM students s
            LEFT JOIN users u ON s.brought_by_code = u.referral_code
            ORDER BY s.id DESC
        """)
        students = cursor.fetchall()
        conn.close()
        
        if not students:
            await message.answer("📭 Hozircha kelgan yangi o'quvchilar ro'yxati bo'sh.")
            return
            
        res = "📊 <b>Yangi kelgan o'quvchilar ro'yxati (Barcha vaqtlar):</b>\n\n"
        for idx, item in enumerate(students, 1):
            s_name, s_phone, s_date, s_code, u_id, u_username, u_first = item
            
            if u_id:
                referrer_link = build_profile_link_html(u_id, u_username, u_first)
                ref_info = f"{referrer_link} (Kod: {s_code})"
            else:
                ref_info = f"To'g'ridan-to'g'ri kelgan / Kod: {s_code if s_code else 'Yo\'q'}"
                
            res += f"{idx}. 🧑‍🎓 <b>{s_name}</b>\n"
            res += f" 📞 Tel: {s_phone}\n"
            res += f" 📅 Kelgan vaqti: {s_date}\n"
            res += f" 🔗 Kim olib keldi: {ref_info}\n\n"
            
        await message.answer(res, parse_mode="HTML", disable_web_page_preview=True)

# Yangi o'quvchi qo'shish jarayoni FSM
@dp.message(BotStates.ADD_STUDENT_NAME)
async def add_student_name(message: Message, state: FSMContext):
    await state.update_data(s_name=message.text)
    await message.answer("📞 O'quvchining telefon raqamini kiriting:")
    await state.set_state(BotStates.ADD_STUDENT_PHONE)

@dp.message(BotStates.ADD_STUDENT_PHONE)
async def add_student_phone(message: Message, state: FSMContext):
    await state.update_data(s_phone=message.text)
    await message.answer("🔑 Uni olib kelgan odamning maxsus kodini kiriting (Agar hech kim olib kelmagan bo'lsa 'yoq' deb yozing):")
    await state.set_state(BotStates.ADD_STUDENT_REF)

@dp.message(BotStates.ADD_STUDENT_REF)
async def add_student_ref(message: Message, state: FSMContext):
    ref_code_input = message.text.strip().upper()
    data = await state.get_data()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    brought_by = None if ref_code_input in ["YOQ", "YO'Q", "YOQUVCHI"] else ref_code_input

    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    
    # Agar kod kiritilgan bo'lsa, u haqiqatan bazada borligini tekshiramiz
    if brought_by:
        cursor.execute("SELECT chat_id FROM users WHERE referral_code = ?", (brought_by,))
        ref_exists = cursor.fetchone()
        if not ref_exists:
            await message.answer("❌ Bunday maxsus kod bazada topilmadi! Qaytadan to'g'ri kodni kiriting yoki 'yoq' deb yozing:")
            conn.close()
            return

    # Talabani bazaga qo'shish
    cursor.execute("""
        INSERT INTO students (fullname, phone, brought_by_code, arrived_at)
        VALUES (?, ?, ?, ?)
    """, (data['s_name'], data['s_phone'], brought_by, now_str))
    
    conn.commit()
    conn.close()
    
    await message.answer("✅ Yangi o'quvchi muvaffaqiyatli ro'yxatga olindi va 'Kelganlar ro'yxati'ga qo'shildi!")
    
    kb = make_row_keyboard(STUDENTS_MENU_KBOARD)
    await message.answer("O'quvchilar paneli:", reply_markup=kb)
    await state.set_state(BotStates.STUDENTS_PANEL)

# ================= ISHGA TUSHIRISH =================
async def main():
    init_db()
    print("🤖 BOT ISHLADI...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())