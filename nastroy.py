import sqlite3
import logging
import re
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

ADMIN_CODE=getenv("ADMIN_CODE")
TOKEN=getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= MA'LUMOTLAR BAZASI TIZIMI =================
def init_db():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    # Foydalanuvchilar jadvali
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_seen TEXT
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

# ================= YORDAMCHI FUNKSIYALAR =================
def make_keyboard(buttons: list) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=btn)] for btn in buttons]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

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

    cursor.execute("""
    INSERT OR REPLACE INTO users (chat_id, username, first_name, last_seen) 
    VALUES (?, ?, ?, ?)
    """, (chat_id, username, first_name, now_str))
    
    conn.commit()
    conn.close()

def build_profile_link_html(chat_id, username, first_name):
    # HTML rejimida maxsus belgilarni tozalash
    safe_name = first_name.replace("<", "&lt;").replace(">", "&gt;") if first_name else "Foydalanuvchi"
    if username:
        return f'<a href="https://t.me/{username}">{safe_name}</a>'
    return f'<a href="tg://user?id={chat_id}">{safe_name}</a>'

# Global menyular
MAIN_MENU_KBOARD = [
    ["📚 Kurslar haqida ma'lumot", "✈️ Chet elda o'qish"],
    ["📝 Ariza qoldirish", "📍 Manzilimiz"],
    ["📞 Aloqaga chiqish"]
]

COURSES_KBOARD = [
    ["IT", "Robototexnika", "English for kids"],
    ["IELTS", "CEFR", "Rus tili"],
    ["⬅️ Ortga"]
]

ADMIN_MENU_KBOARD = [
    ["📋 Arizalar", "❌ Arizalarni tozalash"], 
    ["📢 Xabar yuborish", "🕒 Oxirgi 48 soat"], 
    ["⬅️ Chiqish"]
]

