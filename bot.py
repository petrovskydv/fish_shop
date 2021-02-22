import os
import logging
import redis
from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
import online_shop

_database = None
logger = logging.getLogger(__name__)


def start(bot, update):
    """
    Хэндлер для состояния START.
    """

    reply_markup = get_keyboard()
    update.message.reply_text(text='Привет!', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def get_keyboard():
    products = online_shop.get_products()
    keyboard = []
    for product in products:
        good = InlineKeyboardButton(product['description'], callback_data=product['id'])
        keyboard.append([good])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def handle_menu(bot, update):
    query = update.callback_query
    product = online_shop.get_product(query.data)
    text = '\n'.join([product['description'], product['meta']['display_price']['with_tax']['formatted']])
    try:
        image_id = product['relationships']['main_image']['data']['id']
        image = online_shop.get_href_file_by_id(image_id)
        bot.deleteMessage(chat_id=query.message.chat.id, message_id=query.message.message_id)
        bot.send_photo(chat_id=query.message.chat_id,
                       photo=image['link']['href'],
                       caption=text)
    except KeyError:
        bot.edit_message_text(text=text,
                              chat_id=query.message.chat_id,
                              message_id=query.message.message_id)

    return 'START'


def handle_users_reply(bot, update):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(bot, update)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = os.environ['REDIS_PASSWORD']
        database_host = os.environ['REDIS_HOST']
        database_port = os.environ['REDIS_PORT']
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    load_dotenv()
    token = os.environ['TELEGRAM_TOKEN']
    client_id = os.environ['STORE_CLIENT_ID']

    online_shop.get_access_token(client_id)

    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
