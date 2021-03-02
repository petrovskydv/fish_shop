import logging
import os
from textwrap import dedent

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import Filters, Updater

import online_shop
from keyboards import get_products_keyboard, get_purchase_options_keyboard, get_cart_button, get_menu_button, \
    get_text_and_buttons_for_cart

_database = None
logger = logging.getLogger(__name__)


def start(update, context):
    """Хэндлер для состояния START.

    Выводит кнопки с товарами.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_MENU
    """
    products = online_shop.get_all_products()
    keyboard = get_products_keyboard(products)
    keyboard.append([get_cart_button()])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        update.message.reply_text(text='Привет!', reply_markup=reply_markup)
    elif update.callback_query:
        message = update.callback_query.message
        context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        message.reply_text(text='Привет!', reply_markup=reply_markup)
    logger.info('Выведен список товаров')
    return 'HANDLE_MENU'


def handle_menu(update, context):
    """Хэндлер для состояния HANDLE_MENU.

    Выводит карточку товара из нажатой в меню кнопки.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_DESCRIPTION
    """
    query = update.callback_query
    logger.info(f'Выбран товар с id {query.data}')
    product = online_shop.get_product(query.data)

    keyboard = get_purchase_options_keyboard(product)
    keyboard.append([get_cart_button(), get_menu_button()])
    reply_markup = InlineKeyboardMarkup(keyboard)
    product_price = product['meta']['display_price']['with_tax']

    text = f"""\
    {product['description']}
    {product_price['formatted']}
    """

    try:
        image_id = product['relationships']['main_image']['data']['id']
        image_url = online_shop.get_file_href(image_id)
        context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
        context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, caption=dedent(text),
                               reply_markup=reply_markup)
    except KeyError:
        context.bot.edit_message_text(text=dedent(text), chat_id=query.message.chat_id,
                                      message_id=query.message.message_id,
                                      reply_markup=reply_markup)
    logger.info(f'Выведен товар с id {query.data}')
    return 'HANDLE_DESCRIPTION'


def handle_description(update, context):
    """Хэндлер для состояния HANDLE_DESCRIPTION.

    Добавляет товар в корзину.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_DESCRIPTION
    """
    query = update.callback_query
    product_id, quantity = query.data.split(',')
    logger.info(f'Добавляем товар с id {product_id} в количестве {quantity} корзину {query.message.chat.id}')
    online_shop.add_product_to_cart(query.message.chat.id, product_id, int(quantity))
    query.answer('Товар добавлен в корзину')
    return 'HANDLE_DESCRIPTION'


def handle_cart(update, context):
    """Хэндлер для состояния HANDLE_CART.

    Выводит состав корзины и сумму.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_CART_EDIT
    """
    query = update.callback_query
    logger.info(f'Выводим корзину {query.message.chat.id}')
    products = online_shop.get_cart_items(query.message.chat.id)

    keyboard, text = get_text_and_buttons_for_cart(products)

    keyboard.append([get_menu_button()])
    keyboard.append([InlineKeyboardButton('Оплата', callback_data='payment')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    cart = online_shop.get_cart(query.message.chat.id)
    total = cart['data']['meta']['display_price']['with_tax']['formatted']
    cart_text = f'''\
    {text}
    
        Всего: {total}
    '''

    context.bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    update.callback_query.message.reply_text(text=dedent(cart_text), reply_markup=reply_markup)

    return 'HANDLE_CART_EDIT'


def handle_cart_edit(update, context):
    """Хэндлер для состояния HANDLE_CART_EDIT.

    Удаляет товар из корзины.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние HANDLE_CART_EDIT
    """
    query = update.callback_query
    logger.info(f'Удаляем из корзины {query.message.chat.id} товар с id {query.data}')
    online_shop.remove_product_from_cart(query.message.chat.id, query.data)
    handle_cart(update, context)

    return 'HANDLE_CART_EDIT'


def waiting_email(update, context):
    """Хэндлер для состояния WAITING_EMAIL.

    Запрашивает email.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние CREATE_CUSTOMER
    """
    logger.info('Запрашиваем email')
    update.callback_query.message.reply_text(text='Пришлите, пожалуйста, ваш e-mail')

    return 'CREATE_CUSTOMER'


def create_customer(update, context):
    """Хэндлер для состояния CREATE_CUSTOMER.

    Записывает покупателя в базу CRM.

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        str: состояние END
    """
    message = update.message
    message.reply_text(text=f'Вы прислали эту почту: {message.text}')
    logger.info(f'Записываем покупателя с email {message.text}')
    online_shop.create_customer(message.from_user.first_name, message.text)

    return 'END'


def handle_users_reply(update, context):
    """Хэндлер для обработки всех сообщений.

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

    Args:
        update (:class:`telegram.Update`): Incoming telegram update.
        context (:class:`telegram.ext.CallbackContext`): The context object passed to the callback.

    Returns:
        None
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
    elif user_reply == 'back':
        user_state = 'START'
    elif user_reply == 'cart':
        user_state = 'HANDLE_CART'
    elif user_reply == 'payment':
        user_state = 'WAITING_EMAIL'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'HANDLE_CART_EDIT': handle_cart_edit,
        'WAITING_EMAIL': waiting_email,
        'CREATE_CUSTOMER': create_customer
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def get_database_connection():
    """Соединение с базой банных.

    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.

    Returns:
        (:class:`redis.Redis`): Redis client object
    """
    global _database
    if _database is None:
        database_password = os.environ['REDIS_PASSWORD']
        database_host = os.environ['REDIS_HOST']
        database_port = os.environ['REDIS_PORT']
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def handle_error(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    load_dotenv()

    online_shop.get_access_token(os.environ['STORE_CLIENT_ID'])
    online_shop.set_headers()

    updater = Updater(os.environ['TELEGRAM_TOKEN'])
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.dispatcher.add_error_handler(handle_error)
    updater.start_polling()