# ================= KO'P FUNKSIYALI ADMIN TEKSHIRUVCHISI =================
@dp.message(F.text == ADMIN_CODE)
async def check_global_admin(message: Message, state: FSMContext):
    """Foydalanuvchi qaysi holatda bo'lishidan qat'iy nazar kod kiritsa admin panelga o'tadi"""
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
        chet_el_matni = (
            "✈️ <b>UNIWAY Consulting bilan Xorijda Ta'lim oling!</b>\n\n"
            "Kelajagingizni dunyoning eng nufuzli universitetlarida qurish vaqti keldi. "
            "Biz sizga hujjatlar to'plashdan tortib, viza olishgacha bo'lgan barcha jarayonlarda yaqindan ko'maklashamiz! ✨\n\n"
            "🌟 <b>Biz taklif etayotgan TOP davlatlar:</b>\n\n"
            "🇰🇷 <b>JANUBIY KOREYA — Yuqori texnologiyalar va K-Culture vatani!</b>\n"
            "• TOP-100 talikka kiruvchi nufuzli universitetlar.\n"
            "• To'liq va qisman (30% - 100%) GRANT imkoniyatlari.\n"
            "• O'qish davomida qonuniy ishlash va haftasiga 20 soatgacha daromad topish imkoni.\n"
            "• Bitirgandan so'ng Koreyada qolib, nufuzli kompaniyalarda ishlash vizasini olish imkoniyati.\n\n"
            "🇲🇾 <b>MALAYZIYA — Osiyoning eng xavfsiz va ingliz tilli ta'lim markazi!</b>\n"
            "• AQSH, Buyuk Britaniya va Avstraliya universitetlarining filiallarida o'qish imkoniyati (Double Degree — 2 ta diplom).\n"
            "• IELTS ballingiz bo'lsa, 100% viza kafolati va IELTS'siz ham qabul qilinish imkoni.\n"
            "• Yevropa standartidagi ta'lim, lekin yashash va o'qish xarajatlari juda arzon.\n"
            "• To'liq ingliz tili muhiti.\n\n"
            "🇹🇷 <b>TURKIYA — Yevropa va Osiyo chorrahasidagi sifatli ta'lim!</b>\n"
            "• Imtihonsiz, faqatgina attestat yoki diplom baholari bilan talaba bo'lish imkoniyati.\n"
            "• Turkiya davlat universitetlarida o'ta arzon (kontrakt to'lovlarisiz deyarli tekin) o'qish.\n"
            "• Diplomi butun Yevropada va O'zbekistonda to'g'ridan-to'g'ri (nostrifikatsiyasiz) o'tadi.\n"
            "• Madaniyat, til va qadriyatlarimiz juda yaqinligi sababli moslashish oson.\n\n"
            "🔥 <b>Nega aynan UNIWAY?</b>\n"
            "• 100% ishonchli va shaffof shartnoma.\n"
            "• Professional maslahatchilar guruhining individual yondashuvi.\n"
            "• Ketguningizcha va borganingizdan keyin ham doimiy qo'llab-quvvatlash!\n\n"
            "💬 <i>Orzuingizdagi universitetga ilk qadamni hoziroq qo'ying! Batafsil ma'lumot va maslahat uchun adminimiz bilan bog'laning.</i>\n@bekk_owner"
        )
        await message.answer(chet_el_matni, parse_mode="HTML")

    elif "Manzilimiz" in text:
        google_maps_link = "https://maps.app.goo.gl/diM4bQCEmaVoWuKP8"
        latitude = 38.97539774265464   
        longitude = 66.69552288927127  
        
        await message.answer_location(latitude=latitude, longitude=longitude)
        
        manzil_matni = (
            "📍 <b>Bizning manzilimiz:</b>\n"
            "Yakkabog' tumani, Amir Temur ko'chasi.\nMo'ljal: Agrobank ro'parasidagi bino 2-qavatida \n\n"
             f"🌐 <a href='{google_maps_link}'>Google Maps orqali ko'rish</a>"
        )
        await message.answer(manzil_matni, parse_mode="HTML", disable_web_page_preview=False)

    elif "Aloqaga chiqish" in text:
        await message.answer("📞 <b>Biz bilan aloqa:</b>\n\nAdmin: @bekk_owner\nTelefon: +998770869988", parse_mode="HTML")

    elif "Ariza qoldirish" in text:
        await message.answer("👤 Ism va familiyangizni kiriting (Faqat harflar bilan):", reply_markup=ReplyKeyboardRemove())
        await state.set_state(BotStates.APP_NAME)

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
        "IT": (
            "💻 <b>🚀 KELAJAK KASBI: IT-KURSLARI</b>\n\n"
            "Dunyoning eng daromadli sohasiga biz bilan qadam qo'ying! Nol qiymatdan professional darajagacha o'rgatamiz.\n\n"
            "🔥 <b>Bizning yo'nalishlar:</b>\n"
            "🔹 <b>Tillar:</b> Python, C++, CSS, PostgreSQL JavaScript, \n\n"
            "⏱ <b>Davomiyligi:</b> 6 - 9 oy\n"
            "📅 <b>Dars jadvali:</b> Haftada 3 marta, 2 soatdan\n🔹 Bepul qo'shimcha dars olish imkoniyati\n\n"
            "<i>🎯 Kurs davomida real loyihalar (portfolio) yaratasiz va bitiruvchilarga ish topishda ko'maklashiladi!</i>"
        ),
        
        "Robototexnika": (
            "🤖 <b>✨ ROBOTOTEXNIKA — KELAJAK GENIYLARI UCHUN!</b>\n\n"
            "Farzandingiz telefon o'yinlarini yaxshi ko'radimi? Unda o'z robotlarini yaratishni o'rgansin!\n\n"
            "🛠 <b>Kurs dasturida:</b>\n"
            "• Scratch va Arduino platformasida mukammal ishlash\n"
            "• Elektron sxemalar tuzish va modellashtirish\n"
            "• Robotlarni mustaqil dasturlash va boshqarish\n\n"
            "👶 <b>Yosh cheklovi:</b> 7 yoshdan boshlab\n"
            "⚡️ <b>Afzalligi:</b> Darslar 100% amaliy va qiziqarli laboratoriya xonalarida o'tiladi!"
        ),
        
        "English for kids": (
            "👶 <b>🇬🇧 ENGLISH FOR KIDS — BOLALAR UCHUN INGLIZ TILI</b>\n"
            "AMERIKA🇺🇸 VA JANUBIY KOREYA🇰🇷 STANDARTLARI ASOSIDA INGLIZ TILI KURSLARI\n\n"
            "Zerikarli qoidalar va yodlashlardan voz keching! Bolajonlar ingliz tilini yaxshi ko'rib, erkin gapirishni boshlashadi.\n\n"
            "🌟 <b>Bizning metodika:</b>\n"
            "🎲 Interaktiv va quvnoq o'yinlar\n"
            "🎁 Har xil mukofotlar va sovg'alar \n"
            "🎵 Qo'shiqlar, multfilmlar va jamoaviy bahslar\n"
            "🗣 Psixologik to'siqlarsiz erkin muloqot muhiti\n\n"
            "📅 <b>Dars jadvali:</b> Haftada 3 marta\n"
            "<i>💡 Farzandingiz kelajagi uchun eng to'g'ri investitsiyani hozirdan boshlang!</i>"
        ),
        
        "IELTS": (
            "📈 <b>🏆 IELTS INTENSIVE — YUQORI BALL KAFOLATI</b>\n\n"
            "Xorijiy universitetlar va nufuzli grantlar eshigini ochish vaqti keldi! Maqsadli va qisqa muddatli kuchli tizim.\n\n"
            "📌 <b>Kurs ichida nimalar bor?</b>\n"
            "✔️ Har bir modul (Listening, Reading, Writing, Speaking) uchun alohida strategiyalar\n"
            "✔️ Real exam muhitida tayyorgarlik\n"
            "✔️ Ekspert o'qituvchilardan individual feedback (xatolar ustida ishlash)\n"
            "📅 <b>Dars jadvali:</b> Haftada 3 marta\n\n"            
        ),
        
        "CEFR": (
            "⚠️Davlat CEFR imtihonini baholash tizimi judayam rasvo bo'lganligi va hozirgi vaqtlarda ballar judayam past qo'yilayotganligi sababli biz CEFR o'qitishdan voz kechdik! Va to'liq IELTS tayyorlovga o'tdik. "
        ),
        
        "Rus tili": (
            "🇷🇺 <b>🗣 RUS TILI (SAYRASH — RAZGOVOR KURS)</b>\n\n"
            "Rus tilida tushunasiz-u, lekin gapira olmaysizmi? Komplekslardan qutulib, xuddi ona tilingizdek erkin va ravon gapirishni o'rganing!\n\n"
            "🎯 <b>Kurs kimlar uchun?</b>\n"
            "• Rossiyada o'qish yoki ishlamoqchi bo'lganlar\n"
            "• Biznes va kundalik hayotda qiynalmasdan muloqot qilishni istaganlar\n\n"
            "🎧 <b>Metod:</b> Jonli audio va video materiallar, faqat va faqat jonli muloqot darslari!"
        )
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
        await message.answer("❌ Ism va familiyada raqam qatnashishi mumkin emas! Iltimos, qaytadan to'g'ri kiriting:")
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
    await message.answer("📞 Telefon raqamingizni kiriting:\nFormati qat'iy: <code>+998XXXXXXXXX</code> (Jami 13 ta belgi)", parse_mode="HTML")
    await state.set_state(BotStates.APP_PHONE)

