import logging
import time
from functools import wraps

import requests

logger = logging.getLogger(__name__)
_token = None
_client_id = None
_headers = None


def validate_access_token(fnc):
    @wraps(fnc)
    def wrapped(*args, **kwargs):
        if _token['creation_time'] + _token['expires_in'] < time.time():
            logger.info('Срок действия токена истекает. Получаем новый токен')
            get_access_token()
            set_headers()
        res = fnc(*args, **kwargs)
        return res

    return wrapped


@validate_access_token
def get_all_products():
    logger.info('Получаем список товаров')
    response = requests.get('https://api.moltin.com/v2/products', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    products_for_menu = []
    for product in review_result['data']:
        product_for_menu = {
            'id': product['id'],
            'description': product['description'],
            'price': product['price'][0]['amount']
        }
        products_for_menu.append(product_for_menu)
    return products_for_menu


@validate_access_token
def get_product(product_id):
    logger.info(f'Получаем товар с id {product_id}')
    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def get_file_href(product_id):
    logger.info(f'Получаем ссылку основного изображения товара с id {product_id}')
    response = requests.get(f'https://api.moltin.com/v2/files/{product_id}', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']['link']['href']


@validate_access_token
def add_product_to_cart(reference, product_id, quantity):
    headers = {**_headers, 'Content-Type': 'application/json'}

    data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity
        }
    }
    logger.info(f'Добавляем товар с id {product_id} в количестве {quantity} в корзину {reference}')
    response = requests.post(f'https://api.moltin.com/v2/carts/{reference}/items/', headers=headers, json=data)
    response.raise_for_status()


@validate_access_token
def remove_product_from_cart(reference, product_id):
    logger.info(f'Удаляем товар с id {product_id} из корзины {reference}')
    response = requests.delete(f'https://api.moltin.com/v2/carts/{reference}/items/{product_id}', headers=_headers)
    response.raise_for_status()


@validate_access_token
def get_cart(reference):
    logger.info(f'Получаем данные корзины {reference}')
    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}', headers=_headers)
    response.raise_for_status()
    return response.json()


@validate_access_token
def get_cart_items(reference):
    logger.info(f'Получаем товары корзины {reference}')
    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}/items', headers=_headers)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def create_customer(customer_name, customer_email):
    data = {
        'data': {
            'type': 'customer',
            'name': customer_name,
            'email': customer_email
        }
    }
    logger.info(f'Создаем покупателя {customer_name}, email: {customer_email}')
    response = requests.post('https://api.moltin.com/v2/customers', headers=_headers, json=data)
    response.raise_for_status()


def get_access_token(client_id=None):
    set_client_id(client_id)
    logger.info('Получаем токен')
    payload = {
        'client_id': _client_id,
        'grant_type': 'implicit'
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=payload)
    response.raise_for_status()
    review_result = response.json()

    global _token
    _token = review_result
    _token['expires_in'] = _token['expires_in'] - 10
    _token['creation_time'] = time.time()


def set_headers():
    global _headers
    _headers = {'Authorization': f'Bearer {_token["access_token"]}'}


def set_client_id(client_id=None):
    if client_id is None:
        pass
    else:
        global _client_id
        _client_id = client_id
