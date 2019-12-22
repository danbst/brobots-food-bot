import multiprocessing
import datetime
import time

import tinydb
import telebot
from telebot import types
from config import config

db = tinydb.TinyDB(config['DB_PATH'])
parent_query = tinydb.Query()

bot = telebot.TeleBot(config['BOT']['TOKEN'])


def execute_at(wake_time: datetime.time, callback, args=(), kwargs={}):
    while True:
        now = datetime.datetime.now()

        if now.hour == wake_time.hour \
                and now.minute == wake_time.minute \
                and now.second == wake_time.second:
            time.sleep(1)  # without delay it triggers many times a second
            callback(*args, **kwargs)


def get_food_orders():
    for parent in db.all():
        p_id = parent['telegram_id']

        keyboard_options = types.InlineKeyboardMarkup(row_width=2)
        keyboard_options.add(types.InlineKeyboardButton(
            text='Так!', callback_data=f'{p_id}.1'))
        keyboard_options.add(types.InlineKeyboardButton(
            text='Ні...', callback_data=f'{p_id}.0'))

        bot.send_message(parent['telegram_id'],
                         config['BOT']['ASK_MESSAGE'],
                         reply_markup=keyboard_options)


def send_food_orders():
    parents_str = '\n'.join([parent['name']
                             for parent in db if parent.get('order_food', True)])

    bot.send_message(config['ADMIN_ID'], 'Їжу замовляють:\n' + parents_str)


get_data_process = multiprocessing.Process(
    target=execute_at, args=(config['ASK_TIME'], get_food_orders))
send_data_process = multiprocessing.Process(
    target=execute_at, args=(config['SEND_TIME'], send_food_orders))


@bot.message_handler(commands=['start', 'help'])
def start_menu(message: telebot.types.Message):
    bot.reply_to(message, config['BOT']['START_MESSAGE'])
    u = message.chat

    if u.id not in [parent['telegram_id'] for parent in db] and str(u.id) != config['ADMIN_ID']:
        add_parent_keyboard = types.InlineKeyboardMarkup(row_width=1)
        add_parent_keyboard.add(
            types.InlineKeyboardButton(text='Add to database', callback_data=f'{u.id}:{u.first_name} {u.last_name}'))

        bot.send_message(config['ADMIN_ID'],
                         f'New user: {u.id}, {u.username}, {u.first_name}, {u.last_name}',
                         reply_markup=add_parent_keyboard)


@bot.callback_query_handler(func=lambda call: True)
def inline_button(callback):
    data = callback.data

    if '.' in data:
        p_id, order = data.split('.')

        db.update({'order_food': True if order == '1' else False},
                  parent_query.telegram_id == p_id)
        bot.send_message(callback.from_user.id, config['BOT']['ACCEPTED'])

    elif ':' in data:
        p_id, p_name = data.split(':')
        db.insert({'telegram_id': p_id, 'name': p_name})


if __name__ == '__main__':
    get_data_process.start()
    send_data_process.start()

    bot.polling(none_stop=True)