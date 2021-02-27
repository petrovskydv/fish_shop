from telegram import InlineKeyboardButton


def get_products_keyboard(products):
    keyboard = []
    for product in products:
        keyboard.append(
            [
                InlineKeyboardButton(product['description'], callback_data=product['id'])
            ]
        )
    return keyboard


def get_purchase_options_keyboard(product):
    # Задаем количество покупаемого товара
    purchase_options = (1, 5, 10)

    keyboard = []
    purchase_option_button = []
    for purchase_option in purchase_options:
        purchase_option_button.append(
            # id товара и количество - в строке через запятую
            InlineKeyboardButton(f'{purchase_option} кг', callback_data=f'{product["id"]},{purchase_option}')
        )
    keyboard.append(purchase_option_button)
    return keyboard


def get_cart_button():
    return InlineKeyboardButton('Корзина', callback_data='cart')


def get_menu_button():
    return InlineKeyboardButton('В меню', callback_data='back')