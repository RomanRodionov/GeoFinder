import requests
import sys
from math import sin, cos, sqrt, atan2, radians

token = 'AQAAAAAgS2olAAT7o3M-aOYZyEIrstjmDkHoo7c'
skill_id = '8133ff99-d882-481e-831e-67445dd00c26'
search_api_key = 'dda3ddba-c9ea-4ead-9010-f43fbc15c6e3'

def get_geo_info(city, type):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': city,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    if type == 'country':
        return json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty'][
            'GeocoderMetaData']['AddressDetails']['Country']['CountryName']
    elif type == 'coordinates':
        point_str = json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
        point_array = [float(x) for x in point_str.split(' ')]

        return point_array


def get_distance(p1, p2):
    R = 6373.0

    lon1 = radians(p1[0])
    lat1 = radians(p1[1])
    lon2 = radians(p2[0])
    lat2 = radians(p2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance


def is_address(address):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': address,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    if int(json['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found']) > 0:
        return True
    return False

def find_coords(address):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': address,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    toponym = json["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    toponym_coordinates = ','.join(toponym["Point"]["pos"].split())

    return toponym_coordinates

def find_object(name, address_ll, ignore=0):
    search_api_server = "https://search-maps.yandex.ru/v1/"
    api_key = search_api_key

    coords1 = address_ll.split(',')
    coords1 = [float(coords1[0]), float(coords1[1])]

    search_params = {
        "apikey": api_key,
        "text": name,
        "lang": "ru_RU",
        "ll": address_ll,
        "type": "biz"
    }
    try:
        response = requests.get(search_api_server, params=search_params)
        if not response:
            return False

        # Преобразуем ответ в json-объект
        json_response = response.json()
        if len(json_response['features']) <= ignore:
            return False
        # Получаем первую найденную организацию.
        orgs = []
        for org in json_response["features"]:
            distance = get_distance(coords1, org["geometry"]["coordinates"])
            orgs.append([distance, org])
        orgs.sort()
        organization = orgs[ignore][1]
    except Exception:
        return False
    # Название организации.
    org_name = organization["properties"]["CompanyMetaData"].get("name", 'неизвестно')
    # Адрес организации.
    org_address = organization["properties"]["CompanyMetaData"].get("address", 'неизвестно')

    hours = organization["properties"]["CompanyMetaData"].get("Hours", 'неизвестно')
    days = {'Weekdays': 'по будням',
            'Weekend': 'по выходным',
            'Everyday': 'ежедневно',
            'Sunday': 'воскресенье',
            'Monday': 'понедельник',
            'Tuesday': 'вторник',
            'Wednesday': 'среда',
            'Thursday': 'четверг',
            'Friday': 'пятница',
            'Saturday': 'суббота'
            }
    if hours != 'неизвестно':
        hours_a = []
        for availability in hours["Availabilities"]:
            if "TwentyFourHours" in str(availability) and "Everyday" in str(availability):
                hours_a.append('24/7')
            elif "TwentyFourHours" in str(availability):
                text = 'круглосуточно'
                f = False
                for day in days.keys():
                    if availability.get(day, False):
                        f = True
                        text += ', ' + days[day]
                if not f:
                    if hours.get('text', False):
                        text += ', ' + hours['text']
                    else:
                        text += ', рабочие дни неизвестны'
                hours_a.append(text)
            else:
                text = 'с ' + availability['Intervals'][0]['from'][:-3] + \
                        ' до ' + availability['Intervals'][0]['to'][:-3]
                f = False
                for day in days.keys():
                    if availability.get(day, False):
                        f = True
                        text += ', ' + days[day]
                if not f:
                    if hours.get('text', False):
                        text += ', ' + hours['text']
                    else:
                        text += ', рабочие дни неизвестны'
                hours_a.append(text)
        hours = ' / '.join(hours_a)
    # Получаем координаты ответа.
    point = organization["geometry"]["coordinates"]
    org_point = "{0},{1}".format(point[0], point[1])
    info = {'coords_hrf': org_point, 'coords': point, 'name': org_name, 'address': org_address, 'hours': hours}

    return info

def get_image_id(info, address_ll):
    point = info['coords']
    org_point = info['coords_hrf']

    coords1 = address_ll.split(',')
    coords1 = [float(coords1[0]), float(coords1[1])]

    coords2 = [float(point[0]), float(point[1])]

    coords = [(coords1[0] + coords2[0]) / 2, (coords1[1] + coords2[1]) / 2]

    x = abs(coords1[0] - coords2[0]) * 1.4
    y = abs(coords1[1] - coords2[1]) * 1.4

    #long = 'Расстояние до объекта: ' + str(round(get_distance(coords2, coords1))) + ' м'

    #info = [org_name, org_address, 'Режим работы: ' + hours, long]
    # Собираем параметры для запроса к StaticMapsAPI:
    map_params = {
        "ll": ",".join([str(coords[0]), str(coords[1])]),
        "spn": ",".join([str(x), str(y)]),
        "pt": "{0},round".format(address_ll) + "~{0},comma".format(org_point),
        "l": "map"
    }

    map_api_server = "http://static-maps.yandex.ru/1.x/"

    try:
        response = requests.get(map_api_server, params=map_params)
    except Exception as er:
        print(er)

    url = f'https://dialogs.yandex.net/api/v1/skills/{skill_id}/images'
    file = {'file': response.content}
    image_id = requests.post(url, files=file, headers={'Authorization': f'OAuth {token}'}).json()['image']['id']
    return image_id