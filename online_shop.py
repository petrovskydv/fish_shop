import logging
from functools import wraps
from pprint import pprint
import os

import requests

logger = logging.getLogger(__name__)
_token = None
_client_id = None


def validate_access_token(fnc):
    @wraps(fnc)
    def wrapped(*args, **kwargs):
        try:
            res = fnc(*args, **kwargs)
        except requests.exceptions.HTTPError:
            # TODO сделать проверку на статус 401
            get_access_token()
            res = fnc(*args, **kwargs)
        return res

    return wrapped


@validate_access_token
def get_products():
    headers = get_headers()

    response = requests.get('https://api.moltin.com/v2/products', headers=headers)
    response.raise_for_status()
    review_result = response.json()
    goods = []
    for good in review_result['data']:
        product = {
            'id': good['id'],
            'description': good['description'],
            'price': good['price'][0]['amount']
        }
        goods.append(product)
    return goods


def get_headers():
    headers = {
        'Authorization': f'Bearer {_token}',
    }
    return headers


@validate_access_token
def get_product(product_id):
    headers = get_headers()

    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}', headers=headers)
    print(response.text)
    response.raise_for_status()
    review_result = response.json()
    pprint(review_result)

    return review_result['data']


@validate_access_token
def get_href_file_by_id(product_id):
    headers = get_headers()

    response = requests.get(f'https://api.moltin.com/v2/files/{product_id}', headers=headers)
    print(response.text)
    response.raise_for_status()
    review_result = response.json()
    pprint(review_result)
    return review_result['data']


def download_image(file_name, url, source_path):
    response = requests.get(url, verify=False)
    response.raise_for_status()

    file_path = os.path.join(source_path, file_name)
    with open(file_path, 'wb') as file:
        file.write(response.content)
    logger.info(f'download file: {file_path}')
    return file_path


def create_cart():
    headers = get_headers()
    headers['Content-Type'] = 'application/json'

    data = {
        'data': {
            "id": "b05a9593-73ee-42af-88ef-c35ee4154ef0",
            "type": "cart_item",
            "quantity": 1}
    }

    response = requests.post('https://api.moltin.com/v2/carts/qwerty/items/', headers=headers, json=data)
    print(response.text)
    response.raise_for_status()
    review_result = response.json()
    pprint(review_result)


def get_cart():
    headers = get_headers()

    response = requests.get('https://api.moltin.com/v2/carts/qwerty', headers=headers)
    print(response.text)
    response.raise_for_status()
    review_result = response.json()
    pprint(review_result)


def get_cart_items():
    headers = get_headers()

    response = requests.get('https://api.moltin.com/v2/carts/qwerty/items', headers=headers)
    print(response.text)
    response.raise_for_status()
    review_result = response.json()
    pprint(review_result)


def get_access_token(client_id=None):
    set_client_id(client_id)

    payload = {
        'client_id': _client_id,
        'grant_type': 'implicit'
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=payload)
    response.raise_for_status()
    review_result = response.json()
    pprint(review_result)

    global _token
    _token = review_result['access_token']


def set_client_id(client_id=None):
    if client_id is None:
        pass
    else:
        global _client_id
        _client_id = client_id
