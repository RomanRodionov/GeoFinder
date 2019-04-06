import requests
import sys
from math import sin, cos, sqrt, atan2, radians


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

def find_object(name, address_ll):
    search_api_server = "https://search-maps.yandex.ru/v1/"
    api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"

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

        # Получаем первую найденную организацию.
        organization = json_response["features"][0]
    except Exception:
        return False
    # Название организации.
    org_name = organization["properties"]["CompanyMetaData"]["name"]
    # Адрес организации.
    org_address = organization["properties"]["CompanyMetaData"]["address"]

    hours = organization["properties"]["CompanyMetaData"]["Hours"]

    if "TwentyFourHours" in str(hours["Availabilities"][0]) and "Everyday" in str(hours["Availabilities"][0]):
        hours = '24/7'
    elif "TwentyFourHours" in str(hours["Availabilities"][0]):
        hours = '24, ' + hours['text']
    else:
        hours = 'с ' + hours["Availabilities"][0]['Intervals'][0]['from'] + \
                ' до ' + hours["Availabilities"][0]['Intervals'][0]['to']

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

    x = abs(coords1[0] - coords2[0]) * 1.7
    y = abs(coords1[1] - coords2[1]) * 1.3

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

    url = 'https://dialogs.yandex.net/api/v1/skills/8133ff99-d882-481e-831e-67445dd00c26/images'
    file = {'file': response.content}
    image_id = requests.post(url, files=file, headers={'Authorization': 'OAuth AQAAAAAgS2olAAT7o3M-aOYZyEIrstjmDkHoo7c'}).json()['image']['id']
    return image_id