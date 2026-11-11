import sqlite3
import random
import string
import telebot
from telebot import types

TOKEN = "9214497137:AAGQfTCcwkg7W0vpR10fuQWArtu-0Xz1EgA"
ADMIN_ID = 8672423443
ADMIN_PHONE = "+380975602638"
ADMIN_PASSWORD = "777"

admin_logged_in = {}

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('keys_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            days INTEGER,
            is_used INTEGER DEFAULT 0,
            used_by INTEGER DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def generate_key_string():
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CHESS-{part1}-{part2}"

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_name = message.from_user.first_name
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔑 Активувати ключ", callback_data="enter_key"),
        types.InlineKeyboardButton("💳 Отримати / Купити ключ", callback_data="buy_key"),
        types.InlineKeyboardButton("📱 Завантажити додаток (APK)", callback_data="download_apk"),
        types.InlineKeyboardButton("ℹ️ Інструкція", callback_data="instruction")
    )
    
    if message.from_user.id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛡️ Адмін-панель", callback_data="admin_panel"))

    welcome_text = (
        f"👑 **Вітаю, {user_name}!**\n\n"
        "Це офіційний бот платформи **Chess Bot Mobile**. "
        "Тут ти можеш отримати доступ до софту, активувати ліцензійний ключ та почати гру.\n\n"
        "Обери потрібну опцію в меню нижче:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.from_user.id

    if call.data == "enter_key":
        bot.send_message(
            call.message.chat.id, 
            "✍️ **Активація ключа:**\n\n"
            "Напиши у чат команду активації разом зі своїм ключем у такому форматі:\n"
            "`/activate CHESS-XXXX-XXXX`", 
            parse_mode="Markdown"
        )
    elif call.data == "buy_key":
        bot.send_message(
            call.message.chat.id, 
            "💳 **Придбання або отримання доступу:**\n\n"
            "• Тестовий ключ на 1 день: можна отримати у адміністратора.\n"
            "• Повна версія (30 днів): звертайтесь у підтримку.",
            parse_mode="Markdown"
        )
    elif call.data == "download_apk":
        bot.send_message(
            call.message.chat.id, 
            "📱 **Завантаження додатка:**\n\n"
            "Посилання на останню версію APK-файлу з'явиться тут найближчим часом. Слідкуй за оновленнями!",
            parse_mode="Markdown"
        )
    elif call.data == "instruction":
        bot.send_message(
            call.message.chat.id, 
            "ℹ️ **Покрокова інструкція:**\n\n"
            "1. Отримай унікальний ключ.\n"
            "2. Активуй його тут через кнопку або команду `/activate КЛЮЧ`.\n"
            "3. Встанови APK-додаток на телефон і введи цей же ключ для входу.",
            parse_mode="Markdown"
        )
    elif call.data == "admin_panel":
        if user_id != ADMIN_ID:
            return bot.answer_callback_query(call.id, "❌ У тебе немає прав доступу!", show_alert=True)
        
        if admin_logged_in.get(user_id, False):
            show_admin_menu(call.message.chat.id)
        else:
            msg = bot.send_message(
                call.message.chat.id,
                f"🔐 **Авторизація адміністратора**\n\n"
                f"Номер телефону: `{ADMIN_PHONE}`\n"
                "Введи свій секретний пароль (ПІН-код) у чат:",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, process_admin_password)

    elif call.data.startswith("gen_"):
        if user_id != ADMIN_ID or not admin_logged_in.get(user_id, False):
            return bot.answer_callback_query(call.id, "❌ Потрібна авторизація!", show_alert=True)
        
        days = int(call.data.split("_")[1])
        new_key = generate_key_string()

        conn = sqlite3.connect('keys_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO keys (key, days) VALUES (?, ?)", (new_key, days))
        conn.commit()
        conn.close()

        bot.send_message(
            call.message.chat.id,
            f"✅ **Успішно згенеровано ключ!**\n\n"
            f"🔑 Ключ: `{new_key}`\n"
            f"⏳ Термін дії: **{days} дн.**",
            parse_mode="Markdown"
        )

    elif call.data == "admin_stats":
        if user_id != ADMIN_ID or not admin_logged_in.get(user_id, False):
            return bot.answer_callback_query(call.id, "❌ Потрібна авторизація!", show_alert=True)
        
        conn = sqlite3.connect('keys_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT key, days, is_used, used_by FROM keys")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return bot.send_message(call.message.chat.id, "📊 База ключів наразі порожня.")

        stats_text = "📊 **Статус та активність ключів:**\n\n"
        for r in rows:
            status = f"🟢 Активований (користувач ID: `{r[3]}`)" if r[2] == 1 else "🟡 Вільний"
            stats_text += f"🔑 `{r[0]}` | Днів: {r[1]} | {status}\n"

        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")

def process_admin_password(message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text.strip() == ADMIN_PASSWORD:
        admin_logged_in[message.from_user.id] = True
        bot.send_message(message.chat.id, "✅ **Успішна авторизація!**")
        show_admin_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ **Невірний пароль!** Спробуй знову через меню адмін-панелі.")

def show_admin_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⏱️ Згенерувати на 1 день", callback_data="gen_1"),
        types.InlineKeyboardButton("📅 Згенерувати на 7 днів", callback_data="gen_7"),
        types.InlineKeyboardButton("🚀 Згенерувати на 30 днів", callback_data="gen_30"),
        types.InlineKeyboardButton("📊 Переглянути активність ключів", callback_data="admin_stats")
    )
    bot.send_message(chat_id, "🛡️ **Панель керування ключами:**\nОбери дію:", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['activate'])
def cmd_activate(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.send_message(
            message.chat.id, 
            "⚠️ **Помилка формату!**\nВикористовуй: `/activate CHESS-XXXX-XXXX`", 
            parse_mode="Markdown"
        )

    user_key = args[1].strip()
    user_id = message.from_user.id

    conn = sqlite3.connect('keys_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT days, is_used FROM keys WHERE key = ?", (user_key,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return bot.send_message(message.chat.id, "❌ **Помилка:** Такого ключа не існує в системі!")

    days, is_used = row
    if is_used == 1:
        conn.close()
        return bot.send_message(message.chat.id, "⚠️ **Увага:** Цей ключ уже був активований раніше!")

    cursor.execute("UPDATE keys SET is_used = 1, used_by = ? WHERE key = ?", (user_id, user_key))
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id, 
        f"🎉 **Вітаємо! Ключ успішно активовано!**\n\n"
        f"⏳ Термін дії: **{days} дн.**\n"
        f"🚀 Бажаємо приємної гри!", 
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    print("🤖 Бот із панеллю адміна та обліком активності запущено...")
    bot.infinity_polling()
