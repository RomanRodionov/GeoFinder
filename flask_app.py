from flask import Flask, request
import logging
import json
from geo import get_geo_info, get_distance, is_address, find_coords

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
        res['response']['text'] = 'Привет! Я могу найти ближайший интересующий тебя объект и показать дорогу! Как я могу к тебе обращаться?'
        sessionStorage[user_id] = {
            'first_name': None,
            'coords': None,
            'point': 0
        }
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Мне нужно знать твоё местоположение.'
    #req['request']['original_utterance'].lower() == 'Изменить местоположение'
    elif sessionStorage[user_id]['coords'] is None:
        address = get_address(req)
        if not address:
            res['response']['text'] = 'Мне кажется, адрес какой-то неправильный. Можешь повторить?'
        else:
            sessionStorage[user_id]['coords'] = address
            res['response']['text'] = f'Отлично, теперь я могу тебе помочь. Что надо найти поблизости?'
    else:
        res['response']['text'] = f'Твои координаты: {sessionStorage[user_id]["coords"]}'

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