@dp.message(BotStates.APP_PHONE)
async def app_phone(message: Message, state: FSMContext):
    update_user_activity(message)
    phone_text = message.text.strip()
    
    if phone_text == ADMIN_CODE: return
    
    if not re.match(r'^\+998\d{9}$', phone_text):
        await message.answer("❌ Noto'g'ri raqam formati!\nIltimos raqamni harflarsiz, jami 9 ta raqam bilan <code>+998XXXXXXXXX</code> ko'rinishida qayta kiriting:", parse_mode="HTML")
        return

    await state.update_data(phone=phone_text)
    
    subject_kb = make_row_keyboard([["IT", "Robototexnika"], ["English for kids", "IELTS"], ["CEFR", "Rus tili"]])
    await message.answer("📚 Qaysi fanni o'qimoqchisiz? Quyidagilardan tanlang:", reply_markup=subject_kb)
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
    (message.from_user.id, user_username, user_first_name, 
     data['fullname'], data['birth_year'], data['phone'], message.text, now_str))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Arizangiz muvaffaqiyatli qabul qilindi! Tez orada aloqaga chiqamiz.")
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
                
                # HTML xavfsiz matnga o'tkazish
                safe_fullname = f_fullname.replace("<", "&lt;").replace(">", "&gt;")
                safe_phone = p_phone.replace("<", "&lt;").replace(">", "&gt;")
                safe_sub = s_sub.replace("<", "&lt;").replace(">", "&gt;")

                res += f"{idx}. 👤 <b>{safe_fullname}</b> ({p_link})\n"
                res += f"    📅 Yil: {b_year} | 📞 Raqam: {safe_phone}\n"
                res += f"    📚 Fan: {safe_sub} | 🕒 {c_at}\n\n"
            await message.answer(res, parse_mode="HTML", disable_web_page_preview=True)

    elif text == "❌ Arizalarni tozalash":
        cursor.execute("DELETE FROM applications")
        conn.commit()
        await message.answer("🗑 Barcha arizalar muvaffaqiyatli o'chirildi va tozalandi!")

    elif text == "📢 Xabar yuborish":
        await message.answer("📝 Xabarni kiriting (Rasm, matn yoki video yuborishingiz mumkin):", reply_markup=make_keyboard(["⬅️ Orqaga"]))
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

# ================= ISHGA TUSHIRISH =================
async def main():
    init_db()
    print("🤖 BOT ISHLADI...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())