from flask import Flask, request
import requests
import logging
import json
from geo import is_address, find_coords, find_object, get_image_id, path
from random import choice

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='app.log', format='%(asctime)s %(levelname)s %(name)s %(message)s')
sessionStorage = {}

file = open(path('token.json'), 'r', encoding="utf-8")
tokens = json.loads(file.read())
file.close()

file = open(path('municipals.json'), 'r', encoding="utf-8-sig")
data = json.loads(file.read())
file.close()
municipals = []
for city in data:
    municipals.append(city)

token = tokens["token"]
skill_id = tokens["skill_id"]
search_api_key = tokens["search_api_key"]
del tokens


def delete_image(id):
    url = f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/images/' + str(id)
    requests.delete(url, headers={'Authorization': f'OAuth {token}'}).json()


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    handle_dialog(response, request.json)

    logging.info('Request: %r', response)

    return json.dumps(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']

    if req['session']['new']:
        res['response'][
            'text'] = 'Привет! Я могу найти ближайшую интересующую тебя организацию, например,' \
                      ' магазин, аптеку или кинотеатр, и показать её на карте! Мне нужно знать твой город.'
        sessionStorage[user_id] = {
            'city': None,
            'coords': None,
            'object_name': None,
            'result': None,
            'image_id': None,
            'point': 0,
            'ignore': 0,
            'buttons': {},
            'contact': None
        }
        return
    if req['request']['original_utterance'].lower() in ['помощь', 'помоги', 'что ты умеешь', 'что ты умеешь?']:
        file = open(path('dialogs.json'), 'r', encoding="utf-8")
        text = json.loads(file.read())['help']
        file.close()
        res['response']['text'] = text
    elif sessionStorage[user_id]['city'] is None:
        city = get_city(req)
        if not city:
            res['response']['text'] = 'Я не расслышала город. Можешь повторить?'
        else:
            sessionStorage[user_id]['city'] = city
            if not sessionStorage[user_id]['coords']:
                res['response']['text'] = f'Теперь мне нужно знать твой адрес'
            else:
                res['response']['text'] = f'Что надо найти?'
            sessionStorage[user_id]['buttons']['change_address'] = {
                'title': 'Изменить адрес',
                'hide': True
            }
            sessionStorage[user_id]['buttons']['change_city'] = {
                'title': 'Изменить город',
                'hide': True
            }
    elif sessionStorage[user_id]['coords'] is None:
        address = get_address(sessionStorage[user_id]['city'], req)
        if not address:
            res['response']['text'] = 'Мне кажется, адрес какой-то неправильный. Можешь повторить?'
        else:
            sessionStorage[user_id]['coords'] = address
            res['response']['text'] = f'Отлично, теперь я могу тебе помочь. Что надо найти поблизости?'
            sessionStorage[user_id]['buttons']['change_address'] = {
                'title': 'Изменить адрес',
                'hide': True
            }
            sessionStorage[user_id]['buttons']['change_city'] = {
                'title': 'Изменить город',
                'hide': True
            }
    elif req['request']['original_utterance'].lower() == 'изменить город':
        sessionStorage[user_id]['buttons'].pop('change_address', None)
        sessionStorage[user_id]['buttons'].pop('show_map', None)
        sessionStorage[user_id]['buttons'].pop('skip', None)
        sessionStorage[user_id]['buttons'].pop('site', None)
        sessionStorage[user_id]['buttons'].pop('contact', None)
        if sessionStorage[user_id]['image_id']:
            delete_image(sessionStorage[user_id]['image_id'])
        sessionStorage[user_id]['buttons'].pop('change_city', None)
        sessionStorage[user_id]['city'] = None
        sessionStorage[user_id]['coords'] = None
        res['response']['text'] = 'Хорошо, где же ты теперь?'
    elif req['request']['original_utterance'].lower() == 'изменить адрес':
        sessionStorage[user_id]['buttons'].pop('change_city', None)
        sessionStorage[user_id]['buttons'].pop('show_map', None)
        sessionStorage[user_id]['buttons'].pop('skip', None)
        sessionStorage[user_id]['buttons'].pop('site', None)
        sessionStorage[user_id]['buttons'].pop('contact', None)
        if sessionStorage[user_id]['image_id']:
            delete_image(sessionStorage[user_id]['image_id'])
        sessionStorage[user_id]['buttons'].pop('change_address', None)
        sessionStorage[user_id]['coords'] = None
        res['response']['text'] = 'Хорошо, где же ты теперь?'
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'].lower() == 'сайт организации':
        sessionStorage[user_id]['buttons'].pop('site', None)
        res['response']['text'] = choice(['Ок', 'Хорошо', 'Ладно', 'Окей'])
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'].lower() == 'контактные данные':
        sessionStorage[user_id]['buttons'].pop('contact', None)
        res['response']['text'] = sessionStorage[user_id]['contact']
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'].lower() == 'показать на карте':
        sessionStorage[user_id]['buttons'].pop('show_map', None)
        object_name = sessionStorage[user_id]['object_name']
        coords = sessionStorage[user_id]['result']['coords']
        coords_hrf = sessionStorage[user_id]['result']['coords_hrf']
        if sessionStorage[user_id]['image_id'] is None:
            sessionStorage[user_id]['image_id'] = get_image_id(sessionStorage[user_id]['result'],
                                                               sessionStorage[user_id]['coords'])
        res['response']['text'] = f'Объект "{object_name}" на карте'
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = f'Результат по запросу "{object_name}"'
        res['response']['card']['image_id'] = sessionStorage[user_id]['image_id']
        res['response']['card']['button'] = {}
        res['response']['card']['button']['text'] = 'Найти в Яндекс.Картах'
        res['response']['card']['button'][
            'url'] = f'https://yandex.ru/maps/?clid=9403&ll={str(coords[0])},' \
                     f'{str(coords[1])}&z=14,8&pt={str(coords_hrf)},pm2bm'
    elif sessionStorage[user_id]['result'] and req['request'][
        'original_utterance'].lower() == 'показать другой результат':
        if sessionStorage[user_id]['image_id']:
            delete_image(sessionStorage[user_id]['image_id'])
        sessionStorage[user_id]['ignore'] += 1
        object_name = sessionStorage[user_id]['object_name']
        info = find_object(object_name, sessionStorage[user_id]['coords'], sessionStorage[user_id]['ignore'])
        sessionStorage[user_id]['image_id'] = None
        if not info:
            res['response'][
                'text'] = f'Больше объектов "{object_name}" не найдено. Попробуй изменить запрос или адрес.'
            sessionStorage[user_id]['buttons'].pop('show_map', None)
            sessionStorage[user_id]['buttons'].pop('skip', None)
            sessionStorage[user_id]['buttons'].pop('contact', None)
            sessionStorage[user_id]['buttons'].pop('url', None)
            sessionStorage[user_id]['ignore'] = 0
        else:
            text = f'название: {info["name"]}; адрес: {info["address"]};' \
                   f' время работы: {info["hours"]}; расстояние до объекта: {info["distance"]}'

            res['response']['text'] = f'Объект "{object_name}" найден: ' + text
            sessionStorage[user_id]['buttons']['show_map'] = {
                'title': 'Показать на карте',
                'hide': True
            }
            if info['url']:
                sessionStorage[user_id]['buttons']['site'] = {
                    'title': 'Сайт организации',
                    "url": info['url'],
                    'hide': True
                }
            if info['contact']:
                sessionStorage[user_id]['contact'] = info['contact']
                sessionStorage[user_id]['buttons']['contact'] = {
                    'title': 'Контактные данные',
                    'hide': True
                }
            sessionStorage[user_id]['buttons']['skip'] = {
                'title': 'Показать другой результат',
                'hide': True
            }
            sessionStorage[user_id]['result'] = info
    else:
        sessionStorage[user_id]['buttons'].pop('show_map', None)
        sessionStorage[user_id]['buttons'].pop('skip', None)
        sessionStorage[user_id]['buttons'].pop('site', None)
        sessionStorage[user_id]['buttons'].pop('contact', None)
        if sessionStorage[user_id]['image_id']:
            delete_image(sessionStorage[user_id]['image_id'])
        object_name = req['request']['original_utterance']
        sessionStorage[user_id]['object_name'] = object_name
        sessionStorage[user_id]['ignore'] = 0
        info = find_object(object_name, sessionStorage[user_id]['coords'])
        sessionStorage[user_id]['image_id'] = None
        if not info:
            res['response'][
                'text'] = f'К сожалению, объект "{object_name}" не найден. Попробуй изменить запрос или адрес.'
            sessionStorage[user_id]['buttons'].pop('show_map', None)
        else:
            text = f'название: {info["name"]}; адрес: {info["address"]}; время работы:' \
                   f' {info["hours"]}; расстояние до объекта: {info["distance"]}'
            res['response']['text'] = f'Объект "{object_name}" найден: ' + text
            sessionStorage[user_id]['buttons']['show_map'] = {
                'title': 'Показать на карте',
                'hide': True
            }
            if info['url']:
                sessionStorage[user_id]['buttons']['site'] = {
                    'title': 'Сайт организации',
                    'url': info['url'],
                    'hide': True
                }
            if info['contact']:
                sessionStorage[user_id]['contact'] = info['contact']
                sessionStorage[user_id]['buttons']['contact'] = {
                    'title': 'Контактные данные',
                    'hide': True
                }
            sessionStorage[user_id]['buttons']['skip'] = {
                'title': 'Показать другой результат',
                'hide': True
            }
            sessionStorage[user_id]['result'] = info
    res['response']['buttons'] = list(sessionStorage[user_id]['buttons'].values()) + [{
        'title': 'Помощь',
        'hide': True
    }]


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


def get_city(req):
    city = False

    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':

            if 'city' in entity['value'].keys():
                city = entity['value']['city']

    if not city:
        for municipal in municipals:
            if req['request']['original_utterance'].lower() in municipal.lower():
                city = req['request']['original_utterance']
                break

    return city


def get_address(city, req):
    address = []

    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':

            if 'street' in entity['value'].keys():
                address.append(entity['value']['street'])

            if 'house_number' in entity['value'].keys():
                address.append(entity['value']['house_number'])

            if 'airport' in entity['value'].keys():
                address.append(entity['value']['airport'])

    if len(address) == 0:
        return False
    address = city + ' '.join(address)
    if is_address(address):
        coords = find_coords(address)
        return coords
    return False


if __name__ == '__main__':
    app.run()
