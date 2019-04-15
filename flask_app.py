from flask import Flask, request
import logging
import json
from geo import is_address, find_coords, find_object, get_image_id, path
from random import choice

# https://SkyNET0707.pythonanywhere.com/post
# https://dialogs.yandex.ru/developer/skills/b245f1df-94f4-44e2-aadd-348158a0c34f/draft/test

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='app.log', format='%(asctime)s %(levelname)s %(name)s %(message)s')
sessionStorage = {}


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
                      ' магазин, аптеку или кинотеатр, и показать её на карте! Мне нужно знать твоё местоположение.'
        sessionStorage[user_id] = {
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
    if req['request']['original_utterance'] == 'Помощь':
        file = open(path('dialogs.json'), 'r', encoding="utf-8")
        text = json.loads(file.read())['help']
        file.close()
        res['response']['text'] = text
    elif sessionStorage[user_id]['coords'] is None:
        address = get_address(req)
        if not address:
            res['response']['text'] = 'Мне кажется, адрес какой-то неправильный. Можешь повторить?'
        else:
            sessionStorage[user_id]['coords'] = address
            res['response']['text'] = f'Отлично, теперь я могу тебе помочь. Что надо найти поблизости?'
            sessionStorage[user_id]['buttons']['change_address'] = {
                'title': 'Изменить адрес',
                'hide': True
            }
    elif req['request']['original_utterance'] == 'Изменить адрес':
        sessionStorage[user_id]['buttons'].pop('change_address', None)
        sessionStorage[user_id]['coords'] = None
        res['response']['text'] = 'Хорошо, где же ты теперь?'
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'] == 'Сайт организации':
        sessionStorage[user_id]['buttons'].pop('site', None)
        res['response']['text'] = choice(['Ок', 'Хорошо', 'Ладно', 'Окей'])
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'] == 'Контактные данные':
        sessionStorage[user_id]['buttons'].pop('contact', None)
        res['response']['text'] = sessionStorage[user_id]['contact']
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'] == 'Показать на карте':
        sessionStorage[user_id]['buttons'].pop('show_map', None)
        object_name = sessionStorage[user_id]['object_name']
        cur_coords = sessionStorage[user_id]['coords']
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
    elif sessionStorage[user_id]['result'] and req['request']['original_utterance'] == 'Показать другой результат':
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


def get_address(req):
    address = []
    city = False

    for entity in req['request']['nlu']['entities']:

        if entity['type'] == 'YANDEX.GEO':

            if 'city' in entity['value'].keys():
                address.append(entity['value']['city'])
                city = True

            if 'street' in entity['value'].keys():
                address.append(entity['value']['street'])

            if 'house_number' in entity['value'].keys():
                address.append(entity['value']['house_number'])

            if 'airport' in entity['value'].keys():
                address.append(entity['value']['airport'])

    if len(address) == 0 or not city:
        address = req['request']['original_utterance']
        if not address:
            return False
    else:
        address = ' '.join(address)
    if is_address(address):
        coords = find_coords(address)
        return coords
    return False


if __name__ == '__main__':
    app.run()
