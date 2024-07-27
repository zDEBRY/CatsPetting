'''
BY zDEBRY
Telegramm: t.me/zdebrybio
'''

import sqlite3
import telebot
import os
import random
from datetime import datetime, timedelta
from dateutil import parser
from telebot import types

API_TOKEN = 'Bot_Api_Token'

bot = telebot.TeleBot(API_TOKEN)
# БД
conn = sqlite3.connect('cat_stroke.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    last_stroked TEXT,
                    strokes INTEGER DEFAULT 0,
                    chat_id INTEGER
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    strokes INTEGER DEFAULT 0
                )''')

conn.commit()
# Авто-создание комманд
bot.set_my_commands([
    telebot.types.BotCommand("/start", "Запустить бота"),
    telebot.types.BotCommand("/help", "Помощь"),
    telebot.types.BotCommand("/cat_stroke", "Погладить кота"),
    telebot.types.BotCommand("/stats", "Статистика игроков"),
    telebot.types.BotCommand("/top", "Топ игроков и чатов")
])

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "<b>Привет!</b> Используйте команду <b>/cat_stroke</b>, чтобы погладить кота, и команду <b>/stats</b>, чтобы посмотреть статистику.", parse_mode='HTML')

@bot.message_handler(commands=['cat_stroke'])
def cat_stroke(message):
    username = message.from_user.username
    user_id = message.from_user.id
    chat_id = message.chat.id
    chat_title = message.chat.title

    cursor.execute('SELECT last_stroked FROM users WHERE id = ? AND chat_id = ?', (user_id, chat_id))
    last_stroked_result = cursor.fetchone()

    if last_stroked_result:
        try:
            last_stroked_str = last_stroked_result[0]
            last_stroked = parser.parse(last_stroked_str)
            if datetime.now() - last_stroked < timedelta(hours=1):
                bot.reply_to(message, "Вы уже гладили кота в последний час. Попробуйте позже.")
                return
        except ValueError:
            print(f"Ошибка в формате даты для значения: {last_stroked_result[0]}")

    try:
        cursor.execute('INSERT OR IGNORE INTO users (id, username, last_stroked, strokes, chat_id) VALUES (?, ?, ?, ?, ?)', (user_id, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), 0, chat_id))
        cursor.execute('UPDATE users SET strokes = strokes + 1, last_stroked = ? WHERE id = ? AND chat_id = ?', (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), user_id, chat_id))

        cursor.execute('INSERT OR IGNORE INTO chats (id, title, strokes) VALUES (?, ?, ?)', (chat_id, chat_title, 0))
        cursor.execute('UPDATE chats SET strokes = strokes + 1 WHERE id = ?', (chat_id,))

        conn.commit()

        cursor.execute('SELECT strokes FROM users WHERE id = ? AND chat_id = ?', (user_id, chat_id))
        user_strokes_result = cursor.fetchone()
        user_strokes = user_strokes_result[0] if user_strokes_result else 0

        cursor.execute('SELECT strokes FROM chats WHERE id = ?', (chat_id,))
        chat_strokes_result = cursor.fetchone()
        chat_strokes = chat_strokes_result[0] if chat_strokes_result else 0

        image_folder = os.path.join(os.getcwd(), 'image')
        image_files = [f for f in os.listdir(image_folder) if os.path.isfile(os.path.join(image_folder, f))]
        random_image = random.choice(image_files)
        image_path = os.path.join(image_folder, random_image)

        with open(image_path, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=f'<b>{username}</b>, ты гладишь кота 😺. Всего гладили - <b>{user_strokes}</b> раз.\n'
                                                   f'В этом чате кота гладили <b>{chat_strokes}</b> раз.', parse_mode='HTML')

    except Exception as e:
        print(f"Произошла ошибка при выполнении команды /cat_stroke: {e}")

@bot.message_handler(commands=['stats'])
def stats(message):
    chat_id = message.chat.id
    cursor.execute('SELECT username, strokes FROM users WHERE chat_id = ? ORDER BY strokes DESC LIMIT 10', (chat_id,))
    top_users = cursor.fetchall()

    response = '<b>😺 Топ игроков чата:</b>\n\n'
    medals = ['🥇', '🥈', '🥉']
    for i, (username, strokes) in enumerate(top_users, start=1):
        medal = medals[i-1] if i <= 3 else str(i) + '.'
        response += f'{medal} <b>{username}</b> — {strokes} раз\n'

    cursor.execute('SELECT SUM(strokes) FROM users WHERE chat_id = ?', (chat_id,))
    total_strokes = cursor.fetchone()[0]

    response += f'\nВсего в этом чате кота гладили <b>{total_strokes}</b> раз.'

    bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(commands=['top'])
def top_menu(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('👤 Посмотреть ТОП игроков', callback_data='top_users'))
    keyboard.add(types.InlineKeyboardButton('👥 Посмотреть ТОП чатов', callback_data='top_chats'))

    bot.send_message(message.chat.id, '😺 <b>ТОП лучших игроков и чатов</b>', reply_markup=keyboard, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data in ['top_users', 'top_chats'])
def show_top(call):
    if call.data == 'top_users':
        show_top_users(call.message)
    elif call.data == 'top_chats':
        show_top_chats(call.message)

def show_top_users(message):
    cursor.execute('SELECT username, strokes FROM users ORDER BY strokes DESC LIMIT 10')
    top_users = cursor.fetchall()

    response = '<b>😺 ТОП лучших игроков:</b>\n\n'
    medals = ['🥇', '🥈', '🥉']
    for i, (username, strokes) in enumerate(top_users, start=1):
        medal = medals[i-1] if i <= 3 else str(i) + '.'
        response += f'{medal} <b>{username}</b> — {strokes} раз\n'

    bot.send_message(message.chat.id, response, parse_mode='HTML')

def show_top_chats(message):
    cursor.execute('SELECT title, strokes FROM chats ORDER BY strokes DESC LIMIT 10')
    top_chats = cursor.fetchall()

    response = '<b>😺 ТОП лучших чатов:</b>\n\n'
    medals = ['🥇', '🥈', '🥉']
    for i, (title, strokes) in enumerate(top_chats, start=1):
        medal = medals[i-1] if i <= 3 else str(i) + '.'
        response += f'{medal} <b>{title}</b> — {strokes} раз\n'

    bot.send_message(message.chat.id, response, parse_mode='HTML')

bot.polling()
