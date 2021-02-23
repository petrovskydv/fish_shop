import logging
import sys
import time
from functools import wraps

import requests

logger = logging.getLogger(__name__)
_token = None
_client_id = None


class DuplicateEmail(Exception):
    def __init__(self, text):
        self.txt = text


class InvalidAccessToken(Exception):
    def __init__(self, text):
        self.txt = text


def check_for_error(response):
    if response.status_code == 409:
        # email уже существует
        raise DuplicateEmail(response.text)
    if response.status_code == 401:
        # время действия токена истекло
        raise InvalidAccessToken(response.text)


def validate_access_token(fnc):
    @wraps(fnc)
    def wrapped(*args, **kwargs):
        try:
            res = fnc(*args, **kwargs)
            return res
        except InvalidAccessToken:
            # если время действия токена истекло то получаем новый и повторяем вызов функции
            get_access_token()
            res = fnc(*args, **kwargs)
            return res
        except DuplicateEmail as e:
            logger.info(e)
        except requests.HTTPError as e:
            print(e, file=sys.stderr)
            logger.exception(e)
        except requests.ConnectionError as e:
            logger.exception(e)
            print(e, file=sys.stderr)
            time.sleep(10)

    return wrapped


def get_headers():
    headers = {
        'Authorization': f'Bearer {_token}',
    }
    return headers


@validate_access_token
def get_all_products():
    headers = get_headers()
    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    check_for_error(response)
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
    headers = get_headers()
    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=headers)
    check_for_error(response)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def get_file_href(product_id):
    headers = get_headers()
    response = requests.get(f'https://api.moltin.com/v2/files/{product_id}', headers=headers)
    check_for_error(response)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def add_product_to_cart(reference, product_id, quantity):
    headers = get_headers()
    headers['Content-Type'] = 'application/json'

    data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity}
    }

    response = requests.post(f'https://api.moltin.com/v2/carts/{reference}/items/', headers=headers, json=data)
    check_for_error(response)
    response.raise_for_status()


@validate_access_token
def remove_product_from_cart(reference, product_id):
    headers = get_headers()

    response = requests.delete(f'https://api.moltin.com/v2/carts/{reference}/items/{product_id}', headers=headers)
    check_for_error(response)
    response.raise_for_status()


@validate_access_token
def get_cart(reference):
    headers = get_headers()

    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}', headers=headers)
    check_for_error(response)
    response.raise_for_status()
    return response.json()


@validate_access_token
def get_cart_items(reference):
    headers = get_headers()
    response = requests.get(f'https://api.moltin.com/v2/carts/{reference}/items', headers=headers)
    check_for_error(response)
    response.raise_for_status()
    review_result = response.json()
    return review_result['data']


@validate_access_token
def create_customer(customer_name, customer_email):
    headers = get_headers()

    data = {
        'data': {
            'type': 'customer',
            'name': customer_name,
            'email': customer_email
        }
    }

    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=data)
    check_for_error(response)
    response.raise_for_status()


def get_access_token(client_id=None):
    set_client_id(client_id)

    payload = {
        'client_id': _client_id,
        'grant_type': 'implicit'
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=payload)
    response.raise_for_status()
    review_result = response.json()

    global _token
    _token = review_result['access_token']


def set_client_id(client_id=None):
    if client_id is None:
        pass
    else:
        global _client_id
        _client_id = client_id
